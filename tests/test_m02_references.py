"""M02 tests. The Table 6-1 statistics are the book's own published values (GUD PDF p.196)."""
import math
import unittest

import numpy as np

from aerosuite import project as prj
from aerosuite.m02_references import analyze, load_database, regression, run


class M02Tests(unittest.TestCase):
    def test_table_6_1_statistics_match_book(self):
        r = analyze(load_database("gud_table_6_1_lsa"))
        self.assertEqual(r["n"], 17)
        for key, mean, std in (("we_w0", 0.535, 0.060), ("wu_w0", 0.465, 0.060), ("wf_w0", 0.093, 0.034)):
            self.assertAlmostEqual(r[key]["mean"], mean, delta=0.0006, msg=key)   # book prints 3 decimals
            self.assertAlmostEqual(r[key]["std"], std, delta=0.0006, msg=key)
        self.assertEqual(r["regression_we_w0"]["status"], "degenerate")     # all W0 within 0.4 %

    def test_row_matches_book_c162(self):
        row = next(a for a in analyze(load_database("gud_table_6_1_lsa"))["aircraft"] if "C-162" in a["name"])
        self.assertAlmostEqual(row["we_w0"], 0.632, places=3)
        self.assertAlmostEqual(row["wf_w0"], 0.109, places=3)

    def test_regression_recovers_known_line(self):
        # FORMAT/ALGORITHM FIXTURE (not data): points on We/W0 = 1.4343 - 0.1402 ln W0 (kg form of GUD Eq. 6-18)
        w0 = np.array([300.0, 450.0, 600.0, 750.0, 900.0])
        fit = regression(w0, 1.4343 - 0.1402 * np.log(w0))
        self.assertAlmostEqual(fit["A_kg"], 1.4343, places=9)
        self.assertAlmostEqual(fit["B"], -0.1402, places=9)
        self.assertAlmostEqual(fit["r2"], 1.0, places=9)
        # lbf form: the book prints A = 1.5451 (lbf) next to 1.4343 (kg) for Eq. 6-18; shift is B*ln(0.45359237)
        self.assertAlmostEqual(fit["A_lbf"], 1.4343 - 0.1402 * math.log(0.45359237), places=9)
        self.assertAlmostEqual(fit["A_lbf"], 1.5451, delta=0.0005)

    def test_rejects_mixed_classes(self):
        db = {"name": "x", "class": "a", "propulsion": "piston", "aircraft": [
            {"name": "1", "we_lbf": 1, "w0_lbf": 2, "wf_lbf": 0.1, "class": "a"},
            {"name": "2", "we_lbf": 1, "w0_lbf": 2, "wf_lbf": 0.1, "class": "b"}]}
        with self.assertRaises(ValueError):
            analyze(db)

    def test_run_records_output(self):
        p = prj.new_project("t")
        p["inputs"]["m02"] = {"database": "gud_table_6_1_lsa"}
        run(p)
        self.assertIn("m02", p["outputs"])
        self.assertAlmostEqual(p["outputs"]["m02"]["result"]["suggested_for_m06"]["we_w0"], 0.535, delta=0.001)


if __name__ == "__main__":
    unittest.main()
