import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from aerosuite.airfoil_lab_core import BatchRequest, uiuc_ids, load_profiles
from aerosuite.xfoil_cli import XFoilCase
DATA="Demo\n1.0 0.0\n0.5 0.08\n0.0 0.0\n0.5 -0.08\n1.0 0.0\n"
class AirfoilLabTests(unittest.TestCase):
    def test_batch_input(self):
        with self.assertRaises(ValueError):
            BatchRequest(("naca2412",),None,Path("missing.exe"),XFoilCase(),Path("out")).validate()
    def test_catalog_mixed_profiles(self):
        with tempfile.TemporaryDirectory() as t:
            archive=Path(t)/"test.zip"
            with ZipFile(archive,"w") as z:
                z.writestr("sub/ag03.dat",DATA)
                z.writestr("sub/ag04.dat",DATA)
            self.assertEqual(uiuc_ids(archive),["ag03","ag04"])
            result=load_profiles(("naca2412","ag03"),archive)
            self.assertEqual(len(result),2)
    def test_missing_zip(self):
        with self.assertRaises(ValueError):
            load_profiles(("ag03",),None)
if __name__ == "__main__": unittest.main()
