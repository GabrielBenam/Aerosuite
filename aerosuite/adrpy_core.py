"""ADRpy conceptual sizing and the conceptual SciPy optimizer (no custom aerodynamics).

JSON in, JSON out. Every T/W value comes from the unmodified ADRpy 0.2.6
methods (``twrequired_to``, ``twrequired_clm``, ``twrequired_crs``,
``twrequired_sec``, ``twrequired_trn``, ``wsmaxcleanstall_pa``,
``powerrequired``). AeroSuite only selects which constraints apply, samples
wing loading, records units and plots the results.

References for the method: Gudmundsson, GA Aircraft Design 2nd ed., Sec. 3.2
(PDF p.104-112). See BIBLIOGRAPHY_MAP.md.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
import sys
import warnings
from typing import Any

UPSTREAM_ADRPY = Path(__file__).resolve().parents[1] / "vendor" / "ADRpy"

# ADRpy method -> (label, how the design brief must specify it)
CONSTRAINTS = {
    "takeoff": ("twrequired_to", ("groundrun_m",)),
    "climb": ("twrequired_clm", ("climbspeed_kias", "climbrate_fpm")),
    "cruise": ("twrequired_crs", ("cruisealt_m", "cruisespeed_ktas")),
    "ceiling": ("twrequired_sec", ("servceil_m", "secclimbspd_kias")),
    "turn": ("twrequired_trn", ("turnspeed_ktas", "stloadfactor")),
}
# keys used by ADRpy powerrequired()
POWER_KEYS = {"takeoff": "take-off", "climb": "climb", "cruise": "cruise",
              "ceiling": "servceil", "turn": "turnfeasible"}


def _libraries():
    """Use the installed ADRpy (setup installs vendor/ADRpy); fall back to the vendor tree."""
    try:
        from ADRpy import atmospheres, constraintanalysis  # noqa: F401
    except ImportError:
        if (UPSTREAM_ADRPY / "ADRpy" / "constraintanalysis.py").is_file():
            sys.path.insert(0, str(UPSTREAM_ADRPY))
    try:
        from ADRpy import atmospheres
        from ADRpy import constraintanalysis
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "ADRpy runtime is not installed. Run scripts/setup-engines.ps1 on Windows "
            "or: python -m pip install -r requirements-core.txt && python -m pip install --no-deps vendor/ADRpy"
        ) from exc
    return atmospheres, constraintanalysis, np


def load_concept(filename: Path) -> dict:
    data = json.loads(Path(filename).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON concept must contain an object")
    for name in ("designbrief", "designdefinition", "designperformance"):
        if not isinstance(data.get(name), dict):
            raise ValueError(f"Missing or invalid concept section: {name}")
    atm = data.get("atmosphere", {})
    if not isinstance(atm, dict) or not isinstance(atm.get("offset_deg", 0), (int, float)):
        raise ValueError("Atmosphere requires a numeric offset_deg")
    return data


def _aircraft(doc: dict, aspectratio: float | None = None):
    atmospheres, constraintanalysis, _np = _libraries()
    design = deepcopy(doc["designdefinition"])
    if aspectratio is not None:
        design["aspectratio"] = aspectratio
    atmosphere = atmospheres.Atmosphere(offset_deg=float(doc.get("atmosphere", {}).get("offset_deg", 0)))
    propulsion = doc.get("propulsion")  # e.g. "piston", "turboprop", "turbofan" (ADRpy keywords)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        concept = constraintanalysis.AircraftConcept(
            deepcopy(doc["designbrief"]), design, deepcopy(doc["designperformance"]), atmosphere,
            propulsion if propulsion else None)
    return concept, atmosphere


def _constrained_methods(doc: dict) -> dict[str, str]:
    """Evaluate only constraints for which the design brief supplied full inputs."""
    brief = doc["designbrief"]
    available = {}
    for name, (method, keys) in CONSTRAINTS.items():
        if all(brief.get(k) not in (None, False, 0) or (k == "cruisealt_m" and brief.get(k) == 0)
               for k in keys):
            available[name] = method
    if not available:
        raise ValueError("Supply takeoff, climb, cruise, ceiling or turn requirements")
    return available


def _safe_number(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("ADRpy returned a non-numeric value") from exc
    if not math.isfinite(numeric):
        raise ValueError("ADRpy returned a non-finite value (possibly infeasible)")
    return numeric


def _tw(concept, method: str, ws: float, map2sl: bool = True) -> float:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        answer = getattr(concept, method)(ws, map2sl=map2sl)
    if isinstance(answer, tuple):
        answer = answer[0]
    return _safe_number(answer)


def stall_limit_pa(doc: dict) -> float | None:
    """Maximum W/S from the clean stall speed and CLmaxclean (ADRpy wsmaxcleanstall_pa)."""
    brief, perf = doc["designbrief"], doc["designperformance"]
    if not (brief.get("vstallclean_kcas") and perf.get("CLmaxclean")):
        return None
    concept, _ = _aircraft(doc)
    return _safe_number(concept.wsmaxcleanstall_pa())


def evaluate(doc: dict, ws: float, aspectratio: float | None = None, map2sl: bool = True) -> dict:
    if not math.isfinite(ws) or ws <= 0:
        raise ValueError("wingloading_pa must be positive")
    concept, _ = _aircraft(doc, aspectratio)
    values = {}
    for name, method in _constrained_methods(doc).items():
        try:
            values[name] = _tw(concept, method, ws, map2sl)
        except Exception as exc:
            raise ValueError(f"ADRpy constraint {name}/{method} failed: {exc}") from exc
    result = {"wingloading_pa": float(ws),
              "aspectratio": float(aspectratio if aspectratio is not None else doc["designdefinition"]["aspectratio"]),
              "required_tw": max(values.values()),
              "active_constraint": max(values, key=values.get),
              "by_constraint": values}
    if "turn" in values:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            _tw_trn, cl_trn, feasible = concept.twrequired_trn(ws, map2sl=map2sl)
        result["turn_cl_required"] = _safe_number(cl_trn)
        result["turn_feasible_with_CLmaxclean"] = bool(math.isfinite(float(feasible)))
    return result


def _power(doc: dict, ws_values, map2sl: bool) -> dict | None:
    """Shaft power (hp) from ADRpy powerrequired when MTOW and propeller efficiencies are given."""
    tow = doc.get("tow_kg")
    if not tow or not doc["designperformance"].get("etaprop"):
        return None
    concept, _ = _aircraft(doc)
    needed = set(_constrained_methods(doc))
    if needed != set(CONSTRAINTS):
        return {"available": False,
                "reason": "ADRpy powerrequired() evaluates all five constraints; supply all of them to use it"}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        preq = concept.powerrequired(ws_values, float(tow), feasibleonly=True, map2sl=map2sl)
    return {"available": True, "units": "hp", "map2sl": map2sl,
            "by_constraint": {name: [float(v) for v in preq[key]] for name, key in POWER_KEYS.items()},
            "combined": [float(v) for v in preq["combined"]]}


def size(doc: dict, map2sl: bool = True) -> dict:
    _at, _ca, np = _libraries()
    config = doc.get("wingloading_pa", {})
    low = float(config.get("min", 500))
    high = float(config.get("max", 2500))
    n = int(config.get("samples", 40))
    if not (0 < low < high and 2 <= n <= 2000):
        raise ValueError("Invalid wingloading_pa range / samples")
    samples, failures = [], []
    grid = np.linspace(low, high, n)
    for ws in grid:
        try:
            samples.append(evaluate(doc, float(ws), map2sl=map2sl))
        except (ValueError, ArithmeticError, OverflowError, ZeroDivisionError) as exc:
            failures.append({"wingloading_pa": float(ws), "error": str(exc)})
    if not samples:
        raise ValueError("No valid ADRpy evaluations found. First failures: " + str(failures[:3]))
    ws_stall = stall_limit_pa(doc)
    admissible = [s for s in samples if ws_stall is None or s["wingloading_pa"] <= ws_stall]
    best_unconstrained = min(samples, key=lambda x: x["required_tw"])
    best = min(admissible, key=lambda x: x["required_tw"]) if admissible else None
    power = _power(doc, [s["wingloading_pa"] for s in samples], map2sl)
    return {"engine": "ADRpy v0.2.6", "analysis": "conceptual constraint sizing",
            "units": {"wingloading_pa": "N/m^2", "required_tw": "dimensionless",
                      "tw_reference": "sea-level static equivalent" if map2sl else "local (at each constraint's condition)"},
            "config_name": doc.get("name", "untitled"),
            "constraints_evaluated": list(_constrained_methods(doc)),
            "constraints_not_evaluated": [c for c in CONSTRAINTS if c not in _constrained_methods(doc)],
            "stall_limit_wingloading_pa": ws_stall,
            "design_point_rule": ("minimum required T/W among sampled W/S not exceeding the clean-stall limit"
                                  if ws_stall is not None else
                                  "minimum required T/W among sampled W/S (NO stall limit: supply vstallclean_kcas and CLmaxclean)"),
            "best_sample": best,
            "best_sample_ignoring_stall": best_unconstrained,
            "samples": samples, "rejected_samples": failures,
            "power_required": power,
            "note": "Only explicitly defined constraints are evaluated; sampled grid resolution limits the design point; "
                    "no certification, weight or mission analysis."}


def plot_constraint_diagram(result: dict, destination: Path) -> Path:
    """Constraint diagram from an existing size() result (no new computation)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    samples = result["samples"]
    ws = [s["wingloading_pa"] for s in samples]
    fig, ax = plt.subplots(figsize=(9, 6))
    for name in result["constraints_evaluated"]:
        ax.plot(ws, [s["by_constraint"][name] for s in samples], label=name)
    ax.plot(ws, [s["required_tw"] for s in samples], "k-", lw=2.5, label="combined (max)")
    if result.get("stall_limit_wingloading_pa"):
        ax.axvline(result["stall_limit_wingloading_pa"], color="tab:red", ls="--", label="clean stall limit")
    if result.get("best_sample"):
        b = result["best_sample"]
        ax.plot([b["wingloading_pa"]], [b["required_tw"]], "o", ms=9, mfc="none", mec="k", label="design point (sampled)")
    ax.set_xlabel("Wing loading W/S (N/m²)")
    ax.set_ylabel("T/W required (" + result["units"]["tw_reference"] + ")")
    ax.set_title("ADRpy 0.2.6 constraint diagram — " + str(result.get("config_name", "")))
    ax.grid(True, alpha=.3)
    ax.legend()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return destination


def atmosphere_table(altitudes_m: list[float], offset_deg: float = 0.0) -> dict:
    """ISA (with optional temperature offset) from ADRpy atmospheres.Atmosphere.

    Dynamic viscosity uses Sutherland's law with the ICAO standard-atmosphere
    constants (beta_s = 1.458e-6 kg/(m s K^0.5), S = 110.4 K). ADRpy 0.2.6 has
    no viscosity function; this one line is AeroSuite code and is labelled so.
    """
    atmospheres, _ca, _np = _libraries()
    atm = atmospheres.Atmosphere(offset_deg=float(offset_deg))
    rows = []
    for h in altitudes_m:
        t = float(atm.airtemp_k(h))
        rows.append({"altitude_m": float(h), "temperature_k": t,
                     "pressure_pa": float(atm.airpress_pa(h)),
                     "density_kgm3": float(atm.airdens_kgpm3(h)),
                     "speed_of_sound_mps": float(atm.vsound_mps(h)),
                     "dynamic_viscosity_pas": 1.458e-6 * t ** 1.5 / (t + 110.4)})
    return {"engine": "ADRpy v0.2.6 atmospheres.Atmosphere (ISA)", "offset_deg": float(offset_deg),
            "viscosity_model": "Sutherland law, ICAO constants (AeroSuite code, not ADRpy)", "rows": rows}


def reynolds_number(altitude_m: float, speed_mps: float, chord_m: float, offset_deg: float = 0.0) -> dict:
    row = atmosphere_table([altitude_m], offset_deg)["rows"][0]
    re = row["density_kgm3"] * speed_mps * chord_m / row["dynamic_viscosity_pas"]
    return {"reynolds": re, "mach": speed_mps / row["speed_of_sound_mps"], "atmosphere": row,
            "speed_mps": speed_mps, "chord_m": chord_m}


def optimize(doc: dict) -> dict:
    """Legacy entry point kept for compatibility: minimize required T/W over (W/S, AR).

    WARNING: with ADRpy constraints only, a larger aspect ratio always lowers induced
    drag and nothing penalizes it (no wing weight model), so AR converges to its upper
    bound. Use ``aerosuite opt`` with explicit constraints instead (see optimizer.py).
    """
    from scipy.optimize import differential_evolution
    cfg = doc.get("optimizer", {})
    w = cfg.get("wingloading_pa", {})
    a = cfg.get("aspectratio", {})
    bounds = [(float(w.get("min", 500)), float(w.get("max", 2600))),
              (float(a.get("min", 6)), float(a.get("max", 12)))]
    if any(not all(math.isfinite(v) for v in pair) or pair[0] <= 0 or pair[0] >= pair[1] for pair in bounds):
        raise ValueError("Bad optimizer bounds")
    seed = int(cfg.get("seed", 42))
    maxiter = int(cfg.get("maxiter", 40))
    if not (1 <= maxiter <= 1000):
        raise ValueError("maxiter must be 1..1000")

    def objective(x):
        try:
            return evaluate(doc, float(x[0]), float(x[1]))["required_tw"]
        except (ValueError, ArithmeticError, OverflowError, ZeroDivisionError):
            return 1e9  # evaluation-failure marker, not a physical penalty

    result = differential_evolution(objective, bounds, seed=seed, maxiter=maxiter, polish=True, workers=1)
    if not math.isfinite(float(result.fun)) or result.fun >= 1e9:
        raise ValueError("No valid solution within supplied bounds")
    optimum = evaluate(doc, float(result.x[0]), float(result.x[1]))
    at_bounds = [name for name, value, (lo, hi) in zip(("wingloading_pa", "aspectratio"), result.x, bounds)
                 if abs(value - lo) <= 1e-6 * (hi - lo) or abs(value - hi) <= 1e-6 * (hi - lo)]
    return {"engine": "ADRpy v0.2.6 + SciPy differential_evolution",
            "objective": "minimize max required T/W for supplied constraints",
            "optimum": optimum, "variables_at_bounds": at_bounds,
            "solver_success": bool(result.success),
            "solver_message": str(result.message), "evaluations": int(result.nfev),
            "notes": ["Conceptual optimization only, not flow5 3D shape optimization",
                      "No structural/weight penalty: an aspect ratio at its upper bound is an artefact of the "
                      "missing weight model, not a design recommendation",
                      "Stall limit is not enforced here; use 'aerosuite opt' with a stall constraint",
                      "Result is not aircraft flightworthiness or certification evidence"]}


def export_result(payload: dict, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return destination
