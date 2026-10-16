"""M20 tests: Gudmundsson Examples 16-6 (x0/c, fully laminar and fully turbulent C_f of the SR22 wing) and 16-11 (wing form factor 1.3111),
Prandtl-Schlichting and Young limits, the buildup arithmetic, the project chain, and a bracketing contrast with REAL flow5 7.55 output
(CD_viscous and CD_induced of the wing-tail model, evidence/flow5-7.55-win/run2-custom-ref)."""
import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite import m20_drag as m

EXAMPLE = Path(__file__).parents[1] / "examples" / "projects" / "c172-like-drag-inputs.json"
FLOW5_OUT = Path(__file__).resolve().parents[1] / "evidence" / "flow5-7.55-win" / "run2-custom-ref" / "output"


class BookTests(unittest.TestCase):
    def test_example_16_11_wing_form_factor(self):
        mach = 185.0 * m.KT / m.isa(0.0)["a"]
        self.assertAlmostEqual(m.ff_wing_nicolai(0.15, 0.5, mach), 1.3111, delta=2e-4)

    def test_example_16_6_fictitious_origin(self):
        self.assertAlmostEqual(m.fictitious_origin(5126287.0, 0.50), 0.07290, delta=5e-5)

    def test_example_16_6_laminar_and_turbulent_wing(self):
        # printed: fully laminar C_f = 0.0005068, fully turbulent 0.003185 (same Reynolds number)
        re = (1.328 / 0.0005068) ** 2
        self.assertAlmostEqual(m.cf_laminar(re), 0.0005068, delta=1e-7)
        self.assertAlmostEqual(m.cf_turbulent(re), 0.003185, delta=2e-5)

    def test_cutoff_reynolds_number_formula(self):
        self.assertAlmostEqual(m.cutoff_re(1.0, 1e-5), 38.21 * 1e5 ** 1.053)
        self.assertGreater(m.cutoff_re(1.0, 1e-5, 1.5), 0.0)


class SkinFrictionTests(unittest.TestCase):
    def test_young_limits_and_monotonicity(self):
        re = 3.0e6
        turb = 0.074 / re ** 0.2
        self.assertAlmostEqual(m.cf_mixed_young(re, 0.0), turb)
        vals = [m.cf_mixed_young(re, x) for x in (0.05, 0.2, 0.4, 0.6)]
        self.assertTrue(all(b < a for a, b in zip([turb] + vals, vals)))
        self.assertGreater(vals[-1], m.cf_laminar(re) * 0.0)

    def test_prandtl_schlichting_value(self):
        self.assertAlmostEqual(m.cf_turbulent(1.0e7), 0.455 / 7.0 ** 2.58, places=9)

    def test_cutoff_limits_reynolds(self):
        sf = m.skin_friction(1e9, 1.0, 1.33e-5 * 0.3048, model="turbulent")
        self.assertEqual(sf["re_used"], sf["re_cutoff"])
        self.assertLess(sf["re_used"], 1e9)

    def test_fuselage_form_factor_models(self):
        for f in (4.0, 5.4, 7.0):
            vals = [m.ff_fuselage(f, k) for k in ("hoerner", "torenbeek", "jenkinson")]
            self.assertLess(max(vals) - min(vals), 0.15)
            self.assertTrue(all(v > 1.0 for v in vals + [m.ff_fuselage(f, "nicolai")]))
            self.assertGreater(m.ff_fuselage(4.0, "nicolai"), m.ff_fuselage(4.0, "torenbeek"))     # Nicolai/Raymer is the highest at low f (Fig. 16-47)

    def test_sutherland_viscosity_at_sea_level(self):
        self.assertAlmostEqual(m.sutherland_mu(288.15), 1.789e-5, delta=2e-8)


class BuildupTests(unittest.TestCase):
    def test_arithmetic_and_crud(self):
        comps = [{"name": "a", "cf": 0.003, "ff": 1.2, "if": 1.0, "s_wet_m2": 20.0}, {"name": "b", "cf": 0.004, "ff": 1.1, "if": 1.05, "s_wet_m2": 10.0}]
        out = m.cdmin_buildup(comps, 16.0, misc=0.002)
        cd1 = (0.003 * 1.2 * 20.0 + 0.004 * 1.1 * 1.05 * 10.0) / 16.0
        self.assertAlmostEqual(out["cd_friction_form"], cd1)
        self.assertAlmostEqual(out["cd_min"], (cd1 + 0.002) * 1.25)
        self.assertAlmostEqual(out["equivalent_flat_plate_area_m2"], out["cd_min"] * 16.0)

    def test_misc_increment_scaling(self):
        self.assertAlmostEqual(m.misc_increment(0.35, 0.25, 16.0) * 16.0, 0.35 * 0.25)


class ProjectTests(unittest.TestCase):
    def build(self, tmp, mutate=None):
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        if mutate:
            mutate(data)
        src = Path(tmp) / "in.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        path = Path(tmp) / "p.json"
        main(["project-init", "--project", str(path), "--name", "d", "--from-inputs", str(src)])
        for mod in ("m09b", "m08", "m20"):
            main([mod, "--project", str(path)])
        return path

    def test_chain_polar_and_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.build(tmp)
            data = prj.load(path)
            r = data["outputs"]["m20"]["result"]
            self.assertEqual(sorted(data["outputs"]["m20"]["run"]["depends_on"]), ["m08", "m09b"])
            self.assertEqual(prj.stale(data), [])
            names = [c["name"] for c in r["buildup"]["components"]]
            self.assertEqual(names, ["wing", "ht", "vt", "fuselage"])
            cdmin, k = r["buildup"]["cd_min"], r["induced"]["k"]
            self.assertTrue(0.015 < cdmin < 0.045)                                   # light-airplane range (Sec. 16.6.1 gives the ranges)
            for p in r["polar"]:
                self.assertAlmostEqual(p["cd"], cdmin + k * p["cl"] ** 2)
            o = r["optimum"]
            self.assertAlmostEqual(o["cl_best_ld"] ** 2 * k, cdmin)                   # CDi = CD0 at best L/D
            self.assertAlmostEqual(o["ld_max"], o["cl_best_ld"] / (2.0 * cdmin))
            data["outputs"]["m08"]["result"]["horizontal_tail"]["area_m2"] += 0.1
            self.assertIn("m20", prj.stale(data))
            out = Path(tmp) / "m20.json"
            main(["export", "--project", str(path), "--module", "m20", "--out", str(out)])
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["module"], "m20")

    def test_more_laminar_flow_reduces_drag(self):
        def lam(d):
            d["m20"]["wing"].update(xtr_upper=0.5, xtr_lower=0.5)
        with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
            a = prj.load(self.build(t1))["outputs"]["m20"]["result"]["buildup"]["cd_min"]
            b = prj.load(self.build(t2, lam))["outputs"]["m20"]["result"]["buildup"]["cd_min"]
            self.assertLess(b, a)

    def test_m16_takes_cd0_from_m20(self):
        def mutate(d):
            d["m16"] = {"flight": {"speed_mps": 60.0, "density_kgm3": 1.225}}
        with tempfile.TemporaryDirectory() as tmp:
            path = self.build(tmp, mutate)
            for mod in ("m10", "m12", "m13", "m16"):
                main([mod, "--project", str(path)])
            data = prj.load(path)
            r = data["outputs"]["m16"]["result"]["flight_condition"]
            self.assertAlmostEqual(r["cd0"], data["outputs"]["m20"]["result"]["buildup"]["cd_min"])
            self.assertIn("m20", data["outputs"]["m16"]["run"]["depends_on"])
            self.assertEqual(prj.stale(data), [])

    def test_missing_fuselage_is_reported(self):
        def mutate(d):
            d["m20"].pop("fuselage")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                self.build(tmp, mutate)


@unittest.skipUnless(FLOW5_OUT.is_dir(), "flow5 7.55 evidence not present")
class Flow5ContrastTests(unittest.TestCase):
    @staticmethod
    def rows():
        from aerosuite.flow5_results import collect
        return collect(FLOW5_OUT)["polars"][0]["rows"]

    def test_viscous_drag_is_bracketed_by_turbulent_and_extensive_laminar_buildup(self):
        """flow5 (VLM2 + XFoil on the fly, free transition) wing + elevator + fin at V = 55.6 m/s, 2438 m, S = 11.139 m2, referenced to S.
        The component buildup (no fuselage, no CRUD, no tail interference) with the transition at 0 (fully turbulent) and at 60 % of the
        chord must enclose the minimum CD_viscous of flow5. A bracket, not a calibration."""
        a = m.isa(2438.4)
        v, s_ref, kap = 55.6, 11.139, m.ROUGHNESS_M["smooth_paint"]
        mach = v / a["a"]

        def cdv(xtr):
            tot = 0.0
            for (s_exp, cr, ct, tc, sides) in ((s_ref, 1.25, 1.11, 0.12, 2.0), (1.96, 0.8, 0.6, 0.09, 2.0), (0.96, 1.0, 0.6, 0.09, 2.0)):
                cfs = [m.skin_friction(a["rho"] * v * c / a["mu"], c, kap, xtr, xtr, mach)["cf"] for c in (cr, ct)]
                cf = (cfs[0] * cr + cfs[1] * ct) / (cr + ct)
                tot += cf * m.ff_wing_nicolai(tc, 0.3, mach) * sides * s_exp * 1.07
            return tot / s_ref
        visc = min(r["CD_viscous"] for r in self.rows())
        self.assertAlmostEqual(visc, 0.00743, delta=2e-5)                           # value of the recorded real run
        self.assertGreater(cdv(0.0), visc)
        self.assertLess(cdv(0.6), visc)

    def test_induced_drag_factor_against_flow5(self):
        rows = [r for r in self.rows() if r["alpha_deg"] >= 6.0]
        k_flow5 = np.mean([r["CD_induced"] / r["CL"] ** 2 for r in rows])
        self.assertTrue(0.034 < k_flow5 < 0.040)                                    # flow5 far-field wing-tail value
        # the conservative whole-aircraft e of M09b (Raymer, straight wing) gives a larger k: documented, not forced to agree
        self.assertLess(k_flow5, 1.0 / (math.pi * 8.0 * 0.81))


if __name__ == "__main__":
    unittest.main()
