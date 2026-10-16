"""M16 tests. Dynamics: Etkin's Boeing 747 (Sec. 6.2 / 6.7, flight condition 2: M = 0.8, 40 000 ft) in English units, since the
matrix builders accept any coherent unit system. Statics: Gudmundsson Eqs. 24-91/24-132 and consistency identities.
The longitudinal Table 6.1 values are those of the converted text, except CZ_u = -1.416 (recovered from the printed A(2,1) = -0.09055;
the text shows 'CZ_u' unreadable) and CZ_alpha_dot = +5.896, the sign that reproduces the printed A(2,3) = 773.98 (the sign is not
legible in the converted text). The lateral Table 6.6 values are not in the converted text: they are checked because they reproduce the
printed eigenvalues. These are validation fixtures of published data, not aerodynamic results from AeroSuite."""
import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite import m16_stability as m

EXAMPLE = Path(__file__).parents[1] / "examples" / "projects" / "c172-like-stability-inputs.json"
B747_LONG = dict(u0=774.0, rho=0.0005909, S=5500.0, c=27.31, m=636636 / 32.174, Iy=0.331e8, g=32.174, Cx_u=-0.1080, Cx_a=0.2193,
                 Cz_u=-1.416, Cz_a=-4.920, Cz_q=-5.921, Cz_adot=5.896, Cm_u=0.1043, Cm_a=-1.023, Cm_q=-23.92, Cm_adot=-6.314)
B747_LAT = dict(u0=774.0, rho=0.0005909, S=5500.0, b=195.7, m=636636 / 32.174, Ix=0.183e8, Iz=0.497e8, Ixz=-0.156e7, g=32.174,
                CY_b=-0.8771, Cl_b=-0.2797, Cn_b=0.1946, CY_p=0.0, Cl_p=-0.3295, Cn_p=-0.04073, CY_r=0.0, Cl_r=0.304, Cn_r=-0.2737)


class EtkinB747Tests(unittest.TestCase):
    def test_longitudinal_matrix_entries_and_eigenvalues(self):
        a = m.longitudinal_matrix(B747_LONG)
        self.assertAlmostEqual(a[0, 0], -0.006868, delta=5e-6)       # printed A(1,1)
        self.assertAlmostEqual(a[0, 1], 0.01395, delta=1e-4)
        self.assertAlmostEqual(a[1, 0], -0.09055, delta=1e-4)
        self.assertAlmostEqual(a[1, 2], 773.98, delta=0.01)
        self.assertAlmostEqual(a[2, 2], -0.4285, delta=2e-3)
        c = m.classify_longitudinal(np.linalg.eigvals(a))
        self.assertAlmostEqual(c["phugoid"]["eigenvalue"][0], -0.003289, delta=1e-4)     # book -0.003289 +- 0.067231 i
        self.assertAlmostEqual(c["phugoid"]["eigenvalue"][1], 0.067231, delta=1e-4)
        self.assertAlmostEqual(c["short_period"]["eigenvalue"][0], -0.3719, delta=2e-3)  # book -0.3719 +- 0.8875 i
        self.assertAlmostEqual(c["short_period"]["eigenvalue"][1], 0.8875, delta=2e-3)

    def test_lateral_eigenvalues(self):
        c = m.classify_lateral(np.linalg.eigvals(m.lateral_matrix(B747_LAT)))
        self.assertAlmostEqual(c["spiral"]["eigenvalue"], -0.0072973, delta=1e-4)
        self.assertAlmostEqual(c["roll"]["eigenvalue"], -0.56248, delta=3e-3)
        self.assertAlmostEqual(c["dutch_roll"]["eigenvalue"][0], -0.033011, delta=1e-4)
        self.assertAlmostEqual(c["dutch_roll"]["eigenvalue"][1], 0.94655, delta=1e-3)
        self.assertAlmostEqual(c["dutch_roll"]["period_s"], 6.64, delta=0.02)               # Table in Sec. 6.7

    def test_lanchester_b747(self):
        self.assertAlmostEqual(m.lanchester(235.9, 17.0)["period_s"], 107.0, delta=1.0)           # Sec. 6.3 (u0 = 235.9 m/s)


class StaticTests(unittest.TestCase):
    def test_downwash_gradient(self):
        self.assertAlmostEqual(m.downwash_gradient(math.pi * 2.0, 8.0), 2 * 2 * math.pi / (math.pi * 8.0)) 

    def test_neutral_point_and_cm_alpha_consistency(self):
        args = dict(cl_alpha_w=4.8, cl_alpha_ht=3.6, ar_w=7.5, v_ht=0.7)
        hn = m.neutral_point(**args)["h_n"]
        self.assertAlmostEqual(m.cm_alpha(**args, h_cg=hn), 0.0, places=12)                  # CM_alpha = 0 at the neutral point
        h_cg = 0.3
        self.assertAlmostEqual(m.cm_alpha(**args, h_cg=h_cg), -4.8 * (hn - h_cg), places=12)  # CM_alpha = -CL_alpha_W SM

    def test_cg_limits(self):
        lim = m.cg_limits(0.55)
        self.assertAlmostEqual(lim["aft_h"], 0.45)
        self.assertAlmostEqual(lim["forward_h"], 0.25)

    def test_vertical_tail_formulas(self):
        self.assertEqual(m.k_yvt(1.0), 0.76)
        self.assertEqual(m.k_yvt(4.0), 1.0)
        self.assertAlmostEqual(m.k_yvt(2.0), 0.76)
        sw = m.sidewash_factor(0.1, 0.0, 0.0, 8.0)
        self.assertAlmostEqual(sw, 0.724 + 3.06 * 0.1 / 2.0 + 0.009 * 8.0)
        self.assertAlmostEqual(m.cn_beta_vt(3.0, 1.0, 5.0, 10.0, 8.0, 1.0), 3.0 * 5.0 / 80.0)

    def test_fuselage_munk_sign(self):
        self.assertLess(m.cn_beta_fuselage([0, 4, 8], [0.5, 1.2, 0.5], 8.0, 1.2, 16.0, 11.0), 0.0)


class ProjectTests(unittest.TestCase):
    def build(self, tmp, mutate=None):
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        if mutate:
            mutate(data)
        src = Path(tmp) / "in.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        path = Path(tmp) / "p.json"
        main(["project-init", "--project", str(path), "--name", "s", "--from-inputs", str(src)])
        for mod in ("m09b", "m08", "m10", "m12", "m13", "m16"):
            main([mod, "--project", str(path)])
        return path

    def test_chain_and_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.build(tmp)
            data = prj.load(path)
            r = data["outputs"]["m16"]["result"]
            ls = r["longitudinal_static"]
            self.assertAlmostEqual(ls["static_margin"], ls["h_n"] - ls["h_cg"])
            self.assertAlmostEqual(ls["cm_alpha_per_rad"], -ls["cl_alpha_wing_per_rad"] * ls["static_margin"], places=9)
            self.assertTrue(ls["stable"])
            self.assertEqual(sorted(data["outputs"]["m16"]["run"]["depends_on"]), ["m08", "m09b", "m13"])
            self.assertEqual(prj.stale(data), [])
            self.assertIn("phugoid", r["longitudinal_dynamics"])
            self.assertIn("status", r["lateral_dynamics"])                   # no derivatives given: not invented
            self.assertTrue(all(isinstance(x, str) for x in r["assumptions"]))
            data["outputs"]["m13"]["result"]["total_mass_kg"] += 1.0
            self.assertIn("m16", prj.stale(data))
            out = Path(tmp) / "m16.json"
            main(["export", "--project", str(path), "--module", "m16", "--out", str(out)])
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["module"], "m16")

    def test_lateral_derivatives_input_gives_modes(self):
        def add(d):
            d["m16"]["lateral_derivatives"] = {k: B747_LAT[k] for k in ("Cl_b", "Cl_p", "Cn_p", "Cl_r", "Cn_r")}
            d["m16"]["lateral_derivatives_origin"] = "test fixture (Etkin B747 coefficients, not for this airplane)"
        with tempfile.TemporaryDirectory() as tmp:
            r = prj.load(self.build(tmp, add))["outputs"]["m16"]["result"]["lateral_dynamics"]
            self.assertIn("dutch_roll", r)
            self.assertIn("spiral", r)


if __name__ == "__main__":
    unittest.main()
