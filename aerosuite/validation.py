"""Independent checks of the engines against published references.

Each check reports the engine value, the reference value, the relative
difference and the reason for any expected discrepancy. Nothing here changes
an engine result; it only compares.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

from .adrpy_core import _aircraft, _libraries, evaluate, load_concept

ROOT = Path(__file__).resolve().parents[1]
GUDMUNDSSON_EXAMPLE = ROOT / "examples" / "gudmundsson-ex3-1-c162.json"

# ICAO standard atmosphere values (ICAO Doc 7488; also Diston Ch. 6, PDF p.256-262).
ISA_REFERENCE = [
    {"altitude_m": 0.0, "temperature_k": 288.15, "pressure_pa": 101325.0, "density_kgm3": 1.225, "speed_of_sound_mps": 340.294},
    {"altitude_m": 11000.0, "temperature_k": 216.65, "pressure_pa": 22632.1, "density_kgm3": 0.36392, "speed_of_sound_mps": 295.070},
]


def _rel(a: float, b: float) -> float:
    return (a - b) / b if b else float("nan")


def isa_check() -> dict:
    atmospheres, _ca, _np = _libraries()
    atm = atmospheres.Atmosphere()
    rows = []
    for ref in ISA_REFERENCE:
        h = ref["altitude_m"]
        got = {"temperature_k": float(atm.airtemp_k(h)), "pressure_pa": float(atm.airpress_pa(h)),
               "density_kgm3": float(atm.airdens_kgpm3(h)), "speed_of_sound_mps": float(atm.vsound_mps(h))}
        rows.append({"altitude_m": h, **{k: {"adrpy": v, "reference": ref[k], "rel_diff": _rel(v, ref[k])}
                                        for k, v in got.items()}})
    worst = max(abs(c["rel_diff"]) for r in rows for k, c in r.items() if k != "altitude_m")
    return {"check": "ADRpy ISA vs ICAO standard atmosphere", "rows": rows, "max_abs_rel_diff": worst,
            "pass_threshold": 1e-3, "passed": worst < 1e-3}


def adrpy_docstring_check() -> dict:
    """Reproduce the example printed in ADRpy 0.2.6 twrequired_to docstring."""
    atmospheres, ca, _np = _libraries()
    concept = ca.AircraftConcept({"rwyelevation_m": 1000, "groundrun_m": 1200},
                                 {"aspectratio": 7.3, "bpr": 3.9, "tr": 1.05},
                                 {"CDTO": 0.04, "CLTO": 0.9, "CLmaxTO": 1.6, "mu_R": 0.02},
                                 atmospheres.Atmosphere())
    got = [float(v) for v in concept.twrequired_to([2000, 3000, 4000, 5000])[0]]
    ref = [0.19397876, 0.26758006, 0.33994772, 0.41110154]
    worst = max(abs(_rel(a, b)) for a, b in zip(got, ref))
    return {"check": "ADRpy twrequired_to docstring example (installation/NumPy compatibility)",
            "adrpy": got, "reference": ref, "max_abs_rel_diff": worst, "passed": worst < 1e-6}


def gudmundsson_example_3_1(config: Path = GUDMUNDSSON_EXAMPLE) -> dict:
    """Compare ADRpy local T/W at W/S = 10 lbf/ft^2 with Gudmundsson Example 3-1.

    ADRpy is called with map2sl=False so both sides refer to the local flight
    condition, as in the book. Differences come from model choices, which are
    listed explicitly; they are not tuned away.
    """
    doc = load_concept(config)
    ref = doc["reference_values_gudmundsson"]
    point = evaluate(doc, ref["wingloading_pa"], map2sl=False)
    concept, _ = _aircraft(doc)
    rows = []
    for name, value in point["by_constraint"].items():
        book = ref["tw_local"].get(name)
        rows.append({"constraint": name, "adrpy_tw_local": value, "gudmundsson_tw": book,
                     "rel_diff": _rel(value, book) if book else None})
    # k that ADRpy uses in the cruise constraint at this W/S (same call as twrequired_crs)
    atm = concept.designatm
    from ADRpy import unitconversions as co
    v_cruise = co.kts2mps(doc["designbrief"]["cruisespeed_ktas"])
    h_cruise = doc["designbrief"]["cruisealt_m"]
    q_cruise = float(atm.dynamicpressure_pa(v_cruise, h_cruise))
    cl_cruise = ref["wingloading_pa"] / q_cruise
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        k_lesm = float(concept.induceddragfact_lesm(wingloading_pa=ref["wingloading_pa"], cl_real=cl_cruise,
                                                    mach_inf=float(atm.mach(v_cruise, h_cruise))))
        k_oswald = float(concept.induceddragfact())
    return {
        "check": "ADRpy 0.2.6 vs Gudmundsson Example 3-1 (C-162) at W/S = 10 lbf/ft^2 (478.8 Pa)",
        "reference": "Gudmundsson 2nd ed., Example 3-1, PDF p.109-111 (printed p.64-66)",
        "rows": rows,
        "adrpy_k_cruise_lesm": k_lesm,
        "adrpy_k_oswald_default": k_oswald,
        "cruise_cl_at_reference_point": cl_cruise,
        "gudmundsson_k": ref["k_induced"],
        "known_model_differences": [
            "Induced drag factor: Gudmundsson uses k=1/(pi AR e) with e=0.8106 (Eq. 9-129); ADRpy uses its own "
            "LESM-based estimate (induceddragfact_lesm), evaluated per condition.",
            "Take-off: ADRpy thrusttoweight_takeoff uses 1.21 W/S/(g rho CLmaxTO S_G) + 0.5 CDTO/CLTO + 0.5 mu_R; "
            "Gudmundsson Eq. (3-1) uses 1.21 W/S/(g rho CLmax S_G) + 0.605/CLmax (CDTO - mu CLTO) + mu.",
            "Climb/ceiling: ADRpy converts IAS to TAS internally with its ISA; Gudmundsson uses q at VY and sigma.",
            "Service ceiling altitude: 17,000 ft used to reproduce STEP 7 (the brief says 15,000 ft).",
        ],
        "interpretation": "Agreement within the spread caused by the different k and take-off formulations is "
                          "expected; larger deviations must be investigated before using the sizing results.",
    }


def run_all(out: Path | None = None) -> dict:
    report = {"isa": isa_check(), "adrpy_docstring": adrpy_docstring_check(),
              "gudmundsson_ex3_1": gudmundsson_example_3_1()}
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
