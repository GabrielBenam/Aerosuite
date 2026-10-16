"""M08 tests against Gudmundsson Examples 11-1 to 11-3 (Cessna 172, PDF 556-557, printed p.511-512)."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite import m08_tail as t

EXAMPLE = Path(__file__).parents[1] / "examples" / "projects" / "gud-example-11-tail.json"
S, B, C, R1, R2 = 174.0, 36.0, 4.83, 2.0, 0.5      # ft: the equations are length-homogeneous
V_HT, V_VT = 0.761, 0.0419


class BookExampleTests(unittest.TestCase):
    def test_method_1_example_11_1(self):
        l = t.tail_arm_ht(V_HT, S, C, R1, R2)
        self.assertAlmostEqual(l, 12.76, delta=0.01)                       # book 12.76 ft
        s_ht = t.surface_from_volume(V_HT, S, C, l)
        self.assertAlmostEqual(s_ht, 50.1, delta=0.1)                      # book 50.1 ft^2
        self.assertAlmostEqual(math.sqrt(3.0 * s_ht), 12.26, delta=0.02)   # Eq. 11-21 with AR 3.0
        swet = math.pi * (R1 + R2) * l + 2 * V_HT * S * C / l              # Eq. 11-14
        self.assertAlmostEqual(swet, 200.5, delta=0.2)                     # book 200.5 ft^2

    def test_method_2_example_11_2(self):
        l = t.tail_arm_vt(V_VT, S, B, R1, R2)
        self.assertAlmostEqual(l, 8.18, delta=0.01)                        # book 8.18 ft
        s_vt = t.surface_from_volume(V_VT, S, B, l)
        self.assertAlmostEqual(s_vt, 32.1, delta=0.1)                      # book 32.1 ft^2
        self.assertAlmostEqual(math.sqrt(1.35 * s_vt), 6.58, delta=0.02)   # book 6.58 ft

    def test_method_3_example_11_3(self):
        l = t.tail_arm_combined(V_HT, V_VT, S, C, B, R1, R2)
        self.assertAlmostEqual(l, 15.2, delta=0.05)                        # book 15.2 ft
        self.assertAlmostEqual(t.surface_from_volume(V_HT, S, C, l), 42.2, delta=0.2)   # book 42.2 ft^2
        self.assertAlmostEqual(t.surface_from_volume(V_VT, S, B, l), 17.3, delta=0.1)   # book 17.3 ft^2

    def test_table_11_4_values(self):
        self.assertEqual(t.TAIL_VOLUMES["ga_single_engine"], (0.70, 0.04))
        self.assertEqual(t.TAIL_VOLUMES["jet_transport"], (1.00, 0.09))
        self.assertEqual(len(t.TAIL_VOLUMES), 11)


class GeometryTests(unittest.TestCase):
    def test_trapezoid_book_limits(self):
        rect = t.trapezoid(10.0, 8.0, 1.0)
        self.assertAlmostEqual(rect["cmgc_m"], rect["average_chord_m"])    # lambda = 1: c_MGC = c
        self.assertAlmostEqual(rect["ymgc_m"], rect["span_m"] / 4.0)       # b/4
        tri = t.trapezoid(10.0, 8.0, 1e-9)
        self.assertAlmostEqual(tri["cmgc_m"], 2.0 / 3.0 * tri["root_chord_m"], places=6)   # (2/3) c_r
        self.assertAlmostEqual(tri["ymgc_m"], tri["span_m"] / 6.0, places=6)               # b/6
        tap = t.trapezoid(10.0, 8.0, 0.5)
        self.assertAlmostEqual(tap["span_m"] * (tap["root_chord_m"] + tap["tip_chord_m"]) / 2.0, 10.0)  # Eq. 9-7

    def test_quadratic_profile_boundary_conditions(self):
        for kw, slope_at in (({"theta1_deg": 5.0}, 0.0), ({"theta2_deg": -3.0}, 4.0)):
            a, b, c = t.quadratic_profile(0.6, 0.15, 4.0, **kw)
            self.assertAlmostEqual(c, 0.6)
            self.assertAlmostEqual(a * 16 + b * 4 + c, 0.15)
            theta = kw.get("theta1_deg", kw.get("theta2_deg"))
            self.assertAlmostEqual(2 * a * slope_at + b, math.tan(math.radians(theta)))
        with self.assertRaises(ValueError):
            t.quadratic_profile(0.6, 0.15, 4.0)

    def test_numeric_wetted_area_matches_frustum(self):
        # straight profile y = R1 + (R2 - R1) x / l  ->  Eq. 11-16: pi (R1 + R2) l (slant corrected by the segment length)
        l, r1, r2 = 4.0, 0.6, 0.15
        a, b, c = t.quadratic_profile(r1, r2, l, theta1_deg=math.degrees(math.atan((r2 - r1) / l)))
        self.assertAlmostEqual(a, 0.0, places=12)
        exact = math.pi * (r1 + r2) * math.hypot(l, r1 - r2)               # lateral area of a frustum
        self.assertAlmostEqual(t.aft_fuselage_wetted_area(a, b, c, l, 50), exact, places=9)

    def test_method_4_optimum_agrees_with_grid_search(self):
        # Algorithm check (no book value: Example 11-5 gives ~16 ft only from a spreadsheet figure, theta not stated)
        r1, r2 = 0.6, 0.15
        s, b, c = 16.1651, 10.9728, 1.47218

        def swet(l):
            a_, b_, c_ = t.quadratic_profile(r1, r2, l, theta2_deg=0.0)       # tadpole: horizontal at x = l_T
            return t.aft_fuselage_wetted_area(a_, b_, c_, l) + 2 * s * (V_HT * c + V_VT * b) / l
        l4, val, edge = t.tail_arm_arbitrary_fuselage(V_HT, V_VT, s, c, b, r1, r2, theta2_deg=0.0, search_m=(2.0, 9.0))
        grid = [2.0 + 0.01 * i for i in range(701)]
        best = min(grid, key=swet)
        self.assertFalse(edge)
        self.assertAlmostEqual(l4, best, delta=0.02)
        self.assertAlmostEqual(val, swet(best), delta=1e-3)
        self.assertLessEqual(val, min(swet(2.0), swet(9.0)))


class ProjectTests(unittest.TestCase):
    def init(self, tmp, mutate=None):
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        if mutate:
            mutate(data)
        src = Path(tmp) / "in.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        path = Path(tmp) / "p.json"
        main(["project-init", "--project", str(path), "--name", "c172", "--from-inputs", str(src)])
        return path

    def test_cli_example_11_3_and_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.init(tmp)
            main(["m08", "--project", str(path)])
            r = prj.load(path)["outputs"]["m08"]["result"]
            ft = 0.3048
            self.assertAlmostEqual(r["horizontal_tail"]["arm_m"] / ft, 15.2, delta=0.05)
            self.assertAlmostEqual(r["horizontal_tail"]["area_m2"] / ft ** 2, 42.2, delta=0.2)
            self.assertAlmostEqual(r["vertical_tail"]["area_m2"] / ft ** 2, 17.3, delta=0.1)
            out = Path(tmp) / "m08.json"
            main(["export", "--project", str(path), "--module", "m08", "--out", str(out)])
            exp = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(exp["units"], "SI")
            self.assertFalse(exp["stale"])
            self.assertAlmostEqual(exp["result"]["vertical_tail"]["span_m"], r["vertical_tail"]["span_m"])

    def test_volumes_from_table_class(self):
        def mut(d):
            d["m08"]["volumes"] = {"class": "ga_single_engine"}
        with tempfile.TemporaryDirectory() as tmp:
            path = self.init(tmp, mut)
            main(["m08", "--project", str(path)])
            r = prj.load(path)["outputs"]["m08"]["result"]
            self.assertEqual((r["volumes"]["vht"], r["volumes"]["vvt"]), (0.70, 0.04))

    def test_wing_from_m04_marks_stale(self):
        def mut(d):
            d["m04"] = json.loads((Path(__file__).parents[1] / "examples" / "projects" / "c162-inputs.json")
                                  .read_text(encoding="utf-8"))["m04"]
            d["m04"]["tow_from_m06"] = False
            d["m08"] = {"wing_from_m04": {"aspect_ratio": 8.0, "taper_ratio": 1.0}, "volumes": {"class": "ga_single_engine"},
                        "fuselage": {"r1_m": 0.5, "r2_m": 0.1}}
        with tempfile.TemporaryDirectory() as tmp:
            path = self.init(tmp, mut)
            main(["m04", "--project", str(path)])
            main(["m08", "--project", str(path)])
            data = prj.load(path)
            w = data["outputs"]["m08"]["result"]["wing"]
            self.assertAlmostEqual(w["area_m2"], 598.74 * 9.80665 / w["wing_loading_pa"])
            self.assertEqual(prj.stale(data), [])
            data["outputs"]["m04"]["result"]["best_sample"]["wingloading_pa"] += 1.0
            self.assertEqual(prj.stale(data), ["m08"])


if __name__ == "__main__":
    unittest.main()
