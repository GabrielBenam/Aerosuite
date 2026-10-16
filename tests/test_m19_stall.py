"""M19 tests: lifting line against the elliptic-wing closed form (independent theory), thin-airfoil alpha_ZL of NACA 4-digit sections, the
inversion consistency of Eqs. 9-139/9-140, the benign-stall criteria on controlled distributions, the washout trend, the project chain, and
a contrast with REAL flow5 7.55 output (evidence/flow5-7.55-win/run2-custom-ref): C_L_alpha of the wing-tail model against the wing alone."""
import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite import m19_stall as m

EXAMPLE = Path(__file__).parents[1] / "examples" / "projects" / "c172-like-stall-inputs.json"
FLOW5_OUT = Path(__file__).resolve().parents[1] / "evidence" / "flow5-7.55-win" / "run2-custom-ref" / "output"


class TheoryTests(unittest.TestCase):
    def test_elliptic_wing_lift_slope_and_efficiency(self):
        b, c0, a0 = 10.0, 1.6, 2.0 * math.pi
        chords = lambda e: c0 * math.sqrt(max(1.0 - e * e, 0.0))
        zero = lambda e: 0.0
        ar = b * b / m._area(b, chords)
        sol = m.llt_solve(b, chords, lambda e: a0, zero, zero, math.radians(5.0))
        self.assertAlmostEqual(sol["cl_total"], a0 / (1.0 + a0 / (math.pi * ar)) * math.radians(5.0), delta=2e-4)
        self.assertAlmostEqual(sol["e"], 1.0, delta=1e-3)                      # elliptic loading: e = 1
        cl = [sol["cl_of"](e) for e in (0.0, 0.3, 0.6, 0.9)]
        self.assertTrue(np.allclose(cl, cl[0], atol=2e-3))                     # constant section C_l along an elliptic wing

    def test_rectangular_wing_prandtl_values(self):
        # Glauert correction factors for a rectangular wing of AR = 6 (Anderson Fig. 5.20): tau ~ 0.15-0.17 (lift slope), delta ~ 0.05 (efficiency)
        b, c, a0 = 6.0, 1.0, 2.0 * math.pi
        sol = m.llt_solve(b, lambda e: c, lambda e: a0, lambda e: 0.0, lambda e: 0.0, 0.05)
        cla = sol["cl_total"] / 0.05
        tau = (a0 / cla - 1.0) * math.pi * 6.0 / a0 - 1.0
        self.assertTrue(0.13 < tau < 0.19)
        self.assertTrue(0.03 < 1.0 / sol["e"] - 1.0 < 0.07)

    def test_twist_does_not_change_slope_but_changes_cl0(self):
        ch = lambda e: 1.2 - 0.3 * e
        a = lambda e: 2 * math.pi
        z = lambda e: 0.0
        s0 = m.lift_curve_slope(9.0, ch, a, z, z)
        s1 = m.lift_curve_slope(9.0, ch, a, z, lambda e: -math.radians(3.0) * e)
        self.assertAlmostEqual(s0, s1, places=6)
        self.assertLess(m.llt_solve(9.0, ch, a, z, lambda e: -math.radians(3.0) * e, 0.0)["cl_total"], 0.0)

    def test_alpha_zl_naca4(self):
        self.assertAlmostEqual(m.alpha_zl_naca4_deg("2412"), -2.08, delta=0.03)      # thin-airfoil value for 2412 (tables: -2.0)
        self.assertAlmostEqual(m.alpha_zl_naca4_deg("0012"), 0.0, places=9)
        self.assertAlmostEqual(m.alpha_zl_naca4_deg("4412"), 2.0 * m.alpha_zl_naca4_deg("2412"), delta=0.02)

    def test_pitch_up_limits_are_inverses(self):
        lam, sweep = 0.5, 30.0
        ar_lim = m.pitch_up_limits(8.0, lam, sweep)["ar_limit"]
        self.assertAlmostEqual(m.pitch_up_limits(ar_lim, lam, sweep)["sweep_limit_deg"], sweep, delta=0.01)    # 1/0.04267 = 23.4357 vs the printed 23.436
        self.assertFalse(m.pitch_up_limits(ar_lim * 1.01, lam, sweep)["ar_ok"])


class CriteriaTests(unittest.TestCase):
    ST = np.linspace(0.0, 1.0, 11)

    def first(self, cl, eta):
        return {"stations": self.ST.tolist(), "cl": cl, "clmax": [1.5] * 11, "eta": eta}

    def test_benign_distribution(self):
        cl = [1.50, 1.45, 1.40, 1.35, 1.30, 1.25, 1.20, 1.0, 0.7, 0.4, 0.0]
        out = m.benign_stall_checks(self.first(cl, 0.0))
        self.assertTrue(out["benign"])
        self.assertTrue(out["cl_decreases_70_to_100pct"])
        self.assertTrue(out["torenbeek_margin_ok"])

    def test_tip_stall_is_not_benign(self):
        cl = [1.0, 1.1, 1.2, 1.3, 1.4, 1.45, 1.47, 1.5, 1.5, 1.5, 1.5]
        out = m.benign_stall_checks(self.first(cl, 0.9))
        self.assertFalse(out["benign"])
        self.assertFalse(out["first_stall_inboard_of_70pct"])


class ProjectTests(unittest.TestCase):
    def build(self, tmp, mutate=None):
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        if mutate:
            mutate(data)
        src = Path(tmp) / "in.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        path = Path(tmp) / "p.json"
        main(["project-init", "--project", str(path), "--name", "s", "--from-inputs", str(src)])
        for mod in ("m09b", "m19"):
            main([mod, "--project", str(path)])
        return path

    def test_chain_trend_and_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.build(tmp)
            data = prj.load(path)
            r = data["outputs"]["m19"]["result"]
            self.assertEqual(sorted(data["outputs"]["m19"]["run"]["depends_on"]), ["m09b"])
            self.assertEqual(prj.stale(data), [])
            self.assertAlmostEqual(r["lift_curve"]["cl_alpha_wing_per_rad"], r["lift_curve"]["cl_alpha_m09b_per_rad"], delta=0.05 * r["lift_curve"]["cl_alpha_m09b_per_rad"])
            study = r["washout_study"]
            etas = [s["first_stall"]["eta"] for s in study]
            alphas = [s["alpha_stall_deg"] for s in study]
            self.assertTrue(all(b <= a + 1e-9 for a, b in zip(etas, etas[1:])))      # more washout: the first stall moves inboard
            self.assertTrue(all(b >= a for a, b in zip(alphas, alphas[1:])))          # and the wing stalls later (less tip loading)
            self.assertTrue(r["baseline"]["checks"]["tip_unstalled_at_wing_stall"])
            data["outputs"]["m09b"]["result"]["planform"]["span_m"] += 0.1
            self.assertIn("m19", prj.stale(data))
            out = Path(tmp) / "m19.json"
            main(["export", "--project", str(path), "--module", "m19", "--out", str(out)])
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["module"], "m19")

    def test_unknown_airfoil_needs_alpha_zl(self):
        def mutate(d):
            d["m09b"]["airfoils"]["root"]["id"] = "e387"
            d["m09b"]["airfoils"]["tip"]["id"] = "e387"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                self.build(tmp, mutate)


@unittest.skipUnless(FLOW5_OUT.is_dir(), "flow5 7.55 evidence not present")
class Flow5ContrastTests(unittest.TestCase):
    def test_lift_slope_against_real_flow5_vlm2(self):
        """Wing-tail model of examples/flow5-c162-like.json, V = 55.6 m/s, alpha -4 to 12: flow5 VLM2 CL(alpha) against the lifting line of the wing
        alone (NACA 2412, root 1.25 m, tip 1.11 m, b = 9.44 m, washout 1.5 deg). Not tuned: the tail adds lift slope, so a modest excess is expected."""
        from aerosuite.flow5_results import collect
        rows = collect(FLOW5_OUT)["polars"][0]["rows"]
        al = np.array([r["alpha_deg"] for r in rows])
        cl = np.array([r["CL"] for r in rows])
        sel = (al >= -4) & (al <= 8)
        flow5_slope = np.polyfit(np.radians(al[sel]), cl[sel], 1)[0]
        ch = lambda e: 1.25 + (1.11 - 1.25) * e
        azl = math.radians(m.alpha_zl_naca4_deg("2412"))
        llt = m.lift_curve_slope(9.44, ch, lambda e: 2.0 * math.pi, lambda e: azl, lambda e: -math.radians(1.5) * e)
        self.assertAlmostEqual(flow5_slope, 5.105, delta=0.01)                   # recorded value of the real run
        self.assertLess(abs(llt - flow5_slope) / flow5_slope, 0.08)


if __name__ == "__main__":
    unittest.main()
