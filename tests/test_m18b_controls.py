"""M18b tests: Gudmundsson Example 24-6 (d) for tau_e and CL_delta_e, Table 24-6 ranges, identities of the hinge-moment relations
(floating angle zeroes C_H; free lift-slope factor follows from the floating angle), the manual-gearing geometry and the project chain."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite import m18b_controls as c

EXAMPLE = Path(__file__).parents[1] / "examples" / "projects" / "c172-like-controls-inputs.json"


class BookTests(unittest.TestCase):
    def test_example_24_6_d_elevator_effectiveness(self):
        tau = c.tau_elevator(0.3)
        self.assertAlmostEqual(tau, 0.5066, delta=5e-4)                  # printed 0.5066
        self.assertAlmostEqual(4.529 * tau, 2.294, delta=2e-3)           # CL_delta_e = CL_alpha_HT tau = 2.294 per rad
        self.assertAlmostEqual(4.529 * tau / 57.29578, 0.04004, delta=5e-5)

    def test_tau_limits(self):
        self.assertAlmostEqual(c.tau_elevator(0.0), 0.0316)
        self.assertAlmostEqual(c.tau_elevator(1.0), -4.66 + 8.79 - 6.44 + 2.85 + 0.0316)


class RelationTests(unittest.TestCase):
    def test_float_angle_zeroes_hinge_coefficient(self):
        cha, chd, alpha = -0.12, -0.55, math.radians(4.0)
        delta = c.float_angle(cha, chd, alpha)
        self.assertAlmostEqual(c.hinge_coefficient(ch_alpha=cha, alpha=alpha, ch_delta=chd, delta=delta), 0.0, places=12)

    def test_free_lift_slope_factor_from_floating_angle(self):
        cla, tau, cha, chd, alpha = 4.5, 0.5, -0.12, -0.55, 0.05
        cl = cla * alpha + cla * tau * c.float_angle(cha, chd, alpha)       # CL_delta = CL_alpha tau
        self.assertAlmostEqual(cl, cla * alpha * c.free_lift_slope_factor(tau, cha, chd), places=12)
        self.assertLess(c.free_lift_slope_factor(tau, cha, chd), 1.0)        # underbalanced destabilizes (Sec. 24.4.2)
        self.assertGreater(c.free_lift_slope_factor(tau, 0.1, chd), 1.0)     # overbalanced stabilizes

    def test_balance_class(self):
        self.assertEqual(c.balance_class(-0.1), "underbalanced")
        self.assertEqual(c.balance_class(0.0), "unbalanced")
        self.assertEqual(c.balance_class(0.1), "overbalanced")

    def test_hinge_moment(self):
        self.assertAlmostEqual(c.hinge_moment(1000.0, 0.4, 0.7, -0.1), -28.0)

    def test_manual_gearing(self):
        g = c.manual_elevator_gearing(0.5, 0.2, 0.1, math.radians(10.0))
        self.assertAlmostEqual(g["pushrod_shift_m"], 0.2 * math.sin(math.radians(10.0)))
        self.assertAlmostEqual(math.sin(g["delta_e_rad"]) * 0.1, g["pushrod_shift_m"])
        # virtual work at small angles: F_S l1 dS ~ HM dE  ->  F_S/HM ~ dE/(l1 dS) = gain of rotation / l1
        self.assertAlmostEqual(g["force_gain_per_m"], 0.2 * math.cos(math.radians(10.0)) / (0.5 * 0.1))

    def test_strip_geometry(self):
        s = c.strip_geometry(5.0, 2.0, 1.0, 0.0, 1.0, 0.25)
        self.assertAlmostEqual(s["mean_chord_m"], 1.5)
        self.assertAlmostEqual(s["s_f_m2"], 0.25 * 1.5 * 5.0)


class ProjectTests(unittest.TestCase):
    def build(self, tmp, mutate=None):
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        if mutate:
            mutate(data)
        src = Path(tmp) / "in.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        path = Path(tmp) / "p.json"
        main(["project-init", "--project", str(path), "--name", "c", "--from-inputs", str(src)])
        for mod in ("m09b", "m08", "m10", "m12", "m13", "m16", "m18b"):
            main([mod, "--project", str(path)])
        return path

    def test_chain_stale_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.build(tmp)
            data = prj.load(path)
            r = data["outputs"]["m18b"]["result"]
            self.assertEqual(sorted(data["outputs"]["m18b"]["run"]["depends_on"]), ["m08", "m09b", "m16"])
            self.assertEqual(prj.stale(data), [])
            for name in ("aileron", "elevator", "rudder"):
                self.assertTrue(r[name]["table_24_6"]["cf_within_range"])
                self.assertGreater(r[name]["hinge"]["max_abs_hinge_moment_nm"], 0.0)
                self.assertGreater(r[name]["control_force"]["max_abs_stick_force_n"], 0.0)
            fe = r["elevator"]["free_elevator"]
            self.assertLess(fe["lift_slope_factor"], 1.0)
            self.assertLess(fe["neutral_point"]["h_n_stick_free_without_fuselage"], fe["neutral_point"]["h_n_stick_fixed_without_fuselage"])
            data["outputs"]["m08"]["result"]["horizontal_tail"]["area_m2"] += 0.1
            self.assertIn("m18b", prj.stale(data))
            out = Path(tmp) / "m18b.json"
            main(["export", "--project", str(path), "--module", "m18b", "--out", str(out)])
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["module"], "m18b")

    def test_no_derivatives_reports_geometry_only(self):
        def mutate(d):
            d["m18b"]["rudder"].pop("ch_delta_per_rad")
        with tempfile.TemporaryDirectory() as tmp:
            r = prj.load(self.build(tmp, mutate))["outputs"]["m18b"]["result"]["rudder"]
            self.assertIn("status", r["hinge"])
            self.assertIn("geometry", r)

    def test_force_scales_with_dynamic_pressure(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases = prj.load(self.build(tmp))["outputs"]["m18b"]["result"]["aileron"]["hinge"]["cases"]
            lo = [x for x in cases if x["speed_mps"] == 30.0 and x["delta_deg"] < 0][0]
            hi = [x for x in cases if x["speed_mps"] == 40.0 and x["delta_deg"] < 0][0]
            self.assertAlmostEqual(hi["hinge_moment_nm"] / lo["hinge_moment_nm"], (40.0 / 30.0) ** 2)


if __name__ == "__main__":
    unittest.main()
