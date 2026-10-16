"""M09b Ala (Gudmundsson Tabla 1-4 paso 9; Cap. 9, Secs. 9.2, 9.3, 9.5.4, 9.5.5, 9.5.12).

Nivel conceptual (relaciones del libro; no hay analisis 3D). Define la planta trapezoidal desde S, AR y lambda
con flecha de borde de ataque o de c/4 (Ecs. 9-3, 9-8 a 9-16, 9-28 a 9-31), calcula la pendiente de sustentacion 3D
(Ecs. 9-69, 9-71/9-73 y 9-72), CL_max0 (Ecs. 9-77, 9-78, 9-76), la velocidad de perdida (Ec. 9-74), la eficiencia
de envergadura de Raymer para ala recta (Ec. 9-129), el AR efectivo por alcance/autonomia (Ec. 9-37), el volumen
interno y el combustible (Ec. 9-35/9-36 integrada) y comprueba la geometria contra las guias del libro
(Tablas 9-4 y 9-5, Secs. 9.3.3-9.3.5). Las guias son advertencias con su fuente, no penalizaciones.
flow5 (LLT/VLM) solo por archivos de intercambio: `flow5_config` genera la entrada de `flow5-export`; la corrida
del ejecutable queda pendiente de validacion con el motor real.
"""
import math
from pathlib import Path

from . import project as prj
from .m08_tail import G, trapezoid

REFERENCES = [
    "GUD Sec. 9.2.2, Ecs. 9-3, 9-8 a 9-16 (planta trapezoidal, MGC, flechas), PDF 369-370 / impr. 324-325",
    "GUD Sec. 9.2.5, Ecs. 9-28 a 9-31 (b, c_r, c_t desde S, AR, lambda), PDF 371 / impr. 326",
    "GUD Sec. 9.2.6, Ecs. 9-35 y 9-36, Ejemplo 9-3 (volumen del ala), PDF 374-375 / impr. 329-330",
    "GUD Sec. 9.3.1-9.3.5, Tablas 9-4 y 9-5 (guias de AR y lambda), Ecs. 9-37, 9-40, 9-44 a 9-46, Ejemplo 9-4, PDF 377-385 / impr. 332-340",
    "GUD Sec. 9.5.4, Ecs. 9-68 a 9-73 y Tabla 9-7 (pendiente de sustentacion), PDF 412-414 / impr. 367-369",
    "GUD Sec. 9.5.5, Ecs. 9-74 a 9-78 y Ejemplo 9-9 (CL_max), PDF 415-416 / impr. 370-371",
    "GUD Sec. 9.5.12, Ecs. 9-122 y 9-129 (eficiencia de envergadura, Raymer), PDF 428-430 / impr. 383-385",
]

FT_PER_M = 3.280839895
# Tabla 9-4 (GUD PDF 377): clase -> (AR minimo, AR maximo)
AR_RANGES = {"missile": (0.5, 1.0), "military_fighter": (2.5, 4.0), "general_aviation": (6.0, 11.0),
             "aerobatic": (5.0, 6.0), "twin_commuter": (10.0, 14.0), "commercial_jetliner": (7.0, 10.0),
             "sailplane": (10.0, 51.0)}


def sweeps(ar: float, taper: float, sweep_le_deg=None, sweep_c4_deg=None) -> dict:
    """Flechas LE, c/4 y c/2 de una planta trapezoidal (Ec. 9-16: tan L_n = tan L_m - (4/AR)(n - m)(1 - lambda)/(1 + lambda))."""
    if (sweep_le_deg is None) == (sweep_c4_deg is None):
        raise ValueError("give exactly one of sweep_le_deg or sweep_c4_deg")

    def tan_n(n, tan_m, m):
        return tan_m - 4.0 / ar * (n - m) * (1.0 - taper) / (1.0 + taper)
    if sweep_le_deg is not None:
        t_le = math.tan(math.radians(sweep_le_deg))
    else:
        t_le = tan_n(0.0, math.tan(math.radians(sweep_c4_deg)), 0.25)
    return {"sweep_le_deg": math.degrees(math.atan(t_le)),
            "sweep_c4_deg": math.degrees(math.atan(tan_n(0.25, t_le, 0.0))),
            "sweep_c2_deg": math.degrees(math.atan(tan_n(0.5, t_le, 0.0)))}


def cl_alpha_elliptic(ar: float, cl_alpha_2d: float = 2.0 * math.pi) -> float:
    """Ec. 9-68 (ala eliptica): C_La = Cl_a / (1 + Cl_a / (pi AR)); con Cl_a = 2 pi da la Ec. 9-69, 2 pi AR/(AR + 2)."""
    return cl_alpha_2d / (1.0 + cl_alpha_2d / (math.pi * ar))


def cl_alpha_helmbold(ar: float, cl_alpha_2d: float = 2.0 * math.pi) -> float:
    """Ec. 9-71 (Cl_a = 2 pi) / Ec. 9-73 (Cl_a real): C_La = Cl_a AR / (2 + sqrt(AR^2 + 4))."""
    return cl_alpha_2d * ar / (2.0 + math.sqrt(ar ** 2 + 4.0))


def cl_alpha_polhamus(ar: float, sweep_c2_deg: float, mach: float = 0.0, cl_alpha_2d: float = 2.0 * math.pi) -> float:
    """Ec. 9-72 (Polhamus, solo planta no curva y M <= 0.8):
    C_La = 2 pi AR / (2 + sqrt(4 + (AR beta / kappa)^2 (1 + tan^2(L_c/2) / beta^2))), beta = sqrt(1 - M^2), kappa = Cl_a / 2 pi.
    Forma reconstruida (la conversion digital pierde la agrupacion); reproduce las nueve filas de la Tabla 9-7 con kappa = 5.9/2 pi."""
    if not 0.0 <= mach <= 0.8:
        raise ValueError("Eq. 9-72 is limited to M <= 0.8")
    beta = math.sqrt(1.0 - mach ** 2)
    kappa = cl_alpha_2d / (2.0 * math.pi)
    t2 = math.tan(math.radians(sweep_c2_deg)) ** 2
    return 2.0 * math.pi * ar / (2.0 + math.sqrt(4.0 + (ar * beta / kappa) ** 2 * (1.0 + t2 / beta ** 2)))


def clmax0_rapid(clmax_root: float, clmax_tip: float, ymgc_m: float, span_m: float) -> dict:
    """Metodo 1 (Ecs. 9-77 y 9-78): Cl_max representativo en la MGC y CL_max0 = 0.9 Cl_max."""
    cl_rep = clmax_root + 2.0 * ymgc_m / span_m * (clmax_tip - clmax_root)
    return {"clmax_airfoil_at_mgc": cl_rep, "clmax0": 0.9 * cl_rep}


def stall_speed_mps(ws_pa: float, rho_kgm3: float, clmax: float) -> float:
    """Ec. 9-74 en SI: V_S = sqrt(2 (W/S) / (rho CL_max))."""
    return math.sqrt(2.0 * ws_pa / (rho_kgm3 * clmax))


def oswald_straight(ar: float) -> float:
    """Ec. 9-129 (Raymer, ala recta, AR > 3): e = 1.78 (1 - 0.045 AR^0.68) - 0.64."""
    if ar <= 3.0:
        raise ValueError("Eq. 9-129 is limited to AR > 3")
    return 1.78 * (1.0 - 0.045 * ar ** 0.68) - 0.64


def effective_ar_for_range(cl_cruise: float, cd_min: float, range_nm: float, w_ini: float, w_fin: float,
                           propeller: bool, sfc: float, eta_p: float = 1.0) -> dict:
    """Ec. 9-37: AR_e = C_L^2 / (pi (A - C_Dmin)), con A despejada de la ecuacion de Breguet con polar simple (Ec. 9-38):
    helice, A = 325.9 eta_p C_L ln(Wi/Wf) / (SFC_hp R) (SFC en lbf/(h hp), R en nm, pesos en cualquier unidad).
    Solo la forma de helice (la de jet necesita V en KTAS y no se implementa). Limite de la Ec. 9-40:
    C_L > R SFC_hp C_Dmin / (325.9 eta_p ln(Wi/Wf)). La agrupacion de A en la conversion digital esta perdida: se
    reconstruyo de la deduccion del libro y se comprobo con el Ejemplo 9-4 (A = 0.02872, AR_e = 7.893, limite 0.2533)."""
    if not propeller:
        raise ValueError("only the propeller form of Eq. 9-37/9-38 is implemented")
    ln = math.log(w_ini / w_fin)
    a = 325.9 * eta_p * cl_cruise * ln / (sfc * range_nm)
    cl_limit = range_nm * sfc * cd_min / (325.9 * eta_p * ln)
    if a <= cd_min:
        return {"feasible": False, "A": a, "cl_cruise_limit": cl_limit,
                "note": "A <= C_Dmin: the range cannot be reached at this C_L (Eq. 9-40)"}
    ar_e = cl_cruise ** 2 / (math.pi * (a - cd_min))
    return {"feasible": True, "A": a, "effective_aspect_ratio": ar_e, "cl_cruise_limit": cl_limit}


def wing_volume_m3(c_y1: float, c_y2: float, y1: float, y2: float, t_over_c: float, k: float) -> float:
    """Volumen de una semi-ala entre y1 e y2 (Ecs. 9-35 y 9-36): seccion = (k + 3)/6 (t/c) c^2 (D-cell parabolica + triangulo,
    t maximo en k c) integrada con cuerda lineal: V = (k + 3)/6 (t/c) (y2 - y1)/3 (c1^2 + c1 c2 + c2^2)."""
    if not (0.0 <= y1 < y2) or not 0.0 < k < 1.0:
        raise ValueError("require 0 <= y1 < y2 and 0 < k < 1")
    return (k + 3.0) / 6.0 * t_over_c * (y2 - y1) / 3.0 * (c_y1 ** 2 + c_y1 * c_y2 + c_y2 ** 2)


def _chord_at(c_r: float, taper: float, span: float, y: float) -> float:
    return c_r * (1.0 + 2.0 * (taper - 1.0) * y / span)       # c(y) = c_r (1 + 2 (lambda - 1) y / b)


def planform(s_m2: float, ar: float, taper: float, sweep_le_deg=None, sweep_c4_deg=None) -> dict:
    geo = trapezoid(s_m2, ar, taper)
    sw = sweeps(ar, taper, sweep_le_deg, sweep_c4_deg if sweep_le_deg is None else None)
    t_le = math.tan(math.radians(sw["sweep_le_deg"]))
    x_mgc = geo["ymgc_m"] * t_le                                # Ec. 9-14
    return {"area_m2": s_m2, "aspect_ratio": ar, "taper_ratio": taper, **geo, **sw, "xmgc_le_m": x_mgc,
            "mgc_quarter_chord_x_m": x_mgc + geo["cmgc_m"] / 4.0, "tip_xoffset_m": geo["span_m"] / 2.0 * t_le}


def guidance(pf: dict, wing_class, dihedral_deg: float, washout_deg: float) -> list[dict]:
    """Advertencias con su fuente; el libro no las convierte en limites duros."""
    notes = []
    if wing_class:
        lo, hi = AR_RANGES[wing_class]
        notes.append({"item": "aspect_ratio", "value": pf["aspect_ratio"], "typical_range": [lo, hi],
                      "inside": lo <= pf["aspect_ratio"] <= hi, "source": "GUD Tabla 9-4"})
    notes.append({"item": "taper_ratio", "value": pf["taper_ratio"], "typical_range": [0.3, 1.0],
                  "inside": 0.3 <= pf["taper_ratio"] <= 1.0, "source": "GUD Sec. 9.3.2: 'avoid lambda < 0.3'"})
    straight = abs(pf["sweep_c4_deg"]) < 10.0 and abs(pf["sweep_c2_deg"]) < 5.0
    notes.append({"item": "straight_wing_definition", "sweep_c4_deg": pf["sweep_c4_deg"], "sweep_c2_deg": pf["sweep_c2_deg"],
                  "straight": straight, "source": "GUD Sec. 9.3.3: lambda >= 0.3 and AR > 6 gives |L_c/4| < 10 and |L_c/2| < 5 deg"})
    notes.append({"item": "dihedral_deg", "value": dihedral_deg, "typical_range": [4.0, 7.0],
                  "inside": 4.0 <= dihedral_deg <= 7.0, "source": "GUD Sec. 9.3.4: typical aircraft 4 to 7 deg"})
    if washout_deg:
        notes.append({"item": "washout_deg", "value": washout_deg, "typical_range": [1.0, 4.0],
                      "inside": 1.0 <= washout_deg <= 4.0, "source": "GUD Sec. 9.3.5(1): 'if necessary, 1-4 deg washout'"})
    return notes


def flow5_config(pf: dict, name: str, foil_root: str, foil_tip: str, dihedral_deg: float, washout_deg: float,
                 analysis: dict, nx: int = 13, ny: int = 15) -> dict:
    """Entrada de `aerosuite flow5-export` (solo el ala, MAINWING). Archivos de intercambio: no ejecuta flow5."""
    half = pf["span_m"] / 2.0
    return {"name": name,
            "notes": ["Generated by AeroSuite M09b from the conceptual planform; flow5 NOT executed (pendiente de validacion con el motor real)."],
            "wings": [{"name": "Main wing", "type": "MAINWING", "position_m": [0.0, 0.0, 0.0], "tilt_deg": 0.0,
                       "sections": [{"y_m": 0.0, "chord_m": pf["root_chord_m"], "foil": foil_root, "nx": nx, "ny": ny},
                                    {"y_m": half, "chord_m": pf["tip_chord_m"], "xoffset_m": pf["tip_xoffset_m"],
                                     "dihedral_deg": dihedral_deg, "twist_deg": -abs(washout_deg), "foil": foil_tip,
                                     "nx": nx, "ny": ny}]}],
            "analysis": analysis}


def _naca_label(ident: str) -> str:
    return "NACA " + ident.lower().removeprefix("naca")


def _airfoil_data(project: dict, d: dict):
    """Cl_max, Cl_alpha 2D y alpha_ZL de raiz y punta: datos dados, o de las polares de XFOIL de M09a."""
    af = d.get("airfoils", {})
    depends, out = [], {}
    for end in ("root", "tip"):
        spec = af.get(end)
        if isinstance(spec, dict):
            out[end] = {"id": spec.get("id", end), **spec, "source": "input"}
        elif isinstance(spec, str):
            m = project["outputs"].get("m09a", {}).get("result", {})
            met = m.get("metrics", {}).get(spec.lower())
            if not met:
                raise SystemExit(f"inputs.m09b.airfoils.{end} = {spec!r} has no polar in outputs.m09a: run m09a with that candidate "
                                 "(XFOIL executable required) or give {'clmax', 'cl_alpha_per_rad'} directly")
            out[end] = {"id": spec.lower(), "clmax": met["clmax"], "cl_alpha_per_rad": met["cl_alpha_per_rad"],
                        "alpha_zero_lift_deg": met["alpha_zero_lift_deg"], "source": "m09a (XFOIL, 2D)",
                        "reynolds": m["conditions"].get("reynolds")}
            if "m09a" not in depends:
                depends.append("m09a")
    return out, depends


def _area(project: dict, d: dict):
    pl = d["planform"]
    if "area_m2" in pl:
        return float(pl["area_m2"]), [], {"source": "input"}
    if pl.get("from_m04"):
        if "m04" not in project["outputs"]:
            raise SystemExit("inputs.m09b.planform.from_m04 is set but outputs.m04 is missing: run m04 first")
        best = project["outputs"]["m04"]["result"].get("best_sample")
        if not best:
            raise SystemExit("outputs.m04 has no admissible design point")
        depends = ["m04"]
        if "m06" in project["outputs"] and project["inputs"].get("m04", {}).get("tow_from_m06"):
            tow, depends = project["outputs"]["m06"]["result"]["w0_kg"], ["m04", "m06"]
        else:
            tow = project["inputs"]["m04"]["concept"]["tow_kg"]
        return tow * G / best["wingloading_pa"], depends, {"source": "M04 design point (W0 g / (W/S))",
                                                           "wing_loading_pa": best["wingloading_pa"], "tow_kg": tow}
    raise SystemExit("inputs.m09b.planform needs area_m2 or from_m04")


def evaluate(project: dict) -> tuple[dict, list]:
    d = prj.need_inputs(project, "m09b", ["planform"])
    pl = d["planform"]
    for key in ("aspect_ratio", "taper_ratio"):
        if key not in pl:
            raise SystemExit(f"inputs.m09b.planform is missing: {key}")
    s, depends, s_info = _area(project, d)
    pf = planform(s, pl["aspect_ratio"], pl["taper_ratio"], pl.get("sweep_le_deg"),
                  pl.get("sweep_c4_deg", 0.0 if pl.get("sweep_le_deg") is None else None))
    dihedral, washout = float(d.get("dihedral_deg", 0.0)), float(d.get("washout_deg", 0.0))
    mach = float(d.get("mach", 0.0))
    result = {"level": "conceptual", "units": "SI (m, m^2, deg)", "area_source": s_info, "planform": pf,
              "dihedral_deg": dihedral, "washout_deg": washout,
              "guidance": guidance(pf, d.get("wing_class"), dihedral, washout), "warnings": []}
    if dihedral:
        result["lift_dihedral_factor_cos2"] = math.cos(math.radians(dihedral)) ** 2       # Ec. 9-46
    ar = pf["aspect_ratio"]
    # --- sustentacion 3D ---
    foils, dep2 = _airfoil_data(project, d)
    depends += [x for x in dep2 if x not in depends]
    lift = {"cl_alpha_9_69_per_rad": cl_alpha_elliptic(ar), "cl_alpha_9_71_per_rad": cl_alpha_helmbold(ar)}
    if "root" in foils:
        cla2d = foils["root"].get("cl_alpha_per_rad") or 2.0 * math.pi
        lift["cl_alpha_2d_used_per_rad"] = cla2d
        lift["cl_alpha_9_73_per_rad"] = cl_alpha_helmbold(ar, cla2d)
        if mach <= 0.8:
            lift["cl_alpha_9_72_per_rad"] = cl_alpha_polhamus(ar, pf["sweep_c2_deg"], mach, cla2d)
            lift["cl_alpha_recommended_per_rad"] = lift["cl_alpha_9_72_per_rad"]
            lift["recommended_note"] = "Eq. 9-72: the book reports it agrees best with experiment and VLM (Table 9-7)"
    elif d.get("cl_alpha_2d_per_rad"):
        cla2d = d["cl_alpha_2d_per_rad"]
        lift["cl_alpha_2d_used_per_rad"] = cla2d
        lift["cl_alpha_9_72_per_rad"] = cl_alpha_polhamus(ar, pf["sweep_c2_deg"], mach, cla2d)
        lift["cl_alpha_recommended_per_rad"] = lift["cl_alpha_9_72_per_rad"]
    if "cl_alpha_recommended_per_rad" in lift and dihedral:
        lift["cl_alpha_with_dihedral_per_rad"] = lift["cl_alpha_recommended_per_rad"] * result["lift_dihedral_factor_cos2"]
    result["lift_curve_slope"] = lift
    result["airfoils"] = foils
    if "root" in foils and "tip" in foils and foils["root"].get("clmax") and foils["tip"].get("clmax"):
        m1 = clmax0_rapid(foils["root"]["clmax"], foils["tip"]["clmax"], pf["ymgc_m"], pf["span_m"])
        k_lambda = math.cos(math.radians(pf["sweep_c4_deg"]))                                   # Ec. 9-76
        dev = d.get("clmax_devices", {})
        dle, dte = float(dev.get("le", 0.0)), float(dev.get("te", 0.0))
        clmax = (m1["clmax0"] + dle + dte) * k_lambda                                         # Ec. 9-75 (agrupacion reconstruida)
        result["clmax"] = {**m1, "k_sweep": k_lambda, "delta_le": dle, "delta_te": dte, "clmax": clmax,
                           "method": "Method 1, rapid (Eqs. 9-77, 9-78); 'fair chance' for first estimates (GUD)",
                           "note": "Eq. 9-75 grouping reconstructed; identical for straight wings or without high-lift devices. "
                                   "Cl_max from XFOIL 2-D: Reynolds and surface-quality dependent; the book underestimates "
                                   "CL_max0 by 8-10 % for the Cessna 172 and SR22 with this method"}
        if "wing_loading_pa" in s_info or d.get("wing_loading_pa"):
            ws = d.get("wing_loading_pa", s_info.get("wing_loading_pa"))
            rho = float(d.get("density_kgm3", 1.225))
            vs = stall_speed_mps(ws, rho, clmax)
            result["stall"] = {"wing_loading_pa": ws, "density_kgm3": rho, "vs_mps": vs, "vs_kcas_approx": vs / 0.514444,
                               "note": "V_S = sqrt(2 (W/S) / (rho CL_max)) (Eq. 9-74); the KCAS value uses the given density"}
    # --- eficiencia de envergadura ---
    if "oswald_e" in d:
        e, e_src = float(d["oswald_e"]), "input"
    elif ar > 3.0 and pf["sweep_le_deg"] < 30.0:
        e, e_src = oswald_straight(ar), "Eq. 9-129 (Raymer, straight wing)"
    else:
        e, e_src = None, None
        result["warnings"].append("no span efficiency: Eq. 9-129 needs AR > 3 and a straight wing; the swept-wing Eq. 9-130 "
                                  "is illegible in the digital source (D-26): give inputs.m09b.oswald_e")
    if e:
        result["span_efficiency"] = {"e": e, "source": e_src, "k_induced": 1.0 / (math.pi * ar * e),
                                     "note": "Oswald e of the whole aircraft is lower than the wing-alone value; GUD Sec. 9.5.12"}
    # --- AR efectivo por alcance ---
    if "range_ar" in d:
        r = d["range_ar"]
        out = effective_ar_for_range(r["cl_cruise"], r["cd_min"], r["range_nm"], r["w_ini"], r["w_fin"], True,
                                     r["sfc_hp"], r["eta_p"])
        if out["feasible"] and e:
            out["required_oswald_e_for_planform_ar"] = out["effective_aspect_ratio"] / ar
        result["aspect_ratio_for_range"] = out
    # --- volumen interno ---
    if "volume" in d:
        v = d["volume"]
        y1, y2 = v["y1_m"], v["y2_m"]
        if y2 > pf["span_m"] / 2.0:
            raise SystemExit("inputs.m09b.volume.y2_m exceeds the semi-span")
        c1 = _chord_at(pf["root_chord_m"], pf["taper_ratio"], pf["span_m"], y1)
        c2 = _chord_at(pf["root_chord_m"], pf["taper_ratio"], pf["span_m"], y2)
        v_half = wing_volume_m3(c1, c2, y1, y2, v["t_over_c"], v["k"])
        frac = float(v.get("usable_fraction", 0.30))
        fuel_m3 = 2.0 * v_half * frac
        result["volume"] = {"y1_m": y1, "y2_m": y2, "chord_y1_m": c1, "chord_y2_m": c2, "volume_half_wing_m3": v_half,
                            "volume_both_m3": 2.0 * v_half, "usable_fraction": frac, "fuel_volume_m3": fuel_m3,
                            "fuel_volume_us_gal": fuel_m3 * 264.172,
                            "note": "usable_fraction 0.30 is the book's Example 9-3 value; a section-by-section tank layout replaces it"}
        if "fuel_density_kgm3" in v:
            result["volume"]["fuel_mass_kg"] = fuel_m3 * v["fuel_density_kgm3"]
    # --- archivos de intercambio flow5 ---
    if "flow5" in d:
        f5 = d["flow5"]
        if "root" not in foils or "tip" not in foils:
            raise SystemExit("inputs.m09b.flow5 needs airfoils root and tip (NACA xxxx ids)")
        cfg = flow5_config(pf, f5.get("name", project["name"] + " wing"), _naca_label(foils["root"]["id"]),
                           _naca_label(foils["tip"]["id"]), dihedral, washout, f5["analysis"], f5.get("nx", 13), f5.get("ny", 15))
        result["flow5_config"] = cfg
        result["flow5_status"] = ("config generated; run `aerosuite flow5-export` on it. flow5 NOT executed: "
                                  "pendiente de validacion con el motor real")
    return result, depends


def run(project: dict) -> dict:
    result, depends = evaluate(project)
    prj.record(project, "m09b", result, "conceptual", REFERENCES, depends)
    return result
