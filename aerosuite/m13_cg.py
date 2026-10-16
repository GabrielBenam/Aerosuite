"""M13 CG, inercias y envolvente de CG (Gudmundsson Tabla 1-4 pasos 13 y 14; Secs. 6.6 y 6.7).

Nivel conceptual. El avion se representa como una coleccion de masas puntuales (Sec. 6.6.1): centro de gravedad
(Ecs. 6-128 a 6-137), momentos y productos de inercia con el teorema de los ejes paralelos (Ecs. 6-144 a 6-149),
matriz de inercia y momentos principales (Ecs. 6-150, 6-151), tolerancias de peso y posicion (Ecs. 6-153 a 6-157),
posicion del CG por pesaje (Ecs. 6-138, 6-139), nube de cargas y envolvente de CG (Sec. 6.7). SI interno (kg, m,
kg m^2); el CG en % de c_MGC usa la Ec. 6-137. Los limites delantero y trasero de la envolvente dependen de analisis de
estabilidad y control (Caps. 24 y 25, M16): M13 los toma como dato y no los inventa; sin ellos solo informa la nube.
"""
import math

import numpy as np

from . import project as prj

REFERENCES = [
    "GUD Sec. 6.6.3-6.6.5, Ecs. 6-128 a 6-137 y Ejemplos 6-8 y 6-9 (CG de masas puntuales, % c_MGC), PDF 222-225 / impr. 177-180",
    "GUD Sec. 6.6.6, Ecs. 6-138 y 6-139 (CG por pesaje), PDF 225 / impr. 180",
    "GUD Sec. 6.6.7-6.6.10, Ecs. 6-140 a 6-151 (inercias, ejes paralelos, ejes principales, matriz de inercia), PDF 225-228 / impr. 180-183",
    "GUD Sec. 6.7.1-6.7.3, Tabla 6-6, Figs. 6-26 a 6-31 (envolvente de CG, limites, nube de cargas), PDF 228-236 / impr. 183-191",
    "GUD Sec. 6.7.6, Ecs. 6-152 a 6-157, Tabla 6-9 y Ejemplo 6-10 (tolerancias), PDF 237-239 / impr. 192-194",
]
G = 9.80665


def total_weight(items) -> float:
    """Ec. 6-128 (se trabaja con masas: W = m g, el CG no depende de g)."""
    return sum(i["mass_kg"] for i in items)


def moments(items, ref=(0.0, 0.0, 0.0)):
    """Ec. 6-129/6-130: momentos respecto de `ref` (por defecto el origen)."""
    return tuple(sum(i["mass_kg"] * (i[k] - r) for i in items) for k, r in zip(("x_m", "y_m", "z_m"), ref))


def cg_location(items) -> tuple[float, float, float]:
    """Ecs. 6-134 a 6-136: R_CG = sum(W_i r_i) / sum(W_i)."""
    w = total_weight(items)
    if w <= 0.0:
        raise ValueError("total weight must be positive")
    mx, my, mz = moments(items)
    return mx / w, my / w, mz / w


def pct_mgc(x_cg: float, x_mgc_le: float, c_mgc: float) -> float:
    """Ec. 6-137: P_CG = 100 (X_CG - x_MGC) / c_MGC."""
    return 100.0 * (x_cg - x_mgc_le) / c_mgc


def inertia(items, cg=None) -> dict:
    """Ecs. 6-144 y 6-148 con masas: I_xx = sum m [(y - Y)^2 + (z - Z)^2] + I_xx,i, etc.; I_xy = sum m (x - X)(y - Y) + I_xy,i.
    Cada item puede traer sus propios momentos y productos alrededor de su CG (`i_xx`, `i_yy`, `i_zz`, `i_xy`, `i_xz`, `i_yz`, kg m^2)."""
    cg = cg or cg_location(items)
    ixx = iyy = izz = ixy = ixz = iyz = 0.0
    for i in items:
        dx, dy, dz = i["x_m"] - cg[0], i["y_m"] - cg[1], i["z_m"] - cg[2]
        m = i["mass_kg"]
        ixx += m * (dy * dy + dz * dz) + i.get("i_xx", 0.0)
        iyy += m * (dx * dx + dz * dz) + i.get("i_yy", 0.0)
        izz += m * (dx * dx + dy * dy) + i.get("i_zz", 0.0)
        ixy += m * dx * dy + i.get("i_xy", 0.0)
        ixz += m * dx * dz + i.get("i_xz", 0.0)
        iyz += m * dy * dz + i.get("i_yz", 0.0)
    return {"ixx": ixx, "iyy": iyy, "izz": izz, "ixy": ixy, "ixz": ixz, "iyz": iyz}


def inertia_matrix(i: dict) -> np.ndarray:
    """Ec. 6-151: matriz de inercia (simetrica) con productos de inercia de signo negativo fuera de la diagonal."""
    return np.array([[i["ixx"], -i["ixy"], -i["ixz"]], [-i["ixy"], i["iyy"], -i["iyz"]], [-i["ixz"], -i["iyz"], i["izz"]]])


def principal_moments(i: dict) -> dict:
    """Momentos principales y ejes principales (autovalores y autovectores de la matriz de inercia)."""
    vals, vecs = np.linalg.eigh(inertia_matrix(i))
    return {"moments_kgm2": [float(v) for v in vals], "axes": [[float(c) for c in vecs[:, k]] for k in range(3)]}


def rotate_planar(ixx: float, iyy: float, ixy: float, theta_rad: float) -> dict:
    """Ec. 6-150 (axes x-y girados un angulo theta a u-v):
    I_uu = (Ixx + Iyy)/2 + (Ixx - Iyy)/2 cos 2theta - Ixy sin 2theta, I_vv = (Ixx + Iyy)/2 - (Ixx - Iyy)/2 cos 2theta + Ixy sin 2theta,
    I_uv = (Ixx - Iyy)/2 sin 2theta + Ixy cos 2theta; el angulo principal (I_uv = 0) es theta_P = (1/2) atan(-2 Ixy / (Ixx - Iyy)):
    el signo del PDF original se pierde en la conversion y se fijo imponiendo I_uv = 0 en estas mismas ecuaciones (D-30).
    Convencion: Ixy = integral de x y dm (producto positivo)."""
    c, s = math.cos(2.0 * theta_rad), math.sin(2.0 * theta_rad)
    mean, half = (ixx + iyy) / 2.0, (ixx - iyy) / 2.0
    theta_p = 0.5 * math.atan2(-2.0 * ixy, ixx - iyy)
    return {"iuu": mean + half * c - ixy * s, "ivv": mean - half * c + ixy * s, "iuv": half * s + ixy * c, "theta_principal_rad": theta_p}


def cg_with_tolerances(items) -> dict:
    """Ecs. 6-153 a 6-157: items con `dw_kg`, `dx_m`, `dy_m`, `dz_m`. Devuelve peso y CG minimo, nominal y maximo
    (X_CGmin = M_xmin / W_min, X_CGmax = M_xmax / W_max, como en el Ejemplo 6-10)."""
    out = {}
    for tag, sign in (("min", -1.0), ("nom", 0.0), ("max", 1.0)):
        w = sum(i["mass_kg"] + sign * i.get("dw_kg", 0.0) for i in items)
        mom = [sum((i["mass_kg"] + sign * i.get("dw_kg", 0.0)) * (i[k] + sign * i.get(d, 0.0)) for i in items)
               for k, d in (("x_m", "dx_m"), ("y_m", "dy_m"), ("z_m", "dz_m"))]
        out[tag] = {"weight_kg": w, "moments": mom, "cg": [m / w for m in mom]}
    return out


def cg_from_weighing(r_main: float, r_nose: float, x_nm: float) -> dict:
    """Ecs. 6-138 y 6-139: distancia del CG al tren de nariz x_N = R_M x_NM / W y al principal x_M = (1 - R_M/W) x_NM."""
    w = r_main + r_nose
    return {"weight": w, "x_from_nose_gear": r_main * x_nm / w, "x_from_main_gear": (1.0 - r_main / w) * x_nm,
            "nose_gear_fraction": r_nose / w, "main_gear_fraction": r_main / w}


def point_in_polygon(x: float, y: float, poly) -> bool:
    inside = False
    n = len(poly)
    for k in range(n):
        x1, y1 = poly[k]
        x2, y2 = poly[(k + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def loading_cloud(base: dict, stations: dict, combos: list, x_mgc_le: float, c_mgc: float, envelope=None) -> list:
    """Sec. 6.7.3: CG (y % c_MGC) de cada combinacion de ocupantes, equipaje y combustible sobre el avion vacio.
    base: {mass_kg, x_m} del avion vacio; stations: {nombre: x_m}; combos: [{id, loads: {nombre: kg}}]."""
    rows = []
    for c in combos:
        m = base["mass_kg"] + sum(c["loads"].values())
        mom = base["mass_kg"] * base["x_m"] + sum(kg * stations[n] for n, kg in c["loads"].items())
        x = mom / m
        row = {"id": c["id"], "mass_kg": m, "x_cg_m": x, "cg_pct_mgc": pct_mgc(x, x_mgc_le, c_mgc)}
        if envelope is not None:
            row["inside_envelope"] = point_in_polygon(row["cg_pct_mgc"], m, envelope)
        rows.append(row)
    return rows


def box_envelope(w_empty: float, w_max: float, fwd_pct: float, aft_pct: float):
    """Paso 1 de la Sec. 6.7.2: envolvente de caja entre el peso vacio y el peso maximo y los limites delantero y trasero (% c_MGC)."""
    return [(fwd_pct, w_empty), (aft_pct, w_empty), (aft_pct, w_max), (fwd_pct, w_max)]


def _items_from_inputs(project: dict, d: dict, depends: list) -> list:
    items = [dict(i) for i in d.get("items", [])]
    if d.get("from_m12"):
        if "m12" not in project["outputs"]:
            raise SystemExit("inputs.m13.from_m12 is set but outputs.m12 is missing: run m12 first")
        depends.append("m12")
        comps = project["outputs"]["m12"]["result"]["components"]
        pos = d.get("positions_m", {})
        missing = [n for n, c in comps.items() if c["kg"] is not None and n not in pos]
        if missing:
            raise SystemExit("inputs.m13.positions_m (component CG [x, y, z] in m) is missing for: " + ", ".join(missing))
        for n, c in comps.items():
            if c["kg"] is not None:
                items.append({"name": n, "mass_kg": c["kg"], "x_m": pos[n][0], "y_m": pos[n][1], "z_m": pos[n][2], "source": "M12"})
    if not items:
        raise SystemExit("inputs.m13 needs `items` (point masses) or from_m12 with positions_m")
    for i in items:
        for k in ("mass_kg", "x_m", "y_m", "z_m"):
            if k not in i:
                raise SystemExit(f"inputs.m13 item {i.get('name', '?')} is missing {k}")
    return items


def evaluate(project: dict) -> tuple[dict, list]:
    d = prj.need_inputs(project, "m13", [])
    depends: list = []
    items = _items_from_inputs(project, d, depends)
    w = total_weight(items)
    cg = cg_location(items)
    res = {"level": "conceptual", "units": "SI (kg, m, kg m^2)", "items": len(items), "total_mass_kg": w,
           "moments_kgm": list(moments(items)), "cg_m": list(cg)}
    ref = d.get("reference")           # {"x_mgc_le_m", "c_mgc_m"}; o de M09b (planta) con x_mgc medido desde el dato
    if ref is None and "m09b" in project["outputs"]:
        pf = project["outputs"]["m09b"]["result"]["planform"]
        ref = {"x_mgc_le_m": pf["xmgc_le_m"], "c_mgc_m": pf["cmgc_m"]}
        depends.append("m09b")
    if ref:
        res["cg_pct_mgc"] = pct_mgc(cg[0], ref["x_mgc_le_m"], ref["c_mgc_m"])
        res["reference"] = ref
    inr = inertia(items, cg)
    res["inertia_about_cg_kgm2"] = inr
    res["inertia_matrix_kgm2"] = inertia_matrix(inr).tolist()
    res["principal"] = principal_moments(inr)
    res["inertia_note"] = ("components without their own inertia are treated as point masses (Sec. 6.6.7 allows omitting it for "
                           "low-mass items); heavy items (engine, wing) should bring `i_xx`, `i_yy`, `i_zz`")
    if any("dw_kg" in i or "dx_m" in i for i in items):
        res["tolerances"] = cg_with_tolerances(items)
    if d.get("weighing"):
        wgh = d["weighing"]
        res["weighing"] = cg_from_weighing(wgh["main_gear_reaction"], wgh["nose_gear_reaction"], wgh["gear_spacing_m"])
    # --- nube de cargas y envolvente ---
    env = d.get("envelope")
    polygon = None
    if env:
        if "polygon" in env:
            polygon = [tuple(p) for p in env["polygon"]]
        else:
            polygon = box_envelope(env["empty_mass_kg"], env["max_mass_kg"], env["forward_limit_pct_mgc"], env["aft_limit_pct_mgc"])
        res["envelope"] = {"polygon_pct_mgc_mass_kg": [list(p) for p in polygon],
                           "limits_source": env.get("source", "user input"),
                           "note": "forward/aft limits come from stability and control analysis (M16, Chs. 24-25): input data here"}
        if "cg_pct_mgc" in res:
            res["envelope"]["empty_cg_inside"] = point_in_polygon(res["cg_pct_mgc"], w, polygon)
    if d.get("loading") and ref:
        ld = d["loading"]
        base = {"mass_kg": w, "x_m": cg[0]}
        res["loading_cloud"] = loading_cloud(base, ld["stations_m"], ld["combinations"], ref["x_mgc_le_m"], ref["c_mgc_m"], polygon)
        pcts = [r["cg_pct_mgc"] for r in res["loading_cloud"]]
        res["loading_cloud_range_pct_mgc"] = [min(pcts), max(pcts)]
        if polygon:
            res["loading_cloud_outside"] = [r["id"] for r in res["loading_cloud"] if not r["inside_envelope"]]
    elif d.get("loading"):
        raise SystemExit("inputs.m13.loading needs the MGC reference (inputs.m13.reference or outputs.m09b)")
    return res, depends


def run(project: dict) -> dict:
    result, depends = evaluate(project)
    prj.record(project, "m13", result, "conceptual", REFERENCES, sorted(set(depends)))
    return result
