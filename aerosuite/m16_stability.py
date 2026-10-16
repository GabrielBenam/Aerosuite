"""M16 Estabilidad estatica y dinamica (Gudmundsson Tabla 1-4 pasos 16 y 17; Caps. 24 y 25; Etkin Caps. 4 y 6).

Nivel conceptual. Estatica longitudinal (Cap. 24): CL_alpha del ala y de la cola (Ec. 9-72 de M09b), gradiente de
estela d(eps)/d(alpha) = 2 CL_alpha_W / (pi AR) (Ecs. 8-28 y 24-91), punto neutro con mando fijo (Ec. 24-132), margen
estatico, C_M_alpha (Ec. 24-129), C_M0 (Ec. 24-127) y limites de CG (el minimo/maximo de SM los da la Sec. 24.3.4).
Estatica lateral-direccional (Cap. 25): C_Ybeta y C_Nbeta de la cola vertical (Ecs. 25-12, 25-14, 25-28) y del
fuselaje (Ec. 25-29, Munk). Dinamica: se arman las matrices de estado linealizadas (Etkin Sec. 4.9, Ecs. 4.9,18 y
4.9,19) con ejes de estabilidad y se calculan los autovalores; periodo de Lanchester y amortiguamiento 1/(sqrt2 L/D)
para el fugoide (Etkin Sec. 6.3). Gudmundsson no desarrolla modos dinamicos (Cap. 24, "Action Items"): se usa Etkin.
Derivadas que el libro no da en forma legible o que dependen de flow5 (polar tipo 7) entran como dato con su origen.
SI interno (kg, m, s, rad). Las matrices de los ejemplos B747 de Etkin (Tablas 6.1, 6.6, 6.7) reproducen los
autovalores del libro (pruebas)."""
import math

import numpy as np

from . import project as prj
from .m09b_wing import cl_alpha_helmbold

REFERENCES = [
    "GUD Sec. 24.2.8, Ecs. 8-28 y 24-89 a 24-93 (gradiente de estela d(eps)/d(alpha) = 2 CL_alpha_W/(pi AR)), PDF 990",
    "GUD Sec. 24.2.5 (4)-(5), Ecs. 24-80 a 24-82 (CM_q = 1.1 CM_q_HT, CM_alpha_dot de la cola), PDF 987",
    "GUD Sec. 24.3.4, Ecs. 24-129 a 24-133 y Ejemplo 24-6 (hn = 0.5917, CM_alpha = -0.3721 1/rad, CM0 = -0.005675), PDF 1008-1010",
    "GUD Sec. 24.3.4 (texto): hn tipico 0.4-0.6 en AG; SM minimo 8 % a 10 %, maximo 28 % a 30 %, PDF 1008 (+-1)",
    "GUD Sec. 25.3, Ecs. 25-12 a 25-14, 25-27/25-28 (cola vertical), 25-29 y 24-103 (fuselaje, Munk): inicio de la seccion en PDF 1034; la pagina exacta de cada ecuacion no se verifico",
    "GUD Sec. 24.2.6, Ecs. 24-100, 24-103 a 24-108, Figs. 24-29/24-30, Ejemplos 24-3/24-4 (fuselaje, Munk-Multhopp), PDF 993-996 (marcadores [p. 994]-[p. 996]); D-44",
    "ETK Sec. 4.9, Ecs. 4.9,18 y 4.9,19 (matrices de estado), PDF 120 (+-1); Sec. 6.2 y Tabla 6.1/6.2 (B747 longitudinal), PDF 178; Sec. 6.7 (B747 lateral), PDF 201",
    "ETK Sec. 6.3, aproximacion de Lanchester al fugoide (T = pi sqrt(2) u0/g; zeta = 1/(sqrt(2) L/D) como lo cita el modulo), PDF 185",
    "PDF = marcador [p. N] del texto convertido (impreso = PDF - 46 en Gudmundsson, PDF - 13 en Etkin); +-1 pagina",
]
G = 9.80665
SM_MIN, SM_MAX = 0.10, 0.30          # Sec. 24.3.4: minimo 8-10 %, maximo 28-30 % (se toma el extremo conservador)
CN_BETA_RANGE = (0.03, 0.2)          # Sec. 25.3: +0.03 < CN_beta < +0.2 1/rad
CL_BETA_RANGE = (-0.12, -0.03)       # Sec. 25.4.2: -0.12 < CL_beta < -0.03 1/rad


# --------------------------------------------------------------------------- estatica longitudinal
def downwash_gradient(cl_alpha_w: float, ar_w: float) -> float:
    """Ecs. 8-28 y 24-91: d(eps)/d(alpha) = 2 CL_alpha_W / (pi AR) (teoria de la cantidad de movimiento)."""
    return 2.0 * cl_alpha_w / (math.pi * ar_w)


def neutral_point(cl_alpha_w, cl_alpha_ht, ar_w, v_ht, eta_ht=1.0, h_ac=0.25, dcm_alpha_fuselage=0.0) -> dict:
    """Ec. 24-132: h_n = h_ac + eta V_HT (CL_alpha_HT/CL_alpha_W) (1 - d eps/d alpha); el fuselaje (Munk-Multhopp) desplaza
    h_n hacia delante en -dCM_alpha_fus/CL_alpha_W (dato; 0 si no se aporta). Gradiente de estela: Ec. 24-91."""
    de = downwash_gradient(cl_alpha_w, ar_w)
    tail = eta_ht * v_ht * cl_alpha_ht / cl_alpha_w * (1.0 - de)
    return {"h_n": h_ac + tail - dcm_alpha_fuselage / cl_alpha_w, "h_n_wing_ht": h_ac + tail, "downwash_gradient": de,
            "tail_contribution": tail}


def cm_alpha(cl_alpha_w, cl_alpha_ht, ar_w, v_ht, h_cg, eta_ht=1.0, h_ac=0.25, dcm_alpha_fuselage=0.0) -> float:
    """Ec. 24-129 (planeo, sin empuje): C_M_alpha = CL_alpha_W (h_cg - h_ac) - eta V_HT CL_alpha_HT (1 - d eps/d alpha) + fus."""
    de = downwash_gradient(cl_alpha_w, ar_w)
    return cl_alpha_w * (h_cg - h_ac) - eta_ht * v_ht * cl_alpha_ht * (1.0 - de) + dcm_alpha_fuselage


def cm0(cm_ac_w, cl0_w, h_cg, h_ac, cm_ac_ht=0.0, cl0_ht=0.0, l_ht_cg_over_c=0.0, eta_ht=1.0, v_ht=0.0, cl_alpha_ht=0.0,
        i_ht_rad=0.0, eps0=0.0) -> float:
    """Ec. 24-127 (CM0 = CM_ac,W + CL0_W (h_cg - h_ac) + terminos de la cola). Los terminos CM_ac,HT y CL0_HT del libro se
    reproducen tal cual (Ejemplo 24-6: CM0 = -0.005675); el efecto de la incidencia de la cola y de la estela residual
    -eta V_HT CL_alpha_HT (i_HT - eps0) sigue de la Ec. 24-93 y no lo ilustra el libro (D-36)."""
    del cm_ac_ht, cl0_ht, l_ht_cg_over_c    # nulos en el ejemplo del libro; sin dato legible para CL0_HT != 0
    return cm_ac_w + cl0_w * (h_cg - h_ac) - eta_ht * v_ht * cl_alpha_ht * (i_ht_rad - eps0)


def cg_limits(h_n: float, sm_min: float = SM_MIN, sm_max: float = SM_MAX) -> dict:
    """SM = 100 (h_n - h_cg) (Sec. 24.2.7): limite trasero h_n - SM_min y limite delantero h_n - SM_max (Sec. 24.3.4)."""
    return {"aft_h": h_n - sm_min, "forward_h": h_n - sm_max, "aft_pct_mgc": 100.0 * (h_n - sm_min),
            "forward_pct_mgc": 100.0 * (h_n - sm_max), "sm_min": sm_min, "sm_max": sm_max,
            "note": "el limite delantero por autoridad del elevador (CL_max con el CG delantero) queda para el analisis de trimado"}


# --------------------------------------------------------------------------- fuselaje: Munk-Multhopp (Cap. 24)
def upwash_gradient_forward(x_over_c: float) -> float:
    """Gradiente de upwash por delante del ala, Ecs. 24-104 (curva 1, x/c_MGC 0.4-2.5) y 24-105 (curva 2, 0.1-1.2), digitalizadas por
    el autor de la Fig. 24-29 (derecha). Regla (D-44): curva 2 para x/c < 0.4 y curva 1 en adelante; fuera del dominio graficado
    se toma el valor del extremo (x/c < 0.1 -> 0.1; x/c > 2.5 -> 2.5) en vez de extrapolar el polinomio."""
    x = min(max(x_over_c, 0.1), 2.5)
    if x < 0.4:
        return 1.74611 * x ** -0.4254
    return 1.4758 - 0.40485 * x + 0.09107 * x * x


def munk_multhopp(x_m, width_m, c_root_m, c_mgc_m, s_m2, l_h_m, de_dalpha, alpha_zl_plus_if_deg=None, x_wing_le_m=0.0) -> dict:
    """Aporte del fuselaje a C_M0 y C_M_alpha por Munk-Multhopp (GUD Sec. 24.2.6, Ecs. 24-100, 24-103, 24-107, 24-108, Figs. 24-29/24-30 y
    Ejemplo 24-3). Segmentos entre estaciones consecutivas por delante del borde de ataque de la raiz del ala (x < x_wing_le) y por detras
    de su borde de salida (x > x_wing_le + c_root); el tramo bajo el ala no aporta a C_M_alpha. Por delante, gradiente de upwash
    d(beta)/d(alpha) segun las curvas 1-2 con x = distancia del centro del segmento al borde de ataque del ala; por detras
    d(beta)/d(alpha) = (x_i/l_h)(1 - d eps/d alpha), x_i medida desde el borde de ataque de la raiz y l_h desde ese mismo punto al centro
    aerodinamico de la cola horizontal (asi lo usa la Tabla 24-4). Ecuaciones por grado (36.5 = 180/pi/... del libro):
    C_M_alpha = sum(w_f^2 dbeta/dalpha dx) / (36.5 S c_MGC)  [1/grado; el libro no multiplica por k2-k1 y el Ejemplo 24-3 lo confirma],
    C_M0 = (k2-k1)/(36.5 S c_MGC) sum(w_f^2 (alpha_ZLW + i_f) dx). x positiva hacia atras. alpha_zl_plus_if_deg: escalar o lista
    (un valor por segmento y, si se da lista, uno mas para el tramo del ala al final de los delanteros); None omite C_M0."""
    x, w = np.asarray(x_m, float), np.asarray(width_m, float)
    order = np.argsort(x)
    x, w = x[order], w[order]
    le, te = x_wing_le_m, x_wing_le_m + c_root_m
    wi = lambda xx: float(np.interp(xx, x, w))
    fwd_x = [v for v in x if v < le] + [le]
    aft_x = [te] + [v for v in x if v > te]
    segs = []
    for xa, xb in zip(fwd_x[:-1], fwd_x[1:]):
        xc = le - 0.5 * (xa + xb)
        segs.append({"region": "forward", "x_start_m": xa, "x_end_m": xb, "dx_m": xb - xa, "x_c_ahead_m": xc,
                     "w_f_m": 0.5 * (wi(xa) + wi(xb)), "dbeta_dalpha": upwash_gradient_forward(xc / c_mgc_m)})
    for xa, xb in zip(aft_x[:-1], aft_x[1:]):
        xi = 0.5 * (xa + xb) - le
        segs.append({"region": "aft", "x_start_m": xa, "x_end_m": xb, "dx_m": xb - xa, "x_c_behind_le_m": xi,
                     "w_f_m": 0.5 * (wi(xa) + wi(xb)), "dbeta_dalpha": xi / l_h_m * (1.0 - de_dalpha)})
    k = k2_minus_k1((x.max() - x.min()) / w.max())
    denom = 36.5 * s_m2 * c_mgc_m
    sum9 = sum(g["w_f_m"] ** 2 * g["dbeta_dalpha"] * g["dx_m"] for g in segs)
    out = {"segments": segs, "k2_minus_k1": k, "fineness": (x.max() - x.min()) / w.max(), "sum_wf2_dbeta_dx": sum9,
           "cm_alpha_per_deg": sum9 / denom, "cm_alpha_per_rad": sum9 / denom * 180.0 / math.pi}
    if alpha_zl_plus_if_deg is not None:
        wing = {"region": "wing", "dx_m": c_root_m, "w_f_m": wi(le)}   # el Ejemplo 24-3 usa el ancho en el borde de ataque (4.08 ft)
        rows = segs[:len(fwd_x) - 1] + [wing] + segs[len(fwd_x) - 1:]
        ang = list(alpha_zl_plus_if_deg) if np.ndim(alpha_zl_plus_if_deg) else [float(alpha_zl_plus_if_deg)] * len(rows)
        if len(ang) != len(rows):
            raise ValueError(f"alpha_zl_plus_if_deg needs {len(rows)} values (segments + wing row), got {len(ang)}")
        sum7 = sum(r["w_f_m"] ** 2 * a * r["dx_m"] for r, a in zip(rows, ang))
        out.update({"sum_wf2_angle_dx": sum7, "cm0": k * sum7 / denom})
    return out


# --------------------------------------------------------------------------- cola vertical y fuselaje
def k_yvt(b_vt_over_2r1: float) -> float:
    """Ec. 25-13 (K_YVT): 0.76 para b_VT/2r1 < 2, 1.0 para > 3.5 y lineal entre ambos; el tramo central es ilegible en el PDF
    y se reconstruye por continuidad con los dos extremos (D-36)."""
    x = b_vt_over_2r1
    return 0.76 if x < 2.0 else 1.0 if x > 3.5 else 0.76 + 0.16 * (x - 2.0)


def sidewash_factor(s_vt_over_s: float, sweep_c4_deg: float, z_w_over_d_fus: float, ar_w: float) -> float:
    """Ec. 25-14: eta_VT (1 + d sigma/d beta) = 0.724 + 3.06 (S_VT/S)/(1 + cos Lambda_c/4) + 0.4 z_W/d_FUS + 0.009 AR_W."""
    return 0.724 + 3.06 * s_vt_over_s / (1.0 + math.cos(math.radians(sweep_c4_deg))) + 0.4 * z_w_over_d_fus + 0.009 * ar_w


def cn_beta_vt(cl_alpha_vt, s_vt, l_vt_cg, s, b, sidewash) -> float:
    """Ec. 25-28: C_Nbeta,VT = V_VT CL_alpha_VT eta (1 + d sigma/d beta), V_VT = S_VT l_VT / (S b)."""
    return s_vt * l_vt_cg / (s * b) * cl_alpha_vt * sidewash


def cy_beta_vt(cl_alpha_vt, s_vt, s, sidewash, k_y=1.0) -> float:
    """Ec. 25-12: C_Ybeta,VT = -K_YVT CL_alpha_VT eta (1 + d sigma/d beta) S_VT/S."""
    return -k_y * cl_alpha_vt * sidewash * s_vt / s


def k2_minus_k1(fineness: float) -> float:
    """Ec. 24-103 (ajuste digitalizado de Fig. 24-29): 1 - 1/f + (0.24 f^3 - 5.6 f^2 + 44 f - 72)/1000."""
    f = fineness
    return 1.0 - 1.0 / f + (0.24 * f ** 3 - 5.6 * f ** 2 + 44.0 * f - 72.0) / 1000.0


def cn_beta_fuselage(stations_m, widths_m, length_m, depth_m, s, b) -> float:
    """Ec. 25-29 (Munk), por radian: C_Nbeta,FUS = -2 (k2-k1) / (S b) * integral(w_f^2 dx). Trapecios sobre las estaciones."""
    x, w = np.asarray(stations_m, float), np.asarray(widths_m, float)
    integral = float(np.sum(0.5 * (w[1:] ** 2 + w[:-1] ** 2) * np.diff(x)))
    return -2.0 * k2_minus_k1(length_m / depth_m) * integral / (s * b)


# --------------------------------------------------------------------------- dinamica
def longitudinal_matrix(p: dict) -> np.ndarray:
    """Etkin Ec. 4.9,18 (ejes de estabilidad, theta0 = 0, vuelo nivelado). Estado [u, w, q, theta]. `p`: u0, rho, S, c, m, Iy, g y
    derivadas adimensionales Cx_u, Cx_a, Cz_u, Cz_a, Cz_q, Cz_adot, Cm_u, Cm_a, Cm_q, Cm_adot (con u^, alpha, q^ = q c/2u0,
    alpha_dot^ = alpha_dot c/2u0). Cualquier sistema de unidades coherente."""
    u0, rho, s, c, m, iy = p["u0"], p["rho"], p["S"], p["c"], p["m"], p["Iy"]
    g = p.get("g", G)
    qs = 0.5 * rho * u0 * u0 * s
    xu, xw = qs * p["Cx_u"] / u0, qs * p["Cx_a"] / u0
    zu, zw = qs * p["Cz_u"] / u0, qs * p["Cz_a"] / u0
    zq, zwd = qs * c * p["Cz_q"] / (2 * u0), qs * c * p["Cz_adot"] / (2 * u0 * u0)
    mu, mw = qs * c * p["Cm_u"] / u0, qs * c * p["Cm_a"] / u0
    mq, mwd = qs * c * c * p["Cm_q"] / (2 * u0), qs * c * c * p["Cm_adot"] / (2 * u0 * u0)
    m_mat = np.array([[m, 0, 0, 0], [0, m - zwd, 0, 0], [0, -mwd, iy, 0], [0, 0, 0, 1.0]])
    f_mat = np.array([[xu, xw, 0, -m * g], [zu, zw, zq + m * u0, 0], [mu, mw, mq, 0], [0, 0, 1.0, 0]])
    return np.linalg.solve(m_mat, f_mat)


def lateral_matrix(p: dict) -> np.ndarray:
    """Etkin Ec. 4.9,19 (ejes de estabilidad, theta0 = 0). Estado [v, p, r, phi]. `p`: u0, rho, S, b, m, Ix, Iz, Ixz, g y
    CY_b, Cl_b, Cn_b, CY_p, Cl_p, Cn_p, CY_r, Cl_r, Cn_r (p^ = p b/2u0, r^ = r b/2u0). Convencion: Ixz = integral(x z dm)
    en la Ec. 4.9,19 (en el B747, Ixz = -0.156e7 slug ft2)."""
    u0, rho, s, b, m = p["u0"], p["rho"], p["S"], p["b"], p["m"]
    ix, iz, ixz = p["Ix"], p["Iz"], p["Ixz"]
    g = p.get("g", G)
    qs = 0.5 * rho * u0 * u0 * s
    yv, yp, yr = qs * p["CY_b"] / u0, qs * b * p["CY_p"] / (2 * u0), qs * b * p["CY_r"] / (2 * u0)
    lv, lp, lr = qs * b * p["Cl_b"] / u0, qs * b * b * p["Cl_p"] / (2 * u0), qs * b * b * p["Cl_r"] / (2 * u0)
    nv, np_, nr = qs * b * p["Cn_b"] / u0, qs * b * b * p["Cn_p"] / (2 * u0), qs * b * b * p["Cn_r"] / (2 * u0)
    m_mat = np.array([[m, 0, 0, 0], [0, ix, -ixz, 0], [0, -ixz, iz, 0], [0, 0, 0, 1.0]])
    f_mat = np.array([[yv, yp, yr - m * u0, m * g], [lv, lp, lr, 0], [nv, np_, nr, 0], [0, 1.0, 0, 0]])
    return np.linalg.solve(m_mat, f_mat)


def classify_longitudinal(eigs) -> dict:
    """Fugoide (par complejo de menor frecuencia) y periodo corto (el de mayor); si el periodo corto degenera en dos raices reales se informan."""
    pairs = sorted([e for e in eigs if e.imag > 1e-9], key=lambda e: abs(e))
    reals = sorted([e.real for e in eigs if abs(e.imag) <= 1e-9])
    out = {"modes": []}
    for name, e in zip(("phugoid", "short_period"), pairs):
        out[name] = _mode(e)
    if len(pairs) < 2:
        out["real_roots"] = reals
        out["note"] = "the short-period mode degenerated into non-oscillatory roots (overdamped)"
    return out


def classify_lateral(eigs) -> dict:
    complex_ = [e for e in eigs if e.imag > 1e-9]
    reals = sorted([e.real for e in eigs if abs(e.imag) <= 1e-9], key=abs)
    out = {}
    if complex_:
        out["dutch_roll"] = _mode(complex_[0])
    if len(reals) >= 2:
        out["spiral"] = _real_mode(reals[0])
        out["roll"] = _real_mode(reals[-1])
    elif reals:
        out["real_roots"] = reals
    return out


def _mode(e) -> dict:
    wn = abs(e)
    sigma = e.real
    return {"eigenvalue": [e.real, e.imag], "wn_rad_s": wn, "zeta": -sigma / wn, "period_s": 2 * math.pi / e.imag,
            "t_half_s": math.log(2) / -sigma if sigma < 0 else None, "t_double_s": math.log(2) / sigma if sigma > 0 else None,
            "stable": bool(sigma < 0)}


def _real_mode(lam: float) -> dict:
    return {"eigenvalue": lam, "time_constant_s": (-1.0 / lam) if lam < 0 else None,
            "t_half_s": math.log(2) / -lam if lam < 0 else None, "t_double_s": math.log(2) / lam if lam > 0 else None,
            "stable": bool(lam < 0)}


def lanchester(u0: float, l_over_d: float, g: float = G) -> dict:
    """Etkin Sec. 6.3: T = pi sqrt(2) u0/g (B747: 107 s) y zeta ~ 1/(sqrt(2) L/D)."""
    return {"period_s": math.pi * math.sqrt(2.0) * u0 / g, "zeta": 1.0 / (math.sqrt(2.0) * l_over_d)}


# --------------------------------------------------------------------------- modulo
def _need(project, key, hint):
    if key not in project["outputs"]:
        raise SystemExit(f"outputs.{key} is missing ({hint}): run {key} first")
    return project["outputs"][key]["result"]


def evaluate(project: dict) -> tuple[dict, list]:
    d = prj.need_inputs(project, "m16", ["flight"])
    depends = ["m09b", "m08", "m13"]
    w = _need(project, "m09b", "wing")
    t = _need(project, "m08", "tails")
    cg = _need(project, "m13", "CG and inertia")
    pf = w["planform"]
    s, b, ar, c = pf["area_m2"], pf["span_m"], pf["aspect_ratio"], pf["cmgc_m"]
    cla_w = w["lift_curve_slope"]["cl_alpha_recommended_per_rad"]
    ht, vt = t["horizontal_tail"], t["vertical_tail"]
    cla_ht = d.get("cl_alpha_ht_per_rad") or cl_alpha_helmbold(ht["aspect_ratio"])
    cla_vt = d.get("cl_alpha_vt_per_rad") or cl_alpha_helmbold(2.0 * vt["aspect_ratio"])   # con el plano de simetria: AR efectivo doble
    eta = d.get("eta_ht", 1.0)
    h_ac = d.get("h_ac_wing", 0.25)
    x_cg = cg["cg_m"][0]
    h_cg = (x_cg - pf["xmgc_le_m"]) / c
    l_ht = d.get("l_ht_cg_m") or (ht["arm_m"] + pf["mgc_quarter_chord_x_m"] - x_cg)
    l_vt = d.get("l_vt_cg_m") or (vt["arm_m"] + pf["mgc_quarter_chord_x_m"] - x_cg)
    v_ht = ht["area_m2"] * l_ht / (s * c)
    v_vt = vt["area_m2"] * l_vt / (s * b)
    res = {"level": "conceptual", "units": "SI (kg, m, s, rad)", "assumptions": []}
    # --- fuselaje (Munk-Multhopp, Ecs. 24-100 a 24-108): estaciones de inputs.m16.fuselage_sections o de la geometria de M10 ---
    fs = d.get("fuselage_sections")
    if not fs and "m10" in project["outputs"]:
        fus10 = next(k for k in project["outputs"]["m10"]["result"]["components"] if k["type"] == "fuselage")
        fs = {"x_m": [st["x_m"] for st in fus10["stations"]], "width_m": [2.0 * st["radius_m"] for st in fus10["stations"]],
              "length_m": fus10["length_m"], "depth_m": 2.0 * fus10["max_radius_m"], "origin": "M10 (secciones circulares: ancho = 2 r)"}
        depends.append("m10")
    de0 = downwash_gradient(cla_w, ar)
    fus_mm = None
    if "dcm_alpha_fuselage_per_rad" in d:
        dcm_fus = d["dcm_alpha_fuselage_per_rad"]
        fus_origin = "inputs.m16.dcm_alpha_fuselage_per_rad (dato del usuario)"
    elif fs:
        l_h = pf["mgc_quarter_chord_x_m"] + ht["arm_m"]
        fus_mm = munk_multhopp(fs["x_m"], fs["width_m"], pf["root_chord_m"], c, s, l_h, de0,
                               d.get("alpha_zl_plus_if_deg"), 0.0)
        dcm_fus = fus_mm["cm_alpha_per_rad"]
        fus_origin = fs.get("origin", "inputs.m16.fuselage_sections")
    else:
        dcm_fus = 0.0
        fus_origin = None
        res["assumptions"].append("fuselage contribution to CM_alpha (Munk-Multhopp, Eq. 24-108) not computed (no inputs.m16.fuselage_sections "
                                  "and no M10 geometry): h_n is optimistic (the fuselage is destabilizing)")
        prj.add_assumption(project, "m16", "dcm_alpha_fuselage_per_rad", 0.0, "sin geometria de fuselaje: aporte del fuselaje omitido (D-44)")
    res["punto_neutro_optimista"] = fus_origin is None
    npt = neutral_point(cla_w, cla_ht, ar, v_ht, eta, h_ac, dcm_fus)
    sm = npt["h_n"] - h_cg
    cma = cm_alpha(cla_w, cla_ht, ar, v_ht, h_cg, eta, h_ac, dcm_fus)
    res["longitudinal_static"] = {
        "cl_alpha_wing_per_rad": cla_w, "cl_alpha_ht_per_rad": cla_ht, "v_ht": v_ht, "l_ht_cg_m": l_ht, "eta_ht": eta,
        "h_cg": h_cg, "h_ac_wing": h_ac, **npt, "static_margin": sm, "cm_alpha_per_rad": cma,
        "x_neutral_point_m": pf["xmgc_le_m"] + npt["h_n"] * c, "cg_limits": cg_limits(npt["h_n"], d.get("sm_min", SM_MIN), d.get("sm_max", SM_MAX)),
        "stable": cma < 0.0, "sm_within_guidance": d.get("sm_min", SM_MIN) <= sm <= d.get("sm_max", SM_MAX),
        "hn_guidance_ga": [0.4, 0.6], "fuselage_contribution": {
            "included": fus_origin is not None, "origin": fus_origin, "dcm_alpha_per_rad": dcm_fus,
            "dh_n": -dcm_fus / cla_w, **({"k2_minus_k1": fus_mm["k2_minus_k1"], "fineness": fus_mm["fineness"],
                                          "segments": fus_mm["segments"], "cm_alpha_per_deg": fus_mm["cm_alpha_per_deg"],
                                          "cm0_fuselage": fus_mm.get("cm0")} if fus_mm else {})}}
    if "cm_ac_w" in d:
        res["longitudinal_static"]["cm0"] = cm0(d["cm_ac_w"], d.get("cl0_w", 0.0), h_cg, h_ac, eta_ht=eta, v_ht=v_ht,
                                                cl_alpha_ht=cla_ht, i_ht_rad=math.radians(d.get("i_ht_deg", 0.0)),
                                                eps0=d.get("eps0_rad", 0.0))
    # --- lateral-direccional estatico ---
    sw = d.get("sidewash") or sidewash_factor(vt["area_m2"] / s, pf["sweep_c4_deg"], d.get("z_w_over_d_fus", 0.0), ar)
    lat = {"v_vt": v_vt, "l_vt_cg_m": l_vt, "cl_alpha_vt_per_rad": cla_vt, "sidewash_factor": sw,
           "cn_beta_vt_per_rad": cn_beta_vt(cla_vt, vt["area_m2"], l_vt, s, b, sw),
           "cy_beta_vt_per_rad": cy_beta_vt(cla_vt, vt["area_m2"], s, sw, d.get("k_yvt", 1.0))}
    cn_tot = lat["cn_beta_vt_per_rad"]
    if fs and "length_m" in fs:
        lat["cn_beta_fuselage_per_rad"] = cn_beta_fuselage(fs["x_m"], fs["width_m"], fs["length_m"], fs["depth_m"], s, b)
        cn_tot += lat["cn_beta_fuselage_per_rad"]
    else:
        res["assumptions"].append("CN_beta of the fuselage (Eq. 25-29) not computed without fuselage geometry (inputs.m16.fuselage_sections or M10): CN_beta is optimistic")
    cn_tot += d.get("cn_beta_other_per_rad", 0.0)
    lat["cn_beta_total_per_rad"] = cn_tot
    lat["cn_beta_in_typical_range"] = CN_BETA_RANGE[0] <= cn_tot <= CN_BETA_RANGE[1]
    lat["directionally_stable"] = cn_tot > 0.0
    if "cl_beta_per_rad" in d:
        lat["cl_beta_per_rad"] = d["cl_beta_per_rad"]
        lat["cl_beta_in_typical_range"] = CL_BETA_RANGE[0] <= d["cl_beta_per_rad"] <= CL_BETA_RANGE[1]
        lat["laterally_stable"] = d["cl_beta_per_rad"] < 0.0
    else:
        res["assumptions"].append("CL_beta (dihedral effect, Eqs. 25-53 to 25-62) is not computed (digitized DATCOM polynomials, illegible "
                                  "in the converted text): give inputs.m16.cl_beta_per_rad or flow5 derivatives")
    res["lateral_static"] = lat
    # --- dinamica ---
    fl = d["flight"]
    u0, rho = fl["speed_mps"], fl["density_kgm3"]
    m = cg["total_mass_kg"] if "mass_kg" not in fl else fl["mass_kg"]
    q = 0.5 * rho * u0 * u0
    cl = m * G / (q * s)
    k_ind = fl.get("k", w["span_efficiency"]["k_induced"])
    cd0, cd0_source = fl.get("cd0"), fl.get("cd0_source", "inputs.m16.flight.cd0 (M20 will compute it)")
    if cd0 is None:
        m20 = project["outputs"].get("m20")
        if not m20:
            raise SystemExit("inputs.m16.flight.cd0 is missing: give it or run m20 first")
        cd0, cd0_source = m20["result"]["buildup"]["cd_min"], "M20 component buildup (outputs.m20)"
        depends.append("m20")
    cd = cd0 + k_ind * cl * cl
    res["flight_condition"] = {"speed_mps": u0, "density_kgm3": rho, "mass_kg": m, "q_pa": q, "cl": cl, "cd": cd, "l_over_d": cl / cd,
                               "cd0": cd0, "cd0_source": cd0_source, "k": k_ind}
    inr = cg["inertia_about_cg_kgm2"]
    de = npt["downwash_gradient"]
    lc = l_ht / c
    lp = {"u0": u0, "rho": rho, "S": s, "c": c, "m": m, "Iy": inr["iyy"], "Cx_u": fl.get("cx_u", -2.0 * cd), "Cx_a": cl - 2.0 * k_ind * cl * cla_w,
          "Cz_u": -2.0 * cl, "Cz_a": -(cla_w + cd) - eta * ht["area_m2"] / s * cla_ht * (1 - de),
          "Cz_q": -2.0 * eta * cla_ht * v_ht, "Cz_adot": -2.0 * eta * cla_ht * v_ht * de,
          "Cm_u": fl.get("cm_u", 0.0), "Cm_a": cma, "Cm_q": -1.1 * 2.0 * eta * cla_ht * v_ht * lc,
          "Cm_adot": -2.0 * eta * cla_ht * v_ht * lc * de}
    res["longitudinal_derivatives"] = {k: v for k, v in lp.items() if k.startswith("C")}
    res["longitudinal_derivatives"]["origin"] = ("CZ_alpha, CM_alpha, CZ_q, CM_q (x1.1, Ref. [6]), CM_alpha_dot from the tail only (Eqs. 24-51, 24-80 to "
                                                 "24-82); CX_u = -2 CD, CZ_u = -2 CL, CM_u = 0 (M < 0.3, constant thrust: assumed); wing "
                                                 "contributions to CM_q and CL_q neglected (Sec. 24.2.5: 'the wing contribution is small')")
    res["assumptions"].append("longitudinal dynamics: CX_u = -2 CD, CZ_u = -2 CL, CM_u = 0 and wing CM_q/CL_q neglected; propeller effects not included")
    a_long = longitudinal_matrix(lp)
    eig_l = np.linalg.eigvals(a_long)
    res["longitudinal_dynamics"] = {"A": a_long.tolist(), "eigenvalues": [[e.real, e.imag] for e in eig_l], **classify_longitudinal(eig_l),
                                    "lanchester": lanchester(u0, cl / cd)}
    ld = d.get("lateral_derivatives")
    if ld:
        full = {"CY_b": lat["cy_beta_vt_per_rad"], "Cn_b": cn_tot, "CY_p": 0.0, "CY_r": 0.0}
        full.update(ld)
        miss = [k for k in ("CY_b", "Cl_b", "Cn_b", "Cl_p", "Cn_p", "Cl_r", "Cn_r") if k not in full]
        if miss:
            raise SystemExit("inputs.m16.lateral_derivatives is missing: " + ", ".join(miss))
        lat_p = {"u0": u0, "rho": rho, "S": s, "b": b, "m": m, "Ix": inr["ixx"], "Iz": inr["izz"], "Ixz": inr["ixz"], **full}
        a_lat = lateral_matrix(lat_p)
        eig_t = np.linalg.eigvals(a_lat)
        res["lateral_dynamics"] = {"derivatives": full, "A": a_lat.tolist(), "eigenvalues": [[e.real, e.imag] for e in eig_t],
                                   **classify_lateral(eig_t), "origin": d.get("lateral_derivatives_origin", "user input")}
    else:
        res["lateral_dynamics"] = {"status": "not computed: Cl_p, Cl_r, Cn_p, Cn_r (and CL_beta) are not available in legible form in "
                                             "Gudmundsson Ch. 25; give inputs.m16.lateral_derivatives (e.g. from flow5 type 7)"}
    return res, depends


def run(project: dict) -> dict:
    result, depends = evaluate(project)
    prj.record(project, "m16", result, "conceptual", REFERENCES, sorted(set(depends)))
    return result
