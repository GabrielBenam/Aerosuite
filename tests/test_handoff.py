"""T-1 integration test: full example project (L-1 chain + M24 STEP + M25 + M26) -> `handoff` package. The STEP part needs CadQuery (skipped without it)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from aerosuite import handoff
from aerosuite.__main__ import main

try:
    import cadquery  # noqa: F401
    HAVE_CQ = True
except ImportError:
    HAVE_CQ = False

FULL = Path(__file__).parents[1] / "examples" / "projects" / "c162-full-loop.json"
CHAIN = ["m01", "m02", "m06", "m04", "m09b", "m11", "m18c", "m19", "m08", "m10", "m12", "m13", "m15", "m18a", "m18b", "m20", "m21", "m16", "m03", "m23",
         "m25", "m26"]


def build_project(tmp, with_cad=True):
    data = json.loads(FULL.read_text(encoding="utf-8"))
    data["m25"] = {"category": "normal", "common": {"cl_min": 1.0}}
    data["m26"] = {"out_dir": str(Path(tmp) / "loads")}
    data["m24"] = {"out_dir": str(Path(tmp) / "cad")}
    data.setdefault("m03", json.loads((FULL.parents[0] / "gud-example-2-cost.json").read_text(encoding="utf-8"))["m03"])
    src = Path(tmp) / "in.json"
    src.write_text(json.dumps(data), encoding="utf-8")
    path = Path(tmp) / "p.json"
    main(["project-init", "--project", str(path), "--name", "c162", "--from-inputs", str(src)])
    chain = list(CHAIN)
    if with_cad and HAVE_CQ:
        chain.insert(chain.index("m25"), "m24")
    for m in chain:
        main([m, "--project", str(path)])
    return path


class Handoff(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = build_project(cls.tmp.name)
        cls.out = Path(cls.tmp.name) / "paquete"
        main(["handoff", "--project", str(cls.path), "--out", str(cls.out)])
        cls.man = json.loads((cls.out / "manifest.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_contents(self):
        files = set(self.man["files_sha256"])
        for rel in ("project.json", "LEEME.md", "SUPUESTOS.md", "masas/pesos_cg_inercias.json", "envolvente/envolvente_vn.json", "requisitos/informe_m23.json",
                    "requisitos/informe_m23.md", "cargas/stations.csv", "cargas/loads.json", "costos/nota_costos.txt"):
            self.assertIn(rel, files)
        if HAVE_CQ:
            self.assertTrue(any(f.startswith("cad/") and f.endswith(".step") for f in files))
            self.assertEqual(self.man["missing"], [])

    def test_sha256_matches_files(self):
        for rel, sha in self.man["files_sha256"].items():
            self.assertEqual(hashlib.sha256((self.out / rel).read_bytes()).hexdigest(), sha, rel)

    def test_no_books_or_third_party_binaries(self):
        exts = {p.suffix.lower() for p in self.out.rglob("*") if p.is_file()}
        self.assertTrue(exts <= {".json", ".md", ".txt", ".csv", ".step"}, exts)

    def test_leeme_is_spanish_and_has_cost_note(self):
        text = (self.out / "LEEME.md").read_text(encoding="utf-8")
        self.assertIn("Como usarlo", text)
        self.assertIn("2012", text)
        self.assertIn("milimetros", text)

    def test_supuestos_lists_unvalidated_modules(self):
        text = (self.out / "SUPUESTOS.md").read_text(encoding="utf-8")
        for m in ("M10", "M12", "M25", "M26"):
            self.assertIn(m, text)

    def test_refuses_nonempty_folder_and_flags_stale(self):
        with self.assertRaises(SystemExit):
            handoff.build(self.path, self.out)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        data["inputs"]["m25"]["common"]["cl_min"] = 0.9
        stale_path = Path(self.tmp.name) / "stale.json"
        stale_path.write_text(json.dumps(data), encoding="utf-8")
        man = handoff.build(stale_path, Path(self.tmp.name) / "p2")
        self.assertIn("m25", man["stale_modules"])
        self.assertIn("desactualizados", (Path(self.tmp.name) / "p2" / "LEEME.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
