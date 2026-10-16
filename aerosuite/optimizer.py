"""General SciPy optimizer with an explicit JSON contract.

The optimizer never computes physics. It calls an *evaluation engine*:

* ``adrpy``  — conceptual level (ADRpy 0.2.6 constraint analysis);
* ``xfoil``  — 2D aerodynamic level (original XFOIL executable, NACA 4-digit family);
* ``project`` — M22 multilevel optimizer over a whole project.json (see ProjectEngine): the variables are inputs of the project, each
  evaluation runs the algorithm modules (L-1 loop, `settle`) and the metrics are outputs of those modules. Level `conceptual` (Gudmundsson
  modules and ADRpy); modules that use XFOIL (M09a, M18c) add real 2D data and are reported in `levels_used`; real 3D (flow5) only with
  settings.flow5.enabled = true (explicit flag, time limit per evaluation, low evaluation cap);
* ``flow5``  — standalone 3D engine: NOT AVAILABLE (use ``project`` with settings.flow5).

Contract (JSON):

    {
      "name": "...",
      "level": "conceptual" | "aero2d",
      "engine": "adrpy" | "xfoil",
      "base": {...} or "path/to/concept.json",       # adrpy: concept; xfoil: case settings
      "variables": [{"name": "...", "lower": a, "upper": b}],
      "objective": {"metric": "...", "sense": "minimize" | "maximize"},
      "constraints": [{"metric": "...", "type": "<=" | ">=", "value": v}
                      | {"metric": "...", "type": "<=", "value_metric": "..."}],
      "method": "differential_evolution" | "SLSQP" | "grid",
      "settings": {"seed": 42, "maxiter": 50, "popsize": 10, "tol": 1e-6, "grid_points": 7},
      "ranking": {"top": 10}
    }

Every evaluation (variables, all metrics, feasibility, failures) is stored;
alternatives are ranked among *feasible, successful* evaluations only. A failed
evaluation (solver error, non-converged XFOIL sweep) is reported as a failure:
it is never replaced by an invented physical penalty. For differential
evolution, a failed point receives objective +inf so that it cannot be selected.
"""
from __future__ import annotations

import csv
import itertools
import json
import math
import time
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

LEVELS = {"adrpy": "conceptual", "xfoil": "aero2d", "flow5": "aero3d", "project": "conceptual"}


# ----------------------------------------------------------------- engines
class AdrpyEngine:
    """Conceptual level. Variables: wingloading_pa, aspectratio, or 'section.key' paths into the concept."""

    def __init__(self, base, workdir: Path):
        from .adrpy_core import load_concept
        self.doc = load_concept(Path(base)) if isinstance(base, (str, Path)) else deepcopy(base)
        self.workdir = workdir

    def metrics(self, values: dict) -> dict:
        from .adrpy_core import evaluate, stall_limit_pa
        doc = deepcopy(self.doc)
        ws = values.get("wingloading_pa")
        for name, value in values.items():
            if name == "wingloading_pa":
                continue
            if name == "aspectratio":
                doc["designdefinition"]["aspectratio"] = value
            elif "." in name:
                section, key = name.split(".", 1)
                doc[section][key] = value
            else:
                raise ValueError(f"Unknown ADRpy variable {name!r}")
        if ws is None:
            raise ValueError("ADRpy engine requires the variable wingloading_pa")
        point = evaluate(doc, float(ws))
        out = {"required_tw": point["required_tw"], "wingloading_pa": point["wingloading_pa"],
               "aspectratio": point["aspectratio"], "active_constraint": point["active_constraint"]}
        out.update({f"by_constraint.{k}": v for k, v in point["by_constraint"].items()})
        if "turn_cl_required" in point:
            out["turn_cl_required"] = point["turn_cl_required"]
        stall = stall_limit_pa(doc)
        if stall is not None:
            out["stall_limit_wingloading_pa"] = stall
        return out


class XfoilEngine:
    """2D level. Variables: m, p, t of the NACA 4-digit family (fractions of chord)."""

    def __init__(self, base: dict, workdir: Path):
        from .engines import xfoil_executable
        from .xfoil_cli import XFoilCase
        settings = dict(base or {})
        exe = xfoil_executable(Path(settings.pop("exe")) if settings.get("exe") else None)
        if exe is None:
            raise FileNotFoundError("XFOIL executable not found (runtime/xfoil, AEROSUITE_XFOIL or 'exe')")
        self.exe = exe
        self.points = int(settings.pop("points", 81))
        self.fixed = {k: settings.pop(k) for k in ("m", "p", "t") if k in settings}
        self.case = XFoilCase(**settings)
        self.workdir = workdir
        self.counter = 0

    def metrics(self, values: dict) -> dict:
        from .airfoils import naca4_mpt
        from .uiuc_library import Airfoil
        from .xfoil_cli import run_profile
        params = {**self.fixed, **values}
        m, p, t = float(params.get("m", 0.0)), float(params.get("p", 0.4)), float(params["t"])
        self.counter += 1
        ident = f"eval{self.counter:04d}"
        foil = Airfoil(f"NACA-mpt m={m:.5f} p={p:.4f} t={t:.5f}", ident + ".dat",
                       tuple(naca4_mpt(m, p, t, self.points)))
        meta = run_profile(self.exe, ident, foil, self.case, self.workdir / "xfoil_runs")
        rows = []
        with (self.workdir / "xfoil_runs" / f"{ident}.csv").open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append({k: float(v) for k, v in row.items()})
        positive = [r for r in rows if r["cl"] > 0 and r["cd"] > 0]
        if not meta["converged"]:
            raise RuntimeError(f"XFOIL sweep incomplete for {ident}: missing_alpha={meta['missing_alpha']}")
        best = max(positive, key=lambda r: r["cl"] / r["cd"])
        clmax = max(rows, key=lambda r: r["cl"])
        return {"m": m, "p": p, "t": t, "run_id": ident,
                "best_ld": best["cl"] / best["cd"], "alpha_at_best_ld": best["alpha"],
                "cl_at_best_ld": best["cl"], "cm_at_best_ld": best["cm"],
                "cl_max_observed": clmax["cl"], "alpha_at_cl_max_observed": clmax["alpha"],
                "cd_min_observed": min(r["cd"] for r in rows),
                "points_converged": len(rows)}


class ProjectEngine:
    """M22: evaluates a project.json through the algorithm modules (L-1). Variables are dotted paths into the project inputs
    (e.g. ``m21.cruise.speed_mps``; list items by index). Metrics are dotted paths into the outputs (``m21.payload_range.0.range_const_v_h_km``)
    plus ``m23.n_no_cumple`` / ``m23.n_cumple`` / ``m23.n_no_evaluable`` / ``m23.overall``. Only the metrics named by the objective, the
    constraints and ``settings.report_metrics`` are stored. A module that stops for missing data or a failed solver is a failed evaluation."""

    def __init__(self, base, workdir: Path, spec: "Spec | None" = None):
        from .project import new_project
        doc = json.loads(Path(base).read_text(encoding="utf-8")) if isinstance(base, (str, Path)) else deepcopy(base)
        if "inputs" in doc and doc.get("schema", "").startswith("aerosuite-project"):
            doc = doc["inputs"]
        self.inputs, self.workdir, self.spec = doc, workdir, spec
        self.settings = dict(spec.settings) if spec else {}
        self.f5 = dict(self.settings.get("flow5") or {})
        self.f5_enabled = bool(self.f5.get("enabled", False))
        self.f5_count = 0
        self.counter = 0
        self.levels_used: set = {"conceptual"}
        self.new_project = new_project
        names = [spec.objective["metric"]] if spec else []
        for c in (spec.constraints if spec else []):
            names += [c["metric"]] + ([c["value_metric"]] if "value_metric" in c else [])
        self.wanted = sorted(set(names) | set(self.settings.get("report_metrics", [])))

    @staticmethod
    def _set(doc: dict, path: str, value) -> None:
        keys = path.split(".")
        node = doc
        for k in keys[:-1]:
            node = node[int(k)] if isinstance(node, list) else node[k]
        last = keys[-1]
        if isinstance(node, list):
            node[int(last)] = value
        elif last in node:
            node[last] = value
        else:
            raise KeyError(f"variable path {path!r}: {last!r} is not an existing input (variables must name inputs already in the project)")

    @staticmethod
    def _get(doc, path: str):
        node = doc
        keys = path.split(".")
        i = 0
        while i < len(keys):
            if isinstance(node, list):
                node = node[int(keys[i])]
                i += 1
                continue
            # keys that contain dots themselves (e.g. altitudes "0.0") are tried by joining consecutive parts
            for j in range(len(keys), i, -1):
                cand = ".".join(keys[i:j])
                if isinstance(node, dict) and cand in node:
                    node = node[cand]
                    i = j
                    break
            else:
                raise KeyError(path)
        return node

    def metrics(self, values: dict) -> dict:
        from . import loop
        self.counter += 1
        project = self.new_project("m22-eval")
        project["inputs"] = deepcopy(self.inputs)
        for name, v in values.items():
            self._set(project["inputs"], name, float(v))
        try:
            info = loop.settle(project, int(self.settings.get("max_iter", 3)), float(self.settings.get("tol", 1e-6)))
        except loop.LoopStop as exc:
            raise RuntimeError(f"module {exc.module} stopped: {exc.message}") from exc
        except SystemExit as exc:
            raise RuntimeError(f"module stopped: {exc.code}") from exc
        out = {"loop_iterations": info["iterations"], "loop_stop": info["stop"]}
        results = {m: item["result"] for m, item in project["outputs"].items()}
        for m, item in project["outputs"].items():
            self.levels_used.add(item["run"]["level"])
        for name in self.wanted:
            if name.startswith(("m23.n_", "flow5.")) or name == "m23.overall":
                continue
            out[name] = float(self._get(results, name))
        m23 = results.get("m23")
        if m23:
            out.update({"m23.n_cumple": m23["counts"]["cumple"], "m23.n_no_cumple": m23["counts"]["no cumple"],
                        "m23.n_no_evaluable": m23["counts"]["no evaluable"], "m23.overall": m23["overall"]})
        if self.f5_enabled:
            out.update(self._flow5(project))
        return out

    def _flow5(self, project: dict) -> dict:
        """3D level, only with settings.flow5.enabled: exports the M09b wing (flow5_config), runs the official flow5 (timeout, evaluation cap)
        and reads its polar (lift slope, CD0, k). Wing only: no fuselage/tail in this job."""
        from types import SimpleNamespace
        from .engines import flow5_executable
        from . import flow5_xml
        from .flow5_results import collect, fit_drag_polar, lift_slope
        cap = int(self.f5.get("max_evaluations", 3))
        if self.f5_count >= cap:
            raise RuntimeError(f"flow5 evaluation cap reached ({cap}); raise settings.flow5.max_evaluations deliberately")
        exe = flow5_executable(Path(self.f5["exe"]) if self.f5.get("exe") else None)
        if exe is None:
            raise FileNotFoundError("official flow5 not found (AEROSUITE_FLOW5 or settings.flow5.exe)")
        cfg = project["outputs"].get("m09b", {}).get("result", {}).get("flow5_config")
        if not cfg:
            raise RuntimeError("flow5 level needs inputs.m09b.flow5 (M09b exports the wing configuration)")
        self.f5_count += 1
        job = self.workdir / "flow5_jobs" / f"eval{self.counter:04d}"
        job.mkdir(parents=True, exist_ok=True)
        cfg_path = job / "config.json"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        flow5_xml.export(cfg_path, job / "job")
        manifest = flow5_xml.run(job / "job", exe, int(self.f5.get("timeout_s", 300)))
        if manifest.get("return_code") != 0:
            raise RuntimeError(f"flow5 failed: {manifest.get('status')}")
        polars = collect(job / "job" / "output")["polars"]
        if not polars:
            raise RuntimeError("flow5 produced no polar")
        pol = SimpleNamespace(**{k: polars[0].get(k) for k in ("rows", "path", "plane", "polar")})
        self.levels_used.add("3D")
        fit = fit_drag_polar(pol)["model_simplified"]
        return {"flow5.cl_alpha_per_rad": lift_slope(pol)["CL_alpha_per_rad"], "flow5.cd0": fit["CD0"], "flow5.k": fit["k"],
                "flow5.job": str(job / "job")}


ENGINES = {"adrpy": AdrpyEngine, "xfoil": XfoilEngine, "project": ProjectEngine}


# ----------------------------------------------------------------- contract
@dataclass
class Spec:
    name: str
    engine: str
    base: object
    variables: list[dict]
    objective: dict
    constraints: list[dict] = field(default_factory=list)
    method: str = "differential_evolution"
    settings: dict = field(default_factory=dict)
    ranking: dict = field(default_factory=dict)
    level: str | None = None

    @classmethod
    def load(cls, path: Path) -> "Spec":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        allowed = set(cls.__dataclass_fields__)
        unknown = set(data) - allowed - {"notes", "description"}
        if unknown:
            raise ValueError(f"Unknown spec keys: {sorted(unknown)}")
        spec = cls(**{k: v for k, v in data.items() if k in allowed})
        if isinstance(spec.base, str):
            base_path = Path(spec.base)
            if not base_path.is_absolute():
                base_path = (Path(path).resolve().parent / base_path)
                if not base_path.is_file():
                    base_path = Path(spec.base).resolve()
            spec.base = base_path
        spec.validate()
        return spec

    def validate(self) -> None:
        if self.engine == "flow5":
            raise ValueError("Engine 'flow5' (3D) is not connected to the optimizer in this stage; "
                             "see PROJECT_STATE.md, pending connection C-3D-OPT")
        if self.engine not in ENGINES:
            raise ValueError(f"engine must be one of {sorted(ENGINES)}")
        expected = LEVELS[self.engine]
        if self.engine == "project" and (self.settings.get("flow5") or {}).get("enabled"):
            expected = "aero3d"
        if self.level and self.level != expected:
            raise ValueError(f"level {self.level!r} does not match engine {self.engine!r} ({expected})")
        self.level = expected
        if not self.variables:
            raise ValueError("At least one decision variable is required")
        for v in self.variables:
            lo, hi = float(v["lower"]), float(v["upper"])
            if not (math.isfinite(lo) and math.isfinite(hi) and lo < hi):
                raise ValueError(f"Invalid bounds for {v.get('name')}")
        if self.objective.get("sense", "minimize") not in ("minimize", "maximize") or not self.objective.get("metric"):
            raise ValueError("objective requires metric and sense minimize|maximize")
        for c in self.constraints:
            if c.get("type") not in ("<=", ">=") or not c.get("metric"):
                raise ValueError(f"Invalid constraint {c}")
            if ("value" in c) == ("value_metric" in c):
                raise ValueError(f"Constraint {c['metric']} needs exactly one of value / value_metric")
        if self.method not in ("differential_evolution", "SLSQP", "grid"):
            raise ValueError("method must be differential_evolution, SLSQP or grid")


# ----------------------------------------------------------------- run
class Evaluator:
    def __init__(self, spec: Spec, engine):
        self.spec, self.engine = spec, engine
        self.names = [v["name"] for v in spec.variables]
        self.cache: dict[tuple, dict] = {}
        self.records: list[dict] = []

    def __call__(self, x) -> dict:
        key = tuple(round(float(v), 12) for v in x)
        if key in self.cache:
            return self.cache[key]
        values = dict(zip(self.names, key))
        record = {"index": len(self.records) + 1, "variables": values}
        started = time.time()
        try:
            record["metrics"] = self.engine.metrics(values)
            record["ok"] = True
        except Exception as exc:  # engine failure is data, not a penalty
            record["ok"] = False
            record["error"] = f"{type(exc).__name__}: {exc}"
            record["metrics"] = {}
        record["seconds"] = round(time.time() - started, 3)
        record["constraint_margins"] = self.margins(record["metrics"]) if record["ok"] else {}
        record["feasible"] = record["ok"] and all(m >= -1e-9 for m in record["constraint_margins"].values())
        self.cache[key] = record
        self.records.append(record)
        return record

    def margins(self, metrics: dict) -> dict:
        """Positive margin = satisfied. Units are those of the constrained metric."""
        out = {}
        for c in self.spec.constraints:
            key = f"{c['metric']}{c['type']}{c.get('value', c.get('value_metric'))}"
            value = metrics.get(c["metric"])
            limit = c.get("value", metrics.get(c.get("value_metric")))
            if value is None or limit is None:
                out[key] = float("-inf")
            else:
                out[key] = (float(limit) - float(value)) if c["type"] == "<=" else (float(value) - float(limit))
        return out

    def objective(self, x) -> float:
        record = self(x)
        if not record["ok"]:
            return math.inf
        value = float(record["metrics"][self.spec.objective["metric"]])
        return -value if self.spec.objective.get("sense") == "maximize" else value


def run(spec: Spec, out: Path) -> dict:
    import numpy as np
    from scipy.optimize import NonlinearConstraint, differential_evolution, minimize

    out.mkdir(parents=True, exist_ok=True)
    engine = ENGINES[spec.engine](spec.base, out, spec) if spec.engine == "project" else ENGINES[spec.engine](spec.base, out)
    ev = Evaluator(spec, engine)
    bounds = [(float(v["lower"]), float(v["upper"])) for v in spec.variables]
    s = spec.settings
    solver = {"method": spec.method}
    started = time.time()

    def margin_vector(x):
        record = ev(x)
        if not record["ok"]:
            return np.full(max(1, len(spec.constraints)), -1.0)
        values = np.array(list(record["constraint_margins"].values()) or [0.0], dtype=float)
        return np.where(np.isfinite(values), values, -1.0)

    if spec.method == "grid":
        n = int(s.get("grid_points", 7))
        axes = [np.linspace(lo, hi, n) for lo, hi in bounds]
        for x in itertools.product(*axes):
            ev(x)
        solver.update({"success": True, "message": f"full factorial grid {n}^{len(bounds)}"})
    elif spec.method == "differential_evolution":
        cons = [NonlinearConstraint(margin_vector, 0.0, np.inf)] if spec.constraints else ()
        res = differential_evolution(ev.objective, bounds, seed=int(s.get("seed", 42)),
                                     maxiter=int(s.get("maxiter", 50)), popsize=int(s.get("popsize", 10)),
                                     tol=float(s.get("tol", 1e-6)), polish=bool(s.get("polish", True)),
                                     constraints=cons, workers=1, updating="immediate")
        solver.update({"success": bool(res.success), "message": str(res.message), "nit": int(res.nit),
                       "nfev": int(res.nfev), "x": [float(v) for v in res.x]})
        ev(res.x)
    else:  # SLSQP: gradient-based, local; requires a smooth, always-successful engine
        x0 = s.get("x0") or [(lo + hi) / 2 for lo, hi in bounds]
        cons = [{"type": "ineq", "fun": margin_vector}] if spec.constraints else ()
        res = minimize(ev.objective, x0, method="SLSQP", bounds=bounds, constraints=cons,
                       options={"maxiter": int(s.get("maxiter", 100)), "ftol": float(s.get("tol", 1e-8))})
        solver.update({"success": bool(res.success), "message": str(res.message), "nit": int(res.nit),
                       "nfev": int(res.nfev), "x": [float(v) for v in res.x]})
        ev(res.x)

    sense = spec.objective.get("sense", "minimize")
    metric = spec.objective["metric"]
    feasible = [r for r in ev.records if r["feasible"]]
    feasible.sort(key=lambda r: r["metrics"][metric], reverse=(sense == "maximize"))
    top = int(spec.ranking.get("top", 10))
    best = feasible[0] if feasible else None
    at_bounds = []
    if best:
        for v in spec.variables:
            val, lo, hi = best["variables"][v["name"]], float(v["lower"]), float(v["upper"])
            if min(abs(val - lo), abs(val - hi)) <= 1e-3 * (hi - lo):
                at_bounds.append(v["name"])
    result = {
        "name": spec.name, "level": spec.level, "engine": spec.engine,
        "level_statement": {
            "conceptual": "Conceptual optimization on ADRpy constraint analysis; not an aerodynamic shape optimization.",
            "aero2d": "2D aerodynamic optimization on real XFOIL polars of a NACA 4-digit section; "
                      "not a 3D wing or aircraft optimization.",
            "aero3d": "Project optimization with real 3D flow5 wing polars (settings.flow5.enabled); the rest of each evaluation is the "
                      "conceptual level of the algorithm modules. Wing-only flow5 model.",
        }[spec.level] if spec.engine != "project" or spec.level == "aero3d" else
        "Conceptual project optimization: Gudmundsson algorithm modules and ADRpy (M22). Modules that call XFOIL contribute 2D data "
        "(see levels_used); it is not a 3D or CFD optimization.",
        "variables": spec.variables, "objective": spec.objective, "constraints": spec.constraints,
        "solver": solver, "wall_time_s": round(time.time() - started, 2),
        "evaluations": len(ev.records),
        "failed_evaluations": sum(1 for r in ev.records if not r["ok"]),
        "feasible_evaluations": len(feasible),
        "levels_used": sorted(engine.levels_used) if spec.engine == "project" else [spec.level],
        "roles": {"decision_variables": [v["name"] for v in spec.variables], "objective": spec.objective,
                  "constraints": spec.constraints, "settings": spec.settings},
        "physical_viability": ({"m23.overall": best["metrics"].get("m23.overall"), "m23.n_no_cumple": best["metrics"].get("m23.n_no_cumple"),
                                "note": "viability = M23 requirements check of the best point (cumple / no cumple / no evaluable)"}
                               if best and "m23.overall" in best["metrics"] else
                               {"note": "no M23 result in this project: viability beyond the listed constraints is not assessed"}),
        "best": best, "best_variables_at_bounds": at_bounds,
        "ranking": feasible[:top],
        "convergence_note": ("Solver reported success" if solver.get("success") else
                             "Solver did NOT report convergence; treat best as the best sampled point only"),
        "viability_note": "Feasibility here means only the constraints listed in this spec; physical/structural "
                          "viability outside them is not assessed.",
    }
    (out / "optimization.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    with (out / "evaluations.csv").open("w", newline="", encoding="utf-8") as f:
        metric_keys = sorted({k for r in ev.records for k in r["metrics"]})
        margin_keys = sorted({k for r in ev.records for k in r["constraint_margins"]})
        writer = csv.writer(f)
        writer.writerow(["index", "ok", "feasible", "seconds", *ev.names, *metric_keys, *margin_keys, "error"])
        for r in ev.records:
            writer.writerow([r["index"], r["ok"], r["feasible"], r["seconds"],
                             *[r["variables"][n] for n in ev.names],
                             *[r["metrics"].get(k, "") for k in metric_keys],
                             *[r["constraint_margins"].get(k, "") for k in margin_keys], r.get("error", "")])
    return result
