"""project.json: single source of truth for a design (Gudmundsson Sec. 1.4.2 "General" sheet).

Layout:
  inputs[mxx]   values given by the user (SI, except aviation units named in the key, e.g. *_kcas)
  outputs[mxx]  last result of the module plus a run record (inputs hash, dependencies, level, references)
  assumptions   list of {module, key, value, reason}: data absent from every source, never presented as a result
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "aerosuite-project/1"
LEVELS = ("conceptual", "2D", "3D")


def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def new_project(name: str) -> dict:
    return {"schema": SCHEMA, "name": name, "units": "SI", "inputs": {}, "outputs": {}, "assumptions": []}


def load(path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"{path}: schema {data.get('schema')!r} is not {SCHEMA!r}")
    return data


def save(project: dict, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(project, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    os.replace(tmp, path)


def add_assumption(project: dict, module: str, key: str, value, reason: str) -> None:
    entry = {"module": module, "key": key, "value": value, "reason": reason}
    if entry not in project["assumptions"]:
        project["assumptions"].append(entry)


def record(project: dict, module: str, result: dict, level: str, references: list[str], depends_on=()) -> dict:
    """Store a module result with its run record. depends_on: module ids whose outputs were read."""
    if level not in LEVELS:
        raise ValueError(f"level must be one of {LEVELS}")
    deps = {d: digest(project["outputs"][d]["result"]) for d in depends_on}
    project["outputs"][module] = {
        "result": result,
        "run": {"module": module, "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "inputs_sha256": digest(project["inputs"].get(module, {})), "depends_on": deps,
                "level": level, "references": references}}
    return project["outputs"][module]


def stale(project: dict) -> list[str]:
    """Modules whose stored output no longer matches their inputs or the outputs they depend on."""
    out = []
    for module, item in project["outputs"].items():
        run = item["run"]
        if run["inputs_sha256"] != digest(project["inputs"].get(module, {})):
            out.append(module)
            continue
        for dep, h in run["depends_on"].items():
            if dep not in project["outputs"] or digest(project["outputs"][dep]["result"]) != h:
                out.append(module)
                break
    return out


def need_inputs(project: dict, module: str, required: list[str]) -> dict:
    data = project["inputs"].get(module)
    if data is None:
        raise SystemExit(f"project has no inputs.{module}")
    missing = [k for k in required if k not in data]
    if missing:
        raise SystemExit(f"inputs.{module} is missing: {', '.join(missing)}")
    return data
