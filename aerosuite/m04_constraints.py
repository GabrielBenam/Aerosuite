"""M04 Restricciones (Gudmundsson Tabla 1-4 pasos 4, 5 y 7; Sec. 3.2, Ecs. 3-1, 3-13, 3-14 y Apéndice D).

Nivel conceptual. Reúne tres cosas:
  1. el análisis de restricciones de ADRpy (`adrpy_core.size`, sin modificar), con el límite de pérdida;
  2. la restricción de aterrizaje de Gudmundsson (distancia total Ec. 3-13, solo rodadura Ec. 3-14), que
     ADRpy no trae: es un límite vertical de W/S (la tracción en tierra es mínima y no interviene);
  3. la Ec. 3-1 de despegue del libro, como contraste de la formulación de ADRpy.
Las ecuaciones del libro tienen constantes dimensionales (pies, slug/ft³, lbf/ft²): se evalúan en esas unidades
y las funciones públicas reciben y devuelven SI.
"""
import math

from scipy.optimize import brentq

from . import adrpy_core
from . import project as prj

REFERENCES = [
    "GUD Sec. 3.2.1, Ec. 3-1 (despegue), PDF 104 / impr. 59",
    "GUD Sec. 3.2.1 ítem (9), Ecs. 3-13 y 3-14 (aterrizaje), PDF 106 / impr. 61; deducción en Apéndice D, PDF 1121-1122",
    "GUD Ejemplo 3-1 (Cessna 162), PDF 109-111 / impr. 64-66: pasos 3 y 8",
    "ADRpy 0.2.6 constraintanalysis (twrequired_to/clm/crs/sec/trn, wsmaxcleanstall_pa); contraste en TEST_RESULTS §2.3",
]
FT_PER_M = 3.280839895
G_FTS2 = 32.174
PA_PER_LBF_FT2 = 47.88025898
KGM3_PER_SLUGFT3 = 515.378819


def landing_distance_ft(ws_lbf_ft2: float, rho_slug_ft3: float, clmax: float, cl_ldg: float, cd_ldg: float,
                        mu: float, free_roll_s: float, h_obst_ft: float, tgr_w: float = 0.0,
                        ground_roll_only: bool = False) -> float:
    """Ec. 3-13 (total, sobre obstáculo con trayectoria de 3 grados) o Ec. 3-14 (solo rodadura), en pies.

    S_BR   = 1.21 (W/S) / (g rho CLmax) / [0.605/CLmax (CD_LDG - mu CL_LDG) + mu + Tgr/W]   (frenado desde 1.1 V_S0)
    S_FR   = 1.556 tau sqrt((W/S)/(rho CLmax))                                               (rodadura libre)
    S_LDG  = 19.08 h_obst + 0.007923 (W/S)/(rho CLmax) + S_FR + S_BR                          (Ec. 3-13)
    S_LGR  = 0.01583 (W/S)/(rho CLmax) + S_FR + S_BR                                          (Ec. 3-14)
    """
    a = rho_slug_ft3 * clmax
    denom = 0.605 / clmax * (cd_ldg - mu * cl_ldg) + mu + tgr_w
    if denom <= 0.0:
        raise ValueError("braking deceleration is not positive: check CD_LDG, mu, CL_LDG and Tgr/W")
    s_br = 1.21 * ws_lbf_ft2 / (G_FTS2 * a * denom)
    s_fr = 1.556 * free_roll_s * math.sqrt(ws_lbf_ft2 / a)
    if ground_roll_only:
        return 0.01583 * ws_lbf_ft2 / a + s_fr + s_br
    return 19.08 * h_obst_ft + 0.007923 * ws_lbf_ft2 / a + s_fr + s_br


def landing_distance_m(ws_pa: float, rho_kgm3: float, clmax: float, cl_ldg: float, cd_ldg: float, mu: float,
                       free_roll_s: float, h_obst_m: float, tgr_w: float = 0.0, ground_roll_only: bool = False) -> float:
    return landing_distance_ft(ws_pa / PA_PER_LBF_FT2, rho_kgm3 / KGM3_PER_SLUGFT3, clmax, cl_ldg, cd_ldg, mu,
                               free_roll_s, h_obst_m * FT_PER_M, tgr_w, ground_roll_only) / FT_PER_M


def max_wing_loading_for_landing_pa(distance_m: float, rho_kgm3: float, clmax: float, cl_ldg: float, cd_ldg: float,
                                    mu: float, free_roll_s: float, h_obst_m: float, tgr_w: float = 0.0,
                                    ground_roll_only: bool = False) -> float:
    """W/S máximo (Pa) con el que la distancia de aterrizaje no excede `distance_m` (la ecuación es trascendente: se
    resuelve por bisección; la distancia crece con W/S)."""
    def excess(ws):
        return landing_distance_m(ws, rho_kgm3, clmax, cl_ldg, cd_ldg, mu, free_roll_s, h_obst_m, tgr_w,
                                  ground_roll_only) - distance_m
    lo, hi = 10.0, 20000.0
    if excess(lo) > 0.0:
        raise ValueError("landing distance cannot be met even at a very low wing loading")
    if excess(hi) < 0.0:
        raise ValueError("landing distance is not binding below 20 kPa")
    return brentq(excess, lo, hi, xtol=1e-9, rtol=1e-12)


def takeoff_tw_book(ws_lbf_ft2: float, rho_slug_ft3: float, clmax_to: float, cl_to: float, cd_to: float, mu: float,
                    ground_run_ft: float) -> float:
    """Ec. 3-1: T/W de despegue para una carrera dada (q evaluada a V_LOF/sqrt(2))."""
    return (1.21 * ws_lbf_ft2 / (G_FTS2 * rho_slug_ft3 * clmax_to * ground_run_ft)
            + 0.605 / clmax_to * (cd_to - mu * cl_to) + mu)


def _landing_block(doc_landing: dict, rho_kgm3: float) -> dict:
    need = ("distance_m", "clmax_land", "cl_ldg", "cd_ldg", "mu_brake")
    miss = [k for k in need if k not in doc_landing]
    if miss:
        raise SystemExit(f"inputs.m04.landing is missing: {', '.join(miss)}")
    kind = doc_landing.get("kind", "total")
    if kind not in ("total", "ground_roll"):
        raise SystemExit("landing.kind must be 'total' or 'ground_roll'")
    args = dict(rho_kgm3=rho_kgm3, clmax=doc_landing["clmax_land"], cl_ldg=doc_landing["cl_ldg"],
                cd_ldg=doc_landing["cd_ldg"], mu=doc_landing["mu_brake"],
                free_roll_s=doc_landing.get("free_roll_s", 1.0),
                h_obst_m=doc_landing.get("obstacle_m", 15.24), tgr_w=doc_landing.get("thrust_ratio_gr", 0.0),
                ground_roll_only=kind == "ground_roll")
    ws_max = max_wing_loading_for_landing_pa(doc_landing["distance_m"], **args)
    return {"kind": kind, "distance_m": doc_landing["distance_m"], "density_kgm3": rho_kgm3,
            "max_wingloading_pa": ws_max, "max_wingloading_lbf_ft2": ws_max / PA_PER_LBF_FT2,
            "check_distance_m": landing_distance_m(ws_max, **args), "inputs": doc_landing}


def run(project: dict) -> dict:
    d = prj.need_inputs(project, "m04", ["concept"])
    doc = d["concept"]
    result = adrpy_core.size(doc, map2sl=not d.get("local_tw", False))
    atmospheres, _ca, _np = adrpy_core._libraries()
    offset = float(doc.get("atmosphere", {}).get("offset_deg", 0.0))
    atm = atmospheres.Atmosphere(offset_deg=offset)
    limits = {"stall": result["stall_limit_wingloading_pa"]}
    if "landing" in d:
        alt = d["landing"].get("altitude_m", doc["designbrief"].get("rwyelevation_m", 0.0))
        result["landing"] = _landing_block(d["landing"], float(atm.airdens_kgpm3(alt)))
        limits["landing"] = result["landing"]["max_wingloading_pa"]
    active = {k: v for k, v in limits.items() if v is not None}
    ws_limit = min(active.values()) if active else None
    admissible = [s for s in result["samples"] if ws_limit is None or s["wingloading_pa"] <= ws_limit]
    result["wingloading_limits_pa"] = limits
    result["wingloading_limit_active"] = min(active, key=active.get) if active else None
    result["design_point_rule"] = ("minimum required T/W among sampled W/S not exceeding " +
                                   " and ".join(active) + " limit(s)") if active else result["design_point_rule"]
    result["best_sample"] = min(admissible, key=lambda s: s["required_tw"]) if admissible else None
    if not admissible:
        result["warning"] = "no sampled wing loading satisfies the W/S limits"
    brief, perf = doc["designbrief"], doc["designperformance"]
    if all(k in perf for k in ("CLmaxTO", "CLTO", "CDTO", "mu_R")) and brief.get("groundrun_m"):
        rho = float(atm.airdens_kgpm3(brief.get("rwyelevation_m", 0.0))) / KGM3_PER_SLUGFT3
        result["takeoff_book_eq_3_1"] = [
            {"wingloading_pa": s["wingloading_pa"],
             "tw_local": takeoff_tw_book(s["wingloading_pa"] / PA_PER_LBF_FT2, rho, perf["CLmaxTO"], perf["CLTO"],
                                         perf["CDTO"], perf["mu_R"], brief["groundrun_m"] * FT_PER_M),
             "adrpy_tw_sea_level": s["by_constraint"].get("takeoff")} for s in result["samples"]]
    prj.record(project, "m04", result, "conceptual", REFERENCES)
    return result
