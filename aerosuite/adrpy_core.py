"""Minimal ADRpy conceptual design and SciPy optimizer, no custom aerodynamics.

Designed for Claude handoff: JSON in, JSON out, upstream ADRpy unchanged.
All units are explicit; thrust loading and performance are conceptual estimates.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
import sys
from typing import Any

UPSTREAM_ADRPY = Path(__file__).resolve().parents[1] / "vendor" / "ADRpy"


def _libraries():
    """Prefer the pinned complete vendor source, allow installed ADRpy for source ZIP."""
    if (UPSTREAM_ADRPY / "ADRpy" / "constraintanalysis.py").is_file():
        path = str(UPSTREAM_ADRPY)
        if path not in sys.path:
            sys.path.insert(0,path)
    try:
        from ADRpy import atmospheres
        from ADRpy import constraintanalysis
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "ADRpy runtime is not installed. Run scripts/install-core.ps1 on Windows "
            "or python -m pip install -r requirements-core.txt"
        ) from exc
    return atmospheres, constraintanalysis, np


def load_concept(filename: Path) -> dict:
    data=json.loads(filename.read_text(encoding="utf-8"))
    if not isinstance(data,dict):
        raise ValueError("JSON concept must contain an object")
    for name in ("designbrief","designdefinition","designperformance"):
        if not isinstance(data.get(name),dict):
            raise ValueError(f"Missing or invalid concept section: {name}")
    atm=data.get("atmosphere",{})
    if not isinstance(atm,dict) or not isinstance(atm.get("offset_deg",0),(int,float)):
        raise ValueError("Atmosphere requires a numeric offset_deg")
    return data


def _aircraft(doc: dict, aspectratio: float | None = None):
    atmospheres,constraintanalysis,_np=_libraries()
    design=deepcopy(doc["designdefinition"])
    if aspectratio is not None:
        design["aspectratio"]=aspectratio
    atmosphere=atmospheres.Atmosphere(offset_deg=float(doc.get("atmosphere",{}).get("offset_deg",0)))
    return constraintanalysis.AircraftConcept(
        deepcopy(doc["designbrief"]),design,deepcopy(doc["designperformance"]),atmosphere
    ), atmosphere


def _constrained_methods(doc: dict) -> dict[str,str]:
    """Evaluate only constraints for which the design brief supplied full inputs."""
    brief=doc["designbrief"]
    available={}
    if brief.get("groundrun_m"):
        available["takeoff"]="twrequired_to"
    if brief.get("climbspeed_kias") and brief.get("climbrate_fpm"):
        available["climb"]="twrequired_clm"
    if brief.get("cruisealt_m") is not None and brief.get("cruisespeed_ktas"):
        available["cruise"]="twrequired_crs"
    if brief.get("servceil_m") and brief.get("secclimbspd_kias"):
        available["ceiling"]="twrequired_sec"
    if brief.get("turnspeed_ktas") and brief.get("stloadfactor"):
        available["turn"]="twrequired_trn"
    if not available:
        raise ValueError("Supply takeoff, climb, cruise, ceiling or turn requirements")
    return available


def _safe_number(value: Any) -> float:
    try:
        numeric=float(value)
    except (TypeError,ValueError) as exc:
        raise ValueError("ADRpy returned a non-numeric value") from exc
    if not math.isfinite(numeric):
        raise ValueError("ADRpy returned a non-finite value (possibly infeasible)")
    return numeric


def _tw(concept, method: str, ws: float) -> float:
    answer=getattr(concept,method)(ws)
    if isinstance(answer,tuple):
        answer=answer[0]
    return _safe_number(answer)


def evaluate(doc: dict, ws: float, aspectratio: float | None = None) -> dict:
    if not math.isfinite(ws) or ws <= 0:
        raise ValueError("wingloading_pa must be positive")
    concept, _ = _aircraft(doc, aspectratio)
    methods=_constrained_methods(doc)
    values = {}
    for name, method in methods.items():
        try:
            values[name] = _tw(concept, method, ws)
        except Exception as exc:
            raise ValueError(f"ADRpy constraint {name}/{method} failed: {exc}") from exc
    return {"wingloading_pa":float(ws),
            "aspectratio":float(aspectratio if aspectratio is not None else doc["designdefinition"]["aspectratio"]),
            "required_tw":max(values.values()),"by_constraint":values}


def size(doc: dict) -> dict:
    _at,_ca,np=_libraries()
    config=doc.get("wingloading_pa",{})
    low=float(config.get("min",500))
    high=float(config.get("max",2500))
    n=int(config.get("samples",40))
    if not (0<low<high and 2<=n<=2000):
        raise ValueError("Invalid wingloading_pa range / samples")
    samples=[]
    failures=[]
    for ws in np.linspace(low,high,n):
        try:
            samples.append(evaluate(doc,float(ws)))
        except (ValueError,ArithmeticError,OverflowError,ZeroDivisionError) as exc:
            failures.append({"wingloading_pa":float(ws),"error":str(exc)})
    if not samples:
        raise ValueError("No valid ADRpy evaluations found. First failures: "+str(failures[:3]))
    best=min(samples,key=lambda x:x["required_tw"])
    return {"engine":"ADRpy v0.2.6","analysis":"conceptual constraint sizing",
            "units":{"wingloading_pa":"N/m^2","required_tw":"dimensionless"},
            "config_name":doc.get("name","untitled"),"best_sample":best,
            "samples":samples,"rejected_samples":failures,
            "note":"Incomplete requirement sets yield only the explicitly defined constraints; no certification or full mission analysis."}


def optimize(doc: dict) -> dict:
    """Minimize required T/W at fixed modeled constraints (not a 3D shape optimizer).

    SciPy differential evolution optimizes wing loading and aspect ratio;
    physical feasibility/structure not represented by the user config must
    not be inferred from this scalar numerical objective.
    """
    from scipy.optimize import differential_evolution
    cfg=doc.get("optimizer",{})
    w=cfg.get("wingloading_pa",{})
    a=cfg.get("aspectratio",{})
    bounds=[(float(w.get("min",500)),float(w.get("max",2600))),
            (float(a.get("min",6)),float(a.get("max",12)))]
    if any(not all(math.isfinite(v) for v in pair) or pair[0]<=0 or pair[0]>=pair[1]
           for pair in bounds):
        raise ValueError("Bad optimizer bounds")
    seed=int(cfg.get("seed",42))
    maxiter=int(cfg.get("maxiter",40))
    if not (1<=maxiter<=1000):
        raise ValueError("maxiter must be 1..1000")
    def objective(x):
        try:
            return evaluate(doc,float(x[0]),float(x[1]))["required_tw"]
        except (ValueError,ArithmeticError,OverflowError,ZeroDivisionError):
            return 1e9
    result=differential_evolution(objective,bounds,seed=seed,maxiter=maxiter,
                                  polish=True,workers=1)
    if not math.isfinite(float(result.fun)) or result.fun >= 1e9:
        raise ValueError("No valid solution within supplied bounds")
    optimum=evaluate(doc,float(result.x[0]),float(result.x[1]))
    return {"engine":"ADRpy v0.2.6 + SciPy differential_evolution",
            "objective":"minimize max required T/W for supplied constraints",
            "optimum":optimum,"solver_success":bool(result.success),
            "solver_message":str(result.message),"evaluations":int(result.nfev),
            "notes":["Conceptual optimization only, not flow5 3D shape optimization",
                     "No structural penalty or manufacturability criteria unless modeled externally",
                     "Result is not aircraft flightworthiness or certification evidence"]}


def export_result(payload: dict, destination: Path) -> Path:
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(payload,indent=2,ensure_ascii=False,
                                      allow_nan=False),encoding="utf-8")
    return destination
