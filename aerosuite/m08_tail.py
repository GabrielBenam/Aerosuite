"""M08 Cola inicial (Gudmundsson Tabla 1-4 paso 8; Sec. 11.2.2 y 11.4, Ecs. 11-5, 11-6, 11-14 a 11-33).

Nivel conceptual. A partir de los coeficientes de volumen V_HT y V_VT (Tabla 11-4 o dados) y de la geometria
del ala, calcula el brazo de cola que minimiza el area mojada del fuselaje trasero mas las colas (Metodos 1 a 3,
fuselaje tronco-conico; Metodo 4, perfil de fuselaje cuadratico con integral numerica) y de ahi las areas y
dimensiones de HT y VT. No estima estabilidad ni maniobrabilidad: V_HT y V_VT son datos historicos de partida.
Las ecuaciones son homogeneas en longitud: se evaluan en SI (m, m^2).
"""
import math

from scipy.optimize import minimize_scalar

from . import project as prj

G = 9.80665
REFERENCES = [
    "GUD Sec. 11.2.2, Ecs. 11-5 y 11-6 (volumenes de cola), PDF 530 / impr. 485",
    "GUD Sec. 11.4.1, Tabla 11-4 (V_HT y V_VT por clase), PDF 550 / impr. 505",
    "GUD Sec. 11.4.3-11.4.4, Ecs. 11-14 a 11-26 (brazo optimo, Metodo 1), PDF 555 / impr. 510",
    "GUD Ejemplos 11-1 y 11-2, Ec. 11-27 (Metodo 2), PDF 556 / impr. 511",
    "GUD Sec. 11.4.6, Ec. 11-28 y Ejemplo 11-3 (Metodo 3), PDF 557 / impr. 512",
    "GUD Sec. 11.4.7, Ecs. 11-29 a 11-35 (Metodo 4, fuselaje arbitrario), PDF 558-560 / impr. 513-515",
    "GUD Sec. 9.2.2, Ecs. 9-3, 9-8 a 9-13 (planta trapezoidal) y 9-28 a 9-29, PDF 369-371 / impr. 324-326",
]

# Tabla 11-4 (GUD PDF 550, leida de la figura): clase -> (V_HT, V_VT)
TAIL_VOLUMES = {
    "sailplane": (0.50, 0.02),
    "homebuilt": (0.50, 0.04),
    "ga_single_engine": (0.70, 0.04),
    "ga_twin_engine": (0.80, 0.07),
    "agricultural": (0.50, 0.04),
    "twin_turboprop": (0.90, 0.08),
    "flying_boat": (0.70, 0.06),
    "jet_trainer": (0.70, 0.06),
    "jet_fighter": (0.40, 0.07),
    "military_cargo_bomber": (1.00, 0.08),
    "jet_transport": (1.00, 0.09),
}


def trapezoid(s_m2: float, ar: float, taper: float = 1.0) -> dict:
    """Planta trapezoidal desde S, AR y lambda (Ecs. 9-28, 9-29, 9-11 a 9-13): b, c_r, c_t, c_MGC, y_MGC (m)."""
    if s_m2 <= 0 or ar <= 0 or not 0.0 < taper <= 1.0:
        raise ValueError("S and AR must be positive and 0 < taper <= 1")
    b = math.sqrt(ar * s_m2)
    c_r = 2.0 * s_m2 / (b * (1.0 + taper))
    return {"span_m": b, "root_chord_m": c_r, "tip_chord_m": taper * c_r, "average_chord_m": s_m2 / b,
            "cmgc_m": 2.0 / 3.0 * c_r * (1.0 + taper + taper ** 2) / (1.0 + taper),
            "ymgc_m": b / 6.0 * (1.0 + 2.0 * taper) / (1.0 + taper)}


def tail_arm_ht(v_ht, s, cmgc, r1, r2):
    """Ec. 11-26 (Metodo 1): brazo que minimiza S_wet = pi (R1+R2) l + 2 V_HT S c_MGC / l."""
    return math.sqrt(2.0 * v_ht * s * cmgc / (math.pi * (r1 + r2)))


def tail_arm_vt(v_vt, s, b, r1, r2):
    """Ec. 11-27 (Metodo 2)."""
    return math.sqrt(2.0 * v_vt * s * b / (math.pi * (r1 + r2)))


def tail_arm_combined(v_ht, v_vt, s, cmgc, b, r1, r2):
    """Ec. 11-28 (Metodo 3): un solo brazo para HT y VT."""
    return math.sqrt(2.0 * s * (v_ht * cmgc + v_vt * b) / (math.pi * (r1 + r2)))


def surface_from_volume(volume: float, s: float, reference: float, arm: float) -> float:
    """Ecs. 11-20 y 11-23: S_HT = V_HT S c_MGC / l_HT ; S_VT = V_VT S b / l_VT."""
    return volume * s * reference / arm


def quadratic_profile(r1: float, r2: float, l_t: float, theta1_deg=None, theta2_deg=None):
    """Coeficientes (a, b, c) de y = a x^2 + b x + c con y(0) = R1, y(l_T) = R2 y una pendiente dada:
    theta1 en x = 0 (Ec. 11-31) o theta2 en x = l_T (Ec. 11-33)."""
    if (theta1_deg is None) == (theta2_deg is None):
        raise ValueError("give exactly one of theta1_deg (slope at x=0) or theta2_deg (slope at x=l_T)")
    if theta1_deg is not None:
        t = math.tan(math.radians(theta1_deg))
        return (r2 - r1 - l_t * t) / l_t ** 2, t, r1
    t = math.tan(math.radians(theta2_deg))
    return (r1 - r2 + l_t * t) / l_t ** 2, (2.0 * r2 - 2.0 * r1 - l_t * t) / l_t, r1


def aft_fuselage_wetted_area(a: float, b: float, c: float, l_t: float, n: int = 400) -> float:
    """Ec. 11-17 en forma numerica (Ecs. 11-34, 11-35: troncos de cono sobre N segmentos)."""
    xs = [l_t * i / n for i in range(n + 1)]
    ys = [a * x * x + b * x + c for x in xs]
    if min(ys) <= 0.0:
        raise ValueError("fuselage profile radius is not positive over the tail section")
    return sum(math.pi * (ys[i] + ys[i - 1]) * math.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1])
               for i in range(1, n + 1))


def tail_arm_arbitrary_fuselage(v_ht, v_vt, s, cmgc, b, r1, r2, theta1_deg=None, theta2_deg=None, search_m=None):
    """Metodo 4: minimiza S_wet(l) = S_wet_FUS(l) + 2 V_HT S c_MGC / l + 2 V_VT S b / l (Ecs. 11-14, 11-18, 11-19).
    El perfil de fuselaje se rehace para cada l_T con las mismas R1, R2 y pendiente. `search_m` = intervalo de
    busqueda (dato de entrada: el libro barre l_T en una hoja de calculo sin fijar el intervalo)."""
    lo, hi = search_m if search_m else (0.25 * b, 1.5 * b)

    def swet(l):
        a_, b_, c_ = quadratic_profile(r1, r2, l, theta1_deg, theta2_deg)
        return aft_fuselage_wetted_area(a_, b_, c_, l) + 2.0 * s * (v_ht * cmgc + v_vt * b) / l

    res = minimize_scalar(swet, bounds=(lo, hi), method="bounded", options={"xatol": 1e-6})
    at_edge = min(res.x - lo, hi - res.x) < 1e-3 * (hi - lo)
    return res.x, swet(res.x), at_edge


def _tail_surface(volume, s, reference, arm, ar, taper):
    area = surface_from_volume(volume, s, reference, arm)
    geo = trapezoid(area, ar, taper)           # Ec. 11-21/11-24 (b = sqrt(AR S)); AR_VT = b_VT^2/S_VT (Ec. 9-17)
    return {"area_m2": area, "arm_m": arm, "aspect_ratio": ar, "taper_ratio": taper, **geo, "wetted_area_approx_m2": 2.0 * area}


def _wing(project: dict, d: dict):
    """Geometria del ala: dada, o derivada del punto de diseno de M04 con AR y lambda (dependencia M04/M06)."""
    if "wing" in d:
        w = d["wing"]
        for k in ("area_m2", "span_m", "cmgc_m"):
            if k not in w:
                raise SystemExit(f"inputs.m08.wing is missing: {k}")
        return dict(w), []
    if d.get("wing_from_m09b"):
        if "m09b" not in project["outputs"]:
            raise SystemExit("inputs.m08.wing_from_m09b is set but outputs.m09b is missing: run m09b first")
        pf = project["outputs"]["m09b"]["result"]["planform"]
        return {"area_m2": pf["area_m2"], "span_m": pf["span_m"], "cmgc_m": pf["cmgc_m"], "aspect_ratio": pf["aspect_ratio"],
                "taper_ratio": pf["taper_ratio"], "source": "M09b planform"}, ["m09b"]
    src = d.get("wing_from_m04")
    if not src:
        raise SystemExit("inputs.m08 needs 'wing' {area_m2, span_m, cmgc_m}, 'wing_from_m09b' or 'wing_from_m04' {aspect_ratio, taper_ratio}")
    if "m04" not in project["outputs"]:
        raise SystemExit("inputs.m08.wing_from_m04 is set but outputs.m04 is missing: run m04 first")
    depends = ["m04"]
    best = project["outputs"]["m04"]["result"].get("best_sample")
    if not best:
        raise SystemExit("outputs.m04 has no admissible design point")
    if "m06" in project["outputs"] and project["inputs"].get("m04", {}).get("tow_from_m06"):
        tow, depends = project["outputs"]["m06"]["result"]["w0_kg"], ["m04", "m06"]
    else:
        tow = project["inputs"]["m04"]["concept"]["tow_kg"]
    s = tow * G / best["wingloading_pa"]
    geo = trapezoid(s, src["aspect_ratio"], src.get("taper_ratio", 1.0))
    return {"area_m2": s, **geo, "aspect_ratio": src["aspect_ratio"], "taper_ratio": src.get("taper_ratio", 1.0),
            "source": "M04 design point (W0 g / (W/S))", "wing_loading_pa": best["wingloading_pa"], "tow_kg": tow}, depends


def evaluate(project: dict) -> tuple[dict, list]:
    d = prj.need_inputs(project, "m08", ["volumes", "fuselage"])
    wing, depends = _wing(project, d)
    s, b, c = wing["area_m2"], wing["span_m"], wing["cmgc_m"]
    vol = d["volumes"]
    if "class" in vol:
        if vol["class"] not in TAIL_VOLUMES:
            raise SystemExit(f"inputs.m08.volumes.class must be one of {', '.join(TAIL_VOLUMES)}")
        v_ht, v_vt = TAIL_VOLUMES[vol["class"]]
        vol_source = f"Tabla 11-4, clase {vol['class']}"
    else:
        v_ht, v_vt, vol_source = vol["vht"], vol["vvt"], "dato de entrada"
    fus = d["fuselage"]
    r1, r2 = fus["r1_m"], fus["r2_m"]
    method = d.get("method", 3)
    ar_ht, ar_vt = d.get("ar_ht", 3.0), d.get("ar_vt", 1.35)
    lam_ht, lam_vt = d.get("taper_ht", 1.0), d.get("taper_vt", 1.0)
    warn = []
    if "arms_m" in d:                       # brazos dados por el usuario: sin optimizacion
        l_ht, l_vt, method = d["arms_m"]["l_ht"], d["arms_m"]["l_vt"], "given"
    elif method == 1:
        l_ht = tail_arm_ht(v_ht, s, c, r1, r2)
        l_vt = l_ht
    elif method == 2:
        l_vt = tail_arm_vt(v_vt, s, b, r1, r2)
        l_ht = l_vt
    elif method == 3:
        l_ht = l_vt = tail_arm_combined(v_ht, v_vt, s, c, b, r1, r2)
    elif method == 4:
        l_ht, swet, at_edge = tail_arm_arbitrary_fuselage(v_ht, v_vt, s, c, b, r1, r2, fus.get("theta1_deg"),
                                                          fus.get("theta2_deg"), fus.get("search_m"))
        l_vt = l_ht
        if at_edge:
            warn.append("the optimum tail arm is at the edge of the search interval: widen inputs.m08.fuselage.search_m")
    else:
        raise SystemExit("inputs.m08.method must be 1, 2, 3 or 4 (or give arms_m)")
    if method == 1:
        warn.append("Method 1 sizes only the HT; the VT uses the same arm (the book leaves the VT arm to another method)")
    if method == 2:
        warn.append("Method 2 sizes only the VT; the HT uses the same arm (the book leaves the HT arm to another method)")
    for key, val in (("ar_ht", ar_ht), ("ar_vt", ar_vt)):
        if key not in d:
            prj.add_assumption(project, "m08", key, val, "supuesto: valor del Ejemplo 11-1/11-2 de GUD (Cessna 172); el libro no fija "
                               "un AR de cola por clase. Dar el dato en inputs.m08")
    ht = _tail_surface(v_ht, s, c, l_ht, ar_ht, lam_ht)
    vt = _tail_surface(v_vt, s, b, l_vt, ar_vt, lam_vt)
    l_t = max(l_ht, l_vt)
    result = {"level": "conceptual", "units": "SI (m, m^2)", "method": method, "volumes": {"vht": v_ht, "vvt": v_vt,
              "source": vol_source}, "wing": wing, "fuselage_tail_section": {"r1_m": r1, "r2_m": r2},
              "horizontal_tail": ht, "vertical_tail": vt,
              "wetted_area_estimate_m2": (math.pi * (r1 + r2) * l_t + ht["wetted_area_approx_m2"]
                                          + vt["wetted_area_approx_m2"]) if method in (1, 2, 3, "given") else None,
              "ratios": {"s_ht_over_s": ht["area_m2"] / s, "s_vt_over_s": vt["area_m2"] / s},
              "warnings": warn,
              "note": "V_HT and V_VT are historical starting values (Table 11-4); stability and control are not evaluated here"}
    return result, depends


def run(project: dict) -> dict:
    result, depends = evaluate(project)
    prj.record(project, "m08", result, "conceptual", REFERENCES, depends)
    return result
