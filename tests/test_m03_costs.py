"""M03 tests against Gudmundsson Examples 2-1 to 2-5 (PDF p.85-97; Table 2-3 on PDF p.90)."""
import tempfile
import unittest
from pathlib import Path

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite.m03_costs import (LBF_PER_KG, development_cost, operating_cost, piston_engine_cost, qdf, unit_costs)

KG = 1.0 / LBF_PER_KG
VSC = {"gear": -17500.0, "avionics": 35000.0, "prop": 14000.0}


def book_dev():
    return development_cost(1100 * KG, 185, 1000, 4, f_comp=1.0, cpi_2012=1.10)


class M03Tests(unittest.TestCase):
    def test_workhours_example_2_1(self):
        h = book_dev()["workhours"]
        self.assertAlmostEqual(h["engineering"], 205670, delta=1)
        self.assertAlmostEqual(h["tooling"], 190300, delta=1)
        self.assertAlmostEqual(h["manufacturing"], 1366628, delta=1)
        self.assertAlmostEqual(book_dev()["engineers_average_5y"], 21, delta=0.5)

    def test_fixed_cost_example_2_2(self):
        f = book_dev()["fixed"]
        for key, value in (("engineering", 20813804), ("development_support", 1499633), ("flight_test", 1361666),
                           ("tooling", 12769130), ("total", 36444233)):
            self.assertAlmostEqual(f[key] / value, 1.0, delta=1e-6, msg=key)

    def test_variable_pieces_example_2_2(self):
        v = book_dev()["variable_total_production"]
        self.assertAlmostEqual(v["manufacturing"] / 79674412, 1.0, delta=1e-6)
        self.assertAlmostEqual(v["quality_control"] / 15536510, 1.0, delta=1e-6)
        self.assertAlmostEqual(v["materials"] / 21074485, 1.0, delta=1e-6)

    def test_engine_and_qdf_example_2_3(self):
        self.assertAlmostEqual(piston_engine_cost(1, 6, 310), 102526, delta=1)
        self.assertAlmostEqual(qdf(1000), 0.5998, places=4)

    def test_table_2_3_unit_costs_and_break_even(self):
        vsc = dict(VSC, engine=piston_engine_cost(1, 6, 310))
        no = unit_costs(book_dev(), 1000, vsc, use_qdf=False, target_price_usd=350000)
        yes = unit_costs(book_dev(), 1000, vsc, use_qdf=True, target_price_usd=350000)
        self.assertAlmostEqual(no["variable_per_unit"], 250311, delta=2)
        self.assertAlmostEqual(no["total_cost_per_unit"], 286755, delta=2)
        self.assertAlmostEqual(no["minimum_selling_price"], 339255, delta=2)
        self.assertEqual(round(no["break_even_units"]), 366)
        self.assertAlmostEqual(yes["variable_per_unit"], 196672, delta=2)
        self.assertAlmostEqual(yes["total_cost_per_unit"], 233117, delta=2)
        self.assertAlmostEqual(yes["minimum_selling_price"], 285617, delta=2)
        self.assertEqual(round(yes["break_even_units"]), 238)

    def test_operating_cost_example_2_5(self):
        r = operating_cost({"flight_hours_per_year": 300, "mechanic_rate_usd_h": 60, "ifr_radios": True,
                            "integral_tanks": True, "storage_usd_month": 250, "fuel_flow_gal_h": 16,
                            "fuel_price_usd_gal": 5, "aircraft_price_usd": 350000, "n_engines": 1,
                            "loan_apr": 0.09, "loan_years": 15})
        self.assertAlmostEqual(r["maintenance_ratio_fmf"], 0.35)
        self.assertAlmostEqual(r["maintenance"], 6300)
        self.assertAlmostEqual(r["insurance"], 5750)
        self.assertAlmostEqual(r["loan"], 42599, delta=1)
        self.assertAlmostEqual(r["total_per_year"], 83649, delta=1)

    def test_lsa_factors_reduce_cost(self):
        a = development_cost(300, 100, 500, 2)
        b = development_cost(300, 100, 500, 2, certification="lsa")
        self.assertLess(b["workhours"]["engineering"], a["workhours"]["engineering"])
        with self.assertRaises(ValueError):
            development_cost(300, 100, 500, 2, certification="part25")

    def test_cli_with_book_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.json"
            main(["project-init", "--project", str(path), "--name", "ex2", "--from-inputs",
                  str(Path(__file__).parents[1] / "examples" / "projects" / "gud-example-2-cost.json")])
            main(["m03", "--project", str(path)])
            data = prj.load(path)
            msp = data["outputs"]["m03"]["result"]["unit"]["with_qdf"]["minimum_selling_price"]
            self.assertAlmostEqual(msp, 285617, delta=5)
            self.assertEqual(prj.stale(data), [])
            r = data["outputs"]["m03"]["result"]
            self.assertEqual(r["anio_base"], 2012)
            self.assertIn("dólares de 2012", r["nota_costos"])
            self.assertIn("no están actualizados por inflación", r["nota_costos"])

    def test_project_status_repeats_cost_note(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.json"
            main(["project-init", "--project", str(path), "--name", "ex2", "--from-inputs",
                  str(Path(__file__).parents[1] / "examples" / "projects" / "gud-example-2-cost.json")])
            with contextlib.redirect_stdout(io.StringIO()):
                main(["m03", "--project", str(path)])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                main(["project-status", "--project", str(path)])
            self.assertIn("dólares de 2012", buf.getvalue().replace("\u00f3", "ó"))


if __name__ == "__main__":
    unittest.main()
