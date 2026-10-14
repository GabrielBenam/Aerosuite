"""Locate the original engines and report their real state (no engine code here).

Resolution order for executables:
1. explicit path given on the command line;
2. environment variable (AEROSUITE_XFOIL, AEROSUITE_FLOW5);
3. files installed by scripts/setup-engines.ps1 under runtime/.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as metadata
import os
import platform
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
VENDOR = ROOT / "vendor"

PINNED = {
    "flow5": {"tag": "v7.57", "sha": "a9e852c559590188e00e9efe997c35c1dec7209b",
              "url": "https://github.com/techwinder/flow5"},
    "ADRpy": {"tag": "0.2.6", "sha": "b2beba274ebff93ec9fb22f046e3fc47356ceac2",
              "url": "https://github.com/sobester/ADRpy"},
}


def _git_head(repo: Path) -> str | None:
    """Read the checked-out commit without running git (works for plain copies too)."""
    git = repo / ".git"
    if git.is_file():  # submodule: "gitdir: ../../.git/modules/..."
        text = git.read_text(encoding="utf-8", errors="replace").strip()
        if text.startswith("gitdir:"):
            git = (repo / text.split(":", 1)[1].strip()).resolve()
    head = git / "HEAD"
    if not head.is_file():
        return None
    value = head.read_text(encoding="utf-8", errors="replace").strip()
    if value.startswith("ref:"):
        ref = git / value.split(":", 1)[1].strip()
        return ref.read_text(encoding="utf-8").strip() if ref.is_file() else None
    return value


def vendor_state(name: str) -> dict:
    repo = VENDOR / name
    marker = {"flow5": repo / "flow5.pro", "ADRpy": repo / "ADRpy" / "constraintanalysis.py"}[name]
    head = _git_head(repo)
    return {"path": str(repo), "source_present": marker.is_file(), "commit": head,
            "pinned_commit": PINNED[name]["sha"], "pinned_tag": PINNED[name]["tag"],
            "matches_pin": head == PINNED[name]["sha"] if head else None}


def xfoil_executable(explicit: Path | None = None) -> Path | None:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    if os.getenv("AEROSUITE_XFOIL"):
        candidates.append(Path(os.environ["AEROSUITE_XFOIL"]))
    candidates += [RUNTIME / "xfoil" / "xfoil.exe", RUNTIME / "xfoil" / "xfoil"]
    found = shutil.which("xfoil")
    if found:
        candidates.append(Path(found))
    for candidate in candidates:
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate)
        if candidate.is_file():
            return candidate.resolve()
    return None


def flow5_executable(explicit: Path | None = None) -> Path | None:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    if os.getenv("AEROSUITE_FLOW5"):
        candidates.append(Path(os.environ["AEROSUITE_FLOW5"]))
    location = RUNTIME / "flow5-location.txt"
    if location.is_file():
        candidates.append(Path(location.read_text(encoding="utf-8-sig").strip()))
    for candidate in candidates:
        if not candidate.is_absolute():
            candidate = ROOT / candidate
        if candidate.is_file():
            return candidate.resolve()
    return None


def _version(package: str) -> str | None:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def status() -> dict:
    xfoil = xfoil_executable()
    flow5 = flow5_executable()
    adrpy_import = None
    try:
        import ADRpy  # noqa: F401
        adrpy_import = str(Path(ADRpy.__file__).resolve().parent) if getattr(ADRpy, "__file__", None) else "namespace"
    except ImportError:
        pass
    return {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "vendor": {"flow5": vendor_state("flow5"), "ADRpy": vendor_state("ADRpy")},
        "python_packages": {name: _version(name) for name in ("ADRpy", "numpy", "scipy", "pandas", "matplotlib")},
        "adrpy_import_location": adrpy_import,
        "xfoil_executable": str(xfoil) if xfoil else None,
        "flow5_executable": str(flow5) if flow5 else None,
        "capabilities": {
            "adrpy_sizing": _version("ADRpy") is not None,
            "scipy_optimizer": _version("scipy") is not None,
            "xfoil_2d": xfoil is not None,
            "flow5_gui": flow5 is not None,
            "flow5_batch_script": flow5 is not None,
        },
        "notes": [
            "Presence of an engine is not integration: see PROJECT_STATE.md for verified connections.",
            "flow5 is used as the official executable (GUI or '-s script.xml' batch mode); its C++ API is not linked.",
        ],
    }
