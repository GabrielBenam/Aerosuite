"""M22 tests: the `project` engine of aerosuite/optimizer.py on a small problem with a mesh-verifiable optimum (D-48): the cruise speed of
maximum Breguet range (propeller aircraft, constant speed and altitude, GUD Eq. 21-25 via M21) for the Example 3-1 wing. The reference is a fine
grid on the same engine; DE and SLSQP are compared with it, and the optimum is contrasted (not equated) with the best-L/D speed."""
import csv
import json
import math
import os
import tempfile
import unittest
from pathlib import Path

from aerosuite import m21_performance as m21
from aerosuite.engines import flow5_executable
from aerosuite.optimizer import ProjectEngine, Spec, run

SPEC = Path(__file__).parents[1] / "examples" / "opt-project-range-speed.json"
FLOW5_SPEC = Path(__file__).parents[1] / "examples" / "opt-project-flow5-wing.json"


def load_spec(**over):
    data = json.loads(SPEC.read_text(encoding="utf-8"))
    data["base"] = str((SPEC.parent / data["base"]).resolve())
    data.update(over)
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(data, tmp)
    tmp.close()
    try:
        return Spec.load(Path(tmp.name))
    finally:
        os.unlink(tmp.name)


class RangeSpeedValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = Path(cls.tmp.name)
        cls.grid = run(load_spec(method="grid", settings={"grid_points": 551, "max_iter": 2}), t / "grid")
        cls.de = run(load_spec(), t / "de")
        cls.slsqp = run(load_spec(method="SLSQP", settings={"maxiter": 200, "tol": 1e-12, "x0": [60.0], "max_iter": 2}), t / "slsqp")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def best(self, r):
        return r["best"]["variables"]["m21.cruise.speed_mps"], r["best"]["metrics"]["m21.payload_range.1.range_const_v_h_km"]

    def test_all_methods_find_the_grid_optimum(self):
        vg, rg = self.best(self.grid)
        for r in (self.de, self.slsqp):
            v, rng = self.best(r)
            self.assertAlmostEqual(v, vg, delta=0.15)                       # grid step 0.1 m/s
            self.assertLessEqual(abs(rng - rg) / rg, 2e-4)
        self.assertGreaterEqual(self.best(self.de)[1], rg * (1 - 1e-6))      # DE/polish is at least as good as the grid point
        self.assertTrue(self.de["solver"]["success"])

    def test_optimum_is_near_the_best_ld_speed(self):
        """Contrast: V of max range at constant speed and altitude vs the best-L/D speed at the start and end weights (M21)."""
        v_opt = self.best(self.de)[0]
        pr = json.loads((SPEC.parent / "projects" / "m22-range-speed-inputs.json").read_text(encoding="utf-8"))["m21"]
        s, k, cd0 = 11.148, self.de["best"]["metrics"]["m21.aero.k"], 0.0333
        rho = m21.isa(2438.4)["rho"]
        tow = pr["weights"]["mtow_kg"]
        v_start = m21.v_max_ld(tow * 9.80665, rho, s, cd0, k)
        v_end = m21.v_max_ld(0.8 * tow * 9.80665, rho, s, cd0, k)           # fuel is about 15-25 % of the take-off weight
        self.assertTrue(0.9 * v_end <= v_opt <= 1.1 * v_start, (v_opt, v_end, v_start))

    def test_levels_roles_and_viability_are_declared(self):
        r = self.de
        self.assertEqual(r["level"], "conceptual")
        self.assertEqual(r["levels_used"], ["conceptual"])
        self.assertIn("not a 3D or CFD", r["level_statement"])
        self.assertEqual(r["roles"]["decision_variables"], ["m21.cruise.speed_mps"])
        self.assertEqual(r["roles"]["objective"]["sense"], "maximize")
        self.assertIn("note", r["physical_viability"])
        self.assertEqual(r["failed_evaluations"], 0)
        self.assertEqual(r["best"]["metrics"]["loop_stop"], "stable")

    def test_outputs_files(self):
        out = Path(self.tmp.name) / "de"
        self.assertTrue((out / "optimization.json").is_file())
        rows = list(csv.DictReader((out / "evaluations.csv").open(encoding="utf-8")))
        self.assertEqual(len(rows), self.de["evaluations"])
        self.assertIn("m21.payload_range.1.range_const_v_h_km", rows[0])


class FailureAndFlagTests(unittest.TestCase):
    def test_missing_input_stops_the_evaluation_without_invented_penalty(self):
        spec = load_spec(method="grid", settings={"grid_points": 3, "max_iter": 1}, variables=[{"name": "m21.cruise.speed_mps", "lower": 30.0, "upper": 40.0}])
        with tempfile.TemporaryDirectory() as tmp:
            base = json.loads(Path(spec.base).read_text(encoding="utf-8"))
            base["m21"].pop("weights")                                   # M21 needs it: the evaluation must fail, not be penalised
            p = Path(tmp) / "b.json"
            p.write_text(json.dumps(base), encoding="utf-8")
            spec.base = p
            r = run(spec, Path(tmp) / "o")
            self.assertEqual(r["failed_evaluations"], r["evaluations"])
            self.assertIsNone(r["best"])
            self.assertIn("weights", json.dumps(r["ranking"] or "weights"))

    def test_unknown_variable_path_is_a_failed_evaluation(self):
        spec = load_spec(method="grid", settings={"grid_points": 3}, variables=[{"name": "m21.cruise.nonexistent", "lower": 1.0, "upper": 2.0}])
        with tempfile.TemporaryDirectory() as tmp:
            r = run(spec, Path(tmp))
            self.assertEqual(r["failed_evaluations"], r["evaluations"])

    def test_flow5_requires_explicit_flag(self):
        spec = load_spec(settings={"flow5": {"enabled": False}})
        self.assertEqual(spec.level, "conceptual")
        with self.assertRaises(ValueError):                              # a conceptual spec cannot silently turn on 3D
            load_spec(settings={"flow5": {"enabled": True}})
        spec = load_spec(level="aero3d", settings={"flow5": {"enabled": True, "max_evaluations": 1}})
        self.assertEqual(spec.level, "aero3d")
        eng = ProjectEngine(spec.base, Path("."), spec)
        self.assertTrue(eng.f5_enabled)
        self.assertEqual(eng.f5["max_evaluations"], 1)
        with self.assertRaises(ValueError):
            load_spec(engine="flow5")                                    # standalone 3D engine still refused

    def test_get_path_with_dotted_keys(self):
        doc = {"m21": {"performance_at_mtow": {"0.0": {"rc": 5.0}}, "list": [{"a": 1.0}]}}
        self.assertEqual(ProjectEngine._get(doc, "m21.performance_at_mtow.0.0.rc"), 5.0)
        self.assertEqual(ProjectEngine._get(doc, "m21.list.0.a"), 1.0)
        with self.assertRaises(KeyError):
            ProjectEngine._get(doc, "m21.nothing")


@unittest.skipUnless(os.environ.get("AEROSUITE_FLOW5_TESTS") == "1" and flow5_executable() and FLOW5_SPEC.is_file(),
                     "real flow5 run (about 1-2 min each): set AEROSUITE_FLOW5_TESTS=1")
class Flow5LevelTests(unittest.TestCase):
    def test_project_optimization_with_real_flow5(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run(Spec.load(FLOW5_SPEC), Path(tmp))
            self.assertEqual(r["level"], "aero3d")
            self.assertIn("3D", r["levels_used"])
            self.assertLessEqual(r["evaluations"] - r["failed_evaluations"], 2)
            self.assertTrue(r["best"]["metrics"]["flow5.cl_alpha_per_rad"] > 3.0)


if __name__ == "__main__":
    unittest.main()
