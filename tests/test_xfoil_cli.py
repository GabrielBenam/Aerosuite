import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from aerosuite.xfoil_cli import XFoilCase, load_naca_selected, load_uiuc_selected, make_script, parse_polar, all_angles_present

FIXTURE = """XFOIL Version 6.99
 Re = 1.000 e 6
 alpha    CL        CD       CDp       CM      Top_Xtr Bot_Xtr
 -----  -------   -------- ------- -------- ------- -------
 -2.000 -0.1000 0.01000 0.00600 -0.0500  0.7000 0.8000
  0.000  0.1200 0.00800 0.00400 -0.0450  0.6000 0.7500
  2.000  0.3100 0.00900 0.00500 -0.0400  0.5200 0.7000
"""
SELIG = "Example airfoil\n1.0 0.0\n0.5 0.08\n0.0 0.0\n0.5 -0.08\n1.0 0.0\n"
class XFoilCLITests(unittest.TestCase):
    def test_script(self):
        s=make_script(XFoilCase())
        self.assertIn("PACC\npolar.txt\n",s)
        self.assertIn("ASEQ -2 8 2",s)
    def test_parse_polar(self):
        rows=parse_polar(FIXTURE)
        self.assertEqual(len(rows),3)
        self.assertAlmostEqual(rows[1]["cl"],0.12)
        self.assertTrue(all_angles_present(rows,XFoilCase(alpha_end=2)))
        self.assertFalse(all_angles_present(rows,XFoilCase(alpha_end=4)))
    def test_reject_bad(self):
        with self.assertRaises(ValueError): parse_polar("alpha cl cd")
        with self.assertRaises(ValueError): XFoilCase(alpha_step=0).validate()
    def test_naca(self):
        rows=load_naca_selected(["2412","0012"])
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0][0],"naca2412")
    def test_uiuc_select(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"uiuc.zip"
            with ZipFile(path,"w") as f:
                f.writestr("all/example.dat",SELIG)
            foils=load_uiuc_selected(path,["example"])
            self.assertEqual(foils[0][0],"example")
    def test_missing_exe(self):
        from aerosuite.xfoil_cli import run_profile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                run_profile(Path(tmp)/"xfoil.exe","naca2412",
                            load_naca_selected(["2412"])[0][1],XFoilCase(),Path(tmp)/"results")

if __name__=="__main__":
    unittest.main()
