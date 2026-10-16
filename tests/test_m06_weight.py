"""M06 tests against Gudmundsson Chapter 6: Example 6-2 (Method 1), Example 6-3 (electric), Example 6-4 (Method 3)."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite.m06_weight import (EMPTY_WEIGHT_FRACTION, LBF_PER_KG, electric_gross_mass, empty_weight_fraction,
                                  gross_weight_historical, gross_weight_mission, mission_fractions, segment_ratio)

EXAMPLES = Path(__file__).parents[1] / "examples" / "projects"
JET = {"engine": "jet", "sfc": 0.55}


def example_6_4(r_climb1=0.3, r_climb2=0.5, scaled=False):
    c1 = {"r_ref": r_climb1} if scaled else {"r": r_climb1}
    c2 = {"r_ref": r_climb2} if scaled else {"r": r_climb2}
    return [
        dict(type="taxi_takeoff", typical=True, **JET),
        dict(type="climb", delta_h_ft=36000, roc_fpm=1500, **c1, **JET),
        dict(type="cruise", range_nm=4000, v_ktas=573.6 * 0.85, ld=14, **JET),
        dict(type="descent", delta_h_ft=-31000, rod_fpm=-2000, r=0.1, **JET),
        dict(type="loiter", time_h=5 / 60, ld=10, **JET),
        dict(type="climb", delta_h_ft=15000, roc_fpm=2000, **c2, **JET),
        dict(type="cruise", range_nm=200, v_ktas=614.1 * 0.70, ld=14, **JET),
        dict(type="descent", delta_h_ft=-20000, rod_fpm=-2000, r=0.1, **JET),
        dict(type="reserve", time_h=0.5, ld=14, **JET),
        dict(type="fixed", ratio=1.0)]


class Method1Tests(unittest.TestCase):
    def test_example_6_2(self):
        # GUD Ex. 6-2: Wc 200 lbf, Wp 900 lbf, We/W0 0.6875, Wf/W0 0.1313 -> W0 6069, We 4172, Wf 797 lbf
        r = gross_weight_historical(200.0, 900.0, 0.6875, 0.1313)
        self.assertAlmostEqual(r["w0"], 6069.0, delta=3.0)     # book rounds intermediate values (0.05 %)
        self.assertAlmostEqual(r["we"], 4172.0, delta=3.0)
        self.assertAlmostEqual(r["wf"], 797.0, delta=1.0)

    def test_divergent_ratios_rejected(self):
        with self.assertRaises(ValueError):
            gross_weight_historical(100.0, 100.0, 0.7, 0.3)


class Method2Tests(unittest.TestCase):
    def test_lbf_and_kg_forms_are_consistent(self):
        for cls in EMPTY_WEIGHT_FRACTION:
            w_kg = 1500.0
            self.assertAlmostEqual(empty_weight_fraction(cls, w_kg, "kg"),
                                   empty_weight_fraction(cls, w_kg * LBF_PER_KG, "lbf"), delta=6e-5, msg=cls)

    def test_lsa_matches_table_6_1_mean(self):
        # Eq. 6-18 at 1320 lbf vs the Table 6-1 mean We/W0 = 0.535
        self.assertAlmostEqual(empty_weight_fraction("lsa_land", 1320.0, "lbf"), 0.535, delta=0.005)

    def test_business_jet_example_6_4_value(self):
        # Ex. 6-4 "Further analyses": We/W0 = 0.5652 at W0 = 44,556 lbf
        self.assertAlmostEqual(empty_weight_fraction("business_jet", 44556.0, "lbf"), 0.5652, delta=0.0002)

    def test_unknown_class(self):
        with self.assertRaises(ValueError):
            empty_weight_fraction("airship", 1000.0)


class Method3Tests(unittest.TestCase):
    def test_segment_ratios_example_6_4(self):
        book = [0.9918, 0.9340, 0.7245, 0.9858, 0.9954, 0.9656, 0.9819, 0.9908, 0.9805, 1.0]
        fr = mission_fractions(example_6_4())
        for seg, expected in zip(fr["segments"], book):
            self.assertAlmostEqual(seg["ratio"], expected, delta=6e-5)
        self.assertAlmostEqual(fr["wn_over_w0"], 0.6066, delta=1e-4)

    def test_first_iteration_gross_weight(self):
        # Book: W0 = 44,556 lbf, We/W0 = 0.5652, We = 25,184 lbf, fuel = 17,528 lbf (tolerance 0.05 %: rounded 0.6066)
        r = gross_weight_mission(example_6_4(), 0.9038, -0.03163, 615.0, 1230.0)
        self.assertAlmostEqual(r["w0"] / 44556.0, 1.0, delta=5e-4)
        self.assertAlmostEqual(r["we_w0"], 0.5652, delta=2e-4)
        self.assertAlmostEqual(r["we"] / 25184.0, 1.0, delta=5e-4)
        self.assertAlmostEqual(r["fuel_weight"] / 17528.0, 1.0, delta=5e-4)
        self.assertAlmostEqual(r["residual"], 0.0, places=10)

    def test_second_iteration_with_scaled_thrust_loading(self):
        # Book: with r_climb rescaled by Eq. 6-30 (Tmax/W0 = 0.3 for both climbs) W0 = 43,619 and We = 24,684 lbf
        seg = mission_fractions(example_6_4(0.3, 0.3, scaled=True))["segments"]
        self.assertAlmostEqual(seg[1]["ratio"], 1 - 36000 * 0.55 * (0.3 / mission_fractions(example_6_4())["segments"][0]["cumulative"]) / (60 * 1500), places=9)
        r = gross_weight_mission(example_6_4(0.3, 0.3, scaled=True), 0.9038, -0.03163, 615.0, 1230.0)
        self.assertAlmostEqual(r["w0"] / 43619.0, 1.0, delta=1e-3)
        self.assertAlmostEqual(r["we"] / 24684.0, 1.0, delta=1e-3)

    def test_propeller_cruise_uses_325_9_eta(self):
        seg = {"type": "cruise", "engine": "prop", "sfc": 0.45, "eta_p": 0.8, "ld": 12, "range_nm": 300}
        self.assertAlmostEqual(segment_ratio(seg), math.exp(-300 * 0.45 / (325.9 * 0.8 * 12)))

    def test_mission_that_cannot_close(self):
        heavy = [dict(type="cruise", range_nm=20000, v_ktas=450, ld=5, **JET)]
        with self.assertRaises(ValueError):
            gross_weight_mission(heavy, 0.9038, -0.03163, 615.0, 1230.0)

    def test_nonphysical_segment_rejected(self):
        with self.assertRaises(ValueError):
            mission_fractions([dict(type="climb", delta_h_ft=36000, roc_fpm=100, r=0.5, **JET)])


class ElectricTests(unittest.TestCase):
    def test_example_6_3(self):
        # 10 occupants x 90 kg, We/m0 = 0.5, R = 500 km, E* = 180 Wh/kg, eta = 0.70: LD_min 21.62; LD 30 -> 6444 kg
        r = electric_gross_mass(900.0, 0.5, 500.0, 180.0, 0.70, 30.0)
        self.assertAlmostEqual(r["ld_min"], 21.62, delta=0.005)
        self.assertAlmostEqual(r["m0_kg"], 6444.0, delta=1.0)
        with self.assertRaises(ValueError):
            electric_gross_mass(900.0, 0.5, 500.0, 180.0, 0.70, 21.0)


class ProjectTests(unittest.TestCase):
    def test_cli_mission_example_and_chain_staleness(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.json"
            main(["project-init", "--project", str(path), "--name", "ex64", "--from-inputs",
                  str(EXAMPLES / "gud-example-6-4-mission.json")])
            main(["m06", "--project", str(path)])
            r = prj.load(path)["outputs"]["m06"]["result"]
            self.assertAlmostEqual(r["w0_kg"] * LBF_PER_KG / 44556.0, 1.0, delta=1e-3)
            chain = Path(tmp) / "c.json"
            main(["project-init", "--project", str(chain), "--name", "c162", "--from-inputs",
                  str(EXAMPLES / "c162-inputs.json")])
            main(["m06", "--project", str(chain)])
            main(["m04", "--project", str(chain)])
            data = prj.load(chain)
            self.assertAlmostEqual(data["outputs"]["m04"]["result"]["landing"]["max_wingloading_lbf_ft2"], 11.37, delta=0.02)
            self.assertEqual(prj.stale(data), [])
            data["inputs"]["m06"]["w0_kg"] = 650.0      # M06 changes: M06 reruns, M04 depends on it and is now stale
            self.assertEqual(prj.stale(data), ["m06"])
            prj.save(data, chain)
            main(["m06", "--project", str(chain)])
            self.assertEqual(prj.stale(prj.load(chain)), ["m04"])

    def test_m04_without_m06_is_reported(self):
        p = prj.new_project("t")
        p["inputs"] = json.loads((EXAMPLES / "c162-inputs.json").read_text(encoding="utf-8"))
        from aerosuite import m04_constraints
        with self.assertRaises(SystemExit):
            m04_constraints.run(p)

    def test_historical_ratios_from_m02(self):
        p = prj.new_project("t")
        p["inputs"]["m02"] = {"database": "gud_table_6_1_lsa"}
        p["inputs"]["m06"] = {"method": "historical_ratios", "ratios_from_m02": True, "crew_kg": 90.0, "payload_kg": 90.0}
        from aerosuite import m02_references, m06_weight
        m02_references.run(p)
        r = m06_weight.run(p)
        self.assertAlmostEqual(r["growth_factor"], 1.0 / (1.0 - r["we_w0"] - r["wf_w0"]))
        self.assertEqual(p["outputs"]["m06"]["run"]["depends_on"].keys(), {"m02"})
        self.assertEqual(prj.stale(p), [])


if __name__ == "__main__":
    unittest.main()
