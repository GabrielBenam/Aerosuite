"""Unit and integration tests for the engine connections added in 2026-10.

Integration tests run only when the real engine is available; they are
reported as SKIPPED otherwise (never as passed).
"""
import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from aerosuite import engines
from aerosuite.xfoil_cli import XFoilCase, make_script, missing_angles, parse_polar, solver_version

HAS_ADRPY = importlib.util.find_spec("ADRpy") is not None and importlib.util.find_spec("scipy") is not None
XFOIL = engines.xfoil_executable()
ROOT = Path(__file__).resolve().parents[1]

DEBIAN_POLAR = """ XFOIL         Version 6.99
   alpha    CL        CD       CDp       CM     Top_Xtr  Bot_Xtr  Top_Itr  Bot_Itr
  ------ -------- --------- --------- -------- -------- -------- -------- --------
  -1.000   0.1300   0.00600   0.00050  -0.0520   0.7000   0.5000  20.0000 130.0000
   0.000   0.2371   0.00564   0.00049  -0.0520   0.6517   0.6795  23.5781 139.8384
   2.000   0.4496   0.00578   0.00079  -0.0481   0.5256   0.9675  31.2661 157.0430
"""


class XfoilParsing(unittest.TestCase):
    def test_nine_column_polar_and_missing_points(self):
        rows = parse_polar(DEBIAN_POLAR)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1]["cdp"], 0.00049)
        case = XFoilCase(alpha_start=-1, alpha_end=2, alpha_step=1)
        self.assertEqual(missing_angles(rows, case), [1.0])
        self.assertEqual(solver_version(DEBIAN_POLAR), "6.99")

    def test_from_zero_branches_and_transition(self):
        case = XFoilCase(alpha_start=-4, alpha_end=10, alpha_step=1, from_zero=True, xtr_top=0.3)
        self.assertEqual(case.branches(), [(0.0, 10, 1), (-1, -4, -1)])
        script = make_script(case, case.branches()[1])
        self.assertIn("ASEQ -1 -4 -1", script)
        self.assertIn("XTR 0.3 1", script)
        with self.assertRaises(ValueError):
            XFoilCase(xtr_top=1.5).validate()


class Status(unittest.TestCase):
    def test_status_structure(self):
        s = engines.status()
        self.assertIn("flow5", s["vendor"])
        self.assertEqual(s["vendor"]["flow5"]["pinned_commit"], engines.PINNED["flow5"]["sha"])
        self.assertIn("xfoil_2d", s["capabilities"])


class Flow5Exchange(unittest.TestCase):
    @unittest.skipUnless(HAS_ADRPY, "ADRpy not installed (fluid properties come from ADRpy ISA)")
    def test_export_is_wellformed_and_complete(self):
        from aerosuite.flow5_xml import export
        with tempfile.TemporaryDirectory() as tmp:
            manifest = export(ROOT / "examples" / "flow5-c162-like.json", Path(tmp) / "job")
            plane = ET.parse(manifest["plane_xml"]).getroot()
            self.assertEqual(plane.tag, "xflplane")
            self.assertEqual(len(plane.findall("./Plane/wing")), 3)
            polar = ET.parse(manifest["polar_xml"]).getroot()
            self.assertEqual(polar.find("./Polar/Method").text, "VLM2")
            self.assertEqual(polar.find("./Polar/Plane_Name").text, plane.find("./Plane/Name").text)
            script = ET.parse(manifest["script_xml"]).getroot()
            self.assertEqual(script.tag, "xflscript")
            self.assertEqual(len(script.findall("./Plane_analysis/Foil_Dat_Files/Foil_File_Name")), 2)
            first = Path(manifest["foil_files"][0]).read_text(encoding="ascii").splitlines()[0]
            self.assertEqual(first, "NACA 2412")
            with self.assertRaises(FileExistsError):
                export(ROOT / "examples" / "flow5-c162-like.json", Path(tmp) / "job")

    def test_rejects_bad_planes(self):
        from aerosuite.flow5_xml import validate
        with self.assertRaises(ValueError):
            validate({"name": "x", "wings": [{"type": "FIN", "sections": []}]})
        with self.assertRaises(ValueError):
            validate({"name": "x", "wings": [{"sections": [{"y_m": 1, "chord_m": 1, "foil": "NACA 0012"},
                                                           {"y_m": 0, "chord_m": 1, "foil": "NACA 0012"}]}]})


@unittest.skipUnless(HAS_ADRPY, "ADRpy/SciPy not installed")
class AdrpyAndOptimizer(unittest.TestCase):
    def test_reference_checks(self):
        from aerosuite.validation import adrpy_docstring_check, gudmundsson_example_3_1, isa_check
        self.assertTrue(isa_check()["passed"])
        self.assertTrue(adrpy_docstring_check()["passed"])
        rows = {r["constraint"]: r for r in gudmundsson_example_3_1()["rows"]}
        # Documented tolerance: different k and take-off formulations (see TEST_RESULTS.md)
        for name in ("climb", "cruise", "turn"):
            self.assertLess(abs(rows[name]["rel_diff"]), 0.02, name)
        for name in ("takeoff", "ceiling"):
            self.assertLess(abs(rows[name]["rel_diff"]), 0.08, name)

    def test_size_applies_stall_limit(self):
        from aerosuite.adrpy_core import load_concept, size
        result = size(load_concept(ROOT / "examples" / "gudmundsson-ex3-1-c162.json"))
        self.assertIsNotNone(result["stall_limit_wingloading_pa"])
        self.assertLessEqual(result["best_sample"]["wingloading_pa"], result["stall_limit_wingloading_pa"])
        self.assertTrue(result["power_required"]["available"])

    def test_conceptual_optimizer_contract(self):
        from aerosuite.optimizer import Spec, run
        spec = Spec.load(ROOT / "examples" / "opt-conceptual-c162.json")
        spec.settings = {"seed": 1, "maxiter": 15, "popsize": 6}
        with tempfile.TemporaryDirectory() as tmp:
            result = run(spec, Path(tmp))
            self.assertEqual(result["level"], "conceptual")
            best = result["best"]
            self.assertTrue(best["feasible"])
            self.assertLessEqual(best["variables"]["wingloading_pa"], best["metrics"]["stall_limit_wingloading_pa"])
            self.assertTrue((Path(tmp) / "evaluations.csv").is_file())

    def test_flow5_engine_is_refused(self):
        from aerosuite.optimizer import Spec
        spec = Spec("x", "flow5", {}, [{"name": "a", "lower": 0, "upper": 1}], {"metric": "cl", "sense": "maximize"})
        with self.assertRaises(ValueError):
            spec.validate()


@unittest.skipUnless(XFOIL is not None, "XFOIL executable not found (runtime/xfoil, AEROSUITE_XFOIL or PATH)")
class RealXfoil(unittest.TestCase):
    def test_naca0012_symmetry_and_drag(self):
        """Solver-level check: symmetric section gives CL=0 and CM=0 at alpha=0, positive CD."""
        from aerosuite.xfoil_cli import load_naca_selected, run_profile
        with tempfile.TemporaryDirectory() as tmp:
            ident, foil = load_naca_selected(["0012"])[0]
            meta = run_profile(XFOIL, ident, foil, XFoilCase(1e6, 0, 9, -2, 2, 2, 200), Path(tmp))
            rows = {round(r["alpha"]): r for r in parse_polar((Path(tmp) / "naca0012.polar").read_text())}
            self.assertEqual(meta["solver_version_reported"], "6.99")
            self.assertAlmostEqual(rows[0]["cl"], 0.0, places=3)
            self.assertAlmostEqual(rows[2]["cl"], -rows[-2]["cl"], places=2)
            self.assertGreater(rows[0]["cd"], 0.0)


if __name__ == "__main__":
    unittest.main()
