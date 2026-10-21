"""P-4: M22 `project` engine with the wing weight coupled (M21 OEW from M12). The aspect ratio has an interior optimum of the maximum-payload range
because the M12 wing weight (Eqs. 6-43 to 6-47) grows with AR. DE and SLSQP are compared with a grid on the same engine (D-57).
Slow (about 5 s per evaluation: the loop runs M01-M23 with XFOIL): runs only with AEROSUITE_SLOW=1; the figures of the last run are in TEST_RESULTS."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from aerosuite.optimizer import Spec, run

SPEC = Path(__file__).parents[1] / "examples" / "opt-project-wing-weight.json"
KEY = "m09b.planform.aspect_ratio"
RANGE = "m21.payload_range.0.range_const_v_h_km"


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


class FastChecks(unittest.TestCase):
    def test_spec_declares_level_and_variables(self):
        spec = load_spec()
        self.assertEqual(spec.level, "conceptual")
        self.assertEqual([v["name"] for v in spec.variables], [KEY])

    def test_oew_follows_m12(self):
        from aerosuite import m21_performance as m21
        from aerosuite import project as prj
        p = prj.new_project("x")
        p["inputs"]["m21"] = {"weights": {"oew_from_m12": True, "oew_offset_kg": 5.0, "mtow_kg": 700.0}}
        with self.assertRaises(SystemExit):
            m21.evaluate(p)                                           # no outputs.m12


@unittest.skipUnless(os.environ.get("AEROSUITE_SLOW") == "1", "slow (about 5 minutes); set AEROSUITE_SLOW=1")
class InteriorOptimum(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = Path(cls.tmp.name)
        cls.grid = run(load_spec(method="grid", settings={"grid_points": 15, "max_iter": 1}), t / "grid")
        cls.de = run(load_spec(), t / "de")
        cls.slsqp = run(load_spec(method="SLSQP", settings={"maxiter": 12, "tol": 1e-9, "x0": [7.0], "max_iter": 1}), t / "slsqp")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def best(self, r):
        return r["best"]["variables"][KEY], r["best"]["metrics"][RANGE]

    def test_optimum_is_interior(self):
        ar, _ = self.best(self.grid)
        self.assertGreater(ar, 5.0 + 0.5)
        self.assertLess(ar, 12.0 - 0.5)

    def test_methods_agree_with_the_grid(self):
        ag, rg = self.best(self.grid)
        for r in (self.de, self.slsqp):
            a, rng = self.best(r)
            self.assertLessEqual(abs(rng - rg) / rg, 5e-3)
            self.assertAlmostEqual(a, ag, delta=1.2)


if __name__ == "__main__":
    unittest.main()
