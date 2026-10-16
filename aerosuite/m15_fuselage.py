"""M15 Fuselaje (Gudmundsson Tabla 1-4 paso 15; Sec. 12.3 y 12.4).

Nivel conceptual. Dimensiona el fuselaje tras haber fijado ala y colas (Sec. 12.3.1): cabina minima por ocupante
(Sec. 12.3.3), nariz y cola de la forma "tubo de presion" (Sec. 12.2.2: nariz de 1.45 a 1.75 diametros y cola de 3 a 3.35
diametros), longitud de cola exigida por el brazo de M08, comprobacion contra el rango de CG de M13 y angulo de rotacion
(Sec. 12.3.2), y calcula areas mojadas y volumenes con los solidos elementales de la Sec. 12.4 (Ecs. 12-1 a 12-17).
Escribe un bloque `m10_fuselage` que M10 puede leer. Convenciones SI y ejes de M10 (origen en el borde de ataque de la raiz
del ala, x hacia atras). La disposicion interior (asientos, instrumentos, ergonomia) no se calcula: son datos y figuras.
"""
import math

from . import project as prj

REFERENCES = [
    "GUD Sec. 12.2.1-12.2.3 (frustum, tubo de presion, renacuajo; nariz 1.45-1.75 d, cola 3-3.35 d), PDF 564-566 / impr. 519-521",
    "GUD Sec. 12.3.1, pasos 1 a 6 (dimensionar el fuselaje con ala, colas, CG y componentes), PDF 566-569 / impr. 521-524",
    "GUD Sec. 12.3.2, refinamiento (finura 3-3.35, angulo de la cola para rotacion), PDF 570-571 / impr. 525-526",
    "GUD Sec. 12.3.3-12.3.4, dimensiones interiores (22 x 43 x 65 in por pasajero, pasillo 20 x 76 in, 20 in por persona), PDF 571-573 / impr. 526-528",
    "GUD Sec. 12.4.1-12.4.4, Ecs. 12-1 a 12-17 y Tabla 12-1 (areas y volumenes de solidos elementales), PDF 575-580 / impr. 530-535",
]
IN = 0.0254
PASSENGER_SPACE_M = (22 * IN, 43 * IN, 65 * IN)       # ancho x fondo x alto (GUD 12.3.3 (1))
AISLE_M = (20 * IN, 76 * IN)                           # ancho x alto de pasillo de pie (12.3.3 (2), 14 CFR 23.815)
MIN_WIDTH_PER_PERSON_M = 0.50                          # "al menos 20 in (50 cm) por persona" (12.3.4)
NOSE_RANGE_D = (1.45, 1.75)                            # 12.2.2
TAIL_RANGE_D = (3.0, 3.35)
DESIRED_CG_RANGE_PCT_MGC = (15.0, 35.0)                # 12.3.1, paso 2 (aviones convencionales)


# ------------------------------------------------------------ solidos elementales (Sec. 12.4.2)
def elliptic_cylinder(d1, d2, length):
    """Ecs. 12-2 y 12-3 (sin bases): S = (pi/2)(D1 + D2)(1 + 3h/(10 + sqrt(4 - 3h))) L, h = ((D1 - D2)/(D1 + D2))^2; V = pi/4 D1 D2 L."""
    h = ((d1 - d2) / (d1 + d2)) ** 2
    return {"h": h, "area": math.pi / 2.0 * (d1 + d2) * (1.0 + 3.0 * h / (10.0 + math.sqrt(4.0 - 3.0 * h))) * length,
            "volume": math.pi / 4.0 * d1 * d2 * length}


def uniform_cylinder(d, length):
    return {"area": math.pi * d * length, "volume": math.pi * d * d / 4.0 * length}          # Ecs. 12-4, 12-5


def paraboloid(d, length):
    """Ecs. 12-6 y 12-7 (sin base): S = pi D / (96 L^2) [(D^2 + 16 L^2)^(3/2) - D^3]; V = pi D^2 L / 8."""
    return {"area": math.pi * d / (96.0 * length ** 2) * ((d * d + 16.0 * length ** 2) ** 1.5 - d ** 3),
            "volume": math.pi * d * d * length / 8.0}


def cone(d, length):
    """Ecs. 12-8 y 12-9 (sin base): S = (pi D / 4) sqrt(D^2 + 4 L^2); V = pi D^2 L / 12."""
    return {"area": math.pi * d / 4.0 * math.sqrt(d * d + 4.0 * length ** 2), "volume": math.pi * d * d * length / 12.0}


def frustum(d1, d2, length, as_printed=False):
    """Ecs. 12-10 y 12-11 (sin bases). Area lateral = (pi/2)(D1 + D2) sqrt(((D1 - D2)/2)^2 + L^2) (generatriz exacta).
    `as_printed=True` usa (D1 - D2)^2 en lugar de ((D1 - D2)/2)^2: es lo que reproduce el valor 14.902 de la Tabla 12-1 y
    resulta ser una errata del libro (D-31). V = pi/12 (D1^2 + D1 D2 + D2^2) L."""
    slant = math.sqrt(((d1 - d2) if as_printed else (d1 - d2) / 2.0) ** 2 + length ** 2)
    return {"area": math.pi / 2.0 * (d1 + d2) * slant, "volume": math.pi / 12.0 * (d1 * d1 + d1 * d2 + d2 * d2) * length}


def silhouette_area(a_side, a_top):
    """Ec. 12-1 (reconstruida: la conversion pierde el factor pi): S = pi (A_side + A_top)/2; en el cilindro uniforme
    (A_side = A_top = D L) da pi D L, igual que la Ec. 12-4."""
    return math.pi * (a_side + a_top) / 2.0


def tubular_fuselage(d, l1, l2, l3):
    """Ecs. 12-12 a 12-14: nariz paraboloide L1, cilindro L2 y cola conica L3."""
    p, c, k = paraboloid(d, l1), uniform_cylinder(d, l2), cone(d, l3)
    return {"length": l1 + l2 + l3, "area": p["area"] + c["area"] + k["area"], "volume": p["volume"] + c["volume"] + k["volume"],
            "parts": {"nose_paraboloid": p, "cabin_cylinder": c, "tail_cone": k}}


def tadpole_fuselage(d, d1, d2, l1, l2, l3, l4):
    """Ecs. 12-15 a 12-17: paraboloide L1, cilindro L2 y dos troncos de cono (D -> d1 en L3, d1 -> d2 en L4)."""
    parts = {"nose_paraboloid": paraboloid(d, l1), "cabin_cylinder": uniform_cylinder(d, l2),
             "frustum_1": frustum(d, d1, l3), "frustum_2": frustum(d1, d2, l4)}
    return {"length": l1 + l2 + l3 + l4, "area": sum(p["area"] for p in parts.values()),
            "volume": sum(p["volume"] for p in parts.values()), "parts": parts}


def tail_strike_angle_deg(x_main_contact: float, x_tail_point: float, z_tail_point_above_ground: float) -> float:
    """Angulo de cabeceo maximo antes de que el punto mas bajo de la cola toque el suelo, con el tren comprimido (Sec. 12.3.2 (2),
    Figs. 12-11 y 12-12): la recta que une el contacto de la rueda principal con ese punto forma ese angulo con el suelo."""
    if x_tail_point <= x_main_contact or z_tail_point_above_ground <= 0.0:
        raise ValueError("the tail point must be behind the main contact and above the ground")
    return math.degrees(math.atan2(z_tail_point_above_ground, x_tail_point - x_main_contact))


def cabin_requirements(seats_abreast: int, aisle: bool, passengers: int) -> dict:
    """Minimos de la Sec. 12.3.3-12.3.4: 20 in (50 cm) por persona, pasillo de pie de 20 in, galley y lavabo."""
    width = seats_abreast * MIN_WIDTH_PER_PERSON_M + (AISLE_M[0] if aisle else 0.0)
    return {"min_width_m": width, "passenger_space_m": list(PASSENGER_SPACE_M),
            "aisle_m": list(AISLE_M) if aisle else None, "min_aisle_height_m": AISLE_M[1] if aisle else None,
            "lavatories_if_mission_over_1h": math.ceil(passengers / 50.0) if passengers > 0 else 0,
            "galleys_if_mission_over_1h": math.ceil(passengers / 100.0) if passengers >= 50 else 0,
            "rule": "one lavatory per 1-50 passengers and one galley per 50-100 for missions over 1 h (GUD 12.3.3 (4))"}


def _need(project: dict, mod: str, why: str):
    if mod not in project["outputs"]:
        raise SystemExit(f"inputs.m15 needs outputs.{mod} ({why}): run {mod} first")
    return project["outputs"][mod]["result"]


def evaluate(project: dict) -> tuple[dict, list]:
    d = prj.need_inputs(project, "m15", ["cabin"])
    depends: list = []
    cab = d["cabin"]
    shape = d.get("shape", "tubular")
    if shape not in ("tubular", "tadpole", "frustum_tail"):
        raise SystemExit("inputs.m15.shape must be 'tubular', 'tadpole' or 'frustum_tail'")
    seats, rows = int(cab["seats_abreast"]), int(cab.get("rows", 1))
    req = cabin_requirements(seats, bool(cab.get("aisle", False)), int(cab.get("passengers", seats * rows)))
    dia = float(cab["diameter_m"])
    pitch = float(cab["row_pitch_m"])
    cockpit = float(cab.get("cockpit_length_m", 0.0))
    baggage = float(cab.get("baggage_length_m", 0.0))
    l2 = float(cab["cabin_length_m"]) if "cabin_length_m" in cab else cockpit + max(rows - 1, 0) * pitch + baggage
    if "cabin_length_m" not in cab:
        prj.add_assumption(project, "m15", "cabin_length_m", l2,
                           "supuesto: cabina = cabina de mando + (filas - 1) x paso + equipaje; los pasos de asiento de la Fig. 12-20 no son legibles")
    wing = _need(project, "m09b", "wing planform")["planform"]
    tail = _need(project, "m08", "tail sizing")
    depends += ["m09b", "m08"]
    # --- nariz ---
    l1 = float(d["nose_length_m"]) if "nose_length_m" in d else None
    if l1 is None:
        factor = float(d.get("nose_factor", sum(NOSE_RANGE_D) / 2.0))
        l1 = factor * dia
        if "nose_factor" not in d:
            prj.add_assumption(project, "m15", "nose_factor", factor, "supuesto: centro del rango 1.45-1.75 d (GUD 12.2.2)")
    # --- posiciones respecto del dato del ala ---
    x_cabin_start = -float(d["wing_le_from_cabin_start_m"])
    x_nose = x_cabin_start - l1
    x_tail_start = x_cabin_start + l2
    # --- cola exigida por M08 (mismo calculo de M10: brazo l entre c_MGC/4 del ala y de la cola) ---
    ht, vt = tail["horizontal_tail"], tail["vertical_tail"]
    x_c4 = wing["mgc_quarter_chord_x_m"]

    def root_te(surf, sweep):
        return x_c4 + surf["arm_m"] - surf["cmgc_m"] / 4.0 - surf["ymgc_m"] * math.tan(math.radians(sweep)) + surf["root_chord_m"]
    x_tail_end_min = max(root_te(ht, float(d.get("ht_sweep_le_deg", 0.0))), root_te(vt, float(d.get("vt_sweep_le_deg", 0.0))))
    l3_required = x_tail_end_min - x_tail_start
    if l3_required <= 0.0:
        raise SystemExit("the tail surfaces end before the cabin: increase cabin_length_m or reduce wing_le_from_cabin_start_m")
    l3 = max(l3_required, float(d.get("tail_length_m", 0.0)))
    x_tail_end = x_tail_start + l3
    # --- geometria y solidos elementales ---
    if shape == "tubular":
        geo = tubular_fuselage(dia, l1, l2, l3)
        r2 = 0.0
    elif shape == "tadpole":
        d1, d2 = float(d["tadpole"]["d1_m"]), float(d["tadpole"]["d2_m"])
        l3a = float(d["tadpole"].get("l3_m", l3 / 2.0))
        geo = tadpole_fuselage(dia, d1, d2, l1, l2, l3a, l3 - l3a)
        r2 = d2 / 2.0
    else:                                  # frustum_tail: cola troncoconica como en M08/M10 (R2 de M08)
        r2 = float(d.get("tail_radius_m", tail["fuselage_tail_section"]["r2_m"]))
        parts = {"nose_paraboloid": paraboloid(dia, l1), "cabin_cylinder": uniform_cylinder(dia, l2),
                 "tail_frustum": frustum(dia, 2.0 * r2, l3)}
        geo = {"length": l1 + l2 + l3, "area": sum(p["area"] for p in parts.values()), "volume": sum(p["volume"] for p in parts.values()),
               "parts": parts}
    fineness_tail, fineness_nose = l3 / dia, l1 / dia
    checks = [
        {"name": "cabin_diameter_vs_minimum_width", "ok": dia >= req["min_width_m"], "diameter_m": dia, "min_width_m": req["min_width_m"],
         "source": "GUD 12.3.4: at least 20 in per person (+ aisle)"},
        {"name": "nose_length_range", "ok": NOSE_RANGE_D[0] <= fineness_nose <= NOSE_RANGE_D[1], "value_d": fineness_nose,
         "range_d": list(NOSE_RANGE_D), "source": "GUD 12.2.2"},
        {"name": "tail_length_range", "ok": TAIL_RANGE_D[0] <= fineness_tail <= TAIL_RANGE_D[1], "value_d": fineness_tail,
         "range_d": list(TAIL_RANGE_D), "source": "GUD 12.2.2 / 12.3.2 (ideal tail fineness 3 to 3.35)",
         "note": "the tail length is set by the M08 tail arm; outside the range the drag penalty is the book's warning, not a limit"},
        {"name": "wing_root_inside_cabin_length", "ok": 0.0 <= float(d["wing_le_from_cabin_start_m"]) <= l2 + 0.0,
         "wing_le_from_cabin_start_m": d["wing_le_from_cabin_start_m"], "cabin_length_m": l2}]
    # rotacion de despegue
    rot = d.get("rotation")
    result_rot = None
    if rot:
        angle = tail_strike_angle_deg(rot["x_main_contact_m"], rot["x_tail_point_m"], rot["tail_point_height_m"])
        stall = rot.get("alpha_stall_deg")
        if stall is None and "m09a" in project["outputs"]:
            ids = project["outputs"]["m09a"]["result"].get("metrics", {})
            sid = rot.get("airfoil_id")
            if sid and sid in ids:
                stall = ids[sid]["alpha_clmax_deg"]
                depends.append("m09a")
        inc = float(rot.get("incidence_deg", 0.0))
        required = None if stall is None else stall - inc          # cabeceo del fuselaje respecto del suelo cuando el ala alcanza alpha_stall
        result_rot = {"tail_strike_angle_deg": angle, "alpha_stall_deg": stall, "wing_incidence_deg": inc,
                      "fuselage_pitch_at_stall_deg": required, "ok": None if required is None else angle >= required,
                      "note": "GUD 12.3.2 (2): aim for an upsweep that allows rotation close to the clean stall AOA (compressed gear at "
                              "gross weight); the pitch at stall is taken as alpha_stall minus the wing incidence"}
        checks.append({"name": "tail_strike_clearance", "ok": result_rot["ok"] if result_rot["ok"] is not None else True,
                       "tail_strike_angle_deg": angle, "alpha_stall_deg": stall})
    # CG deseado
    cg_info = None
    if "m13" in project["outputs"]:
        r13 = project["outputs"]["m13"]["result"]
        depends.append("m13")
        if "loading_cloud_range_pct_mgc" in r13:
            lo, hi = r13["loading_cloud_range_pct_mgc"]
            dlo, dhi = d.get("desired_cg_range_pct_mgc", DESIRED_CG_RANGE_PCT_MGC)
            cg_info = {"loading_cloud_range_pct_mgc": [lo, hi], "desired_range_pct_mgc": [dlo, dhi],
                       "inside_desired": dlo <= lo and hi <= dhi,
                       "source": "GUD 12.3.1 step 2: conventional aircraft 15-35 % MGC (envelope still to be fixed by M16)"}
            checks.append({"name": "loading_cloud_inside_desired_cg_range", "ok": cg_info["inside_desired"], **cg_info})
    result = {"level": "conceptual", "units": "SI (m, m^2, m^3)", "shape": shape, "cabin": {**req, "diameter_m": dia, "length_m": l2,
              "row_pitch_m": pitch, "seats_abreast": seats, "rows": rows},
              "lengths_m": {"nose": l1, "cabin": l2, "tail": l3, "tail_required_by_m08": l3_required, "total": l1 + l2 + l3},
              "fineness": {"nose_over_d": fineness_nose, "tail_over_d": fineness_tail, "overall": (l1 + l2 + l3) / dia},
              "positions_m": {"x_nose": x_nose, "x_cabin_start": x_cabin_start, "x_tail_start": x_tail_start, "x_tail_end": x_tail_end,
                              "x_tail_end_min_from_m08": x_tail_end_min},
              "wetted_area_m2": geo["area"], "volume_m3": geo["volume"], "solids": geo["parts"],
              "rotation": result_rot, "cg": cg_info, "checks": checks, "within_guidance": all(c["ok"] for c in checks),
              "m10_fuselage": {"from_m08": False, "x_nose_m": x_nose, "nose_length_m": l1, "radius_m": dia / 2.0,
                               "tail_radius_m": r2, "x_tail_start_m": x_tail_start, "x_tail_end_m": x_tail_end,
                               "nose_shape": "paraboloid", "z_axis_m": float(d.get("z_axis_m", 0.0))},
              "note": "interior layout (seats, instruments, ergonomics; Figs. 12-13 to 12-22, Tables 12-2 to 12-5) is outside the computation"}
    return result, depends


def run(project: dict) -> dict:
    result, depends = evaluate(project)
    prj.record(project, "m15", result, "conceptual", REFERENCES, sorted(set(depends)))
    return result
