"""M25 tests. Reference: Gudmundsson Sec. 17.4.1 worked example (Table 17-6, W = 1320 lbf, S = 130 ft^2). The book prints CL_max = 1.45 in the table but
its V_S+ = 46.3 KEAS and the Step 10 quadratic use 1.4, so 1.4 is used (see DECISIONS D-55)."""
import json
import tempfile
import unittest
from pathlib import Path

from aerosuite import m25_envelope as m25
from aerosuite import project as prj
from aerosuite.__main__ import main

EXAMPLE = Path(__file__).parents[1] / "examples" / "projects" / "gud-example-17-4-vn.json"


def case(**kw):
    d = json.loads(EXAMPLE.read_text(encoding="utf-8"))["m25"]
    c = {**d["common"], **d["cases"][0], "category": "normal"}
    c.update(kw)
    return c


class BookExample(unittest.TestCase):
    def setUp(self):
        self.r = m25.build(case())

    def test_load_factors(self):
        ll = self.r["load_factors"]
        self.assertAlmostEqual(ll["n_plus_formula"], 4.22, places=2)
        self.assertEqual(ll["n_plus"], 3.8)
        self.assertAlmostEqual(ll["n_minus"], -1.52, places=6)
        self.assertAlmostEqual(ll["n_ultimate_plus"], 5.7, places=6)

    def test_speeds_keas(self):
        s = self.r["speeds"]
        self.assertAlmostEqual(s["v_s_pos_mps_keas"], 46.3, delta=0.1)
        self.assertAlmostEqual(s["v_s_neg_mps_keas"], 54.7, delta=0.1)
        self.assertAlmostEqual(s["v_c_min_mps_keas"], 105.2, delta=0.1)
        self.assertAlmostEqual(s["v_g_mps_keas"], 67.5, delta=0.1)
        self.assertAlmostEqual(s["v_a_mps_keas"], 90.3, delta=0.15)
        self.assertAlmostEqual(s["v_a_effective_mps_keas"], 94.6, delta=0.1)

    def test_gust(self):
        g = self.r["gust"]
        self.assertAlmostEqual(g["mu_g"], 14.77, delta=0.02)
        self.assertAlmostEqual(g["k_g"], 0.6476, delta=0.001)
        self.assertAlmostEqual(g["n_c_plus"], 4.60, delta=0.01)
        self.assertAlmostEqual(g["n_c_minus"], -2.60, delta=0.01)

    def test_polygon_closed_and_contains_corners(self):
        poly = self.r["polygon_v_eas_mps_n"]
        self.assertEqual(max(p[1] for p in poly), self.r["n_max_envelope"])
        self.assertAlmostEqual(self.r["n_max_envelope"], 4.60, delta=0.01)
        self.assertAlmostEqual(self.r["n_min_envelope"], -2.60, delta=0.01)
        c = {k["name"]: k for k in self.r["corner_points"]}
        self.assertAlmostEqual(c["D+"]["n_limit"], 3.8, places=6)
        self.assertAlmostEqual(c["D-"]["n_limit"], -1.52, delta=0.01)
        self.assertAlmostEqual(c["C+"]["n_ultimate"], 1.5 * c["C+"]["n_limit"], places=9)

    def test_independent_stall_gust_intersection(self):
        # quadratic of Step 10 solved independently: 2.362 V^2 - 170.0 V - 5057 = 0 (V in KEAS)
        a, b, c = 2.362, -170.0, -5057.0
        v = (-b + (b * b - 4 * a * c) ** 0.5) / (2 * a)
        self.assertAlmostEqual(self.r["speeds"]["v_a_effective_mps_keas"], v, delta=0.1)

    def test_aerobatic_and_commuter(self):
        ac = m25.build(case(category="aerobatic"))
        self.assertEqual(ac["load_factors"]["n_plus"], 6.0)
        self.assertAlmostEqual(ac["load_factors"]["n_minus"], -3.0)
        cm = m25.build(case(category="commuter"))
        self.assertIn("v_b_mps", cm["gust"])
        self.assertGreater(cm["gust"]["v_b_mps"], 0)

    def test_gust_alleviation_altitude(self):
        hi = m25.gust_velocities_mps(50000 * m25.FT, "normal")
        self.assertAlmostEqual(hi["u_c_mps"] / m25.FT, 25.0, places=6)
        self.assertAlmostEqual(hi["u_d_mps"] / m25.FT, 12.5, places=6)


class Cli(unittest.TestCase):
    def test_m25_export_and_stale(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "p.json"
            main(["project-init", "--project", str(p), "--name", "vn", "--from-inputs", str(EXAMPLE)])
            main(["m25", "--project", str(p)])
            out = Path(t) / "e.json"
            main(["export", "--module", "m25", "--project", str(p), "--out", str(out)])
            self.assertFalse(json.loads(out.read_text(encoding="utf-8"))["stale"])
            data = prj.load(p)
            data["inputs"]["m25"]["cases"][0]["mass_kg"] = 550.0
            prj.save(data, p)
            self.assertIn("m25", prj.stale(prj.load(p)))

    def test_missing_inputs_message(self):
        with self.assertRaises(SystemExit):
            m25.evaluate({"inputs": {"m25": {"category": "normal"}}, "outputs": {}})


if __name__ == "__main__":
    unittest.main()
