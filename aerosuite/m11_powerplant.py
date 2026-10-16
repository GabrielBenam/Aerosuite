"""M11 Planta motriz y helice (Gudmundsson Tabla 1-4 paso 11; Sec. 7.2 motores de piston y Sec. 15.3 seleccion de helice).

Nivel conceptual, solo motor de piston con helice (turbinas y motores electricos quedan fuera: D-28). A partir de la
potencia requerida de M04 (ADRpy, equivalente a nivel del mar) comprueba un motor candidato (potencia nominal, altitud,
temperatura, caja reductora) y dimensiona la helice con las relaciones del libro (diametro, velocidad de punta, paso,
razon de avance, eficiencia requerida). El deck IO-540 de ADRpy (digitalizado de Saarlas, Fig. 2-D3) se ofrece solo como
contraste de la variacion de la potencia con la altitud; no es un dato del motor del usuario.
"""
import math

from . import adrpy_core
from . import project as prj

HP_W = 745.69987158
KTAS_MPS = 0.514444
G = 9.80665
REFERENCES = [
    "GUD Sec. 7.2.1(2), Ecs. 7-7 y 7-8 (altitud, Gagg-Ferrar), Ecs. 7-9 y 7-10 (altitud critica), PDF 252-253 / impr. 207-208",
    "GUD Sec. 7.2.1(4), Ecs. 7-12 y 7-13 y Ejemplo 7-2 (correccion de temperatura), PDF 253-254 / impr. 208-209",
    "GUD Sec. 7.2.3, Ecs. 7-14 a 7-17 y Ejemplo 7-3 (caja reductora), PDF 254-255 / impr. 209-210",
    "GUD Sec. 15.3.1-15.3.2, Ecs. 15-24 a 15-26 y Ejemplo 15-2 (diametro de helice de madera, velocidad de punta), PDF 665-666 / impr. 620-621",
    "GUD Sec. 15.3.3, Ec. 15-30 (paso geometrico, constante corregida: D-28), PDF 666-667 / impr. 621-622",
    "GUD Sec. 15.3.4-15.3.5, Ec. 15-32, Ejemplo 15-3 (eficiencia requerida, razon de avance), PDF 668-669 / impr. 623-624",
    "ADRpy 0.2.6 propulsion.PistonDeck (IO-540, Saarlas, Aircraft Performance, Fig. 2-D3): solo contraste",
]
KAPPA_PER_FT = 0.0000068756         # GUD Ec. 7-10 (sigma = (1 - kappa h)^4.2561, h en ft)
KAPPA_PER_M = 0.000022558
WOOD_COEFF = {2: 53.5, 3: 75.8, 4: 111.0}   # Ecs. 15-24 (2 palas), interpolada para 3 palas (derivada en el libro) y 15-26 (4 palas)
TIP_MACH_LIMIT = {"wood": (0.6, 0.6), "metal": (0.75, 0.8), "composite": (0.75, 0.8)}   # GUD Sec. 15.3.1


def sigma_isa(altitude_m: float) -> float:
    atmospheres, _ca, _np = adrpy_core._libraries()
    return float(atmospheres.Atmosphere().airdens_kgpm3(altitude_m)) / 1.225


def gagg_ferrar(sigma: float) -> float:
    """Ec. 7-8: P/P_SL = 1.132 sigma - 0.132 (motores aspirados)."""
    return 1.132 * sigma - 0.132


def sigma_standard_ft(h_ft: float) -> float:
    """sigma = (1 - kappa h)^4.2561 con kappa = 6.8756e-6 /ft (Ejemplo 7-2: 0.9312^4.2561 = 0.7385 a 10 000 ft)."""
    return (1.0 - KAPPA_PER_FT * h_ft) ** 4.2561


def piston_power_bhp(p_sl_bhp: float, altitude_m: float, h_crit_m: float | None = None) -> float:
    """Potencia a plena admision a `altitude_m` (ISA). Motor aspirado: Gagg-Ferrar (Ec. 7-8). Con altitud critica
    (turbonormalizado): P_SL hasta h_crit y despues la Ec. 7-10 con (1 - kappa (h - h_crit))^4.2561 (signo de kappa
    reconstruido: en el libro kappa es negativo en (1 + kappa h) y la forma impresa pierde el signo)."""
    if h_crit_m is None:
        return p_sl_bhp * gagg_ferrar(sigma_isa(altitude_m))
    if altitude_m <= h_crit_m:
        return p_sl_bhp
    s = (1.0 - KAPPA_PER_M * (altitude_m - h_crit_m)) ** 4.2561
    return p_sl_bhp * gagg_ferrar(s)


def temperature_correction(p_std: float, t_std: float, t_oat: float, form: str = "sqrt") -> float:
    """Ec. 7-12 (P = P_std sqrt(T_std/T_OAT)) o Ec. 7-13 (P = P_std T_std/T_OAT); temperaturas absolutas."""
    ratio = t_std / t_oat
    return p_std * (math.sqrt(ratio) if form == "sqrt" else ratio)


def gearbox(rpm_engine: float, ratio: float) -> float:
    """Ec. 7-14: Omega_2 = Omega_1 R_1 / R_2 con relacion de reduccion `ratio` = R_2/R_1; la potencia no cambia (Ec. 7-17)."""
    if ratio < 1.0:
        raise ValueError("a reduction drive has ratio >= 1")
    return rpm_engine / ratio


def wood_prop_diameter_in(p_bhp: float, rpm: float, v_ktas: float, blades: int) -> float:
    """Ecs. 15-24 a 15-26: D_p = 10000 (P_BHP / (K RPM^2 V_KTAS))^(1/4) pulgadas, K = 53.5, 75.8, 111 para 2, 3, 4 palas."""
    if blades not in WOOD_COEFF:
        raise ValueError("blades must be 2, 3 or 4")
    return 10000.0 * (p_bhp / (WOOD_COEFF[blades] * rpm ** 2 * v_ktas)) ** 0.25


def tip_speed_mps(diameter_m: float, rpm: float) -> float:
    return 2.0 * math.pi * rpm / 60.0 * diameter_m / 2.0


def pitch_in(v_ktas: float, rpm: float) -> float:
    """Ec. 15-30 con la constante de la deduccion del libro: P_G = 60 V / RPM; V en KTAS y P_G en pulgadas da
    60 x 20.256 = 1215.36 (el libro imprime 1251.36: transposicion de cifras, D-28)."""
    return 1215.36 * v_ktas / rpm


def advance_ratio(v_mps: float, rpm: float, diameter_m: float) -> float:
    """J = 60 V / (RPM D) (Ejemplo 15-3)."""
    return 60.0 * v_mps / (rpm * diameter_m)


def required_prop_efficiency(weight_n: float, v_mps: float, ld: float, power_w: float) -> float:
    """Ec. 15-32: eta_p = W V / ((L/D) P) (vuelo nivelado, T = D = W/(L/D))."""
    return weight_n * v_mps / (ld * power_w)


def _brief(project: dict) -> dict:
    return project["inputs"].get("m04", {}).get("concept", {}).get("designbrief", {})


def _m04_power(project: dict, depends: list) -> dict:
    if "m04" not in project["outputs"]:
        raise SystemExit("inputs.m11.power_required.source = 'm04' but outputs.m04 is missing: run m04 first")
    r = project["outputs"]["m04"]["result"]
    pr = r.get("power_required")
    best = r.get("best_sample")
    if not pr or not pr.get("available") or not best:
        raise SystemExit("outputs.m04 has no power_required (needs tow_kg, all five constraints and etaprop) or no design point")
    ws = [s["wingloading_pa"] for s in r["samples"]]
    i = min(range(len(ws)), key=lambda k: abs(ws[k] - best["wingloading_pa"]))
    depends.append("m04")
    by = {k: v[i] for k, v in pr["by_constraint"].items()}
    return {"source": "M04 ADRpy powerrequired() at the design point", "wingloading_pa": ws[i], "units": "hp (sea-level equivalent)",
            "by_constraint_hp": by, "combined_hp": pr["combined"][i], "active": max(by, key=by.get),
            "takeoff_note": "the take-off entry uses ADRpy's formulation (not Eq. 3-1, D-22)"}


def evaluate(project: dict) -> tuple[dict, list]:
    d = prj.need_inputs(project, "m11", ["engine"])
    depends: list = []
    pr = d.get("power_required", {"source": "m04"})
    if pr.get("source", "m04") == "m04":
        req = _m04_power(project, depends)
    else:
        req = {"source": "input", "combined_hp": float(pr["bhp"]), "by_constraint_hp": {}, "active": None}
    e = d["engine"]
    rated, rpm_e = float(e["rated_bhp"]), float(e["rated_rpm"])
    ratio = float(e.get("gear_ratio", 1.0))
    rpm_p = gearbox(rpm_e, ratio)
    h_crit = e.get("critical_altitude_m")
    brief = _brief(project)
    cruise_alt = float(d.get("cruise", {}).get("altitude_m", brief.get("cruisealt_m", 0.0)))
    cruise_v = float(d.get("cruise", {}).get("ktas", brief.get("cruisespeed_ktas", 0.0)))
    result = {"level": "conceptual", "required_power": req,
              "engine": {**{k: e[k] for k in e if k != "name"}, "name": e.get("name", "engine"), "propeller_rpm": rpm_p,
                         "power_after_gearbox_bhp": rated, "model": "Gagg-Ferrar (Ec. 7-8)" if h_crit is None else "Ec. 7-9/7-10"},
              "warnings": []}
    margin = (rated - req["combined_hp"]) / req["combined_hp"]
    result["engine"]["sl_rated_margin_over_required"] = margin
    result["engine"]["meets_sl_equivalent_power"] = margin >= 0.0
    if margin < 0.0:
        result["warnings"].append("the rated power is below the sea-level-equivalent power required by the active constraint")
    # potencia disponible a la altitud de cada restriccion (informativa)
    avail = {}
    brief_alt = {"takeoff": brief.get("rwyelevation_m", 0.0), "climb": brief.get("climbalt_m", 0.0),
                 "cruise": brief.get("cruisealt_m", 0.0), "turn": brief.get("turnalt_m", 0.0),
                 "ceiling": brief.get("servceil_m", 0.0)}
    for name, hp in req.get("by_constraint_hp", {}).items():
        alt = float(brief_alt.get(name, 0.0))
        p_alt = piston_power_bhp(rated, alt, h_crit)
        avail[name] = {"altitude_m": alt, "available_bhp": p_alt, "required_sl_equivalent_hp": hp,
                       "required_at_altitude_hp": hp * (p_alt / rated) if rated else None}
    result["availability_by_constraint"] = avail
    if "temperature_offset_k" in d:
        t_std = 288.15 - 0.0065 * cruise_alt
        t_oat = t_std + float(d["temperature_offset_k"])
        p_std = piston_power_bhp(rated, cruise_alt, h_crit)
        result["temperature_correction"] = {"cruise_altitude_m": cruise_alt, "offset_k": d["temperature_offset_k"],
                                            "power_eq_7_12_bhp": temperature_correction(p_std, t_std, t_oat, "sqrt"),
                                            "power_eq_7_13_bhp": temperature_correction(p_std, t_std, t_oat, "ratio"),
                                            "note": "the book recommends the Gagg-Ferrar density route for design work"}
    # --- helice ---
    pp = d.get("propeller", {})
    material = pp.get("material", "wood")
    if cruise_v > 0.0:
        cruise_power = rated * 0.75 if "power_fraction" not in pp else rated * float(pp["power_fraction"])
        if "power_fraction" not in pp:
            prj.add_assumption(project, "m11", "propeller_power_fraction", 0.75,
                               "supuesto: la helice se dimensiona al 75 % de la potencia nominal (el Ejemplo 15-2 del libro usa 75 %)")
        a = float(adrpy_core._libraries()[0].Atmosphere().vsound_mps(cruise_alt))
        rows = []
        for n in (2, 3, 4):
            d_in = wood_prop_diameter_in(cruise_power, rpm_p, cruise_v, n)
            d_m = d_in * 0.0254
            tip = tip_speed_mps(d_m, rpm_p)
            rows.append({"blades": n, "diameter_in": d_in, "diameter_m": d_m, "tip_speed_mps": tip, "tip_speed_fts": tip / 0.3048,
                         "tip_mach_cruise_rotational": tip / a})
        lim = TIP_MACH_LIMIT[material]
        v_mps = cruise_v * KTAS_MPS
        sel = next((r for r in rows if r["blades"] == int(pp.get("blades", 2))), rows[0])
        j = advance_ratio(v_mps, rpm_p, sel["diameter_m"])
        result["propeller"] = {"material": material, "design_power_bhp": cruise_power, "rpm": rpm_p, "cruise_ktas": cruise_v,
                               "cruise_altitude_m": cruise_alt, "diameter_estimates": rows, "selected_blades": sel["blades"],
                               "tip_mach_limit": list(lim), "selected_tip_mach_ok": sel["tip_mach_cruise_rotational"] <= lim[1],
                               "pitch_estimate_in": pitch_in(cruise_v, rpm_p), "advance_ratio_cruise": j,
                               "diameter_method": "wooden-propeller formulas (Eqs. 15-24 to 15-26); metal/composite: "
                                                  "Table 15-2 factors are illegible in the digital source, use the manufacturer (D-28)",
                               "constant_speed_guideline": {"bhp_over_180": rated > 180.0, "ktas_over_130": cruise_v > 130.0,
                                                            "constant_speed_suggested": rated > 180.0 and cruise_v > 130.0,
                                                            "source": "GUD Sec. 15.3.1(4): >180-200 BHP and >130-140 KTAS"}}
        if material != "wood":
            result["warnings"].append(f"diameter estimates use wooden-propeller formulas; {material} propellers need the manufacturer's data")
        if "ld_cruise" in d:
            w_n = (project["inputs"]["m04"]["concept"].get("tow_kg", 0.0)) * G
            if "m06" in project["outputs"] and project["inputs"].get("m04", {}).get("tow_from_m06"):
                w_n = project["outputs"]["m06"]["result"]["w0_kg"] * G
                depends.append("m06")
            p_w = cruise_power * HP_W
            result["propeller"]["required_efficiency_eq_15_32"] = required_prop_efficiency(w_n, v_mps, float(d["ld_cruise"]), p_w)
    else:
        result["warnings"].append("no cruise speed (inputs.m11.cruise.ktas or m04 brief): propeller not sized")
    # --- contraste ADRpy (deck IO-540) ---
    if d.get("adrpy_deck"):
        from ADRpy import propulsion
        deck = propulsion.PistonDeck(d["adrpy_deck"])
        rpm = float(d.get("adrpy_deck_rpm", rpm_e))
        rows = []
        p0 = float(deck.shaftpower(rpm, 0.0))
        for alt in d.get("adrpy_deck_altitudes_m", [0.0, 1500.0, 3000.0]):
            p = float(deck.shaftpower(rpm, alt))
            rows.append({"altitude_m": alt, "deck_ratio_to_sl": p / p0, "gagg_ferrar_ratio": gagg_ferrar(sigma_isa(alt))})
        result["adrpy_deck_contrast"] = {"engine": d["adrpy_deck"], "rpm": rpm, "rows": rows,
                                         "note": "digitized chart data (Saarlas); contrast only, not validation of the user's engine"}
    return result, depends


def run(project: dict) -> dict:
    result, depends = evaluate(project)
    prj.record(project, "m11", result, "conceptual", REFERENCES, sorted(set(depends)))
    return result
