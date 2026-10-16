"""M24 tests (STEP export of the M10 OML with CadQuery). The CAD tests are skipped when CadQuery is not installed (requirements-cad.txt);
the CAD-free invariants and the missing-CadQuery message are always checked. Reference values are computed from M10 without CAD."""
import builtins
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aerosuite import m24_cad as cad
from aerosuite import project as prj
from aerosuite.__main__ import main

try:
    import cadquery  # noqa: F401
    HAVE_CQ = True
except ImportError:
    HAVE_CQ = False

EXAMPLE = Path(__file__).parents[1] / "examples" / "projects" / "oml-c172-like.json"


def build_project(tmp, m24=None, mutate=None):
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    if mutate:
        mutate(data)
    data["m24"] = dict(m24 or {})
    data["m24"].setdefault("out_dir", str(Path(tmp) / "cad"))
    src = Path(tmp) / "in.json"
    src.write_text(json.dumps(data), encoding="utf-8")
    path = Path(tmp) / "p.json"
    main(["project-init", "--project", str(path), "--name", "oml", "--from-inputs", str(src)])
    for m in ("m09b", "m08", "m10"):
        main([m, "--project", str(path)])
    return path


class CadFreeTests(unittest.TestCase):
    def test_missing_cadquery_gives_install_instruction(self):
        real = builtins.__import__

        def fake(name, *a, **k):
            if name == "cadquery":
                raise ImportError("no cadquery")
            return real(name, *a, **k)
        with mock.patch("builtins.__import__", fake):
            with self.assertRaises(SystemExit) as cm:
                cad.require_cadquery()
        self.assertIn("requirements-cad.txt", str(cm.exception))

    def test_polygon_area_and_frustum_volume(self):
        self.assertAlmostEqual(cad.polygon_area([(0, 0), (2, 0), (2, 1), (0, 1)]), 2.0)
        comp = {"type": "fuselage", "axis_z_m": 0.0, "max_radius_m": 1.0,
                "stations": [{"x_m": 0.0, "radius_m": 0.0}, {"x_m": 3.0, "radius_m": 1.0}, {"x_m": 5.0, "radius_m": 1.0}]}
        ref = cad.reference_invariants(comp, {})
        self.assertAlmostEqual(ref["volume_m3"], math.pi * 3.0 / 3.0 + math.pi * 2.0, places=12)       # cone + cylinder
        self.assertAlmostEqual(ref["length_m"], 5.0)

    def test_naca_foil_closed_and_open_trailing_edge(self):
        closed = cad.foil_points("naca2412", {"te": "closed"})
        opened = cad.foil_points("naca2412", {"te": "open"})
        self.assertEqual(closed[0], closed[-1])
        self.assertNotEqual(opened[0], opened[-1])
        self.assertGreater(cad.polygon_area(cad._ring(opened)), cad.polygon_area(cad._ring(closed)))
        with self.assertRaises(SystemExit):
            cad.foil_points("e387", {})
        with self.assertRaises(SystemExit):
            cad.foil_points("naca2412", {"te": "round"})

    def test_selig_file_foil_and_te_closing(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "x.dat"
            f.write_text("X\n1 0.01\n0.5 0.06\n0 0\n0.5 -0.05\n1 -0.01\n", encoding="utf-8")
            pts = cad.foil_points("x", {"airfoil_files": {"x": str(f)}, "te": "closed"})
            self.assertEqual(pts[0], pts[-1])                                 # closed at the TE midpoint
            self.assertAlmostEqual(pts[0][1], 0.0)


@unittest.skipUnless(HAVE_CQ, "CadQuery not installed (requirements-cad.txt)")
class StepExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = build_project(cls.tmp.name)
        main(["m24", "--project", str(cls.path)])
        cls.data = prj.load(cls.path)
        cls.r = cls.data["outputs"]["m24"]["result"]
        cls.out = Path(cls.r["out_dir"])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_files_manifest_and_names(self):
        for name in ("oml.step", "oml-wing.step", "oml-horizontal_tail.step", "oml-vertical_tail.step", "oml-fuselage.step", "manifest.json"):
            self.assertTrue((self.out / name).is_file(), name)
        text = (self.out / "oml.step").read_text(errors="replace")
        self.assertIn("SI_UNIT(.MILLI.,.METRE.)", text)                      # millimetres declared in the STEP
        for part in ("wing", "horizontal_tail", "vertical_tail", "fuselage"):
            self.assertIn(part, text)
        man = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(man["units_out"], "mm")
        self.assertIn("aft", man["axes"]["x"])
        self.assertEqual(len(man["source_project"]["sha256"]), 64)
        self.assertEqual(man["source_project"]["m10_result_sha256"], prj.digest(self.data["outputs"]["m10"]["result"]))
        self.assertIn("cadquery", man["versions"])

    def test_reimported_invariants_within_tolerance(self):
        v = self.r["validation"]
        self.assertTrue(v["all_ok"])
        by = {(c["component"], c["quantity"]): c for c in v["checks"]}
        self.assertLess(by[("wing", "volume_m3")]["relative_difference"], 1e-6)
        self.assertLess(by[("wing", "planform_area_m2")]["relative_difference"], 1e-3)       # vs M10 planform area
        self.assertAlmostEqual(by[("wing", "span_m")]["step"], 11.3719, delta=1e-3)
        self.assertAlmostEqual(by[("fuselage", "volume_m3")]["step"], by[("fuselage", "volume_m3")]["reference"], delta=1e-9)
        self.assertEqual(self.r["assembly_solids"], 4)

    def test_bbox_in_mm_matches_m10_axes(self):
        oml = self.data["outputs"]["m10"]["result"]
        box = self.r["assembly_bbox_mm"]
        span_mm = 1000.0 * oml["reference"]["overall_span_m"]
        self.assertAlmostEqual(box["y"][1] - box["y"][0], span_mm, delta=1.0)
        self.assertAlmostEqual(box["y"][0], -box["y"][1], delta=1e-3)         # symmetric about y = 0
        length_mm = 1000.0 * oml["reference"]["overall_length_m"]
        self.assertGreaterEqual(box["x"][1] - box["x"][0], length_mm - 1.0)

    def test_stale_after_m10_change_and_export(self):
        data = prj.load(self.path)
        self.assertEqual(prj.stale(data), [])
        data["outputs"]["m10"]["result"]["reference"]["overall_span_m"] += 0.1
        self.assertIn("m24", prj.stale(data))
        out = Path(self.tmp.name) / "m24.json"
        main(["export", "--project", str(self.path), "--module", "m24", "--out", str(out)])
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["module"], "m24")

    def test_refuses_to_overwrite_an_export(self):
        with self.assertRaises(SystemExit) as cm:
            main(["m24", "--project", str(self.path)])
        self.assertIn("already has an M24 export", str(cm.exception))

    def test_open_trailing_edge_gives_more_volume(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build_project(tmp, {"te": "open"})
            main(["m24", "--project", str(path)])
            r = prj.load(path)["outputs"]["m24"]["result"]
            self.assertTrue(r["validation"]["all_ok"])
            vo = next(c["step"] for c in r["validation"]["checks"] if c["component"] == "wing" and c["quantity"] == "volume_m3")
            vc = next(c["step"] for c in self.r["validation"]["checks"] if c["component"] == "wing" and c["quantity"] == "volume_m3")
            self.assertGreater(vo, vc)

    def test_non_circular_fuselage_section_is_refused(self):
        def mutate(d):
            d["m10"]["fuselage"]["n1"] = 0.8
        with tempfile.TemporaryDirectory() as tmp:
            path = build_project(tmp, mutate=mutate)
            with self.assertRaises(SystemExit) as cm:
                main(["m24", "--project", str(path)])
            self.assertIn("only circular sections", str(cm.exception))

    def test_invalid_component_names_the_component(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build_project(tmp)
            data = prj.load(path)
            data["outputs"]["m10"]["result"]["components"][2]["sections"][1]["chord_m"] = 0.0      # horizontal tail tip chord = 0
            prj.save(data, path)
            with self.assertRaises(SystemExit) as cm:
                main(["m24", "--project", str(path)])
            self.assertIn("horizontal_tail", str(cm.exception))

    def test_requires_m10(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.json"
            data = prj.new_project("x")
            data["inputs"]["m24"] = {"out_dir": str(Path(tmp) / "c")}
            prj.save(data, path)
            with self.assertRaises(SystemExit) as cm:
                main(["m24", "--project", str(path)])
            self.assertIn("run m10 first", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
