"""Contrast of M16 (stability, conceptual) with a flow5 type 7 stability polar (P-3, F6).

Reads the operating point written by flow5 (via flow5_results) and the flow5 plane configuration (JSON of flow5_xml) and returns, side by side:

* derivatives: M16 formulas (Gudmundsson Ch. 24-25; same ones as ``m16_stability.evaluate``) against flow5's values at the same flight condition,
  CG and inertia (flow5 uses the inertia of its point masses/wing/tail masses; the very same Ixx, Iyy, Izz, Ixz are given to M16);
* longitudinal modes: (a) M16 derivatives + flow5 inertia, (b) flow5 derivatives through the M16 matrices (checks the equations of motion), (c) flow5 modes;
* lateral modes: (a) M16 CY_b/Cn_b + flow5 Cl_b, Cl_p, Cn_p, Cl_r, Cn_r (M16 has no legible source for these, D-34), (b) all flow5 derivatives through the
  M16 matrix, (c) flow5 modes.

Nothing is tuned: the geometry-dependent quantities come from the book formulas, and each difference is reported, not corrected.
"""
from __future__ import annotations

import math

import numpy as np

from . import m16_stability as m
from .m09b_wing import cl_alpha_helmbold

G = m.G


def _trap(wing):
    """Area, MAC, y_MAC, and (for the tail) planar quantities of one semi-wing described by sections (y, chord, xoffset)."""
    secs = wing["sections"]
    area = mac_n = ymac_n = x_n = 0.0
    for a, b in zip(secs[:-1], secs[1:]):
        dy = b["y_m"] - a["y_m"]
        c1, c2 = a["chord_m"], b["chord_m"]
        ds = 0.5 * (c1 + c2) * dy
        cm = 2.0 / 3.0 * (c1 * c1 + c1 * c2 + c2 * c2) / (c1 + c2)
        ym = a["y_m"] + dy / 3.0 * (c1 + 2 * c2) / (c1 + c2)
        xle = a.get("xoffset_m", 0.0) + (b.get("xoffset_m", 0.0) - a.get("xoffset_m", 0.0)) * (ym - a["y_m"]) / dy
        area += ds
        mac_n += ds * cm
        ymac_n += ds * ym
        x_n += ds * (xle + 0.25 * cm)
    return {"area_half": area, "mac": mac_n / area, "x_ac_rel": x_n / area, "span_half": secs[-1]["y_m"] - secs[0]["y_m"]}


def geometry(cfg: dict) -> dict:
    """S, b, MAC, root chord, wing LE x, tail areas, aerodynamic centres (x of the c/4 of the MAC), from a flow5_xml configuration."""
    w = {x["type"]: x for x in cfg["wings"]}
    mw, el, fin = w["MAINWING"], w["ELEVATOR"], w["FIN"]
    tm, te, tf = _trap(mw), _trap(el), _trap(fin)
    s, b = 2 * tm["area_half"], 2 * tm["span_half"]
    x0 = mw.get("position_m", [0, 0, 0])[0]
    return {"S": s, "b": b, "ar": b * b / s, "mac": tm["mac"], "c_root": mw["sections"][0]["chord_m"],
            "x_ac_w": x0 + tm["x_ac_rel"], "x_le_w": x0 + 0.0,
            "S_h": 2 * te["area_half"], "b_h": 2 * te["span_half"], "x_ac_h": el["position_m"][0] + te["x_ac_rel"],
            "S_v": tf["area_half"], "h_v": tf["span_half"], "x_ac_v": fin["position_m"][0] + tf["x_ac_rel"],
            "sweep_c4_deg": 0.0}


def m16_derivatives(g: dict, flight: dict, cg_x: float, fuselage=None) -> dict:
    """Derivatives that M16 computes (the formulas of ``m16_stability.evaluate``) at CG x = cg_x and the flight condition of flow5."""
    s, b, c, ar = g["S"], g["b"], g["mac"], g["ar"]
    cla_w = cl_alpha_helmbold(ar)
    ar_h, ar_v = g["b_h"] ** 2 / g["S_h"], 2.0 * g["h_v"] ** 2 / g["S_v"]
    cla_h, cla_v = cl_alpha_helmbold(ar_h), cl_alpha_helmbold(ar_v)
    l_h, l_v = g["x_ac_h"] - cg_x, g["x_ac_v"] - cg_x
    v_h, v_v = g["S_h"] * (g["x_ac_h"] - g["x_ac_w"]) / (s * c), g["S_v"] * l_v / (s * b)
    v_h_cg = g["S_h"] * l_h / (s * c)                      # tail volume about the CG (used in the damping terms)
    de = m.downwash_gradient(cla_w, ar)
    h_cg = (cg_x - g["x_ac_w"]) / c + 0.25
    npt = m.neutral_point(cla_w, cla_h, ar, v_h_cg)             # as m16_stability.evaluate: tail volume about the CG in both
    npt_ac = m.neutral_point(cla_w, cla_h, ar, v_h)              # tail volume from the wing AC (independent of the CG), for information
    cma = m.cm_alpha(cla_w, cla_h, ar, v_h_cg, h_cg)
    cl, k = flight["CL"], flight["k_induced"]
    cd = flight["CD"]
    sw = m.sidewash_factor(g["S_v"] / s, g["sweep_c4_deg"], 0.0, ar)
    out = {"Cx_u": -2.0 * cd, "Cx_a": cl - 2.0 * k * cl * cla_w, "Cz_u": -2.0 * cl,
           "Cz_a": -(cla_w + cd) - g["S_h"] / s * cla_h * (1 - de), "Cz_q": -2.0 * cla_h * v_h_cg,
           "Cz_adot": -2.0 * cla_h * v_h_cg * de, "Cm_u": 0.0, "Cm_a": cma, "Cm_q": -1.1 * 2.0 * cla_h * v_h_cg * l_h / c,
           "Cm_adot": -2.0 * cla_h * v_h_cg * (l_h / c) * de,
           "CY_b": m.cy_beta_vt(cla_v, g["S_v"], s, sw), "Cn_b": m.cn_beta_vt(cla_v, g["S_v"], l_v, s, b, sw)}
    if fuselage:
        out["Cn_b"] += m.cn_beta_fuselage(fuselage["x_m"], fuselage["width_m"], fuselage["length_m"], fuselage["depth_m"], s, b)
    out["_aux"] = {"cl_alpha_w": cla_w, "cl_alpha_h": cla_h, "cl_alpha_v": cla_v, "v_h": v_h, "v_v": v_v, "l_h_cg": l_h, "l_v_cg": l_v,
                   "downwash_gradient": de, "x_np_wing_tail_m": g["x_ac_w"] - 0.25 * c + npt["h_n"] * c,
                   "x_np_wing_tail_ac_based_m": g["x_ac_w"] - 0.25 * c + npt_ac["h_n"] * c, "sidewash_factor": sw,
                   "h_cg": h_cg, "static_margin": npt["h_n"] - h_cg}
    return out


def flow5_derivatives(opp: dict) -> dict:
    """Derivatives of a flow5 operating point in the M16 names. flow5's file labels the Z-force derivatives 'CLa'/'CLq' but they are
    C_Z derivatives (negative for a stable lift curve: the log prints them as CZa/CZq)."""
    sc, dv = opp["scalars"], opp["derivatives"]
    return {"Cx_u": dv["CXu"], "Cx_a": dv["CXa"], "Cz_u": dv["CZu"], "Cz_a": sc["CLa"], "Cz_q": sc["CLq"], "Cm_u": dv["Cmu"],
            "Cm_a": dv["Cma"], "Cm_q": dv["Cmq"], "Cm_adot": 0.0, "Cz_adot": 0.0,
            "CY_b": sc["CYb"], "CY_p": sc["CYp"], "CY_r": sc["CYr"], "Cl_b": dv["Clb"], "Cl_p": dv["Clp"], "Cl_r": dv["Clr"],
            "Cn_b": dv["Cnb"], "Cn_p": dv["Cnp"], "Cn_r": dv["Cnr"]}


def parse_state_matrices(log_text: str) -> dict:
    """The longitudinal ([u, w, q, theta]) and lateral ([v, p, r, phi]) state matrices that flow5 prints in its log (SI, stability axes)."""
    lines = log_text.splitlines()
    out = {}
    for key, title in (("longitudinal", "Longitudinal state matrix"), ("lateral", "Lateral state matrix")):
        i = next((n for n, l in enumerate(lines) if title in l), None)
        if i is None:
            continue
        out[key] = np.array([[float(v) for v in lines[i + 1 + r].split()] for r in range(4)])
    return out


def flow5_derivatives_from_matrix(a_lon: np.ndarray, u0: float, rho: float, s: float, mass: float) -> dict:
    """C_Zu implied by the flow5 longitudinal state matrix (Z_u = A[1,0] m, Z_w_dot = 0). The 'CZu' column of flow5's files
    (about -1e-5 here) is inconsistent with its own matrix and log (Zu = -202 N s/m -> C_Zu = -2 C_L = -0.648)."""
    qs_u = 0.5 * rho * u0 * s
    return {"Cz_u": a_lon[1, 0] * mass / qs_u}


def modes(lon_eigs, lat_eigs) -> dict:
    out = {}
    lon = m.classify_longitudinal(lon_eigs)
    for k in ("phugoid", "short_period"):
        if k in lon:
            out[k] = {"wn_rad_s": lon[k]["wn_rad_s"], "zeta": lon[k]["zeta"], "freq_Hz": lon[k]["wn_rad_s"] / (2 * math.pi)}
    lat = m.classify_lateral(lat_eigs)
    if "dutch_roll" in lat:
        d = lat["dutch_roll"]
        out["dutch_roll"] = {"wn_rad_s": d["wn_rad_s"], "zeta": d["zeta"], "freq_Hz": d["wn_rad_s"] / (2 * math.pi)}
    for k in ("spiral", "roll"):
        if k in lat:
            out[k] = {"eigenvalue": lat[k]["eigenvalue"], "t_half_s": lat[k]["t_half_s"], "t_double_s": lat[k]["t_double_s"]}
    return out


def matrices(der: dict, u0, rho, s, b, c, mass, inertia, ixz_sign=1.0, g=G) -> tuple:
    """Longitudinal and lateral eigenvalues with the M16 matrices (Etkin Eqs. 4.9,18/19). ``ixz_sign`` selects the convention of the product of inertia."""
    lp = {"u0": u0, "rho": rho, "S": s, "c": c, "m": mass, "Iy": inertia["Iyy"], "g": g,
          **{k: der[k] for k in ("Cx_u", "Cx_a", "Cz_u", "Cz_a", "Cz_q", "Cz_adot", "Cm_u", "Cm_a", "Cm_q", "Cm_adot")}}
    la = {"u0": u0, "rho": rho, "S": s, "b": b, "m": mass, "Ix": inertia["Ixx"], "Iz": inertia["Izz"], "Ixz": ixz_sign * inertia["Ixz"], "g": g,
          **{k: der.get(k, 0.0) for k in ("CY_b", "CY_p", "CY_r", "Cl_b", "Cl_p", "Cl_r", "Cn_b", "Cn_p", "Cn_r")}}
    return np.linalg.eigvals(m.longitudinal_matrix(lp)), np.linalg.eigvals(m.lateral_matrix(la))


def contrast(opp: dict, polar_row: dict, cfg: dict, fuselage=None, log_text: str | None = None) -> dict:
    """Full side-by-side report (see the module docstring)."""
    g = geometry(cfg)
    sc = opp["scalars"]
    u0, mass, cg_x = sc["V_mps"], sc["mass_kg"], sc["CoG_x_m"]
    # density from the flow5 plane polar: q from lift = weight is not needed; the polar fluid is the ISA value of the configuration
    from .adrpy_core import atmosphere_table
    rho = atmosphere_table([float(cfg["analysis"].get("altitude_m", 0.0))], 0.0)["rows"][0]["density_kgm3"]
    inertia = {k: sc[f"{k}_kgm2"] for k in ("Ixx", "Iyy", "Izz", "Ixz")}
    flight = {"CL": sc["CL"], "CD": sc["CD"], "k_induced": sc["CD_induced"] / sc["CL"] ** 2}
    d16 = m16_derivatives(g, flight, cg_x, fuselage)
    d5 = flow5_derivatives(opp)
    state = parse_state_matrices(log_text) if log_text else {}
    if "longitudinal" in state:
        d5["Cz_u_file"] = d5["Cz_u"]
        d5.update(flow5_derivatives_from_matrix(state["longitudinal"], u0, rho, g["S"], mass))
    aux = d16.pop("_aux")
    common = [k for k in ("Cx_u", "Cx_a", "Cz_u", "Cz_a", "Cz_q", "Cm_a", "Cm_q", "CY_b", "Cn_b") if k in d5]
    table = {k: {"m16": d16[k], "flow5": d5[k], "rel_diff": (d16[k] - d5[k]) / abs(d5[k]) if abs(d5[k]) > 1e-9 else None} for k in common}
    # (a) M16 derivatives + flow5 lateral derivatives that M16 does not compute
    mix = {**d16, **{k: d5[k] for k in ("CY_p", "CY_r", "Cl_b", "Cl_p", "Cl_r", "Cn_p", "Cn_r")}}
    a_lon, a_lat = matrices(mix, u0, rho, g["S"], g["b"], g["mac"], mass, inertia)
    f_lon, f_lat = matrices(d5, u0, rho, g["S"], g["b"], g["mac"], mass, inertia)
    no_dot = {**mix, "Cm_adot": 0.0, "Cz_adot": 0.0}                # flow5 has no alpha_dot derivatives: same set without them
    n_lon, _ = matrices(no_dot, u0, rho, g["S"], g["b"], g["mac"], mass, inertia)
    flow5_modes = {"phugoid": {"freq_Hz": polar_row["phugoid_freq_Hz"], "zeta": polar_row["phugoid_damping"]},
                   "short_period": {"freq_Hz": polar_row["short_period_freq_Hz"], "zeta": polar_row["short_period_damping_ratio"]},
                   "dutch_roll": {"freq_Hz": polar_row["dutch_roll_freq_Hz"], "zeta": polar_row["dutch_roll_damping"]}}
    a_m16_lon = m.longitudinal_matrix({"u0": u0, "rho": rho, "S": g["S"], "c": g["mac"], "m": mass, "Iy": inertia["Iyy"],
                                       **{k: d16[k] for k in ("Cx_u", "Cx_a", "Cz_u", "Cz_a", "Cz_q", "Cz_adot", "Cm_u", "Cm_a", "Cm_q", "Cm_adot")}})
    out_matrix = {}
    if state:
        e_lon = np.linalg.eigvals(state["longitudinal"])
        e_lat = np.linalg.eigvals(state["lateral"])
        out_matrix = {"flow5_state_matrices": {k: v.tolist() for k, v in state.items()}, "modes_from_flow5_state_matrices": modes(e_lon, e_lat),
                      "m16_longitudinal_matrix": a_m16_lon.tolist()}
    return {**out_matrix, "geometry": g, "flight": {"u0_mps": u0, "rho_kgm3": rho, "mass_kg": mass, "cg_x_m": cg_x, "alpha_deg": sc["alpha_deg"], **flight},
            "inertia_kgm2": inertia, "m16_aux": aux, "derivatives": table,
            "modes_m16_with_flow5_lateral_derivatives": modes(a_lon, a_lat), "modes_flow5_derivatives_in_m16_matrices": modes(f_lon, f_lat),
            "longitudinal_eigenvalues_m16": [[e.real, e.imag] for e in a_lon], "longitudinal_eigenvalues_m16_without_alpha_dot": [[e.real, e.imag] for e in n_lon],
            "modes_m16_without_alpha_dot_longitudinal": modes(n_lon, a_lat),
            "modes_flow5": flow5_modes}
