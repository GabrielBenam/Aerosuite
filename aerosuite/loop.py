"""L-1 Lazo completo del algoritmo de Gudmundsson (Tabla 1-4, pasos 1 a 23) sobre un project.json.

El lazo no contiene fisica: llama a `run(project)` de cada modulo con las entradas del proyecto y las salidas ya guardadas, usando el
mecanismo de dependencias y la marca de "desactualizado" de `project.py`. Una iteracion es una pasada por los modulos del plan (los
que tienen `inputs.mXX`) que no tienen salida o estan desactualizados, en el orden de la Tabla 1-4; un modulo que necesita la salida de
otro que aun no corrio ("run mYY first") se pospone dentro de la misma pasada. El libro no impone una regla de actualizacion de las
variables de diseno entre iteraciones y no se inventa una (D-46): el lazo solo recalcula con las entradas del proyecto; las
actualizaciones de diseno las hace el usuario o el optimizador (M22).

Cada iteracion se guarda en `<out>/iter-NNN.json` (numero, entradas, salidas, estado) y `<out>/loop.json` resume la corrida; una carpeta
`--out` nueva por corrida, nunca se sobrescribe nada. Falta de datos: el lazo se detiene en el modulo, con el mensaje y la lista de claves
faltantes; no rellena con supuestos."""
import importlib
import json
import platform
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import project as prj
from .cli_modules import MODULES

# Orden de la Tabla 1-4. M22 (optimizador) no forma parte del lazo: lo usa por encima (aerosuite/m22_optimizer.py).
ORDER = ["m01", "m02", "m03", "m04", "m06", "m08", "m09a", "m09b", "m10", "m11", "m12", "m13", "m15", "m16",
         "m18a", "m18b", "m18c", "m19", "m20", "m21", "m23"]
STEPS = {"m01": "1", "m02": "2", "m03": "3", "m04": "4-5,7", "m06": "6", "m08": "8", "m09a": "9", "m09b": "9", "m10": "10",
         "m11": "11", "m12": "12", "m13": "13-14", "m15": "15", "m16": "16-17", "m18a": "18", "m18b": "18", "m18c": "18",
         "m19": "19", "m20": "20", "m21": "21", "m23": "23"}
_RUN_FIRST = re.compile(r"run ((?:m\d+[abc]?)(?: and m\d+[abc]?)*)(?: first|\b)")
_MOD_ID = re.compile(r"\bm\d+[abc]?\b")


class LoopStop(Exception):
    def __init__(self, module: str, message: str, status=None, executed=None):
        super().__init__(message)
        self.module, self.message = module, message
        self.status, self.executed = status or {}, executed or []


def plan(project: dict) -> list[str]:
    """Modulos del plan: los de ORDER con entradas en el proyecto (M23 entra si hay entradas de M01: sus requisitos)."""
    mods = [m for m in ORDER if m in project["inputs"] and m in MODULES]
    if "m23" in MODULES and "m01" in project["inputs"] and "m23" not in mods:
        mods.append("m23")
    return mods


def _flatten(obj, prefix="", out=None):
    out = {} if out is None else out
    if isinstance(obj, bool) or obj is None or isinstance(obj, str):
        out[prefix] = obj
    elif isinstance(obj, (int, float)):
        out[prefix] = float(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _flatten(v, f"{prefix}/{k}", out)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _flatten(v, f"{prefix}[{i}]", out)
    return out


def snapshot(project: dict) -> dict:
    return {m: _flatten(item["result"]) for m, item in project["outputs"].items()}


def max_relative_change(a: dict, b: dict) -> float:
    """Mayor cambio relativo |x - y| / max(|x|, |y|, 1e-12) entre dos instantaneas; 1.0 si cambian claves o textos."""
    worst = 0.0
    for m in set(a) | set(b):
        fa, fb = a.get(m), b.get(m)
        if fa is None or fb is None or fa.keys() != fb.keys():
            return 1.0
        for k, x in fa.items():
            y = fb[k]
            if isinstance(x, float) and isinstance(y, float):
                if abs(x - y) > 1e-12:
                    worst = max(worst, abs(x - y) / max(abs(x), abs(y), 1e-12))
            elif x != y:
                return 1.0
    return worst


def missing_keys(message: str) -> list[str]:
    m = re.search(r"is missing:? ?(.*)$", message)
    return [k.strip() for k in re.split(r",\s*", m.group(1)) if k.strip()] if m and m.group(1).strip() else []


def _run_module(project: dict, module: str) -> float:
    mod = importlib.import_module(f"aerosuite.{MODULES[module][1]}")
    t0 = time.perf_counter()
    mod.run(project)
    return time.perf_counter() - t0


def run_iteration(project: dict, modules: list[str]) -> tuple[dict, list[str]]:
    """Una pasada. Devuelve (estado por modulo, orden ejecutado). Lanza LoopStop ante datos faltantes."""
    stale = set(prj.stale(project))
    pending = [m for m in modules if m not in project["outputs"] or m in stale]
    status = {m: {"status": "up_to_date"} for m in modules if m not in pending}
    executed: list[str] = []
    progress = True
    while pending and progress:
        progress = False
        for m in list(pending):
            try:
                secs = _run_module(project, m)
            except SystemExit as exc:
                msg = str(exc.code if exc.code is not None else exc)
                hit = _RUN_FIRST.search(msg)
                needed = _MOD_ID.findall(hit.group(1)) if hit else []
                # se pospone solo si lo que falta es la salida de un modulo del plan que aun esta pendiente
                if needed and any(x in pending and x != m for x in needed):
                    status[m] = {"status": "deferred", "waiting_for": needed}
                    continue
                status[m] = {"status": "stopped", "message": msg, "missing_keys": missing_keys(msg)}
                raise LoopStop(m, msg, status, executed) from exc
            run = project["outputs"][m]["run"]
            status[m] = {"status": "ran", "seconds": round(secs, 4), "level": run["level"], "inputs_sha256": run["inputs_sha256"],
                         "depends_on": run["depends_on"]}
            executed.append(m)
            pending.remove(m)
            progress = True
    if pending:
        m = pending[0]
        raise LoopStop(m, f"{m} waits for {status.get(m, {}).get('waiting_for')}, which cannot run (cyclic dependency among pending modules)",
                       status, executed)
    return status, executed


def _versions() -> dict:
    import numpy
    out = {"python": sys.version.split()[0], "numpy": numpy.__version__, "platform": platform.platform()}
    try:
        import scipy
        out["scipy"] = scipy.__version__
    except ImportError:
        pass
    return out


def _next_out(project_path: Path) -> Path:
    base = project_path.with_name(project_path.stem + ".loop")
    n = 1
    while (base / f"run-{n:03d}").exists():
        n += 1
    return base / f"run-{n:03d}"


def run_loop(project_path, max_iter: int = 5, tol: float = 1e-6, out_dir=None) -> dict:
    project_path = Path(project_path)
    project = prj.load(project_path)
    out = Path(out_dir) if out_dir else _next_out(project_path)
    if out.exists():
        raise SystemExit(f"{out} already exists; refusing to overwrite (use a new --out)")
    out.mkdir(parents=True)
    modules = plan(project)
    summary = {"schema": "aerosuite-loop/1", "project": str(project_path), "project_name": project["name"],
               "inputs_sha256": prj.digest(project["inputs"]), "plan": modules, "steps": {m: STEPS[m] for m in modules},
               "max_iter": max_iter, "tol_relative": tol, "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "versions": _versions(), "iterations": [],
               "update_rule": "none: the loop only recomputes with the project inputs (D-46); design updates are the user's or M22's"}
    stop = None
    for it in range(1, max_iter + 1):
        record = {"schema": "aerosuite-loop-iter/1", "iteration": it, "started": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        before = snapshot(project)
        try:
            status, executed = run_iteration(project, modules)
            record.update({"status": "completed", "modules": status, "order_executed": executed})
        except LoopStop as exc:
            record.update({"status": "stopped", "stopped_at": exc.module, "message": exc.message, "order_executed": exc.executed,
                           "modules": exc.status, "missing_keys": missing_keys(exc.message)})
            stop = {"reason": "missing_data", "module": exc.module, "message": exc.message, "missing_keys": missing_keys(exc.message)}
        changed = max_relative_change(before, snapshot(project)) if before else None
        record["max_relative_change_vs_previous_state"] = changed
        record["inputs"] = {m: project["inputs"].get(m) for m in record["order_executed"]}
        record["outputs"] = {m: project["outputs"][m]["result"] for m in record["order_executed"]}
        record["stale_after"] = prj.stale(project)
        prj.save(project, project_path)
        (out / f"iter-{it:03d}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
        summary["iterations"].append({k: record[k] for k in ("iteration", "status", "order_executed", "max_relative_change_vs_previous_state",
                                                               "stale_after")})
        if stop:
            break
        m23 = project["outputs"].get("m23", {}).get("result", {})
        if m23.get("overall") == "cumple":
            stop = {"reason": "requirements_met (step 23)"}
        elif not record["order_executed"]:
            stop = {"reason": "nothing_to_run (no stale output)"}
        elif not record["stale_after"]:
            stop = {"reason": "stable (no stale output after the pass)"}
        elif it >= 2 and changed is not None and changed <= tol:
            stop = {"reason": "converged (two consecutive iterations without change beyond tol)", "max_relative_change": changed}
        if stop:
            break
    summary["stop"] = stop or {"reason": "max_iter reached", "max_iter": max_iter}
    summary["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary["outputs"] = sorted(project["outputs"])
    summary["stale"] = prj.stale(project)
    summary["m23_overall"] = project["outputs"].get("m23", {}).get("result", {}).get("overall")
    summary["output_dir"] = str(out)
    (out / "loop.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    return summary
