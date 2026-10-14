"""Reproducible offline airfoil comparison based on measured/simulated polar CSVs.

This module never invents aerodynamic performance. All polars must come from
a user-supplied solver or experiment with compatible metadata.
"""
from __future__ import annotations
from dataclasses import dataclass
import csv
import json
import math
from pathlib import Path
from .airfoil_compare import read_polar_csv, plot_polars, plot_geometry
from .uiuc_library import load_library

REQUIRED_CONDITIONS = ("reynolds", "mach", "ncrit", "xtr_top", "xtr_bottom")

@dataclass(frozen=True)
class Comparison:
    profiles: tuple[str, ...]
    polars_dir: Path
    output_dir: Path
    uiuc_zip: Path | None = None
    allow_partial: bool = False

def _conditions(path: Path, allow_partial: bool = False) -> dict:
    metadata = json.loads(path.read_text(encoding="utf-8"))
    missing = [key for key in REQUIRED_CONDITIONS if key not in metadata]
    if missing:
        raise ValueError(f"{path}: missing conditions {missing}")
    for key in REQUIRED_CONDITIONS:
        value = metadata[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{path}: invalid {key}")
    if metadata["reynolds"] <= 0 or not (0 <= metadata["mach"] < 1):
        raise ValueError(f"{path}: invalid Reynolds or Mach")
    if not all(0 <= metadata[key] <= 1 for key in ("xtr_top", "xtr_bottom")):
        raise ValueError(f"{path}: invalid transition location")
    if metadata["ncrit"] <= 0:
        raise ValueError(f"{path}: invalid Ncrit")
    if metadata.get("converged") is False and not allow_partial:
        raise ValueError(f"{path}: incomplete sweep (missing_alpha={metadata.get('missing_alpha')}); "
                         "rerun or use --allow-partial to compare only converged points")
    return metadata

def compare(job: Comparison, charts: bool = True) -> dict:
    """Require <id>.csv and <id>.json for every profile.

    CSV has alpha, cl, cd, cm; JSON contains the matching solver conditions.
    Ranking only covers converged/recorded data; it does not extrapolate.
    """
    if len(job.profiles) < 2 or len(job.profiles) != len(set(job.profiles)):
        raise ValueError("Select at least two distinct profiles")
    if any(not ident or "/" in ident or "\\" in ident or ident in (".", "..") for ident in job.profiles):
        raise ValueError("Unsafe profile identifier")
    polars = {}
    conditions = {}
    for ident in job.profiles:
        polars[ident] = read_polar_csv(job.polars_dir / f"{ident}.csv")
        conditions[ident] = _conditions(job.polars_dir / f"{ident}.json", job.allow_partial)
    signature = tuple(conditions[job.profiles[0]][k] for k in REQUIRED_CONDITIONS)
    for ident in job.profiles[1:]:
        if tuple(conditions[ident][k] for k in REQUIRED_CONDITIONS) != signature:
            raise ValueError("Polar conditions differ; comparison rejected")
    metrics = []
    for ident, rows in polars.items():
        positive = [r for r in rows if r["cl"] > 0 and r["cd"] > 0]
        if not positive:
            metrics.append({"profile": ident, "best_ld": None, "alpha_at_best_ld": None, "num_points": len(rows)})
            continue
        best = max(positive, key=lambda r:r["cl"]/r["cd"])
        clmax = max(rows, key=lambda r:r["cl"])
        cdmin = min(rows, key=lambda r:r["cd"])
        metrics.append({"profile":ident,"best_ld":best["cl"]/best["cd"],"alpha_at_best_ld":best["alpha"],
                        "cl_at_best_ld":best["cl"],"cm_at_best_ld":best["cm"],
                        "cl_max_observed":clmax["cl"],"alpha_at_cl_max_observed":clmax["alpha"],
                        "cd_min_observed":cdmin["cd"],"alpha_at_cd_min_observed":cdmin["alpha"],
                        "num_points":len(rows),
                        "missing_alpha":conditions[ident].get("missing_alpha",[]),
                        "cl_max_is_bounded_by_sweep": clmax["alpha"] >= max(r["alpha"] for r in rows)})
    metrics.sort(key=lambda item: (item["best_ld"] is None, -(item["best_ld"] or 0), item["profile"]))
    # Create no output until validation completed.
    job.output_dir.mkdir(parents=True, exist_ok=True)
    if charts:
        plot_polars(polars, job.output_dir / "plots", conditions)
        if job.uiuc_zip:
            library, _errors = load_library(job.uiuc_zip)
            missing = [key for key in job.profiles if key.lower() not in library]
            if missing:
                raise ValueError(f"Missing UIUC geometries: {missing}")
            plot_geometry([library[key.lower()] for key in job.profiles], job.output_dir / "plots" / "geometry.png")
    result = {"status":"COMPARISON_OF_SUPPLIED_POLARS","conditions":dict(zip(REQUIRED_CONDITIONS,signature)),
              "ranking_scope":"highest CL/CD over sampled positive-lift points only; not validated design selection",
              "partial_sweeps_allowed":job.allow_partial,
              "observed_values_note":"cl_max/cd_min are the extremes among converged sampled points, not interpolated true maxima; if cl_max_is_bounded_by_sweep is true, stall was not reached in the sweep",
              "ranking":metrics,"provenance":{ident:{"polar":str((job.polars_dir / f"{ident}.csv").resolve()),
                                                "metadata":str((job.polars_dir / f"{ident}.json").resolve()),
                                                "solver":conditions[ident].get("solver","unspecified")}
                                        for ident in job.profiles}}
    (job.output_dir / "comparison.json").write_text(json.dumps(result, indent=2),encoding="utf-8")
    return result
