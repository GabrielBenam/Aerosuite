import unittest
from pathlib import Path
from aerosuite.flow5_adapter import Flow5Job, build_command, execute_job

class Flow5AdapterTests(unittest.TestCase):
    def test_command(self):
        job=Flow5Job("2412", (100000, 200000))
        cmd=build_command(Path("solver.exe"),job,Path("result.fl5"))
        self.assertIn("--reynolds",cmd)
        self.assertIn("100000,200000",cmd)
        self.assertIn("--output",cmd)
        self.assertEqual(cmd[-1],"result.fl5")

    def test_bad_airfoil(self):
        with self.assertRaises(ValueError):
            Flow5Job("2099",(100000,)).validate()

    def test_bad_reynolds(self):
        with self.assertRaises(ValueError):
            Flow5Job("2412",(float("nan"),)).validate()

    def test_bad_alpha(self):
        with self.assertRaises(ValueError):
            Flow5Job("2412",(100000,), alpha_step=0).validate()

    def test_solver_absent(self):
        with self.assertRaises(FileNotFoundError):
            execute_job(Path("/missing-aerosuite-solver.exe"), Flow5Job("2412",(100000,)), Path("results"))

if __name__=="__main__":
    unittest.main()
