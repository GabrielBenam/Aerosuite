"""Airfoil Lab: native XFOIL batch execution, UIUC catalog and comparison.

No simulated coefficient is generated here. The solver and archive are acquired
from official upstream projects at user request, never silently on import.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request
import uuid
from zipfile import ZipFile

from .airfoil_compare import read_polar_csv, plot_geometry, plot_polars
from .uiuc_library import Airfoil, UIUC_ARCHIVE_URL
from .xfoil_cli import XFoilCase, load_naca_selected, load_uiuc_selected, run_profile

MIT_XFOIL_ZIP = "https://web.mit.edu/drela/Public/web/xfoil/XFOIL6.99.zip"
MAX_ARCHIVE_BYTES = 60_000_000


def data_directory() -> Path:
    root = os.getenv("LOCALAPPDATA")
    return (Path(root) if root else Path.home() / ".local" / "share") / "AeroSuite"


def official_uiuc_path() -> Path:
    return data_directory() / "data" / "coord_seligFmt.zip"


def official_xfoil_path() -> Path:
    return data_directory() / "bin" / "xfoil.exe"


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, filename = tempfile.mkstemp(prefix="aerosuite-", suffix=".tmp",
                                            dir=destination.parent)
    os.close(descriptor)
    tmp = Path(filename)
    try:
        with urllib.request.urlopen(url, timeout=60) as response, tmp.open("wb") as out:
            total = 0
            while True:
                block = response.read(128 * 1024)
                if not block:
                    break
                total += len(block)
                if total > MAX_ARCHIVE_BYTES:
                    raise ValueError("Download larger than permitted limit")
                out.write(block)
        if not ZipFile(tmp).testzip() is None:
            raise ValueError("ZIP integrity check failed")
        tmp.replace(destination)
    finally:
        tmp.unlink(missing_ok=True)


def download_uiuc() -> Path:
    """On-demand download from Michael Selig's UIUC official archive."""
    destination = official_uiuc_path()
    _download(UIUC_ARCHIVE_URL, destination)
    return destination


def download_xfoil() -> Path:
    """On-demand MIT XFOIL6.99 ZIP: extract only the executable, never extractall."""
    archive = data_directory() / "cache" / "XFOIL6.99.zip"
    _download(MIT_XFOIL_ZIP, archive)
    destination = official_xfoil_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive) as zf:
        binary = [entry for entry in zf.infolist()
                  if entry.filename.replace("\\", "/").split("/")[-1].lower() == "xfoil.exe"
                  and not entry.is_dir()]
        if len(binary) != 1 or binary[0].file_size > 30_000_000:
            raise ValueError("Expected a single reasonable-sized XFOIL executable in MIT ZIP")
        target = destination.with_suffix(".tmp")
        try:
            with zf.open(binary[0]) as stream, target.open("wb") as out:
                shutil.copyfileobj(stream, out)
            target.replace(destination)
        finally:
            target.unlink(missing_ok=True)
    return destination


def uiuc_ids(archive: Path) -> list[str]:
    """Return catalog filenames, no geometry parsing or extraction at index time."""
    with ZipFile(archive) as zf:
        counts = {}
        for entry in zf.infolist():
            if entry.is_dir() or not entry.filename.lower().endswith(".dat"):
                continue
            key = Path(entry.filename.replace("\\", "/")).stem.lower()
            if key and all(c.isascii() and (c.isalnum() or c in "_-") for c in key):
                counts[key] = counts.get(key, 0) + 1
        return sorted(k for k, count in counts.items() if count == 1)


@dataclass(frozen=True)
class BatchRequest:
    profiles: tuple[str, ...]
    uiuc_zip: Path | None
    executable: Path
    case: XFoilCase
    destination: Path
    workers: int = 2

    def validate(self) -> None:
        self.case.validate()
        if not 2 <= len(self.profiles) <= 24 or len(self.profiles) != len(set(self.profiles)):
            raise ValueError("Select between 2 and 24 different profiles")
        if not 1 <= self.workers <= 4:
            raise ValueError("Concurrent workers must be 1-4")
        if not self.executable.is_file():
            raise FileNotFoundError("XFOIL executable not found")
        if self.uiuc_zip is not None and not self.uiuc_zip.is_file():
            raise FileNotFoundError("UIUC ZIP archive not found")


def load_profiles(ids: tuple[str, ...], uiuc_zip: Path | None) -> list[tuple[str, Airfoil]]:
    """Accept NACA#### and UIUC identifiers in the same comparative batch."""
    naca = [s[4:] for s in ids if s.lower().startswith("naca") and len(s) == 8 and s[4:].isdigit()]
    name_to_foil = dict(load_naca_selected(naca)) if naca else {}
    other = [s for s in ids if s.lower() not in name_to_foil]
    if other and uiuc_zip is None:
        raise ValueError("Choose the UIUC ZIP archive for non-NACA profiles")
    if other:
        name_to_foil.update(load_uiuc_selected(uiuc_zip, other))
    if len(name_to_foil) != len(ids):
        raise ValueError("Duplicate or unsupported profile selection")
    return [(ident, name_to_foil[ident]) for ident in ids]


def run_batch(request: BatchRequest, progress=None) -> dict:
    """Run isolated XFOIL processes concurrently and report partial convergence.

    Return a report with explicit per-profile status. Only complete sweeps
    enter the ranking; partial polars may be displayed as incomplete.
    """
    request.validate()
    foils = load_profiles(request.profiles, request.uiuc_zip)
    if request.destination.exists() and any(request.destination.iterdir()):
        raise FileExistsError("Choose a new or empty output folder")
    request.destination.mkdir(parents=True, exist_ok=True)
    polar_dir = request.destination / "polars"
    polar_dir.mkdir()
    pictures = request.destination / "plots"
    pictures.mkdir()
    plot_geometry([foil for _, foil in foils], pictures / "geometry.png")
    success: dict[str,dict] = {}
    failed: dict[str,str] = {}
    polars: dict[str,list[dict[str,float]]] = {}
    def notify(event):
        if progress:
            progress(event)
    def one(item):
        ident, foil = item
        return run_profile(request.executable, ident, foil, request.case, polar_dir)
    with ThreadPoolExecutor(max_workers=request.workers) as pool:
        pending = {pool.submit(one, item):item[0] for item in foils}
        for future in as_completed(pending):
            name = pending[future]
            try:
                meta = future.result()
                success[name] = meta
                polars[name] = read_polar_csv(polar_dir / (name + ".csv"))
                notify({"id":name, "state":"complete" if meta["converged"] else "partial",
                        "message":f"{name}: {meta['points_returned']}/{meta['points_requested']} points"})
            except Exception as exc:
                failed[name] = str(exc)
                notify({"id":name,"state":"failed","message":f"{name}: {exc}"})
    ordered = {name:polars[name] for name in request.profiles if name in polars}
    if ordered:
        conditions = {name:success[name] for name in ordered}
        plot_polars(ordered,pictures,conditions)
    ranked = []
    for name in request.profiles:
        if name not in ordered or not success[name]["converged"]:
            continue
        valid = [r for r in ordered[name] if r["cl"] > 0 and r["cd"] > 0]
        if valid:
            best = max(valid,key=lambda r:r["cl"]/r["cd"])
            ranked.append({"id":name,"max_sampled_cl_cd":best["cl"]/best["cd"],
                           "alpha_at_max":best["alpha"],
                           "points":len(ordered[name])})
    ranked.sort(key=lambda x:x["max_sampled_cl_cd"],reverse=True)
    statuses = {}
    for ident in request.profiles:
        statuses[ident] = ("failed" if ident in failed else
                           "complete" if success[ident]["converged"] else "partial")
    result = {
        "status":"COMPLETE" if all(s=="complete" for s in statuses.values()) else "PARTIAL",
        "source":"Real externally executed XFOIL; no synthetic polars",
        "conditions":{"reynolds":request.case.reynolds,"mach":request.case.mach,
                      "ncrit":request.case.ncrit,"alpha_start":request.case.alpha_start,
                      "alpha_end":request.case.alpha_end,"alpha_step":request.case.alpha_step},
        "profiles":list(request.profiles),"status_by_profile":statuses,
        "errors":failed,"ranking_complete_only":ranked,
        "warning":"Partial sweeps plotted for diagnostics only. Rankings are among fully recorded sweeps, not flightworthiness or experimental validation.",
    }
    (request.destination/"report.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    return result
