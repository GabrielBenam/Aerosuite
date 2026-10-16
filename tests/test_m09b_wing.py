"""M09b tests against Gudmundsson Chapter 9 (Examples 9-3, 9-4, 9-9; Table 9-7; Eq. 9-129)."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from aerosuite import flow5_xml, project as prj
from aerosuite.__main__ import main
from aerosuite import m09b_wing as w

FT = 0.3048
C162 = Path(__file__).parents[1] / "examples" / "projects" / "c162-inputs.json"


class PlanformTests(unittest.TestCase):
    def test_example_9_3_planform(self):
        # S = 130 ft^2, lambda = 0.5, AR = 8 -> b = 32.25 ft, c_r = 5.375 ft, c_t = 2.687 ft (GUD PDF 375)
        pf = w.planform(130.0, 8.0, 0.5, sweep_c4_deg=0.0)
        self.assertAlmostEqual(pf["span_m"], 32.25, delta=0.01)
        self.assertAlmostEqual(pf["root_chord_m"], 5.375, delta=0.001)
        self.assertAlmostEqual(pf["tip_chord_m"], 2.687, delta=0.001)

    def test_sweep_conversion_matches_geometry(self):
        # Eq. 9-16 against the planform geometry: x_LE(y) = y tan L_LE, x_c4(y) = x_LE(y) + (c(y) - c_r)/4
        ar, lam, le = 8.0, 0.5, 12.0
        pf = w.planform(20.0, ar, lam, sweep_le_deg=le)
        half = pf["span_m"] / 2.0
        x_c4_tip = pf["tip_xoffset_m"] + (pf["tip_chord_m"] - pf["root_chord_m"]) / 4.0
        self.assertAlmostEqual(math.degrees(math.atan(x_c4_tip / half)), pf["sweep_c4_deg"], places=9)
        x_c2_tip = pf["tip_xoffset_m"] + (pf["tip_chord_m"] - pf["root_chord_m"]) / 2.0
        self.assertAlmostEqual(math.degrees(math.atan(x_c2_tip / half)), pf["sweep_c2_deg"], places=9)
        back = w.sweeps(ar, lam, sweep_c4_deg=pf["sweep_c4_deg"])
        self.assertAlmostEqual(back["sweep_le_deg"], le, places=9)
        self.assertAlmostEqual(pf["xmgc_le_m"], pf["ymgc_m"] * math.tan(math.radians(le)))     # Eq. 9-14

    def test_rectangular_wing_has_no_sweep_shift(self):
        s = w.sweeps(8.0, 1.0, sweep_le_deg=0.0)
        self.assertEqual((s["sweep_c4_deg"], s["sweep_c2_deg"]), (0.0, 0.0))

    def test_guidance_flags(self):
        pf = w.planform(16.0, 8.0, 0.25, sweep_c4_deg=0.0)
        g = {n["item"]: n for n in w.guidance(pf, "general_aviation", 2.0, 0.0)}
        self.assertFalse(g["taper_ratio"]["inside"])        # avoid lambda < 0.3 (GUD 9.3.2)
        self.assertTrue(g["aspect_ratio"]["inside"])        # Table 9-4: GA 6-11
        self.assertFalse(g["dihedral_deg"]["inside"])


class LiftTests(unittest.TestCase):
    # Table 9-7 (GUD PDF 413-414): AR, mid-chord sweep, Eq. 9-69, Eq. 9-71, Eq. 9-72 (per radian). kappa = 5.9 / 2 pi (Fig. 8-5).
    TABLE_9_7 = [(10, 0.00, 5.24, 5.15, 4.90), (10, 6.60, 5.24, 5.15, 4.87), (10, 22.48, 5.24, 5.15, 4.59),
                 (10, 28.55, 5.24, 5.15, 4.40), (10, 32.78, 5.24, 5.15, 4.24), (2.27, 38.59, 3.34, 2.84, 2.51),
                 (2.26, 45.08, 3.33, 2.83, 2.39), (1.29, 0.00, 2.46, 1.85, 1.83)]

    def test_table_9_7(self):
        for ar, lam2, e69, e71, e72 in self.TABLE_9_7:
            self.assertAlmostEqual(w.cl_alpha_elliptic(ar), e69, delta=0.006, msg=f"9-69 AR {ar}")
            self.assertAlmostEqual(w.cl_alpha_helmbold(ar), e71, delta=0.006, msg=f"9-71 AR {ar}")
            self.assertAlmostEqual(w.cl_alpha_polhamus(ar, lam2, 0.0, 5.9), e72, delta=0.006, msg=f"9-72 AR {ar} L {lam2}")

    def test_limits(self):
        with self.assertRaises(ValueError):
            w.cl_alpha_polhamus(8.0, 0.0, 0.9)
        self.assertAlmostEqual(w.cl_alpha_elliptic(1e9), 2 * math.pi, places=4)   # AR -> infinity recovers the airfoil slope
        self.assertGreater(w.cl_alpha_polhamus(8.0, 0.0, 0.5, 6.0), w.cl_alpha_polhamus(8.0, 0.0, 0.0, 6.0))
        self.assertGreater(w.cl_alpha_helmbold(8.0, 6.28), w.cl_alpha_helmbold(8.0, 5.5))

    def test_example_9_9_clmax_and_stall_speed(self):
        # Cessna 172: NACA 2412 root and tip, Cl_max 1.58 at Re 3.1e6 -> CL_max0 = 0.9 (1.58) = 1.422 (POH 1.54)
        r = w.clmax0_rapid(1.58, 1.58, 1.0, 6.0)
        self.assertAlmostEqual(r["clmax0"], 1.422, places=3)
        self.assertAlmostEqual((1.54 - r["clmax0"]) / 1.54, 0.08, delta=0.005)             # "8 % less" in the book
        # POH: W = 2550 lbf, S = 174 ft^2, V_S = 53 KCAS at CL_max0 = 1.54 (rho = 0.002378 slug/ft^3)
        ws = 2550.0 / 174.0 * 47.88025898
        vs = w.stall_speed_mps(ws, 0.002378 * 515.378819, 1.54)
        self.assertAlmostEqual(vs / 0.514444, 53.0, delta=0.3)
        r2 = w.clmax0_rapid(1.6, 1.2, 1.5, 10.0)
        self.assertAlmostEqual(r2["clmax_airfoil_at_mgc"], 1.6 + 2 * 1.5 / 10.0 * (1.2 - 1.6))


class EfficiencyAndVolumeTests(unittest.TestCase):
    def test_oswald_eq_9_129(self):
        self.assertAlmostEqual(w.oswald_straight(10.0), 0.7566, delta=0.0001)             # Example 9-4
        # Example 3-1 (AR = 8): e = 0.8106 and k = 1/(pi AR e) = 0.04909 (GUD PDF 109-113)
        self.assertAlmostEqual(w.oswald_straight(8.0), 0.8106, delta=0.0001)
        self.assertAlmostEqual(1.0 / (math.pi * 8.0 * w.oswald_straight(8.0)), 0.04909, delta=0.00002)
        with self.assertRaises(ValueError):
            w.oswald_straight(3.0)

    def test_example_9_4_effective_aspect_ratio(self):
        r = w.effective_ar_for_range(0.2864, 0.02541, 900.0, 3379.0, 2910.0, True, 0.4586, 0.85)
        self.assertAlmostEqual(r["A"], 0.02872, delta=0.00001)                             # book 0.02872
        self.assertAlmostEqual(r["effective_aspect_ratio"], 7.893, delta=0.03)             # book 7.893 (rounded A)
        self.assertAlmostEqual(r["cl_cruise_limit"], 0.2533, delta=0.0001)                 # Eq. 9-40, book 0.2533
        low = w.effective_ar_for_range(0.2, 0.02541, 900.0, 3379.0, 2910.0, True, 0.4586, 0.85)
        self.assertFalse(low["feasible"])                                                  # CL below the Eq. 9-40 limit

    def test_wing_volume_integration(self):
        # Example 9-3 inputs: stations y = 5 and 10 ft, c = 4.542 and 3.708 ft, t/c = 0.15, k = 0.3
        v = w.wing_volume_m3(4.542 * FT, 3.708 * FT, 5 * FT, 10 * FT, 0.15, 0.3) / FT ** 3
        n = 20000
        quad = sum((0.3 + 3) / 6 * 0.15 * (4.542 + (3.708 - 4.542) * (i + 0.5) / n) ** 2 * (5.0 / n) for i in range(n))
        self.assertAlmostEqual(v, quad, places=6)                                           # exact integral vs quadrature
        self.assertAlmostEqual(v, 7.04, delta=0.01)
        # The book prints 10.16 ft^3: its constants A = 28.89 and B = 1.792 use c_r = 5.375 ft where Eq. 9-36 needs the
        # chord at y = b1 (4.542 ft). Reproducing the printed numbers shows the example, not the equation, is inconsistent.
        printed = 0.55 * 0.15 * (28.89 * 5 - 0.5 * 1.792 * 25 + 0.02778 * 125 / 3)
        self.assertAlmostEqual(printed, 10.16, delta=0.01)
        # Fuel from the book's volume (usable 30 %, 2 wing halves): 45.62 US gal and 273.7 lbf of Avgas (6 lbf/gal)
        gal = 0.3 * 20.33 * 1728 / 231.02      # book: 20.33 ft^3 for both halves = 35,130 in^3
        self.assertAlmostEqual(gal, 45.62, delta=0.02)
        self.assertAlmostEqual(gal * 6.0, 273.7, delta=0.2)


class ProjectTests(unittest.TestCase):
    def make(self, tmp, m09b, with_m04=True):
        data = {"m09b": m09b}
        if with_m04:
            data["m04"] = json.loads(C162.read_text(encoding="utf-8"))["m04"]
            data["m04"]["tow_from_m06"] = False
        src = Path(tmp) / "in.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        path = Path(tmp) / "p.json"
        main(["project-init", "--project", str(path), "--name", "c162", "--from-inputs", str(src)])
        return path

    def test_cli_chain_m04_m09b_m08(self):
        m09b = {"planform": {"from_m04": True, "aspect_ratio": 8.0, "taper_ratio": 0.6},
                "dihedral_deg": 3.0, "washout_deg": 2.0, "mach": 0.15, "wing_class": "general_aviation",
                "airfoils": {"root": {"id": "naca2412", "clmax": 1.58, "cl_alpha_per_rad": 6.1},
                             "tip": {"id": "naca2412", "clmax": 1.58, "cl_alpha_per_rad": 6.1}},
                "volume": {"y1_m": 0.5, "y2_m": 2.0, "k": 0.3, "t_over_c": 0.12, "fuel_density_kgm3": 720},
                "range_ar": {"cl_cruise": 0.3, "cd_min": 0.03, "range_nm": 500, "w_ini": 1320, "w_fin": 1200,
                             "sfc_hp": 0.5, "eta_p": 0.8}}
        with tempfile.TemporaryDirectory() as tmp:
            path = self.make(tmp, m09b)
            main(["m04", "--project", str(path)])
            main(["m09b", "--project", str(path)])
            data = prj.load(path)
            r = data["outputs"]["m09b"]["result"]
            self.assertAlmostEqual(r["planform"]["area_m2"] * r["area_source"]["wing_loading_pa"], 598.74 * 9.80665, places=6)
            self.assertAlmostEqual(r["planform"]["aspect_ratio"], r["planform"]["span_m"] ** 2 / r["planform"]["area_m2"])
            self.assertLess(r["lift_curve_slope"]["cl_alpha_recommended_per_rad"], 2 * math.pi)
            self.assertAlmostEqual(r["span_efficiency"]["e"], w.oswald_straight(8.0))
            self.assertAlmostEqual(r["clmax"]["clmax0"], 0.9 * 1.58)
            self.assertGreater(r["stall"]["vs_mps"], 0)
            self.assertGreater(r["volume"]["fuel_mass_kg"], 0)
            self.assertEqual(prj.stale(data), [])
            data["outputs"]["m04"]["result"]["best_sample"]["wingloading_pa"] += 1.0
            self.assertEqual(prj.stale(data), ["m09b"])
            # M08 can take the wing from M09b
            d2 = prj.load(path)
            d2["inputs"]["m08"] = {"wing_from_m09b": True, "volumes": {"class": "ga_single_engine"},
                                   "fuselage": {"r1_m": 0.5, "r2_m": 0.1}}
            from aerosuite import m08_tail
            res = m08_tail.run(d2)
            self.assertAlmostEqual(res["wing"]["area_m2"], r["planform"]["area_m2"])
            self.assertEqual(list(d2["outputs"]["m08"]["run"]["depends_on"]), ["m09b"])

    def test_flow5_exchange_files_validate_and_export(self):
        m09b = {"planform": {"area_m2": 11.15, "aspect_ratio": 8.0, "taper_ratio": 0.7},
                "dihedral_deg": 2.0, "washout_deg": 1.5,
                "airfoils": {"root": {"id": "naca2412", "clmax": 1.6, "cl_alpha_per_rad": 6.1},
                             "tip": {"id": "naca2412", "clmax": 1.6, "cl_alpha_per_rad": 6.1}},
                "flow5": {"analysis": {"type": "FIXEDSPEEDPOLAR", "method": "LLT", "velocity_mps": 55.6,
                                       "altitude_m": 2438.4, "viscous": True, "xfoil_on_the_fly": True, "ncrit": 9,
                                       "alpha_deg": [-2, 10, 2]}}}
        with tempfile.TemporaryDirectory() as tmp:
            path = self.make(tmp, m09b, with_m04=False)
            main(["m09b", "--project", str(path)])
            r = prj.load(path)["outputs"]["m09b"]["result"]
            cfg = r["flow5_config"]
            flow5_xml.validate(cfg)
            self.assertEqual(cfg["wings"][0]["sections"][1]["twist_deg"], -1.5)
            self.assertAlmostEqual(cfg["wings"][0]["sections"][1]["y_m"], r["planform"]["span_m"] / 2)
            self.assertIn("pendiente de validacion", r["flow5_status"])
            cfg_path = Path(tmp) / "wing.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            man = flow5_xml.export(cfg_path, Path(tmp) / "job")
            self.assertEqual(man["status"], "EXPORTED (not yet executed)")
            self.assertIn("NACA 2412", cfg["wings"][0]["sections"][0]["foil"])

    def test_missing_polar_without_m09a_stops_with_message(self):
        m09b = {"planform": {"area_m2": 10.0, "aspect_ratio": 8.0, "taper_ratio": 0.6},
                "airfoils": {"root": "naca2412", "tip": "naca2412"}}
        with tempfile.TemporaryDirectory() as tmp:
            path = self.make(tmp, m09b, with_m04=False)
            with self.assertRaises(SystemExit):
                main(["m09b", "--project", str(path)])


if __name__ == "__main__":
    unittest.main()
