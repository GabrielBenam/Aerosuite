"""M18b Controles: momentos de charnela y fuerzas en la palanca (Gudmundsson Tabla 1-4 paso 18; Sec. 24.4).

Nivel conceptual. Para alerones, timon de profundidad y timon de direccion: geometria de la superficie movil (cuerda y area detras de
la charnela, Tabla 24-6), momento de charnela H = q c_f S_f C_H (Ec. 24-148) con C_H = C_H0 + C_Halpha alpha + C_Hdelta delta
+ C_Hdelta_t delta_t (Ecs. 24-150 a 24-154), fuerza en la palanca F = G H (Ec. 24-149) con la ganancia del sistema manual simple del
timon de profundidad (Ecs. 24-159 a 24-164), angulo de flotacion delta = -(C_Halpha/C_Hdelta) alpha (Ec. 24-155) y su efecto
sobre la pendiente de sustentacion de la cola, factor 1 - tau_e C_Halpha/C_Hdelta (Ec. 24-157), con el punto neutro con mando libre.
Las derivadas de charnela C_Halpha, C_Hdelta no se estiman (el libro remite a Refs. [6, 12, 27]): son datos de entrada con origen; sin
ellas solo se informa la geometria. Los limites de fuerza del piloto (14 CFR 23.143(c)) son datos opcionales: no se citan valores sin
comprobarlos. No incluye compensadores (Sec. 24.4.3, Ref. [28]), cuernos (24.4.4) ni cargas del sistema de control en estructura
(Ansys). SI interno (N, m, rad)."""
import math

from . import project as prj
from .m16_stability import neutral_point

REFERENCES = [
    "GUD Sec. 24.4.1, Ecs. 24-148 a 24-155 (momento de charnela, coeficientes C_H, flotacion), PDF 1012-1014 / impr. 1013-1015",
    "GUD Tabla 24-6 (cuerda y deflexiones tipicas de superficies de control), PDF 1014",
    "GUD Sec. 24.4.2, Ecs. 24-156 a 24-164 (sistema manual simple, ganancias G_S y G_delta) y Ec. 24-157 (factor 1 - tau C_Halpha/C_Hdelta), PDF 1015-1016",
    "GUD Sec. 24.2.7, Ec. 24-86 y Fig. 24-21 (efectividad del timon de profundidad tau_e) y Ejemplo 24-6 (d) (tau = 0.5066 para r_e = 0.3), PDF 1001 / 1009",
]
# Tabla 24-6: cuerda c_f/c y deflexiones (grados) TEU = borde de salida arriba, TED = abajo, TEL/TER = izquierda/derecha.
TABLE_24_6 = {"aileron": {"cf_over_c": (0.20, 0.35), "up_deg": (15.0, 25.0), "down_deg": (15.0, 20.0)},
              "elevator": {"cf_over_c": (0.20, 0.35), "up_deg": (20.0, 27.0), "down_deg": (15.0, 20.0)},
              "rudder": {"cf_over_c": (0.20, 0.40), "up_deg": (20.0, 25.0), "down_deg": (20.0, 25.0)}}


def tau_elevator(r_e: float) -> float:
    """Ec. 24-86: tau_e = -4.66 r^4 + 8.79 r^3 - 6.44 r^2 + 2.85 r + 0.0316 (r_e = c_e/c_HT; signos reconstruidos con el Ejemplo 24-6: r = 0.3 -> 0.5066)."""
    return -4.66 * r_e ** 4 + 8.79 * r_e ** 3 - 6.44 * r_e ** 2 + 2.85 * r_e + 0.0316


def hinge_moment(q: float, c_f: float, s_f: float, c_h: float) -> float:
    """Ec. 24-148: H = q c_f S_f C_H."""
    return q * c_f * s_f * c_h


def hinge_coefficient(ch0=0.0, ch_alpha=0.0, alpha=0.0, ch_delta=0.0, delta=0.0, ch_delta_t=0.0, delta_t=0.0) -> float:
    """Ecs. 24-150 a 24-154 (angulos en rad)."""
    return ch0 + ch_alpha * alpha + ch_delta * delta + ch_delta_t * delta_t


def float_angle(ch_alpha: float, ch_delta: float, alpha: float) -> float:
    """C_H = 0 (mando libre, sin compensador) en la Ec. 24-151: delta = -(C_Halpha/C_Hdelta) alpha (Ec. 24-155)."""
    return -ch_alpha / ch_delta * alpha


def free_lift_slope_factor(tau: float, ch_alpha: float, ch_delta: float) -> float:
    """Ec. 24-157: CL_alpha,HT(libre) = CL_alpha,HT (1 - tau_e C_Halpha/C_Hdelta); se deduce de CL = CL_alpha alpha + CL_alpha tau delta con delta flotante."""
    return 1.0 - tau * ch_alpha / ch_delta


def balance_class(ch_alpha: float, tol: float = 1e-9) -> str:
    """Sec. 24.4.2: C_Halpha < 0 subcompensado (desestabiliza), = 0 sin compensar, > 0 sobrecompensado (estabiliza, mando opuesto a la intencion)."""
    return "underbalanced" if ch_alpha < -tol else "overbalanced" if ch_alpha > tol else "unbalanced"


def manual_elevator_gearing(l1: float, l2: float, e: float, stick_deflection_rad: float) -> dict:
    """Ecs. 24-159 a 24-164: dx = l2 sin(dS); F_e = F_S l1/(l2 cos dS); delta_e = asin(l2 sin(dS)/e); HM = F_e e.
    Devuelve la ganancia de fuerza F_S/HM = l2 cos(dS)/(l1 e) [1/m] y la de giro delta_e/delta_S."""
    dx = l2 * math.sin(stick_deflection_rad)
    delta_e = math.asin(dx / e)
    return {"pushrod_shift_m": dx, "delta_e_rad": delta_e, "force_gain_per_m": l2 * math.cos(stick_deflection_rad) / (l1 * e),
            "rotation_gain": delta_e / stick_deflection_rad}


def strip_geometry(semispan: float, root_chord: float, tip_chord: float, y_in: float, y_out: float, cf_over_c: float) -> dict:
    """Superficie movil entre las fracciones de semienvergadura y_in..y_out (por lado, cuerda lineal; semispan = semienvergadura o altura de la cola vertical): cuerda media c_f y area S_f detras de la charnela."""
    half = semispan
    c = lambda y: root_chord + (tip_chord - root_chord) * y
    mid = c(0.5 * (y_in + y_out))
    length = (y_out - y_in) * half
    return {"strip_length_m": length, "mean_chord_m": mid, "c_f_m": cf_over_c * mid, "s_f_m2": cf_over_c * mid * length}


def _check_table(name, cf_over_c, up_deg, down_deg):
    t = TABLE_24_6[name]
    return {"cf_over_c": cf_over_c, "cf_range": list(t["cf_over_c"]), "cf_within_range": t["cf_over_c"][0] <= cf_over_c <= t["cf_over_c"][1],
            "up_deg": up_deg, "up_range_deg": list(t["up_deg"]), "up_within_range": up_deg <= t["up_deg"][1],
            "down_deg": down_deg, "down_range_deg": list(t["down_deg"]), "down_within_range": down_deg <= t["down_deg"][1]}


def _surface(name, d, planform, q, sides):
    cf = d["cf_over_c"]
    geo = strip_geometry(planform["semispan_m"], planform["root_chord_m"], planform["tip_chord_m"], d.get("y_in", 0.0), d.get("y_out", 1.0), cf)
    out = {"geometry": {**geo, "s_f_total_m2": sides * geo["s_f_m2"], "sides": sides},
           "table_24_6": _check_table(name, cf, d.get("delta_up_deg", 0.0), d.get("delta_down_deg", 0.0))}
    if "ch_delta_per_rad" not in d:
        out["hinge"] = {"status": "not computed: give C_Hdelta (and C_Halpha for the elevator and rudder), Refs. [6, 12, 27] of Sec. 24.4"}
        return out
    chd, cha = d["ch_delta_per_rad"], d.get("ch_alpha_per_rad", 0.0)
    cases = []
    for v in d["speeds_mps"]:
        qv = 0.5 * q["rho"] * v * v
        for sign, key in ((-1.0, "delta_up_deg"), (1.0, "delta_down_deg")):
            if d.get(key, 0.0) == 0.0:
                continue
            delta = sign * math.radians(d[key])
            ch = hinge_coefficient(d.get("ch0", 0.0), cha, math.radians(d.get("alpha_deg", 0.0)), chd, delta)
            h = hinge_moment(qv, geo["c_f_m"], geo["s_f_m2"], ch)       # una superficie
            cases.append({"speed_mps": v, "delta_deg": math.degrees(delta), "c_h": ch, "hinge_moment_nm": h})
    out["hinge"] = {"cases": cases, "ch_delta_per_rad": chd, "ch_alpha_per_rad": cha, "balance": balance_class(cha),
                    "origin": d.get("ch_origin", "user input"),
                    "max_abs_hinge_moment_nm": max((abs(c["hinge_moment_nm"]) for c in cases), default=None),
                    "rule_of_thumb": "C_Halpha = 0 and a small negative C_Hdelta (Sec. 24.4.1 (5)); this is guidance, not a requirement",
                    "c_h_delta_negative": chd < 0.0}
    g = d.get("gearing")
    if g and "force_gain_per_m" in g:
        gain = g["force_gain_per_m"]
    elif g and {"l1_m", "l2_m", "e_m", "stick_deflection_deg"} <= g.keys():
        mg = manual_elevator_gearing(g["l1_m"], g["l2_m"], g["e_m"], math.radians(g["stick_deflection_deg"]))
        gain = mg["force_gain_per_m"]
        out["gearing"] = mg
    else:
        gain = None
    if gain is not None and cases:
        for c in cases:
            c["stick_force_n"] = gain * c["hinge_moment_nm"] * sides        # las superficies de ambos lados cargan la misma palanca
        fmax = max(abs(c["stick_force_n"]) for c in cases)
        out["control_force"] = {"max_abs_stick_force_n": fmax, "force_gain_per_m": gain, "equation": "Eq. 24-149 / 24-160",
                                "limit_n": d.get("pilot_force_limit_n")}
        if d.get("pilot_force_limit_n") is not None:
            out["control_force"]["within_limit"] = fmax <= d["pilot_force_limit_n"]
    else:
        out["control_force"] = {"status": "not computed: give inputs.m18b.<surface>.gearing {l1_m, l2_m, e_m, stick_deflection_deg} or {force_gain_per_m}"}
    return out


def evaluate(project: dict) -> tuple[dict, list]:
    d = prj.need_inputs(project, "m18b", ["speeds_mps", "rho_kgm3"])
    w = project["outputs"].get("m09b")
    t = project["outputs"].get("m08")
    if not w or not t:
        raise SystemExit("outputs.m09b and outputs.m08 are missing: run m09b and m08 first")
    depends = ["m09b", "m08"]
    wing, tails = w["result"], t["result"]
    q = {"rho": d["rho_kgm3"]}
    res = {"level": "conceptual", "units": "SI (N, m, rad)", "assumptions": []}
    surfaces = {"aileron": (wing["planform"], 2), "elevator": (tails["horizontal_tail"], 2), "rudder": (tails["vertical_tail"], 1)}
    for name, (pf, sides) in surfaces.items():
        sd = d.get(name)
        if not sd:
            res["assumptions"].append(f"{name} not analyzed: no inputs.m18b.{name}")
            continue
        sd = {"speeds_mps": d["speeds_mps"], **sd}
        res[name] = _surface(name, sd, _planform(name, pf), q, sides)
    if "elevator" in res and "ch_alpha_per_rad" in res["elevator"].get("hinge", {}):
        res["elevator"]["free_elevator"] = _free_elevator(project, d["elevator"], res, depends)
    return res, depends


def _planform(name, pf):
    """Semienvergadura (ala, cola horizontal) o altura (cola vertical) y cuerdas de raiz y punta."""
    return {"semispan_m": pf["span_m"] if name == "rudder" else pf["span_m"] / 2.0, "root_chord_m": pf["root_chord_m"], "tip_chord_m": pf["tip_chord_m"]}


def _free_elevator(project, ed, res, depends):
    h = res["elevator"]["hinge"]
    tau = ed.get("tau_e") or tau_elevator(ed["cf_over_c"])
    cha, chd = h["ch_alpha_per_rad"], h["ch_delta_per_rad"]
    out = {"tau_e": tau, "lift_slope_factor": free_lift_slope_factor(tau, cha, chd), "balance": h["balance"],
           "float_angle_deg_per_deg_alpha": math.degrees(float_angle(cha, chd, math.radians(1.0)))}
    m16 = project["outputs"].get("m16")
    if m16:
        ls = m16["result"]["longitudinal_static"]
        fixed = neutral_point(ls["cl_alpha_wing_per_rad"], ls["cl_alpha_ht_per_rad"], _ar_w(project), ls["v_ht"], ls["eta_ht"], ls["h_ac_wing"])
        free = neutral_point(ls["cl_alpha_wing_per_rad"], ls["cl_alpha_ht_per_rad"] * out["lift_slope_factor"], _ar_w(project), ls["v_ht"],
                             ls["eta_ht"], ls["h_ac_wing"])
        out["neutral_point"] = {"h_n_stick_fixed_without_fuselage": fixed["h_n"], "h_n_stick_free_without_fuselage": free["h_n"],
                                "stick_free_margin": free["h_n"] - ls["h_cg"], "stick_fixed_margin": fixed["h_n"] - ls["h_cg"],
                                "note": "same assumptions as M16 (no fuselage contribution)"}
        depends.append("m16")
    return out


def _ar_w(project):
    return project["outputs"]["m09b"]["result"]["planform"]["aspect_ratio"]


def run(project: dict) -> dict:
    result, depends = evaluate(project)
    prj.record(project, "m18b", result, "conceptual", REFERENCES, sorted(set(depends)))
    return result
