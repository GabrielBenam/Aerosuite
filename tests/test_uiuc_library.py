import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from aerosuite.uiuc_library import parse_selig,load_library,catalog
from aerosuite.airfoil_compare import read_polar_csv, plot_polars

TEST_DATA = """Example foil
1.0 0.0
0.5 0.07
0.0 0.0
0.5 -0.07
1.0 0.0
"""

class UIUCTests(unittest.TestCase):
    def test_geometry(self):
        p=parse_selig(TEST_DATA)
        self.assertEqual(len(p.coordinates),5)
    def test_comment(self):
        p=parse_selig("# hello\n"+TEST_DATA.replace("0.5 0.07","0.5 0.07 # comment"))
        self.assertEqual(p.coordinates[1],(.5,.07))
    def test_invalid(self):
        with self.assertRaises(ValueError):
            parse_selig("invalid\n0 0\n1 1")
    def test_zip_catalog(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            archive=root/"test.zip"
            with ZipFile(archive,"w") as z:
                z.writestr("example.dat",TEST_DATA)
                z.writestr("invalid.dat","bad")
            profiles,errors=load_library(archive)
            self.assertEqual(len(profiles),1)
            self.assertEqual(len(errors),1)
            stats=catalog(archive,root/"catalog.json")
            self.assertEqual(stats["profiles_imported"],1)
    def test_polar_csv(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"polar.csv"
            path.write_text("alpha,cl,cd,cm\n0,0.1,0.02,-0.01\n")
            self.assertEqual(read_polar_csv(path)[0]["cl"],0.1)
    def test_conditions_must_match(self):
        p={"a":[{"alpha":0,"cl":1,"cd":.1,"cm":0}],
           "b":[{"alpha":0,"cl":1,"cd":.1,"cm":0}]}
        with self.assertRaises(ValueError):
            plot_polars(p,Path("not-used"))

if __name__=="__main__":
    unittest.main()
