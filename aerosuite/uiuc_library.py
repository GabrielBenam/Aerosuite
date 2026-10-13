"""Offline UIUC Selig .dat airfoil catalog; no aerodynamic coefficients.

Download the authoritative archive from the UIUC website, then import locally.
Files are not redistributed with AeroSuite.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile, BadZipFile
import io
import json
import math
import re

UIUC_ARCHIVE_URL = "https://m-selig.ae.illinois.edu/ads/archives/coord_seligFmt.zip"


@dataclass(frozen=True)
class Airfoil:
    name: str
    source_file: str
    coordinates: tuple[tuple[float, float], ...]

def parse_selig(text: str, filename: str = "profile.dat") -> Airfoil:
    """Parse the single-contour Selig convention, discarding # comments.

    The expected order is trailing edge of upper surface, leading edge,
    trailing edge of lower surface. Lednicer two-block formats are not
    silently interpreted as Selig files.
    """
    rows = []
    for raw in text.replace("\ufeff", "").splitlines():
        s = raw.split("#", 1)[0].strip()
        if s:
            rows.append(s)
    if len(rows) < 5:
        raise ValueError("Not enough lines for Selig geometry")
    name = rows[0].strip()
    if not name:
        raise ValueError("Missing airfoil name")
    points = []
    for n, row in enumerate(rows[1:], start=2):
        fields = row.replace(",", " ").split()
        if len(fields) != 2:
            raise ValueError(f"Non-Selig coordinate row {n}: {row!r}")
        try:
            x, y = (float(f) for f in fields)
        except ValueError as exc:
            raise ValueError(f"Non-numeric coordinate in row {n}") from exc
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError("Coordinates must be finite")
        points.append((x, y))
    if len(points) < 4:
        raise ValueError("Insufficient airfoil coordinates")
    xs = [p[0] for p in points]
    i_le = min(range(len(xs)), key=xs.__getitem__)
    if not (0 < i_le < len(xs) - 1):
        raise ValueError("Expected leading edge between trailing edge points")
    if max(xs) - min(xs) <= 0:
        raise ValueError("Degenerate chord")
    # Check x decreases on the upper surface and increases on the lower one.
    # A small tolerance handles numerical/rounding artifacts.
    tol = 1e-3 * (max(xs)-min(xs))
    if any(xs[i+1] > xs[i]+tol for i in range(i_le)):
        raise ValueError("Unexpected upper surface ordering")
    if any(xs[i+1] < xs[i]-tol for i in range(i_le,len(xs)-1)):
        raise ValueError("Unexpected lower surface ordering")
    return Airfoil(name,filename,tuple(points))


def load_library(archive: Path) -> tuple[dict[str, Airfoil], dict[str, str]]:
    """Read all valid .dat files, keeping a per-file report of failures."""
    profiles: dict[str, Airfoil] = {}
    errors: dict[str, str] = {}
    with ZipFile(archive) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".dat") and not n.endswith("/")]
        for name in sorted(names):
            path = Path(name)
            # Never extract archive entries to the filesystem.
            if ".." in path.parts:
                errors[name] = "Unsafe archive entry"
                continue
            try:
                info = zf.getinfo(name)
                if info.file_size > 1_000_000:
                    raise ValueError("Geometry file exceeds 1 MB")
                text = zf.read(name).decode("utf-8-sig",errors="replace")
                profile = parse_selig(text, filename=name)
                key = path.stem.lower()
                if key in profiles:
                    raise ValueError("Duplicate profile identifier")
                profiles[key] = profile
            except (ValueError, OSError, UnicodeError, BadZipFile) as exc:
                errors[name] = str(exc)
    return profiles,errors


def catalog(archive: Path, output: Path) -> dict:
    profiles, errors = load_library(archive)
    payload = {
        "source": UIUC_ARCHIVE_URL, "format": "Selig DAT",
        "profiles_imported":len(profiles), "profiles_rejected":len(errors),
        "profiles":[{"id":key,"name":p.name,"file":p.source_file,
                     "points":len(p.coordinates)} for key,p in sorted(profiles.items())],
        "errors":errors,
        "note":"Geometry only. No polar/performance values.",
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8")
    return payload
