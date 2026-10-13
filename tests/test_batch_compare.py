import json
import tempfile
import unittest
from pathlib import Path
from aerosuite.batch_compare import Comparison, compare

class ComparisonTests(unittest.TestCase):
    def _fixture(self, root, profile, re=150000):
        (root/f"{profile}.csv").write_text("alpha,cl,cd,cm\n0,0.3,0.02,-0.02\n4,0.7,0.03,-0.01\n",encoding="utf-8")
        (root/f"{profile}.json").write_text(json.dumps({"reynolds":re,"mach":0.0,"ncrit":9.0,
            "xtr_top":1.0,"xtr_bottom":1.0,"solver":"test fixture","converged":True}),encoding="utf-8")

    def test_ranking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self._fixture(root,"ag03")
            self._fixture(root,"ag04")
            result=compare(Comparison(("ag03","ag04"),root,root/"report"),charts=False)
            self.assertEqual(len(result["ranking"]),2)
            self.assertTrue((root/"report"/"comparison.json").exists())

    def test_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self._fixture(root,"ag03")
            self._fixture(root,"ag04",re=160000)
            with self.assertRaises(ValueError):
                compare(Comparison(("ag03","ag04"),root,root/"report"),charts=False)
            self.assertFalse((root/"report"/"comparison.json").exists())

    def test_missing_data_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self._fixture(root,"ag03")
            with self.assertRaises(FileNotFoundError):
                compare(Comparison(("ag03","ag04"),root,root/"report"),charts=False)

    def test_duplicate_profiles_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(ValueError):
                compare(Comparison(("ag03","ag03"),root,root/"out"),charts=False)

    def test_unconverged_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self._fixture(root,"ag03")
            self._fixture(root,"ag04")
            path=root/"ag04.json"
            j=json.loads(path.read_text())
            j["converged"]=False
            path.write_text(json.dumps(j))
            with self.assertRaises(ValueError):
                compare(Comparison(("ag03","ag04"),root,root/"out"),charts=False)

if __name__=="__main__":
    unittest.main()
