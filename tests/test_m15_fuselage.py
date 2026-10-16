"""M15 tests: Table 12-1 of Gudmundsson (validation sample, PDF 578), numeric integration of bodies of revolution as an
independent check of Eqs. 12-2 to 12-17, and the sizing logic."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite import m15_fuselage as f

EXAMPLE = Path(__file__).parents[1] / "examples" / "projects" / "c172-like-fuselage-inputs.json"


def revolution_area_volume(profile, x0, x1, n=40000):
    """Body of revolution r(x): S = 2 pi int r sqrt(1 + r'^2) dx (lateral, no bases), V = pi int r^2 dx (midpoint rule)."""
    h = (x1 - x0) / n
    s = v = 0.0
    for i in range(n):
        x = x0 + (i + 0.5) * h
        r = profile(x)
        dr = (profile(x + 1e-6) - profile(x - 1e-6)) / 2e-6 if 1e-6 < x - x0 < (x1 - x0) - 1e-6 else (profile(x + 1e-4) - profile(x)) / 1e-4
        s += 2.0 * math.pi * r * math.sqrt(1.0 + dr * dr) * h
        v += math.pi * r * r * h
    return s, v


class Table121Tests(unittest.TestCase):
    # D = 2, D1 = 2, D2 = 1, L = 3 (GUD Table 12-1)
    def test_elliptic_cylinder(self):
        r = f.elliptic_cylinder(2.0, 1.0, 3.0)
        self.assertAlmostEqual(r["h"], 0.1111, places=4)
        self.assertAlmostEqual(r["area"], 14.533, places=3)
        self.assertAlmostEqual(r["volume"], 4.712, places=3)

    def test_uniform_cylinder_paraboloid_cone(self):
        u, p, c = f.uniform_cylinder(2.0, 3.0), f.paraboloid(2.0, 3.0), f.cone(2.0, 3.0)
        self.assertAlmostEqual(u["area"], 18.850, places=3)
        self.assertAlmostEqual(u["volume"], 9.425, places=3)
        self.assertAlmostEqual(p["area"], 13.035, places=3)
        self.assertAlmostEqual(p["volume"], 4.712, places=3)
        self.assertAlmostEqual(c["area"], 9.935, places=3)
        self.assertAlmostEqual(c["volume"], 3.142, places=3)

    def test_frustum_book_value_and_erratum(self):
        # Table 12-1 prints S = 14.902 and V = 5.498. The volume matches; the area matches only with (D1 - D2)^2 inside the
        # square root of Eq. 12-10 (as printed). The exact lateral area uses ((D1 - D2)/2)^2: 14.332 (D-31).
        printed = f.frustum(2.0, 1.0, 3.0, as_printed=True)
        exact = f.frustum(2.0, 1.0, 3.0)
        self.assertAlmostEqual(printed["area"], 14.902, places=3)
        self.assertAlmostEqual(printed["volume"], 5.498, places=3)
        self.assertAlmostEqual(exact["volume"], 5.498, places=3)
        self.assertAlmostEqual(exact["area"], 14.332, places=3)
        s, v = revolution_area_volume(lambda x: 1.0 - x / 6.0, 0.0, 3.0, 4000)               # radius 1 -> 0.5 over L = 3
        self.assertAlmostEqual(exact["area"], s, delta=1e-4)                                   # independent integration
        self.assertAlmostEqual(exact["volume"], v, delta=1e-4)


class IndependentIntegrationTests(unittest.TestCase):
    def test_paraboloid_and_cone_by_integration(self):
        d, l = 2.0, 3.0
        s, v = revolution_area_volume(lambda x: d / 2.0 * math.sqrt(x / l), 0.0, l, 200000)    # y^2 = (D/2)^2 x / L
        p = f.paraboloid(d, l)
        self.assertAlmostEqual(p["volume"], v, delta=2e-4)
        self.assertAlmostEqual(p["area"], s, delta=2e-3)
        s, v = revolution_area_volume(lambda x: d / 2.0 * (1.0 - x / l), 0.0, l, 4000)
        c = f.cone(d, l)
        self.assertAlmostEqual(c["area"], s, delta=1e-4)
        self.assertAlmostEqual(c["volume"], v, delta=1e-4)

    def test_tubular_and_tadpole_totals(self):
        d, l1, l2, l3 = 2.0, 3.0, 5.0, 4.0
        t = f.tubular_fuselage(d, l1, l2, l3)
        self.assertAlmostEqual(t["volume"], math.pi * d * d * (l1 / 8.0 + l2 / 4.0 + l3 / 12.0))                  # Eq. 12-14
        self.assertAlmostEqual(t["area"], sum(p["area"] for p in t["parts"].values()))
        td = f.tadpole_fuselage(2.0, 1.0, 0.2, 3.0, 5.0, 4.0, 2.0)
        self.assertAlmostEqual(td["length"], 14.0)
        expected_v = math.pi * (4 * 3 / 8.0 + 4 * 5 / 4.0 + (4 + 2 + 1) * 4 / 12.0 + (1 + 0.2 + 0.04) * 2 / 12.0)    # Eq. 12-17
        self.assertAlmostEqual(td["volume"], expected_v, places=9)

    def test_silhouette_formula_limits(self):
        # Eq. 12-1 (reconstructed): uniform cylinder D L, A_side = A_top = D L -> pi D L (= Eq. 12-4)
        self.assertAlmostEqual(f.silhouette_area(2.0 * 5.0, 2.0 * 5.0), f.uniform_cylinder(2.0, 5.0)["area"])
        # an elliptic cylinder 2 x 1 x 3: the average-width estimate is within 3 % of the Ramanujan-based Eq. 12-2 for a 2:1 ellipse
        e = f.elliptic_cylinder(2.0, 1.0, 3.0)["area"]
        self.assertAlmostEqual(f.silhouette_area(2.0 * 3.0, 1.0 * 3.0) / e, 1.0, delta=0.03)


class RulesTests(unittest.TestCase):
    def test_tail_strike_angle(self):
        self.assertAlmostEqual(f.tail_strike_angle_deg(0.0, 4.0, 4.0 * math.tan(math.radians(14.0))), 14.0)
        with self.assertRaises(ValueError):
            f.tail_strike_angle_deg(3.0, 2.0, 0.5)

    def test_cabin_requirements_from_the_text(self):
        r = f.cabin_requirements(2, False, 4)
        self.assertAlmostEqual(r["min_width_m"], 1.0)                              # 2 x 50 cm
        r2 = f.cabin_requirements(6, True, 120)
        self.assertAlmostEqual(r2["min_width_m"], 6 * 0.5 + 20 * 0.0254)
        self.assertEqual((r2["lavatories_if_mission_over_1h"], r2["galleys_if_mission_over_1h"]), (3, 2))
        self.assertAlmostEqual(f.PASSENGER_SPACE_M[1], 43 * 0.0254)


class ProjectTests(unittest.TestCase):
    def build(self, tmp, mutate=None, mods=("m09b", "m08", "m15", "m10")):
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        if mutate:
            mutate(data)
        src = Path(tmp) / "in.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        path = Path(tmp) / "p.json"
        main(["project-init", "--project", str(path), "--name", "fus", "--from-inputs", str(src)])
        for mod in mods:
            main([mod, "--project", str(path)])
        return path

    def test_sizing_chain_into_m10(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = prj.load(self.build(tmp))
            r15, r10 = data["outputs"]["m15"]["result"], data["outputs"]["m10"]["result"]
            lens = r15["lengths_m"]
            self.assertAlmostEqual(lens["total"], lens["nose"] + lens["cabin"] + lens["tail"])
            self.assertGreaterEqual(lens["tail"], lens["tail_required_by_m08"] - 1e-12)
            # M10 builds the fuselage that M15 sized
            fus = next(c for c in r10["components"] if c["type"] == "fuselage")
            self.assertAlmostEqual(fus["length_m"], lens["total"], places=9)
            self.assertAlmostEqual(fus["max_radius_m"], r15["cabin"]["diameter_m"] / 2.0)
            self.assertAlmostEqual(fus["stations"][0]["x_m"], r15["positions_m"]["x_nose"])
            self.assertAlmostEqual(fus["stations"][-1]["x_m"], r15["positions_m"]["x_tail_end"])
            self.assertTrue(r10["valid"], [c for c in r10["checks"] if not c["ok"]])
            self.assertEqual(sorted(data["outputs"]["m10"]["run"]["depends_on"]), ["m08", "m09b", "m15"])
            self.assertEqual(prj.stale(data), [])
            # areas: M15's elementary-solid estimate and M10's station polyline agree within 5 % for the same shapes
            ratio = r15["wetted_area_m2"] / fus["wetted_area_estimate_m2"]
            self.assertAlmostEqual(ratio, 1.0, delta=0.05)
            keys = {a["key"] for a in data["assumptions"] if a["module"] == "m15"}
            self.assertEqual(keys, {"nose_factor", "cabin_length_m"})

    def test_checks_report_ranges_without_correcting(self):
        def mut(d):
            d["m15"]["cabin"]["diameter_m"] = 0.9          # narrower than 2 x 0.5 m: fails the width check
        with tempfile.TemporaryDirectory() as tmp:
            r = prj.load(self.build(tmp, mut, mods=("m09b", "m08", "m15")))["outputs"]["m15"]["result"]
            names = {c["name"]: c for c in r["checks"]}
            self.assertFalse(names["cabin_diameter_vs_minimum_width"]["ok"])
            self.assertFalse(r["within_guidance"])
            self.assertEqual(r["cabin"]["diameter_m"], 0.9)             # the input is not silently changed

    def test_rotation_check(self):
        def mut(d):
            d["m15"]["rotation"] = {"x_main_contact_m": 0.4, "x_tail_point_m": 5.0, "tail_point_height_m": 1.0, "alpha_stall_deg": 15.0,
                                    "incidence_deg": 2.0}
        with tempfile.TemporaryDirectory() as tmp:
            r = prj.load(self.build(tmp, mut, mods=("m09b", "m08", "m15")))["outputs"]["m15"]["result"]["rotation"]
            self.assertAlmostEqual(r["tail_strike_angle_deg"], math.degrees(math.atan2(1.0, 4.6)))
            self.assertAlmostEqual(r["fuselage_pitch_at_stall_deg"], 13.0)
            self.assertFalse(r["ok"])                                                 # 12.3 deg < 13 deg needed

    def test_tadpole_and_frustum_tail_shapes(self):
        def tadpole(d):
            d["m15"]["shape"] = "tadpole"
            d["m15"]["tadpole"] = {"d1_m": 0.5, "d2_m": 0.2}
        with tempfile.TemporaryDirectory() as tmp:
            r = prj.load(self.build(tmp, tadpole, mods=("m09b", "m08", "m15")))["outputs"]["m15"]["result"]
            self.assertEqual(set(r["solids"]), {"nose_paraboloid", "cabin_cylinder", "frustum_1", "frustum_2"})
            self.assertAlmostEqual(r["m10_fuselage"]["tail_radius_m"], 0.1)
        def frustum(d):
            d["m15"]["shape"] = "frustum_tail"
        with tempfile.TemporaryDirectory() as tmp:
            r = prj.load(self.build(tmp, frustum, mods=("m09b", "m08", "m15")))["outputs"]["m15"]["result"]
            self.assertIn("tail_frustum", r["solids"])
            self.assertAlmostEqual(r["m10_fuselage"]["tail_radius_m"], 0.1524)     # R2 of M08 (Example 11-1 data)


if __name__ == "__main__":
    unittest.main()
