"""M23 tests. Threshold cases are built from values of the sources: 14 CFR 23.2120(a) (8.3 % / 4 %), GUD Sec. 24.3.4 (SM 10 %-30 %),
Table 1-2 (12 500 lbf), Example 3-1 (stall 45 KCAS). The synthetic project dicts are logic fixtures, not aircraft results."""
import json
import tempfile
import unittest
from pathlib import Path

from aerosuite import loop
from aerosuite import m23_verification as v
from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite.engines import xfoil_executable

EXAMPLE = Path(__file__).parents[1] / "examples" / "projects" / "c162-full-loop.json"


def fake_project(rc=3.0, v_y=25.0, level=2, perf="low", engines=1, sm=0.2, cm_a=-1.0, cn_b=0.06, vso_req=45.0, clmax_l=2.029):
    p = prj.new_project("fixture")
    p["inputs"] = {"m01": {"vso_kcas_max": vso_req, "engines": engines},
                   "m21": {"landing": {"clmax": clmax_l}}, "m04": {"concept": {"designbrief": {}}}}
    run = {"inputs_sha256": "", "depends_on": {}, "level": "conceptual", "references": [], "module": "x", "timestamp": ""}
    p["outputs"]["m01"] = {"run": run, "result": {"checks": [{"name": "mtow", "ok": True, "value_lbf": 1320.0, "limit_lbf": 12500},
                                                              {"name": "occupants", "ok": True, "value": 2, "limit": 9}],
                                                  "new_part23": {"certification_level": level, "performance_level": perf}}}
    p["outputs"]["m21"] = {"run": run, "result": {
        "weights": {"mtow_kg": 598.74}, "aero": {"s_m2": 11.148},
        "performance_at_mtow": {"0.0": {"rc_max_mps": rc, "v_best_rc_mps": v_y, "rc_max_fpm": rc * 196.85}},
        "takeoff": {}, "landing": {}, "cruise_condition": {}, "ceilings_at_mtow": {}}}
    p["outputs"]["m16"] = {"run": run, "result": {
        "punto_neutro_optimista": False,
        "longitudinal_static": {"static_margin": sm, "cm_alpha_per_rad": cm_a},
        "lateral_static": {"cn_beta_total_per_rad": cn_b}, "longitudinal_dynamics": {}}}
    return p


def item(res, rid):
    return next(i for i in res["items"] if i["id"] == rid)


class ThresholdTests(unittest.TestCase):
    def test_climb_gradient_23_2120a_low_speed_8_3_percent(self):
        # clean gradient 0.083 exactly: the clean configuration is only an upper bound, so it is not evaluable (never "cumple")
        it = item(v.evaluate(fake_project(rc=0.083 * 25.0))[0], "climb_gradient_23_2120a")
        self.assertEqual(it["status"], "no evaluable")
        self.assertAlmostEqual(it["limit"], 0.083)
        self.assertAlmostEqual(it["value"], 0.083)
        below = item(v.evaluate(fake_project(rc=0.082 * 25.0))[0], "climb_gradient_23_2120a")
        self.assertEqual(below["status"], "no cumple")           # fails even in the clean configuration
        self.assertAlmostEqual(below["margin"], -0.001)

    def test_climb_gradient_high_speed_is_4_percent(self):
        r = v.evaluate(fake_project(rc=0.039 * 25.0, perf="high"))[0]
        self.assertEqual(item(r, "climb_gradient_23_2120a")["limit"], 0.04)
        self.assertEqual(item(r, "climb_gradient_23_2120a")["status"], "no cumple")
        r = v.evaluate(fake_project(rc=0.03 * 25.0, level=4, engines=2))[0]      # level 4 twin: the paragraph read gives no value
        self.assertEqual(item(r, "climb_gradient_23_2120a")["status"], "no evaluable")

    def test_static_margin_boundaries(self):
        for sm, lo, hi in ((0.10, "cumple", "cumple"), (0.0999, "no cumple", "cumple"), (0.30, "cumple", "cumple"),
                           (0.3001, "cumple", "no cumple")):
            r = v.evaluate(fake_project(sm=sm))[0]
            self.assertEqual(item(r, "static_margin_min")["status"], lo, sm)
            self.assertEqual(item(r, "static_margin_max")["status"], hi, sm)

    def test_stability_signs(self):
        r = v.evaluate(fake_project(cm_a=0.1, cn_b=0.02))[0]
        self.assertEqual(item(r, "cm_alpha_negative")["status"], "no cumple")
        self.assertEqual(item(r, "cn_beta_positive")["status"], "no cumple")
        self.assertEqual(r["overall"], "no cumple")

    def test_stall_speed_at_the_requirement(self):
        # CLmax that makes V_S0 exactly the 45 KCAS requirement: at the threshold -> cumple; a bit less CLmax -> no cumple
        w, s = 598.74 * v.G, 11.148
        clmax = 2 * w / (v.RHO0 * s * (45.0 * v.KT) ** 2)
        self.assertEqual(item(v.evaluate(fake_project(clmax_l=clmax))[0], "vso_calculada")["status"], "cumple")
        self.assertEqual(item(v.evaluate(fake_project(clmax_l=clmax * 0.999))[0], "vso_calculada")["status"], "no cumple")
        self.assertEqual(item(v.evaluate(fake_project(clmax_l=clmax * 1.001))[0], "vso_calculada")["status"], "cumple")

    def test_overall_rule_and_unverified_criteria(self):
        r = v.evaluate(fake_project())[0]
        self.assertEqual(r["overall"], "cumple")
        for rid in ("controllability_23_2135", "stability_23_2145a", "stall_characteristics_23_2150", "balked_landing_23_2120c"):
            self.assertEqual(item(r, rid)["status"], "no evaluable")
            self.assertIn("reason", item(r, rid))
        self.assertEqual(sum(r["counts"].values()), len(r["items"]))
        self.assertTrue(all("reference" in i and "basis" in i for i in r["items"]))

    def stable_project(self, **kw):
        p = fake_project(**kw)
        r = p["outputs"]["m16"]["result"]
        r["lateral_static"]["laterally_stable"] = True
        r["longitudinal_dynamics"] = {"short_period": {"stable": True, "eigenvalue": [-4.0, 8.0]}, "phugoid": {"stable": True, "eigenvalue": [-0.02, 0.2]}}
        r["lateral_dynamics"] = {"modes": {"dutch_roll": {"stable": True, "eigenvalue": [-1.0, 4.0]}}}
        return p

    def test_stability_23_2145_sign_thresholds(self):
        """14 CFR 23.2145(a)/(b), text read 2026-10-20: qualitative; only the sign of the stability criteria is checked."""
        self.assertEqual(item(v.evaluate(self.stable_project())[0], "stability_23_2145a")["status"], "cumple")
        self.assertEqual(item(v.evaluate(self.stable_project())[0], "longitudinal_divergence_23_2145b")["status"], "cumple")
        self.assertEqual(item(v.evaluate(self.stable_project(cm_a=0.01))[0], "stability_23_2145a")["status"], "no cumple")      # just above 0
        self.assertEqual(item(v.evaluate(self.stable_project(cm_a=-0.01))[0], "stability_23_2145a")["status"], "cumple")        # just below 0
        self.assertEqual(item(v.evaluate(self.stable_project(cn_b=-0.001))[0], "stability_23_2145a")["status"], "no cumple")
        p = self.stable_project()
        p["outputs"]["m16"]["result"]["lateral_dynamics"]["modes"]["dutch_roll"]["stable"] = False
        it = item(v.evaluate(p)[0], "stability_23_2145a")
        self.assertEqual(it["status"], "no cumple")
        self.assertIn("balanceo holandes estable", it["failed"])
        p = self.stable_project()
        p["outputs"]["m16"]["result"]["longitudinal_dynamics"]["phugoid"]["stable"] = False
        self.assertEqual(item(v.evaluate(p)[0], "longitudinal_divergence_23_2145b")["status"], "no evaluable")
        p = self.stable_project()
        p["inputs"]["m01"]["category"] = "aerobatic"
        self.assertEqual(item(v.evaluate(p)[0], "stability_23_2145a")["status"], "no evaluable")

    def test_missing_modules_are_not_evaluable_not_errors(self):
        p = prj.new_project("x")
        p["inputs"] = {"m01": {}}
        r = v.evaluate(p)[0]
        self.assertEqual(r["overall"], "no evaluable")


class ChainTests(unittest.TestCase):
    def build(self, tmp, mutate=None):
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        if not xfoil_executable():
            data.pop("m18c")
        if mutate:
            mutate(data)
        src = Path(tmp) / "in.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        path = Path(tmp) / "p.json"
        main(["project-init", "--project", str(path), "--name", "c162-full", "--from-inputs", str(src)])
        return path

    def test_loop_reports_cg_failure_and_stops_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = loop.run_loop(self.build(tmp), max_iter=3)
            self.assertEqual(s["m23_overall"], "no cumple")
            m23 = prj.load(Path(tmp) / "p.json")["outputs"]["m23"]["result"]
            self.assertEqual(m23["failed"], ["cg_envelope"])            # illustrative loading above MTOW (M12 empty weight 395 kg)
            self.assertIn("m23", s["plan"])
            self.assertTrue(s["stop"]["reason"].startswith("stable"))

    def test_loop_stops_when_requirements_are_met(self):
        def fix(d):
            d["m13"]["envelope"]["max_mass_kg"] = 700.0
        with tempfile.TemporaryDirectory() as tmp:
            s = loop.run_loop(self.build(tmp, fix), max_iter=3)
            self.assertEqual(s["m23_overall"], "cumple")
            self.assertTrue(s["stop"]["reason"].startswith("requirements_met"))

    def test_export_and_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.build(tmp)
            loop.run_loop(path, max_iter=2)
            out = Path(tmp) / "m23.json"
            main(["export", "--project", str(path), "--module", "m23", "--out", str(out)])
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["module"], "m23")
            data = prj.load(path)
            data["outputs"]["m21"]["result"]["weights"]["mtow_kg"] += 1.0
            self.assertIn("m23", prj.stale(data))


if __name__ == "__main__":
    unittest.main()
