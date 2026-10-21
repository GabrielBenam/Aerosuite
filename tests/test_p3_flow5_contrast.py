"""P-3 (F6): M16 dynamics and M19 spanwise distribution against REAL flow5 7.55 output (evidence/flow5-7.55-win). Nothing is tuned to flow5."""
import glob
import json
import math
import unittest
from pathlib import Path

import numpy as np

from aerosuite import m16_flow5_contrast as mc
from aerosuite import m19_stall as m19
from aerosuite.flow5_results import collect

EVID = Path(__file__).resolve().parents[1] / "evidence" / "flow5-7.55-win"
STAB = EVID / "stability-t7"
M19D = EVID / "m19-distribution"


@unittest.skipUnless((STAB / "job" / "flow5_results.json").is_file(), "stability evidence not present")
class M16DynamicsContrast(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cfg = json.loads((Path(__file__).resolve().parents[1] / "examples" / "flow5-c162-like-stability.json").read_text(encoding="utf-8"))
        res = json.loads((STAB / "job" / "flow5_results.json").read_text(encoding="utf-8"))
        log = Path(glob.glob(str(STAB / "job" / "output" / "*" / "*.log"))[0]).read_text(encoding="utf-8", errors="replace")
        cls.rep = mc.contrast(res["operating_points"][0], res["polars"][0]["rows"][0], cfg, log_text=log)

    def test_m16_matrices_with_flow5_derivatives_reproduce_flow5_modes(self):
        """Etkin's matrices (as in M16) fed with flow5's derivatives and inertia give flow5's own modes: checks the equations of motion."""
        a, f = self.rep["modes_flow5_derivatives_in_m16_matrices"], self.rep["modes_flow5"]
        for mode in ("phugoid", "short_period", "dutch_roll"):
            self.assertLess(abs(a[mode]["freq_Hz"] - f[mode]["freq_Hz"]) / f[mode]["freq_Hz"], 0.01, mode)
            self.assertLess(abs(a[mode]["zeta"] - f[mode]["zeta"]) / f[mode]["zeta"], 0.02, mode)
        self.assertAlmostEqual(a["spiral"]["t_half_s"], 229.8, delta=1.0)
        self.assertAlmostEqual(a["roll"]["eigenvalue"], -12.51, delta=0.02)

    def test_derivative_differences_are_reported_not_hidden(self):
        d = self.rep["derivatives"]
        self.assertAlmostEqual(d["Cz_u"]["flow5"], -2.0 * 0.324169, delta=2e-3)      # -2 CL from flow5's own state matrix
        self.assertLess(abs(d["Cx_u"]["rel_diff"]), 0.01)
        self.assertLess(abs(d["Cz_a"]["rel_diff"]), 0.05)
        self.assertLess(abs(d["Cm_q"]["rel_diff"]), 0.10)
        self.assertLess(abs(d["CY_b"]["rel_diff"]), 0.08)
        self.assertLess(abs(d["Cn_b"]["rel_diff"]), 0.08)
        self.assertGreater(d["Cm_a"]["rel_diff"], 0.2)        # M16 is less stable (static margin 7.9 % against 10.2 %): known, D-53
        self.assertGreater(d["Cz_q"]["rel_diff"], 0.3)        # M16 neglects the wing contribution to C_Zq (Sec. 24.2.5)

    def test_m16_lateral_modes_close_to_flow5(self):
        a, f = self.rep["modes_m16_with_flow5_lateral_derivatives"], self.rep["modes_flow5"]
        self.assertLess(abs(a["dutch_roll"]["freq_Hz"] - f["dutch_roll"]["freq_Hz"]) / f["dutch_roll"]["freq_Hz"], 0.03)
        self.assertLess(abs(a["dutch_roll"]["zeta"] - f["dutch_roll"]["zeta"]) / f["dutch_roll"]["zeta"], 0.03)

    def test_m16_short_period_degenerates_with_alpha_dot_terms(self):
        """With M16's own derivatives (including C_m_alpha_dot) the short period is two real roots; without the alpha_dot terms it is oscillatory."""
        eig = np.array(self.rep["longitudinal_eigenvalues_m16"])
        self.assertTrue(np.sum(np.abs(eig[:, 1]) < 1e-9) == 2)
        eig2 = np.array(self.rep["longitudinal_eigenvalues_m16_without_alpha_dot"])
        self.assertTrue(np.sum(np.abs(eig2[:, 1]) < 1e-9) == 0)


@unittest.skipUnless((M19D / "vlm2-ala-sola" / "output").is_dir(), "M19 distribution evidence not present")
class M19DistributionContrast(unittest.TestCase):
    HB, CR, CT = 4.72, 1.25, 1.11

    def solve(self, alpha_deg):
        azl = math.radians(m19.alpha_zl_naca4_deg("2412"))
        return m19.llt_solve(2 * self.HB, lambda e: self.CR + (self.CT - self.CR) * e, lambda e: 2 * math.pi, lambda e: azl,
                             lambda e: -math.radians(1.5) * e, math.radians(alpha_deg + 1.0))        # +1 deg wing tilt

    def test_vlm2_distribution_rms(self):
        d = collect(M19D / "vlm2-ala-sola" / "output")
        for o in d["operating_points"]:
            a = o["scalars"]["alpha_deg"]
            if a not in (0.0, 4.0, 10.0):
                continue
            rows = [r for r in o["span"]["Main wing"]["rows"] if r["y_m"] >= 0]
            sol = self.solve(a)
            diff = np.array([sol["cl_of"](min(r["y_m"] / self.HB, 1.0)) - r["Cl"] for r in rows])
            self.assertLess(float(np.sqrt(np.mean(diff ** 2))), 0.07, a)
            self.assertLess(abs(sol["cl_total"] / o["scalars"]["CL"] - 1.0), 0.06, a)

    def test_llt_stall_advance(self):
        d = collect(M19D / "llt-ala-sola" / "output")
        cm = {f["reynolds"]: max(r["CL"] for r in f["rows"]) for f in d["foil_polars"]}
        re_, c_ = np.array(sorted(cm)), np.array([cm[k] for k in sorted(cm)])
        last = max(d["operating_points"], key=lambda o: o["scalars"]["alpha_deg"])
        ratio = max(r["Cl"] / float(np.interp(r["Re"], re_, c_)) for r in last["span"]["Main wing"]["rows"] if r["y_m"] >= 0)
        self.assertGreater(ratio, 0.99)                    # flow5 LLT reaches C_lmax at alpha = 20 deg at the innermost station
        self.assertEqual(last["scalars"]["alpha_deg"], 20.0)
        cm_root, cm_tip = float(np.interp(3.8e6, re_, c_)), float(np.interp(3.4e6, re_, c_))
        azl = math.radians(m19.alpha_zl_naca4_deg("2412"))
        args = (2 * self.HB, lambda e: self.CR + (self.CT - self.CR) * e, lambda e: 2 * math.pi, lambda e: azl, lambda e: -math.radians(1.5) * e)
        first = m19.stall_progression(*args, lambda e: cm_root + (cm_tip - cm_root) * e, step_deg=0.25)["first"]
        self.assertLess(first["eta"], 0.2)                 # stall starts at the root, as in flow5
        self.assertAlmostEqual(first["alpha_deg"] - 1.0, 15.0, delta=0.6)      # 5 deg before flow5's linear-free LLT (about 20 deg)


if __name__ == "__main__":
    unittest.main()
