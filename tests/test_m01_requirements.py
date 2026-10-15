"""M01 tests. Numerical references come from Gudmundsson 2nd ed. Sec. 1.3 (PDF p.57-58)."""
import json
import tempfile
import unittest
from pathlib import Path

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite.m01_requirements import evaluate, maneuver_load_factors, new_part23_class


def make(**kw):
    p = prj.new_project("t")
    base = {"category": "normal", "mtow_kg": 1000.0, "occupants": 4, "engines": 1, "vno_kcas": 130,
            "mmo": 0.2, "vso_kcas_max": 50}
    base.update(kw)
    p["inputs"]["m01"] = base
    return p


class M01Tests(unittest.TestCase):
    def test_book_examples_new_part23_classes(self):
        # GUD p.58: a Cessna 172 class aircraft is Level 2, Low-Performance, nonaerobatic;
        # an Eclipse 550 is Level 3, High-Performance, nonaerobatic.
        c172 = new_part23_class(4, 140, 0.2, False)
        self.assertEqual((c172["certification_level"], c172["performance_level"]), (2, "low"))
        eclipse = new_part23_class(7, 285, 0.6, False)
        self.assertEqual((eclipse["certification_level"], eclipse["performance_level"]), (3, "high"))

    def test_level_boundaries(self):
        for seats, level in ((1, 1), (2, 2), (6, 2), (7, 3), (9, 3), (10, 4), (19, 4)):
            self.assertEqual(new_part23_class(seats, 100, 0.1, False)["certification_level"], level)
        with self.assertRaises(ValueError):
            new_part23_class(20, 100, 0.1, False)

    def test_load_factors_table_1_2(self):
        light = maneuver_load_factors("normal", 600.0)       # 1323 lbf -> formula > 3.8 -> capped
        self.assertAlmostEqual(light["n_plus"], 3.8)
        self.assertAlmostEqual(light["n_minus"], 1.52)
        heavy = maneuver_load_factors("normal", 5000.0)      # 11023 lbf -> 2.1 + 24000/21023
        self.assertAlmostEqual(heavy["n_plus"], 2.1 + 24000 / (5000 * 2.2046226218 + 10000), places=9)
        self.assertEqual(maneuver_load_factors("utility", 900.0)["n_plus"], 4.4)
        self.assertEqual(maneuver_load_factors("aerobatic", 900.0)["n_minus"], 3.0)
        with self.assertRaises(ValueError):
            maneuver_load_factors("commuter", 900.0)

    def test_compliance_checks(self):
        self.assertTrue(evaluate(make())["compliant"])
        self.assertFalse(evaluate(make(vso_kcas_max=62))["compliant"])
        self.assertFalse(evaluate(make(occupants=10))["compliant"])
        self.assertFalse(evaluate(make(mtow_kg=6000))["compliant"])   # 13228 lbf > 12500 lbf
        self.assertTrue(evaluate(make(category="commuter", mtow_kg=8000, occupants=19, engines=2))["compliant"])

    def test_cli_roundtrip_and_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project.json"
            inputs = Path(tmp) / "in.json"
            inputs.write_text(json.dumps({"m01": make()["inputs"]["m01"]}), encoding="utf-8")
            main(["project-init", "--project", str(path), "--name", "t", "--from-inputs", str(inputs)])
            main(["m01", "--project", str(path)])
            data = prj.load(path)
            self.assertIn("m01", data["outputs"])
            self.assertEqual(prj.stale(data), [])
            data["inputs"]["m01"]["mtow_kg"] = 1100.0
            self.assertEqual(prj.stale(data), ["m01"])


if __name__ == "__main__":
    unittest.main()
