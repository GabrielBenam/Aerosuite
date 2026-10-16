"""M10 Geometria parametrica (OML) (Gudmundsson Tabla 1-4 paso 10; Caps. 4 y 9.1.3, Sec. 11.2; Sobester & Forrester Caps. 2-4).

Nivel conceptual. Ensambla ala (M09b), cola (M08) y fuselaje en una sola geometria exterior (OML) dentro de
`project.json`, en SI y con ejes definidos. Principios tomados de Sobester & Forrester Sec. 2.3: la geometria es
parametrica y concisa (pocas variables: forma separada de la escala, Sec. 2.1.1), robusta (comprobaciones previas a
cualquier analisis, Sec. 2.2.1/2.3.2) y las superficies son sustentadoras por solevado lineal entre secciones
(Ec. 4.1, L(u,t) = (1-u) B1(t) + u B2(t)); la seccion del fuselaje es el "circulo generalizado" Y(Z) = Z^N1 (1-Z)^N2
(Ec. 2.16; N1 = N2 = 0.5 es un circulo). Convenciones: el origen es el borde de ataque de la raiz del ala en el plano
de simetria (Gudmundsson Sec. 9.1.3); x positivo hacia atras, y a estribor, z hacia arriba; angulos de incidencia,
diedro y torsion positivos con el borde de ataque o la punta hacia arriba. La torsion se mide respecto al borde de
ataque de la seccion (convencion declarada de AeroSuite; verificar con flow5 antes de intercambiar).
"""
import math

from . import project as prj
from .airfoils import naca4

SCHEMA = "aerosuite-oml/1"
REFERENCES = [
    "GUD Sec. 9.1.3 y Tabla 9-1 (dato del ala en el plano de simetria), PDF 367 / impr. 322",
    "GUD Sec. 11.2.1-11.2.2, Figs. 11-1 y 11-2 (brazos l_HT y l_VT medidos entre c_MGC/4 del ala y de la cola), PDF 529-530 / impr. 484-485",
    "GUD Sec. 9.2.2, Ecs. 9-12 a 9-14 (c_MGC, y_MGC, x_MGC), PDF 369-370 / impr. 324-325",
    "SOB Sec. 2.1.1 (forma y escala), 2.2.1 y 2.3 (comprobaciones previas, concision, robustez, flexibilidad), PDF 30-35",
    "SOB Sec. 2.4.1, Ec. 2.16 (seccion transversal generalizada del fuselaje) y Sec. 2.4.3 (fuselaje 3D por solevado de secciones), PDF 36-46",
    "SOB Sec. 4.1, Ec. 4.1 (superficie solevada entre dos curvas), PDF 85-86",
]
AXES = {"origin": "leading edge of the wing root chord at the plane of symmetry",
        "x": "aft", "y": "starboard", "z": "up", "angles": "incidence, dihedral, twist positive nose/tip up",
        "twist_pivot": "section leading edge (AeroSuite convention, to verify against flow5)"}


def cross_section(n1: float = 0.5, n2: float = 0.5, n: int = 41) -> list[tuple[float, float]]:
    """Semiseccion normalizada (Z, Y) de SOB Ec. 2.16: Y(Z) = Z^N1 (1 - Z)^N2, Z en [0, 1] (alto total 1)."""
    if not (0.0 < n1 <= 2.0 and 0.0 < n2 <= 2.0) or n < 5:
        raise ValueError("require 0 < N1, N2 <= 2 and n >= 5")
    return [(z, z ** n1 * (1.0 - z) ** n2) for z in (i / (n - 1) for i in range(n))]


def fuselage(d: dict, x_tail_start: float, tail_end_x: float) -> dict:
    """Fuselaje por estaciones: casquete de nariz elipsoidal, tramo cilindrico y cono de cola (tronco de cono como el
    de M08, Ecs. 11-14/11-16). d: x_nose_m (negativo si la nariz esta delante del dato), nose_length_m, radius_m (R1),
    tail_radius_m (R2), z_axis_m, n1, n2, stations_nose / stations_tail (resolucion)."""
    x_nose, l_nose = float(d["x_nose_m"]), float(d["nose_length_m"])
    r1, r2 = float(d["radius_m"]), float(d["tail_radius_m"])
    z0 = float(d.get("z_axis_m", 0.0))
    if not (0.0 < r2 <= r1) or l_nose <= 0.0:
        raise ValueError("require 0 < tail radius <= cabin radius and nose length > 0")
    x_cabin = x_nose + l_nose
    if not x_cabin < x_tail_start < tail_end_x:
        raise ValueError("require nose < cabin start < tail-cone start < tail end along x")
    stations = []
    nn = int(d.get("stations_nose", 6))
    for i in range(nn):                                    # elipsoide: r = R sqrt(1 - ((x_cabin - x)/L)^2)
        x = x_nose + l_nose * (i / nn) ** 1.0
        r = r1 * math.sqrt(max(0.0, 1.0 - ((x_cabin - x) / l_nose) ** 2))
        stations.append({"x_m": x, "radius_m": r})
    stations += [{"x_m": x_cabin, "radius_m": r1}, {"x_m": x_tail_start, "radius_m": r1}]
    nt = int(d.get("stations_tail", 3))
    for i in range(1, nt + 1):
        x = x_tail_start + (tail_end_x - x_tail_start) * i / nt
        stations.append({"x_m": x, "radius_m": r1 + (r2 - r1) * i / nt})
    n1, n2 = float(d.get("n1", 0.5)), float(d.get("n2", 0.5))
    wetted = sum(math.pi * (a["radius_m"] + b["radius_m"]) * math.hypot(b["x_m"] - a["x_m"], b["radius_m"] - a["radius_m"])
                 for a, b in zip(stations, stations[1:]))
    return {"type": "fuselage", "axis_z_m": z0, "section": {"n1": n1, "n2": n2, "form": "Y(Z)=Z^N1(1-Z)^N2 (SOB Eq. 2.16)"},
            "stations": stations, "length_m": tail_end_x - x_nose, "max_radius_m": r1,
            "wetted_area_estimate_m2": wetted,
            "note": "wetted area of the station polyline treated as circular (n1 = n2 = 0.5); a different n1/n2 changes it"}


def lifting_surface(name: str, kind: str, root_le: tuple[float, float, float], span_m: float, root_chord_m: float,
                    tip_chord_m: float, sweep_le_deg: float, dihedral_deg: float, twist_tip_deg: float,
                    incidence_deg: float, foil_root: str, foil_tip: str, n_stations: int = 2, vertical: bool = False) -> dict:
    """Superficie solevada linealmente entre raiz y punta (SOB Ec. 4.1). Para la cola vertical `span_m` es la altura y la
    superficie se extiende hacia +z (un solo lado). Las secciones intermedias interpolan cuerda, torsion y flecha
    linealmente (ala trapezoidal)."""
    if n_stations < 2:
        raise ValueError("n_stations >= 2")
    half = span_m if vertical else span_m / 2.0
    t_le, t_dih = math.tan(math.radians(sweep_le_deg)), math.tan(math.radians(dihedral_deg))
    secs = []
    for i in range(n_stations):
        u = i / (n_stations - 1)
        s = half * u                                       # distancia a lo largo de la envergadura (o de la altura)
        c = (1.0 - u) * root_chord_m + u * tip_chord_m
        x = root_le[0] + s * t_le
        if vertical:
            y, z = root_le[1], root_le[2] + s
        else:
            y, z = root_le[1] + s, root_le[2] + s * t_dih
        secs.append({"station": u, "x_le_m": x, "y_m": y, "z_le_m": z, "chord_m": c, "twist_deg": incidence_deg + u * twist_tip_deg,
                     "airfoil": foil_root if u == 0.0 else (foil_tip if u == 1.0 else f"{foil_root}->{foil_tip} blend {u:.3f}")})
    area = (root_chord_m + tip_chord_m) / 2.0 * half * (1.0 if vertical else 2.0)
    return {"type": kind, "name": name, "symmetric": not vertical, "semi_span_m": half, "root_le_m": list(root_le),
            "sweep_le_deg": sweep_le_deg, "dihedral_deg": dihedral_deg, "incidence_root_deg": incidence_deg,
            "twist_tip_deg": twist_tip_deg, "sections": secs, "planform_area_m2": area,
            "loft": "linear between sections (SOB Eq. 4.1)"}


def section_contour(coords, chord_m: float, x_le: float, y: float, z_le: float, twist_deg: float) -> list[list[float]]:
    """Contorno 3D de un perfil (Selig, c = 1) a la cuerda dada, girado `twist_deg` respecto del borde de ataque
    (positivo = borde de ataque arriba) y colocado en (x_le, y, z_le)."""
    a = math.radians(twist_deg)
    out = []
    for px, pz in coords:
        xx, zz = px * chord_m, pz * chord_m
        out.append([x_le + xx * math.cos(a) + zz * math.sin(a), y, z_le - xx * math.sin(a) + zz * math.cos(a)])
    return out


def foil_coords(ident: str):
    code = ident.lower().removeprefix("naca")
    if len(code) == 4 and code.isdigit():
        return naca4(code, 41)
    raise ValueError(f"airfoil {ident!r}: only NACA 4-digit contours are generated; supply .dat contours to M24")


def _contour(c: dict, s: dict) -> list[list[float]]:
    """Contorno 3D de una seccion: horizontal (ala, HT) con torsion, o vertical (VT: espesor en y, plano z = const)."""
    coords = foil_coords(s["airfoil"].split("->")[0])
    if c["type"] == "vertical_tail":
        return [[s["x_le_m"] + px * s["chord_m"], pz * s["chord_m"], s["z_le_m"]] for px, pz in coords]
    return section_contour(coords, s["chord_m"], s["x_le_m"], s["y_m"], s["z_le_m"], s["twist_deg"])


def _need(project: dict, mod: str):
    if mod not in project["outputs"]:
        raise SystemExit(f"inputs.m10 needs outputs.{mod}: run {mod} first")
    return project["outputs"][mod]["result"]


def evaluate(project: dict) -> tuple[dict, list]:
    d = prj.need_inputs(project, "m10", ["fuselage"])
    wing, tail = _need(project, "m09b"), _need(project, "m08")
    depends = ["m09b", "m08"]
    pf = wing["planform"]
    foils = wing.get("airfoils", {})
    wid = lambda end: d.get("wing_airfoils", {}).get(end) or (foils.get(end) or {}).get("id")
    if not (wid("root") and wid("tip")):
        raise SystemExit("inputs.m10.wing_airfoils {root, tip} (or airfoils in m09b) are required")
    fr, ft = wid("root"), wid("tip")
    ht_foil, vt_foil = d.get("ht_airfoil", "naca0009"), d.get("vt_airfoil", "naca0009")
    if "ht_airfoil" not in d or "vt_airfoil" not in d:
        prj.add_assumption(project, "m10", "tail_airfoils", {"ht": ht_foil, "vt": vt_foil},
                           "supuesto: perfil simetrico NACA 0009 para las colas (M09a no seleccionó perfiles de cola)")
    z_w = float(d.get("wing_z_m", 0.0))
    inc_w = float(d.get("wing_incidence_deg", 0.0))
    if "wing_incidence_deg" not in d:
        prj.add_assumption(project, "m10", "wing_incidence_deg", 0.0,
                           "supuesto: incidencia del ala 0 deg; el libro la calcula en el paso de ajuste (Ec. 9-55), no implementado")
    wing_s = lifting_surface("wing", "wing", (0.0, 0.0, z_w), pf["span_m"], pf["root_chord_m"], pf["tip_chord_m"],
                             pf["sweep_le_deg"], wing.get("dihedral_deg", 0.0), -abs(wing.get("washout_deg", 0.0)), inc_w,
                             fr, ft, int(d.get("wing_stations", 2)))
    x_c4_wing = pf["mgc_quarter_chord_x_m"]                # c_MGC/4 del ala respecto del dato
    ht, vt = tail["horizontal_tail"], tail["vertical_tail"]
    sw_ht, sw_vt = float(d.get("ht_sweep_le_deg", 0.0)), float(d.get("vt_sweep_le_deg", 0.0))
    # raiz de la cola: l = x(c/4 MGC cola) - x(c/4 MGC ala) (Fig. 11-1)
    def root_le_x(surf, sweep):
        ymgc = surf["ymgc_m"]
        return x_c4_wing + surf["arm_m"] - surf["cmgc_m"] / 4.0 - ymgc * math.tan(math.radians(sweep))
    ht_z, vt_z = float(d.get("ht_z_m", 0.0)), float(d.get("vt_base_z_m", 0.0))
    ht_inc = float(d.get("ht_incidence_deg", 0.0))
    ht_s = lifting_surface("horizontal_tail", "horizontal_tail", (root_le_x(ht, sw_ht), 0.0, ht_z), ht["span_m"],
                           ht["root_chord_m"], ht["tip_chord_m"], sw_ht, 0.0, 0.0, ht_inc, ht_foil, ht_foil)
    vt_s = lifting_surface("vertical_tail", "vertical_tail", (root_le_x(vt, sw_vt), 0.0, vt_z), vt["span_m"],
                           vt["root_chord_m"], vt["tip_chord_m"], sw_vt, 0.0, 0.0, 0.0, vt_foil, vt_foil, vertical=True)
    # --- fuselaje ---
    fz = dict(d["fuselage"])
    if fz.pop("from_m08", False):
        fz.setdefault("radius_m", tail["fuselage_tail_section"]["r1_m"])
        fz.setdefault("tail_radius_m", tail["fuselage_tail_section"]["r2_m"])
    tail_end = float(fz["x_tail_end_m"]) if "x_tail_end_m" in fz else max(
        ht_s["root_le_m"][0] + ht["root_chord_m"], vt_s["root_le_m"][0] + vt["root_chord_m"])
    x_start = float(fz.get("x_tail_start_m", x_c4_wing))
    fus = fuselage(fz, x_start, tail_end)
    comps = [fus, wing_s, ht_s, vt_s]
    # --- comprobaciones previas (SOB Sec. 2.2.1: la geometria se valida antes de cualquier analisis) ---
    checks = []

    def check(name, ok, **info):
        checks.append({"name": name, "ok": bool(ok), **info})
    check("wing_root_inside_fuselage_height", abs(z_w - fus["axis_z_m"]) <= fus["max_radius_m"], wing_z_m=z_w,
          fuselage_radius_m=fus["max_radius_m"])
    check("wing_root_x_within_fuselage", fus["stations"][0]["x_m"] < 0.0 < tail_end, x_nose_m=fus["stations"][0]["x_m"])
    check("tail_roots_within_fuselage_length",
          ht_s["root_le_m"][0] + ht["root_chord_m"] <= tail_end + 1e-9 and vt_s["root_le_m"][0] + vt["root_chord_m"] <= tail_end + 1e-9,
          tail_end_x_m=tail_end)
    check("arms_positive", ht["arm_m"] > 0 and vt["arm_m"] > 0, l_ht_m=ht["arm_m"], l_vt_m=vt["arm_m"])
    check("ht_clear_of_wing", ht_s["root_le_m"][0] > wing_s["sections"][0]["x_le_m"] + pf["root_chord_m"],
          ht_root_le_x_m=ht_s["root_le_m"][0], wing_root_te_x_m=pf["root_chord_m"])
    check("positive_chords", all(s["chord_m"] > 0 for c in comps[1:] for s in c["sections"]))
    # --- cantidades derivadas e invariantes de reconstruccion ---
    ref = {"s_ref_m2": pf["area_m2"], "b_ref_m": pf["span_m"], "c_ref_m": pf["cmgc_m"],
           "wing_c4_mgc_x_m": x_c4_wing, "l_ht_check_m": ht_s["root_le_m"][0] + ht["ymgc_m"] * math.tan(math.radians(sw_ht))
           + ht["cmgc_m"] / 4.0 - x_c4_wing,
           "l_vt_check_m": vt_s["root_le_m"][0] + vt["ymgc_m"] * math.tan(math.radians(sw_vt)) + vt["cmgc_m"] / 4.0 - x_c4_wing,
           "volume_coefficients_check": {"vht": ht_s["planform_area_m2"] * ht["arm_m"] / (pf["area_m2"] * pf["cmgc_m"]),
                                         "vvt": vt_s["planform_area_m2"] * vt["arm_m"] / (pf["area_m2"] * pf["span_m"])},
           "overall_length_m": fus["length_m"], "overall_span_m": pf["span_m"],
           "overall_height_m": max(vt_s["sections"][-1]["z_le_m"], fus["axis_z_m"] + fus["max_radius_m"]) - (fus["axis_z_m"] - fus["max_radius_m"])}
    result = {"schema": SCHEMA, "level": "conceptual", "units": "SI", "axes": AXES, "components": comps, "reference": ref,
              "checks": checks, "valid": all(c["ok"] for c in checks),
              "sources": {"wing": "M09b planform", "tail": "M08 tail sizing"}}
    if d.get("contours"):
        result["contours"] = {c["name"]: [{"station": s["station"], "airfoil": s["airfoil"].split("->")[0],
                                           "points_m": _contour(c, s)} for s in c["sections"]] for c in (wing_s, ht_s, vt_s)}
    return result, depends


def run(project: dict) -> dict:
    result, depends = evaluate(project)
    prj.record(project, "m10", result, "conceptual", REFERENCES, depends)
    return result
