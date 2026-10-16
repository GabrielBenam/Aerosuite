"""M19 Perdida benigna en envergadura (Gudmundsson Tabla 1-4 paso 19; Secs. 9.5.4 (metodo 2), 9.6 y 9.7).

Nivel conceptual (potencial lineal). La distribucion de C_l(eta) sale de la linea sustentadora de Prandtl con serie de Fourier
(Sec. 9.7.3, ecuacion del monoplano: sum A_n sin(n phi)(mu n + sin phi) = mu (alpha - alpha_ZL) sin phi, mu = c C_l_alpha/(4 b),
C_L = pi AR A_1, C_l = (4 b/c) sum A_n sin(n phi)), con alabeo (washout) lineal y perfiles de raiz y punta. Se aplica el metodo 2 de
la Sec. 9.5.4: se busca la incidencia a la que C_l(eta) toca por primera vez a C_lmax(eta) (con C_lmax interpolado entre raiz y punta,
Reynolds incluido por los datos de los perfiles). Criterios de la Sec. 9.6.3: la perdida debe empezar en la raiz y avanzar hacia la
punta; C_l a 70 % de la semienvergadura no debe exceder C_lmax y de 70 % a 100 % debe caer gradualmente (Torenbeek: C_lmax - 0.1).
Tambien el limite de cabeceo ascendente en alas con flecha (Ecs. 9-139 y 9-140). Limitaciones: linea sustentadora lineal sin flecha
ni fuselaje (la flecha, el flujo transversal y la separacion en la union ala-fuselaje no se capturan; Sec. 9.6.4); los resultados
de pos-perdida no se calculan. Contraste con flow5 (VLM2 real): ver pruebas y TEST_RESULTS. SI interno (rad internamente)."""
import math

import numpy as np

from . import project as prj

REFERENCES = [
    "GUD Sec. 9.7.3, Ecs. 9-166 a 9-172 (linea sustentadora de Prandtl, serie de Fourier, ecuacion del monoplano), PDF 19377-19430 del texto convertido",
    "GUD Sec. 9.5.4, metodo 2 (pasos 1 a 4: C_lmax(eta), interseccion con C_l(eta), Ec. 9-80) y Ejemplos 9-9 y 9-10 (C172: C_Lmax0 = 1.468 frente a 1.41 del POH)",
    "GUD Sec. 9.6.3 (1) (perdida de raiz a punta; C_l(70 %) <= C_lmax; C_l cae a cero de 70 % a 100 %; Torenbeek: C_lmax - 0.1; lavado 1-4 deg)",
    "GUD Sec. 9.6.5, Ecs. 9-139 y 9-140 (limite de AR y de la flecha c/4 para evitar el cabeceo ascendente; el signo de (2 - lambda) se reconstruye por inversion de ambas ecuaciones)",
    "Anderson, Fundamentals of Aerodynamics, Sec. 5.3 (solucion de la ecuacion del monoplano por colocacion; contraste: ala eliptica C_L_alpha = a0/(1 + a0/(pi AR)))",
]
CRITERIA_FRACTION = 0.7
TORENBEEK_MARGIN = 0.1


def alpha_zl_naca4_deg(code: str, n: int = 2001) -> float:
    """Incidencia de sustentacion nula de un NACA de 4 digitos por teoria de perfil delgado:
    alpha_L0 = -(1/pi) int_0^pi (dz/dx)(cos(theta) - 1) dtheta, con la linea de curvatura analitica."""
    m, p = int(code[0]) / 100.0, int(code[1]) / 10.0
    if m == 0.0 or p == 0.0:
        return 0.0
    th = np.linspace(0.0, math.pi, n)
    x = 0.5 * (1.0 - np.cos(th))
    dz = np.where(x < p, 2.0 * m / p ** 2 * (p - x), 2.0 * m / (1.0 - p) ** 2 * (p - x))
    y = dz * (np.cos(th) - 1.0)
    return -math.degrees(float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(th))) / math.pi)


def llt_solve(span, chords, cl_alpha, alpha_zl, twist, alpha, n_terms=40):
    """Linea sustentadora (ecuacion del monoplano) por colocacion en phi_i = i pi/(2N), armonicos impares n = 1, 3, ... (ala simetrica).
    `chords`, `cl_alpha` (1/rad), `alpha_zl` (rad), `twist` (rad, incidencia local relativa a la raiz; negativa = lavado) son funciones de eta = cos(phi)
    (0 = raiz, 1 = punta). Devuelve A_n, C_L, e_inducido y una funcion cl(eta)."""
    k = np.arange(1, n_terms + 1)
    phi = k * math.pi / (2 * n_terms)
    n = 2 * k - 1
    eta = np.cos(phi)
    c = np.array([chords(e) for e in eta])
    mu = c * np.array([cl_alpha(e) for e in eta]) / (4.0 * span)
    a_eff = alpha + np.array([twist(e) for e in eta]) - np.array([alpha_zl(e) for e in eta])
    mat = np.sin(np.outer(phi, n)) * (mu[:, None] * n[None, :] + np.sin(phi)[:, None])
    rhs = mu * a_eff * np.sin(phi)
    a = np.linalg.solve(mat, rhs)
    sref = _area(span, chords)
    ar = span ** 2 / sref
    cl_total = math.pi * ar * a[0]
    e_ind = a[0] ** 2 / float(np.sum(n * a ** 2)) if cl_total != 0 else 1.0

    def cl_of(e):
        ph = math.acos(min(1.0, max(0.0, e)))
        s = float(np.sum(a * np.sin(n * ph)))
        return 4.0 * span / chords(e) * s
    return {"A": a, "cl_total": cl_total, "e": e_ind, "cl_of": cl_of, "area_m2": sref, "aspect_ratio": ar}


def _area(span, chords, n=2001):
    eta = np.linspace(0.0, 1.0, n)
    c = np.array([chords(e) for e in eta])
    return 2.0 * (span / 2.0) * float(np.sum(0.5 * (c[1:] + c[:-1]) * np.diff(eta)))


def lift_curve_slope(span, chords, cl_alpha, alpha_zl, twist) -> float:
    """C_L_alpha (1/rad) de la linea sustentadora (diferencia entre dos incidencias; el alabeo no la modifica en el modelo lineal)."""
    d = 0.01
    a = llt_solve(span, chords, cl_alpha, alpha_zl, twist, 0.0)["cl_total"]
    b = llt_solve(span, chords, cl_alpha, alpha_zl, twist, d)["cl_total"]
    return (b - a) / d


def stall_progression(span, chords, cl_alpha, alpha_zl, twist, clmax, alpha_max_deg=30.0, step_deg=0.05, n_stations=21):
    """Metodo 2 de la Sec. 9.5.4: aumenta alpha hasta que C_l(eta) toca C_lmax(eta); registra para cada estacion la incidencia a la que
    la toca (progresion). Devuelve la primera perdida, la distribucion en ese instante y las incidencias por estacion."""
    stations = np.linspace(0.0, 1.0, n_stations)
    first = None
    onset = {float(s): None for s in stations}
    alpha = -2.0
    while alpha <= alpha_max_deg:
        sol = llt_solve(span, chords, cl_alpha, alpha_zl, twist, math.radians(alpha))
        cl = np.array([sol["cl_of"](s) for s in stations])
        cmx = np.array([clmax(s) for s in stations])
        for s, c, m in zip(stations, cl, cmx):
            if onset[float(s)] is None and c >= m:
                onset[float(s)] = alpha
        if first is None and np.any(cl >= cmx):
            idx = int(np.argmax(cl - cmx))
            first = {"alpha_deg": alpha, "eta": float(stations[idx]), "cl_total": sol["cl_total"], "cl": cl.tolist(), "clmax": cmx.tolist(),
                     "stations": stations.tolist()}
        alpha += step_deg
        if first is not None and all(v is not None for v in onset.values()):
            break
    return {"first": first, "onset_alpha_deg": {str(k): v for k, v in onset.items()}}


def refine_first_stall(span, chords, cl_alpha, alpha_zl, twist, clmax, a_lo_deg, a_hi_deg, n_stations=41, iters=40):
    """Biseccion sobre alpha para la primera interseccion C_l - C_lmax = 0 (maximo sobre estaciones)."""
    stations = np.linspace(0.0, 1.0, n_stations)
    cmx = np.array([clmax(s) for s in stations])

    def margin(a):
        sol = llt_solve(span, chords, cl_alpha, alpha_zl, twist, math.radians(a))
        return float(np.max(np.array([sol["cl_of"](s) for s in stations]) - cmx))
    lo, hi = a_lo_deg, a_hi_deg
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if margin(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    sol = llt_solve(span, chords, cl_alpha, alpha_zl, twist, math.radians(hi))
    cl = np.array([sol["cl_of"](s) for s in stations])
    return {"alpha_deg": hi, "eta": float(stations[int(np.argmax(cl - cmx))]), "cl_total": sol["cl_total"], "cl": cl.tolist(),
            "clmax": cmx.tolist(), "stations": stations.tolist()}


def benign_stall_checks(first: dict) -> dict:
    """Sec. 9.6.3: en la primera perdida (a) la estacion critica debe quedar en la raiz o claramente por dentro de 70 % de la semienvergadura,
    (b) C_l(70 %) <= C_lmax(70 %), (c) C_l decrece de 70 % a 100 % (y a C_lmax - 0.1 como margen de Torenbeek)."""
    st, cl, cm = np.array(first["stations"]), np.array(first["cl"]), np.array(first["clmax"])
    out = {"first_stall_eta": first["eta"], "first_stall_inboard_of_70pct": first["eta"] <= CRITERIA_FRACTION + 1e-9}
    i70 = int(np.argmin(np.abs(st - CRITERIA_FRACTION)))
    out["cl_at_70pct"] = float(cl[i70])
    out["clmax_at_70pct"] = float(cm[i70])
    out["cl_70_below_clmax"] = bool(cl[i70] <= cm[i70] + 1e-6)
    tail = cl[i70:]
    out["cl_decreases_70_to_100pct"] = bool(np.all(np.diff(tail) <= 1e-9))
    out["cl_tip"] = float(cl[-1])
    out["torenbeek_margin_ok"] = bool(np.all(cl[i70:] <= cm[i70:] - TORENBEEK_MARGIN + 1e-9))
    out["tip_unstalled_at_wing_stall"] = bool(cl[-1] < cm[-1])
    out["benign"] = bool(out["first_stall_inboard_of_70pct"] and out["cl_70_below_clmax"] and out["tip_unstalled_at_wing_stall"])
    return out


def pitch_up_limits(ar: float, taper: float, sweep_c4_deg: float) -> dict:
    """Ecs. 9-139 y 9-140: AR_lim = 17.714 (2 - lambda) exp(-0.04267 Lambda_c/4); Lambda_lim = 23.436 [ln(17.714 (2 - lambda)) - ln AR]."""
    ar_lim = 17.714 * (2.0 - taper) * math.exp(-0.04267 * sweep_c4_deg)
    lam_lim = 23.436 * (math.log(17.714 * (2.0 - taper)) - math.log(ar))
    return {"ar_limit": ar_lim, "sweep_limit_deg": lam_lim, "ar_ok": ar < ar_lim, "applies": sweep_c4_deg > 5.0,
            "note": "relevant for aft swept wings only (Sec. 9.6.5)"}


# --------------------------------------------------------------------------- modulo
def _distributions(pf, airfoils, washout_deg, alpha_zl_deg, cl_alpha_root, cl_alpha_tip):
    cr, ct = pf["root_chord_m"], pf["tip_chord_m"]
    chords = lambda e: cr + (ct - cr) * e
    cla = lambda e: cl_alpha_root + (cl_alpha_tip - cl_alpha_root) * e
    azl = lambda e: math.radians(alpha_zl_deg[0] + (alpha_zl_deg[1] - alpha_zl_deg[0]) * e)
    twist = lambda e: -math.radians(washout_deg) * e
    cm_r, cm_t = airfoils["root"]["clmax"], airfoils["tip"]["clmax"]
    clmax = lambda e: cm_r + (cm_t - cm_r) * e
    return chords, cla, azl, twist, clmax


def evaluate(project: dict) -> tuple[dict, list]:
    d = project["inputs"].get("m19", {})
    w = project["outputs"].get("m09b")
    if not w:
        raise SystemExit("outputs.m09b is missing: run m09b first")
    wing = w["result"]
    pf = wing["planform"]
    m9in = project["inputs"].get("m09b", {})
    airfoils = m9in["airfoils"] if "airfoils" in m9in else None
    if not airfoils:
        raise SystemExit("inputs.m09b.airfoils is missing (root/tip C_lmax and C_l_alpha)")
    washout = d.get("washout_deg", m9in.get("washout_deg", 0.0))
    res = {"level": "conceptual (linear lifting line; no fuselage, no sweep effects)", "units": "SI (angles in deg in reports)", "assumptions": []}
    azl = []
    for end in ("root", "tip"):
        if "alpha_zl_deg" in d:
            azl.append(d["alpha_zl_deg"][end])
        else:
            ident = airfoils[end].get("id", "")
            code = ident.lower().replace("naca", "")
            if len(code) == 4 and code.isdigit():
                azl.append(alpha_zl_naca4_deg(code))
                res["assumptions"].append(f"alpha_ZL({end}) of {ident} from thin-airfoil theory (camber line); give inputs.m19.alpha_zl_deg to override")
            else:
                raise SystemExit(f"inputs.m19.alpha_zl_deg is required for airfoil '{ident}'")
    cla_r, cla_t = (airfoils[e].get("cl_alpha_per_rad", 2 * math.pi) for e in ("root", "tip"))
    chords, cla, azl_f, twist, clmax = _distributions(pf, airfoils, washout, azl, cla_r, cla_t)
    span = pf["span_m"]
    res["inputs_used"] = {"washout_deg": washout, "alpha_zl_deg": azl, "cl_alpha_section_per_rad": [cla_r, cla_t],
                          "clmax_section": [airfoils["root"]["clmax"], airfoils["tip"]["clmax"]]}
    res["lift_curve"] = {"cl_alpha_wing_per_rad": lift_curve_slope(span, chords, cla, azl_f, twist),
                         "cl_alpha_m09b_per_rad": wing["lift_curve_slope"]["cl_alpha_recommended_per_rad"]}
    sweep = pf.get("sweep_c4_deg", 0.0)
    if abs(sweep) > 5.0:
        res["assumptions"].append(f"sweep c/4 = {sweep:.1f} deg is ignored by the lifting line; spanwise flow and tip upwash (Sec. 9.6.4) are not captured")

    def one(wo):
        ch, cl_a, az, tw, cm = _distributions(pf, airfoils, wo, azl, cla_r, cla_t)
        coarse = stall_progression(span, ch, cl_a, az, tw, cm, step_deg=0.5, n_stations=21)
        f = coarse["first"]
        if f is None:
            return {"washout_deg": wo, "stalled": False}
        fine = refine_first_stall(span, ch, cl_a, az, tw, cm, max(f["alpha_deg"] - 0.5, -5.0), f["alpha_deg"])
        onset = {k: v for k, v in coarse["onset_alpha_deg"].items()}
        return {"washout_deg": wo, "stalled": True, "alpha_stall_deg": fine["alpha_deg"], "cl_max_wing": fine["cl_total"],
                "first_stall": {k: fine[k] for k in ("alpha_deg", "eta", "cl_total")}, "distribution": {k: fine[k] for k in ("stations", "cl", "clmax")},
                "onset_alpha_deg_coarse": onset, "checks": benign_stall_checks(fine)}
    res["baseline"] = one(washout)
    res["washout_study"] = [one(wo) for wo in d.get("washout_study_deg", [0.0, 2.0, 4.0])]
    res["pitch_up"] = pitch_up_limits(pf["aspect_ratio"], pf["taper_ratio"], sweep)
    res["clmax0_m09b"] = wing.get("clmax", {}).get("clmax0") if isinstance(wing.get("clmax"), dict) else None
    res["pending"] = ("validation against flow5 VLM2/LLT spanwise distributions with the real engine: flow5 7.55 polar files give integrated "
                      "coefficients only; see tests for the C_L_alpha contrast")
    return res, ["m09b"]


def run(project: dict) -> dict:
    result, depends = evaluate(project)
    prj.record(project, "m19", result, "conceptual", REFERENCES, sorted(set(depends)))
    return result
