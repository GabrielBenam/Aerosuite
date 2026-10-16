"""M11 tests against Gudmundsson Chapters 7 and 15 (Examples 7-2, 7-3, 15-2, 15-3, Fig. 7-8, Eq. 15-32 worked case)."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite import m11_powerplant as m

C162 = Path(__file__).parents[1] / "examples" / "projects" / "c162-inputs.json"
FT = 0.3048


class PistonPowerTests(unittest.TestCase):
    def test_example_7_2_gagg_ferrar_and_temperature(self):
        # 100 BHP engine at 10 000 ft, OAT 30 degR above ISA
        sigma = m.sigma_standard_ft(10000.0)
        self.assertAlmostEqual(sigma, 0.7385, delta=0.0001)
        p_std = 100.0 * m.gagg_ferrar(sigma)
        self.assertAlmostEqual(p_std, 70.4, delta=0.05)                                    # book 70.4 BHP
        t_std = 518.67 * (1.0 - m.KAPPA_PER_FT * 10000.0)                                  # 483.0 degR
        self.assertAlmostEqual(t_std, 483.0, delta=0.05)
        self.assertAlmostEqual(m.temperature_correction(p_std, t_std, t_std + 30.0, "sqrt"), 68.3, delta=0.05)    # Eq. 7-12
        self.assertAlmostEqual(m.temperature_correction(p_std, t_std, t_std + 30.0, "ratio"), 66.3, delta=0.05)   # Eq. 7-13
        self.assertAlmostEqual(100.0 * m.gagg_ferrar(0.6951), 65.5, delta=0.05)           # ideal-gas density route

    def test_fig_7_8_power_fractions_at_altitude(self):
        # GUD text: normally aspirated engine delivers 75 %, 65 % and 55 % at 8283, 12 106 and 16 324 ft
        for h_ft, frac in ((8283.0, 0.75), (12106.0, 0.65), (16324.0, 0.55)):
            self.assertAlmostEqual(m.gagg_ferrar(m.sigma_standard_ft(h_ft)), frac, delta=0.001)
        self.assertAlmostEqual(m.gagg_ferrar(1.0), 1.0)

    def test_isa_sigma_from_adrpy_matches_book_formula(self):
        self.assertAlmostEqual(m.sigma_isa(3048.0), m.sigma_standard_ft(10000.0), delta=0.0005)

    def test_critical_altitude_model(self):
        self.assertEqual(m.piston_power_bhp(200.0, 1000.0, h_crit_m=5000.0), 200.0)        # Eq. 7-9
        above = m.piston_power_bhp(200.0, 8000.0, h_crit_m=5000.0)                         # Eq. 7-10
        self.assertLess(above, 200.0)
        self.assertAlmostEqual(m.piston_power_bhp(200.0, 5000.0, 5000.0), 200.0)
        self.assertAlmostEqual(m.piston_power_bhp(200.0, 3000.0), 200.0 * m.gagg_ferrar(m.sigma_isa(3000.0)))

    def test_example_7_3_gearbox(self):
        self.assertAlmostEqual(m.gearbox(5800.0, 2.43), 2387.0, delta=0.5)                 # book 2387 RPM, power unchanged
        with self.assertRaises(ValueError):
            m.gearbox(2700.0, 0.8)


class PropellerTests(unittest.TestCase):
    def test_example_15_2_wooden_propellers(self):
        # Rotax 912UL 80 BHP at 75 % power (60 BHP), 2300 RPM, 104 KTAS
        for n, d_in, tip_fts in ((2, 67.2, 675.0), (3, 61.6, 618.0), (4, 56.0, 562.0)):
            d = m.wood_prop_diameter_in(60.0, 2300.0, 104.0, n)
            self.assertAlmostEqual(d, d_in, delta=0.06, msg=f"{n} blades")
            tip = m.tip_speed_mps(d * 0.0254, 2300.0) / FT
            self.assertAlmostEqual(tip, tip_fts, delta=1.5, msg=f"{n} blades tip speed")
        # the book notes the 3-blade result is the mean of the 2- and 4-blade ones: (67.2 + 56.0)/2 = 61.6
        self.assertAlmostEqual((m.wood_prop_diameter_in(60.0, 2300.0, 104.0, 2) + m.wood_prop_diameter_in(60.0, 2300.0, 104.0, 4)) / 2.0,
                               61.6, delta=0.1)
        with self.assertRaises(ValueError):
            m.wood_prop_diameter_in(60.0, 2300.0, 104.0, 5)

    def test_example_15_3_advance_ratio(self):
        j = m.advance_ratio(185.0 * 1.688 * FT, 2700.0, 76.0 * 0.0254)                      # 76 in, 185 KTAS, 2700 RPM
        self.assertAlmostEqual(j, 1.096, delta=0.002)

    def test_required_efficiency_lsa_case(self):
        # GUD Sec. 15.3.4(2): 1320 lbf LSA, 110 KTAS, 65 BHP, L/D = 10 -> eta_p >= 0.686
        w_n = 1320.0 * 4.4482216
        eta = m.required_prop_efficiency(w_n, 110.0 * 0.514444, 10.0, 65.0 * m.HP_W)
        self.assertAlmostEqual(eta, 0.686, delta=0.002)

    def test_pitch_constant_from_the_derivation(self):
        # derivation: V = (RPM/60) P_G with 1 KTAS = 1.688 ft/s = 20.256 in/s -> P_G = 60 (20.256) V/RPM
        self.assertAlmostEqual(m.pitch_in(100.0, 1000.0), 60.0 * 1.688 * 12.0 * 100.0 / 1000.0, places=6)
        # physical check in SI: P_G = 60 V / RPM
        self.assertAlmostEqual(m.pitch_in(100.0, 2400.0) * 0.0254, 60.0 * 100.0 * 0.514444 / 2400.0, delta=0.002)


class ProjectTests(unittest.TestCase):
    def make(self, tmp, m11):
        data = {"m04": json.loads(C162.read_text(encoding="utf-8"))["m04"], "m11": m11}
        data["m04"]["tow_from_m06"] = False
        src = Path(tmp) / "in.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        path = Path(tmp) / "p.json"
        main(["project-init", "--project", str(path), "--name", "c162", "--from-inputs", str(src)])
        return path

    def test_chain_m04_m11(self):
        m11 = {"engine": {"name": "100 BHP example engine (user data)", "rated_bhp": 100.0, "rated_rpm": 2800.0, "gear_ratio": 1.0},
               "propeller": {"material": "wood", "blades": 2}, "ld_cruise": 10.0, "temperature_offset_k": 15.0,
               "adrpy_deck": "IO-540", "adrpy_deck_rpm": 2400}
        with tempfile.TemporaryDirectory() as tmp:
            path = self.make(tmp, m11)
            main(["m04", "--project", str(path)])
            main(["m11", "--project", str(path)])
            data = prj.load(path)
            r = data["outputs"]["m11"]["result"]
            self.assertEqual(r["required_power"]["active"], "climb")
            self.assertAlmostEqual(r["required_power"]["combined_hp"], r["required_power"]["by_constraint_hp"]["climb"])
            self.assertTrue(r["engine"]["meets_sl_equivalent_power"])
            self.assertAlmostEqual(r["availability_by_constraint"]["ceiling"]["available_bhp"],
                                   100.0 * m.gagg_ferrar(m.sigma_isa(5181.6)), places=9)
            p = r["propeller"]
            self.assertAlmostEqual(p["design_power_bhp"], 75.0)
            self.assertAlmostEqual(p["diameter_estimates"][0]["diameter_in"], m.wood_prop_diameter_in(75.0, 2800.0, 108.0, 2), places=9)
            self.assertTrue(0.3 < p["required_efficiency_eq_15_32"] < 1.5)
            self.assertLess(r["temperature_correction"]["power_eq_7_12_bhp"], 100.0)
            rows = r["adrpy_deck_contrast"]["rows"]
            self.assertAlmostEqual(rows[0]["deck_ratio_to_sl"], 1.0)
            self.assertTrue(all(0.5 < row["deck_ratio_to_sl"] / row["gagg_ferrar_ratio"] < 1.5 for row in rows))
            self.assertEqual(prj.stale(data), [])
            self.assertEqual(list(data["outputs"]["m11"]["run"]["depends_on"]), ["m04"])
            keys = {a["key"] for a in data["assumptions"] if a["module"] == "m11"}
            self.assertEqual(keys, {"propeller_power_fraction"})

    def test_underpowered_engine_is_flagged_not_hidden(self):
        m11 = {"engine": {"rated_bhp": 60.0, "rated_rpm": 2700.0}}
        with tempfile.TemporaryDirectory() as tmp:
            path = self.make(tmp, m11)
            main(["m04", "--project", str(path)])
            main(["m11", "--project", str(path)])
            r = prj.load(path)["outputs"]["m11"]["result"]
            self.assertFalse(r["engine"]["meets_sl_equivalent_power"])
            self.assertTrue(any("below" in w for w in r["warnings"]))

    def test_example_15_2_through_the_cli_with_explicit_power(self):
        m11 = {"engine": {"rated_bhp": 80.0, "rated_rpm": 2300.0}, "power_required": {"source": "input", "bhp": 60.0},
               "cruise": {"ktas": 104.0, "altitude_m": 0.0}, "propeller": {"material": "wood", "blades": 3}}
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.json"
            src.write_text(json.dumps({"m11": m11}), encoding="utf-8")
            path = Path(tmp) / "p.json"
            main(["project-init", "--project", str(path), "--name", "a240", "--from-inputs", str(src)])
            main(["m11", "--project", str(path)])
            r = prj.load(path)["outputs"]["m11"]["result"]
            d = {row["blades"]: row["diameter_in"] for row in r["propeller"]["diameter_estimates"]}
            self.assertAlmostEqual(d[2], 67.2, delta=0.06)
            self.assertAlmostEqual(d[3], 61.6, delta=0.06)
            self.assertAlmostEqual(d[4], 56.0, delta=0.06)
            self.assertTrue(r["propeller"]["selected_tip_mach_ok"])
            self.assertFalse(r["propeller"]["constant_speed_guideline"]["constant_speed_suggested"])


if __name__ == "__main__":
    unittest.main()
