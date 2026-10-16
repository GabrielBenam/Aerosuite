"""M18a Tren de aterrizaje (Gudmundsson Tabla 1-4 paso 18; Cap. 13, Secs. 13.2 y 13.3).

Nivel conceptual. Disposicion geometrica (Sec. 13.3.1/13.3.2) y cargas: reacciones estaticas en tren de nariz/cola y principal
(Ecs. 13-17 a 13-22) con la regla de reparto (nariz 10-20 %, cola 5-10 %), angulo de vuelco (< 63 deg desde el suelo en triciclo,
>= 25 deg desde la vertical en tren convencional), angulo de golpe de cola y de vuelco hacia atras, holgura de helice
(14 CFR 23.925(a): 7 in triciclo, 9 in convencional), radio de giro (Ec. 13-2), huella del neumatico (Ecs. 13-4 y 13-5),
energia de frenado (Ec. 13-6) y velocidad de descenso de diseno (14 CFR 23.725 via la Sec. 13.2.5). Ejes de M10 (x hacia atras,
origen en el borde de ataque de la raiz del ala). SI interno. No selecciona neumaticos de catalogo (Tablas 13-7 a 13-9 son datos
de entrada: carga nominal y dimensiones), no calcula cargas de estructura (trayectorias de carga: Ansys) ni la dinamica del
amortiguador mas alla de la desaceleracion media (Ec. 13-8)."""
import math

from . import project as prj

REFERENCES = [
    "GUD Sec. 13.3.1, pasos 1 a 14 (tren triciclo: CG, golpe de cola, vuelco <= 63 deg, nariz 10 %-20 %), PDF 605-608",
    "GUD Sec. 13.3.2, pasos 1 a 10 (tren convencional: 15 deg, 25 deg, cola 5 %-10 %, vuelco >= 25 deg), PDF 608-609",
    "GUD Sec. 13.3.4, Ecs. 13-17 a 13-19 y Ejemplo 13-2 (RN estatica 357.5 lbf), PDF 610-613",
    "GUD Sec. 13.3.5, Ecs. 13-20 a 13-22 y Ejemplo 13-3 (cola 11.5 %), PDF 614-615",
    "GUD Sec. 13.2.1, Ecs. 13-2 a 13-5 (radio de giro, huella del neumatico), PDF 590-592",
    "GUD Sec. 13.2.3, Ec. 13-6 (energia de frenado, 14 CFR 23.735), PDF 598",
    "GUD Sec. 13.2.5, Ec. 13-8 y h = 3.6 (W/S)^(1/2) in, w ~ 4.4 (W/S)^(1/4) ft/s (14 CFR 23.725), PDF 603",
    "GUD Sec. 13.2: el neumatico principal debe admitir 25 % de crecimiento del peso bruto, PDF 590",
    "PDF = marcador [p. N] del texto convertido (impreso = PDF - 46 en Gudmundsson, PDF - 13 en Etkin); +-1 pagina",
]
G = 9.80665
FT = 0.3048
IN = 0.0254
KT = 0.514444
PSF = 47.88026
NOSE_LOAD_PCT = (10.0, 20.0)            # Sec. 13.3.1, paso 9 (10 % con CG trasero, 20 % con CG delantero)
TAIL_LOAD_PCT = (5.0, 10.0)             # Sec. 13.3.2, paso 9
OVERTURN_MAX_TRICYCLE_DEG = 63.0        # desde el suelo (paso 14)
OVERTURN_MIN_TAILDRAGGER_DEG = 25.0     # desde la vertical (paso 10); equivale a ~65 deg desde el suelo (D-37)
PROP_CLEARANCE_M = {"tricycle": 7 * IN, "taildragger": 9 * IN}
TAIL_STRIKE_MAX_DEG = 15.0
GROWTH_FACTOR = 1.25                    # Sec. 13.2: neumatico principal con 25 % de crecimiento


# --------------------------------------------------------------------------- cargas de reaccion
def static_loads_tricycle(w, x_n, x_m):
    """Ec. 13-19: R_N = W x_M/(x_N + x_M); R_M = W - R_N (x_N delante del CG, x_M detras, ambos positivos)."""
    rn = w * x_m / (x_n + x_m)
    return {"nose": rn, "main": w - rn, "share_pct": 100.0 * rn / w}


def static_loads_taildragger(w, x_m, x_t):
    """Ecs. 13-21 y 13-22 estaticas: R_T = W x_M/(x_M + x_T); R_M = W - R_T (x_M delante del CG, x_T detras)."""
    rt = w * x_m / (x_m + x_t)
    return {"tail": rt, "main": w - rt, "share_pct": 100.0 * rt / w}


def dynamic_loads_tricycle(w, x_n, x_m, z_cg, mu, thrust=0.0, z_t=0.0, lift_w=0.0, x_w=0.0, lift_ht=0.0, l_ht=0.0, m_w=0.0):
    """Ec. 13-17 con fuerzas hacia arriba positivas (`lift_ht` < 0 es la sustentacion negativa de la cola; el libro usa su magnitud
    hacia abajo). x_w y l_ht: distancia detras del CG del centro aerodinamico del ala y de la cola; z_t: altura de la linea de
    empuje sobre el CG; m_w: momento del ala (picado negativo). R_N = [T z_T + (W - L_W - L_HT)(x_M + mu z_CG) + L_W x_W
    + L_HT l_HT - M_W]/(x_N + x_M); R_M = W - L_W - L_HT - R_N. Se verifica con el equilibrio de momentos en las pruebas (D-37)."""
    net = w - lift_w - lift_ht
    rn = (thrust * z_t + net * (x_m + mu * z_cg) + lift_w * x_w + lift_ht * l_ht - m_w) / (x_n + x_m)
    return {"nose": rn, "main": net - rn}


def dynamic_loads_taildragger(w, x_m, x_t, z_cg, mu, thrust=0.0, z_t=0.0, lift_w=0.0, x_w=0.0, lift_ht=0.0, l_ht=0.0, m_w=0.0):
    """Ec. 13-20 (cola en el suelo), misma convencion: R_T = [(W - L_W - L_HT)(x_M - mu z_CG) - L_W x_W - L_HT l_HT - T z_T + M_W]
    /(x_M + x_T); R_M = W - L_W - L_HT - R_T (x_M delante del CG, x_T detras)."""
    net = w - lift_w - lift_ht
    rt = (net * (x_m - mu * z_cg) - lift_w * x_w - lift_ht * l_ht - thrust * z_t + m_w) / (x_m + x_t)
    return {"tail": rt, "main": net - rt}


# --------------------------------------------------------------------------- geometria
def lateral_distance(p1, p2, p0):
    """Distancia en planta del punto p0 a la recta p1-p2 (x, y)."""
    (x1, y1), (x2, y2), (x0, y0) = p1, p2, p0
    return abs((x2 - x1) * (y1 - y0) - (x1 - x0) * (y2 - y1)) / math.hypot(x2 - x1, y2 - y1)


def overturn_angle_deg(z_cg, lateral_dist, from_ground=True):
    """Triciclo (paso 14): tan(theta) = z_CG/d, desde el suelo. Convencional (paso 10): atan(d/z_CG), desde la vertical."""
    return math.degrees(math.atan2(z_cg, lateral_dist) if from_ground else math.atan2(lateral_dist, z_cg))


def turning_radius(wheel_base, nose_angle_deg):
    """Ec. 13-2: h = WB/tan(theta), R = sqrt(WB^2 + h^2) = WB/sin(theta)."""
    h = wheel_base / math.tan(math.radians(nose_angle_deg))
    return {"h": h, "radius": math.sqrt(wheel_base ** 2 + h ** 2)}


def min_nose_angle_turn_on_dime_deg(wheel_base, track):
    """h = track/2, de donde tan(theta) = 2 WB/track."""
    return math.degrees(math.atan(2.0 * wheel_base / track))


def tire_footprint(load, pressure_pa, diameter, loaded_radius):
    """Ecs. 13-4 y 13-5: S_e = F/p; c = sqrt(R0^2 - R_L^2) con R0 = D0/2, a = 0.85 c. La relacion entre a, b y S_e es ilegible
    en el texto convertido: b se despeja de S_e = pi a b/4 con S_e = F/p (supuesto, D-37)."""
    c = math.sqrt((diameter / 2.0) ** 2 - loaded_radius ** 2)
    a = 0.85 * c
    area = load / pressure_pa
    return {"c_m": c, "a_m": a, "contact_area_m2": area, "b_m": 4.0 * area / (math.pi * a)}


def brake_energy_per_brake(w_n, vs0_mps, n_brakes):
    """Ec. 13-6, 14 CFR 23.735: KE = (1/2)(W/g) V_S0^2 / N. El libro imprime 0.0433 W V^2 (lbf, KTAS, ft lbf), pero la deduccion
    que muestra da 0.5 (1.688)^2/32.174 = 0.0443: se usa la deduccion (D-37)."""
    return 0.5 * w_n / G * vs0_mps ** 2 / n_brakes


def sink_rate(wing_loading_pa):
    """14 CFR 23.725 (Sec. 13.2.5): h = 3.6 (W/S)^(1/2) in con W/S en lbf/ft2, entre 9.2 y 18.7 in; w = sqrt(2 g h)."""
    ws = wing_loading_pa / PSF
    h_in = min(18.7, max(9.2, 3.6 * math.sqrt(ws)))
    return {"drop_height_m": h_in * IN, "sink_rate_mps": math.sqrt(2 * G * h_in * IN), "book_approx_mps": 4.4 * ws ** 0.25 * FT}


def mean_deceleration(sink_mps, stroke_m):
    """Ec. 13-8: a_z = w^2/(2 d), media sin amortiguador ni neumatico."""
    a = sink_mps ** 2 / (2.0 * stroke_m)
    return {"a_mps2": a, "a_g": a / G}


def rotation_speed(reaction, v_lo=5.0, v_hi=100.0, n=2000):
    """Velocidad a la que `reaction(V)` (nariz o cola) se anula (Ejemplo 13-2 c): primer cruce de positivo a no positivo."""
    prev_v, prev = v_lo, reaction(v_lo)
    for i in range(1, n + 1):
        v = v_lo + (v_hi - v_lo) * i / n
        cur = reaction(v)
        if prev > 0.0 >= cur:
            return prev_v + (v - prev_v) * prev / (prev - cur)
        prev_v, prev = v, cur
    return None


# --------------------------------------------------------------------------- modulo
def _cases(project, d):
    """Casos de carga: los de `inputs.m18a.cases` o, si no, el avion vacio y la nube de cargas de M13."""
    if d.get("cases"):
        return [{"id": c.get("id", f"case {i}"), "mass_kg": c["mass_kg"], "x_cg_m": c["x_cg_m"]} for i, c in enumerate(d["cases"])], []
    out = project["outputs"].get("m13")
    if not out:
        raise SystemExit("outputs.m13 is missing (CG cases): run m13 first or give inputs.m18a.cases")
    r = out["result"]
    cases = [{"id": "empty", "mass_kg": r["total_mass_kg"], "x_cg_m": r["cg_m"][0]}]
    cases += [{"id": c["id"], "mass_kg": c["mass_kg"], "x_cg_m": c["x_cg_m"]} for c in r.get("loading_cloud", [])]
    return cases, ["m13"]


def evaluate(project: dict) -> tuple[dict, list]:
    d = prj.need_inputs(project, "m18a", ["configuration", "x_main_m", "z_cg_above_ground_m", "track_m"])
    cfg = d["configuration"]
    if cfg not in ("tricycle", "taildragger"):
        raise SystemExit("inputs.m18a.configuration must be 'tricycle' or 'taildragger'")
    second = "x_nose_m" if cfg == "tricycle" else "x_tail_m"
    if second not in d:
        raise SystemExit(f"inputs.m18a.{second} is missing")
    cases, depends = _cases(project, d)
    xm, x2, zc, track = d["x_main_m"], d[second], d["z_cg_above_ground_m"], d["track_m"]
    res = {"level": "conceptual", "units": "SI (kg, m, N, s)", "configuration": cfg, "assumptions": []}
    rows = []
    for c in cases:
        w = c["mass_kg"] * G
        if cfg == "tricycle":
            ld = static_loads_tricycle(w, c["x_cg_m"] - x2, xm - c["x_cg_m"])
            key, rng = "nose", NOSE_LOAD_PCT
        else:
            ld = static_loads_taildragger(w, c["x_cg_m"] - xm, x2 - c["x_cg_m"])
            key, rng = "tail", TAIL_LOAD_PCT
        rows.append({**c, "weight_n": w, **ld, "within_guidance": rng[0] <= ld["share_pct"] <= rng[1]})
    res["static_loads"] = {"cases": rows, "secondary_gear": key, "guidance_pct": list(rng),
                           "equation": "Eq. 13-19" if cfg == "tricycle" else "Eqs. 13-21 / 13-22",
                           "max_main_n": max(r["main"] for r in rows), "max_secondary_n": max(r[key] for r in rows)}
    x_fwd, x_aft = min(r["x_cg_m"] for r in rows), max(r["x_cg_m"] for r in rows)
    # --- vuelco: recta entre el tren de nariz/cola y un tren principal (y = +-track/2); caso mas desfavorable ---
    dist = min(lateral_distance((x2, 0.0), (xm, track / 2.0), (x, 0.0)) for x in (x_fwd, x_aft))
    if cfg == "tricycle":
        ang = overturn_angle_deg(zc, dist, True)
        res["overturn"] = {"angle_deg": ang, "limit_deg": OVERTURN_MAX_TRICYCLE_DEG, "ok": ang < OVERTURN_MAX_TRICYCLE_DEG,
                           "measured_from": "ground", "distance_cg_to_line_m": dist}
    else:
        ang = overturn_angle_deg(zc, dist, False)
        res["overturn"] = {"angle_deg": ang, "limit_deg": OVERTURN_MIN_TAILDRAGGER_DEG, "ok": ang >= OVERTURN_MIN_TAILDRAGGER_DEG,
                           "measured_from": "vertical", "distance_cg_to_line_m": dist}
    # --- golpe de cola y vuelco hacia atras ---
    if "tail_strike" in d:
        ts = d["tail_strike"]
        angle = math.degrees(math.atan2(ts["tail_point_height_above_ground_m"], ts["tail_point_x_m"] - xm))
        tip = math.degrees(math.atan2(xm - x_aft, zc))
        res["tail_strike"] = {"geometric_angle_deg": angle, "alpha_stall_clean_deg": ts.get("alpha_stall_deg"),
                              "ok_vs_stall": (angle >= ts["alpha_stall_deg"]) if "alpha_stall_deg" in ts else None,
                              "recommended_max_deg": TAIL_STRIKE_MAX_DEG, "tip_back_angle_deg": tip,
                              "tip_back_ok": (tip > angle) if cfg == "tricycle" else None,
                              "note": "tip_back_angle: from the vertical at the aft-most CG to the main contact; it must exceed the tail-strike angle (step 7)"}
    else:
        res["assumptions"].append("tail-strike and tip-back check skipped: give inputs.m18a.tail_strike "
                                  "{tail_point_x_m, tail_point_height_above_ground_m, alpha_stall_deg}")
    if "prop_tip_height_above_ground_m" in d:
        cl = d["prop_tip_height_above_ground_m"]
        res["prop_clearance"] = {"clearance_m": cl, "minimum_m": PROP_CLEARANCE_M[cfg], "ok": cl >= PROP_CLEARANCE_M[cfg],
                                 "note": "14 CFR 23.925(a): 7 in (tricycle) / 9 in (taildragger); check with a flat nose tire"}
    if cfg == "tricycle":
        wb = xm - x2
        res["ground_handling"] = {"wheel_base_m": wb, "track_m": track,
                                  "min_nose_angle_turn_on_dime_deg": min_nose_angle_turn_on_dime_deg(wb, track)}
        if "nose_steer_deg" in d:
            res["ground_handling"]["turning"] = turning_radius(wb, d["nose_steer_deg"])
    # --- neumaticos, frenos, impacto ---
    w_max = max(c["mass_kg"] for c in cases) * G
    n_main = d.get("n_main_wheels", 2)
    per_tire = res["static_loads"]["max_main_n"] / n_main
    tires = {"main_design_load_per_tire_n": GROWTH_FACTOR * per_tire, "growth_factor": GROWTH_FACTOR}
    mt = d.get("main_tire")
    if mt:
        tires["main_rated_load_n"] = mt["rated_load_n"]
        tires["main_ok"] = mt["rated_load_n"] >= tires["main_design_load_per_tire_n"]
        if {"diameter_m", "loaded_radius_m", "inflation_pa"} <= mt.keys():
            tires["footprint"] = tire_footprint(per_tire, mt["inflation_pa"] * 1.04, mt["diameter_m"], mt["loaded_radius_m"])
    else:
        res["assumptions"].append("main tire not checked: give inputs.m18a.main_tire {rated_load_n, diameter_m, loaded_radius_m, "
                                  "inflation_pa} (catalog data, Tables 13-7 to 13-9)")
    res["tires"] = tires
    fl = d.get("flight", {})
    if "vs0_mps" in fl:
        n_b = d.get("n_braked_wheels", 2)
        res["brakes"] = {"energy_per_brake_j": brake_energy_per_brake(w_max, fl["vs0_mps"], n_b), "n_brakes": n_b,
                         "equation": "Eq. 13-6 (from its derivation, D-37)"}
    if "wing_loading_pa" in fl or "wing_area_m2" in fl:
        ws = fl.get("wing_loading_pa") or w_max / fl["wing_area_m2"]
        res["landing_impact"] = {"wing_loading_pa": ws, **sink_rate(ws)}
        if "stroke_m" in d:
            res["landing_impact"]["mean_deceleration"] = mean_deceleration(res["landing_impact"]["sink_rate_mps"], d["stroke_m"])
    if "dynamic" in d:
        res["rotation"] = _rotation(d, cfg, xm, x2, zc, rows)
    res["verdict"] = {"static_share_ok": all(r["within_guidance"] for r in rows), "overturn_ok": res["overturn"]["ok"]}
    return res, depends


def _rotation(d, cfg, xm, x2, zc, rows):
    dy = d["dynamic"]
    case = max(rows, key=lambda r: r["mass_kg"])
    w, xcg = case["weight_n"], case["x_cg_m"]
    rho, s = dy["density_kgm3"], dy["wing_area_m2"]

    def reaction(v):
        q = 0.5 * rho * v * v
        lw, lht = q * s * dy["cl_w"], q * dy["ht_area_m2"] * dy["cl_ht"]
        thr = min(dy["static_thrust_n"], dy["eta_p"] * dy["power_w"] / max(v, 0.1))
        args = dict(thrust=thr, z_t=dy.get("z_thrust_m", 0.0), lift_w=lw, x_w=dy["x_w_m"], lift_ht=lht, l_ht=dy["l_ht_m"],
                    m_w=q * s * dy["c_m_cg"] * dy["mgc_m"])
        if cfg == "tricycle":
            return dynamic_loads_tricycle(w, xcg - x2, xm - xcg, zc, dy.get("mu", 0.04), **args)["nose"]
        return dynamic_loads_taildragger(w, xcg - xm, x2 - xcg, zc, dy.get("mu", 0.04), **args)["tail"]
    v = rotation_speed(reaction)
    return {"rotation_speed_mps": v, "rotation_speed_kt": None if v is None else v / KT, "mass_kg": case["mass_kg"],
            "note": "constant-speed approximation (Sec. 13.3.4); ground effect on CL and CL_HT must be included in the inputs; "
                    "the take-off run itself belongs to M21"}


def run(project: dict) -> dict:
    result, depends = evaluate(project)
    prj.record(project, "m18a", result, "conceptual", REFERENCES, sorted(set(depends)))
    return result
