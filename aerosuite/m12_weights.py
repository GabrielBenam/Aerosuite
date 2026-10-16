"""M12 Pesos detallados (Gudmundsson Tabla 1-4 paso 12; Secs. 6.3, 6.4 y 6.5).

Nivel conceptual. Estima el peso de cada componente con las ecuaciones estadisticas de la Sec. 6.4.1 (Cessna, Raymer,
Torenbeek, USAF; aviones GA de aluminio) y con el modelo directo de cajones de ala de la Sec. 6.5 (capas del larguero y
variacion con el alargamiento). Las ecuaciones del libro estan en unidades inglesas (lbf, ft, ft^2, KEAS, psf, hp, gal
EE. UU.): se evaluan en esas unidades y el modulo recibe y devuelve SI. Siguiendo la Sec. 6.3, los pesos conocidos
(`known_weights`) mandan sobre cualquier estimacion, se evaluan todos los metodos dentro de su ambito de validez y se
promedian, y se admiten factores de calibracion por componente (`calibration`). Cada ecuacion declara su estado:
`validated` (reproduce un ejemplo del libro), `transcribed` (leida del PDF original, sin ejemplo resuelto).
"""
import math

from . import adrpy_core
from . import project as prj

LBF_PER_KG = 2.2046226218
FT_PER_M = 3.280839895
FT2_PER_M2 = FT_PER_M ** 2
GAL_PER_M3 = 264.172052
G = 9.80665
PSF_PER_PA = 0.0208854342
AVGAS_LBF_PER_GAL = 6.0                       # GUD Ejemplo 9-3
REFERENCES = [
    "GUD Sec. 6.3, metodos de peso secundarios (pesos conocidos, estadisticos, directos), PDF 204-205 / impr. 159-160",
    "GUD Sec. 6.4.1, Ecs. 6-43 a 6-105 (pesos de componentes de aviones GA), PDF 205-209 / impr. 160-164; Ejemplo 6-5 (ala), PDF 210 / impr. 165",
    "GUD Sec. 6.4.2, Ec. 6-106 (peso de motor de piston), PDF 210 / impr. 165",
    "GUD Sec. 6.5.1-6.5.2, Ecs. 6-109 a 6-127 y Ejemplos 6-6 y 6-7 (cajon de ala, variacion con AR), PDF 212-221 / impr. 167-176",
]


# ---------------------------------------------------------------- ala (Ecs. 6-43 a 6-47; Ejemplo 6-5)
def wing_cessna_cantilever(nz, w0, sw, ar):
    return 0.04674 * (nz * w0) ** 0.397 * sw ** 0.360 * ar ** 1.712                      # Ec. 6-43


def wing_cessna_strut(nz, sw, ar):
    return 0.002933 * nz ** 0.611 * sw ** 1.018 * ar ** 2.473                              # Ec. 6-44 (sin W0)


def wing_raymer(nz, w0, sw, ar, sweep_c4_deg, tc, q, taper, wfw=0.0):
    wfw = wfw if wfw > 0.0 else 1.0                                                         # si W_FW = 0, W_FW^0.0035 = 1
    c4 = math.cos(math.radians(sweep_c4_deg))
    return (0.036 * sw ** 0.758 * wfw ** 0.0035 * (ar / c4 ** 2) ** 0.6 * q ** 0.006 * taper ** 0.04
            * (100.0 * tc / c4) ** -0.3 * (nz * w0) ** 0.49)                              # Ec. 6-45


def wing_torenbeek(nz, w0, bw, sw, sweep_c2_deg, t_max_root_ft):
    c2 = math.cos(math.radians(sweep_c2_deg))
    return (0.00125 * w0 * (bw / c2) ** 0.75 * (1.0 + math.sqrt(6.3 * c2 / bw)) * nz ** 0.55
            * (bw * sw / (t_max_root_ft * w0 * c2)) ** 0.30)                              # Ec. 6-46


def wing_usaf(nz, w0, sw, ar, sweep_c4_deg, tc, taper, vh_keas):
    c4 = math.cos(math.radians(sweep_c4_deg))
    return 96.948 * ((nz * w0 / 1e5) ** 0.65 * (ar / c4 ** 2) ** 0.57 * (sw / 100.0) ** 0.61
                     * ((1.0 + taper) / (2.0 * tc)) ** 0.36 * math.sqrt(1.0 + vh_keas / 500.0)) ** 0.993   # Ec. 6-47


# ---------------------------------------------------------------- cola horizontal (Ecs. 6-48 a 6-51)
def ht_cessna(w0, s, ar, t_max_ft):
    return 3.184 * w0 ** 0.887 * s ** 0.101 * ar ** 0.138 / (174.04 * t_max_ft ** 0.223)  # Ec. 6-48


def ht_raymer(nz, w0, q, s, tc, sweep_c4_deg, ar_w, sweep_ht_deg, taper_ht):
    c4, ch = math.cos(math.radians(sweep_c4_deg)), math.cos(math.radians(sweep_ht_deg))
    return (0.016 * (nz * w0) ** 0.414 * q ** 0.168 * s ** 0.896 * (100.0 * tc / c4) ** -0.12
            * (ar_w / ch ** 2) ** 0.043 * taper_ht ** -0.02)                              # Ec. 6-49


def ht_usaf(nz, w0, s, l_ht, b_ht, t_max_ft):
    return 71.927 * ((nz * w0 / 1e5) ** 0.87 * (s / 100.0) ** 1.2 * (l_ht / 10.0) ** 0.483
                     * math.sqrt(b_ht / t_max_ft)) ** 0.458                               # Ec. 6-51


def empennage_torenbeek(nz, s_ht, s_vt):
    return 0.04 * (nz * (s_ht + s_vt) ** 2) ** 0.75                                       # Ec. 6-50 (HT + VT)


# ---------------------------------------------------------------- cola vertical (Ecs. 6-52 a 6-54)
def vt_cessna(f_tail, w0, s, ar, t_max_ft, sweep_vt_deg):
    return ((1.0 + 0.2 * f_tail) * 1.68 * w0 ** 0.567 * s ** 0.1249 * ar ** 0.482
            / (639.95 * t_max_ft ** 0.747 * math.cos(math.radians(sweep_vt_deg)) ** 0.882))   # Ec. 6-52


def vt_raymer(f_tail, nz, w0, q, s, tc, sweep_vt_deg, ar_w, taper_vt):
    c = math.cos(math.radians(sweep_vt_deg))
    return (0.073 * (1.0 + 0.2 * f_tail) * (nz * w0) ** 0.376 * q ** 0.122 * s ** 0.873 * (100.0 * tc / c) ** -0.49
            * (ar_w / c ** 2) ** 0.357 * taper_vt ** 0.039)                               # Ec. 6-53


def vt_usaf(f_tail, nz, w0, s, b_vt, t_max_ft):
    return 55.786 * (1.0 + 0.2 * f_tail) * ((nz * w0 / 1e5) ** 0.87 * (s / 100.0) ** 1.2
                                             * math.sqrt(b_vt / t_max_ft)) ** 0.458         # Ec. 6-54


# ---------------------------------------------------------------- fuselaje (Ecs. 6-55 a 6-58)
def fuselage_cessna(w0, r_max, l_fs, high_wing, n_occ):
    if high_wing:
        return 14.86 * w0 ** 0.144 * (l_fs / r_max) ** 0.778 * l_fs ** 0.383 * n_occ ** 0.455   # Ec. 6-56
    return 0.04682 * w0 ** 0.692 * r_max ** 0.374 * l_fs ** 0.590                               # Ec. 6-55


def fuselage_raymer(s_fus, nz, w0, l_ht, l_fs, d_fs, q, v_p=0.0, dp_psi=0.0):
    return (0.052 * s_fus ** 1.086 * (nz * w0) ** 0.177 * l_ht ** -0.051 * (l_fs / d_fs) ** -0.072 * q ** 0.241
            + 11.9 * (v_p * dp_psi) ** 0.271)                                             # Ec. 6-57


def fuselage_usaf(nz, w0, l_f, w_f, d_f, vh_keas):
    return 200.0 * ((nz * w0 / 1e5) ** 0.286 * (l_f / 10.0) ** 0.857 * ((w_f + d_f) / 10.0)
                    * (vh_keas / 100.0) ** 0.338) ** 1.1                                  # Ec. 6-58


# ---------------------------------------------------------------- tren (Ecs. 6-65 a 6-67 y 6-64)
def main_gear_raymer(nl, wl, lm):
    return 0.095 * (nl * wl) ** 0.768 * lm ** 0.409


def nose_gear_raymer(nl, wl, ln):
    return 0.125 * (nl * wl) ** 0.566 * ln ** 0.845


def landing_gear_usaf(nl, wl, lm):
    return 0.054 * (nl * wl) ** 0.684 * lm ** 0.501                                       # Ec. 6-64 (incluye la pata de nariz)


# ---------------------------------------------------------------- planta motriz, combustible y sistemas
def engine_dry_piston(p_max_bhp):
    return 50.56 + 1.352 * p_max_bhp                                                      # Ec. 6-106


def installed_engine_cessna(p_max, w_prop, n_eng, w_nac):
    return (1.3 * p_max + w_prop) * n_eng + w_nac                                         # Ec. 6-77


def installed_engine_raymer_usaf(w_eng, n_eng):
    return 2.575 * w_eng ** 0.922 * n_eng                                                 # Ecs. 6-78 y 6-80 (incluye gondola/capot)


def installed_engine_torenbeek(w_eng, w_prop, n_eng, p_max, w_nac):
    return (w_eng + w_prop) * n_eng + 1.03 * n_eng ** 0.3 * p_max ** 0.7 + w_nac          # Ec. 6-79


def nacelle_cessna(p_max, n_eng, kind):
    return (0.37 if kind == "radial" else 0.24) * p_max * n_eng                           # Ecs. 6-68, 6-69


def nacelle_torenbeek(p_max, n_eng, kind):
    if kind == "single_tractor":
        return 2.5 * math.sqrt(p_max)                                                     # Ec. 6-70
    return {"hop": 0.32 * p_max * n_eng, "radial": 0.045 * p_max ** 1.25 * n_eng}[kind]   # Ecs. 6-71, 6-72


def fuel_system(q_tot_gal, q_int_gal, n_tank, n_eng, tip_tanks=False):
    cessna = (0.70 if tip_tanks else 0.40) * q_tot_gal                                    # Ecs. 6-81, 6-83 (Avgas)
    frac = q_tot_gal / (q_tot_gal + q_int_gal) if (q_tot_gal + q_int_gal) > 0 else 1.0
    raymer = 2.49 * q_tot_gal ** 0.726 * frac ** 0.363 * n_tank ** 0.242 * n_eng ** 0.157   # Ec. 6-85
    usaf = 2.49 * (q_tot_gal ** 0.6 * frac ** 0.3 * n_tank ** 0.2 * n_eng ** 0.13) ** 1.21   # Ec. 6-89
    return {"cessna": cessna, "raymer": raymer, "usaf": usaf}


def controls(w0, l_fs, b_w, nz):
    return {"cessna": 0.0168 * w0,                                                        # Ec. 6-90 (W0 <= 8000 lbf)
            "raymer": 0.053 * l_fs ** 1.536 * b_w ** 0.371 * (nz * w0 * 1e-4) ** 0.80,    # Ec. 6-91
            "torenbeek": 0.23 * w0 ** 0.667,                                              # Ec. 6-92
            "usaf": 1.066 * w0 ** 0.626}                                                  # Ec. 6-95


def hydraulics(w0):
    return 0.001 * w0                                                                     # Ec. 6-97


def avionics_installed(w_uninstalled):
    return 2.11 * w_uninstalled ** 0.933                                                  # Ec. 6-98


def air_conditioning(w0, n_occ, w_av, mach):
    return 0.265 * w0 ** 0.52 * n_occ ** 0.68 * w_av ** 0.17 * mach ** 0.080             # Ec. 6-102


def electrical(w0, w_fs, w_av):
    return {"cessna": 0.0268 * w0, "raymer_usaf": 12.57 * (w_fs + w_av) ** 0.51}          # Ecs. 6-99, 6-101


def furnishings(n_occ, w0, n_crew, q_h):
    return {"cessna": 0.0412 * n_occ ** 1.145 * w0 ** 0.489,                              # Ec. 6-103
            "raymer": 0.0582 * w0 - 65.0,                                                 # Ec. 6-104
            "usaf": 34.5 * n_crew * q_h ** 0.25}                                          # Ec. 6-105


# ---------------------------------------------------------------- cajon directo de ala (Sec. 6.5; Ejemplos 6-6 y 6-7)
def box_wing_geometry(s, ar, taper, tc):
    """Ecs. 6-112 a 6-114 (unidades coherentes): b, c_MGC, y_MGC y profundidad estructural h en el plano de simetria."""
    b = math.sqrt(ar * s)
    c_mgc = 4.0 / 3.0 * math.sqrt(s / ar) * (1.0 + taper + taper ** 2) / (1.0 + taper) ** 2
    y_mgc = b / 6.0 * (1.0 + 2.0 * taper) / (1.0 + taper)
    return {"span": b, "cmgc": c_mgc, "ymgc": y_mgc, "h": c_mgc * tc}


def spar_cap(n_ult, w0, s, ar, taper, tc, sigma_max, rho_cap):
    """Ecs. 6-115 a 6-118: momento maximo en la raiz, area de cabeza de larguero y peso de las
    cabezas (el area en la punta es 10 % de la de la raiz, factor 1.1). Unidades coherentes (p. ej. lbf, ft, psf, lbf/ft^3)."""
    g = box_wing_geometry(s, ar, taper, tc)
    m_max = n_ult * w0 / 2.0 * g["ymgc"]
    a_cap = n_ult * w0 * ar * (1.0 + 3.0 * taper + 2.0 * taper ** 2) / (
        16.0 * sigma_max * tc * (1.0 + taper + taper ** 2))
    w_cap = 1.1 * rho_cap * a_cap * g["span"]
    return {**g, "m_max": m_max, "a_cap": a_cap, "w_cap": w_cap}


def ar_scaling(w_cap1, m_max1, ar1, ar2):
    """Metodo de las fracciones (Ecs. 6-119 a 6-127), S y lambda constantes: b ~ AR^1/2, M_max ~ AR^1/2, A_cap ~ AR,
    W_cap ~ AR^3/2."""
    r = ar2 / ar1
    return {"span_ratio": math.sqrt(r), "m_max": m_max1 * math.sqrt(r), "a_cap_ratio": r, "w_cap": w_cap1 * r ** 1.5,
            "delta_w_cap": w_cap1 * (r ** 1.5 - 1.0)}


# ================================================================ integracion con project.json
def _need(project: dict, mod: str, why: str):
    if mod not in project["outputs"]:
        raise SystemExit(f"inputs.m12 needs outputs.{mod} ({why}): run {mod} first")
    return project["outputs"][mod]["result"]


def _q_psf(v_mps: float, altitude_m: float) -> float:
    atm = adrpy_core._libraries()[0].Atmosphere()
    rho = float(atm.airdens_kgpm3(altitude_m))
    return 0.5 * rho * v_mps ** 2 * PSF_PER_PA


def _method(eq, status, value_lbf, scope_ok=True, note=None):
    return {"eq": eq, "status": status, "lbf": value_lbf, "kg": value_lbf / LBF_PER_KG, "in_scope": scope_ok,
            **({"note": note} if note else {})}


def _component(methods: dict, known_kg, calibration: float, exclude: list, missing: list) -> dict:
    usable = {k: v for k, v in methods.items() if v["in_scope"] and k not in exclude}
    out = {"methods": methods, "missing_inputs": missing, "calibration_factor": calibration}
    if known_kg is not None:
        out.update({"source": "known weight (supersedes estimates, GUD Sec. 6.3)", "kg": known_kg})
    elif usable:
        mean = sum(v["kg"] for v in usable.values()) / len(usable)
        out.update({"source": "mean of the in-scope statistical methods (GUD Sec. 6.4.1)", "kg": mean * calibration,
                    "methods_averaged": sorted(usable),
                    "spread_kg": [min(v["kg"] for v in usable.values()), max(v["kg"] for v in usable.values())]})
    else:
        out.update({"source": "no applicable method", "kg": None})
    return out


def _globals(project: dict, d: dict, depends: list) -> dict:
    """Datos comunes a todas las ecuaciones: W0, factor de carga ultimo, presiones dinamicas, ocupantes."""
    if "w0_kg" in d:
        w0_kg = float(d["w0_kg"])
    else:
        w0_kg = _need(project, "m06", "initial weight W0")["w0_kg"]
        depends.append("m06")
    if "n_ult" in d:
        nz = float(d["n_ult"])
    else:
        n_plus = _need(project, "m01", "limit load factor; or give inputs.m12.n_ult")["maneuver_load_factors"].get("n_plus")
        if not n_plus:
            raise SystemExit("M01 has no limit load factor for this category (D-17): give inputs.m12.n_ult")
        nz = 1.5 * n_plus                                            # n_z = 1.5 x limit load factor (GUD Sec. 6.4.1)
        depends.append("m01")
    if "landing_weight_fraction" not in d:
        prj.add_assumption(project, "m12", "landing_weight_fraction", 1.0, "supuesto: peso de aterrizaje de diseño = W0")
    cruise = d.get("cruise") or {}
    brief = project["inputs"].get("m04", {}).get("concept", {}).get("designbrief", {})
    v_ktas = float(cruise.get("ktas", brief.get("cruisespeed_ktas", 0.0)))
    h = float(cruise.get("altitude_m", brief.get("cruisealt_m", 0.0)))
    if v_ktas <= 0.0:
        raise SystemExit("inputs.m12.cruise.ktas (or the M04 brief cruise speed) is required")
    vh = float(d["vh_keas"]) if "vh_keas" in d else v_ktas
    if "vh_keas" not in d:
        prj.add_assumption(project, "m12", "vh_keas", vh,
                           "supuesto: V_H (máxima a nivel del mar, KEAS) igual a la velocidad de crucero de M04")
    atm = adrpy_core._libraries()[0].Atmosphere()
    n_occ = int(d.get("occupants", project["inputs"].get("m01", {}).get("occupants", 0)))
    if n_occ < 1:
        raise SystemExit("inputs.m12.occupants (or inputs.m01.occupants) is required")
    return {"w0_kg": w0_kg, "w0": w0_kg * LBF_PER_KG, "nz": nz, "wl": float(d.get("landing_weight_fraction", 1.0)) * w0_kg * LBF_PER_KG,
            "v_ktas": v_ktas, "h": h, "q": _q_psf(v_ktas * 0.514444, h), "vh": vh, "q_h": 0.5 * 0.002377 * (vh * 1.688) ** 2,
            "mach": v_ktas * 0.514444 / float(atm.vsound_mps(h)), "n_occ": n_occ, "n_crew": int(d.get("crew", 1))}


def _lifting_components(project, d, g, kw, cal, exc, depends):
    """Ala, cola horizontal y cola vertical (Ecs. 6-43 a 6-54)."""
    w0, nz, q, vh = g["w0"], g["nz"], g["q"], g["vh"]
    wing = _need(project, "m09b", "wing planform")["planform"]
    tail = _need(project, "m08", "tail sizing")
    depends += ["m09b", "m08"]
    ht, vt = tail["horizontal_tail"], tail["vertical_tail"]
    sw, bw, ar = wing["area_m2"] * FT2_PER_M2, wing["span_m"] * FT_PER_M, wing["aspect_ratio"]
    lam, c4, c2 = wing["taper_ratio"], wing["sweep_c4_deg"], wing["sweep_c2_deg"]
    if "wing_tc" not in d:
        raise SystemExit("inputs.m12.wing_tc (wing maximum thickness ratio) is required")
    tc = float(d["wing_tc"])
    if "tail_tc" not in d:
        prj.add_assumption(project, "m12", "tail_tc", 0.09, "supuesto: espesor relativo 0.09 (NACA 0009, coherente con M10)")
    tail_tc = float(d.get("tail_tc", 0.09))
    ok_c, ok_u = vh <= 200.0, vh <= 300.0
    scope_c = None if ok_c else "Cessna equations are valid for V_H <= 200 KTAS"
    ok_usaf_w = ok_u and w0 <= 12500.0
    wm = {"cessna_cantilever": _method("6-43", "validated (Example 6-5)", wing_cessna_cantilever(nz, w0, sw, ar), ok_c, scope_c),
          "cessna_strut_braced": _method("6-44", "validated (Example 6-5)", wing_cessna_strut(nz, sw, ar), ok_c,
                                         "strut-braced wings only; no W0 in the equation, use with care (GUD)"),
          "raymer": _method("6-45", "validated (Example 6-5)",
                            wing_raymer(nz, w0, sw, ar, c4, tc, q, lam, kw.get("fuel_in_wing_kg", 0.0) * LBF_PER_KG)),
          "torenbeek": _method("6-46", "validated (Example 6-5)",
                               wing_torenbeek(nz, w0, bw, sw, c2, wing["root_chord_m"] * FT_PER_M * tc)),
          "usaf": _method("6-47", "validated (Example 6-5, V_H inferred)", wing_usaf(nz, w0, sw, ar, c4, tc, lam, vh), ok_usaf_w,
                          None if ok_usaf_w else "USAF: V_H <= 300 KTAS and W0 <= 12 500 lbf")}
    strut = bool(d.get("strut_braced", False))
    wm["cessna_cantilever" if strut else "cessna_strut_braced"].update(
        {"in_scope": False, "note": "excluded by the declared wing type (inputs.m12.strut_braced)"})
    comps = {"wing": _component(wm, kw.get("wing_kg"), cal.get("wing", 1.0), exc.get("wing", []), [])}
    f_tail = int(d.get("t_tail", False))
    sht, svt = ht["area_m2"] * FT2_PER_M2, vt["area_m2"] * FT2_PER_M2
    t_ht, t_vt = ht["root_chord_m"] * FT_PER_M * tail_tc, vt["root_chord_m"] * FT_PER_M * tail_tc
    lht = ht["arm_m"] * FT_PER_M
    sw_ht, sw_vt = float(d.get("ht_sweep_c4_deg", 0.0)), float(d.get("vt_sweep_c4_deg", 0.0))
    hm = {"cessna": _method("6-48", "transcribed", ht_cessna(w0, sht, ht["aspect_ratio"], t_ht), ok_c, scope_c),
          "raymer": _method("6-49", "transcribed", ht_raymer(nz, w0, q, sht, tc, c4, ar, sw_ht, ht["taper_ratio"]), True,
                            "the book does not define t/c and AR in Eq. 6-49: wing values assumed (as printed)"),
          "usaf": _method("6-51", "transcribed", ht_usaf(nz, w0, sht, lht, ht["span_m"] * FT_PER_M, t_ht), ok_u)}
    comps["horizontal_tail"] = _component(hm, kw.get("horizontal_tail_kg"), cal.get("horizontal_tail", 1.0),
                                          exc.get("horizontal_tail", []), [])
    suspect = bool(d.get("include_suspect_equations", False))
    vm = {"cessna": _method("6-52", "suspect (printed exponent of S_VT gives 0.9 lbf for an 18 ft^2 fin)",
                            vt_cessna(f_tail, w0, svt, vt["aspect_ratio"], t_vt, sw_vt), ok_c and suspect,
                            scope_c or "excluded by default: with S_VT^0.1249 as printed the result is implausibly small "
                                       "(D-29); inputs.m12.include_suspect_equations = true keeps it"),
          "raymer": _method("6-53", "transcribed", vt_raymer(f_tail, nz, w0, q, svt, tc, sw_vt, ar, vt["taper_ratio"]), True,
                            "the book does not define t/c and AR in Eq. 6-53: wing values assumed (as printed)"),
          "usaf": _method("6-54", "transcribed", vt_usaf(f_tail, nz, w0, svt, vt["span_m"] * FT_PER_M, t_vt), ok_u)}
    comps["vertical_tail"] = _component(vm, kw.get("vertical_tail_kg"), cal.get("vertical_tail", 1.0),
                                        exc.get("vertical_tail", []), [])
    return comps, {"sw": sw, "bw": bw, "ar": ar, "tc": tc, "lht": lht, "ok_c": ok_c, "ok_u": ok_u, "scope_c": scope_c,
                   "lam": lam, "wing": wing}


def _body_components(project, d, g, kw, cal, exc, depends, ctx):
    """Fuselaje, tren y planta motriz instalada (Ecs. 6-55 a 6-80, 6-106)."""
    w0, nz, q, vh = g["w0"], g["nz"], g["q"], g["vh"]
    ok_c, ok_u, scope_c, lht = ctx["ok_c"], ctx["ok_u"], ctx["scope_c"], ctx["lht"]
    fus_in = d.get("fuselage", {})
    if "m10" in project["outputs"] and not fus_in.get("manual"):
        fus = next(c for c in project["outputs"]["m10"]["result"]["components"] if c["type"] == "fuselage")
        depends.append("m10")
        l_f, r_max, s_fus = fus["length_m"] * FT_PER_M, fus["max_radius_m"] * FT_PER_M, fus["wetted_area_estimate_m2"] * FT2_PER_M2
    else:
        for k in ("length_m", "radius_m", "wetted_area_m2"):
            if k not in fus_in:
                raise SystemExit("inputs.m12.fuselage {length_m, radius_m, wetted_area_m2} is required without M10")
        l_f, r_max, s_fus = fus_in["length_m"] * FT_PER_M, fus_in["radius_m"] * FT_PER_M, fus_in["wetted_area_m2"] * FT2_PER_M2
    l_fs = float(fus_in.get("structure_length_m", 0.0)) * FT_PER_M or l_f
    if "structure_length_m" not in fus_in:
        prj.add_assumption(project, "m12", "fuselage_structure_length_m", l_f / FT_PER_M,
                           "supuesto: l_FS (mamparo delantero a cuaderna trasera) = longitud del fuselaje")
    d_f = 2.0 * r_max
    fm = {"cessna": _method("6-55/6-56", "transcribed",
                            fuselage_cessna(w0, 2.0 * math.pi * r_max, l_fs, d.get("high_wing", False), g["n_occ"]),
                            ok_c and not d.get("pressurized", False), "Cessna: unpressurized fuselages, V_H <= 200 KTAS"),
          "raymer": _method("6-57", "transcribed", fuselage_raymer(s_fus, nz, w0, lht, l_fs, d_f, q)),
          "usaf": _method("6-58", "transcribed", fuselage_usaf(nz, w0, l_f, d_f, d_f, vh), ok_u)}
    comps = {"fuselage": _component(fm, kw.get("fuselage_kg"), cal.get("fuselage", 1.0), exc.get("fuselage", []), [])}
    lg = d.get("landing_gear")
    if lg and "ultimate_landing_load_factor" in lg and "main_strut_m" in lg:
        nl, lm, wl = float(lg["ultimate_landing_load_factor"]), lg["main_strut_m"] * FT_PER_M, g["wl"]
        ray = main_gear_raymer(nl, wl, lm) + (nose_gear_raymer(nl, wl, lg["nose_strut_m"] * FT_PER_M) if "nose_strut_m" in lg else 0.0)
        comps["landing_gear"] = _component({"raymer": _method("6-65+6-67", "transcribed", ray),
                                            "usaf": _method("6-64", "transcribed", landing_gear_usaf(nl, wl, lm), ok_u)},
                                           kw.get("landing_gear_kg"), cal.get("landing_gear", 1.0), exc.get("landing_gear", []), [])
    else:
        comps["landing_gear"] = _component({}, kw.get("landing_gear_kg"), 1.0, [],
                                           ["landing_gear.ultimate_landing_load_factor", "landing_gear.main_strut_m"])
    eng = d.get("engine", {})
    p_max = eng.get("rated_bhp")
    if p_max is None and "m11" in project["outputs"]:
        p_max = project["outputs"]["m11"]["result"]["engine"]["rated_bhp"]
        depends.append("m11")
    n_eng = int(eng.get("count", 1))
    w_eng = kw["engine_dry_kg"] * LBF_PER_KG if "engine_dry_kg" in kw else (engine_dry_piston(p_max) if p_max else None)
    w_prop = kw["propeller_kg"] * LBF_PER_KG if "propeller_kg" in kw else None
    kind = eng.get("nacelle_kind", "single_tractor" if n_eng == 1 else "hop")
    if p_max and w_eng is not None:
        em = {"raymer_usaf": _method("6-78/6-80", "transcribed", installed_engine_raymer_usaf(w_eng, n_eng), True,
                                     "includes nacelle/cowl and propeller")}
        if w_prop is not None:
            nac_c = nacelle_cessna(p_max, n_eng, "radial" if kind == "radial" else "hop")
            em["cessna"] = _method("6-77+6-68/6-69", "transcribed", installed_engine_cessna(p_max, w_prop, n_eng, nac_c), ok_c, scope_c)
            em["torenbeek"] = _method("6-79+6-70/6-72", "transcribed",
                                      installed_engine_torenbeek(w_eng, w_prop, n_eng, p_max, nacelle_torenbeek(p_max, n_eng, kind)))
        miss = [] if w_prop is not None else ["known_weights.propeller_kg (Cessna and Torenbeek need the manufacturer's propeller weight)"]
        comps["engine_installed"] = _component(em, kw.get("engine_installed_kg"), cal.get("engine_installed", 1.0),
                                               exc.get("engine_installed", []), miss)
        comps["engine_installed"]["engine_dry_lbf"] = w_eng
        comps["engine_installed"]["engine_dry_source"] = "known weight" if "engine_dry_kg" in kw else "Eq. 6-106 (piston, statistical)"
    else:
        comps["engine_installed"] = _component({}, kw.get("engine_installed_kg"), 1.0, [], ["engine.rated_bhp (or outputs.m11)"])
    return comps, n_eng, l_fs


def _system_components(d, g, kw, cal, exc, ctx, n_eng, l_fs):
    """Combustible, mandos, hidraulica, aviónica, electrico, acondicionamiento y mobiliario (Ecs. 6-81 a 6-105)."""
    w0, nz = g["w0"], g["nz"]
    ok_c, ok_u, scope_c = ctx["ok_c"], ctx["ok_u"], ctx["scope_c"]
    comps, w_fs = {}, 0.0
    fuel = d.get("fuel")
    if fuel and "total_gal" in fuel:
        fs = fuel_system(fuel["total_gal"], fuel.get("integral_gal", 0.0), int(fuel.get("tanks", 2)), n_eng, fuel.get("tip_tanks", False))
        comps["fuel_system"] = _component({k: _method(e, "transcribed", fs[k]) for k, e in
                                           (("cessna", "6-81/6-83"), ("raymer", "6-85"), ("usaf", "6-89"))},
                                          kw.get("fuel_system_kg"), cal.get("fuel_system", 1.0), exc.get("fuel_system", []), [])
        w_fs = (comps["fuel_system"]["kg"] or 0.0) * LBF_PER_KG
    else:
        comps["fuel_system"] = _component({}, kw.get("fuel_system_kg"), 1.0, [], ["fuel.total_gal"])
    ct = controls(w0, l_fs, ctx["bw"], nz)
    cm = {k: _method(e, "transcribed", ct[k]) for k, e in
          (("cessna", "6-90"), ("raymer", "6-91"), ("torenbeek", "6-92"), ("usaf", "6-95"))}
    cm["cessna"]["in_scope"] = w0 <= 8000.0 and ok_c
    cm["usaf"]["in_scope"] = ok_u
    comps["flight_controls"] = _component(cm, kw.get("flight_controls_kg"), cal.get("flight_controls", 1.0),
                                          exc.get("flight_controls", []), [])
    comps["hydraulics"] = _component({"all": _method("6-97", "transcribed", hydraulics(w0))}, kw.get("hydraulics_kg"),
                                     cal.get("hydraulics", 1.0), exc.get("hydraulics", []), [])
    if "avionics_uninstalled_kg" in kw:
        comps["avionics"] = _component({"all": _method("6-98", "transcribed", avionics_installed(kw["avionics_uninstalled_kg"] * LBF_PER_KG))},
                                       kw.get("avionics_installed_kg"), cal.get("avionics", 1.0), exc.get("avionics", []), [])
        w_av = (comps["avionics"]["kg"] or 0.0) * LBF_PER_KG
        el = electrical(w0, w_fs, w_av)
        comps["electrical"] = _component({"cessna": _method("6-99", "transcribed", el["cessna"], ok_c, scope_c),
                                          "raymer_usaf": _method("6-101", "transcribed", el["raymer_usaf"])},
                                         kw.get("electrical_kg"), cal.get("electrical", 1.0), exc.get("electrical", []), [])
        comps["air_conditioning"] = _component(
            {"all": _method("6-102", "transcribed", air_conditioning(w0, g["n_occ"], w_av, g["mach"]))},
            kw.get("air_conditioning_kg"), cal.get("air_conditioning", 1.0), exc.get("air_conditioning", []), [])
    else:
        need = ["known_weights.avionics_uninstalled_kg"]
        comps["avionics"] = _component({}, kw.get("avionics_installed_kg"), 1.0, [], need)
        comps["electrical"] = _component({}, kw.get("electrical_kg"), 1.0, [], need)
        comps["air_conditioning"] = _component({}, kw.get("air_conditioning_kg"), 1.0, [], need)
    fu = furnishings(g["n_occ"], w0, g["n_crew"], g["q_h"])
    comps["furnishings"] = _component({"cessna": _method("6-103", "transcribed", fu["cessna"], ok_c, scope_c),
                                       "raymer": _method("6-104", "transcribed", fu["raymer"]),
                                       "usaf": _method("6-105", "transcribed", fu["usaf"], ok_u)},
                                      kw.get("furnishings_kg"), cal.get("furnishings", 1.0), exc.get("furnishings", []), [])
    return comps


def _direct_wing(d, g, ctx):
    """Cajon directo de ala, solo cabezas de larguero (Ecs. 6-115 a 6-118) y variacion con AR (Ecs. 6-119 a 6-127)."""
    dw = d["direct_wing"]
    sw, ar, lam = ctx["sw"], ctx["ar"], ctx["lam"]
    sc = spar_cap(float(dw.get("n_ult", g["nz"])), g["w0"], sw, ar, lam, float(dw.get("tc", ctx["tc"])),
                  dw["sigma_max_pa"] * PSF_PER_PA, dw["rho_cap_kgm3"] / 16.01846337)      # kg/m^3 -> lbf/ft^3
    nm = 1.3558179483
    out = {"span_m": sc["span"] / FT_PER_M, "cmgc_m": sc["cmgc"] / FT_PER_M, "ymgc_m": sc["ymgc"] / FT_PER_M,
           "structural_depth_m": sc["h"] / FT_PER_M, "max_bending_moment_nm": sc["m_max"] * nm,
           "spar_cap_area_m2": sc["a_cap"] / FT2_PER_M2, "spar_cap_weight_kg": sc["w_cap"] / LBF_PER_KG,
           "scope": "spar caps only (Eqs. 6-115 to 6-118); skin, shear web and ribs of Sec. 6.5.1 are not implemented (D-29)"}
    if dw.get("ar_values"):
        out["ar_variation"] = []
        for ar2 in dw["ar_values"]:
            s2 = ar_scaling(sc["w_cap"], sc["m_max"], ar, ar2)
            out["ar_variation"].append({"aspect_ratio": ar2, "spar_cap_weight_kg": s2["w_cap"] / LBF_PER_KG,
                                        "delta_spar_cap_weight_kg": s2["delta_w_cap"] / LBF_PER_KG,
                                        "max_bending_moment_nm": s2["m_max"] * nm, "span_m": ctx["wing"]["span_m"] * s2["span_ratio"]})
    return out


def evaluate(project: dict) -> tuple[dict, list]:
    d = prj.need_inputs(project, "m12", [])
    depends: list = []
    kw, cal, exc = d.get("known_weights", {}), d.get("calibration", {}), d.get("exclude_methods", {})
    g = _globals(project, d, depends)
    comps, ctx = _lifting_components(project, d, g, kw, cal, exc, depends)
    body, n_eng, l_fs = _body_components(project, d, g, kw, cal, exc, depends, ctx)
    comps.update(body)
    comps.update(_system_components(d, g, kw, cal, exc, ctx, n_eng, l_fs))
    groups = {"structure": ("wing", "horizontal_tail", "vertical_tail", "fuselage", "landing_gear"),
              "propulsion": ("engine_installed", "fuel_system"),
              "systems": ("flight_controls", "hydraulics", "electrical", "air_conditioning"),
              "equipment": ("avionics", "furnishings")}
    totals, missing = {}, []
    for grp, names in groups.items():
        totals[grp] = sum(comps[n]["kg"] for n in names if comps[n]["kg"] is not None)
        missing += [f"{n}: {', '.join(comps[n]['missing_inputs']) or 'no applicable method'}" for n in names if comps[n]["kg"] is None]
    we_kg = sum(totals.values())
    result = {"level": "conceptual", "units": "SI (kg); equations evaluated in lbf/ft", "w0_kg": g["w0_kg"],
              "ultimate_load_factor": g["nz"],
              "conditions": {"q_cruise_psf": g["q"], "q_vh_psf": g["q_h"], "vh_keas": g["vh"], "cruise_ktas": g["v_ktas"],
                             "mach_cruise": g["mach"], "landing_weight_kg": g["wl"] / LBF_PER_KG},
              "components": comps, "group_totals_kg": totals, "empty_weight_kg": we_kg, "complete": not missing, "missing": missing,
              "validation_note": "wing equations (6-43 to 6-47) reproduce Example 6-5; all other component equations are transcribed "
                                 "from the original PDF without a solved example in the book (D-29)",
              "warnings": [] if not missing else ["the empty weight is a partial sum: the missing components are listed in `missing`"]}
    we06 = project["outputs"].get("m06", {}).get("result", {}).get("we_kg")
    if we06:
        result["compare_m06"] = {"we_m06_kg": we06, "we_m12_kg": we_kg, "difference_pct": 100.0 * (we_kg / we06 - 1.0),
                                 "comparable": not missing}
        if "m06" not in depends:
            depends.append("m06")
    if "direct_wing" in d:
        result["direct_wing"] = _direct_wing(d, g, ctx)
    return result, depends


def run(project: dict) -> dict:
    result, depends = evaluate(project)
    prj.record(project, "m12", result, "conceptual", REFERENCES, sorted(set(depends)))
    return result
