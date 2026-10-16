"""M18a tests: Gudmundsson Examples 13-2 and 13-3 (static reactions), an independent force/moment equilibrium check of the dynamic
reaction equations (Eqs. 13-17 and 13-20 as re-derived, D-37), geometry identities and the project chain."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite import m18a_gear as g

EXAMPLE = Path(__file__).parents[1] / "examples" / "projects" / "c172-like-gear-inputs.json"


class BookExampleTests(unittest.TestCase):
    def test_example_13_2_static_nose_reaction(self):
        r = g.static_loads_tricycle(1320.0, 3.5, 1.3)                       # lbf, ft (units cancel)
        self.assertAlmostEqual(r["nose"], 357.5, delta=0.05)
        self.assertAlmostEqual(r["main"], 962.5, delta=0.05)

    def test_example_13_3_tailwheel_share(self):
        # The solution printed in Example 13-3 gives the arms: R_T = 1320 (1.3)/(1.3 + 10) = 151.9 lbf (x_M = 1.3 ft, x_TW = 10 ft), so the
        # check is NOT circular (F5, C-2: the arm ratio is no longer solved from the result).
        r = g.static_loads_taildragger(1320.0, 1.3, 10.0)
        self.assertAlmostEqual(r["tail"], 151.9, delta=0.05)
        self.assertAlmostEqual(r["share_pct"], 11.5, delta=0.05)
        self.assertAlmostEqual(r["main"], 1168.0, delta=0.2)

    def test_example_13_3_dynamic_reaction_at_40_ktas(self):
        # Example 13-3 (b), V = 40 KTAS, delta_e = 0: T = 408 lbf (z_T = 1.2 ft), L_W = 834.7 lbf (x_W = 0.7 ft), L_HT = 97.6 lbf (l_HT = 12 ft),
        # M_W = -96.9 ft lbf, mu = 0.04, z_CG = 3.5 ft. Printed R_T = 167.5 lbf (the converted text lost the minus sign: the book says the
        # negative R_T means the tailwheel is already off the ground) and R_M = W - L_HT - L_W - R_T = 555.2 lbf. Arithmetic of Eq. 13-20
        # with the printed data (z_CG = 3.5 ft appears in the printed expression 1.3 - 0.04 (3.5)).
        r = g.dynamic_loads_taildragger(1320.0, 1.3, 10.0, 3.5, 0.04, thrust=408.0, z_t=1.2, lift_w=834.7, x_w=0.7, lift_ht=97.6, l_ht=12.0,
                                        m_w=-96.9)
        self.assertAlmostEqual(r["tail"], -167.5, delta=0.1)
        self.assertAlmostEqual(r["main"], 555.2, delta=0.1)


class EquilibriumTests(unittest.TestCase):
    A = dict(thrust=300.0, z_t=0.2, lift_w=2000.0, x_w=0.15, lift_ht=-150.0, l_ht=4.0, m_w=-400.0)

    def test_tricycle_dynamic_equilibrium(self):
        a, w, x_n, x_m, z, mu = self.A, 12000.0, 1.8, 0.5, 0.9, 0.04
        r = g.dynamic_loads_tricycle(w, x_n, x_m, z, mu, **a)
        self.assertAlmostEqual(r["nose"] + r["main"] + a["lift_w"] + a["lift_ht"] - w, 0.0, places=8)
        # independent moment sum about the CG (x forward, z up, nose-up positive M = x Fz - z Fx); friction acts aft at z = -z_CG
        fric = lambda rr: -mu * rr
        m = (x_n * r["nose"] + z * fric(r["nose"])) + (-x_m * r["main"] + z * fric(r["main"])) - a["x_w"] * a["lift_w"] \
            - a["l_ht"] * a["lift_ht"] - a["z_t"] * a["thrust"] + a["m_w"]
        self.assertAlmostEqual(m, 0.0, places=6)

    def test_taildragger_dynamic_equilibrium(self):
        a, w, x_m, x_t, z, mu = self.A, 12000.0, 0.5, 5.0, 0.9, 0.04
        r = g.dynamic_loads_taildragger(w, x_m, x_t, z, mu, **a)
        self.assertAlmostEqual(r["tail"] + r["main"] + a["lift_w"] + a["lift_ht"] - w, 0.0, places=8)
        fric = lambda rr: -mu * rr
        m = (x_m * r["main"] + z * fric(r["main"])) + (-x_t * r["tail"] + z * fric(r["tail"])) - a["x_w"] * a["lift_w"] \
            - a["l_ht"] * a["lift_ht"] - a["z_t"] * a["thrust"] + a["m_w"]
        self.assertAlmostEqual(m, 0.0, places=6)

    def test_static_limit_of_dynamic_equations(self):
        self.assertAlmostEqual(g.dynamic_loads_tricycle(1000.0, 2.0, 0.5, 1.0, 0.0)["nose"],
                               g.static_loads_tricycle(1000.0, 2.0, 0.5)["nose"])
        self.assertAlmostEqual(g.dynamic_loads_taildragger(1000.0, 0.5, 4.0, 1.0, 0.0)["tail"],
                               g.static_loads_taildragger(1000.0, 0.5, 4.0)["tail"])

    def test_rotation_speed_zero_crossing(self):
        self.assertAlmostEqual(g.rotation_speed(lambda v: 100.0 - 2.0 * v), 50.0, places=6)
        self.assertIsNone(g.rotation_speed(lambda v: 1.0))


class GeometryTests(unittest.TestCase):
    def test_turning_radius_and_dime_angle(self):
        wb, th = 1.75, 30.0
        self.assertAlmostEqual(g.turning_radius(wb, th)["radius"], wb / math.sin(math.radians(th)))
        a = g.min_nose_angle_turn_on_dime_deg(wb, 2.5)
        self.assertAlmostEqual(g.turning_radius(wb, a)["h"], 2.5 / 2.0)

    def test_overturn_geometry(self):
        d = g.lateral_distance((0.0, 0.0), (2.0, 1.0), (1.0, 0.0))
        self.assertAlmostEqual(d, 1.0 / math.hypot(2.0, 1.0))
        self.assertAlmostEqual(g.overturn_angle_deg(1.0, 1.0, True), 45.0)
        self.assertAlmostEqual(g.overturn_angle_deg(2.0, 1.0, True), math.degrees(math.atan(2.0)))
        self.assertAlmostEqual(g.overturn_angle_deg(2.0, 1.0, False), math.degrees(math.atan(0.5)))

    def test_brake_energy_with_unit_constant(self):
        w_lbf, v_kt = 2550.0, 50.0
        ke_ft_lbf = 0.5 * w_lbf / 32.174 * (1.6878 * v_kt) ** 2
        ke_j = g.brake_energy_per_brake(w_lbf * 4.4482216, v_kt * g.KT, 1)
        self.assertAlmostEqual(ke_j, ke_ft_lbf * 1.3558179, delta=ke_j * 2e-3)
        self.assertAlmostEqual(ke_ft_lbf / (w_lbf * v_kt ** 2), 0.04428, places=4)      # the book prints 0.0433 (D-37)

    def test_sink_rate_matches_book_approximation(self):
        s = g.sink_rate(15.0 * g.PSF)
        self.assertAlmostEqual(s["sink_rate_mps"], s["book_approx_mps"], delta=0.02)
        self.assertTrue(9.2 * g.IN <= s["drop_height_m"] <= 18.7 * g.IN)

    def test_footprint(self):
        f = g.tire_footprint(6000.0, 230000.0, 0.53, 0.225)
        self.assertAlmostEqual(f["a_m"], 0.85 * math.sqrt(0.265 ** 2 - 0.225 ** 2))
        self.assertAlmostEqual(math.pi * f["a_m"] * f["b_m"] / 4.0, 6000.0 / 230000.0)


class ProjectTests(unittest.TestCase):
    def build(self, tmp, mutate=None, mods=("m09b", "m08", "m10", "m12", "m13", "m18a")):
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        if mutate:
            mutate(data)
        src = Path(tmp) / "in.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        path = Path(tmp) / "p.json"
        main(["project-init", "--project", str(path), "--name", "g", "--from-inputs", str(src)])
        for mod in mods:
            main([mod, "--project", str(path)])
        return path

    def test_chain_stale_and_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.build(tmp)
            data = prj.load(path)
            r = data["outputs"]["m18a"]["result"]
            for c in r["static_loads"]["cases"]:
                self.assertAlmostEqual(c["nose"] + c["main"], c["weight_n"], places=6)
            self.assertEqual(sorted(data["outputs"]["m18a"]["run"]["depends_on"]), ["m13"])
            self.assertEqual(prj.stale(data), [])
            self.assertIn("overturn", r)
            data["outputs"]["m13"]["result"]["total_mass_kg"] += 1.0
            self.assertIn("m18a", prj.stale(data))
            out = Path(tmp) / "m18a.json"
            main(["export", "--project", str(path), "--module", "m18a", "--out", str(out)])
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["module"], "m18a")

    def test_taildragger_and_rotation(self):
        def mutate(d):
            m = d["m18a"]
            m.update(configuration="taildragger", x_main_m=0.25, x_tail_m=5.0)
            m.pop("x_nose_m")
            m["dynamic"] = {"density_kgm3": 1.225, "wing_area_m2": 16.17, "ht_area_m2": 3.0, "cl_w": 0.5, "cl_ht": -0.4,
                            "static_thrust_n": 2500.0, "eta_p": 0.7, "power_w": 119000.0, "x_w_m": 0.0, "l_ht_m": 4.5,
                            "c_m_cg": -0.05, "mgc_m": 1.44, "mu": 0.04}
        with tempfile.TemporaryDirectory() as tmp:
            r = prj.load(self.build(tmp, mutate))["outputs"]["m18a"]["result"]
            self.assertEqual(r["configuration"], "taildragger")
            self.assertIn("rotation", r)

    def test_missing_inputs_are_reported(self):
        def mutate(d):
            d["m18a"].pop("track_m")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                self.build(tmp, mutate)


if __name__ == "__main__":
    unittest.main()
