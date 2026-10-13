import unittest
from aerosuite.airfoils import naca4
from aerosuite.preselection import Requirements, evaluate_naca4

class AirfoilTests(unittest.TestCase):
    def test_count(self):
        self.assertEqual(len(naca4("2412",81)),161)
    def test_symmetry(self):
        pts=naca4("0012",81)
        self.assertAlmostEqual(pts[0][1],-pts[-1][1],places=7)
        self.assertAlmostEqual(pts[40][1],-pts[-41][1],places=7)
    def test_le(self):
        self.assertAlmostEqual(naca4("0012",81)[80][0],0,places=10)
    def test_bad_code(self):
        for code in ("24A2","241","2012","2400"):
            with self.assertRaises(ValueError): naca4(code)
    def test_shortlist(self):
        rows=evaluate_naca4(["0006","2412","4420"],Requirements(.10,.18,.05))
        self.assertTrue(next(r for r in rows if r["code"]=="2412")["passes_geometry_constraints"])
        self.assertFalse(next(r for r in rows if r["code"]=="0006")["passes_geometry_constraints"])

if __name__=="__main__": unittest.main()
