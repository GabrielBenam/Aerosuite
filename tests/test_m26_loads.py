"""M26 tests: equilibrium, independent recomputation of the bending moment, CSV/JSON export, CAD transformation and the optional flow5 contrast
(real flow5 7.55 operating point from evidence/)."""
import csv
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from aerosuite import m26_loads as m26
from aerosuite import project as prj
from aerosuite.__main__ import main

ROOT = Path(__file__).parents[1]
FULL = ROOT / "examples" / "projects" / "c162-full-loop.json"
OPP = ROOT / "evidence" / "flow5-7.55-win" / "m19-distribution" / "vlm2-ala-sola" / "output" / "AeroSuite_wing_only" / "AeroSuite wing only" \
    / "FIXEDSPEEDPOLAR-VLM2-55_6mps" / " 6_00°_55_60m_s.csv"
CHAIN = ["m01", "m02", "m06", "m04", "m09b", "m11", "m18c", "m19", "m08", "m10", "m12", "m13", "m15", "m20", "m25"]


def build(tmp, m26_inputs=None):
    data = json.loads(FULL.read_text(encoding="utf-8"))
    data["m25"] = {"category": "normal", "common": {"cl_min": 1.0}}
    data["m26"] = {"out_dir": str(Path(tmp) / "loads"), **(m26_inputs or {})}
    src = Path(tmp) / "in.json"
    src.write_text(json.dumps(data), encoding="utf-8")
    path = Path(tmp) / "p.json"
    main(["project-init", "--project", str(path), "--name", "c162", "--from-inputs", str(src)])
    for m in CHAIN:
        main([m, "--project", str(path)])
    return path


class Loads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = build(cls.tmp.name)
        main(["m26", "--project", str(cls.path)])
        cls.proj = prj.load(cls.path)
        cls.res = cls.proj["outputs"]["m26"]["result"]
        cls.conds = cls.res["cases"][0]["conditions"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_uses_mtow_and_all_corners(self):
        self.assertAlmostEqual(self.res["cases"][0]["mass_kg"], 598.74, places=2)
        self.assertEqual([c["name"] for c in self.conds], ["A", "C+", "D+", "G", "C-", "D-"])

    def test_total_lift_is_n_w(self):
        for c in self.conds:
            self.assertAlmostEqual(c["totals"]["lift_n"], c["n_limit"] * c["mass_kg"] * 9.80665, places=6)
            self.assertAlmostEqual(c["totals"]["lift_wing_n"] + c["totals"]["tail_load_n"], c["totals"]["lift_n"], places=6)

    def test_equilibrium_from_stations(self):
        for c in self.conds:
            e = c["equilibrium"]
            self.assertLess(abs(e["force_residual_relative"]), 1e-3, c["name"])        # sum of station forces = lift
            self.assertLess(abs(e["pitch_residual_relative_to_nWc"]), 1e-3, c["name"])

    def test_pitch_balance_closed_form(self):
        w = self.res["wing"]
        t = self.res["tail"]
        for c in self.conds:
            cg = c["cg_x_m"]
            moment = c["totals"]["lift_wing_n"] * (cg - w["x_ac_wing_m"]) + c["totals"]["pitching_moment_wing_ac_nm"] + c["totals"]["tail_load_n"] * (cg - t["x_ac_m"])
            self.assertAlmostEqual(moment / (c["totals"]["lift_n"] * w["cmgc_m"]), 0.0, places=9)

    def test_bending_matches_independent_integral(self):
        for c in self.conds:
            st = c["span_distribution"]["stations"]
            m_root = sum(r["force_n"] * r["y_m"] for r in st)                        # moment of the station forces about the root
            self.assertAlmostEqual(st[0]["bending_in_nm"] / m_root, 1.0, delta=0.01, msg=c["name"])
            hb = self.proj["outputs"]["m09b"]["result"]["planform"]["span_m"] / 2
            ratio = st[0]["bending_in_nm"] / (c["span_distribution"]["half_wing_force_n"] * hb)
            if abs(c["totals"]["cl_wing"]) > 1.0:      # at low C_L the washout moves the load inboard/outboard: far from elliptic
                self.assertTrue(0.38 < abs(ratio) < 0.48, (c["name"], ratio))         # elliptic: 4/(3 pi) = 0.424

    def test_stall_corner_a_reaches_clmax(self):
        a = next(c for c in self.conds if c["name"] == "A")
        self.assertTrue(0.95 < a["span_distribution"]["max_cl_over_clmax"] < 1.1)
        d = next(c for c in self.conds if c["name"] == "D+")
        self.assertLess(d["span_distribution"]["max_cl_over_clmax"], 0.6)

    def test_thin_airfoil_cm(self):
        self.assertAlmostEqual(m26.cm_ac_naca4("0012"), 0.0, places=9)
        self.assertAlmostEqual(m26.cm_ac_naca4("2412"), -0.053, delta=0.002)

    def test_export_files_and_cad_axes(self):
        out = Path(self.res["export"]["out_dir"])
        man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        for name, sha in man["files_sha256"].items():
            self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), sha)
        with (out / "stations.csv").open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 6 * 2 * 21)
        r = next(x for x in rows if x["side"] == "starboard")
        self.assertAlmostEqual(float(r["cad_x_mm"]), float(r["x_c4_m"]) * 1000, places=6)
        self.assertAlmostEqual(float(r["cad_y_mm"]), float(r["z_m"]) * 1000, places=6)
        self.assertAlmostEqual(float(r["cad_z_mm"]), -float(r["y_m"]) * 1000, places=6)
        p = next(x for x in rows if x["side"] == "port")
        self.assertGreater(float(p["cad_z_mm"]), 0)
        total = sum(float(x["force_up_n"]) for x in rows if x["condition"] == "A")
        a = next(c for c in self.conds if c["name"] == "A")
        self.assertAlmostEqual(total / a["totals"]["lift_wing_n"], 1.0, delta=1e-3)

    def test_stale_when_m25_changes(self):
        proj = prj.load(self.path)
        self.assertNotIn("m26", prj.stale(proj))
        proj["inputs"]["m25"]["common"]["cl_min"] = 0.9
        main_ = proj
        self.assertIn("m25", prj.stale(main_))


@unittest.skipUnless(OPP.is_file(), "flow5 operating-point evidence not present")
class Flow5Contrast(unittest.TestCase):
    def test_matching_cl_is_used_and_mismatch_rejected(self):
        ok = m26.flow5_compare(OPP, [], [], 0.6848, 0.03)
        self.assertTrue(ok["used"])
        self.assertEqual(ok["rows"], len(ok["stations"]))
        bad = m26.flow5_compare(OPP, [], [], 1.2, 0.03)
        self.assertFalse(bad["used"])
        self.assertIn("no coincide", bad["reason"])


if __name__ == "__main__":
    unittest.main()
