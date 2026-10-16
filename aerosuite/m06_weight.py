"""M06 Peso inicial y misión (Gudmundsson Tabla 1-4 paso 6; Sec. 6.2, métodos 1 a 3 y eléctrico).

Nivel conceptual. Cuatro métodos de peso bruto inicial:
  historical_ratios  Método 1, Ec. 6-9:  W0 = (Wc + Wp) / (1 - We/W0 - Wf/W0)
  empty_fraction     Método 2, Ecs. 6-16 a 6-24: We/W0 = A + B ln W0 para W0 conocido
  mission            Método 3, Ecs. 6-25 a 6-42 y 6-29: cadena de fracciones de peso por segmento + We/W0 histórica
  electric           Ecs. 6-12 y 6-13 (Hepperle): masa bruta y L/D mínimo de una aeronave de baterías
Los coeficientes del libro son dimensionales (SFC en 1/h o lbf/(h·hp), distancias en nm, velocidades en KTAS,
altitudes en ft, tasas en fpm). Los pesos de las ecuaciones de fracción de peso son homogéneos: las funciones del
núcleo trabajan en la unidad de peso que reciba la regresión (lbf con A_lbf, kg con A_kg). project.json usa kg.
"""
import math

from . import project as prj

LBF_PER_KG = 2.2046226218
G0 = 9.807
REFERENCES = [
    "GUD Sec. 6.2.1 Método 1, Ec. 6-9 y Ejemplo 6-2, PDF 195-196 / impr. 150-151",
    "GUD Sec. 6.2.2 Método 2, Ecs. 6-16 a 6-24, PDF 197-198 / impr. 152-153",
    "GUD Sec. 6.2.3 Método 3, Ecs. 6-25 a 6-42 y Ejemplo 6-4, PDF 198-204 / impr. 153-159",
    "GUD Ecs. 6-10 a 6-15 y Ejemplo 6-3 (aeronave eléctrica), PDF 197 / impr. 152",
]

# Tabla de la Sec. 6.2.2: clase -> (n aeronaves, A_lbf, B, A_kg). B es común a ambas unidades.
EMPTY_WEIGHT_FRACTION = {
    "sailplane": (35, 0.2950, 0.0386, 0.3255),
    "powered_sailplane": (13, 0.3068, 0.0510, 0.3471),
    "lsa_land": (35, 1.5451, -0.1402, 1.4343),
    "lsa_amphibian": (None, 1.6351, -0.1402, 1.5243),
    "ga_single_engine": (86, 0.8841, -0.0333, 0.8578),
    "ga_twin_piston": (12, 0.4074, 0.0253, 0.4274),
    "ga_twin_turboprop": (28, 0.5319, 0.0066, 0.5371),
    "agricultural": (5, 1.4029, -0.0995, 1.3242),
    "business_jet": (72, 0.9038, -0.03163, 0.8788),
}


# ---------------------------------------------------------------- Método 1
def gross_weight_historical(w_crew, w_payload, we_w0, wf_w0) -> dict:
    """Ec. 6-9. Falla si la suma de razones deja un crecimiento infinito (We/W0 + Wf/W0 >= 1)."""
    if not (0.0 < we_w0 < 1.0 and 0.0 <= wf_w0 < 1.0) or we_w0 + wf_w0 >= 1.0:
        raise ValueError("We/W0 + Wf/W0 must be < 1 (the growth factor would not be finite)")
    k = 1.0 / (1.0 - we_w0 - wf_w0)
    w0 = k * (w_crew + w_payload)
    return {"w0": w0, "we": we_w0 * w0, "wf": wf_w0 * w0, "growth_factor": k}


# ---------------------------------------------------------------- Método 2
def empty_weight_fraction(cls: str, w0: float, unit: str = "kg") -> float:
    if cls not in EMPTY_WEIGHT_FRACTION:
        raise ValueError(f"class must be one of {sorted(EMPTY_WEIGHT_FRACTION)}")
    if unit not in ("kg", "lbf"):
        raise ValueError("unit must be 'kg' or 'lbf'")
    _n, a_lbf, b, a_kg = EMPTY_WEIGHT_FRACTION[cls]
    return (a_kg if unit == "kg" else a_lbf) + b * math.log(w0)


# ---------------------------------------------------------------- Método 3
def segment_ratio(seg: dict, w_start_over_w0: float = 1.0) -> float:
    """W_i/W_{i-1} de un segmento (Ecs. 6-32 a 6-42). Unidades del libro (ver docstring del módulo).

    Campos comunes: type, engine ('jet'|'prop'), sfc (1/h para jets, lbf/(h hp) para hélices), eta_p, ld.
    Empuje o potencia por segmento: `r` (jet) o `p` (hélice) fijo, o `r_ref`/`p_ref` = Tmax/W0 (o Pmax/W0) que se
    escala con el peso al inicio del segmento (Ec. 6-30/6-31: r_i = r_ref * W0/W_{i-1}).
    """
    kind, engine = seg["type"], seg.get("engine", "jet")
    sfc = seg.get("sfc")
    if engine not in ("jet", "prop"):
        raise ValueError("engine must be 'jet' or 'prop'")

    def load(name):
        if f"{name}_ref" in seg:
            return seg[f"{name}_ref"] / w_start_over_w0
        return seg[name]

    sym = "r" if engine == "jet" else "p"
    if kind == "fixed":
        return float(seg["ratio"])
    if kind == "taxi_takeoff":
        if seg.get("typical", False):                                                  # Ec. 6-33
            return 1.0 - (0.015 if engine == "jet" else 0.004) * sfc
        return 1.0 - (seg["t_taxi_h"] * seg[f"{sym}_idle"] + seg["t_max_h"] * seg[f"{sym}_max"]) * sfc   # Ec. 6-32
    if kind in ("climb", "descent"):                                                   # Ecs. 6-34 y 6-39
        rate = seg["roc_fpm"] if kind == "climb" else seg["rod_fpm"]
        return 1.0 - seg["delta_h_ft"] * sfc * load(sym) / (60.0 * rate)
    if kind == "cruise":                                                                # Ecs. 6-35 y 6-37
        if engine == "jet":
            return math.exp(-seg["range_nm"] * sfc / (seg["v_ktas"] * seg["ld"]))
        return math.exp(-seg["range_nm"] * sfc / (325.9 * seg["eta_p"] * seg["ld"]))
    if kind in ("loiter", "reserve"):                                                   # Ecs. 6-36, 6-38, 6-40, 6-41
        if engine == "jet":
            return math.exp(-seg["time_h"] * sfc / seg["ld"])
        return math.exp(-seg["v_ktas"] * seg["time_h"] * sfc / (325.9 * seg["eta_p"] * seg["ld"]))
    raise ValueError(f"unknown segment type {kind!r}")


def mission_fractions(segments: list[dict]) -> dict:
    """Producto de las fracciones (Ec. 6-26) y detalle por nodo."""
    ratios, cum = [], 1.0
    for seg in segments:
        r = segment_ratio(seg, cum)
        if not (0.0 < r <= 1.0 + 1e-12):
            raise ValueError(f"segment {seg.get('name', seg['type'])!r} gives weight ratio {r:.4f}: not in (0, 1]")
        cum *= r
        ratios.append({"name": seg.get("name", seg["type"]), "ratio": r, "cumulative": cum})
    return {"segments": ratios, "wn_over_w0": cum}


def gross_weight_mission(segments: list[dict], a: float, b: float, w_crew: float, w_payload: float) -> dict:
    """Resuelve la Ec. 6-29: A + B ln W0 + (Wc + Wp)/W0 - WN/W0 = 0. a y b deben corresponder a la unidad de peso
    de w_crew y w_payload (A_lbf con lbf, A_kg con kg)."""
    fr = mission_fractions(segments)
    wn = fr["wn_over_w0"]
    fixed = w_crew + w_payload

    def f(w0):
        return a + b * math.log(w0) + fixed / w0 - wn

    grid = [fixed * 1.001 * 10 ** (k / 40.0) for k in range(0, 40 * 4 + 1)]   # fixed ... 10^4 * fixed
    root = None
    for lo, hi in zip(grid, grid[1:]):
        if f(lo) * f(hi) <= 0.0:
            from scipy.optimize import brentq
            root = brentq(f, lo, hi, xtol=1e-10, rtol=1e-14)
            break
    if root is None:
        raise ValueError("Eq. 6-29 has no solution between 1x and 10^4x of (Wc+Wp): the mission cannot close with "
                         "this empty-weight relation (weight growth diverges)")
    we_w0 = a + b * math.log(root)
    return {"w0": root, "we_w0": we_w0, "we": we_w0 * root, "wn_over_w0": wn,
            "fuel_weight": root * (1.0 - wn), "mission": fr["segments"], "residual": f(root)}


# ---------------------------------------------------------------- Eléctrico
def electric_gross_mass(m_crew_payload_kg, we_m0, range_km, e_wh_kg, eta_tot, ld_c) -> dict:
    """Ec. 6-12. Devuelve la masa bruta y el L/D mínimo (Ec. 6-13)."""
    ld_min = range_km * G0 / (3.6 * (1.0 - we_m0) * e_wh_kg * eta_tot)
    denom = 1.0 - we_m0 - G0 * range_km / (3.6 * e_wh_kg * eta_tot * ld_c)
    if denom <= 0.0:
        raise ValueError(f"L/D {ld_c} is below the minimum {ld_min:.2f}: the mass diverges")
    return {"m0_kg": m_crew_payload_kg / denom, "ld_min": ld_min, "battery_fraction": G0 * range_km / (3.6 * e_wh_kg * eta_tot * ld_c)}


# ---------------------------------------------------------------- Proyecto
def run(project: dict) -> dict:
    d = prj.need_inputs(project, "m06", ["method"])
    method, depends = d["method"], []
    if method == "historical_ratios":
        we, wf = d.get("we_w0"), d.get("wf_w0")
        if d.get("ratios_from_m02"):
            sug = project["outputs"]["m02"]["result"]["suggested_for_m06"]
            we, wf, depends = sug["we_w0"], sug["wf_w0"], ["m02"]
        if we is None or wf is None:
            raise SystemExit("inputs.m06 needs we_w0 and wf_w0 (or ratios_from_m02)")
        r = gross_weight_historical(d["crew_kg"], d["payload_kg"], we, wf)
        result = {"method": method, "w0_kg": r["w0"], "we_kg": r["we"], "wf_kg": r["wf"], "we_w0": we, "wf_w0": wf,
                  "growth_factor": r["growth_factor"]}
    elif method == "empty_fraction":
        frac = empty_weight_fraction(d["class"], d["w0_kg"], "kg")
        result = {"method": method, "class": d["class"], "w0_kg": d["w0_kg"], "we_w0": frac, "we_kg": frac * d["w0_kg"],
                  "wu_kg": (1.0 - frac) * d["w0_kg"]}
    elif method == "mission":
        a, b = d.get("A_kg"), d.get("B")
        if d.get("class"):
            _n, _al, b, a = EMPTY_WEIGHT_FRACTION[d["class"]]
        if a is None or b is None:
            raise SystemExit("inputs.m06 needs class or A_kg and B for the mission method")
        r = gross_weight_mission(d["segments"], a, b, d["crew_kg"], d["payload_kg"])
        result = {"method": method, "w0_kg": r["w0"], "we_kg": r["we"], "we_w0": r["we_w0"],
                  "fuel_kg": r["fuel_weight"], "wn_over_w0": r["wn_over_w0"], "mission": r["mission"],
                  "residual": r["residual"], "A_kg": a, "B": b}
    elif method == "electric":
        r = electric_gross_mass(d["crew_payload_kg"], d["we_m0"], d["range_km"], d["e_wh_kg"], d["eta_tot"], d["ld_c"])
        result = {"method": method, "w0_kg": r["m0_kg"], "ld_min": r["ld_min"], "battery_fraction": r["battery_fraction"]}
    else:
        raise SystemExit("method must be historical_ratios, empty_fraction, mission or electric")
    result["w0_n"] = result["w0_kg"] * 9.80665
    prj.record(project, "m06", result, "conceptual", REFERENCES, depends)
    return result
