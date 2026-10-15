"""M01 Requisitos y base regulatoria (Gudmundsson Tabla 1-4 paso 1; Sec. 1.3, Tablas 1-2 y 1-3).

Nivel conceptual. Clasifica la aeronave en las categorías del 14 CFR Part 23 anterior a la enmienda 64
(Tabla 1-2) y en los niveles de certificación/desempeño del Part 23 nuevo (Tabla 1-3), y comprueba los
requisitos de entrada contra los límites que la obra reproduce. No sustituye al eCFR ni a CS-23.
"""
from . import project as prj

LBF_PER_KG = 2.2046226218
REFERENCES = ["GUD Sec. 1.3, Tabla 1-2 (impr. 13), PDF 58", "GUD Sec. 1.3, Tabla 1-3 (impr. 13), PDF 58",
              "GUD §23.2110 Stall speed (cita en Sec. 1.3, impr. 12), PDF 57"]

# Tabla 1-2: límites por categoría. Las celdas fusionadas de la tabla (peso 12 500 lbf, 9 ocupantes) se
# aplican a Normal, Utility y Aerobatic (ver DECISIONS D-17).
OLD_CATEGORIES = {
    "commuter": {"max_occupants": 19, "max_mtow_lbf": 19000, "aerobatics": "no"},
    "normal": {"max_occupants": 9, "max_mtow_lbf": 12500, "aerobatics": "limited", "n_plus_max": 3.8},
    "utility": {"max_occupants": 9, "max_mtow_lbf": 12500, "aerobatics": "limited", "n_plus_max": 4.4},
    "aerobatic": {"max_occupants": 9, "max_mtow_lbf": 12500, "aerobatics": "yes", "n_plus_max": 6.0},
}
# Tabla 1-2, fila n-: Normal 1.52, Utility 1.76, Aerobatic 3.0 (= 0.4 n+ máximo).
N_MINUS = {"normal": 1.52, "utility": 1.76, "aerobatic": 3.0}
# Tabla 1-3: nivel de certificación por asientos.
LEVEL_SEATS = ((1, 0, 1), (2, 2, 6), (3, 7, 9), (4, 10, 19))
VNO_HIGH_KCAS = 250.0
MMO_HIGH = 0.6
VSO_LIMIT_KCAS = 61.0  # §23.2110(c): monomotores y multimotores <= 6000 lbf


def maneuver_load_factors(category: str, mtow_kg: float) -> dict:
    """n+ y n- de maniobra de la Tabla 1-2 (basados en 14 CFR §23.337). W en lbf en la fórmula del libro."""
    cat = OLD_CATEGORIES[category]
    if "n_plus_max" not in cat:
        raise ValueError(f"la categoría {category!r} no tiene factores de carga legibles en la Tabla 1-2")
    w = mtow_kg * LBF_PER_KG
    if category == "normal":
        n_plus = min(cat["n_plus_max"], 2.1 + 24000.0 / (w + 10000.0))
    else:
        n_plus = cat["n_plus_max"]
    return {"n_plus": n_plus, "n_minus": N_MINUS[category], "weight_lbf": w}


def new_part23_class(seats: int, vno_kcas: float, mmo: float, aerobatic: bool) -> dict:
    level = next((lv for lv, lo, hi in LEVEL_SEATS if lo <= seats <= hi), None)
    if level is None:
        raise ValueError(f"{seats} asientos fuera de la Tabla 1-3 (0-19)")
    high = vno_kcas > VNO_HIGH_KCAS or mmo > MMO_HIGH
    return {"certification_level": level, "performance_level": "high" if high else "low",
            "aerobatic": bool(aerobatic)}


def evaluate(project: dict) -> dict:
    d = prj.need_inputs(project, "m01", ["category", "mtow_kg", "occupants", "vno_kcas", "mmo", "vso_kcas_max"])
    cat = d["category"]
    if cat not in OLD_CATEGORIES:
        raise SystemExit(f"category must be one of {sorted(OLD_CATEGORIES)}")
    limits = OLD_CATEGORIES[cat]
    mtow_lbf = d["mtow_kg"] * LBF_PER_KG
    checks = [
        {"name": "mtow", "ok": mtow_lbf <= limits["max_mtow_lbf"], "value_lbf": mtow_lbf,
         "limit_lbf": limits["max_mtow_lbf"]},
        {"name": "occupants", "ok": d["occupants"] <= limits["max_occupants"], "value": d["occupants"],
         "limit": limits["max_occupants"]},
    ]
    single_or_light = d.get("engines", 1) == 1 or mtow_lbf <= 6000.0
    if single_or_light:
        checks.append({"name": "vso_23.2110c", "ok": d["vso_kcas_max"] <= VSO_LIMIT_KCAS,
                       "value_kcas": d["vso_kcas_max"], "limit_kcas": VSO_LIMIT_KCAS})
    result = {"category": cat, "old_part23_limits": limits, "checks": checks,
              "new_part23": new_part23_class(d["occupants"], d["vno_kcas"], d["mmo"], d.get("aerobatic", cat == "aerobatic")),
              "compliant": all(c["ok"] for c in checks), "requirements": {k: v for k, v in d.items()}}
    try:
        result["maneuver_load_factors"] = maneuver_load_factors(cat, d["mtow_kg"])
    except ValueError as exc:
        result["maneuver_load_factors"] = {"error": str(exc)}
    return result


def run(project: dict) -> dict:
    result = evaluate(project)
    prj.record(project, "m01", result, "conceptual", REFERENCES)
    return result
