"""M09a tests: decision-matrix scoring (GUD Sec. 8.3.9 example), polar metrics (algorithm fixtures, NOT aerodynamic data)
and, when an XFOIL executable is available, a real 2-D run checked against thin-airfoil theory (independent source)."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from aerosuite import engines, project as prj
from aerosuite.__main__ import main
from aerosuite import m09a_airfoils as m
from aerosuite.airfoils import naca4

XFOIL = engines.xfoil_executable()


class ScoringTests(unittest.TestCase):
    def test_book_prorated_thickness_example(self):
        # GUD Sec. 8.3.9 (10): t/c 0.10, 0.12, 0.14, 0.16 score 0, 0.333, 0.667, 1.
        table = {n: {"thickness_ratio": t} for n, t in (("a", 0.10), ("b", 0.12), ("c", 0.14), ("d", 0.16))}
        r = m.score_matrix(table, weights={c: 0.0 for c in m.CRITERIA if c != "thickness_ratio"})
        self.assertEqual(r["criteria_used"], ["thickness_ratio"])
        for n, expect in (("a", 0.0), ("b", 1 / 3), ("c", 2 / 3), ("d", 1.0)):
            self.assertAlmostEqual(r["scores"][n]["thickness_ratio"], expect, places=9)
        self.assertEqual(r["ranking"][0], "d")

    def test_direction_weights_and_manual_scores(self):
        table = {"x": {"clmax": 1.5, "cd_at_cruise_cl": 0.006}, "y": {"clmax": 1.7, "cd_at_cruise_cl": 0.008}}
        only = {c: 0.0 for c in m.CRITERIA}
        r = m.score_matrix(table, {**only, "clmax": 3.0, "cd_at_cruise_cl": 1.0})
        self.assertAlmostEqual(r["totals"]["x"], 1.0)    # best drag: 1 x weight 1; worst Cl_max: 0
        self.assertAlmostEqual(r["totals"]["y"], 3.0)    # best Cl_max: 1 x weight 3 (book: "max score 3 for Cl_max")
        r2 = m.score_matrix(table, {**only, "clmax": 3.0, "cd_at_cruise_cl": 1.0}, manual={"x": {"contamination": 2.5}})
        self.assertAlmostEqual(r2["totals"]["x"], 3.5)
        self.assertEqual(r2["ranking"][0], "x")

    def test_missing_data_drops_criterion(self):
        table = {"x": {"clmax": 1.5, "stall_cl_drop": None}, "y": {"clmax": 1.7, "stall_cl_drop": 0.1}}
        r = m.score_matrix(table, {c: 0.0 for c in m.CRITERIA if c not in ("clmax", "stall_cl_drop")})
        self.assertEqual(r["criteria_used"], ["clmax"])
        self.assertEqual(r["criteria_dropped_missing_data"], {"stall_cl_drop": ["x"]})


class MetricsTests(unittest.TestCase):
    """Format/algorithm fixture: an analytic parabolic polar, not aerodynamic data."""

    def rows(self):
        out = []
        for a in range(-4, 21):
            cl = 0.1 * (a + 2.0) if a <= 14 else 1.6 - 0.05 * (a - 14)
            out.append({"alpha": float(a), "cl": cl, "cd": 0.006 + 0.01 * (cl - 0.4) ** 2, "cm": -0.05})
        return out

    def test_extraction(self):
        r = m.polar_metrics(self.rows(), cl_cruise=0.5)
        self.assertAlmostEqual(r["clmax"], 1.6)
        self.assertEqual(r["alpha_clmax_deg"], 14.0)
        self.assertAlmostEqual(r["cl_alpha_per_rad"], 0.1 * 180 / math.pi, places=6)
        self.assertAlmostEqual(r["alpha_zero_lift_deg"], -2.0, places=6)
        self.assertAlmostEqual(r["alpha_cruise_deg"], 3.0, places=6)          # Cl = 0.1 (a + 2)
        self.assertAlmostEqual(r["cl_at_cdmin"], 0.4)
        self.assertAlmostEqual(r["stall_cl_drop"], 0.1)                       # 1.6 -> 1.5 at +2 deg
        self.assertTrue(r["stall_reached_in_sweep"])
        self.assertEqual(r["ld_max"], round(r["ld_max_unrounded"]))

    def test_no_stall_drop_without_sweep_beyond_stall(self):
        rows = [r for r in self.rows() if r["alpha"] <= 15]
        self.assertIsNone(m.polar_metrics(rows, 0.5)["stall_cl_drop"])

    def test_geometry_stats_naca(self):
        g = m.geometry_stats(naca4("2412", 161))
        self.assertAlmostEqual(g["thickness_ratio"], 0.12, delta=0.002)
        self.assertAlmostEqual(g["camber_ratio"], 0.02, delta=0.002)
        self.assertAlmostEqual(g["camber_position"], 0.4, delta=0.03)


def thin_airfoil_alpha_zero_lift_deg(code: str, n: int = 4000) -> float:
    """Thin-airfoil theory (Glauert): alpha_L0 = -(1/pi) integral_0^pi (dz/dx)(cos(theta) - 1) dtheta, NACA 4-digit camber line."""
    mm, p = int(code[0]) / 100, int(code[1]) / 10
    total = 0.0
    for i in range(n):
        th = math.pi * (i + 0.5) / n
        x = (1 - math.cos(th)) / 2
        dz = 0.0 if mm == 0 else (2 * mm / p ** 2 * (p - x) if x < p else 2 * mm / (1 - p) ** 2 * (p - x))
        total += dz * (math.cos(th) - 1.0) * (math.pi / n)
    return math.degrees(-total / math.pi)


@unittest.skipUnless(XFOIL, "XFOIL executable not available: real-engine test skipped")
class RealXfoilTests(unittest.TestCase):
    def test_real_run_against_thin_airfoil_theory(self):
        inputs = {"m09a": {"candidates": {"naca4": ["0012", "2412"]},
                           "conditions": {"reynolds": 3e6, "mach": 0.0, "ncrit": 9, "alpha_start": -4, "alpha_end": 14,
                                          "alpha_step": 2, "from_zero": True},
                           "targets": {"cl_cruise": 0.3}}}
        with tempfile.TemporaryDirectory() as tmp:
            inputs["m09a"]["out_dir"] = str(Path(tmp) / "xf")
            src = Path(tmp) / "in.json"
            src.write_text(json.dumps(inputs), encoding="utf-8")
            path = Path(tmp) / "p.json"
            main(["project-init", "--project", str(path), "--name", "af", "--from-inputs", str(src)])
            main(["m09a", "--project", str(path)])
            r = prj.load(path)["outputs"]["m09a"]["result"]
            self.assertEqual(r["status"], "computed")
            for ident in ("naca0012", "naca2412"):
                met = r["metrics"][ident]
                self.assertAlmostEqual(met["cl_alpha_per_rad"] / (2 * math.pi), 1.0, delta=0.1)   # thin theory 2 pi
            self.assertAlmostEqual(r["metrics"]["naca0012"]["alpha_zero_lift_deg"], 0.0, delta=0.3)
            self.assertAlmostEqual(r["metrics"]["naca2412"]["alpha_zero_lift_deg"],
                                   thin_airfoil_alpha_zero_lift_deg("2412"), delta=0.4)
            self.assertEqual(len(r["decision_matrix"]["ranking"]), 2)
            self.assertIn("solver_sha256", r["xfoil_runs"]["naca2412"])
            self.assertIn("XFOIL", r["xfoil_runs"]["naca2412"]["solver"])
            # reuse of the real run (same conditions and geometry) must not call XFOIL again
            main(["m09a", "--project", str(path)])
            r2 = prj.load(path)["outputs"]["m09a"]["result"]
            self.assertTrue(r2["xfoil_runs"]["naca2412"]["reused_run"])

    def test_without_engine_declares_pending(self):
        import os
        old = os.environ.pop("AEROSUITE_XFOIL", None)
        try:
            from unittest import mock
            with mock.patch.object(engines, "xfoil_executable", return_value=None):
                p = prj.new_project("x")
                p["inputs"]["m09a"] = {"candidates": {"naca4": ["2412"]}, "conditions": {"reynolds": 1e6},
                                       "targets": {"cl_cruise": 0.3}}
                r = m.evaluate(p)
        finally:
            if old:
                os.environ["AEROSUITE_XFOIL"] = old
        self.assertEqual(r["status"], "pending_engine")
        self.assertNotIn("metrics", r)
        self.assertIn("naca2412", r["geometry"])


if __name__ == "__main__":
    unittest.main()
