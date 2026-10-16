"""M04 tests against Gudmundsson Example 3-1 (Cessna 162, PDF p.109-111, printed p.64-66)."""
import json
import tempfile
import unittest
from pathlib import Path

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite.m04_constraints import (FT_PER_M, KGM3_PER_SLUGFT3, PA_PER_LBF_FT2, landing_distance_ft,
                                       landing_distance_m, max_wing_loading_for_landing_pa, takeoff_tw_book)

RHO_BOOK = 0.002378  # slug/ft^3, value used by the book
EXAMPLES = Path(__file__).parents[1] / "examples" / "projects" / "c162-inputs.json"
BOOK_LDG = dict(clmax=2.029, cl_ldg=0.5, cd_ldg=0.07, mu=0.3, free_roll_s=1.0)


class LandingTests(unittest.TestCase):
    def test_step_8_distance_at_book_wing_loading(self):
        # The book reports that 1369 ft is met for W/S < 11.37 lbf/ft^2 (STEP 8).
        s = landing_distance_ft(11.37, RHO_BOOK, h_obst_ft=50.0, **BOOK_LDG)
        self.assertAlmostEqual(s, 1369.0, delta=1.0)

    def test_step_8_inverse(self):
        ws = max_wing_loading_for_landing_pa(1369.0 / FT_PER_M, RHO_BOOK * KGM3_PER_SLUGFT3, h_obst_m=50.0 / FT_PER_M,
                                             **BOOK_LDG) / PA_PER_LBF_FT2
        self.assertAlmostEqual(ws, 11.37, delta=0.01)

    def test_ground_roll_is_shorter_by_obstacle_phase(self):
        total = landing_distance_ft(11.0, RHO_BOOK, h_obst_ft=50.0, **BOOK_LDG)
        roll = landing_distance_ft(11.0, RHO_BOOK, h_obst_ft=50.0, ground_roll_only=True, **BOOK_LDG)
        # Eq. 3-13 minus Eq. 3-14 = 19.08 h_obst + (0.007923 - 0.01583)(W/S)/A (the flare is counted in the roll)
        a = RHO_BOOK * 2.029
        self.assertAlmostEqual(total - roll, 19.08 * 50.0 + (0.007923 - 0.01583) * 11.0 / a, places=6)
        self.assertLess(roll, total)

    def test_monotonic_in_wing_loading_and_si_wrapper(self):
        ws = [300.0, 400.0, 500.0, 600.0]
        d = [landing_distance_m(w, 1.225, h_obst_m=15.24, **BOOK_LDG) for w in ws]
        self.assertEqual(d, sorted(d))
        self.assertAlmostEqual(landing_distance_m(11.37 * PA_PER_LBF_FT2, RHO_BOOK * KGM3_PER_SLUGFT3,
                                                  h_obst_m=15.24, **BOOK_LDG) * FT_PER_M, 1369.0, delta=1.5)

    def test_invalid_braking_rejected(self):
        with self.assertRaises(ValueError):
            landing_distance_ft(11.0, RHO_BOOK, 2.029, 0.5, 0.07, -0.5, 1.0, 50.0)

    def test_takeoff_equation_3_1_step_3(self):
        # STEP 3: T/W = 0.1869 at W/S = 10 lbf/ft^2 (CLmax 1.756, S_G 640 ft, CD_TO 0.038, CL_TO 0.5, mu 0.04)
        self.assertAlmostEqual(takeoff_tw_book(10.0, RHO_BOOK, 1.756, 0.5, 0.038, 0.04, 640.0), 0.1869, delta=0.0001)


def standalone_inputs(tmp: Path) -> Path:
    """Example inputs without the M06 link (M04 alone, MTOW taken from the concept)."""
    data = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    data["m04"]["tow_from_m06"] = False
    out = tmp / "inputs.json"
    out.write_text(json.dumps(data), encoding="utf-8")
    return out


class M04ProjectTests(unittest.TestCase):
    def test_cli_example_3_1_with_landing_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.json"
            main(["project-init", "--project", str(path), "--name", "c162", "--from-inputs",
                  str(standalone_inputs(Path(tmp)))])
            main(["m04", "--project", str(path)])
            r = prj.load(path)["outputs"]["m04"]["result"]
        # Stall limit (45 KCAS, CLmax 1.68) 551.5 Pa; landing limit 11.37 lbf/ft^2 = 544 Pa (ISA rho 1.225 vs 1.2255 book)
        self.assertAlmostEqual(r["wingloading_limits_pa"]["stall"], 551.5, delta=0.5)
        self.assertAlmostEqual(r["landing"]["max_wingloading_lbf_ft2"], 11.37, delta=0.02)
        self.assertEqual(r["wingloading_limit_active"], "landing")
        self.assertLessEqual(r["best_sample"]["wingloading_pa"], r["wingloading_limits_pa"]["landing"])
        self.assertAlmostEqual(r["landing"]["check_distance_m"] * FT_PER_M, 1369.0, delta=0.5)
        self.assertEqual(r["constraints_evaluated"], ["takeoff", "climb", "cruise", "ceiling", "turn"])

    def test_adrpy_vs_book_tolerances_at_10_lbf_ft2(self):
        """Documented tolerances (TEST_RESULTS 8.4): ADRpy 0.2.6 vs the book's local T/W at W/S = 10 lbf/ft^2.

        Causes of the differences are in TEST_RESULTS section 2.3 (k, take-off formulation, ceiling altitude)."""
        from aerosuite.adrpy_core import evaluate, load_concept
        doc = load_concept(Path(__file__).parents[1] / "examples" / "gudmundsson-ex3-1-c162.json")
        ws = 10.0 * PA_PER_LBF_FT2
        local = evaluate(doc, ws, map2sl=False)["by_constraint"]
        book = {"takeoff": 0.1869, "climb": 0.2140, "turn": 0.1245, "cruise": 0.1192, "ceiling": 0.09429}
        tol = {"takeoff": 0.07, "climb": 0.01, "turn": 0.01, "cruise": 0.01, "ceiling": 0.03}
        for name, value in book.items():
            self.assertLess(abs(local[name] / value - 1.0), tol[name], msg=f"{name}: {local[name]} vs {value}")

    def test_missing_landing_keys(self):
        data = json.loads(EXAMPLES.read_text(encoding="utf-8"))
        data["m04"]["tow_from_m06"] = False
        data["m04"]["landing"].pop("cd_ldg")
        p = prj.new_project("x")
        p["inputs"] = data
        from aerosuite import m04_constraints
        with self.assertRaises(SystemExit):
            m04_constraints.run(p)


if __name__ == "__main__":
    unittest.main()

