"""Optional interface to an external real XFOIL executable (not bundled)."""
from __future__ import annotations
import csv
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from .airfoils import naca4
from .uiuc_library import Airfoil, parse_selig

SOURCE_URL = "https://web.mit.edu/drela/Public/web/xfoil/"
PROFILE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class XFoilCase:
    reynolds: float = 1000000.0
    mach: float = 0.0
    ncrit: float = 9.0
    alpha_start: float = -2.0
    alpha_end: float = 8.0
    alpha_step: float = 2.0
    iterations: int = 150

    def validate(self) -> None:
        numbers = (self.reynolds,self.mach,self.ncrit,self.alpha_start,self.alpha_end,self.alpha_step)
        if not all(math.isfinite(x) for x in numbers):
            raise ValueError("Non-finite XFOIL operating condition")
        if self.reynolds <= 0 or not 0 <= self.mach < 1 or not 0 < self.ncrit <= 20:
            raise ValueError("Invalid Reynolds, Mach or Ncrit")
        if not 0 < self.alpha_step <= 10 or self.alpha_end < self.alpha_start:
            raise ValueError("Invalid alpha range")
        if (self.alpha_end-self.alpha_start)/self.alpha_step > 150:
            raise ValueError("Requested sweep is too large")
        if type(self.iterations) is not int or not 1 <= self.iterations <= 500:
            raise ValueError("Invalid XFOIL iteration limit")

    def angles(self) -> list[float]:
        self.validate()
        n = int(math.floor((self.alpha_end-self.alpha_start)/self.alpha_step+1e-8))+1
        return [self.alpha_start+i*self.alpha_step for i in range(n)]


def load_uiuc_selected(archive: Path, names: list[str]) -> list[tuple[str,Airfoil]]:
    """Read selected profiles from the user-downloaded UIUC Selig-format ZIP."""
    if not names or len({n.lower() for n in names}) != len(names):
        raise ValueError("Require unique UIUC IDs")
    if any(not PROFILE_ID.fullmatch(n) for n in names):
        raise ValueError("Invalid UIUC identifier")
    selected = {n.lower() for n in names}
    collected: dict[str,Airfoil] = {}
    with ZipFile(archive) as zf:
        for entry in zf.infolist():
            if entry.is_dir() or not entry.filename.lower().endswith(".dat"):
                continue
            key = Path(entry.filename).stem.lower()
            if key not in selected:
                continue
            if key in collected or entry.file_size > 1_000_000:
                raise ValueError("Duplicate or oversized UIUC file: "+entry.filename)
            # No ZIP files are extracted to disk.
            data = zf.read(entry).decode("utf-8-sig",errors="replace")
            collected[key] = parse_selig(data,entry.filename)
    missing = [n for n in names if n.lower() not in collected]
    if missing:
        raise ValueError("UIUC IDs not found: "+str(missing))
    return [(n.lower(),collected[n.lower()]) for n in names]


def load_naca_selected(codes: list[str]) -> list[tuple[str,Airfoil]]:
    if not codes or len(set(codes))!=len(codes):
        raise ValueError("NACA codes must be unique")
    return [("naca"+c,Airfoil("NACA "+c,"naca"+c+".dat",tuple(naca4(c)))) for c in codes]


def make_script(case: XFoilCase) -> str:
    """Command stream for original XFOIL in headless mode."""
    case.validate()
    return "\n".join([
        "PLOP","G","", "LOAD foil.dat","PANE","OPER",
        f"VISC {case.reynolds:.12g}", f"MACH {case.mach:.12g}",
        "VPAR", f"N {case.ncrit:.12g}","",
        f"ITER {case.iterations}","PACC","polar.txt","",
        f"ASEQ {case.alpha_start:.12g} {case.alpha_end:.12g} {case.alpha_step:.12g}",
        "PACC","","QUIT",""
    ])


def parse_polar(data: str) -> list[dict[str,float]]:
    """Read XFOIL saved polar text: alpha, CL, CD, CDp, CM, Top_Xtr, Bot_Xtr."""
    header = False
    values = []
    for line in data.splitlines():
        if not header:
            if line.lower().split()[:5] == ["alpha","cl","cd","cdp","cm"]:
                header = True
            continue
        fields = line.split()
        if len(fields) != 7:
            continue
        try:
            row = [float(v) for v in fields]
        except ValueError:
            continue
        if not all(math.isfinite(v) for v in row) or row[2] <= 0:
            continue
        values.append({"alpha":row[0],"cl":row[1],"cd":row[2],"cm":row[4]})
    if not header or not values:
        raise ValueError("XFOIL output has no recognizable usable polar")
    if len({row["alpha"] for row in values})!=len(values):
        raise ValueError("XFOIL output has duplicate alpha values")
    return sorted(values,key=lambda r:r["alpha"])


def all_angles_present(rows: list[dict[str,float]], case: XFoilCase) -> bool:
    actual = [r["alpha"] for r in rows]
    return all(any(abs(a-b)<=0.001 for b in actual) for a in case.angles())


def run_profile(exe: Path, identifier: str, foil: Airfoil,
                case: XFoilCase, out: Path, timeout: int = 180) -> dict:
    """Execute real XFOIL and write actual CSV + provenance JSON.

    Incomplete sweeps are marked converged=False, and the AeroSuite comparator
    rejects them. Physical accuracy still requires independent validation.
    """
    case.validate()
    if not PROFILE_ID.fullmatch(identifier):
        raise ValueError("Invalid profile ID")
    if not exe.is_file():
        raise FileNotFoundError("Missing XFOIL executable: "+str(exe))
    if timeout <= 0:
        raise ValueError("Timeout must be positive")
    out.mkdir(parents=True,exist_ok=True)
    paths = {ext:out/(identifier+"."+ext) for ext in ("csv","json","polar","log")}
    if any(path.exists() for path in paths.values()):
        raise FileExistsError("Result already exists for "+identifier)
    with TemporaryDirectory(prefix="aerosuite-xfoil-") as tmp:
        work = Path(tmp)
        dat = ("AeroSuite\n"+"".join(f"{x:.9f} {y:.9f}\n" for x,y in foil.coordinates)).encode("ascii")
        (work/"foil.dat").write_bytes(dat)
        try:
            proc = subprocess.run([str(exe.resolve())],input=make_script(case),cwd=work,
                                  text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                  timeout=timeout,errors="replace")
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("XFOIL timed out for "+identifier) from exc
        paths["log"].write_text((proc.stdout or "")[-250000:],encoding="utf-8")
        polar_file = work/"polar.txt"
        if proc.returncode!=0 or not polar_file.is_file():
            raise RuntimeError("XFOIL did not create a polar; see "+str(paths["log"]))
        polar = polar_file.read_text(encoding="utf-8",errors="replace")
        rows = parse_polar(polar)
        paths["polar"].write_text(polar,encoding="utf-8")
        with paths["csv"].open("w",newline="",encoding="utf-8") as output:
            writer = csv.DictWriter(output,fieldnames=("alpha","cl","cd","cm"))
            writer.writeheader()
            writer.writerows(rows)
        complete = all_angles_present(rows,case)
        metadata = {
            "solver":"External XFOIL executable (binary version unverified)",
            "solver_source":SOURCE_URL,
            "solver_sha256":hashlib.sha256(exe.read_bytes()).hexdigest(),
            "geometry_sha256":hashlib.sha256(dat).hexdigest(),
            "geometry_source":foil.source_file,
            "reynolds":case.reynolds, "mach":case.mach, "ncrit":case.ncrit,
            "xtr_top":1.0, "xtr_bottom":1.0,
            "alpha_start":case.alpha_start,"alpha_end":case.alpha_end,
            "alpha_step":case.alpha_step,"iterations":case.iterations,
            "points_requested":len(case.angles()),"points_returned":len(rows),
            "converged":complete,
            "note":("Requested angles recorded; not independent physical validation"
                    if complete else "Some angles missing; excluded from comparison")
        }
        paths["json"].write_text(json.dumps(metadata,indent=2),encoding="utf-8")
        return metadata
