"""M25 Envolvente V-n (Gudmundsson Tabla 1-4 paso 25; Sec. 17.4 y 17.4.1; 14 CFR 23 §23.333-§23.341 anterior a la Enmienda 23-64 tal como los reproduce el libro).

Nivel conceptual (potencial lineal, ala rigida, sin carga de cola). Velocidades equivalentes (EAS) internas en m/s; salidas tambien en KEAS.
Maniobra: n+ = 2.1 + 24000/(W + 10000) con W en lbf y tope de la categoria (normal 3.8, utilitaria 4.4, acrobatica 6.0; M01), n- = -0.4 n+ (-0.5 n+ acrobatica),
V_S+/- = sqrt(2 W/(rho0 S CL_max/min)), V_A = V_S+ sqrt(n+), V_G = V_S- sqrt(|n-|). Cargas de rafaga (Sec. 17.4.1, Pasos 7 y 8):
mu_g = 2 (W/S)/(rho c CL_alpha g), K_g = 0.88 mu_g/(5.3 + mu_g), n_g = 1 +- K_g rho0 U_de V CL_alpha/(2 W/S) con U_de = 50 ft/s a V_C y 25 ft/s a V_D
(reducidas linealmente por encima de 20 000 ft hasta 25 y 12.5 ft/s a 50 000 ft; commuter: 66 ft/s a V_B). El contorno es el exterior de la union de la
envolvente de maniobra y la de rafaga, con la linea de perdida como limite (nuevo V_A = interseccion de la linea de perdida con la linea de rafaga, Paso 10).
Carga ultima = 1.5 x limite (14 CFR §23.2230(b), vigente). Los umbrales numericos de §23.333-§23.341, §23.335 (V_C y V_D minimas) no existen en el Part 23 vigente: se
toman del libro (n+, V_Cmin = 33 sqrt(W/S), V_D = 1.4 V_Cmin, 50/25 ft/s, K_g) y, para lo que el libro no da, de ADRpy 0.2.6 (CS-23.335: interpolaciones 33 -> 28.6 de V_C/sqrt(W/S)
y factores de V_D, 20-100 lbf/ft^2; utilitaria 4.4; acrobatica 6.0 y -0.5 n+), marcados como `fuente: ADRpy` en `assumptions`. Con flaps solo se da la linea de perdida: V_F y n con
flaps (§23.345) no se evaluan (texto no leido); se aceptan como datos. SI interno."""
from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq

from . import project as prj
from .m20_drag import isa

REFERENCES = [
    "GUD Sec. 17.4 (The Structural Envelope), 17.4.1 (Step-by-Step: Create a V-n Diagram) y Tabla 17-6, PDF 815-823 (+-1; impr. = PDF - 46); Ecs. 17-35 a 17-47",
    "14 CFR §23.333-§23.341 y §23.2215/§23.2230 (eCFR vigente leido el 2026-10-16: §23.2230(b) carga ultima = 1.5 x limite; §23.2215(a)-(b) rafagas y maniobras sin valores numericos)",
    "ADRpy 0.2.6 `airworthiness.CertificationSpecifications` (CS-23.333/335/337/341): implementacion independiente usada en el contraste",
    "M01 (Tabla 1-3: n+ maximo por categoria)",
]
G = 9.80665
RHO0 = 1.225
KT = 0.514444
FT = 0.3048
LBF = 4.4482216152605
PSF = LBF / FT ** 2          # lbf/ft^2 -> Pa
SLUG_FT3 = 515.378818        # slug/ft^3 -> kg/m^3 (the book uses 0.002378 slug/ft^3)
CATEGORIES = ("normal", "utility", "aerobatic", "commuter")
N_CAP = {"normal": 3.8, "utility": 4.4, "aerobatic": 6.0, "commuter": 3.8}
RHO0_BOOK = 0.002378 * SLUG_FT3


def keas(v_mps: float) -> float:
    return v_mps / KT


def limit_load_factors(category: str, w_lbf: float, n_plus: float | None = None) -> dict:
    """n+ (§23.337(a) anterior, Sec. 17.4.1 Paso 1) y n-: la formula 2.1 + 24000/(W + 10000) es el minimo; el libro adopta el tope de la categoria cuando la formula lo excede."""
    formula = 2.1 + 24000.0 / (w_lbf + 10000.0)
    if n_plus is not None:
        npos, origin = n_plus, "dato del usuario"
    elif category in ("normal", "commuter"):
        npos, origin = min(N_CAP[category], formula), "min(3.8, 2.1 + 24000/(W + 10000)) (libro, Paso 1)"
    else:
        npos, origin = N_CAP[category], "tope de la categoria (M01 / ADRpy CS-23.337)"
    nneg = -(0.5 if category == "aerobatic" else 0.4) * npos
    return {"n_plus": npos, "n_minus": nneg, "n_plus_formula": formula, "origin": origin}


def design_speeds(category: str, w_pa: float, v_s_pos: float, v_s_neg: float, n_plus: float, n_minus: float, v_h: float | None,
                  v_c: float | None, v_d: float | None) -> dict:
    """V_C minima/maxima, V_C, V_D, V_A, V_G (EAS m/s). W/S en Pa."""
    ws = w_pa / PSF                                                    # lbf/ft^2
    k_c = float(np.interp(ws, [20, 100], [36.0 if category == "aerobatic" else 33.0, 28.6]))
    vc_min = k_c * math.sqrt(ws) * KT
    vc_max = 0.9 * v_h if v_h else None
    if v_c is None:
        v_c, v_c_origin = vc_min, "V_Cmin (no se dio V_C)"
    else:
        v_c_origin = "dato del usuario"
    fd = {"normal": (1.4, 1.35), "commuter": (1.4, 1.35), "utility": (1.5, 1.35), "aerobatic": (1.55, 1.35)}[category]
    kd = float(np.interp(ws, [20, 100], list(fd)))
    vd_min = max(1.25 * v_c, kd * vc_min)
    return {"v_c_min_mps": vc_min, "v_c_max_mps": vc_max, "v_c_mps": v_c, "v_c_origin": v_c_origin, "v_d_min_mps": vd_min,
            "v_d_mps": v_d if v_d else vd_min, "v_d_origin": "dato del usuario" if v_d else "max(1.25 V_C, factor V_Cmin)",
            "v_a_mps": v_s_pos * math.sqrt(n_plus), "v_g_mps": v_s_neg * math.sqrt(abs(n_minus)),
            "k_vc": k_c, "k_vd": kd, "complies": {"v_c_ge_v_cmin": v_c >= vc_min - 1e-9, "v_d_ge_v_dmin": (v_d if v_d else vd_min) >= vd_min - 1e-9,
                                                 "v_c_le_0.9_vh": None if vc_max is None else v_c <= vc_max + 1e-9,
                                                 "v_a_le_v_c": v_s_pos * math.sqrt(n_plus) <= v_c + 1e-9}}


def gust_velocities_mps(altitude_m: float, category: str) -> dict:
    """U_de a V_C y V_D (50 y 25 ft/s hasta 20 000 ft, reduccion lineal a 25 y 12.5 ft/s a 50 000 ft) y a V_B (commuter, 66 ft/s -> 38 ft/s)."""
    h = altitude_m / FT
    f = 0.0 if h <= 20000 else min(1.0, (h - 20000) / 30000.0)
    uc, ud = (50.0 - 25.0 * f), (25.0 - 12.5 * f)
    ub = 66.0 - 28.0 * f
    return {"u_c_mps": uc * FT, "u_d_mps": ud * FT, "u_b_mps": ub * FT if category == "commuter" else None}


def gust_factor(w_pa: float, rho: float, c_mgc: float, cl_alpha: float) -> dict:
    mu = 2.0 * w_pa / (rho * c_mgc * cl_alpha * G)
    return {"mu_g": mu, "k_g": 0.88 * mu / (5.3 + mu)}


def build(case: dict) -> dict:
    """Envolvente de un caso. case: mass_kg, s_m2, cl_max, cl_min (<0 o magnitud), cl_alpha, c_mgc_m, category, altitude_m, v_h_mps, v_c_mps, v_d_mps,
    n_plus, v_s_pos_mps/v_s_neg_mps (opcional, sustituyen al calculo), rho_kgm3 (EAS: densidad del nivel del mar; el libro usa 0.002378 slug/ft^3)."""
    cat = case.get("category", "normal")
    if cat not in CATEGORIES:
        raise SystemExit(f"category must be one of {CATEGORIES}")
    rho0 = case.get("rho0_kgm3", RHO0)
    w_n = case["mass_kg"] * G
    s = case["s_m2"]
    w_pa = w_n / s
    clmax, clmin = abs(case["cl_max"]), abs(case["cl_min"])
    cla, cm = case["cl_alpha"], case["c_mgc_m"]
    ll = limit_load_factors(cat, w_n / LBF, case.get("n_plus"))
    npos, nneg = ll["n_plus"], ll["n_minus"]
    vs_pos = case.get("v_s_pos_mps") or math.sqrt(2.0 * w_pa / (rho0 * clmax))
    vs_neg = case.get("v_s_neg_mps") or math.sqrt(2.0 * w_pa / (rho0 * clmin))
    sp = design_speeds(cat, w_pa, vs_pos, vs_neg, npos, nneg, case.get("v_h_mps"), case.get("v_c_mps"), case.get("v_d_mps"))
    vc, vd, va0, vg0 = sp["v_c_mps"], sp["v_d_mps"], sp["v_a_mps"], sp["v_g_mps"]
    alt = case.get("altitude_m", 0.0)
    rho_alt = isa(alt)["rho"]
    gu = gust_velocities_mps(alt, cat)
    gf = gust_factor(w_pa, case.get("rho_gust_kgm3", rho_alt if alt else rho0), cm, cla)
    kg = gf["k_g"]
    slope = lambda u: kg * rho0 * u * cla / (2.0 * w_pa)          # dn/dV (1/(m/s))
    s_c, s_d = slope(gu["u_c_mps"]), slope(gu["u_d_mps"])
    gust = {**gf, **gu, "n_c_plus": 1 + s_c * vc, "n_c_minus": 1 - s_c * vc, "n_d_plus": 1 + s_d * vd, "n_d_minus": 1 - s_d * vd}
    pts_up, pts_lo = [(0.0, 1.0), (vc, gust["n_c_plus"]), (vd, gust["n_d_plus"])], [(0.0, 1.0), (vc, gust["n_c_minus"]), (vd, gust["n_d_minus"])]
    if gu["u_b_mps"]:
        sb = slope(gu["u_b_mps"])
        vb = brentq(lambda v: 0.5 * rho0 * v * v * clmax / w_pa - 1 - sb * v, 1e-3, 3 * vd)
        gust.update({"v_b_mps": vb, "n_b_plus": 1 + sb * vb})
        pts_up = [(0.0, 1.0), (vb, 1 + sb * vb), (vc, gust["n_c_plus"]), (vd, gust["n_d_plus"])]
        pts_lo = [(0.0, 1.0), (vb, 1 - sb * vb), (vc, gust["n_c_minus"]), (vd, gust["n_d_minus"])]
    gu_line = lambda v: float(np.interp(v, *zip(*pts_up)))
    gl_line = lambda v: float(np.interp(v, *zip(*pts_lo)))
    st_pos = lambda v: 0.5 * rho0 * v * v * clmax / w_pa
    st_neg = lambda v: -0.5 * rho0 * v * v * clmin / w_pa

    def man_up(v):
        return min(st_pos(v), npos)

    def man_lo(v):
        if v <= vc:
            return max(st_neg(v), nneg)
        return nneg * (vd - v) / (vd - vc) if vd > vc else 0.0

    upper = lambda v: max(man_up(v), min(st_pos(v), gu_line(v)))
    lower = lambda v: min(man_lo(v), max(st_neg(v), gl_line(v)))
    # nuevos V_A / V_G: interseccion de la linea de perdida con la linea de rafaga (Paso 10, Ec. 17-45/17-47) si el gusto la supera
    out_speeds = {**{k: sp[k] for k in sp}, "v_s_pos_mps": vs_pos, "v_s_neg_mps": vs_neg}
    a_eff = va0
    if gu_line(va0) > st_pos(va0) + 1e-12 and st_pos(vc) > gu_line(vc):
        a_eff = brentq(lambda v: st_pos(v) - gu_line(v), va0, vc)       # Step 10: the gust line is above V_A, so the stall line is extended to it
    out_speeds["v_a_effective_mps"] = a_eff
    g_eff = vg0
    if gl_line(vg0) < st_neg(vg0) - 1e-12 and st_neg(vc) < gl_line(vc):
        g_eff = brentq(lambda v: st_neg(v) - gl_line(v), vg0, vc)
    out_speeds["v_g_effective_mps"] = g_eff
    vgrid = np.unique(np.concatenate([np.linspace(0.0, vd, 801), [vs_pos, vs_neg, va0, vg0, vc, vd, out_speeds["v_a_effective_mps"], g_eff]]))
    up = np.array([upper(v) for v in vgrid])
    lo = np.array([lower(v) for v in vgrid])
    poly = [[float(v), float(n)] for v, n in zip(vgrid, up)] + [[float(v), float(n)] for v, n in zip(vgrid[::-1], lo[::-1])]
    names = [("A", out_speeds["v_a_effective_mps"], upper), ("C+", vc, upper), ("D+", vd, upper),
             ("G", out_speeds["v_g_effective_mps"], lower), ("C-", vc, lower), ("D-", vd, lower)]
    corners = []
    for nm, v, fn in names:
        n = float(fn(v))
        corners.append({"name": nm, "v_eas_mps": float(v), "v_keas": keas(v), "n_limit": n, "n_ultimate": 1.5 * n,
                        "governing": ("maneuver" if abs(n - (npos if n > 0 else nneg)) < 1e-6 or (nm in ("G",) and abs(n - nneg) < 1e-6) else "gust/stall/linear")})
    # estalla con flaps: solo la linea
    flaps = None
    if case.get("cl_max_flaps"):
        cf = abs(case["cl_max_flaps"])
        flaps = {"cl_max": cf, "v_s_mps": math.sqrt(2.0 * w_pa / (rho0 * cf)), "v_s_keas": keas(math.sqrt(2.0 * w_pa / (rho0 * cf))),
                 "n_limit": case.get("n_flaps"), "v_f_mps": case.get("v_f_mps"),
                 "note": "stall line only; V_F and n with flaps (§23.345) are inputs, not evaluated (text not read)"}
    return {"case": case.get("name", "case"), "category": cat, "mass_kg": case["mass_kg"], "wing_loading_pa": w_pa, "s_m2": s,
            "load_factors": {**ll, "n_ultimate_plus": 1.5 * npos, "n_ultimate_minus": 1.5 * nneg, "safety_factor": 1.5},
            "speeds": {**out_speeds, **{k + "_keas": keas(v) for k, v in out_speeds.items() if k.endswith("_mps") and v}},
            "gust": gust, "corner_points": corners, "polygon_v_eas_mps_n": poly, "flaps_down": flaps,
            "n_max_envelope": float(up.max()), "n_min_envelope": float(lo.min())}


def evaluate(project: dict) -> tuple[dict, list]:
    d = prj.need_inputs(project, "m25", ["category"])
    depends: list[str] = []
    out = project["outputs"]
    base = dict(d.get("common", {}))
    base["category"] = d["category"]
    wing = out.get("m09b", {}).get("result") if out.get("m09b") else None
    if wing:
        depends.append("m09b")
        pf = wing["planform"]
        base.setdefault("s_m2", pf["area_m2"])
        base.setdefault("c_mgc_m", pf["cmgc_m"])
        base.setdefault("cl_alpha", wing["lift_curve_slope"]["cl_alpha_recommended_per_rad"])
        if isinstance(wing.get("clmax"), dict) and wing["clmax"].get("clmax"):
            base.setdefault("cl_max", wing["clmax"]["clmax"])
    if d.get("v_h_from_m21") and out.get("m21"):
        depends.append("m21")
        base.setdefault("v_h_mps", out["m21"]["result"]["performance"]["0"]["v_max_mps"] if "performance" in out["m21"]["result"] else None)
    cases = d.get("cases")
    if not cases:
        if out.get("m12"):                                       # MTOW (w0) de M12; M13 da el peso vacio, no el de diseno
            depends.append("m12")
            cases = [{"name": "MTOW", "mass_kg": out["m12"]["result"]["w0_kg"]}]
        elif project["inputs"].get("m01", {}).get("mtow_kg"):
            cases = [{"name": "MTOW", "mass_kg": project["inputs"]["m01"]["mtow_kg"]}]
    if not cases:
        raise SystemExit("inputs.m25.cases (list of {name, mass_kg, ...}) is missing and no outputs.m12 w0_kg or inputs.m01.mtow_kg exists")
    miss = [k for k in ("s_m2", "c_mgc_m", "cl_alpha", "cl_max", "cl_min") if not any(k in {**base, **c} for c in cases)]
    if miss:
        raise SystemExit("inputs.m25 is missing: " + ", ".join(miss) + " (give them in inputs.m25.common or run m09b)")
    res = {"level": "conceptual (envelope for rigid wing with linear lift; no tail load, no dynamic response)", "units": "SI (EAS in m/s; KEAS also given)",
           "assumptions": [], "cases": []}
    for c in cases:
        res["cases"].append(build({**base, **c}))
    res["assumptions"].append("V_C limits and V_D factors for 20-100 lbf/ft^2 (33 -> 28.6, 1.4 -> 1.35; utility 1.5, aerobatic 1.55 and 36), utility 4.4 / aerobatic 6.0 and -0.5 n+: source ADRpy 0.2.6 "
                              "(CS-23.335/337), not checked in the book; the book verifies 33 sqrt(W/S), 1.4 V_Cmin, n+ = min(3.8, 2.1 + 24000/(W + 10000)), n- = -0.4 n+ and the 50/25 ft/s gusts")
    res["assumptions"].append("14 CFR Part 23 current (Amdt. 23-64) has no numerical load-factor or speed thresholds: they come from the superseded §23.333-§23.341, as in the book")
    res["assumptions"].append("positive/negative stall lines use CL_max/CL_min of the clean wing; flaps-down only the stall line (V_F and n with flaps are not evaluated)")
    return res, sorted(set(depends))


def run(project: dict) -> dict:
    result, depends = evaluate(project)
    prj.record(project, "m25", result, "conceptual", REFERENCES, depends)
    return result
