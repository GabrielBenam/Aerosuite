"""Tests for the flow5 result reader (M-F5R).

The fixtures below are FORMAT FIXTURES: they reproduce, character for character
where it matters, what flow5 v7.57 writes in PlanePolar::exportToString and
PlaneOpp::exportMainDataToString (vendor/flow5, see aerosuite/flow5_results.py).
Their numbers are simple analytic values chosen to check parsing and fitting;
they are NOT aerodynamic results and must never be used as such.
"""
import tempfile
import unittest
from pathlib import Path

from aerosuite.flow5_results import (collect, detect_separator, fit_drag_polar, lift_slope,
                                     parse_plane_opp, parse_plane_polar, split_label, static_margin)

NAMES = ["Ctrl", "α (°)", "β (°)", "φ (°)", "CL", "CD", "CD_viscous", "CD_induced", "CY", "Cm", "Cm_viscous",
         "Cm_pressure", "Cl", "Cn", "Cn_viscous", "Cn_pressure", "CL/CD", "CL^(3/2)/CD", "1/sqrt(CL)",
         "Lift ({f})", "Drag ({f})", "Fx_FF_wind ({f})", "Fy_FF_wind ({f})", "Fz_FF_wind ({f})",
         "Fx_sum_wind ({f})", "Fy_sum_wind ({f})", "Fz_sum_wind ({f})", "Extra drag ({f})", "Fuse drag ({f})",
         "Cf_Fuse", "Vx ({v})", "Vz ({v})", "V ({v})", "Gamma", "L ({mo})", "M ({mo})", "N ({mo})",
         "CPx ({l})", "CPy ({l})", "CPz ({l})", "BM ({mo})", "m.g.Vz (W)", "Drag x V (W)", "Efficiency",
         "XCp.Cl", "XNP ({l})", "Phugoid Freq. (Hz)", "Phugoid Damping", "Short Period Freq. (Hz)",
         "Short Period Damping Ratio", "Dutch Roll Freq. (Hz)", "Dutch Roll Damping", "Roll Damping",
         "Spiral Damping", "Mass ({ma})", "CoG_x ({l})", "CoG_z ({l})"]


def polar_text(sep=", ", units=None, condition=True):
    u = units or {"f": "N", "v": "m/s", "mo": "N.m", "l": "m", "ma": "kg"}
    names = [n.format(**u) for n in NAMES]
    out = ["Type 1: Fixed speed", "Nbr. of data points = 5", "V∞ = 56m/s", "", "Plane A", "T1-VLM2", ]
    out.append(("Freestream speed = 55.600 " + u["v"] + "\n\n") if condition else "\n")
    header = ""
    for i, n in enumerate(names):
        s = (" " + n) if i == 0 else n
        header += s.ljust(11) + sep
    out.append(header)
    for alpha in (-2, 0, 2, 4, 6):
        cl = 0.2 + 0.08 * alpha
        cd = 0.02 + 0.05 * cl * cl
        vals = [0.0] * len(names)
        vals[1], vals[4], vals[5], vals[9] = alpha, cl, cd, 0.01 - 0.12 * cl
        vals[19] = 1000.0 * cl
        vals[32] = 55.6 if u["v"] == "m/s" else 55.6 / 0.514444
        vals[45], vals[55] = 0.52, 0.40
        vals[54] = 600.0
        out.append("".join(f"{v:11.5g}" + sep for v in vals))
    return "\n".join(out) + "\n"


OPP = """Plane A
T1-VLM2

                α,                 β,                 φ,              ctrl, ,  VInf(m/s)
                4,                 0,                 0,                 0,              55.6

               CL,                CX,                CY,       CD_inviscid,        CD_viscous,                Cl,       Cm_inviscid,        Cm_viscous,       Cn_inviscid,        Cn_viscous
             0.52,           0.0335,                 0,             0.012,            0.0215,                 0,           -0.0524,            -0.004,                 0,                 0

          CP.x(m),           CP.y(m),           CP.z(m),           NP.x(m),
             0.31,                 0,             0.01,              0.52,

          mass(kg),          CoG.x(m),          CoG.y(m),          CoG.z(m),    CoG_Ixx(kg.m²),    CoG_Iyy(kg.m²),    CoG_Izz(kg.m²),    CoG_Ixz(kg.m²),               600,               0.4,                 0,                 0,               900,               700,              1500,                10

              CXu,               CZu,               Cmu,               CXa,               CZa,               Cma,               CXq,               CZq,               Cmq,
           -0.067,             -1.04,                 0,             0.312,             -4.98,             -0.62,                 0,             -7.2,             -12.1,

              Cyb,               Clb,               Cnb,               Cyp,               Clp,               Cnp,               Cyr,               Clr,               Cnr,
            -0.31,            -0.045,             0.061,                 0,             -0.47,            -0.036,               0.2,              0.11,            -0.081,

  Elevator
              CXd,               CYd,               CZd,               Cld,               Cmd,               Cnd,
            0.001,                 0,             -0.41,                 0,              -1.3,                 0,



Main wing
y(m), Re, Ai, Cd_i, Cd_v, Cl, CP.x(%), Trans.top, Trans.bot, Cm_i, Cm_v, Bending.mom, Vd.x, Vd.y, Vd.z, F.x, F.y, F.z, Γ
                0,         4.6e+06,              -1.2,             0.009,            0.0062,              0.58,                26,              0.35,                 1,            -0.052,                 0,              1890,                 0,                 0,             -1.1,                 0,                 0,              0.6,               1.2,
             2.36,         4.4e+06,              -1.1,            0.0085,            0.0061,              0.55,                26,              0.37,                 1,            -0.052,                 0,               540,                 0,                 0,             -1.0,                 0,                 0,             0.55,               1.1,
             4.65,         4.2e+06,              -1.6,             0.012,            0.0065,              0.40,                26,              0.40,                 1,            -0.051,                 0,                 0,                 0,                 0,             -1.4,                 0,                 0,              0.4,               0.8,

"""


class Flow5ResultsTests(unittest.TestCase):
    def write(self, tmp, name, text):
        p = Path(tmp) / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def test_labels_and_separator(self):
        self.assertEqual(split_label("Lift (lbf)"), ("Lift", "lbf"))
        self.assertEqual(split_label("CP.x(m)"), ("CP.x", "m"))
        self.assertEqual(detect_separator(polar_text()), ",")
        self.assertIsNone(detect_separator(polar_text(sep="  ")))

    def test_polar_csv_si(self):
        with tempfile.TemporaryDirectory() as tmp:
            pol = parse_plane_polar(self.write(tmp, "A/T1.csv", polar_text()))
            self.assertEqual((pol.plane, pol.polar), ("Plane A", "T1-VLM2"))
            self.assertTrue(pol.condition_line.startswith("Freestream speed"))
            self.assertEqual(pol.polar_type, "Type 1: Fixed speed")
            self.assertEqual(len(pol.rows), 5)
            self.assertEqual(len(pol.columns), 57)
            self.assertAlmostEqual(pol.rows[1]["CL"], 0.2)
            self.assertIn("Cl_roll", pol.rows[0])
            self.assertEqual(pol.unconverted, [])

    def test_polar_txt_and_imperial_units(self):
        units = {"f": "lbf", "v": "kt", "mo": "lbf.ft", "l": "ft", "ma": "lb"}
        with tempfile.TemporaryDirectory() as tmp:
            pol = parse_plane_polar(self.write(tmp, "A/T1.txt", polar_text(sep="  ", units=units)))
            # flow5 writes 5 significant digits ({:11.5g}): 108.08 kt -> 55.601 m/s
            self.assertAlmostEqual(pol.rows[0]["V_mps"], 55.6, places=2)
            self.assertAlmostEqual(pol.rows[0]["lift_N"], 1000 * 0.04 * 4.44822, places=3)
            self.assertAlmostEqual(pol.rows[0]["XNP_m"], 0.52 * 0.3048, places=6)
            self.assertAlmostEqual(pol.rows[0]["mass_kg"], 600 * 0.45359237, places=3)

    def test_polar_without_condition_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            pol = parse_plane_polar(self.write(tmp, "A/T2.csv", polar_text(condition=False)))
            self.assertEqual((pol.plane, pol.polar, pol.condition_line), ("Plane A", "T1-VLM2", ""))

    def test_derived_quantities(self):
        with tempfile.TemporaryDirectory() as tmp:
            pol = parse_plane_polar(self.write(tmp, "A/T1.csv", polar_text()))
            fit = fit_drag_polar(pol)
            self.assertAlmostEqual(fit["model_simplified"]["CD0"], 0.02, places=6)
            self.assertAlmostEqual(fit["model_simplified"]["k"], 0.05, places=6)
            self.assertAlmostEqual(fit["model_adjusted"]["CL_minD"], 0.0, places=5)
            ls = lift_slope(pol, -2, 6)
            self.assertAlmostEqual(ls["CL_alpha_per_deg"], 0.08, places=6)
            self.assertAlmostEqual(ls["alpha_zero_lift_deg"], -2.5, places=6)
            sm = static_margin(pol, mac_m=1.18)
            self.assertAlmostEqual(sm["from_dCm_dCL"]["static_margin"], 0.12, places=6)
            self.assertAlmostEqual(sm["from_XNP"]["static_margin_mean"], 0.12 / 1.18, places=6)
            with self.assertRaises(ValueError):
                fit_drag_polar(pol, cl_min=0.6)

    def test_operating_point(self):
        with tempfile.TemporaryDirectory() as tmp:
            opp = parse_plane_opp(self.write(tmp, "A/T1-VLM2/a4.csv", OPP))
            s = opp.scalars
            self.assertEqual((opp.plane, opp.polar), ("Plane A", "T1-VLM2"))
            self.assertAlmostEqual(s["alpha_deg"], 4)
            self.assertAlmostEqual(s["V_mps"], 55.6)
            self.assertAlmostEqual(s["CD"], 0.0335)
            self.assertAlmostEqual(s["XNP_m"], 0.52)
            self.assertAlmostEqual(s["mass_kg"], 600)
            self.assertAlmostEqual(s["Ixz_kgm2"], 10)
            self.assertAlmostEqual(opp.derivatives["Cma"], -0.62)
            self.assertAlmostEqual(opp.derivatives["Cnr"], -0.081)
            self.assertAlmostEqual(opp.control_derivatives["Elevator"]["Cmd"], -1.3)
            wing = opp.span["Main wing"]
            self.assertEqual(len(wing["rows"]), 3)
            self.assertAlmostEqual(wing["rows"][1]["y_m"], 2.36)
            self.assertAlmostEqual(wing["rows"][0]["Cl"], 0.58)

    def test_collect_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, "out/Plane A/T1-VLM2.csv", polar_text())
            self.write(tmp, "out/Plane A/T1-VLM2/a4.csv", OPP)
            self.write(tmp, "out/Plane A/broken.csv", "not a flow5 file\n")
            data = collect(Path(tmp) / "out")
            self.assertEqual(len(data["polars"]), 1)
            self.assertEqual(len(data["operating_points"]), 1)
            self.assertEqual(len(data["errors"]), 1)


if __name__ == "__main__":
    unittest.main()
