"""AeroSuite command line (python -m aerosuite <command>). Minimal interface over the original engines."""
import argparse
import json
import subprocess
from pathlib import Path

from .airfoils import write_csv, write_dat
from .preselection import Requirements, evaluate_naca4


def _floats(text: str) -> list[float]:
    return [float(v) for v in str(text).split(",") if v.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m aerosuite",
                                     description="AeroSuite: flow5 v7.57, ADRpy 0.2.6, XFOIL 6.99 and SciPy, used unmodified.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Report engines, pinned versions and executables actually found")

    gen = sub.add_parser("generate", help="NACA 4-digit coordinates (geometry only)")
    gen.add_argument("code")
    gen.add_argument("--out", type=Path, default=Path("results"))
    gen.add_argument("--points", type=int, default=81)

    select = sub.add_parser("shortlist", help="Filter NACA codes by geometry only (no aerodynamics)")
    select.add_argument("codes", nargs="+")
    select.add_argument("--min-thickness", type=float, default=.10)
    select.add_argument("--max-thickness", type=float, default=.18)
    select.add_argument("--max-camber", type=float, default=.05)
    select.add_argument("--out", type=Path, default=Path("results/shortlist.json"))

    xf = sub.add_parser("xfoil", help="Real polars with the external XFOIL executable")
    xf.add_argument("profiles", nargs="+", help="NACA four digits or UIUC identifiers")
    xf.add_argument("--exe", type=Path, help="xfoil executable (default: runtime/xfoil or AEROSUITE_XFOIL)")
    xf.add_argument("--uiuc-zip", type=Path)
    xf.add_argument("--reynolds", type=str, default="1000000", help="one value or comma list, e.g. 2e5,5e5,1e6")
    xf.add_argument("--mach", type=float, default=0.0)
    xf.add_argument("--ncrit", type=float, default=9.0)
    xf.add_argument("--xtr-top", type=float, default=1.0)
    xf.add_argument("--xtr-bottom", type=float, default=1.0)
    xf.add_argument("--alpha-start", type=float, default=-2.0)
    xf.add_argument("--alpha-end", type=float, default=8.0)
    xf.add_argument("--alpha-step", type=float, default=2.0)
    xf.add_argument("--iterations", type=int, default=150)
    xf.add_argument("--from-zero", action="store_true", help="sweep 0->max and 0->min in two runs (better convergence)")
    xf.add_argument("--timeout", type=int, default=180)
    xf.add_argument("--compare", action="store_true", help="compare the profiles after the run")
    xf.add_argument("--allow-partial", action="store_true", help="compare using converged points only")
    xf.add_argument("--out", type=Path, default=Path("results/xfoil"))

    comp = sub.add_parser("compare", help="Compare existing polar CSV+JSON (same Re, Mach, Ncrit, Xtr)")
    comp.add_argument("profiles", nargs="+")
    comp.add_argument("--polars", type=Path, required=True)
    comp.add_argument("--out", type=Path, default=Path("results/comparison"))
    comp.add_argument("--uiuc-zip", type=Path)
    comp.add_argument("--no-charts", action="store_true")
    comp.add_argument("--allow-partial", action="store_true")

    atm = sub.add_parser("atmos", help="ISA table from ADRpy (+ Sutherland viscosity)")
    atm.add_argument("--alt", type=str, default="0,1000,2000,3000,5000,8000,11000", help="altitudes in m")
    atm.add_argument("--offset", type=float, default=0.0, help="ISA temperature offset (K)")
    atm.add_argument("--out", type=Path)

    rey = sub.add_parser("reynolds", help="Reynolds and Mach for a flight condition (ADRpy ISA)")
    rey.add_argument("--alt", type=float, required=True, help="m")
    rey.add_argument("--speed", type=float, required=True, help="true airspeed, m/s")
    rey.add_argument("--chord", type=float, required=True, help="m")
    rey.add_argument("--offset", type=float, default=0.0)

    sizing = sub.add_parser("size", help="ADRpy constraint analysis (T/W vs W/S)")
    sizing.add_argument("--config", type=Path, required=True)
    sizing.add_argument("--out", type=Path, default=Path("results/conceptual-sizing.json"))
    sizing.add_argument("--plot", type=Path, help="PNG constraint diagram")
    sizing.add_argument("--local-tw", action="store_true", help="T/W at each constraint condition (not mapped to sea level)")

    opt = sub.add_parser("optimize", help="Legacy: minimize T/W over W/S and AR (see 'opt')")
    opt.add_argument("--config", type=Path, required=True)
    opt.add_argument("--out", type=Path, default=Path("results/conceptual-optimum.json"))

    gopt = sub.add_parser("opt", aliases=["m22"], help="General optimizer from a JSON spec (engines: adrpy, xfoil, project); m22 = multilevel project optimizer")
    gopt.add_argument("--spec", type=Path, required=True)
    gopt.add_argument("--out", type=Path, required=True, help="output folder")

    val = sub.add_parser("validate", help="Check engines against published references (ISA, ADRpy docs, Gudmundsson)")
    val.add_argument("--out", type=Path, default=Path("results/validation/validation.json"))

    flow = sub.add_parser("flow5", help="Open the official, unmodified flow5 application")
    flow.add_argument("--exe", type=Path, help="Path to official flow5.exe")

    fexp = sub.add_parser("flow5-export", help="Write foils, plane XML, polar XML and script XML for flow5")
    fexp.add_argument("--config", type=Path, required=True)
    fexp.add_argument("--out", type=Path, required=True, help="job folder")

    fres = sub.add_parser("flow5-results", help="Read flow5 output files (polars, operating points) into SI JSON")
    fres.add_argument("--dir", type=Path, required=True, help="flow5 output folder (job/output)")
    fres.add_argument("--out", type=Path, required=True, help="JSON file to write")
    fres.add_argument("--mac", type=float, help="mean aerodynamic chord in m, for the static margin")
    fres.add_argument("--cl-min", type=float)
    fres.add_argument("--cl-max", type=float)

    frun = sub.add_parser("flow5-run", help="Run official flow5 in batch mode on an exported job (flow5 -s)")
    frun.add_argument("--job", type=Path, required=True)
    frun.add_argument("--exe", type=Path)
    frun.add_argument("--timeout", type=int, default=1800)
    from .cli_modules import add_commands
    add_commands(sub)
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    from .cli_modules import dispatch
    if dispatch(args):
        return
    if args.command == "status":
        from .engines import status
        print(json.dumps(status(), indent=2))
    elif args.command == "generate":
        write_csv(args.code, args.out/f"naca{args.code}.csv", args.points)
        write_dat(args.code, args.out/f"naca{args.code}.dat", args.points)
        print(f"Generated NACA {args.code}: {args.out.resolve()}")
    elif args.command == "shortlist":
        req = Requirements(args.min_thickness, args.max_thickness, args.max_camber)
        result = {"analysis_type": "GEOMETRY_CONSTRAINTS_ONLY", "requirements": vars(req),
                  "results": evaluate_naca4(args.codes, req)}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
    elif args.command == "xfoil":
        from .engines import xfoil_executable
        from .xfoil_cli import XFoilCase, load_naca_selected, load_uiuc_selected, run_profile
        exe = xfoil_executable(args.exe)
        if exe is None:
            raise SystemExit("XFOIL executable not found: use --exe, AEROSUITE_XFOIL or scripts/setup-engines.ps1")
        profiles = (load_uiuc_selected(args.uiuc_zip, args.profiles) if args.uiuc_zip
                    else load_naca_selected(args.profiles))
        reynolds = _floats(args.reynolds)
        summary = []
        for re_value in reynolds:
            case = XFoilCase(re_value, args.mach, args.ncrit, args.alpha_start, args.alpha_end, args.alpha_step,
                             args.iterations, args.xtr_top, args.xtr_bottom, args.from_zero)
            out = args.out if len(reynolds) == 1 else args.out / f"re{re_value:.0f}"
            results = [run_profile(exe, ident, foil, case, out, args.timeout) for ident, foil in profiles]
            summary += results
            if args.compare and len(profiles) > 1:
                from .batch_compare import Comparison, compare
                cmp = compare(Comparison(tuple(i for i, _ in profiles), out, out / "comparison", args.uiuc_zip,
                                         args.allow_partial))
                print(json.dumps(cmp["ranking"], indent=2))
        print(json.dumps(summary, indent=2))
    elif args.command == "compare":
        from .batch_compare import Comparison, compare
        result = compare(Comparison(tuple(args.profiles), args.polars, args.out, args.uiuc_zip, args.allow_partial),
                         charts=not args.no_charts)
        print(json.dumps(result, indent=2))
    elif args.command == "atmos":
        from .adrpy_core import atmosphere_table, export_result
        table = atmosphere_table(_floats(args.alt), args.offset)
        if args.out:
            export_result(table, args.out)
        print(json.dumps(table, indent=2))
    elif args.command == "reynolds":
        from .adrpy_core import reynolds_number
        print(json.dumps(reynolds_number(args.alt, args.speed, args.chord, args.offset), indent=2))
    elif args.command == "size":
        from .adrpy_core import load_concept, size, export_result, plot_constraint_diagram
        result = size(load_concept(args.config), map2sl=not args.local_tw)
        export_result(result, args.out)
        if args.plot:
            plot_constraint_diagram(result, args.plot)
        print(json.dumps({k: result[k] for k in ("engine", "config_name", "constraints_evaluated",
                                                 "stall_limit_wingloading_pa", "design_point_rule", "best_sample")},
                         indent=2, ensure_ascii=False))
    elif args.command == "optimize":
        from .adrpy_core import load_concept, optimize, export_result
        result = optimize(load_concept(args.config))
        export_result(result, args.out)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.command in ("opt", "m22"):
        from .optimizer import Spec, run
        result = run(Spec.load(args.spec), args.out)
        print(json.dumps({k: result[k] for k in ("name", "level", "level_statement", "solver", "evaluations",
                                                 "failed_evaluations", "feasible_evaluations", "best",
                                                 "best_variables_at_bounds", "convergence_note")},
                         indent=2, ensure_ascii=False, default=float))
    elif args.command == "validate":
        from .validation import run_all
        print(json.dumps(run_all(args.out), indent=2, ensure_ascii=False))
    elif args.command == "flow5":
        from .engines import flow5_executable
        exe = flow5_executable(args.exe)
        if exe is None:
            raise SystemExit("Official flow5 not installed. Run scripts/setup-engines.ps1 or supply --exe.")
        subprocess.Popen([str(exe)], cwd=exe.parent)
        print(f"Official upstream flow5 started (no AeroSuite modifications): {exe}")
    elif args.command == "flow5-export":
        from .flow5_xml import export
        print(json.dumps(export(args.config, args.out), indent=2))
    elif args.command == "flow5-results":
        from .flow5_results import Flow5Polar, collect, export_json, fit_drag_polar, lift_slope, static_margin
        data = collect(args.dir)
        derived = []
        for item in data["polars"]:
            pol = Flow5Polar(**item)
            entry = {"plane": pol.plane, "polar": pol.polar}
            for name, fn in (("drag_polar", lambda: fit_drag_polar(pol, args.cl_min, args.cl_max)),
                             ("lift_slope", lambda: lift_slope(pol)),
                             ("static_margin", lambda: static_margin(pol, args.mac) if args.mac else None)):
                try:
                    value = fn()
                    if value is not None:
                        entry[name] = value
                except (ValueError, KeyError) as exc:
                    entry[name] = {"error": str(exc)}
            derived.append(entry)
        data["derived"] = derived
        export_json(data, args.out)
        print(json.dumps({"polars": len(data["polars"]), "operating_points": len(data["operating_points"]),
                          "errors": data["errors"], "derived": derived}, indent=2, default=float))
    elif args.command == "flow5-run":
        from .engines import flow5_executable
        from .flow5_xml import run
        exe = flow5_executable(args.exe)
        if exe is None:
            raise SystemExit("Official flow5 not installed. Run scripts/setup-engines.ps1 or supply --exe.")
        print(json.dumps(run(args.job, exe, args.timeout), indent=2))


if __name__ == "__main__":
    main()
