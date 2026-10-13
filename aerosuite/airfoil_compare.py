"""Create multi-airfoil geometry plots and compare verified imported polar CSVs.

No CL/CD/CM coefficients are generated in this module.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

from .uiuc_library import Airfoil


def plot_geometry(profiles: list[Airfoil], output: Path) -> None:
    """Save overlays with equal axis scaling; matplotlib is optional."""
    if not profiles:
        raise ValueError("Select at least one airfoil")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11, 5))
    for foil in profiles:
        x, y = zip(*foil.coordinates)
        ax.plot(x, y, label=foil.name)
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xlabel("x/c (as supplied by source)")
    ax.set_ylabel("y/c (as supplied by source)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(output,dpi=180,bbox_inches="tight")
    plt.close(fig)


def read_polar_csv(path: Path) -> list[dict[str, float]]:
    """Accept CSV columns alpha, cl, cd, cm and explicitly test validity."""
    with path.open(newline="",encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not {"alpha","cl","cd","cm"}.issubset({s.strip().lower() for s in reader.fieldnames}):
            raise ValueError("Polar CSV requires alpha,cl,cd,cm columns")
        rows = []
        for row in reader:
            normalized = {k.strip().lower():v for k,v in row.items() if k}
            vals = {k:float(normalized[k]) for k in ("alpha","cl","cd","cm")}
            if not all(map(math.isfinite,vals.values())) or vals["cd"] <= 0:
                raise ValueError("Non-finite values or non-positive CD")
            rows.append(vals)
    if not rows:
        raise ValueError("Empty polar")
    return sorted(rows,key=lambda r:r["alpha"])


PLOT_SPECS = {
    "cl_alpha":("alpha","cl","Angle of attack α (deg)","Lift coefficient CL"),
    "cd_alpha":("alpha","cd","Angle of attack α (deg)","Drag coefficient CD"),
    "cm_alpha":("alpha","cm","Angle of attack α (deg)","Moment coefficient CM"),
    "cl_cd":("cd","cl","Drag coefficient CD","Lift coefficient CL"),
    "efficiency_alpha":("alpha","efficiency","Angle of attack α (deg)","CL/CD"),
}


def plot_polars(polars: dict[str, list[dict[str,float]]], output_dir: Path,
                conditions: dict[str, dict] | None = None) -> None:
    """Generate comparison charts; optional metadata enforces condition equality.

    With multiple profiles, conditions metadata must contain comparable
    reynolds, mach, ncrit, xtr_top and xtr_bottom for EVERY profile.
    """
    if not polars:
        raise ValueError("No polars provided")
    if len(polars) > 1:
        required = ("reynolds","mach","ncrit","xtr_top","xtr_bottom")
        if conditions is None or any(name not in conditions for name in polars):
            raise ValueError("Comparison requires explicit matching solver conditions")
        first = None
        for name in polars:
            current = tuple(conditions[name].get(k) for k in required)
            if any(v is None for v in current):
                raise ValueError("Missing solver condition metadata")
            if first is not None and current != first:
                raise ValueError("Cannot compare mismatched analysis conditions")
            first = current
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    output_dir.mkdir(parents=True,exist_ok=True)
    for plotname,(xkey,ykey,xlabel,ylabel) in PLOT_SPECS.items():
        fig,ax=plt.subplots(figsize=(9,6))
        for name,rows in polars.items():
            xvals=[r[xkey] if xkey!="efficiency" else r["cl"]/r["cd"] for r in rows]
            yvals=[r[ykey] if ykey!="efficiency" else r["cl"]/r["cd"] for r in rows]
            ax.plot(xvals,yvals,label=name)
        ax.set(xlabel=xlabel,ylabel=ylabel,title=plotname.replace("_"," ").title())
        ax.legend()
        ax.grid(True,alpha=.3)
        fig.savefig(output_dir/f"{plotname}.png",dpi=180,bbox_inches="tight")
        plt.close(fig)
