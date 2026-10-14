import json
import tempfile
import unittest
from pathlib import Path

from aerosuite.adrpy_core import load_concept, export_result

class CoreTests(unittest.TestCase):
    def test_load_example(self):
        doc=load_concept(Path("examples/aircraft-concept.json"))
        self.assertIn("aspectratio",doc["designdefinition"])
        self.assertIn("groundrun_m",doc["designbrief"])
    def test_reject_broken_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"bad.json"
            p.write_text('{"designbrief":1}',encoding="utf-8")
            with self.assertRaises(ValueError):load_concept(p)
    def test_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"out.json"
            export_result({"value":1.5,"units":"N/m²"},p)
            self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["value"],1.5)

if __name__ == "__main__":
    unittest.main()
