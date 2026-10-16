"""M09a Perfiles (Gudmundsson Tabla 1-4 paso 9; Sec. 8.3.9, matriz de decision para seleccion de perfil).

Nivel 2D. Cada candidato (NACA 4 digitos del generador propio, archivos Selig .dat o perfiles del ZIP UIUC que
aporta el usuario) se analiza con el XFOIL real (`xfoil_cli.run_profile`); de la polar se extraen las magnitudes
que pide la Sec. 8.3.9 y se puntuan con la matriz del libro: peor = 0, mejor = 1, el resto prorrateado
linealmente (ejemplo del libro: t/c 0.10, 0.12, 0.14, 0.16 -> 0, 0.333, 0.667, 1), L/D redondeado a entero, y
pesos por criterio opcionales. Sin ejecutable de XFOIL el modulo solo devuelve la geometria y declara
"pendiente de validacion con el motor real": nunca fabrica una polar. XFOIL es un resultado 2D (flujo
bidimensional): sustituir CL (3D) por Cl (2D) es una aproximacion del propio libro en zonas de Cl casi constante.
"""
import hashlib
import json
import math
from pathlib import Path

from . import engines
from . import project as prj
from .uiuc_library import Airfoil, parse_selig
from .xfoil_cli import XFoilCase, load_naca_selected, load_uiuc_selected, parse_polar, run_profile

REFERENCES = [
    "GUD Sec. 8.3.9 Decision Matrix for Airfoil Selection, criterios (1)-(11) y Tabla 8-13, PDF 355-361 / impr. 310-316",
    "GUD Tabla 8-12 (clases de perfil: convencional, laminar natural, supercritico, reflexado, bajo Re), PDF 356-357 / impr. 311-312",
    "GUD Sec. 8.1.4 definiciones (Cl_max, Cl_alpha, alpha_ZL, coeficiente de eficiencia Cl_max/Cd_min), PDF 305-306 / impr. 260-261",
    "XFOIL 6.99 (Drela): acoplamiento viscoso-no viscoso y transicion e^N; DRE Sec. 4.12.2 y 4.14, PDF 112-118",
]

# criterio: (direccion, descripcion). 'max' = mayor es mejor; 'min' = menor es mejor.
CRITERIA = {
    "cd_at_cruise_cl": ("min", "Cd at the cruise Cl (criterion 1, drag)"),
    "cl_at_cdmin_gap": ("min", "|Cl at Cd_min - target Cl| (criterion 1: Cd_min at the right Cl)"),
    "clmax": ("max", "Cl_max (criterion 2)"),
    "stall_cl_drop": ("min", "Cl lost 2 deg beyond Cl_max (criterion 2, gentle stall)"),
    "cm_at_cruise_cl_abs": ("min", "|Cm about c/4| at the cruise Cl (criterion 4)"),
    "thickness_ratio": ("max", "t/c (criterion 6, structural depth)"),
    "efficiency_ratio": ("max", "Cl_max / Cd_min (criterion 8)"),
    "ld_max": ("max", "(Cl/Cd)_max rounded to an integer (criterion 9)"),
    "alpha_ldmax_gap": ("min", "|alpha at (Cl/Cd)_max - alpha at cruise Cl| (criterion 9)"),
}
# Criterios del libro que M09a no puntua automaticamente (ver DECISIONS D-25): (3) contaminacion y transicion, (5) M_crit,
# (7) union ala-fuselaje. Se pueden aportar con `manual_scores`.


def geometry_stats(coords) -> dict:
    """Espesor y curvatura maximos (fraccion de cuerda) de un contorno Selig (TE superior -> LE -> TE inferior)."""
    pts = list(coords)
    i_le = min(range(len(pts)), key=lambda i: pts[i][0])
    upper = sorted(pts[: i_le + 1])
    lower = sorted(pts[i_le:])

    def interp(side, x):
        for (x0, y0), (x1, y1) in zip(side, side[1:]):
            if x0 <= x <= x1 and x1 > x0:
                return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        return None
    best_t, best_c, x_t, x_c = 0.0, 0.0, 0.0, 0.0
    for k in range(1, 200):
        x = k / 200.0
        yu, yl = interp(upper, x), interp(lower, x)
        if yu is None or yl is None:
            continue
        if yu - yl > best_t:
            best_t, x_t = yu - yl, x
        if abs((yu + yl) / 2.0) > abs(best_c):
            best_c, x_c = (yu + yl) / 2.0, x
    return {"thickness_ratio": best_t, "thickness_position": x_t, "camber_ratio": best_c, "camber_position": x_c}


def _interp(xs, ys, x):
    for (x0, y0), (x1, y1) in zip(zip(xs, ys), zip(xs[1:], ys[1:])):
        if min(x0, x1) <= x <= max(x0, x1) and x0 != x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return None


def polar_metrics(rows: list[dict], cl_cruise: float, cl_target_mind: float | None = None,
                  fit_cl_range=(0.1, 0.9)) -> dict:
    """Magnitudes de la Sec. 8.3.9 desde una polar real de XFOIL (filas alpha, cl, cd, cm). Lo que la polar no permite
    calcular (p. ej. caida tras la perdida si el barrido no la alcanza) se devuelve como None."""
    if len(rows) < 3:
        raise ValueError("polar has fewer than 3 converged points")
    rows = sorted(rows, key=lambda r: r["alpha"])
    k_max = max(range(len(rows)), key=lambda i: rows[i]["cl"])
    clmax, a_clmax = rows[k_max]["cl"], rows[k_max]["alpha"]
    pre = rows[: k_max + 1]                      # rama ascendente (Cl crece con alpha)
    k_cd = min(range(len(rows)), key=lambda i: rows[i]["cd"])
    ld = [r["cl"] / r["cd"] for r in rows]
    k_ld = max(range(len(rows)), key=lambda i: ld[i])
    # pendiente y alpha_ZL: ajuste lineal de la zona fit_cl_range de la rama ascendente (dato del analisis, no del libro)
    lin = [r for r in pre if fit_cl_range[0] <= r["cl"] <= fit_cl_range[1]]
    cl_alpha = a_zl = None
    if len(lin) >= 3:
        xs, ys = [r["alpha"] for r in lin], [r["cl"] for r in lin]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        sxx = sum((x - mx) ** 2 for x in xs)
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
        cl_alpha, a_zl = math.degrees(slope), mx - my / slope   # por radian; alpha_ZL en grados
    cls, alphas = [r["cl"] for r in pre], [r["alpha"] for r in pre]
    a_cruise = _interp(cls, alphas, cl_cruise)
    cd_cruise = _interp(cls, [r["cd"] for r in pre], cl_cruise)
    cm_cruise = _interp(cls, [r["cm"] for r in pre], cl_cruise)
    drop = None
    after = _interp([r["alpha"] for r in rows], [r["cl"] for r in rows], a_clmax + 2.0) if a_clmax + 2.0 <= rows[-1]["alpha"] else None
    if after is not None:
        drop = clmax - after
    target = cl_cruise if cl_target_mind is None else cl_target_mind
    return {"clmax": clmax, "alpha_clmax_deg": a_clmax, "stall_reached_in_sweep": k_max < len(rows) - 1,
            "stall_cl_drop": drop, "cd_min": rows[k_cd]["cd"], "cl_at_cdmin": rows[k_cd]["cl"],
            "cl_at_cdmin_gap": abs(rows[k_cd]["cl"] - target), "efficiency_ratio": clmax / rows[k_cd]["cd"],
            "ld_max": float(round(ld[k_ld])), "ld_max_unrounded": ld[k_ld], "alpha_ldmax_deg": rows[k_ld]["alpha"],
            "cl_alpha_per_rad": cl_alpha, "alpha_zero_lift_deg": a_zl, "alpha_cruise_deg": a_cruise,
            "cd_at_cruise_cl": cd_cruise, "cm_at_cruise_cl": cm_cruise,
            "cm_at_cruise_cl_abs": None if cm_cruise is None else abs(cm_cruise),
            "alpha_ldmax_gap": None if a_cruise is None else abs(rows[k_ld]["alpha"] - a_cruise),
            "cl_alpha_fit_window_cl": list(fit_cl_range), "points": len(rows)}


def score_matrix(table: dict, weights: dict | None = None, manual: dict | None = None) -> dict:
    """Matriz de decision de la Sec. 8.3.9. table: {perfil: {criterio: valor|None}}.

    Para cada criterio: peor = 0, mejor = 1, prorrateo lineal entre ambos (si todos son iguales, todos 1).
    Un criterio sin dato para algun perfil se excluye de la matriz y se informa. `manual`: {perfil: {criterio: puntos}}
    para criterios cualitativos del libro (contaminacion, M_crit, union ala-fuselaje), sumados tal cual."""
    weights = weights or {}
    names = list(table)
    used, dropped = [], {}
    for crit, (direction, _desc) in CRITERIA.items():
        if weights.get(crit, 1.0) == 0.0:
            continue
        values = {n: table[n].get(crit) for n in names}
        missing = [n for n, v in values.items() if v is None]
        if missing:
            dropped[crit] = missing
        else:
            used.append(crit)
    scores = {n: {} for n in names}
    for crit in used:
        direction = CRITERIA[crit][0]
        vals = [table[n][crit] for n in names]
        lo, hi = min(vals), max(vals)
        for n in names:
            v = table[n][crit]
            if hi == lo:
                s = 1.0
            else:
                s = (v - lo) / (hi - lo) if direction == "max" else (hi - v) / (hi - lo)
            scores[n][crit] = s * weights.get(crit, 1.0)
    totals = {}
    for n in names:
        extra = dict((manual or {}).get(n, {}))
        scores[n].update({f"manual:{k}": v for k, v in extra.items()})
        totals[n] = sum(scores[n].values())
    ranking = sorted(names, key=lambda n: -totals[n])
    best = totals[ranking[0]] if ranking else None
    second = totals[ranking[1]] if len(ranking) > 1 else None
    return {"criteria_used": used, "criteria_dropped_missing_data": dropped, "weights": {c: weights.get(c, 1.0) for c in used},
            "scores": scores, "totals": totals, "ranking": ranking,
            "margin_first_second": None if second is None else best - second,
            "note": "the highest score is the airfoil to consider; the result may be ambiguous when the margin is small (GUD Sec. 8.3.9)"}


def _candidates(d: dict) -> list[tuple[str, Airfoil]]:
    c = d["candidates"]
    out = []
    if c.get("naca4"):
        out += load_naca_selected(list(c["naca4"]))
    for path in c.get("dat_files", []):
        p = Path(path)
        out.append((p.stem.lower(), parse_selig(p.read_text(encoding="utf-8-sig", errors="replace"), p.name)))
    if c.get("uiuc"):
        out += load_uiuc_selected(Path(c["uiuc"]["archive"]), list(c["uiuc"]["names"]))
    if not out:
        raise SystemExit("inputs.m09a.candidates is empty (naca4, dat_files or uiuc)")
    ids = [i for i, _ in out]
    if len(set(ids)) != len(ids):
        raise SystemExit("inputs.m09a.candidates has duplicate identifiers")
    return out


def _case(cond: dict) -> XFoilCase:
    keys = ("reynolds", "mach", "ncrit", "alpha_start", "alpha_end", "alpha_step", "iterations", "xtr_top", "xtr_bottom",
            "from_zero")
    return XFoilCase(**{k: cond[k] for k in keys if k in cond})


def _load_or_run(exe: Path, ident: str, foil: Airfoil, case: XFoilCase, out: Path, timeout: int) -> dict:
    """Reutiliza una corrida real previa de XFOIL si sus condiciones y geometria coinciden; si no, ejecuta."""
    meta_path, csv_path = out / f"{ident}.json", out / f"{ident}.csv"
    dat = ("AeroSuite\n" + "".join(f"{x:.9f} {y:.9f}\n" for x, y in foil.coordinates)).encode("ascii")
    if meta_path.exists() and csv_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        same = (meta.get("geometry_sha256") == hashlib.sha256(dat).hexdigest()
                and all(meta.get(k) == getattr(case, k) for k in ("reynolds", "mach", "ncrit", "alpha_start", "alpha_end",
                                                                  "alpha_step", "xtr_top", "xtr_bottom")))
        if not same:
            raise SystemExit(f"{out} already has a different XFOIL run for {ident}: use another inputs.m09a.out_dir")
        meta["reused_run"] = True
    else:
        meta = run_profile(exe, ident, foil, case, out, timeout)
        meta["reused_run"] = False
    import csv
    with csv_path.open(encoding="utf-8") as f:
        rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]
    return {"meta": meta, "rows": rows}


def evaluate(project: dict) -> dict:
    d = prj.need_inputs(project, "m09a", ["candidates", "conditions", "targets"])
    cands = _candidates(d)
    case = _case(d["conditions"])
    case.validate()
    tg = d["targets"]
    if "cl_cruise" not in tg:
        raise SystemExit("inputs.m09a.targets.cl_cruise is required")
    geo = {i: geometry_stats(f.coordinates) for i, f in cands}
    exe = engines.xfoil_executable(Path(d["xfoil"]) if d.get("xfoil") else None)
    result = {"level": "2D", "airfoil_class": d.get("airfoil_class"), "conditions": d["conditions"], "targets": tg,
              "geometry": geo}
    if exe is None:
        result.update({"status": "pending_engine",
                       "note": "XFOIL executable not found: polars NOT computed. Pendiente de validacion con el motor real "
                               "(set AEROSUITE_XFOIL or run scripts/setup-engines.ps1). No aerodynamic data is presented."})
        return result
    out = Path(d.get("out_dir", "results/m09a_xfoil"))
    runs, table, failures = {}, {}, {}
    for ident, foil in cands:
        try:
            r = _load_or_run(exe, ident, foil, case, out, int(d.get("timeout_s", 180)))
        except (RuntimeError, ValueError) as exc:
            failures[ident] = str(exc)
            continue
        met = polar_metrics(r["rows"], tg["cl_cruise"], tg.get("cl_min_drag_target"))
        met["thickness_ratio"] = geo[ident]["thickness_ratio"]
        table[ident] = met
        runs[ident] = {k: r["meta"].get(k) for k in ("solver", "solver_sha256", "geometry_sha256", "converged", "missing_alpha",
                                                     "points_requested", "points_returned", "reused_run", "note")}
    result.update({"status": "computed", "solver": {"executable": str(exe)}, "xfoil_runs": runs, "failures": failures,
                   "metrics": table})
    if len(table) >= 2:
        result["decision_matrix"] = score_matrix(table, d.get("weights"), d.get("manual_scores"))
    elif table:
        result["decision_matrix"] = None
        result["note"] = "a decision matrix needs at least two candidates with converged polars"
    result["incomplete_sweeps"] = [i for i, r in runs.items() if not r["converged"]]
    return result


def run(project: dict) -> dict:
    result = evaluate(project)
    prj.record(project, "m09a", result, "2D", REFERENCES)
    return result
