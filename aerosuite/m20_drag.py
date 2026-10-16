"""M20 Resistencia por componentes (Gudmundsson Tabla 1-4 paso 20; Cap. 16, Secs. 16.3.1 a 16.3.9 y 16.4).

Nivel conceptual. Metodo de acumulacion por componentes (CDBM, Sec. 16.3.5): C_Dmin = [ (1/S) sum C_f,j FF_j IF_j S_wet,j + C_Dmisc ] k_crud
(Ecs. 16-118 y 16-122), con C_f de capa limite mixta (metodo de Young, Ecs. 16-69/16-70) o turbulenta de Prandtl-Schlichting
(Ec. 16-43) y limite de Reynolds de corte (Ec. 16-31), factores de forma (Sec. 16.3.6), de interferencia (Tabla 16-12) y CRUD 25 %
(Sec. 16.3.8). La resistencia inducida usa k = 1/(pi AR e) con e de M09b (Sec. 9.5.12); C_D = C_Dmin + k C_L^2 (Ec. 16-141, sin onda ni
resistencia de compensacion). Aportes diversos (tren fijo, flaps, antenas...) entran como incrementos C_D,pi A_pi/S (Ec. 16-115) con
datos de entrada y su origen (Tabla 16-10 y Sec. 16.4): no se inventan. Contraste con flow5 7.55 real: C_D viscoso e inducido del modelo
ala-cola (pruebas). Resistencia de onda y compresibilidad (M > 0.3) quedan fuera. SI interno."""
import math

from . import project as prj

REFERENCES = [
    "GUD Sec. 16.3.1, Ecs. 16-40, 16-43 (Prandtl-Schlichting), 16-69/16-70 (Young, capa limite mixta), 16-71/16-72 (ponderacion por area mojada), 16-31 (Re de corte), Tabla 16-2 (rugosidad), PDF 726-733",
    "GUD Sec. 16.3.5, Ecs. 16-117, 16-118 y 16-122 (acumulacion por componentes), Tabla 16-10 (areas parasitas equivalentes), PDF 747-749",
    "GUD Sec. 16.3.6, Ecs. 16-123 a 16-135 (factores de forma: Hoerner, Torenbeek, Nicolai/Raymer, fuselaje) y Ejemplo 16-11 (FF del ala = 1.3111), PDF 750-752",
    "GUD Sec. 16.3.7, Tabla 16-12 (factores de interferencia), PDF 757",
    "GUD Sec. 16.3.8 (CRUD, k = 1.25) y 16.3.9, Ec. 16-141 (C_D = C_Dmin + C_Di + C_Dw), PDF 758",
    "GUD Ejemplos 16-6 (x0/c = 0.0729 para x_tr/c = 0.50, Re = 5 126 287) y 16-7 (C_f ponderado = 0.00554; C_Df = 0.01219), PDF 733-737",
    "PDF = marcador [p. N] del texto convertido (impreso = PDF - 46 en Gudmundsson, PDF - 13 en Etkin); +-1 pagina",
]
KT = 0.514444
FT = 0.3048
# Tabla 16-2: rugosidad kappa (pies) -> metros
ROUGHNESS_M = {"camouflage_paint_aluminum": 3.33e-5 * FT, "smooth_paint": 2.08e-5 * FT, "production_sheet_metal": 1.33e-5 * FT,
               "polished_sheet_metal": 0.50e-5 * FT, "smooth_molded_composite": 0.17e-5 * FT}
CRUD = 1.25
GAMMA_R = 287.05287
T0, RHO0 = 288.15, 1.225


def sutherland_mu(t_k: float) -> float:
    """Ec. 16-24: mu = 1.458e-6 T^1.5/(110.4 + T) [N s/m2]."""
    return 1.458e-6 * t_k ** 1.5 / (110.4 + t_k)


def cutoff_re(length_m: float, kappa_m: float, mach: float = 0.0) -> float:
    """Ec. 16-31 (subsonico): Re_cutoff = 38.21 (c/kappa)^1.053; Ec. 16-32 (transonico/supersonico): 44.62 (c/kappa)^1.053 M^1.16."""
    if mach > 1.0:
        return 44.62 * (length_m / kappa_m) ** 1.053 * mach ** 1.16
    return 38.21 * (length_m / kappa_m) ** 1.053


def cf_laminar(re: float) -> float:
    """Ec. 16-40 (promedio sobre la placa): 1.328/sqrt(Re)."""
    return 1.328 / math.sqrt(re)


def cf_turbulent(re: float) -> float:
    """Ec. 16-43 (Prandtl-Schlichting, promedio): 0.455/(log10 Re)^2.58."""
    return 0.455 / math.log10(re) ** 2.58


def cf_mixed_young(re: float, xtr_over_c: float) -> float:
    """Young (Ecs. 16-69 y 16-70): x0/c = 36.9 (xtr/c)^0.625 (1/Re)^0.375; Cf = 0.074/Re^0.2 (1 - (xtr/c - x0/c))^0.8, una superficie.
    xtr = 0 reproduce el caso turbulento de Prandtl (0.074/Re^0.2)."""
    if xtr_over_c <= 0.0:
        return 0.074 / re ** 0.2
    x0 = 36.9 * xtr_over_c ** 0.625 * (1.0 / re) ** 0.375
    return 0.074 / re ** 0.2 * (1.0 - (xtr_over_c - x0)) ** 0.8


def fictitious_origin(re: float, xtr_over_c: float) -> float:
    return 36.9 * xtr_over_c ** 0.625 * (1.0 / re) ** 0.375


def skin_friction(re: float, length_m: float, kappa_m: float, xtr_upper: float = 0.0, xtr_lower: float = 0.0, mach: float = 0.0,
                  model: str = "mixed") -> dict:
    """C_f medio de un perfil/cuerpo: promedio de superficies superior e inferior, con Re limitado por el de corte (Sec. 16.3.1 (6))."""
    cut = cutoff_re(length_m, kappa_m, mach)
    re_a = min(re, cut)
    if model == "turbulent":
        c_u = c_l = cf_turbulent(re_a)
    else:
        c_u, c_l = cf_mixed_young(re_a, xtr_upper), cf_mixed_young(re_a, xtr_lower)
    return {"re": re, "re_cutoff": cut, "re_used": re_a, "cf_upper": c_u, "cf_lower": c_l, "cf": 0.5 * (c_u + c_l)}


def ff_wing_nicolai(tc: float, xc_max: float, mach: float, sweep_tmax_deg: float = 0.0) -> float:
    """Ec. 16-127 (Nicolai/Raymer): FF = [1 + 0.6/(x/c)max (t/c) + 100 (t/c)^4] [1.34 M^0.18 (cos Lambda_tmax)^0.28]; la correccion
    de compresibilidad se omite para M < 0.2 (texto de la Sec. 16.3.6). Reproduce 1.3111 del Ejemplo 16-11 (t/c 0.15, x/c max 0.5, M 0.28)."""
    base = 1.0 + 0.6 / xc_max * tc + 100.0 * tc ** 4
    if mach < 0.2:
        return base
    return base * (1.34 * mach ** 0.18 * math.cos(math.radians(sweep_tmax_deg)) ** 0.28)


def ff_wing_hoerner(tc: float, xc_max: float = 0.3) -> float:
    """Hoerner: (x/c)max = 0.30: 1 + 2 t/c + 60 (t/c)^4; (x/c)max = 0.40-0.50: 1 + 1.2 t/c + 70 (t/c)^4 (Sec. 16.3.6 (1))."""
    return 1.0 + 2.0 * tc + 60.0 * tc ** 4 if xc_max <= 0.35 else 1.0 + 1.2 * tc + 70.0 * tc ** 4


def ff_fuselage(f: float, model: str = "torenbeek") -> float:
    """Sec. 16.3.6 (2): f = l/d. Hoerner (16-133): 1 + 1.5 f^-1.5 + 7 f^-3; Torenbeek (16-134): 1 + 2.2 f^-1.5 + 3.8 f^-3;
    Nicolai/Raymer (16-135): 1 + 60/f^3 + f/400; Jenkinson: 1 + 2.2 f^-1.5 - 0.9 f^-3."""
    if model == "hoerner":
        return 1.0 + 1.5 * f ** -1.5 + 7.0 * f ** -3
    if model == "torenbeek":
        return 1.0 + 2.2 * f ** -1.5 + 3.8 * f ** -3
    if model == "nicolai":
        return 1.0 + 60.0 / f ** 3 + f / 400.0
    if model == "jenkinson":
        return 1.0 + 2.2 * f ** -1.5 - 0.9 * f ** -3
    raise ValueError("unknown fuselage form factor model")


def ff_nacelle(f: float) -> float:
    """Raymer, Ec. 16-140: FF = 1 + 0.35/f."""
    return 1.0 + 0.35 / f


def isa(altitude_m: float) -> dict:
    """ISA troposfera (hasta 11 km): T, rho, a, mu."""
    t = T0 - 0.0065 * altitude_m
    p = 101325.0 * (t / T0) ** 5.25588
    rho = p / (GAMMA_R * t)
    return {"t_k": t, "rho": rho, "a": math.sqrt(1.4 * GAMMA_R * t), "mu": sutherland_mu(t)}


def misc_increment(cd_pi: float, a_pi_m2: float, s_ref_m2: float) -> float:
    """Ec. 16-115 / 16-143: Delta C_D = C_D,pi A_pi / S (el coeficiente se refiere al area de la fuente)."""
    return cd_pi * a_pi_m2 / s_ref_m2


def cdmin_buildup(components, s_ref, misc=0.0, k_crud=CRUD) -> dict:
    """Ecs. 16-118 y 16-122: C_Dmin = [ (1/S) sum C_f FF IF S_wet + C_Dmisc ] k_crud."""
    rows = []
    total = 0.0
    for c in components:
        term = c["cf"] * c["ff"] * c.get("if", 1.0) * c["s_wet_m2"]
        rows.append({**c, "cf_ff_if_swet_m2": term, "cd_contribution": term / s_ref})
        total += term
    cd1 = total / s_ref
    return {"components": rows, "cd_friction_form": cd1, "cd_misc": misc, "k_crud": k_crud, "cd_min": (cd1 + misc) * k_crud,
            "equivalent_flat_plate_area_m2": (cd1 + misc) * k_crud * s_ref}


# --------------------------------------------------------------------------- modulo
def _component(name, kind, d, re_len, mu_info, mach, kappa):
    """Calcula C_f, FF y S_wet de un componente a partir de sus datos (`d`) y devuelve el renglon del buildup."""
    out = {"name": name, "kind": kind}
    sf = skin_friction(re_len, d["ref_length_m"], kappa, d.get("xtr_upper", 0.0), d.get("xtr_lower", 0.0), mach, d.get("cf_model", "mixed"))
    out.update({"cf": sf["cf"], "cf_detail": sf, "s_wet_m2": d["s_wet_m2"], "if": d.get("interference", 1.0), "reference_length_m": d["ref_length_m"]})
    if kind == "wing_like":
        out["ff"] = ff_wing_nicolai(d["t_over_c"], d.get("xc_max", 0.4), mach, d.get("sweep_tmax_deg", 0.0)) if d.get("ff_model", "nicolai") == "nicolai" \
            else ff_wing_hoerner(d["t_over_c"], d.get("xc_max", 0.3))
    elif kind == "fuselage":
        out["ff"] = ff_fuselage(d["length_m"] / d["diameter_m"], d.get("ff_model", "torenbeek"))
    elif kind == "nacelle":
        out["ff"] = ff_nacelle(d["length_m"] / d["diameter_m"])
    else:
        raise SystemExit(f"unknown component kind '{kind}'")
    return out


def evaluate(project: dict) -> tuple[dict, list]:
    d = prj.need_inputs(project, "m20", ["flight", "surface"])
    w = project["outputs"].get("m09b")
    t = project["outputs"].get("m08")
    if not w or not t:
        raise SystemExit("outputs.m09b and outputs.m08 are missing: run m09b and m08 first")
    wing, tails = w["result"], t["result"]
    pf = wing["planform"]
    s_ref = pf["area_m2"]
    fl = d["flight"]
    atm = isa(fl.get("altitude_m", 0.0))
    v = fl["speed_mps"]
    mach = v / atm["a"]
    kappa = ROUGHNESS_M[d["surface"]]
    res = {"level": "conceptual", "units": "SI", "assumptions": [], "flight": {"speed_mps": v, "mach": mach, "rho": atm["rho"], "mu": atm["mu"],
                                                                         "altitude_m": fl.get("altitude_m", 0.0), "q_pa": 0.5 * atm["rho"] * v * v}}
    if mach > 0.3:
        res["assumptions"].append("M > 0.3: the compressibility corrections of Eqs. 16-60 onward are not applied")
    boost = d.get("wetted_booster", 1.07)
    res["assumptions"].append(f"wing/tail wetted area = 2 S_exposed x {boost} (GUD Example 16-6 assumes 7 % over the planform)")
    comps = []
    wd = d.get("wing", {})
    c_r, c_t = pf["root_chord_m"], pf["tip_chord_m"]
    # ala: Cf en cuerda de raiz y de punta, ponderado por la cuerda (area mojada proporcional)
    s_exposed = wd.get("exposed_area_m2", s_ref)
    ww = {"s_wet_m2": 2.0 * s_exposed * boost, "t_over_c": wd["t_over_c"], "xc_max": wd.get("xc_max", 0.4), "sweep_tmax_deg": wd.get("sweep_tmax_deg", 0.0),
          "xtr_upper": wd.get("xtr_upper", 0.0), "xtr_lower": wd.get("xtr_lower", 0.0), "interference": wd.get("interference", 1.0),
          "cf_model": wd.get("cf_model", "mixed"), "ff_model": wd.get("ff_model", "nicolai")}
    re_r, re_t = atm["rho"] * v * c_r / atm["mu"], atm["rho"] * v * c_t / atm["mu"]
    cr = _component("wing(root)", "wing_like", {**ww, "ref_length_m": c_r, "s_wet_m2": 0.0}, re_r, atm, mach, kappa)
    ct = _component("wing(tip)", "wing_like", {**ww, "ref_length_m": c_t, "s_wet_m2": 0.0}, re_t, atm, mach, kappa)
    cf_w = (cr["cf"] * c_r + ct["cf"] * c_t) / (c_r + c_t)
    comps.append({"name": "wing", "kind": "wing_like", "cf": cf_w, "ff": cr["ff"], "if": ww["interference"], "s_wet_m2": ww["s_wet_m2"],
                  "cf_root": cr["cf"], "cf_tip": ct["cf"], "note": "C_f averaged root/tip weighted by chord"})
    for key, name in (("horizontal_tail", "ht"), ("vertical_tail", "vt")):
        td = d.get(name)
        if not td:
            res["assumptions"].append(f"{name} skipped: no inputs.m20.{name}")
            continue
        surf = tails[key]
        ref = surf["average_chord_m"]
        row = _component(name, "wing_like", {"ref_length_m": ref, "s_wet_m2": 2.0 * surf["area_m2"] * boost, "t_over_c": td["t_over_c"], "xc_max": td.get("xc_max", 0.3),
                                             "sweep_tmax_deg": td.get("sweep_tmax_deg", 0.0), "xtr_upper": td.get("xtr_upper", 0.0),
                                             "xtr_lower": td.get("xtr_lower", 0.0), "interference": td.get("interference", 1.05),
                                             "cf_model": td.get("cf_model", "mixed"), "ff_model": td.get("ff_model", "nicolai")},
                         atm["rho"] * v * ref / atm["mu"], atm, mach, kappa)
        comps.append(row)
    fd = d.get("fuselage")
    if not fd:
        raise SystemExit("inputs.m20.fuselage {length_m, diameter_m, s_wet_m2} is required")
    comps.append(_component("fuselage", "fuselage", {"ref_length_m": fd["length_m"], "length_m": fd["length_m"], "diameter_m": fd["diameter_m"], "s_wet_m2": fd["s_wet_m2"],
                                                     "xtr_upper": fd.get("xtr_upper", 0.0), "xtr_lower": fd.get("xtr_lower", 0.0), "interference": fd.get("interference", 1.0),
                                                     "cf_model": fd.get("cf_model", "mixed"), "ff_model": fd.get("ff_model", "torenbeek")},
                            atm["rho"] * v * fd["length_m"] / atm["mu"], atm, mach, kappa))
    for nd in d.get("nacelles", []):
        comps.append(_component(nd.get("name", "nacelle"), "nacelle", {**nd, "ref_length_m": nd["length_m"]}, atm["rho"] * v * nd["length_m"] / atm["mu"], atm, mach, kappa))
    misc_rows, misc = [], 0.0
    for m in d.get("misc", []):
        inc = misc_increment(m["cd_pi"], m["a_pi_m2"], s_ref)
        misc_rows.append({**m, "delta_cd": inc})
        misc += inc
    if not d.get("misc"):
        res["assumptions"].append("no miscellaneous drag (landing gear, antennas, flaps...): give inputs.m20.misc [{name, cd_pi, a_pi_m2, source}] (Sec. 16.4, Table 16-10)")
    bu = cdmin_buildup(comps, s_ref, misc, d.get("k_crud", CRUD))
    if "k_crud" not in d:
        res["assumptions"].append("k_crud = 1.25 (typical 25 %, Sec. 16.3.8); an aircraft-specific value should come from comparing similar aircraft")
    k = wing["span_efficiency"]["k_induced"]
    res["buildup"] = bu
    res["misc"] = misc_rows
    res["induced"] = {"k": k, "e": wing["span_efficiency"]["e"], "source": wing["span_efficiency"]["source"]}
    cdmin = bu["cd_min"]
    cl_g = d.get("polar_cl", [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2])
    res["polar"] = [{"cl": c, "cd": cdmin + k * c * c, "l_over_d": (c / (cdmin + k * c * c)) if c > 0 else 0.0} for c in cl_g]
    cl_opt = math.sqrt(cdmin / k)
    res["optimum"] = {"cl_best_ld": cl_opt, "ld_max": 0.5 / math.sqrt(cdmin * k), "cd_at_best_ld": 2.0 * cdmin,
                      "cl_min_power": math.sqrt(3.0 * cdmin / k)}
    res["note_polar"] = "C_D = C_Dmin + k C_L^2 (Eq. 16-141 without wave or trim drag); k from M09b (whole-aircraft Oswald e is lower than the wing-alone value)"
    return res, ["m09b", "m08"]


def run(project: dict) -> dict:
    result, depends = evaluate(project)
    prj.record(project, "m20", result, "conceptual", REFERENCES, sorted(set(depends)))
    return result
