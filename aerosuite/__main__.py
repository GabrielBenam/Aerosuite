"""CLI de prototipo AeroSuite."""
import argparse
import json
import subprocess
from pathlib import Path
from .airfoils import write_csv, write_dat
from .preselection import Requirements, evaluate_naca4

def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m aerosuite")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="Generar coordenadas NACA")
    gen.add_argument("code")
    gen.add_argument("--out", type=Path, default=Path("results"))
    gen.add_argument("--points", type=int, default=81)
    select = sub.add_parser("shortlist", help="Filtrar por geometría, no CFD")
    select.add_argument("codes", nargs="+")
    select.add_argument("--min-thickness", type=float, default=.10)
    select.add_argument("--max-thickness", type=float, default=.18)
    select.add_argument("--max-camber", type=float, default=.05)
    select.add_argument("--out", type=Path, default=Path("results/shortlist.json"))
    comp = sub.add_parser("compare", help="Compare existing verified polar CSVs")
    comp.add_argument("profiles", nargs="+")
    comp.add_argument("--polars", type=Path, required=True)
    comp.add_argument("--out", type=Path, default=Path("results/comparison"))
    comp.add_argument("--uiuc-zip", type=Path)
    comp.add_argument("--no-charts", action="store_true")
    xf = sub.add_parser("xfoil", help="Real polar calculations using an external XFOIL binary")
    xf.add_argument("profiles", nargs="+", help="NACA four digits or UIUC identifiers")
    xf.add_argument("--exe", type=Path, required=True)
    xf.add_argument("--uiuc-zip", type=Path)
    xf.add_argument("--reynolds", type=float, default=1000000.0)
    xf.add_argument("--mach", type=float, default=0.0)
    xf.add_argument("--ncrit", type=float, default=9.0)
    xf.add_argument("--alpha-start", type=float, default=-2.0)
    xf.add_argument("--alpha-end", type=float, default=8.0)
    xf.add_argument("--alpha-step", type=float, default=2.0)
    xf.add_argument("--iterations", type=int, default=150)
    xf.add_argument("--out", type=Path, default=Path("results/xfoil"))
    sizing = sub.add_parser("size", help="ADRpy aircraft conceptual constraints")
    sizing.add_argument("--config", type=Path, required=True)
    sizing.add_argument("--out", type=Path, default=Path("results/conceptual-sizing.json"))
    opt = sub.add_parser("optimize", help="ADRpy+SciPy conceptual T/W optimizer")
    opt.add_argument("--config", type=Path, required=True)
    opt.add_argument("--out", type=Path, default=Path("results/conceptual-optimum.json"))
    flow = sub.add_parser("flow5", help="Open official unmodified flow5 Windows application")
    flow.add_argument("--exe", type=Path, help="Path to official flow5.exe")
    sub.add_parser("status", help="Report available engine source and executable locations")
    args = parser.parse_args()
    if args.command == "generate":
        write_csv(args.code, args.out/f"naca{args.code}.csv", args.points)
        write_dat(args.code, args.out/f"naca{args.code}.dat", args.points)
        print(f"Generated NACA {args.code}: {args.out.resolve()}")
    elif args.command in ("size", "optimize"):
        from .adrpy_core import load_concept, size, optimize, export_result
        concept = load_concept(args.config)
        result = size(concept) if args.command == "size" else optimize(concept)
        export_result(result, args.out)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.command == "flow5":
        exe = args.exe
        if exe is None:
            location_file = Path(__file__).resolve().parents[1] / "runtime" / "flow5-location.txt"
            if not location_file.is_file():
                raise SystemExit("Official flow5 not installed. Run scripts/setup-engines.ps1 or supply --exe.")
            exe = Path(location_file.read_text(encoding="utf-8-sig").strip())
        if not exe.is_absolute():
            exe = Path(__file__).resolve().parents[1] / exe
        if not exe.is_file():
            raise SystemExit(f"flow5.exe not found: {exe}")
        subprocess.Popen([str(exe.resolve())], cwd=exe.resolve().parent)
        print("Official upstream flow5 started (no AeroSuite modifications).")
    elif args.command == "status":
        root = Path(__file__).resolve().parents[1]
        upstream = root / "vendor"
        print(json.dumps({"flow5_source":(upstream/"flow5"/"flow5.pro").is_file(),
                          "adrpy_source":(upstream/"ADRpy"/"ADRpy"/"constraintanalysis.py").is_file(),
                          "flow5_launch_path":(root/"runtime"/"flow5-location.txt").read_text(encoding="utf-8-sig").strip()
                          if (root/"runtime"/"flow5-location.txt").is_file() else None,
                          "xfoil":"python -m aerosuite xfoil --help",
                          "sizing":"python -m aerosuite size --help",
                          "optimization":"python -m aerosuite optimize --help"},indent=2))
    elif args.command == "xfoil":
        from .xfoil_cli import XFoilCase, load_naca_selected, load_uiuc_selected, run_profile
        case = XFoilCase(args.reynolds, args.mach, args.ncrit, args.alpha_start,
                         args.alpha_end, args.alpha_step, args.iterations)
        profiles = (load_uiuc_selected(args.uiuc_zip, args.profiles) if args.uiuc_zip
                    else load_naca_selected(args.profiles))
        results = [run_profile(args.exe, ident, foil, case, args.out)
                   for ident, foil in profiles]
        print(json.dumps(results, indent=2))
    elif args.command == "compare":
        from .batch_compare import Comparison, compare
        result = compare(Comparison(tuple(args.profiles), args.polars, args.out, args.uiuc_zip), charts=not args.no_charts)
        print(json.dumps(result, indent=2))
    else:
        req = Requirements(args.min_thickness, args.max_thickness, args.max_camber)
        result = {"analysis_type":"GEOMETRY_CONSTRAINTS_ONLY", "requirements":vars(req), "results":evaluate_naca4(args.codes,req)}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
