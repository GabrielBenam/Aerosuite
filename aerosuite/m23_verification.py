"""M23 Verificacion de requisitos (Gudmundsson Tabla 1-4 paso 23).

Nivel conceptual. Para cada requisito devuelve `cumple`, `no cumple` o `no evaluable`, con valor calculado, limite, margen y referencia.
Solo se implementan criterios cuyo texto se leyo: 14 CFR Part 23 vigente (eCFR, consultado 2026-10-16: 23.2110, 23.2120, 23.2130), la
Tabla 1-2/1-3 y las Secs. 3.2, 24.3.4 y 25.3 de Gudmundsson, y los requisitos de diseno del propio proyecto (los que M01/M04 reciben como
entrada). Los criterios sin texto verificado, o cuya configuracion el modelo conceptual no representa, quedan `no evaluable` con la razon:
no se inventan umbrales (D-47). La base de cada verificacion se declara (`basis`: norma | libro | requisito del proyecto)."""
import math

from . import project as prj

G = 9.80665
RHO0 = 1.225
KT = 0.514444
FT = 0.3048
REFERENCES = [
    "14 CFR 23.2110 (eCFR vigente, leido 2026-10-16): determinar la velocidad de perdida para cada configuracion; el apartado numerico (c) de la version anterior ya no existe",
    "14 CFR 23.2120 (eCFR vigente, leido 2026-10-16): gradientes de ascenso minimos (a) todos los motores 8.3 % (nivel 1-2 baja velocidad, tren fijo) y 4 % (nivel 1-2 alta velocidad, nivel 3, nivel 4 monomotor); (c) ascenso frustrado 3 %",
    "14 CFR 23.2130 (eCFR vigente, leido 2026-10-16): la distancia de aterrizaje se determina desde 50 ft (15 m); no fija un limite numerico",
    "GUD Sec. 1.3, Tablas 1-2 y 1-3 (PDF 58) y cita del limite de 61 KCAS (impr. 12, PDF 57; texto de la version anterior del Part 23)",
    "GUD Sec. 24.3.4 (margen estatico minimo 8-10 %, maximo 28-30 %), PDF 1008; Sec. 25.3 (CN_beta 0.03-0.2 1/rad); Etkin Sec. 6.1 (estabilidad dinamica: partes reales negativas)",
]
SM_MIN, SM_MAX = 0.10, 0.30
CN_MIN = 0.03


def _check(rid, text, value, limit, op, unit, ref, basis, note=None):
    ok = value <= limit * (1 + 1e-9) + 1e-12 if op == "<=" else value >= limit * (1 - 1e-9) - 1e-12
    margin = (limit - value) if op == "<=" else (value - limit)
    return {"id": rid, "requirement": text, "status": "cumple" if ok else "no cumple", "value": value, "limit": limit, "operator": op,
            "unit": unit, "margin": margin, "margin_pct_of_limit": 100.0 * margin / limit if limit else None, "reference": ref,
            "basis": basis, **({"note": note} if note else {})}


def _na(rid, text, reason, ref, basis, value=None, limit=None, unit=None):
    out = {"id": rid, "requirement": text, "status": "no evaluable", "reason": reason, "reference": ref, "basis": basis}
    if value is not None:
        out.update({"value": value, "limit": limit, "unit": unit})
    return out


def evaluate(project: dict) -> tuple[dict, list]:
    d = project["inputs"].get("m23", {})
    out = project["outputs"]
    res = lambda m: out[m]["result"] if m in out else None
    depends = [m for m in ("m01", "m04", "m09b", "m13", "m16", "m21") if m in out]
    m01, m04, m09b, m13, m16, m21 = (res(m) for m in ("m01", "m04", "m09b", "m13", "m16", "m21"))
    items = []
    brief = project["inputs"].get("m04", {}).get("concept", {}).get("designbrief", {})

    # --- categoria (Tabla 1-2) y reglamento ---
    if m01:
        for c in m01["checks"]:
            if c["name"] == "mtow":
                items.append(_check("cat_mtow", "MTOW dentro del limite de la categoria (Tabla 1-2)", c["value_lbf"], c["limit_lbf"], "<=", "lbf",
                                    "GUD Tabla 1-2, PDF 58", "libro"))
            elif c["name"] == "occupants":
                items.append(_check("cat_occupants", "Ocupantes dentro del limite de la categoria (Tabla 1-2)", c["value"], c["limit"], "<=", "-",
                                    "GUD Tabla 1-2, PDF 58", "libro"))
            elif c["name"].startswith("vso"):
                items.append(_check("vso_61kcas", "V_S0 maxima de 61 KCAS para monomotores y multimotores <= 6000 lbf", c["value_kcas"],
                                    c["limit_kcas"], "<=", "KCAS", "GUD Sec. 1.3 (impr. 12, PDF 57); el eCFR vigente de 23.2110 ya no trae este numero",
                                    "libro", "con el dato de entrada de M01 (vso_kcas_max), no con el valor calculado: ver vso_calculada"))
    else:
        items.append(_na("categoria", "Categoria y limites de la Tabla 1-2", "falta outputs.m01", "GUD Tabla 1-2", "libro"))

    # --- velocidad de perdida calculada ---
    vso_req = project["inputs"].get("m01", {}).get("vso_kcas_max")
    clmax_l = project["inputs"].get("m21", {}).get("landing", {}).get("clmax")
    if m21 and clmax_l and vso_req:
        w, s = m21["weights"]["mtow_kg"] * G, m21["aero"]["s_m2"]
        vso = math.sqrt(2.0 * w / (RHO0 * s * clmax_l)) / KT
        items.append(_check("vso_calculada", "V_S0 calculada (MTOW, configuracion de aterrizaje, nivel del mar) no mayor que el requisito de M01",
                            vso, float(vso_req), "<=", "KCAS", "14 CFR 23.2110 (determinar V_S por configuracion); requisito de M01", "requisito del proyecto",
                            "V_S0 = sqrt(2 W / (rho0 S CLmax_ldg)); CLmax de aterrizaje es dato de M21"))
    else:
        items.append(_na("vso_calculada", "V_S0 calculada contra el requisito de M01", "faltan outputs.m21, inputs.m21.landing.clmax o inputs.m01.vso_kcas_max",
                         "14 CFR 23.2110", "norma"))

    # --- desempeno contra los requisitos del proyecto (designbrief de M04) ---
    if m21 and "groundrun_m" in brief:
        items.append(_check("takeoff_ground_run", "Rodadura de despegue no mayor que el requisito", m21["takeoff"]["ground_run_m"], brief["groundrun_m"], "<=", "m",
                            "requisito de inputs.m04.designbrief.groundrun_m; M21 (Ec. 3-1)", "requisito del proyecto",
                            "usa thrust_to_weight_avg dado en inputs.m21"))
    else:
        items.append(_na("takeoff_ground_run", "Rodadura de despegue", "falta outputs.m21 o designbrief.groundrun_m", "GUD Cap. 3", "requisito del proyecto"))
    ldg = project["inputs"].get("m04", {}).get("landing")
    if m21 and ldg:
        key = "total_over_obstacle_m" if ldg.get("kind", "total") == "total" else "ground_roll_m"
        items.append(_check("landing_distance", "Distancia de aterrizaje no mayor que el requisito (desde el obstaculo declarado; 23.2130 pide determinarla desde 50 ft)",
                            m21["landing"][key], ldg["distance_m"], "<=", "m", "requisito de inputs.m04.landing; 14 CFR 23.2130(a) (50 ft, sin limite numerico)",
                            "requisito del proyecto"))
    else:
        items.append(_na("landing_distance", "Distancia de aterrizaje", "falta outputs.m21 o inputs.m04.landing", "14 CFR 23.2130", "norma"))
    if m21 and "climbrate_fpm" in brief:
        sl = m21["performance_at_mtow"].get("0.0")
        if sl:
            items.append(_check("climb_rate_sl", "Velocidad de ascenso maxima a nivel del mar no menor que el requisito", sl["rc_max_fpm"], brief["climbrate_fpm"], ">=", "fpm",
                                "requisito de designbrief.climbrate_fpm; M21", "requisito del proyecto"))
        else:
            items.append(_na("climb_rate_sl", "Ascenso maximo a nivel del mar", "M21 no evaluo la altitud 0 m", "M21", "requisito del proyecto"))
    if m21 and "cruisespeed_ktas" in brief:
        cc = m21["cruise_condition"]
        ok_alt = abs(cc["altitude_m"] - brief.get("cruisealt_m", cc["altitude_m"])) < 1.0
        if ok_alt:
            items.append(_check("cruise_speed", "Velocidad de crucero requerida sostenible (potencia disponible >= requerida)", cc["power_required_w_at_mtow"],
                                cc["power_available_w"], "<=", "W", "requisito de designbrief.cruisespeed_ktas; M21", "requisito del proyecto",
                                f"a {cc['speed_kt']:.1f} KTAS"))
        else:
            items.append(_na("cruise_speed", "Velocidad de crucero", "la altitud de crucero de M21 no coincide con la del requisito", "M21", "requisito del proyecto"))
    if m21 and "servceil_m" in brief:
        items.append(_check("service_ceiling", "Techo de servicio no menor que el requisito", m21["ceilings_at_mtow"]["service_m"], brief["servceil_m"], ">=", "m",
                            "requisito de designbrief.servceil_m; M21 (100 fpm)", "requisito del proyecto"))
    # --- punto de diseno (W/S) ---
    if m04 and m09b and "m21" in out:
        ws = m21["weights"]["mtow_kg"] * G / m09b["planform"]["area_m2"]
        lim = min(m04["wingloading_limits_pa"].values())
        items.append(_check("wing_loading_limits", "W/S del avion no mayor que los limites de perdida y aterrizaje de M04", ws, lim, "<=", "Pa",
                            "GUD Sec. 3.2.3 y Ec. 3-13/3-14; M04", "libro"))
    # --- gradientes 14 CFR 23.2120 ---
    if m01 and m21:
        lvl, perf = m01["new_part23"]["certification_level"], m01["new_part23"]["performance_level"]
        engines = project["inputs"].get("m01", {}).get("engines", 1)
        req = None
        if lvl in (1, 2) and perf == "low":
            req = 0.067 if d.get("seaplane") else 0.083
        elif (lvl in (1, 2) and perf == "high") or lvl == 3 or (lvl == 4 and engines == 1):
            req = 0.04
        sl = m21["performance_at_mtow"].get("0.0")
        if req is None or not sl:
            items.append(_na("climb_gradient_23_2120a", "Gradiente de ascenso con todos los motores (23.2120(a))",
                             "nivel 4 multimotor: el apartado leido no fija el valor para este caso, o falta M21 a nivel del mar", "14 CFR 23.2120(a)", "norma"))
        else:
            g_clean = sl["rc_max_mps"] / sl["v_best_rc_mps"]
            if g_clean < req:
                it = _check("climb_gradient_23_2120a", "Gradiente de ascenso con todos los motores (23.2120(a)), configuracion limpia como cota superior",
                            g_clean, req, ">=", "-", "14 CFR 23.2120(a)", "norma", "la configuracion limpia da un gradiente mayor que el de la configuracion inicial de ascenso: si ni asi cumple, no cumple")
            else:
                it = _na("climb_gradient_23_2120a", "Gradiente de ascenso con todos los motores (23.2120(a))",
                         "M21 no modela la configuracion de ascenso inicial (flaps de despegue, tren): el gradiente de la configuracion limpia es solo una condicion necesaria",
                         "14 CFR 23.2120(a)", "norma", g_clean, req, "-")
            items.append(it)
        items.append(_na("balked_landing_23_2120c", "Ascenso frustrado, 3 % (23.2120(c))",
                         "falta modelar la configuracion de aterrizaje con empuje de despegue y la velocidad de referencia (el texto leido no fija la velocidad)",
                         "14 CFR 23.2120(c)", "norma"))
    # --- estabilidad (M16) ---
    if m16:
        ls, lat = m16["longitudinal_static"], m16["lateral_static"]
        items.append(_check("static_margin_min", "Margen estatico no menor que el minimo de guia", ls["static_margin"], d.get("sm_min", SM_MIN), ">=", "c_MGC",
                            "GUD Sec. 24.3.4 (8-10 %; se toma 10 %)", "libro", "criterio de diseno del libro, no un requisito de la norma leida"))
        items.append(_check("static_margin_max", "Margen estatico no mayor que el maximo de guia", ls["static_margin"], d.get("sm_max", SM_MAX), "<=", "c_MGC",
                            "GUD Sec. 24.3.4 (28-30 %; se toma 30 %)", "libro", "criterio de diseno del libro, no un requisito de la norma leida"))
        items.append(_check("cm_alpha_negative", "C_M_alpha < 0 (estabilidad estatica longitudinal)", ls["cm_alpha_per_rad"], 0.0, "<=", "1/rad",
                            "GUD Cap. 24", "libro"))
        items.append(_check("cn_beta_positive", "C_N_beta > 0 (estabilidad direccional)", lat["cn_beta_total_per_rad"], CN_MIN, ">=", "1/rad",
                            "GUD Sec. 25.3 (0.03 < C_Nbeta < 0.2)", "libro", "cota inferior del intervalo tipico del libro"))
        if m16["punto_neutro_optimista"]:
            items.append(_na("neutral_point_fuselage", "Punto neutro con el aporte del fuselaje", "M16 corrio sin geometria de fuselaje: el punto neutro es optimista (D-44)",
                             "GUD Sec. 24.2.6", "libro"))
        dyn = m16.get("longitudinal_dynamics", {})
        for name in ("phugoid", "short_period"):
            if name in dyn:
                items.append(_check(f"dynamic_{name}", f"Modo {name}: parte real negativa (estable)", dyn[name]["eigenvalue"][0], 0.0, "<=", "1/s",
                                    "Etkin Sec. 6.1 (definicion de estabilidad)", "libro", "solo el signo; los niveles de calidad de vuelo no se evaluan"))
    else:
        items.append(_na("stability", "Estabilidad estatica y dinamica", "falta outputs.m16", "GUD Caps. 24-25", "libro"))
    # --- CG (M13) ---
    if m13 and m13.get("envelope"):
        cloud = m13.get("loading_cloud", [])
        bad = [c["id"] for c in cloud if not c["inside_envelope"]]
        if cloud:
            items.append({"id": "cg_envelope", "requirement": "CG dentro de la envolvente declarada en todas las combinaciones de carga",
                          "status": "no cumple" if bad or not m13["envelope"].get("empty_cg_inside", True) else "cumple",
                          "value": len(cloud) - len(bad), "limit": len(cloud), "unit": "combinaciones dentro", "failed": bad,
                          "reference": "GUD Sec. 6.7.2; limites de CG de inputs.m13.envelope (" + m13["envelope"].get("limits_source", "") + ")",
                          "basis": "requisito del proyecto"})
        else:
            items.append(_na("cg_envelope", "CG dentro de la envolvente", "no hay combinaciones de carga en M13", "GUD Sec. 6.7.2", "requisito del proyecto"))
    else:
        items.append(_na("cg_envelope", "CG dentro de la envolvente", "falta outputs.m13 o la envolvente", "GUD Sec. 6.7.2", "requisito del proyecto"))
    # --- criterios sin texto leido ---
    for rid, text in (("controllability_23_2135", "Controlabilidad y maniobrabilidad (23.2135)"),
                      ("stability_23_2145", "Estabilidad (23.2145)"), ("stall_characteristics_23_2150", "Caracteristicas de perdida (23.2150)")):
        items.append(_na(rid, text, "texto normativo no leido ni citado en esta corrida; no se inventan umbrales", "14 CFR Part 23, Subparte B", "norma"))
    counts = {s: sum(1 for i in items if i["status"] == s) for s in ("cumple", "no cumple", "no evaluable")}
    overall = "no cumple" if counts["no cumple"] else ("cumple" if counts["cumple"] else "no evaluable")
    result = {"level": "conceptual", "units": "SI salvo donde la unidad se indica", "items": items, "counts": counts, "overall": overall,
              "overall_rule": "no cumple si algun requisito evaluable no cumple; cumple si hay al menos uno evaluable y ninguno falla; los no evaluables se cuentan aparte y no equivalen a cumplir",
              "failed": [i["id"] for i in items if i["status"] == "no cumple"], "not_evaluable": [i["id"] for i in items if i["status"] == "no evaluable"],
              "regulatory_note": "base: 14 CFR Part 23 vigente (eCFR) y Tablas 1-2/1-3 de Gudmundsson; no sustituye a una demostracion de cumplimiento"}
    return result, depends



def run(project: dict) -> dict:
    result, depends = evaluate(project)
    prj.record(project, "m23", result, "conceptual", REFERENCES, sorted(set(depends)))
    return result
