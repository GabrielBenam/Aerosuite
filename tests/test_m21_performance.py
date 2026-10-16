"""M21 tests: Gudmundsson Example 21-6 (range profiles 737 nm and 768 nm, optimum 950 nm) and Example 21-2 (c_kW = 0.304 kg/(kW h)),
an independent numerical integration of the Breguet integral, speed/ceiling consistency with the parabolic polar (closed forms) and the
payload-range diagram of the project chain. No external solver is involved (the drag input comes from M20/M09b or from the user)."""
import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite import m21_performance as m

EXAMPLE = Path(__file__).parents[1] / "examples" / "projects" / "c172-like-performance-inputs.json"
LBF, FT, SLUG_FT3, FT2 = 4.4482216, 0.3048, 515.378819, 0.3048 ** 2


class Example216Tests(unittest.TestCase):
    # light airplane: S = 145 ft2, k = 0.04207, CDmin = 0.025, c_hp = 0.60 lbf/(BHP h), eta_p = 0.85, 10 000 ft (rho = 0.001756 slug/ft3), 150 KTAS, 3200 -> 2800 lbf
    S, K, CD, ETA = 145.0 * FT2, 0.04207, 0.025, 0.85
    RHO, V = 0.001756 * SLUG_FT3, 150.0 * m.KT
    C_P = 0.60 * 0.45359237 / 0.74569987                                     # kg/(kW h): 0.60 lbf/(BHP h) as mass flow
    WI, WF = 3200.0 * LBF, 2800.0 * LBF

    def test_example_21_2_specific_fuel_consumption(self):
        c = 12.5 * m.AVGAS_KG_PER_GAL / 111.9                              # kg/(kW h): 12.5 gal/h at 150 BHP = 111.9 kW
        self.assertAlmostEqual(c, 0.304, delta=0.001)

    def test_profile_1_constant_speed_altitude(self):
        r = m.range_const_v_h(self.WI, self.WF, self.V, self.RHO, self.S, self.CD, self.K, self.ETA, self.C_P)
        self.assertAlmostEqual(r / m.NM, 737.0, delta=737.0 * 0.01)              # printed 737 nm

    def test_profile_3_constant_attitude(self):
        cl = 2.0 * self.WI / (self.RHO * self.V ** 2 * self.S)
        self.assertAlmostEqual(cl, 0.3921, delta=5e-4)                          # Example 21-3
        ld = cl / (self.CD + self.K * cl ** 2)
        r = m.range_const_attitude(self.WI, self.WF, ld, self.ETA, self.C_P)
        self.assertAlmostEqual(r / m.NM, 768.0, delta=768.0 * 0.01)             # printed 768 nm

    def test_optimum_range_uses_ld_max_of_the_given_polar(self):
        # printed 950 nm; the intermediate LD_max = 19.0 shown in the book comes from other k, CDmin values: the printed result needs 15.42
        ld = 0.5 / math.sqrt(self.CD * self.K)
        self.assertAlmostEqual(ld, 15.42, delta=0.01)
        r = m.range_const_attitude(self.WI, self.WF, ld, self.ETA, self.C_P)
        self.assertAlmostEqual(r / m.NM, 950.0, delta=950.0 * 0.01)

    def test_breguet_integral_matches_numerical_integration(self):
        """R = int V dt with dW/dt = -c_w P, P = D V/eta : integrate dW numerically with the drag of the polar."""
        w = np.linspace(self.WF, self.WI, 20001)
        q = 0.5 * self.RHO * self.V ** 2
        d = q * self.S * self.CD + self.K * w ** 2 / (q * self.S)
        integrand = self.ETA / (m.c_weight_per_joule(self.C_P) * d)
        numeric = float(np.sum(0.5 * (integrand[1:] + integrand[:-1]) * np.diff(w)))
        analytic = m.range_const_v_h(self.WI, self.WF, self.V, self.RHO, self.S, self.CD, self.K, self.ETA, self.C_P)
        self.assertAlmostEqual(numeric / analytic, 1.0, places=6)

    def test_endurance_is_range_over_speed(self):
        r = m.range_const_v_h(self.WI, self.WF, self.V, self.RHO, self.S, self.CD, self.K, self.ETA, self.C_P)
        self.assertAlmostEqual(m.endurance_const_v_h(self.WI, self.WF, self.V, self.RHO, self.S, self.CD, self.K, self.ETA, self.C_P), r / self.V)


class ClosedFormTests(unittest.TestCase):
    W, S, CD, K, PSL, ETA = 11000.0, 16.0, 0.027, 0.05, 119000.0, 0.8

    def test_speeds_from_the_parabolic_polar(self):
        rho = 1.225
        v = m.v_max_ld(self.W, rho, self.S, self.CD, self.K)
        cl = 2 * self.W / (rho * v * v * self.S)
        self.assertAlmostEqual(cl, math.sqrt(self.CD / self.K))
        vp = m.v_min_power(self.W, rho, self.S, self.CD, self.K)
        self.assertAlmostEqual(2 * self.W / (rho * vp * vp * self.S), math.sqrt(3 * self.CD / self.K))
        # P_r minimum at the minimum-power speed (numerical neighbors)
        pr = lambda x: m.power_required(x, self.W, rho, self.S, self.CD, self.K)
        self.assertLess(pr(vp), pr(vp * 0.97))
        self.assertLess(pr(vp), pr(vp * 1.03))

    def test_vmax_satisfies_power_balance_and_ceilings_are_consistent(self):
        vmax = m.max_speed(self.W, 0.0, self.S, self.CD, self.K, self.PSL, self.ETA)
        pa = m.power_available(self.PSL, self.ETA, 0.0)
        self.assertAlmostEqual(m.power_required(vmax, self.W, 1.225, self.S, self.CD, self.K), pa, delta=1e-2)
        sc = m.ceiling(self.W, self.S, self.CD, self.K, self.PSL, self.ETA, m.SERVICE_CEILING_RC)
        ac = m.ceiling(self.W, self.S, self.CD, self.K, self.PSL, self.ETA, 0.0)
        self.assertLess(sc, ac)
        self.assertAlmostEqual(m.best_climb(self.W, sc, self.S, self.CD, self.K, self.PSL, self.ETA)["rc_mps"], 0.508, delta=1e-4)
        self.assertAlmostEqual(m.best_climb(self.W, ac, self.S, self.CD, self.K, self.PSL, self.ETA)["rc_mps"], 0.0, delta=1e-4)

    def test_best_climb_is_maximum_of_excess_power(self):
        bc = m.best_climb(self.W, 0.0, self.S, self.CD, self.K, self.PSL, self.ETA)
        f = lambda v: (m.power_available(self.PSL, self.ETA, 0.0) - m.power_required(v, self.W, 1.225, self.S, self.CD, self.K)) / self.W
        self.assertAlmostEqual(bc["rc_mps"], f(bc["v_mps"]), places=7)
        self.assertGreaterEqual(bc["rc_mps"], f(bc["v_mps"] * 1.05))
        self.assertGreaterEqual(bc["rc_mps"], f(bc["v_mps"] * 0.95))

    def test_gagg_ferrar(self):
        self.assertAlmostEqual(m.gagg_ferrar(1.0), 1.0)
        self.assertLess(m.gagg_ferrar(0.7), 0.7)                               # power falls faster than density

    def test_no_level_flight_returns_none(self):
        self.assertIsNone(m.max_speed(self.W * 4, 0.0, self.S, self.CD, self.K, 5000.0, self.ETA))


class ProjectTests(unittest.TestCase):
    def build(self, tmp, mutate=None):
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        if mutate:
            mutate(data)
        src = Path(tmp) / "in.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        path = Path(tmp) / "p.json"
        main(["project-init", "--project", str(path), "--name", "p", "--from-inputs", str(src)])
        for mod in ("m09b", "m08", "m20", "m21"):
            main([mod, "--project", str(path)])
        return path

    def test_chain_payload_range_and_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.build(tmp)
            data = prj.load(path)
            r = data["outputs"]["m21"]["result"]
            self.assertEqual(sorted(data["outputs"]["m21"]["run"]["depends_on"]), ["m09b", "m20"])
            self.assertEqual(prj.stale(data), [])
            a, b, c = r["payload_range"]
            self.assertLess(a["range_const_v_h_km"], b["range_const_v_h_km"])
            self.assertLess(b["range_const_v_h_km"], c["range_const_v_h_km"])
            self.assertLessEqual(b["tow_kg"], 1157.0 + 1e-6)
            self.assertAlmostEqual(a["tow_kg"], 1157.0, delta=1e-6)               # maximum payload, fuel up to MTOW
            self.assertTrue(r["cruise_condition"]["sustainable"])
            self.assertGreater(r["ceilings_at_mtow"]["service_m"], 3000.0)
            self.assertGreater(r["takeoff"]["ground_run_m"], 0.0)
            self.assertGreater(r["landing"]["total_over_obstacle_m"], r["landing"]["ground_roll_m"])
            # best-range attitude profile beats the constant speed profile at the same fuel
            self.assertGreater(c["range_at_ld_max_attitude_km"], c["range_const_v_h_km"])
            data["outputs"]["m20"]["result"]["buildup"]["cd_min"] += 0.001
            self.assertIn("m21", prj.stale(data))
            out = Path(tmp) / "m21.json"
            main(["export", "--project", str(path), "--module", "m21", "--out", str(out)])
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["module"], "m21")

    def test_cdmin_input_overrides_m20(self):
        def mutate(d):
            d["m21"]["cdmin"] = 0.04
        with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
            base = prj.load(self.build(t1))["outputs"]["m21"]["result"]["payload_range"][1]["range_const_v_h_km"]
            worse = prj.load(self.build(t2, mutate))["outputs"]["m21"]["result"]["payload_range"][1]["range_const_v_h_km"]
            self.assertLess(worse, base)

    def test_overweight_payload_is_reported(self):
        def mutate(d):
            d["m21"]["weights"]["max_payload_kg"] = 600.0
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                self.build(tmp, mutate)


if __name__ == "__main__":
    unittest.main()
