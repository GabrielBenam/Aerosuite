"""CLI de prototipo AeroSuite."""
import argparse
import json
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
    args = parser.parse_args()
    if args.command == "generate":
        write_csv(args.code, args.out/f"naca{args.code}.csv", args.points)
        write_dat(args.code, args.out/f"naca{args.code}.dat", args.points)
        print(f"Generated NACA {args.code}: {args.out.resolve()}")
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
