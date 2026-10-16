"""M21 Prestaciones y diagrama de carga util-alcance (Gudmundsson Tabla 1-4 paso 21; Caps. 19, 20 y 21; Sec. 3.2 para el techo de servicio).

Nivel conceptual, avion de helice con motor de piston y polar parabolica C_D = C_Dmin + k C_L^2 (de M20 y M09b o dados). Potencia disponible
P_a = eta_p P_SL (1.132 sigma - 0.132) (modelo de Gagg-Ferrar, Ec. 3-17), potencia requerida P_r = D V; velocidad maxima (P_a = P_r),
velocidad de perdida, velocidad y razon de ascenso maximas, techo de servicio (V_V = 100 fpm = 0.508 m/s, Sec. 3.2) y techo absoluto.
Alcance de Breguet para helice a velocidad y altitud constantes (Ec. 21-25 en forma de helice, Ec. 21-27) y a actitud constante
(perfil 3: R = (eta_p/c)(L/D) ln(W_i/W_f)); resistencia equivalente; diagrama carga util-alcance con reserva y combustible de
operaciones no de crucero dados. Despegue y aterrizaje reutilizan las ecuaciones de M04 (Ecs. 3-13/3-14). Limitaciones: eta_p constante
(la curva eta_p(J) de M03/M11 no se acopla), sin compresibilidad (M < 0.3), sin viento, ascenso a velocidad constante sin aceleracion, tiempo
a altura sin integrar; ADRpy no aporta funciones de alcance en la version instalada y no se usa aqui. SI interno."""
import math

from scipy.optimize import brentq, minimize_scalar

from . import project as prj
from .m20_drag import isa
from . import m04_constraints as m04

REFERENCES = [
    "GUD Sec. 3.2 / Ec. 3-17 y Sec. 7 (modelo de Gagg-Ferrar: P = P_SL (1.132 sigma - 0.132)); techo de servicio con V_V = 100 fpm = 0.508 m/s",
    "GUD Cap. 19 (ascenso: P_a, P_r y potencia excedente, RC = (P_a - D V)/W) y 19.3.7 (techo absoluto y de servicio)",
    "GUD Cap. 20 (crucero estacionario: velocidades de maximo L/D y maximo CL^1.5/CD con polar parabolica)",
    "GUD Sec. 21.3, Ecs. 21-25 a 21-29 (alcance de Breguet a velocidad y altitud constantes: R = ... [atan(A W_ini) - atan(A W_fin)]) y Ejemplo 21-6 (737 nm, 768 nm, optimo 950 nm), PDF 40385-40800",
    "GUD Ejemplo 21-2 (Avgas 2.72 kg/gal; c_kW = 0.304 kg/(kW h) para 12.5 gal/h y 150 BHP)",
    "GUD Caps. 18 y 23 via M04 (distancias de despegue y aterrizaje)",
]
G = 9.80665
KT = 0.514444
NM = 1852.0
BHP_W = 745.69987
AVGAS_KG_PER_GAL = 2.72
SERVICE_CEILING_RC = 0.508


def gagg_ferrar(sigma: float) -> float:
    """P/P_SL = 1.132 sigma - 0.132 (motor atmosferico)."""
    return 1.132 * sigma - 0.132


def power_available(power_sl_w, eta_p, altitude_m):
    sigma = isa(altitude_m)["rho"] / 1.225
    return eta_p * power_sl_w * gagg_ferrar(sigma)


def drag_n(v, w_n, rho, s, cdmin, k):
    q = 0.5 * rho * v * v
    return q * s * cdmin + k * w_n ** 2 / (q * s)


def power_required(v, w_n, rho, s, cdmin, k):
    return drag_n(v, w_n, rho, s, cdmin, k) * v


def stall_speed(w_n, rho, s, clmax):
    return math.sqrt(2.0 * w_n / (rho * s * clmax))


def v_min_power(w_n, rho, s, cdmin, k):
    """CL = sqrt(3 CDmin/k) (maximo CL^1.5/CD, minima potencia requerida)."""
    return math.sqrt(2.0 * w_n / (rho * s * math.sqrt(3.0 * cdmin / k)))


def v_max_ld(w_n, rho, s, cdmin, k):
    """CL = sqrt(CDmin/k) (maximo L/D)."""
    return math.sqrt(2.0 * w_n / (rho * s * math.sqrt(cdmin / k)))


def max_speed(w_n, altitude_m, s, cdmin, k, power_sl_w, eta_p):
    """Mayor raiz de P_a(V) = P_r(V) por encima de la velocidad de minima potencia; None si no hay raiz (el avion no sostiene vuelo nivelado)."""
    atm = isa(altitude_m)
    pa = power_available(power_sl_w, eta_p, altitude_m)
    f = lambda v: pa - power_required(v, w_n, atm["rho"], s, cdmin, k)
    v0 = v_min_power(w_n, atm["rho"], s, cdmin, k)
    if f(v0) < 0.0:
        return None
    hi = v0 * 1.5
    while f(hi) > 0.0 and hi < 400.0:
        hi *= 1.25
    return brentq(f, v0, hi, xtol=1e-9)


def best_climb(w_n, altitude_m, s, cdmin, k, power_sl_w, eta_p):
    """Razon de ascenso maxima RC = (P_a - P_r)/W (vuelo cuasi-estacionario) y la velocidad a la que ocurre."""
    atm = isa(altitude_m)
    pa = power_available(power_sl_w, eta_p, altitude_m)
    res = minimize_scalar(lambda v: -(pa - power_required(v, w_n, atm["rho"], s, cdmin, k)) / w_n,
                          bounds=(0.5 * v_min_power(w_n, atm["rho"], s, cdmin, k), 3.0 * v_max_ld(w_n, atm["rho"], s, cdmin, k)), method="bounded",
                          options={"xatol": 1e-9})
    return {"v_mps": float(res.x), "rc_mps": float(-res.fun)}


def ceiling(w_n, s, cdmin, k, power_sl_w, eta_p, rc_target=0.0, h_hi=11000.0):
    """Altitud a la que RC_max = rc_target (0: techo absoluto; 0.508 m/s: techo de servicio); troposfera ISA."""
    f = lambda h: best_climb(w_n, h, s, cdmin, k, power_sl_w, eta_p)["rc_mps"] - rc_target
    if f(0.0) < 0.0:
        return None
    if f(h_hi) > 0.0:
        return h_hi
    return brentq(f, 0.0, h_hi, xtol=1e-6)


def fuel_flow_w(c_p_kg_per_kwh, power_w):
    """Gasto de combustible en kg/s para una potencia al eje dada."""
    return c_p_kg_per_kwh * (power_w / 1000.0) / 3600.0


def c_weight_per_joule(c_p_kg_per_kwh):
    """c_w [N/J = 1/m] : dW/dt = -c_w P (Ec. 21-20/21-21 en SI)."""
    return c_p_kg_per_kwh * G / 3.6e6


def range_const_v_h(w_ini_n, w_fin_n, v, rho, s, cdmin, k, eta_p, c_p_kg_per_kwh):
    """Alcance de Breguet de helice a velocidad y altitud constantes (Ec. 21-25 con c_t = c V/eta_p): R = eta/(c_w sqrt(k CDmin)) [atan(A Wi) - atan(A Wf)],
    A = sqrt(k/CDmin) 2/(rho V^2 S)."""
    a = math.sqrt(k / cdmin) * 2.0 / (rho * v * v * s)
    return eta_p / (c_weight_per_joule(c_p_kg_per_kwh) * math.sqrt(k * cdmin)) * (math.atan(a * w_ini_n) - math.atan(a * w_fin_n))


def range_const_attitude(w_ini_n, w_fin_n, l_over_d, eta_p, c_p_kg_per_kwh):
    """Perfil de actitud constante (L/D constante): R = (eta_p/c_w)(L/D) ln(W_i/W_f) (perfil 3 del Ejemplo 21-6)."""
    return eta_p / c_weight_per_joule(c_p_kg_per_kwh) * l_over_d * math.log(w_ini_n / w_fin_n)


def endurance_const_v_h(w_ini_n, w_fin_n, v, rho, s, cdmin, k, eta_p, c_p_kg_per_kwh):
    """Autonomia a velocidad y altitud constantes: E = R/V."""
    return range_const_v_h(w_ini_n, w_fin_n, v, rho, s, cdmin, k, eta_p, c_p_kg_per_kwh) / v


# --------------------------------------------------------------------------- modulo
def _aero(project, d):
    w = project["outputs"].get("m09b")
    if not w:
        raise SystemExit("outputs.m09b is missing: run m09b first")
    deps = ["m09b"]
    wing = w["result"]
    s = wing["planform"]["area_m2"]
    k = d.get("k") or wing["span_efficiency"]["k_induced"]
    cdmin, src = d.get("cdmin"), "inputs.m21.cdmin"
    if cdmin is None:
        m20 = project["outputs"].get("m20")
        if not m20:
            raise SystemExit("inputs.m21.cdmin is missing: give it or run m20 first")
        cdmin, src = m20["result"]["buildup"]["cd_min"], "M20 component buildup"
        deps.append("m20")
    clmax = d.get("clmax") or (wing.get("clmax") or {}).get("clmax")
    if not clmax:
        raise SystemExit("inputs.m21.clmax or M09b CLmax is required")
    return s, cdmin, k, clmax, src, deps


def evaluate(project: dict) -> tuple[dict, list]:
    d = prj.need_inputs(project, "m21", ["engine", "weights", "cruise"])
    s, cdmin, k, clmax, src, depends = _aero(project, d)
    eng, wt, cr = d["engine"], d["weights"], d["cruise"]
    p_sl, eta = eng["power_sl_w"], eng["eta_p"]
    c_p = eng["c_p_kg_per_kwh"]
    res = {"level": "conceptual", "units": "SI", "assumptions": [], "aero": {"cdmin": cdmin, "cdmin_source": src, "k": k, "clmax": clmax, "s_m2": s}}
    res["assumptions"].append("eta_p constant and C_D = C_Dmin + k C_L^2 (no compressibility, no wind, quasi-steady climb)")
    # --- masas ---
    mtow, oew = wt["mtow_kg"], wt["oew_kg"]
    fuel_cap = wt.get("fuel_capacity_kg") or wt["fuel_capacity_gal"] * AVGAS_KG_PER_GAL
    pay_max = wt["max_payload_kg"]
    res["weights"] = {"mtow_kg": mtow, "oew_kg": oew, "fuel_capacity_kg": fuel_cap, "max_payload_kg": pay_max}
    w_n = mtow * G
    # --- velocidades y ascenso al peso maximo ---
    perf = {}
    for h in d.get("altitudes_m", [0.0, 1500.0, 3000.0]):
        atm = isa(h)
        vmax = max_speed(w_n, h, s, cdmin, k, p_sl, eta)
        bc = best_climb(w_n, h, s, cdmin, k, p_sl, eta)
        perf[str(h)] = {"altitude_m": h, "rho": atm["rho"], "v_stall_mps": stall_speed(w_n, atm["rho"], s, clmax), "v_max_mps": vmax,
                        "v_max_kt": None if vmax is None else vmax / KT, "v_best_rc_mps": bc["v_mps"], "rc_max_mps": bc["rc_mps"],
                        "rc_max_fpm": bc["rc_mps"] / 0.3048 * 60.0, "p_available_w": power_available(p_sl, eta, h),
                        "v_best_ld_mps": v_max_ld(w_n, atm["rho"], s, cdmin, k), "v_min_power_mps": v_min_power(w_n, atm["rho"], s, cdmin, k)}
    res["performance_at_mtow"] = perf
    sc = ceiling(w_n, s, cdmin, k, p_sl, eta, SERVICE_CEILING_RC)
    ac = ceiling(w_n, s, cdmin, k, p_sl, eta, 0.0)
    res["ceilings_at_mtow"] = {"service_m": sc, "service_ft": None if sc is None else sc / 0.3048, "absolute_m": ac,
                               "absolute_ft": None if ac is None else ac / 0.3048,
                               "note": "ISA troposphere (to 11 km); Gagg-Ferrar power lapse (normally aspirated engine)"}
    # --- crucero y alcance ---
    h_c, v_c = cr["altitude_m"], cr["speed_mps"]
    atm = isa(h_c)
    non_cruise = wt["non_cruise_fuel_fraction"]
    reserve_min = wt["reserve_minutes"]
    res["assumptions"].append("fuel for taxi, take-off, climb, descent and landing: fraction of take-off weight given in inputs.m21.weights.non_cruise_fuel_fraction; "
                              "reserve: minutes at the cruise fuel flow (inputs, not a certified value)")

    def breakdown(payload_kg, fuel_kg, label):
        tow = oew + payload_kg + fuel_kg
        w_ini = tow * G
        fuel_nc = non_cruise * tow
        p_req = power_required(v_c, w_ini * (1.0 - 0.5 * non_cruise), atm["rho"], s, cdmin, k)
        reserve = reserve_min * 60.0 * fuel_flow_w(c_p, p_req / eta)
        cruise_fuel = fuel_kg - fuel_nc - reserve
        if cruise_fuel <= 0.0:
            return {"case": label, "payload_kg": payload_kg, "fuel_kg": fuel_kg, "tow_kg": tow, "range_km": 0.0, "note": "no fuel left for cruise"}
        w_start = w_ini - fuel_nc * G
        w_end = w_start - cruise_fuel * G
        r1 = range_const_v_h(w_start, w_end, v_c, atm["rho"], s, cdmin, k, eta, c_p)
        ld_max = 0.5 / math.sqrt(cdmin * k)
        r_opt = range_const_attitude(w_start, w_end, ld_max, eta, c_p)
        return {"case": label, "payload_kg": payload_kg, "fuel_kg": fuel_kg, "tow_kg": tow, "non_cruise_fuel_kg": fuel_nc, "reserve_fuel_kg": reserve,
                "cruise_fuel_kg": cruise_fuel, "range_const_v_h_km": r1 / 1000.0, "range_const_v_h_nm": r1 / NM,
                "range_at_ld_max_attitude_km": r_opt / 1000.0, "range_at_ld_max_attitude_nm": r_opt / NM,
                "endurance_const_v_h_h": endurance_const_v_h(w_start, w_end, v_c, atm["rho"], s, cdmin, k, eta, c_p) / 3600.0,
                "p_required_at_start_kw": power_required(v_c, w_start, atm["rho"], s, cdmin, k) / 1000.0}

    a_fuel = min(fuel_cap, mtow - oew - pay_max)
    if a_fuel <= 0.0:
        raise SystemExit("OEW + maximum payload >= MTOW: no fuel can be carried with the maximum payload")
    b_pay = max(0.0, min(pay_max, mtow - oew - fuel_cap))
    pts = [breakdown(pay_max, a_fuel, "A: maximum payload"), breakdown(b_pay, min(fuel_cap, mtow - oew - b_pay), "B: maximum fuel at MTOW"),
           breakdown(0.0, fuel_cap, "C: ferry (zero payload, full tanks)")]
    res["cruise_condition"] = {"altitude_m": h_c, "speed_mps": v_c, "speed_kt": v_c / KT, "rho": atm["rho"],
                               "power_available_w": power_available(p_sl, eta, h_c), "power_required_w_at_mtow": power_required(v_c, w_n, atm["rho"], s, cdmin, k),
                               "sustainable": power_required(v_c, w_n, atm["rho"], s, cdmin, k) <= power_available(p_sl, eta, h_c)}
    res["payload_range"] = pts
    # --- despegue y aterrizaje (M04) ---
    to = d.get("takeoff")
    if to:
        ws_pa = w_n / s
        rho = isa(to.get("altitude_m", 0.0))["rho"]
        tw = to["thrust_to_weight_avg"]
        clmax_to, cl_to, cd_to, mu = to["clmax"], to["cl"], to["cd"], to["mu"]
        denom = tw - 0.605 / clmax_to * (cd_to - mu * cl_to) - mu
        if denom <= 0.0:
            res["takeoff"] = {"status": "T/W is insufficient to accelerate (denominator <= 0)"}
        else:
            ft = 1.21 * (ws_pa / m04.PA_PER_LBF_FT2) / (m04.G_FTS2 * (rho / m04.KGM3_PER_SLUGFT3) * clmax_to * denom)
            res["takeoff"] = {"ground_run_m": ft / m04.FT_PER_M, "equation": "Ec. 3-1 inverted for the ground run (M04)", "thrust_to_weight_avg": tw}
    ld = d.get("landing")
    if ld:
        ws_pa = (ld.get("mass_kg", mtow) * G) / s
        rho = isa(ld.get("altitude_m", 0.0))["rho"]
        res["landing"] = {"ground_roll_m": m04.landing_distance_m(ws_pa, rho, ld["clmax"], ld["cl_ldg"], ld["cd_ldg"], ld["mu_brake"], ld["free_roll_s"],
                                                                  ld.get("h_obst_m", 15.0), ld.get("tgr_w", 0.0), True),
                          "total_over_obstacle_m": m04.landing_distance_m(ws_pa, rho, ld["clmax"], ld["cl_ldg"], ld["cd_ldg"], ld["mu_brake"], ld["free_roll_s"],
                                                                          ld.get("h_obst_m", 15.0), ld.get("tgr_w", 0.0), False), "equations": "Eqs. 3-13/3-14 (M04)"}
    return res, depends


def run(project: dict) -> dict:
    result, depends = evaluate(project)
    prj.record(project, "m21", result, "conceptual", REFERENCES, sorted(set(depends)))
    return result
