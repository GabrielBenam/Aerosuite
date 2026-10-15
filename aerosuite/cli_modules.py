"""CLI for the algorithm modules (M01...) and project.json handling."""
import json
from pathlib import Path

from . import project as prj

# command -> (module id, importable "package.module", help)
MODULES = {
    "m01": ("m01", "m01_requirements", "M01 requirements and regulatory basis (Gudmundsson step 1)"),
    "m02": ("m02", "m02_references", "M02 reference aircraft database, weight ratios and regressions (step 2)"),
}


def add_commands(sub) -> None:
    init = sub.add_parser("project-init", help="Create an empty project.json")
    init.add_argument("--project", type=Path, required=True)
    init.add_argument("--name", required=True)
    init.add_argument("--from-inputs", type=Path, help="JSON {module: {inputs}} to preload")
    status = sub.add_parser("project-status", help="List stored outputs and stale modules")
    status.add_argument("--project", type=Path, required=True)
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
        print(json.dumps({"name": data["name"], "outputs": sorted(data["outputs"]), "stale": prj.stale(data),
                          "assumptions": data["assumptions"]}, indent=2, ensure_ascii=False))
        return True
    if args.command in MODULES:
        module = importlib.import_module(f"aerosuite.{MODULES[args.command][1]}")
        data = prj.load(args.project)
        result = module.run(data)
        prj.save(data, args.project)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=float))
        return True
    return False
