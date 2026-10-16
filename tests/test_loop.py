"""L-1 tests: the full algorithm loop (aerosuite/loop.py) on examples/projects/c162-full-loop.json.

The project joins the Gudmundsson Example 3-1 front end (Cessna 162: M01, M02, M04, M06, data of the book) with ILLUSTRATIVE user data for
the rest (marked in `_source`). The book figures checked here are those of Example 3-1 (T/W of take-off 0.1869 at W/S = 10 lbf/ft2, landing
W/S 11.37 lbf/ft2, S = 120 ft2, AR = 8). The convergence tests use a synthetic fixed-point 'module' (format/logic fixture, not aerodynamics)."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aerosuite import loop
from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite.engines import xfoil_executable

EXAMPLE = Path(__file__).parents[1] / "examples" / "projects" / "c162-full-loop.json"
G = 9.80665
PA_PER_PSF = 47.8803


def make_project(tmp, drop=(), mutate=None):
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    for k in drop:
        data.pop(k, None)
    if mutate:
        mutate(data)
    src = Path(tmp) / "in.json"
    src.write_text(json.dumps(data), encoding="utf-8")
    path = Path(tmp) / "p.json"
    main(["project-init", "--project", str(path), "--name", "c162-full", "--from-inputs", str(src)])
    return path


class FullLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = make_project(cls.tmp.name, drop=() if xfoil_executable() else ("m18c",))
        cls.summary = loop.run_loop(cls.path, max_iter=5)
        cls.data = prj.load(cls.path)
        cls.out = Path(cls.summary["output_dir"])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_stops_stable_with_everything_computed(self):
        self.assertTrue(self.summary["stop"]["reason"].startswith("stable"), self.summary["stop"])
        self.assertEqual(self.summary["stale"], [])
        expected = {"m01", "m02", "m04", "m06", "m08", "m09b", "m10", "m11", "m12", "m13", "m15", "m16", "m18a", "m18b", "m19", "m20", "m21"}
        self.assertTrue(expected <= set(self.data["outputs"]))

    def test_order_and_deferral(self):
        order = self.summary["iterations"][0]["order_executed"]
        pos = {m: i for i, m in enumerate(order)}
        self.assertLess(pos["m06"], pos["m04"])                 # M04 reads W0 from M06: deferred in the same pass
        self.assertLess(pos["m09b"], pos["m08"])                # M08 takes the wing from M09b
        self.assertLess(pos["m20"], pos["m16"])                 # M16 takes C_D0 from M20 (it is later in Table 1-4)
        self.assertLess(pos["m08"], pos["m10"])
        self.assertLess(pos["m12"], pos["m13"])
        self.assertIn("m20", self.data["outputs"]["m16"]["run"]["depends_on"])

    def test_iteration_files_record_inputs_outputs_status(self):
        it = json.loads((self.out / "iter-001.json").read_text(encoding="utf-8"))
        self.assertEqual(it["iteration"], 1)
        self.assertEqual(it["status"], "completed")
        self.assertEqual(set(it["inputs"]), set(it["order_executed"]))
        self.assertEqual(set(it["outputs"]), set(it["order_executed"]))
        self.assertTrue(all(v["status"] == "ran" for v in it["modules"].values()))
        loop_json = json.loads((self.out / "loop.json").read_text(encoding="utf-8"))
        self.assertEqual(loop_json["inputs_sha256"], prj.digest(json.loads(EXAMPLE.read_text(encoding="utf-8"))))
        self.assertIn("update_rule", loop_json)
        self.assertEqual(loop_json["versions"]["numpy"][:4], "1.26")

    def test_book_figures_example_3_1(self):
        m04 = self.data["outputs"]["m04"]["result"]
        i = min(range(len(m04["samples"])), key=lambda k: abs(m04["samples"][k]["wingloading_pa"] - 10 * PA_PER_PSF))
        s = m04["samples"][i]
        self.assertAlmostEqual(s["by_constraint"]["takeoff"], 0.1869, delta=0.0005)       # Eq. 3-1, printed 0.1869
        self.assertAlmostEqual(s["by_constraint"]["climb"], 0.2140, delta=0.2140 * 0.02)  # printed 0.2140 (ADRpy: 0.2126, -0.7 %)
        self.assertAlmostEqual(m04["landing"]["max_wingloading_lbf_ft2"], 11.37, delta=0.02)
        m09b = self.data["outputs"]["m09b"]["result"]["planform"]
        self.assertAlmostEqual(m09b["area_m2"] / 0.09290304, 120.0, delta=0.5)            # S = 120 ft2
        self.assertAlmostEqual(m09b["aspect_ratio"], 8.0)
        self.assertAlmostEqual(self.data["outputs"]["m06"]["result"]["w0_kg"] * 2.20462, 1320.0, delta=0.5)

    def test_cruise_t_w_is_sea_level_equivalent(self):
        """The book's cruise T/W (0.1192 at 8000 ft) is a thrust at altitude; M04 (ADRpy) reports it mapped to sea level."""
        m04 = self.data["outputs"]["m04"]["result"]
        i = min(range(len(m04["samples"])), key=lambda k: abs(m04["samples"][k]["wingloading_pa"] - 10 * PA_PER_PSF))
        cruise = m04["samples"][i]["by_constraint"]["cruise"]
        self.assertGreater(cruise, 0.1192)
        self.assertAlmostEqual(cruise * 0.7860, 0.1192, delta=0.1192 * 0.05)              # sigma = 0.7860 at 8000 ft (book, STEP 10)

    def test_m16_includes_fuselage(self):
        r = self.data["outputs"]["m16"]["result"]
        self.assertFalse(r["punto_neutro_optimista"])
        self.assertTrue(r["longitudinal_static"]["fuselage_contribution"]["included"])

    def test_rerun_is_reproducible_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_project(tmp, drop=() if xfoil_executable() else ("m18c",))
            summary = loop.run_loop(path, max_iter=5)
            again = prj.load(path)
            for m in self.data["outputs"]:
                if m in again["outputs"] and m not in ("m18c",):
                    self.assertEqual(prj.digest(again["outputs"][m]["result"]), prj.digest(self.data["outputs"][m]["result"]), m)
            # a second loop on the same project: nothing stale, new run folder, the first one is untouched
            before = (Path(summary["output_dir"]) / "iter-001.json").read_text(encoding="utf-8")
            second = loop.run_loop(path, max_iter=5)
            self.assertNotEqual(second["output_dir"], summary["output_dir"])
            self.assertEqual(second["stop"]["reason"].split()[0], "nothing_to_run")
            self.assertEqual((Path(summary["output_dir"]) / "iter-001.json").read_text(encoding="utf-8"), before)
            with self.assertRaises(SystemExit):
                loop.run_loop(path, max_iter=1, out_dir=summary["output_dir"])


class MissingDataTests(unittest.TestCase):
    def test_stops_at_the_module_with_missing_keys(self):
        def mutate(d):
            d["m09b"]["planform"].pop("taper_ratio")
        with tempfile.TemporaryDirectory() as tmp:
            path = make_project(tmp, drop=("m18c",), mutate=mutate)
            s = loop.run_loop(path, max_iter=3)
            self.assertEqual(s["stop"]["reason"], "missing_data")
            self.assertEqual(s["stop"]["module"], "m09b")
            self.assertIn("taper_ratio", s["stop"]["message"])
            self.assertIn("m09b", s["iterations"][0]["order_executed"] + [s["stop"]["module"]])
            self.assertNotIn("m09b", prj.load(path)["outputs"])
            self.assertEqual(len(s["iterations"]), 1)

    def test_missing_input_list_is_parsed(self):
        self.assertEqual(loop.missing_keys("inputs.m10 is missing: a, b"), ["a", "b"])
        self.assertEqual(loop.missing_keys("nothing here"), [])

    def test_project_without_dependency_inputs_stops_with_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_project(tmp, drop=("m18c", "m09b"))
            s = loop.run_loop(path, max_iter=2)
            self.assertEqual(s["stop"]["reason"], "missing_data")
            self.assertIn("m09b", s["stop"]["message"])


class ConvergenceFixtureTests(unittest.TestCase):
    """Synthetic fixed-point modules (logic fixture, NOT aerodynamics): A reads B's previous output and B reads A's, so each pass leaves the
    other stale until the values stop changing."""

    def run_fixture(self, max_iter, tol=1e-6, k=0.5):
        p = prj.new_project("fixture")
        p["inputs"] = {"m01": {}, "m02": {}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.json"

            def fake(project, module):
                other = {"m01": "m02", "m02": "m01"}[module]
                prev = project["outputs"].get(other, {}).get("result", {}).get("x", 1.0)
                prj.record(project, module, {"x": 1.0 + k * prev}, "conceptual", [], [other] if other in project["outputs"] else [])
                return 0.0
            for m in ("m01", "m02", "m01"):              # a previous run in which each module used the other's output: m02 is now stale
                fake(p, m)
            prj.save(p, path)
            with mock.patch.object(loop, "_run_module", fake), mock.patch.object(loop, "plan", lambda project: ["m01", "m02"]):
                return loop.run_loop(path, max_iter=max_iter, tol=tol)

    def test_converges_by_relative_change(self):
        s = self.run_fixture(60, tol=1e-6)
        self.assertTrue(s["stop"]["reason"].startswith("converged"), s["stop"])
        self.assertLess(len(s["iterations"]), 60)

    def test_max_iter_reached(self):
        s = self.run_fixture(2, tol=1e-12)
        self.assertEqual(s["stop"]["reason"], "max_iter reached")
        self.assertEqual(len(s["iterations"]), 2)

    def test_relative_change_function(self):
        a = {"m": {"x": 1.0, "y": "t"}}
        self.assertEqual(loop.max_relative_change(a, copy.deepcopy(a)), 0.0)
        self.assertAlmostEqual(loop.max_relative_change(a, {"m": {"x": 1.1, "y": "t"}}), 0.1 / 1.1)
        self.assertEqual(loop.max_relative_change(a, {"m": {"x": 1.0, "y": "u"}}), 1.0)


if __name__ == "__main__":
    unittest.main()
