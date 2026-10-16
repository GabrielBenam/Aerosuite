"""M12 tests against Gudmundsson Chapter 6: Example 6-5 (wing, five methods), Examples 6-6 and 6-7 (direct spar-cap model and
aspect-ratio variation). Other component equations have no solved example in the book: they are tested for unit handling,
scope rules and plumbing only (documented in TEST_RESULTS)."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite import m12_weights as w

EXAMPLE = Path(__file__).parents[1] / "examples" / "projects" / "c172-like-weights-inputs.json"


class Example65Tests(unittest.TestCase):
    # S_W = 130 ft^2, W_FW = 100 lbf, AR = 8, c/4 sweep 0, c/2 sweep -2.386, q = 33.9 psf, lambda = 0.5, t/c = 0.16,
    # W0 = 1320 lbf, n_z = 6.0, c_r = 5.375 ft (GUD PDF 210)
    S, WFW, AR, C4, C2, Q, LAM, TC, W0, NZ, CR = 130.0, 100.0, 8.0, 0.0, 2.386, 33.9, 0.5, 0.16, 1320.0, 6.0, 5.375

    def test_cessna_cantilever_and_strut(self):
        self.assertAlmostEqual(w.wing_cessna_cantilever(self.NZ, self.W0, self.S, self.AR), 335.0, delta=1.0)   # book 335
        self.assertAlmostEqual(w.wing_cessna_strut(self.NZ, self.S, self.AR), 213.0, delta=1.0)                 # book 213

    def test_raymer_and_torenbeek(self):
        self.assertAlmostEqual(w.wing_raymer(self.NZ, self.W0, self.S, self.AR, self.C4, self.TC, self.Q, self.LAM, self.WFW),
                               180.0, delta=1.0)                                                                 # book 180
        b = math.sqrt(self.AR * self.S)
        self.assertAlmostEqual(w.wing_torenbeek(self.NZ, self.W0, b, self.S, self.C2, self.CR * self.TC), 128.0, delta=1.0)  # book 128

    def test_usaf_and_the_book_average(self):
        # The example does not list V_H; 120 to 125 KEAS reproduces the printed 139 lbf (inferred input, not a book value)
        for vh in (120.0, 125.0):
            self.assertAlmostEqual(w.wing_usaf(self.NZ, self.W0, self.S, self.AR, self.C4, self.TC, self.LAM, vh), 139.0, delta=0.5)
        raymer = w.wing_raymer(self.NZ, self.W0, self.S, self.AR, self.C4, self.TC, self.Q, self.LAM, self.WFW)
        toren = w.wing_torenbeek(self.NZ, self.W0, math.sqrt(self.AR * self.S), self.S, self.C2, self.CR * self.TC)
        usaf = w.wing_usaf(self.NZ, self.W0, self.S, self.AR, self.C4, self.TC, self.LAM, 122.0)
        self.assertAlmostEqual((raymer + toren + usaf) / 3.0, 149.0, delta=1.0)           # book: average of the last three = 149 lbf

    def test_wfw_zero_convention(self):
        # "If W_FW = 0 then let W_FW^0.0035 = 1"
        a = w.wing_raymer(self.NZ, self.W0, self.S, self.AR, self.C4, self.TC, self.Q, self.LAM, 0.0)
        b = w.wing_raymer(self.NZ, self.W0, self.S, self.AR, self.C4, self.TC, self.Q, self.LAM, 1.0)
        self.assertEqual(a, b)


class Example66And67Tests(unittest.TestCase):
    # Beech Bonanza A36: W0 = 3600 lbf, S = 181 ft^2, AR = 6.2, lambda = 0.538, t/c = 0.165, n_ult = 6.6 (4.4 g x 1.5),
    # 2024-T3: density 0.1 lbf/in^3, sigma_max = 65 000 psi (GUD PDF 217-218)
    def case(self):
        return w.spar_cap(6.6, 3600.0, 181.0, 6.2, 0.538, 0.165, 9.36e6, 0.1 * 1728.0)

    def test_example_6_6(self):
        r = self.case()
        self.assertAlmostEqual(r["span"], 33.5, delta=0.01)
        self.assertAlmostEqual(r["cmgc"], 5.566, delta=0.001)
        self.assertAlmostEqual(r["ymgc"], 7.536, delta=0.001)
        self.assertAlmostEqual(r["h"], 0.918, delta=0.001)
        self.assertAlmostEqual(r["m_max"], 89530.0, delta=2.0)                              # ft lbf
        self.assertAlmostEqual(r["a_cap"] * 144.0, 1.500, delta=0.002)                       # in^2
        self.assertAlmostEqual(r["w_cap"], 66.3, delta=0.1)                                  # lbf

    def test_example_6_7_aspect_ratio_variation(self):
        r = self.case()
        s = w.ar_scaling(r["w_cap"], r["m_max"], 6.2, 10.0)
        self.assertAlmostEqual(s["m_max"], 113703.0, delta=3.0)                              # book 113 703 ft lbf
        self.assertAlmostEqual(s["w_cap"], 135.9, delta=0.1)                                 # book 135.9 lbf
        self.assertAlmostEqual(s["delta_w_cap"], 69.6, delta=0.1)                            # book 69.6 lbf
        self.assertAlmostEqual(2247.0 + s["delta_w_cap"], 2317.0, delta=0.5)                 # book W_e(AR = 10) = 2317 lbf
        # consistency of the scaling with a fresh evaluation of the model (same S and lambda, new AR)
        direct = w.spar_cap(6.6, 3600.0, 181.0, 10.0, 0.538, 0.165, 9.36e6, 172.8)
        self.assertAlmostEqual(direct["w_cap"], s["w_cap"], delta=0.05)
        self.assertAlmostEqual(direct["m_max"], s["m_max"], delta=1.0)
        self.assertAlmostEqual(direct["a_cap"] / r["a_cap"], 10.0 / 6.2, places=6)


class EquationBehaviourTests(unittest.TestCase):
    def test_engine_and_scope_helpers(self):
        self.assertAlmostEqual(w.engine_dry_piston(100.0), 185.76)                         # Eq. 6-106
        self.assertGreater(w.installed_engine_raymer_usaf(w.engine_dry_piston(160.0), 2),
                           w.installed_engine_raymer_usaf(w.engine_dry_piston(160.0), 1))
        fs = w.fuel_system(56.0, 56.0, 2, 1)
        self.assertAlmostEqual(fs["cessna"], 0.40 * 56.0)                                   # Eq. 6-81
        self.assertAlmostEqual(w.fuel_system(56.0, 56.0, 2, 1, tip_tanks=True)["cessna"], 0.70 * 56.0)   # Eq. 6-83
        self.assertAlmostEqual(w.hydraulics(1000.0), 1.0)
        self.assertAlmostEqual(w.controls(1000.0, 20.0, 30.0, 5.7)["cessna"], 16.8)       # Eq. 6-90


class ProjectTests(unittest.TestCase):
    def build(self, mutate=None):
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        if mutate:
            mutate(data)
        return data

    def init(self, tmp, data, mods=("m09b", "m08", "m10", "m12")):
        src = Path(tmp) / "in.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        path = Path(tmp) / "p.json"
        main(["project-init", "--project", str(path), "--name", "c172", "--from-inputs", str(src)])
        for m in mods:
            main([m, "--project", str(path)])
        return path

    def test_chain_and_unit_conversion(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.init(tmp, self.build())
            data = prj.load(path)
            r = data["outputs"]["m12"]["result"]
            self.assertTrue(r["complete"], r["missing"])
            # SI -> imperial -> SI plumbing: the stored wing value equals the book equation on converted inputs
            pf = data["outputs"]["m09b"]["result"]["planform"]
            nz, w0 = 5.7, 1156.7 * w.LBF_PER_KG
            direct = w.wing_cessna_cantilever(nz, w0, pf["area_m2"] * w.FT2_PER_M2, pf["aspect_ratio"]) / w.LBF_PER_KG
            self.assertAlmostEqual(r["components"]["wing"]["methods"]["cessna_cantilever"]["kg"], direct, places=9)
            self.assertAlmostEqual(r["empty_weight_kg"], sum(r["group_totals_kg"].values()))
            self.assertEqual(sorted(data["outputs"]["m12"]["run"]["depends_on"]), ["m08", "m09b", "m10"])
            self.assertEqual(prj.stale(data), [])
            # direct spar-cap model and AR variation (Sec. 6.5): W_cap ~ AR^1.5
            dw = r["direct_wing"]
            v = {x["aspect_ratio"]: x["spar_cap_weight_kg"] for x in dw["ar_variation"]}
            self.assertAlmostEqual(v[8] , dw["spar_cap_weight_kg"], places=9)
            self.assertAlmostEqual(v[12] / v[8], (12.0 / 8.0) ** 1.5, places=9)
            keys = {a["key"] for a in data["assumptions"] if a["module"] == "m12"}
            self.assertEqual(keys, {"landing_weight_fraction", "tail_tc", "fuselage_structure_length_m"})

    def test_suspect_cessna_vt_excluded_by_default_and_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = prj.load(self.init(tmp, self.build()))["outputs"]["m12"]["result"]
            vt = r["components"]["vertical_tail"]
            self.assertNotIn("cessna", vt["methods_averaged"])
            self.assertLess(vt["methods"]["cessna"]["lbf"], 3.0)         # the printed exponent gives an absurd 0.9 lbf
            self.assertFalse(vt["methods"]["cessna"]["in_scope"])
        def mut(d):
            d["m12"]["include_suspect_equations"] = True
        with tempfile.TemporaryDirectory() as tmp:
            r2 = prj.load(self.init(tmp, self.build(mut)))["outputs"]["m12"]["result"]
            self.assertIn("cessna", r2["components"]["vertical_tail"]["methods_averaged"])

    def test_known_weights_supersede_and_missing_inputs_are_listed(self):
        def mut(d):
            d["m12"]["known_weights"]["wing_kg"] = 100.0
            d["m12"]["known_weights"].pop("propeller_kg")
            d["m12"]["landing_gear"] = {}
        with tempfile.TemporaryDirectory() as tmp:
            r = prj.load(self.init(tmp, self.build(mut)))["outputs"]["m12"]["result"]
            self.assertEqual(r["components"]["wing"]["kg"], 100.0)
            self.assertIn("known weight", r["components"]["wing"]["source"])
            self.assertFalse(r["complete"])
            self.assertTrue(any(m.startswith("landing_gear") for m in r["missing"]))
            eng = r["components"]["engine_installed"]
            self.assertEqual(eng["methods_averaged"], ["raymer_usaf"])               # Cessna/Torenbeek need the propeller weight
            self.assertTrue(eng["missing_inputs"])

    def test_scope_limits_and_calibration(self):
        def mut(d):
            d["m12"]["vh_keas"] = 250.0                     # above the Cessna limit (200 KTAS)
            d["m12"]["calibration"] = {"fuselage": 1.18}
        with tempfile.TemporaryDirectory() as tmp:
            base = prj.load(self.init(tmp, self.build()))["outputs"]["m12"]["result"]
        with tempfile.TemporaryDirectory() as tmp:
            r = prj.load(self.init(tmp, self.build(mut)))["outputs"]["m12"]["result"]
            self.assertFalse(r["components"]["wing"]["methods"]["cessna_cantilever"]["in_scope"])
            self.assertNotIn("cessna_cantilever", r["components"]["wing"]["methods_averaged"])
            self.assertEqual(r["components"]["fuselage"]["calibration_factor"], 1.18)
            self.assertNotEqual(r["components"]["fuselage"]["kg"], base["components"]["fuselage"]["kg"])

    def test_missing_wing_tc_is_an_error_not_a_guess(self):
        def mut(d):
            d["m12"].pop("wing_tc")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                self.init(tmp, self.build(mut))


if __name__ == "__main__":
    unittest.main()
