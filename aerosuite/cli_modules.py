"""CLI for the algorithm modules (M01...) and project.json handling."""
import json
from pathlib import Path

from . import project as prj

# command -> (module id, importable "package.module", help)
MODULES = {
    "m01": ("m01", "m01_requirements", "M01 requirements and regulatory basis (Gudmundsson step 1)"),
    "m02": ("m02", "m02_references", "M02 reference aircraft database, weight ratios and regressions (step 2)"),
    "m03": ("m03", "m03_costs", "M03 development and operating costs, Eastlake model (step 3)"),
    "m04": ("m04", "m04_constraints", "M04 constraint diagram, stall and landing limits (steps 4, 5, 7)"),
    "m08": ("m08", "m08_tail", "M08 initial tail sizing, VHT/VVT and tail arm (step 8)"),
    "m09a": ("m09a", "m09a_airfoils", "M09a airfoil analysis (XFOIL) and decision matrix (step 9)"),
    "m06": ("m06", "m06_weight", "M06 initial weight: historical ratios, empty-weight fraction, mission, electric (step 6)"),
}


def add_commands(sub) -> None:
    init = sub.add_parser("project-init", help="Create an empty project.json")
    init.add_argument("--project", type=Path, required=True)
    init.add_argument("--name", required=True)
    init.add_argument("--from-inputs", type=Path, help="JSON {module: {inputs}} to preload")
    status = sub.add_parser("project-status", help="List stored outputs and stale modules")
    status.add_argument("--project", type=Path, required=True)
    exp = sub.add_parser("export", help="Write a module result as JSON (SI units) for later CAD use (M24)")
    exp.add_argument("--project", type=Path, required=True)
    exp.add_argument("--module", required=True, help="module id, e.g. m08")
    exp.add_argument("--out", type=Path, required=True)
    for cmd, (_, _, help_text) in MODULES.items():
        p = sub.add_parser(cmd, help=help_text)
        p.add_argument("--project", type=Path, required=True, help="project.json (reads inputs.%s, writes outputs.%s)" % (cmd, cmd))


def dispatch(args) -> bool:
    import importlib
    if args.command == "project-init":
        if args.project.exists():
            raise SystemExit(f"{args.project} already exists; refusing to overwrite")
        data = prj.new_project(args.name)
        if args.from_inputs:
            data["inputs"] = json.loads(args.from_inputs.read_text(encoding="utf-8"))
        prj.save(data, args.project)
        print(f"Created {args.project}")
        return True
    if args.command == "project-status":
        data = prj.load(args.project)
        summary = {"name": data["name"], "outputs": sorted(data["outputs"]), "stale": prj.stale(data),
                   "assumptions": data["assumptions"]}
        if "m03" in data["outputs"]:
            summary["nota_costos_m03"] = data["outputs"]["m03"]["result"].get("nota_costos")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return True
    if args.command == "export":
        data = prj.load(args.project)
        if args.module not in data["outputs"]:
            raise SystemExit(f"outputs.{args.module} is missing: run {args.module} first")
        if args.out.exists():
            raise SystemExit(f"{args.out} already exists; refusing to overwrite")
        item = data["outputs"][args.module]
        stale = args.module in prj.stale(data)
        payload = {"schema": "aerosuite-export/1", "project": data["name"], "module": args.module, "units": "SI",
                   "stale": stale, "run": item["run"], "result": item["result"]}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
        print(f"Exported {args.module} to {args.out}" + (" (WARNING: stale)" if stale else ""))
        return True
    if args.command in MODULES:
        module = importlib.import_module(f"aerosuite.{MODULES[args.command][1]}")
        data = prj.load(args.project)
        result = module.run(data)
        prj.save(data, args.project)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=float))
        return True
    return False
