"""M13 tests against Gudmundsson Chapter 6 (Examples 6-8, 6-9, 6-10; Table 6-5 and Table 6-10 read from the figures).
Inertia equations have no solved example in the book: they are checked against classical mechanics (independent source)."""
import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite import m13_cg as m

EXAMPLE = Path(__file__).parents[1] / "examples" / "projects" / "c172-like-cg-inputs.json"
# Table 6-5 (GUD PDF 224): W (lbf), x, y, z (ft). The equations are linear in W, so weights are passed as "mass".
TABLE_6_5 = [(3.25, 5.0, 3.0, 1.0), (7.50, 3.5, -2.0, 3.0), (2.50, 6.5, -2.5, -2.0), (1.25, 10.0, 3.0, -2.5),
             (5.00, 12.0, -3.0, 1.5), (2.50, 8.0, -1.0, -3.5), (2.50, 7.5, 4.0, -4.0)]
ITEMS_6_5 = [{"mass_kg": w, "x_m": x, "y_m": y, "z_m": z} for w, x, y, z in TABLE_6_5]


class BookExampleTests(unittest.TestCase):
    def test_example_6_8_cg_as_percent_of_mgc(self):
        # CG at FS 191.3 in, LE of the MGC at FS 185 in, c_MGC = 6.32 ft -> 8.31 % MGC
        self.assertAlmostEqual(m.pct_mgc(191.3, 185.0, 6.32 * 12.0), 8.31, delta=0.005)

    def test_example_6_9_point_loads(self):
        self.assertAlmostEqual(m.total_weight(ITEMS_6_5), 24.50)
        mx, my, mz = m.moments(ITEMS_6_5)
        self.assertAlmostEqual(mx, 170.0)
        self.assertAlmostEqual(my, -15.25)
        self.assertAlmostEqual(mz, 6.38, delta=0.005)                                       # book 6.38
        x, y, z = m.cg_location(ITEMS_6_5)
        self.assertAlmostEqual(x, 6.939, delta=0.001)
        self.assertAlmostEqual(y, -0.622, delta=0.001)
        self.assertAlmostEqual(z, 0.260, delta=0.001)

    def test_example_6_10_tolerances(self):
        # Table 6-10: W +- dW (lbf) at x +- dx (ft): (10 +- 2) at 5.0 +- 0.5, (20 +- 1) at 3.5 +- 0.5, (30 +- 2) at 8.5 +- 0.5
        items = [{"mass_kg": 10.0, "dw_kg": 2.0, "x_m": 5.0, "dx_m": 0.5, "y_m": 0.0, "z_m": 0.0},
                 {"mass_kg": 20.0, "dw_kg": 1.0, "x_m": 3.5, "dx_m": 0.5, "y_m": 0.0, "z_m": 0.0},
                 {"mass_kg": 30.0, "dw_kg": 2.0, "x_m": 8.5, "dx_m": 0.5, "y_m": 0.0, "z_m": 0.0}]
        t = m.cg_with_tolerances(items)
        self.assertEqual([t["min"]["weight_kg"], t["nom"]["weight_kg"], t["max"]["weight_kg"]], [55.0, 60.0, 65.0])
        self.assertAlmostEqual(t["min"]["moments"][0], 317.0)
        self.assertAlmostEqual(t["nom"]["moments"][0], 375.0)
        self.assertAlmostEqual(t["max"]["moments"][0], 438.0)
        self.assertAlmostEqual(t["min"]["cg"][0], 5.764, delta=0.001)                        # book 5.764
        self.assertAlmostEqual(t["nom"]["cg"][0], 6.250, delta=0.001)                        # book 6.250
        self.assertAlmostEqual(t["max"]["cg"][0], 6.738, delta=0.001)                        # book 6.738

    def test_weighing_statics(self):
        r = m.cg_from_weighing(r_main=800.0, r_nose=200.0, x_nm=2.0)                         # Eqs. 6-138, 6-139
        self.assertAlmostEqual(r["x_from_nose_gear"], 1.6)
        self.assertAlmostEqual(r["x_from_main_gear"], 0.4)
        self.assertAlmostEqual(r["x_from_nose_gear"] + r["x_from_main_gear"], 2.0)
        self.assertAlmostEqual(r["nose_gear_fraction"], 0.2)


class InertiaTests(unittest.TestCase):
    def test_dumbbell_and_parallel_axis(self):
        # two equal masses at x = +-a on the x-axis: I_yy = I_zz = 2 m a^2, I_xx = 0, no products
        a, mm = 1.5, 3.0
        items = [{"mass_kg": mm, "x_m": a + 10, "y_m": 2.0, "z_m": -1.0}, {"mass_kg": mm, "x_m": -a + 10, "y_m": 2.0, "z_m": -1.0}]
        i = m.inertia(items)
        self.assertAlmostEqual(i["iyy"], 2 * mm * a * a)
        self.assertAlmostEqual(i["izz"], 2 * mm * a * a)
        self.assertAlmostEqual(i["ixx"], 0.0)
        self.assertEqual((i["ixy"], i["ixz"], i["iyz"]), (0.0, 0.0, 0.0))
        # Eq. 6-145 (parallel-axis): about a point displaced d from the CG, I = I_cg + M d^2
        cg = m.cg_location(items)
        about = m.inertia(items, cg=(cg[0], cg[1] + 4.0, cg[2]))
        self.assertAlmostEqual(about["ixx"], i["ixx"] + 2 * mm * 16.0)

    def test_own_inertia_is_added(self):
        i = m.inertia([{"mass_kg": 5.0, "x_m": 1.0, "y_m": 0.0, "z_m": 0.0, "i_xx": 0.7, "i_xy": 0.1}], cg=(1.0, 0.0, 0.0))
        self.assertAlmostEqual(i["ixx"], 0.7)
        self.assertAlmostEqual(i["ixy"], 0.1)

    def test_uniform_rod_discretised_against_analytic(self):
        # uniform rod of length L along x, mass M: I_yy = M L^2 / 12 about its centre; n point masses converge as 1/n^2
        L, M, n = 4.0, 10.0, 400
        items = [{"mass_kg": M / n, "x_m": L * (k + 0.5) / n, "y_m": 0.0, "z_m": 0.0} for k in range(n)]
        self.assertAlmostEqual(m.inertia(items)["iyy"], M * L * L / 12.0, delta=M * L * L / 12.0 * 1e-4)

    def test_rotation_equations_match_direct_computation(self):
        rng = np.random.default_rng(7)
        pts = [(float(w), float(x), float(y)) for w, x, y in zip(rng.uniform(1, 3, 12), rng.uniform(-2, 2, 12), rng.uniform(-1, 1, 12))]
        items = [{"mass_kg": w, "x_m": x, "y_m": y, "z_m": 0.0} for w, x, y in pts]
        cg = m.cg_location(items)
        base = m.inertia(items, cg)
        th = math.radians(27.0)
        rot = m.rotate_planar(base["izz"] * 0 + base["ixx"], base["iyy"], base["ixy"], th)
        # direct: express the points in axes rotated by th about the CG and recompute I_uu, I_vv, I_uv
        c, s = math.cos(th), math.sin(th)
        rotated = []
        for w, x, y in pts:
            dx, dy = x - cg[0], y - cg[1]
            rotated.append({"mass_kg": w, "x_m": c * dx + s * dy, "y_m": -s * dx + c * dy, "z_m": 0.0})
        d = m.inertia(rotated, cg=(0.0, 0.0, 0.0))
        self.assertAlmostEqual(rot["iuu"], d["ixx"], places=9)
        self.assertAlmostEqual(rot["ivv"], d["iyy"], places=9)
        self.assertAlmostEqual(rot["iuv"], d["ixy"], places=9)
        # principal angle: I_uv = 0 and I_uu, I_vv are the extreme values (eigenvalues of the 2x2 inertia tensor)
        p = m.rotate_planar(base["ixx"], base["iyy"], base["ixy"], rot["theta_principal_rad"])
        self.assertAlmostEqual(p["iuv"], 0.0, places=9)
        eig = sorted(np.linalg.eigvalsh(np.array([[base["ixx"], -base["ixy"]], [-base["ixy"], base["iyy"]]])))
        self.assertAlmostEqual(min(p["iuu"], p["ivv"]), eig[0], places=9)
        self.assertAlmostEqual(max(p["iuu"], p["ivv"]), eig[1], places=9)

    def test_matrix_symmetry_and_principal_invariants(self):
        rng = np.random.default_rng(11)
        items = [{"mass_kg": float(w), "x_m": float(x), "y_m": float(y), "z_m": float(z)}
                 for w, x, y, z in zip(rng.uniform(1, 5, 20), rng.uniform(-3, 3, 20), rng.uniform(-2, 2, 20), rng.uniform(-1, 1, 20))]
        i = m.inertia(items)
        mat = m.inertia_matrix(i)
        self.assertTrue(np.allclose(mat, mat.T))
        pr = m.principal_moments(i)
        self.assertAlmostEqual(sum(pr["moments_kgm2"]), np.trace(mat))                          # trace is invariant
        self.assertTrue(all(v > 0 for v in pr["moments_kgm2"]))
        # triangle inequality of rigid-body principal moments: I1 + I2 >= I3
        a, b, c = sorted(pr["moments_kgm2"])
        self.assertGreaterEqual(a + b + 1e-9, c)


class EnvelopeTests(unittest.TestCase):
    def test_polygon_and_box_envelope(self):
        env = m.box_envelope(600.0, 1100.0, 15.0, 35.0)
        self.assertTrue(m.point_in_polygon(25.0, 900.0, env))
        self.assertFalse(m.point_in_polygon(36.0, 900.0, env))
        self.assertFalse(m.point_in_polygon(25.0, 1200.0, env))
        self.assertFalse(m.point_in_polygon(25.0, 500.0, env))

    def test_loading_cloud_arithmetic(self):
        # algorithm fixture: empty airplane 600 kg at x = 0.40 m; MGC LE at 0.0, c_MGC = 1.5 m
        rows = m.loading_cloud({"mass_kg": 600.0, "x_m": 0.40}, {"pilot": 0.2, "bag": 1.8},
                               [{"id": "a", "loads": {"pilot": 80.0}}, {"id": "b", "loads": {"bag": 100.0}}], 0.0, 1.5,
                               m.box_envelope(600.0, 800.0, 20.0, 30.0))
        self.assertAlmostEqual(rows[0]["x_cg_m"], (600 * 0.40 + 80 * 0.2) / 680.0)
        self.assertAlmostEqual(rows[0]["cg_pct_mgc"], 100.0 * rows[0]["x_cg_m"] / 1.5)
        self.assertTrue(rows[0]["inside_envelope"] is False or rows[0]["inside_envelope"] is True)
        self.assertGreater(rows[1]["cg_pct_mgc"], rows[0]["cg_pct_mgc"])                       # baggage moves the CG aft
        self.assertFalse(rows[1]["inside_envelope"])                                            # 100 kg in the rear goes aft of 30 %


class ProjectTests(unittest.TestCase):
    def build(self, tmp, mutate=None, mods=("m09b", "m08", "m10", "m12", "m13")):
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        if mutate:
            mutate(data)
        src = Path(tmp) / "in.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        path = Path(tmp) / "p.json"
        main(["project-init", "--project", str(path), "--name", "cg", "--from-inputs", str(src)])
        for mod in mods:
            main([mod, "--project", str(path)])
        return path

    def test_chain_m12_m13(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = prj.load(self.build(tmp))
            r, m12 = data["outputs"]["m13"]["result"], data["outputs"]["m12"]["result"]
            self.assertAlmostEqual(r["total_mass_kg"], m12["empty_weight_kg"], places=9)        # items come from M12
            self.assertEqual(sorted(data["outputs"]["m13"]["run"]["depends_on"]), ["m09b", "m12"])
            self.assertEqual(prj.stale(data), [])
            self.assertAlmostEqual(r["cg_pct_mgc"], m.pct_mgc(r["cg_m"][0], r["reference"]["x_mgc_le_m"], r["reference"]["c_mgc_m"]))
            self.assertEqual(len(r["loading_cloud"]), 3)
            self.assertTrue(r["envelope"]["empty_cg_inside"])
            self.assertIn("limits come from stability" if False else "stability and control", r["envelope"]["note"])
            self.assertTrue(np.allclose(np.array(r["inertia_matrix_kgm2"]), np.array(r["inertia_matrix_kgm2"]).T))
            # staleness: changing M12 inputs marks M13 once M12 is re-run
            data["outputs"]["m12"]["result"]["empty_weight_kg"] += 1.0
            self.assertIn("m13", prj.stale(data))

    def test_missing_positions_are_reported_not_guessed(self):
        def mut(d):
            d["m13"]["positions_m"].pop("wing")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as cm:
                self.build(tmp, mut)
            self.assertIn("wing", str(cm.exception))

    def test_envelope_without_limits_reports_only_the_cloud(self):
        def mut(d):
            d["m13"].pop("envelope")
        with tempfile.TemporaryDirectory() as tmp:
            r = prj.load(self.build(tmp, mut))["outputs"]["m13"]["result"]
            self.assertNotIn("envelope", r)
            self.assertNotIn("loading_cloud_outside", r)
            self.assertEqual(len(r["loading_cloud"]), 3)

    def test_weighing_and_tolerance_blocks(self):
        def mut(d):
            d["m13"]["weighing"] = {"main_gear_reaction": 800.0, "nose_gear_reaction": 200.0, "gear_spacing_m": 1.7}
            d["m13"]["items"] = [{"name": "battery", "mass_kg": 10.0, "dw_kg": 1.0, "x_m": -0.5, "dx_m": 0.05, "y_m": 0.0, "z_m": 0.0}]
        with tempfile.TemporaryDirectory() as tmp:
            r = prj.load(self.build(tmp, mut))["outputs"]["m13"]["result"]
            self.assertAlmostEqual(r["weighing"]["x_from_nose_gear"], 800.0 * 1.7 / 1000.0)
            self.assertLess(r["tolerances"]["min"]["weight_kg"], r["tolerances"]["max"]["weight_kg"])


if __name__ == "__main__":
    unittest.main()
