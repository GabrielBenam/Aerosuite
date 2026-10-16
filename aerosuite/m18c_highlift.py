"""M18c Hipersustentacion y flaps (Gudmundsson Tabla 1-4 paso 18; Cap. 10, Secs. 10.3 y 10.4).

Nivel conceptual (2D con XFOIL para la seccion; 3D por el metodo de particion del ala del libro). El incremento de C_lmax de la seccion
sale de (a) datos de ensayo de la Tabla 10-5 prorrateados por cuerda y deflexion (Ejemplo 10-2: C_lmax = C_lmax,b + k dC_lmax
(c_f/c)/(c_f,tabla/c) (delta/delta_tabla)), (b) la correlacion del flap simple, Ec. 10-1, o (c) XFOIL real con la deflexion aplicada
a la geometria (GDES/FLAP). El ala se divide en segmentos (Sec. 10.4.2) y C_Lmax = 0.9 [sum C_lmax,i S_i cos(Lambda_h) (segmentos con flap)
+ sum C_l,i S_i (sin flap, a la incidencia de perdida del flap)] / S (Ec. 10-2), con las dos mitades del ala. Compara con el C_Lmax
exigido por despegue y aterrizaje (datos o M04). XFOIL no predice C_lmax de elementos multiples con fiabilidad: el resultado se rotula
como 2D de XFOIL y, si el barrido termina sin pico de C_l, como cota inferior. Los incrementos de la Tabla 10-5 son datos de entrada
(la tabla esta en imagenes); dispositivos de borde de ataque y compensacion de momento (Ec. 10-3) solo como dato. SI interno."""
import math
import subprocess
import tempfile
from pathlib import Path

from . import project as prj
from .airfoils import naca4
from .engines import xfoil_executable
from .xfoil_cli import parse_polar

REFERENCES = [
    "GUD Sec. 10.3.2 y Ec. 10-1 (flap simple: C_lmax en funcion de c_f/c = 0.1, 0.2 y delta_f), PDF 486-487",
    "GUD Sec. 10.3.9 (1)-(3) y Ejemplo 10-2 (prorrateo de dC_lmax de la Tabla 10-5; resultado 3.01), PDF 500-501",
    "GUD Sec. 10.4.2, Ecs. 10-2 y 10-3 (metodo de particion del ala) y Ejemplo 10-3 (SR22: C_Lmax = 1.936 frente a 1.99 del POH), PDF 503-505",
    "GUD Sec. 8.1 (Ecs. 8-11 y 8-12: C_l = C_l0 + C_l_alpha alpha, usadas en el Ejemplo 10-3 para los segmentos sin flap)",
    "XFOIL 6.99, comando GDES/FLAP (Drela): flap de charnela articulada aplicado a la geometria del perfil",
]
PLAIN_FLAP_CLMAX = {0.1: (1.262, 0.01492, -8.315e-5), 0.2: (1.234, 0.02216, -1.611e-4)}   # Ec. 10-1
HINGE_SWEEP_NOTE = "cos(Lambda_hingeline) penaliza la deflexion en estrechamiento/flecha (Sec. 10.4.2)"
KT = 0.514444


def plain_flap_clmax(cf_over_c: float, delta_deg: float) -> float:
    """Ec. 10-1 (ajuste por minimos cuadrados, c_f/c = 0.1 o 0.2; los signos de los terminos cuadraticos se reconstruyen como negativos)."""
    for key, (a, b, c) in PLAIN_FLAP_CLMAX.items():
        if abs(cf_over_c - key) < 1e-9:
            return a + b * delta_deg + c * delta_deg ** 2
    raise ValueError("Eq. 10-1 only covers c_f/c = 0.1 and 0.2")


def prorate_clmax(clmax_base: float, d_clmax_table: float, cf_over_c: float, cf_over_c_table: float, delta_deg: float,
                  delta_deg_table: float, factor: float = 1.0) -> float:
    """Ejemplo 10-2: C_lmax = C_lmax,b + factor dC_lmax (cf/c)/(cf/c)_tabla (delta/delta_tabla); `factor` es la correccion
    por Reynolds/aproximacion elegida por el disenador (0.90 en el ejemplo, por Re = 6 M frente a 9 M del ensayo)."""
    return clmax_base + factor * d_clmax_table * (cf_over_c / cf_over_c_table) * (delta_deg / delta_deg_table)


def wing_partition_clmax(segments, s_ref: float, k3d: float = 0.9) -> float:
    """Ec. 10-2 (una semi-ala por segmento; el factor 2 cuenta las dos mitades): C_Lmax = k3d * 2 * [sum S_i * c_i] / S, con
    c_i = C_lmax,i cos(Lambda_h,i) en segmentos con flap y c_i = C_l,i (a la incidencia de perdida del flap) en los demas."""
    total = 0.0
    for s in segments:
        if s["flapped"]:
            total += s["clmax_i"] * s["area_m2"] * math.cos(math.radians(s.get("hinge_sweep_deg", 0.0)))
        else:
            total += s["cl_unflapped_at_stall"] * s["area_m2"]
    return k3d * 2.0 * total / s_ref


def segment_geometry(span: float, root_chord: float, tip_chord: float, y_in: float, y_out: float) -> dict:
    """Segmento trapezoidal entre fracciones de semienvergadura (cuerda lineal): area de una semi-ala y cuerdas extremas."""
    half = span / 2.0
    c = lambda f: root_chord + (tip_chord - root_chord) * f
    return {"area_m2": 0.5 * (c(y_in) + c(y_out)) * (y_out - y_in) * half, "chord_in_m": c(y_in), "chord_out_m": c(y_out)}


def xfoil_flapped_section(exe: Path, coords, cf_over_c: float, delta_deg: float, reynolds: float, alpha_start: float,
                          alpha_end: float, alpha_step: float, ncrit: float = 9.0, timeout: int = 240) -> dict:
    """XFOIL real con el flap aplicado por GDES/FLAP (charnela en x/c = 1 - cf/c, a media espesor; deflexion positiva hacia abajo).
    Devuelve las filas convergidas, C_lmax (maximo de la polar) y si el barrido llego a un pico (stall_captured)."""
    with tempfile.TemporaryDirectory(prefix="aerosuite-xfoil-flap-") as tmp:
        work = Path(tmp)
        (work / "foil.dat").write_text("AeroSuite\n" + "".join(f"{x:.9f} {y:.9f}\n" for x, y in coords), encoding="ascii")
        lines = ["PLOP", "G", "", "LOAD foil.dat"]
        if abs(delta_deg) > 0.0:
            lines += ["GDES", "FLAP", f"{1.0 - cf_over_c:.6f}", "999", "0.5", f"{delta_deg:.6f}", "EXEC", ""]
        lines += ["PANE", "OPER", f"VISC {reynolds:.12g}", "VPAR", f"N {ncrit:.12g}", "", "ITER 300", "PACC", "polar.txt", "",
                  f"ASEQ {alpha_start:.12g} {alpha_end:.12g} {alpha_step:.12g}", "PACC", "", "", "QUIT", ""]
        proc = subprocess.run([str(exe.resolve())], input="\n".join(lines), cwd=work, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout, errors="replace")
        polar = work / "polar.txt"
        if not polar.is_file():
            raise RuntimeError("XFOIL produced no polar file for the flapped section")
        rows = parse_polar(polar.read_text(encoding="utf-8", errors="replace"))
        log = proc.stdout or ""
    if not rows:
        raise RuntimeError("XFOIL produced no converged point for the flapped section")
    top = max(rows, key=lambda r: r["cl"])
    return {"rows": rows, "clmax": top["cl"], "alpha_at_clmax": top["alpha"], "stall_captured": top is not rows[-1],
            "return_code": proc.returncode, "log_tail": log[-400:]}


def alpha0l_from_rows(rows) -> float:
    """alpha de C_l = 0 por interpolacion lineal entre los dos puntos que lo encierran."""
    for a, b in zip(rows, rows[1:]):
        if a["cl"] <= 0.0 <= b["cl"] and b["cl"] != a["cl"]:
            return a["alpha"] + (b["alpha"] - a["alpha"]) * (0.0 - a["cl"]) / (b["cl"] - a["cl"])
    return None


# --------------------------------------------------------------------------- modulo
def _section_clmax(cfg, base_clmax, sec, xfoil_ctx):
    """Incremento y C_lmax de la seccion con flap segun la fuente declarada en la configuracion `cfg` (cf_over_c, delta_deg, source...)."""
    src = cfg["source"]
    if src == "table_10_5":
        t = cfg["table"]
        clmax = prorate_clmax(base_clmax, t["d_clmax"], cfg["cf_over_c"], t["cf_over_c"], cfg["delta_deg"], t["delta_deg"], cfg.get("factor", 1.0))
        return {"source": "Table 10-5 prorated (Example 10-2)", "clmax": clmax, "d_clmax": clmax - base_clmax,
                "reference": t.get("reference", "user input from Table 10-5")}
    if src == "plain_flap_eq_10_1":
        clmax = plain_flap_clmax(cfg["cf_over_c"], cfg["delta_deg"])
        return {"source": "Eq. 10-1 (plain flap)", "clmax": clmax, "d_clmax": clmax - base_clmax,
                "note": "Eq. 10-1 is a fit to three specific airfoils, not to this one: indicative only"}
    if src == "direct":
        return {"source": "direct user input", "clmax": base_clmax + cfg["d_clmax"], "d_clmax": cfg["d_clmax"], "reference": cfg.get("reference", "user input")}
    if src == "xfoil":
        exe, coords, x, clean = xfoil_ctx
        if exe is None:
            raise SystemExit("flap source 'xfoil' needs an XFOIL executable (AEROSUITE_XFOIL or tools/xfoil)")
        r = xfoil_flapped_section(exe, coords, cfg["cf_over_c"], cfg["delta_deg"], x["reynolds"], x.get("alpha_start", -4.0),
                                  x.get("alpha_end", 20.0), x.get("alpha_step", 1.0), x.get("ncrit", 9.0))
        out = {"source": "XFOIL 2D (GDES/FLAP), viscous", "clmax": r["clmax"], "d_clmax": r["clmax"] - clean["clmax"],
               "alpha_at_clmax_deg": r["alpha_at_clmax"], "stall_captured": r["stall_captured"], "alpha0l_deg": alpha0l_from_rows(r["rows"]),
               "points": len(r["rows"]), "polar": r["rows"], "caution": "XFOIL does not model slot flow or massive separation: indicator, not a certification value"}
        if not r["stall_captured"]:
            out["note"] = "the sweep ended without a C_l peak: C_lmax is a lower bound of the XFOIL value"
        return out
    raise SystemExit(f"unknown flap source '{src}'")


def evaluate(project: dict) -> tuple[dict, list]:
    d = prj.need_inputs(project, "m18c", ["segments", "configurations", "section"])
    w = project["outputs"].get("m09b")
    if not w:
        raise SystemExit("outputs.m09b is missing: run m09b first")
    pf = w["result"]["planform"]
    s_ref = pf["area_m2"]
    sec = d["section"]
    res = {"level": "conceptual (3D wing partition method; 2D flap increments as declared per source)", "units": "SI", "assumptions": [],
           "configurations": {}}
    xfoil_ctx = None
    if any(c["source"] == "xfoil" for c in d["configurations"].values()):
        x = sec.get("xfoil")
        if not x or "naca" not in x:
            raise SystemExit("inputs.m18c.section.xfoil {naca, reynolds, ...} is required for the 'xfoil' source")
        exe = xfoil_executable()
        coords = naca4(x["naca"])
        clean = xfoil_flapped_section(exe, coords, 0.3, 0.0, x["reynolds"], x.get("alpha_start", -4.0), x.get("alpha_end", 20.0),
                                      x.get("alpha_step", 1.0), x.get("ncrit", 9.0)) if exe else None
        xfoil_ctx = (exe, coords, x, clean)
        if clean:
            res["xfoil_clean_section"] = {"naca": x["naca"], "reynolds": x["reynolds"], "clmax": clean["clmax"],
                                          "alpha_at_clmax_deg": clean["alpha_at_clmax"], "stall_captured": clean["stall_captured"],
                                          "polar": clean["rows"]}
    for name, cfg in d["configurations"].items():
        segs = []
        for i, sg in enumerate(d["segments"]):
            geo = segment_geometry(pf["span_m"], pf["root_chord_m"], pf["tip_chord_m"], sg["y_in"], sg["y_out"])
            cl_in = sec["clmax_root"] + (sec["clmax_tip"] - sec["clmax_root"]) * sg["y_in"]
            cl_out = sec["clmax_root"] + (sec["clmax_tip"] - sec["clmax_root"]) * sg["y_out"]
            base = 0.5 * (cl_in + cl_out)
            e = {"id": sg.get("id", f"segment {i + 1}"), "y_in": sg["y_in"], "y_out": sg["y_out"], **geo, "clmax_clean": base, "flapped": bool(sg.get("flap"))}
            if sg.get("flap"):
                sr = _section_clmax({**cfg, "cf_over_c": sg["flap"]["cf_over_c"]}, base, sec, xfoil_ctx)
                e.update({"clmax_i": sr["clmax"], "section": sr, "hinge_sweep_deg": sg["flap"].get("hinge_sweep_deg", 0.0)})
            else:
                a_stall = d.get("alpha_stall_flapped_deg", {}).get(name)
                if a_stall is not None and "cl_alpha_per_deg" in sec and "alpha_zl_deg" in sec:
                    e["cl_unflapped_at_stall"] = min(base, sec["cl_alpha_per_deg"] * (a_stall - sec["alpha_zl_deg"]))      # Eqs. 8-11/8-12
                else:
                    e["cl_unflapped_at_stall"] = base
                    res["assumptions"].append(f"{name}/{e['id']}: unflapped segment contributes its C_lmax, which is optimistic; give "
                                              f"alpha_stall_flapped_deg.{name}, section.cl_alpha_per_deg and section.alpha_zl_deg")
            segs.append(e)
        cl_max = wing_partition_clmax(segs, s_ref)
        clean = wing_partition_clmax([{**s, "flapped": False, "cl_unflapped_at_stall": s["clmax_clean"]} for s in segs], s_ref)
        res["configurations"][name] = {"segments": segs, "cl_max_wing": cl_max, "cl_max_wing_clean_same_method": clean, "delta_cl_max": cl_max - clean,
                                       "sref_m2": s_ref, "area_covered_pct": 100.0 * 2.0 * sum(s["area_m2"] for s in segs) / s_ref}
    req = dict(d.get("required", {}))
    m4 = project["inputs"].get("m04", {}).get("landing", {}).get("clmax_land")
    if m4 and "landing" not in req:
        req["landing"] = m4
        res["assumptions"].append("required landing C_Lmax taken from inputs.m04.landing.clmax_land")
    res["requirements"] = {k: {"required_cl_max": v, "available": res["configurations"][k]["cl_max_wing"],
                               "ok": res["configurations"][k]["cl_max_wing"] >= v} for k, v in req.items() if k in res["configurations"]}
    return res, ["m09b"]


def run(project: dict) -> dict:
    result, depends = evaluate(project)
    prj.record(project, "m18c", result, "conceptual", REFERENCES, sorted(set(depends)))
    return result
