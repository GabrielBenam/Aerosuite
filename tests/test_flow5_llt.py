import json
import math
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

from aerosuite import flow5_xml as fx
from aerosuite import m19_stall as m19

EVID = Path(__file__).resolve().parents[1] / "evidence" / "flow5-7.55-win" / "llt"


def _rows(sub):
    path = EVID / sub / "flow5_results.json"
    return json.loads(path.read_text(encoding="utf-8"))["polars"][0]["rows"]


class LltScriptTests(unittest.TestCase):
    """Format tests of the foil-polar section written for LLT (D-51); not aerodynamic results."""

    def cfg(self):
        return json.loads((EVID / "llt-config.json").read_text(encoding="utf-8")) if EVID.is_dir() else None

    @unittest.skipUnless(EVID.is_dir(), "flow5 LLT evidence not present")
    def test_foil_analysis_section(self):
        cfg = self.cfg()
        text = fx.script_xml(Path("job"), [Path("a.dat")], Path("p.xml"), Path("q.xml"), cfg)
        root = ET.fromstring(text)
        fa = root.find("Foil_analysis")
        self.assertIsNotNone(fa)
        self.assertEqual(fa.findtext("Batch_Analysis_Data/Polar_Type"), "FIXEDSPEEDPOLAR")
        self.assertEqual(len(fa.findtext("Batch_Analysis_Data/Batch_Range/Reynolds").split(",")), 5)
        self.assertEqual(fa.findtext("OpPoint_Range/Alpha").split(",")[2].strip(), "0.5")
        cfg["analysis"].pop("foil_polars")
        self.assertIsNone(ET.fromstring(fx.script_xml(Path("job"), [Path("a.dat")], Path("p.xml"), Path("q.xml"), cfg)).find("Foil_analysis"))


@unittest.skipUnless(EVID.is_dir(), "flow5 LLT evidence not present")
class LltEvidenceTests(unittest.TestCase):
    """Real flow5 7.55 LLT / VLM2 output (evidence/flow5-7.55-win/llt) against the M19 lifting line; nothing tuned."""

    def test_lift_slopes_agree_within_a_few_percent(self):
        llt, v2 = _rows("c-con-polares-2d"), _rows("vlm2-ala-sola-no-viscoso")
        slope = lambda r: np.polyfit(np.radians([x["alpha_deg"] for x in r]), [x["CL"] for x in r], 1)[0]
        cr, ct, span = 1.25, 1.11, 9.44
        azl = math.radians(m19.alpha_zl_naca4_deg("2412"))
        m19_slope = m19.lift_curve_slope(span, lambda e: cr + (ct - cr) * e, lambda e: 2 * math.pi, lambda e: azl,
                                         lambda e: -math.radians(1.5) * e)
        self.assertAlmostEqual(slope(llt), 4.743, delta=0.005)
        self.assertAlmostEqual(slope(v2), 4.650, delta=0.005)
        self.assertLess(abs(m19_slope - slope(v2)) / slope(v2), 0.06)
        self.assertLess(abs(m19_slope - slope(llt)) / slope(llt), 0.06)

    def test_failure_case_has_no_points(self):
        log = next((EVID / "a-sin-polares-2d-falla" / "output").rglob("*.log")).read_text(encoding="utf-8", errors="replace")
        self.assertIn("LLT analysis completed ... Errors encountered", log)


if __name__ == "__main__":
    unittest.main()
