"""M10 tests. There is no solved OML example in the books: the checks are geometric invariants recomputed by independent
numerical integration (GUD Eqs. 9-1, 9-5, 9-6, 11-5, 11-6) and construction rules (SOB Eq. 2.16, Eq. 4.1)."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite import m10_geometry as g

EXAMPLE = Path(__file__).parents[1] / "examples" / "projects" / "oml-c172-like.json"


def build(tmp, mutate=None, run_all=True):
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    if mutate:
        mutate(data)
    src = Path(tmp) / "in.json"
    src.write_text(json.dumps(data), encoding="utf-8")
    path = Path(tmp) / "p.json"
    main(["project-init", "--project", str(path), "--name", "oml", "--from-inputs", str(src)])
    if run_all:
        for m in ("m09b", "m08", "m10"):
            main([m, "--project", str(path)])
    return path


class ConstructionTests(unittest.TestCase):
    def test_generalized_circle_eq_2_16(self):
        pts = g.cross_section(0.5, 0.5, 101)
        for z, y in pts:
            self.assertAlmostEqual((z - 0.5) ** 2 + y ** 2, 0.25, places=12)       # unit-diameter circle
        flat = g.cross_section(0.7, 0.7, 101)
        self.assertLess(max(y for _, y in flat), 0.5)                                # different N changes the lobe
        with self.assertRaises(ValueError):
            g.cross_section(0.0, 0.5)

    def test_loft_is_linear_and_symmetric_geometry(self):
        s = g.lifting_surface("w", "wing", (0.0, 0.0, 0.5), 10.0, 1.4, 0.9, 10.0, 3.0, -2.0, 1.0, "naca2412", "naca2412", 5)
        self.assertEqual(len(s["sections"]), 5)
        mid = s["sections"][2]
        root, tip = s["sections"][0], s["sections"][-1]
        for k in ("x_le_m", "y_m", "z_le_m", "chord_m", "twist_deg"):
            self.assertAlmostEqual(mid[k], (root[k] + tip[k]) / 2.0, places=12)       # Eq. 4.1 with u = 1/2
        self.assertAlmostEqual(tip["y_m"], 5.0)
        self.assertAlmostEqual(tip["z_le_m"], 0.5 + 5.0 * math.tan(math.radians(3.0)))
        self.assertAlmostEqual(tip["x_le_m"], 5.0 * math.tan(math.radians(10.0)))
        self.assertAlmostEqual(root["twist_deg"], 1.0)
        self.assertAlmostEqual(tip["twist_deg"], -1.0)                                  # incidence 1 + washout -2
        self.assertAlmostEqual(s["planform_area_m2"], (1.4 + 0.9) / 2 * 10.0)

    def test_contour_chord_and_twist_sign(self):
        coords = [(1.0, 0.0), (0.5, 0.06), (0.0, 0.0), (0.5, -0.06), (1.0, 0.0)]
        flat = g.section_contour(coords, 2.0, 1.0, 3.0, 0.2, 0.0)
        self.assertAlmostEqual(flat[0][0], 3.0)                                         # TE at x_le + chord
        self.assertAlmostEqual(flat[2][0], 1.0)                                         # LE at x_le
        self.assertTrue(all(abs(p[1] - 3.0) < 1e-12 for p in flat))
        up = g.section_contour(coords, 2.0, 1.0, 3.0, 0.2, 5.0)                         # nose-up: trailing edge goes down
        self.assertLess(up[0][2], flat[0][2])
        self.assertAlmostEqual(math.dist((up[0][0], up[0][2]), (up[2][0], up[2][2])), 2.0, places=12)   # chord preserved


class AssemblyTests(unittest.TestCase):
    def test_invariants_from_independent_integration(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build(tmp)
            data = prj.load(path)
            r = data["outputs"]["m10"]["result"]
            self.assertTrue(r["valid"], [c for c in r["checks"] if not c["ok"]])
            wing = next(c for c in r["components"] if c["type"] == "wing")
            ht = next(c for c in r["components"] if c["type"] == "horizontal_tail")
            vt = next(c for c in r["components"] if c["type"] == "vertical_tail")
            # Eqs. 9-2, 9-5, 9-6 by midpoint quadrature over the lofted chord distribution
            n, half = 4000, wing["semi_span_m"]
            c0, c1 = wing["sections"][0]["chord_m"], wing["sections"][-1]["chord_m"]
            ys = [(i + 0.5) * half / n for i in range(n)]
            cs = [c0 + (c1 - c0) * y / half for y in ys]
            dy = half / n
            area = 2.0 * sum(cs) * dy
            cmgc = 2.0 / area * sum(c * c for c in cs) * dy                              # Eq. 9-5
            ymgc = 2.0 / area * sum(y * c for y, c in zip(ys, cs)) * dy                  # Eq. 9-6
            self.assertAlmostEqual(area, r["reference"]["s_ref_m2"], delta=2e-5)
            self.assertAlmostEqual(cmgc, r["reference"]["c_ref_m"], delta=2e-4)
            b = r["reference"]["b_ref_m"]
            self.assertAlmostEqual(ymgc, b / 6.0 * (1 + 2 * c1 / c0) / (1 + c1 / c0), delta=2e-4)
            # Tail arms and volume coefficients recovered from the assembled coordinates (Eqs. 11-5, 11-6)
            m08 = data["outputs"]["m08"]["result"]
            self.assertAlmostEqual(r["reference"]["l_ht_check_m"], m08["horizontal_tail"]["arm_m"], places=9)
            self.assertAlmostEqual(r["reference"]["l_vt_check_m"], m08["vertical_tail"]["arm_m"], places=9)
            self.assertAlmostEqual(r["reference"]["volume_coefficients_check"]["vht"], 0.761, delta=1e-9)
            self.assertAlmostEqual(r["reference"]["volume_coefficients_check"]["vvt"], 0.0419, delta=1e-9)
            self.assertAlmostEqual(ht["planform_area_m2"], m08["horizontal_tail"]["area_m2"], delta=1e-9)
            self.assertAlmostEqual(vt["sections"][-1]["z_le_m"] - vt["sections"][0]["z_le_m"], m08["vertical_tail"]["span_m"])
            self.assertEqual(r["schema"], "aerosuite-oml/1")
            self.assertEqual(r["units"], "SI")
            self.assertEqual(r["axes"]["x"], "aft")
            # assumptions recorded, not hidden
            keys = {a["key"] for a in data["assumptions"] if a["module"] == "m10"}
            self.assertEqual(keys, {"tail_airfoils", "wing_incidence_deg"})

    def test_robustness_checks_flag_bad_geometry(self):
        def mut(d):
            d["m10"]["wing_z_m"] = 2.0              # wing root above the fuselage (radius 0.61 m)
        with tempfile.TemporaryDirectory() as tmp:
            path = build(tmp, mut)
            r = prj.load(path)["outputs"]["m10"]["result"]
            self.assertFalse(r["valid"])
            bad = {c["name"] for c in r["checks"] if not c["ok"]}
            self.assertIn("wing_root_inside_fuselage_height", bad)

    def test_fuselage_profile_and_wetted_area(self):
        f = g.fuselage({"x_nose_m": -1.0, "nose_length_m": 1.0, "radius_m": 0.5, "tail_radius_m": 0.1}, 2.0, 5.0)
        xs = [s["x_m"] for s in f["stations"]]
        self.assertEqual(xs, sorted(xs))
        self.assertAlmostEqual(f["stations"][0]["radius_m"], 0.0)
        self.assertAlmostEqual(f["stations"][-1]["radius_m"], 0.1)
        # cylinder part (x 0 -> 2) lateral area 2 pi R L is contained in the estimate; tail frustum per Eq. 11-16 form
        self.assertGreater(f["wetted_area_estimate_m2"], 2 * math.pi * 0.5 * 2.0)
        with self.assertRaises(ValueError):
            g.fuselage({"x_nose_m": -1.0, "nose_length_m": 1.0, "radius_m": 0.5, "tail_radius_m": 0.6}, 2.0, 5.0)
        with self.assertRaises(ValueError):
            g.fuselage({"x_nose_m": -1.0, "nose_length_m": 1.0, "radius_m": 0.5, "tail_radius_m": 0.1}, 6.0, 5.0)

    def test_stale_chain_and_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build(tmp)
            data = prj.load(path)
            self.assertEqual(sorted(data["outputs"]["m10"]["run"]["depends_on"]), ["m08", "m09b"])
            self.assertEqual(prj.stale(data), [])
            out = Path(tmp) / "oml.json"
            main(["export", "--project", str(path), "--module", "m10", "--out", str(out)])
            exp = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(exp["result"]["schema"], "aerosuite-oml/1")
            self.assertFalse(exp["stale"])
            data["inputs"]["m09b"]["planform"]["taper_ratio"] = 0.6
            self.assertEqual(prj.stale(data), ["m09b"])

    def test_contours_for_cad(self):
        def mut(d):
            d["m10"]["contours"] = True
        with tempfile.TemporaryDirectory() as tmp:
            path = build(tmp, mut)
            r = prj.load(path)["outputs"]["m10"]["result"]
            root = r["contours"]["wing"][0]
            self.assertEqual(root["airfoil"], "naca2412")
            xs = [p[0] for p in root["points_m"]]
            chord = next(c for c in r["components"] if c["type"] == "wing")["sections"][0]["chord_m"]
            self.assertAlmostEqual(max(xs) - min(xs), chord, delta=chord * 0.01)       # twist 0 at the root (incidence 0)
            self.assertIn("vertical_tail", r["contours"])


if __name__ == "__main__":
    unittest.main()
