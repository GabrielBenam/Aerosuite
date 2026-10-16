"""M18c tests: Gudmundsson Example 10-2 (prorating, 3.01), Eq. 10-2 arithmetic with the printed Example 10-3 sum (1.936), Eq. 10-1 values,
partition geometry, the project chain with data-declared increments, and (when a real XFOIL executable is present) the flapped section
against thin-airfoil theory. The XFOIL test is skipped without the executable; nothing here is a synthetic aerodynamic result."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from aerosuite import project as prj
from aerosuite.__main__ import main
from aerosuite.airfoils import naca4
from aerosuite.engines import xfoil_executable
from aerosuite import m18c_highlift as h

EXAMPLE = Path(__file__).parents[1] / "examples" / "projects" / "c172-like-highlift-inputs.json"


class BookTests(unittest.TestCase):
    def test_example_10_2_prorating(self):
        # NACA 65(215)-114 data: dClmax = 1.65 at delta = 40 deg, cf/c = 0.256; target cf/c = 0.30, delta = 32 deg, Re factor 0.90
        clmax = h.prorate_clmax(1.62, 1.65, 0.30, 0.256, 32.0, 40.0, 0.90)
        self.assertAlmostEqual(clmax, 3.01, delta=0.01)

    def test_example_10_3_arithmetic_with_printed_sum(self):
        # printed: C_Lmax = 0.9 * 2 * 155.81 / 144.9 = 1.936 (155.81 ft2 = sum of C_l,i S_i of ONE semi-wing, read from the example)
        seg = [{"flapped": False, "cl_unflapped_at_stall": 1.0, "area_m2": 155.81}]
        self.assertAlmostEqual(h.wing_partition_clmax(seg, 144.9), 1.936, delta=0.001)
        self.assertAlmostEqual(1.936 / 1.99, 0.973, delta=0.001)                      # 97.3 % of the POH value

    def test_eq_10_1_values(self):
        self.assertAlmostEqual(h.plain_flap_clmax(0.1, 0.0), 1.262)
        self.assertAlmostEqual(h.plain_flap_clmax(0.2, 20.0), 1.234 + 0.02216 * 20.0 - 1.611e-4 * 400.0)
        with self.assertRaises(ValueError):
            h.plain_flap_clmax(0.3, 10.0)


class PartitionTests(unittest.TestCase):
    def test_geometry_conserves_area(self):
        s, b, cr, ct = 16.0, 10.0, 2.0, 1.2
        parts = [h.segment_geometry(b, cr, ct, a, c)["area_m2"] for a, c in ((0, 0.3), (0.3, 0.7), (0.7, 1.0))]
        self.assertAlmostEqual(2 * sum(parts), 0.5 * (cr + ct) * b)

    def test_hand_computed_partition(self):
        segs = [{"flapped": True, "clmax_i": 2.4, "area_m2": 3.0, "hinge_sweep_deg": 0.0},
                {"flapped": False, "cl_unflapped_at_stall": 1.5, "area_m2": 5.0}]
        self.assertAlmostEqual(h.wing_partition_clmax(segs, 16.0), 0.9 * 2.0 * (2.4 * 3.0 + 1.5 * 5.0) / 16.0)

    def test_hinge_sweep_penalizes(self):
        a = [{"flapped": True, "clmax_i": 2.4, "area_m2": 3.0, "hinge_sweep_deg": 0.0}]
        b = [{"flapped": True, "clmax_i": 2.4, "area_m2": 3.0, "hinge_sweep_deg": 20.0}]
        self.assertAlmostEqual(h.wing_partition_clmax(b, 6.0) / h.wing_partition_clmax(a, 6.0), math.cos(math.radians(20.0)))

    def test_alpha0l_interpolation(self):
        rows = [{"alpha": -2.0, "cl": -0.2}, {"alpha": 0.0, "cl": 0.2}, {"alpha": 2.0, "cl": 0.6}]
        self.assertAlmostEqual(h.alpha0l_from_rows(rows), -1.0)


class ProjectTests(unittest.TestCase):
    def build(self, tmp, mutate):
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        mutate(data)
        src = Path(tmp) / "in.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        path = Path(tmp) / "p.json"
        main(["project-init", "--project", str(path), "--name", "h", "--from-inputs", str(src)])
        for mod in ("m09b", "m18c"):
            main([mod, "--project", str(path)])
        return path

    @staticmethod
    def declared(d):
        t = {"d_clmax": 1.65, "cf_over_c": 0.256, "delta_deg": 40.0, "reference": "test data (Example 10-2 numbers)"}
        d["m18c"]["configurations"] = {"takeoff": {"source": "direct", "d_clmax": 0.5, "delta_deg": 10.0},
                                       "landing": {"source": "table_10_5", "table": t, "delta_deg": 32.0, "factor": 0.9}}
        d["m18c"]["required"] = {"landing": 1.4}

    def test_chain_with_declared_increments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.build(tmp, self.declared)
            data = prj.load(path)
            r = data["outputs"]["m18c"]["result"]
            self.assertEqual(sorted(data["outputs"]["m18c"]["run"]["depends_on"]), ["m09b"])
            self.assertEqual(prj.stale(data), [])
            to, ld = r["configurations"]["takeoff"], r["configurations"]["landing"]
            self.assertGreater(to["cl_max_wing"], to["cl_max_wing_clean_same_method"] - 1e-9)
            self.assertGreater(ld["delta_cl_max"], to["delta_cl_max"])
            self.assertAlmostEqual(r["configurations"]["landing"]["area_covered_pct"], 100.0, places=6)
            self.assertIn("landing", r["requirements"])
            data["outputs"]["m09b"]["result"]["planform"]["area_m2"] += 0.1
            self.assertIn("m18c", prj.stale(data))
            out = Path(tmp) / "m18c.json"
            main(["export", "--project", str(path), "--module", "m18c", "--out", str(out)])
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["module"], "m18c")

    def test_unknown_source_is_rejected(self):
        def mutate(d):
            d["m18c"]["configurations"] = {"landing": {"source": "magic", "delta_deg": 30.0}}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                self.build(tmp, mutate)


@unittest.skipUnless(xfoil_executable(), "real XFOIL executable not found (AEROSUITE_XFOIL or tools/xfoil)")
class RealXfoilTests(unittest.TestCase):
    def test_flapped_naca2412_against_thin_airfoil_theory(self):
        exe = xfoil_executable()
        coords = naca4("2412")
        clean = h.xfoil_flapped_section(exe, coords, 0.3, 0.0, 3.0e6, -2.0, 6.0, 2.0)
        flap = h.xfoil_flapped_section(exe, coords, 0.3, 10.0, 3.0e6, -2.0, 6.0, 2.0)
        cl0 = lambda rows: next(r["cl"] for r in rows if abs(r["alpha"]) < 1e-9)
        d_cl0 = cl0(flap["rows"]) - cl0(clean["rows"])
        theta = math.acos(1.0 - 2.0 * 0.7)                                   # hinge at x/c = 0.70
        tau = 1.0 - (theta - math.sin(theta)) / math.pi                      # thin-airfoil flap effectiveness (~0.66)
        theory = 2.0 * math.pi * tau * math.radians(10.0)
        self.assertGreater(d_cl0, 0.0)
        self.assertGreater(d_cl0 / theory, 0.4)                              # viscous XFOIL gives less than inviscid theory
        self.assertLess(d_cl0 / theory, 1.05)


if __name__ == "__main__":
    unittest.main()
