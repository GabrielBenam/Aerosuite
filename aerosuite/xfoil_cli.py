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
    xtr_top: float = 1.0
    xtr_bottom: float = 1.0
    from_zero: bool = False

    def validate(self) -> None:
        numbers = (self.reynolds,self.mach,self.ncrit,self.alpha_start,self.alpha_end,
                   self.alpha_step,self.xtr_top,self.xtr_bottom)
        if not all(math.isfinite(x) for x in numbers):
            raise ValueError("Non-finite XFOIL operating condition")
        if self.reynolds <= 0 or not 0 <= self.mach < 1 or not 0 < self.ncrit <= 20:
            raise ValueError("Invalid Reynolds, Mach or Ncrit")
        if not (0 <= self.xtr_top <= 1 and 0 <= self.xtr_bottom <= 1):
            raise ValueError("Forced transition Xtr/c must be within [0,1]")
        if not 0 < self.alpha_step <= 10 or self.alpha_end < self.alpha_start:
            raise ValueError("Invalid alpha range")
        if (self.alpha_end-self.alpha_start)/self.alpha_step > 150:
            raise ValueError("Requested sweep is too large")
        if type(self.iterations) is not int or not 1 <= self.iterations <= 500:
            raise ValueError("Invalid XFOIL iteration limit")

    def angles(self) -> list[float]:
        self.validate()
        n = int(math.floor((self.alpha_end-self.alpha_start)/self.alpha_step+1e-8))+1
        return [round(self.alpha_start+i*self.alpha_step, 10) for i in range(n)]

    def branches(self) -> list[tuple[float,float,float]]:
        """ASEQ sweeps. With from_zero, two independent XFOIL runs start at 0 deg
        (0 -> alpha_end and -step -> alpha_start), which normally improves
        convergence of the viscous solution near stall in both directions."""
        self.validate()
        if self.from_zero and self.alpha_start < 0 < self.alpha_end:
            return [(0.0, self.alpha_end, self.alpha_step),
                    (-self.alpha_step, self.alpha_start, -self.alpha_step)]
        return [(self.alpha_start, self.alpha_end, self.alpha_step)]


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


def make_script(case: XFoilCase, sweep: tuple[float,float,float] | None = None) -> str:
    """Command stream for original XFOIL in headless mode (graphics disabled)."""
    case.validate()
    a0,a1,da = sweep if sweep is not None else case.branches()[0]
    return "\n".join([
        "PLOP","G","", "LOAD foil.dat","PANE","OPER",
        f"VISC {case.reynolds:.12g}", f"MACH {case.mach:.12g}",
        "VPAR", f"N {case.ncrit:.12g}", f"XTR {case.xtr_top:.12g} {case.xtr_bottom:.12g}","",
        f"ITER {case.iterations}","PACC","polar.txt","",
        f"ASEQ {a0:.12g} {a1:.12g} {da:.12g}",
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
        if len(fields) not in (7, 9):
            continue
        try:
            row = [float(v) for v in fields]
        except ValueError:
            continue
        if not all(math.isfinite(v) for v in row) or row[2] <= 0:
            continue
        values.append({"alpha":row[0],"cl":row[1],"cd":row[2],"cm":row[4],
                       "cdp":row[3],"xtr_top":row[5],"xtr_bottom":row[6]})
    if not header or not values:
        raise ValueError("XFOIL output has no recognizable usable polar")
    if len({row["alpha"] for row in values})!=len(values):
        raise ValueError("XFOIL output has duplicate alpha values")
    return sorted(values,key=lambda r:r["alpha"])


def missing_angles(rows: list[dict[str,float]], case: XFoilCase) -> list[float]:
    """Requested angles for which XFOIL returned no converged point."""
    actual = [r["alpha"] for r in rows]
    return [a for a in case.angles() if not any(abs(a-b)<=0.001 for b in actual)]


VERSION_LINE = re.compile(r"XFOIL\s+Version\s+([0-9.]+)")


def solver_version(log: str) -> str | None:
    match = VERSION_LINE.search(log or "")
    return match.group(1) if match else None


def all_angles_present(rows: list[dict[str,float]], case: XFoilCase) -> bool:
    actual = [r["alpha"] for r in rows]
    return all(any(abs(a-b)<=0.001 for b in actual) for a in case.angles())


def _run_branch(exe: Path, dat: bytes, case: XFoilCase, sweep, timeout: int) -> tuple[int,str,str|None]:
    """One XFOIL process for one ASEQ branch; returns (returncode, log, polar text)."""
    with TemporaryDirectory(prefix="aerosuite-xfoil-") as tmp:
        work = Path(tmp)
        (work/"foil.dat").write_bytes(dat)
        try:
            proc = subprocess.run([str(exe.resolve())],input=make_script(case,sweep),cwd=work,
                                  text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                  timeout=timeout,errors="replace")
        except subprocess.TimeoutExpired as exc:
            log = exc.stdout if isinstance(exc.stdout,str) else ""
            polar_file = work/"polar.txt"
            polar = polar_file.read_text(encoding="utf-8",errors="replace") if polar_file.is_file() else None
            return -9, (log or "")+"\n[AeroSuite] TIMEOUT after %d s\n" % timeout, polar
        polar_file = work/"polar.txt"
        polar = polar_file.read_text(encoding="utf-8",errors="replace") if polar_file.is_file() else None
        return proc.returncode, proc.stdout or "", polar


def run_profile(exe: Path, identifier: str, foil: Airfoil,
                case: XFoilCase, out: Path, timeout: int = 180) -> dict:
    """Execute real XFOIL and write actual CSV + provenance JSON.

    Only points that XFOIL itself converged and wrote to its polar file are kept.
    Requested angles without a converged point are listed in ``missing_alpha``.
    ``converged`` is True only for a complete sweep (backward compatible); the
    comparator rejects incomplete sweeps unless partial comparison is requested.
    Physical accuracy still requires independent validation.
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
    dat = ("AeroSuite\n"+"".join(f"{x:.9f} {y:.9f}\n" for x,y in foil.coordinates)).encode("ascii")
    logs, polars, codes = [], [], []
    for sweep in case.branches():
        code, log, polar = _run_branch(exe, dat, case, sweep, timeout)
        codes.append(code)
        logs.append(f"===== AeroSuite branch ASEQ {sweep[0]:g} {sweep[1]:g} {sweep[2]:g} | return code {code}\n"+log)
        if polar:
            polars.append(polar)
    paths["log"].write_text("\n".join(logs)[-500000:],encoding="utf-8")
    rows_by_alpha: dict[float,dict] = {}
    for polar in polars:
        try:
            for row in parse_polar(polar):
                rows_by_alpha.setdefault(round(row["alpha"],6), row)
        except ValueError:
            continue
    if not rows_by_alpha:
        raise RuntimeError("XFOIL produced no converged polar point; see "+str(paths["log"]))
    rows = sorted(rows_by_alpha.values(), key=lambda r:r["alpha"])
    paths["polar"].write_text("\n\n".join(polars),encoding="utf-8")
    with paths["csv"].open("w",newline="",encoding="utf-8") as output:
        writer = csv.DictWriter(output,fieldnames=("alpha","cl","cd","cm","cdp","xtr_top","xtr_bottom"))
        writer.writeheader()
        writer.writerows(rows)
    missing = missing_angles(rows,case)
    complete = not missing
    version = solver_version("\n".join(logs))
    metadata = {
        "solver":"XFOIL " + (version or "(version not reported)") + " external executable",
        "solver_version_reported":version,
        "solver_source":SOURCE_URL,
        "solver_path":str(exe.resolve()),
        "solver_sha256":hashlib.sha256(exe.read_bytes()).hexdigest(),
        "solver_return_codes":codes,
        "geometry_sha256":hashlib.sha256(dat).hexdigest(),
        "geometry_source":foil.source_file,
        "geometry_points":len(foil.coordinates),
        "reynolds":case.reynolds, "mach":case.mach, "ncrit":case.ncrit,
        "xtr_top":case.xtr_top, "xtr_bottom":case.xtr_bottom,
        "alpha_start":case.alpha_start,"alpha_end":case.alpha_end,
        "alpha_step":case.alpha_step,"iterations":case.iterations,
        "sweep_branches":[list(b) for b in case.branches()],
        "points_requested":len(case.angles()),"points_returned":len(rows),
        "missing_alpha":missing,
        "converged":complete,
        "note":("All requested angles converged; not independent physical validation"
                if complete else "Some requested angles did not converge (missing_alpha); "
                "only converged points are stored")
    }
    paths["json"].write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    return metadata
