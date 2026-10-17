import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from aerosuite import flow5_xml as fx
from aerosuite import m16_stability as m

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "examples" / "flow5-c162-like-fuselage.json"


class FuselageXmlTests(unittest.TestCase):
    """Format tests of the <body> element (structure of vendor/flow5 PlaneRun4 plane.xml); not aerodynamic results."""

    def test_body_element_structure(self):
        cfg = json.loads(CFG.read_text(encoding="utf-8"))
        root = ET.fromstring(fx.plane_xml(cfg))
        body = root.find("Plane/body")
        self.assertIsNotNone(body)
        self.assertEqual(body.findtext("Type"), "NURBS")
        frames = body.findall("NURBS/frame")
        self.assertEqual(len(frames), len(cfg["fuselage"]["stations"]))
        self.assertTrue(all(len(f.findall("point")) == 5 for f in frames))
        # mid frame: top, quarter points and bottom of the +y half ellipse (width 1.1 m, height 1.3 m)
        pts = [[float(v) for v in p.text.split(",")] for p in frames[3].findall("point")]
        self.assertAlmostEqual(pts[0][2], 0.65, places=5)
        self.assertAlmostEqual(pts[2][1], 0.55, places=5)
        self.assertAlmostEqual(pts[4][2], -0.65, places=5)
        # the body comes before the wings, as in flow5's writer
        names = [e.tag for e in root.find("Plane")]
        self.assertLess(names.index("body"), names.index("wing"))

    def test_nose_tip_frame_is_degenerate(self):
        cfg = json.loads(CFG.read_text(encoding="utf-8"))
        root = ET.fromstring(fx.plane_xml(cfg))
        pts = {p.text for p in root.findall("Plane/body/NURBS/frame")[0].findall("point")}
        self.assertEqual(len(pts), 1)

    def test_without_fuselage_no_body(self):
        cfg = json.loads(CFG.read_text(encoding="utf-8"))
        cfg.pop("fuselage")
        self.assertIsNone(ET.fromstring(fx.plane_xml(cfg)).find("Plane/body"))

    def test_unordered_stations_rejected(self):
        with self.assertRaises(ValueError):
            fx.fuselage_xml({"stations": [{"x_m": 1, "width_m": 1, "height_m": 1}, {"x_m": 0, "width_m": 1, "height_m": 1}]})


class SignRegressionTests(unittest.TestCase):
    """F5 sign fix (D-44): only the fuselage term moves the neutral point; without it h_n is the wing-tail value."""

    def test_no_fuselage_unchanged_and_destabilising_fuselage_moves_np_forward(self):
        a_w, a_h, ar, v = 4.9058, 3.8832, 7.99, 0.6722
        base = m.neutral_point(a_w, a_h, ar, v)
        self.assertAlmostEqual(base["h_n"], base["h_n_wing_ht"], places=12)
        fus = m.neutral_point(a_w, a_h, ar, v, dcm_alpha_fuselage=0.2)       # C_M_alpha,fus > 0 (destabilising)
        self.assertAlmostEqual(base["h_n"] - fus["h_n"], 0.2 / a_w, places=12)
        self.assertEqual(fus["tail_contribution"], base["tail_contribution"])
        self.assertAlmostEqual(m.cm_alpha(a_w, a_h, ar, v, 0.3, dcm_alpha_fuselage=0.2) - m.cm_alpha(a_w, a_h, ar, v, 0.3), 0.2, places=12)


if __name__ == "__main__":
    unittest.main()
