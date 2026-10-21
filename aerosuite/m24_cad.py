"""M24 Exportacion CAD a STEP de la geometria exterior (OML) (Gudmundsson Tabla 1-4 paso 24; Sobester & Forrester Caps. 2-4).

Nivel conceptual. Solo la geometria exterior de M10 (`aerosuite-oml/1`): ala y colas por solevado recto (ruled) entre secciones con la
cuerda, torsion, diedro y flecha que define M10; cada perfil es una curva suave (dos splines extradosal/intradosal unidos en el borde de
ataque, mas un segmento si el borde de salida es romo), no un poligono; fuselaje como solido de revolucion de sus estaciones (equivale al
solevado de circulos entre estaciones: troncos de cono, como la estimacion de area mojada de M10). Sin estructura y sin elementos que M10 no
defina. Unidades de salida: milimetros (convencion de STEP).

Ejes de salida (convencion de SolidWorks, D-54): X hacia atras (cuerda), Y hacia arriba (espesor), Z a lo largo de la envergadura; el perfil
de la raiz queda en el plano Frontal (XY) en Z = 0, que es el plano de simetria de la aeronave, y el ala se extiende en horizontal a ambos
lados. Transformacion desde M10 (x atras, y estribor, z arriba): (X, Y, Z) = (x, z, -y), un giro de -90 grados alrededor de X (determinante +1,
sin espejo). CadQuery (motor OCP/OpenCASCADE) se importa de forma diferida: el nucleo de AeroSuite no depende de el.

Salidas en `<out_dir>` (por defecto `cad/<proyecto>`): `<proyecto>.step` (ensamble con una pieza por superficie, con nombre), un STEP por
componente y `manifest.json` (versiones, unidades, ejes, origen del proyecto y SHA-256, validacion). Validacion: se reimporta cada STEP
y se compara con invariantes calculados de M10 sin CAD (volumen del ala y colas por la integral de la seccion, volumen del fuselaje por
troncos de cono, area en planta, envergadura y caja envolvente)."""
import hashlib
import json
import math
from pathlib import Path

from . import project as prj
from .airfoils import naca4

REFERENCES = [
    "SOB Sec. 2.4.3 (fuselaje 3D por solevado de secciones) y Sec. 4.1, Ec. 4.1 (superficie solevada entre dos curvas), PDF 36-46 y 85-86",
    "AeroSuite M10 `aerosuite-oml/1` (ejes, secciones, unidades)",
    "ISO 10303 (STEP): unidades de longitud en milimetros por convencion; escritor de OpenCASCADE (OCP)",
]
MM = 1000.0
INSTALL_HINT = ("M24 needs CadQuery (OCP/OpenCASCADE). Install it from PyPI inside the project environment: "
                "python -m pip install --no-deps -r requirements-cad.txt (versions in requirements-cad.txt)")
TOL = {"volume": 0.01, "planform_area": 0.01, "span": 1e-6, "bbox": 1e-6}     # declared validation tolerances (relative)


def require_cadquery():
    try:
        import cadquery as cq
        return cq
    except ImportError as exc:
        raise SystemExit(INSTALL_HINT) from exc


# --------------------------------------------------------------------------- perfiles
def read_selig(path) -> list[tuple[float, float]]:
    pts = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.replace(",", " ").split()
        try:
            x, z = float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            continue
        pts.append((x, z))
    if len(pts) < 5:
        raise ValueError(f"{path}: fewer than 5 coordinates")
    return pts


def foil_points(ident: str, d: dict) -> list[tuple[float, float]]:
    """Coordenadas Selig (TE superior -> LE -> TE inferior, c = 1). NACA 4 digitos generados; otros desde inputs.m24.airfoil_files."""
    te = d.get("te", "closed")
    if te not in ("closed", "open"):
        raise SystemExit("inputs.m24.te must be 'closed' (sharp trailing edge) or 'open' (blunt, as generated)")
    key = ident.lower()
    files = {k.lower(): v for k, v in d.get("airfoil_files", {}).items()}
    code = key.removeprefix("naca")
    if key in files:
        pts = read_selig(files[key])
    elif len(code) == 4 and code.isdigit():
        pts = naca4(code, int(d.get("profile_points", 61)), closed_te=(te == "closed"))
    else:
        raise SystemExit(f"airfoil {ident!r}: only NACA 4-digit sections are generated; give inputs.m24.airfoil_files {{id: path to a Selig .dat}}")
    if te == "closed":
        mid = ((pts[0][0] + pts[-1][0]) / 2.0, (pts[0][1] + pts[-1][1]) / 2.0)      # cierra el borde de salida en su punto medio
        pts = [mid] + pts[1:-1] + [mid]
    return pts


def polygon_area(pts) -> float:
    s = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def _ring(pts):
    """Puntos del anillo cerrado sin duplicar el ultimo si coincide con el primero."""
    if abs(pts[0][0] - pts[-1][0]) < 1e-12 and abs(pts[0][1] - pts[-1][1]) < 1e-12:
        return list(pts[:-1])
    return list(pts)


# --------------------------------------------------------------------------- contornos 3D (m)
def section_points(comp: dict, sec: dict, pts) -> list[list[float]]:
    """Contorno 3D (m) de una seccion de M10; misma convencion que M10 (torsion respecto del borde de ataque de la seccion)."""
    c, x0, y, z0 = sec["chord_m"], sec["x_le_m"], sec["y_m"], sec["z_le_m"]
    if comp["type"] == "vertical_tail":                                  # espesor en y, plano z = const
        return [[x0 + px * c, pz * c, z0] for px, pz in pts]
    a = math.radians(sec["twist_deg"])
    return [[x0 + px * c * math.cos(a) + pz * c * math.sin(a), y, z0 - px * c * math.sin(a) + pz * c * math.cos(a)] for px, pz in pts]


def surface_stations(comp: dict, d: dict) -> list[dict]:
    """Lista ordenada de secciones de punta a punta: lado izquierdo reflejado, raiz, lado derecho (superficies simetricas).
    Cada elemento: {"pts": contorno 3D (m, ejes M10, sin punto repetido), "ile": indice del borde de ataque, "closed_te": bool}."""
    stations = []
    for sec in comp["sections"]:
        ident = sec["airfoil"].split("->")[0].strip()
        foil = foil_points(ident, d)
        closed = abs(foil[0][0] - foil[-1][0]) < 1e-12 and abs(foil[0][1] - foil[-1][1]) < 1e-12
        ring = _ring(foil)
        stations.append({"pts": section_points(comp, sec, ring), "ile": _le_index(ring), "closed_te": closed})
    if comp["symmetric"]:
        left = [{**s, "pts": [[x, -y, z] for x, y, z in s["pts"]]} for s in stations[:0:-1]]
        return left + stations
    return stations


def section_files(comp: dict, d: dict) -> list[dict]:
    """Contornos de cada seccion en ejes SolidWorks (mm), listos para `Insertar > Curva > Curva por puntos XYZ`: TE superior -> LE -> TE inferior."""
    out = []
    for i, st in enumerate(surface_stations(comp, d)):
        pts = [[c * MM for c in to_cad_xyz(p)] for p in st["pts"]]
        if st["closed_te"]:
            pts = pts + [pts[0]]
        out.append({"index": i, "points_mm": pts, "closed": st["closed_te"]})
    return out


def to_cad_xyz(p):
    """Punto M10 (x atras, y estribor, z arriba) -> convencion SolidWorks (X atras, Y arriba, Z envergadura): (x, z, -y)."""
    return [p[0], p[2], -p[1]]


def _le_index(pts) -> int:
    return min(range(len(pts)), key=lambda i: pts[i][0])


def _wire(cq, pts_m, ile, closed_te):
    """Perfil como curva suave: spline por el extrados (TE -> LE) y spline por el intrados (LE -> TE); si el borde de salida es romo,
    un segmento recto lo cierra. `pts_m` es el anillo sin punto repetido (indice 0 = TE superior, `ile` = borde de ataque)."""
    v = [cq.Vector(x * MM, y * MM, z * MM) for x, y, z in pts_m]
    upper = v[:ile + 1]
    lower = v[ile:] + ([v[0]] if closed_te else [])
    edges = [cq.Edge.makeSpline(upper), cq.Edge.makeSpline(lower)]
    if not closed_te:
        edges.append(cq.Edge.makeLine(v[-1], v[0]))
    return cq.Wire.assembleEdges(edges)


def build_surface(cq, comp: dict, d: dict):
    stations = surface_stations(comp, d)
    try:
        solid = cq.Solid.makeLoft([_wire(cq, st["pts"], st["ile"], st["closed_te"]) for st in stations], True)
    except Exception as exc:
        raise SystemExit(f"M24: the loft of component {comp['name']!r} failed: {type(exc).__name__}: {exc}") from exc
    _check_solid(cq, solid, comp["name"])
    return solid


def build_fuselage(cq, comp: dict):
    n1, n2 = comp["section"]["n1"], comp["section"]["n2"]
    if abs(n1 - 0.5) > 1e-9 or abs(n2 - 0.5) > 1e-9:
        raise SystemExit(f"M24: fuselage section n1 = {n1}, n2 = {n2}: only circular sections (0.5, 0.5) are exported; M10 gives the "
                         "section exponent but not a width law, so a generalized section is not built")
    z0 = comp["axis_z_m"]
    st = comp["stations"]
    prof = [(st[0]["x_m"], 0.0)] + [(s["x_m"], s["radius_m"]) for s in st if s["radius_m"] > 0.0] + [(st[-1]["x_m"], 0.0)]
    pts = [cq.Vector(x * MM, 0.0, (z0 + r) * MM) for x, r in prof]
    try:
        wire = cq.Wire.makePolygon(pts, close=True)
        solid = cq.Solid.revolve(cq.Face.makeFromWires(wire), 360.0, cq.Vector(st[0]["x_m"] * MM, 0, z0 * MM),
                                 cq.Vector(st[-1]["x_m"] * MM, 0, z0 * MM))
    except Exception as exc:
        raise SystemExit(f"M24: the fuselage solid could not be built: {type(exc).__name__}: {exc}") from exc
    _check_solid(cq, solid, comp.get("name", "fuselage"))
    return solid


def _check_solid(cq, solid, name):
    if not solid.isValid() or volume_mm3(solid) <= 0.0:
        raise SystemExit(f"M24: component {name!r} did not produce a valid solid (valid={solid.isValid()}, volume={volume_mm3(solid):.3f} mm3)")


# --------------------------------------------------------------------------- invariantes sin CAD (m, m2, m3)
def reference_invariants(comp: dict, d: dict) -> dict:
    if comp["type"] == "fuselage":
        st = comp["stations"]
        vol = sum(math.pi * (b["x_m"] - a["x_m"]) / 3.0 * (a["radius_m"] ** 2 + a["radius_m"] * b["radius_m"] + b["radius_m"] ** 2)
                  for a, b in zip(st, st[1:]))
        return {"volume_m3": vol, "length_m": st[-1]["x_m"] - st[0]["x_m"],
                "bbox_m": {"x": [st[0]["x_m"], st[-1]["x_m"]], "y": [-comp["max_radius_m"], comp["max_radius_m"]],
                           "z": [comp["axis_z_m"] - comp["max_radius_m"], comp["axis_z_m"] + comp["max_radius_m"]]}}
    secs = comp["sections"]
    vertical = comp["type"] == "vertical_tail"
    ring = []
    for sec in secs:
        pts3 = section_points(comp, sec, _ring(foil_points(sec["airfoil"].split("->")[0].strip(), d)))
        ring.append([(p[0], p[1] if vertical else p[2]) for p in pts3])          # seccion en el plano z = const (VT) o y = const
    vol = 0.0
    for a, b, sa, sb in zip(ring, ring[1:], secs, secs[1:]):
        mid = [((p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0) for p, q in zip(a, b)]
        length = abs(sb["z_le_m"] - sa["z_le_m"]) if vertical else abs(sb["y_m"] - sa["y_m"])
        vol += length * (polygon_area(a) + 4.0 * polygon_area(mid) + polygon_area(b)) / 6.0     # Simpson: A(u) es cuadratica para un loft recto
    if comp["symmetric"]:
        vol *= 2.0
    out = {"volume_m3": vol, "planform_area_m2": comp["planform_area_m2"]}
    if comp["type"] == "vertical_tail":
        out["height_m"] = comp["semi_span_m"]
    else:
        out["span_m"] = 2.0 * comp["semi_span_m"]
    return out


def volume_mm3(shape, eps: float = 1e-8) -> float:
    """Volumen (mm3) con integracion adaptativa de OpenCASCADE hasta el error relativo `eps`. `Shape.Volume()` usa la precision por defecto y
    para superficies B-spline puede errar ~1 % (comprobado en una cola prismatica de NACA 0009: 0.2635 frente a 0.2660 m3)."""
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape.wrapped, props, eps, False, False)
    return props.Mass()


def _bbox_m(shape):
    b = shape.BoundingBox()
    return {"x": [b.xmin / MM, b.xmax / MM], "y": [b.ymin / MM, b.ymax / MM], "z": [b.zmin / MM, b.zmax / MM]}


def measure_planform(cq, solid, comp: dict, n: int = 41) -> float:
    """Area en planta por rebanadas: integral trapezoidal de la cuerda (extension en x de la seccion) sobre la envergadura (y) o la altura (z)."""
    b = solid.BoundingBox()
    vertical = comp["type"] == "vertical_tail"
    lo, hi = (b.zmin, b.zmax) if vertical else (b.ymin, b.ymax)
    xs = [lo + (hi - lo) * (i + 0.5) / n for i in range(n)]               # puntos medios: evita las caras extremas
    total = 0.0
    big = 10.0 * max(b.xlen, b.ylen, b.zlen)
    for t in xs:
        plane = (cq.Plane(origin=(0, 0, t), xDir=(1, 0, 0), normal=(0, 0, 1)) if vertical
                 else cq.Plane(origin=(0, t, 0), xDir=(1, 0, 0), normal=(0, 1, 0)))
        face = cq.Face.makePlane(big, big, basePnt=plane.origin, dir=plane.zDir)
        section = solid.intersect(face)
        total += section.BoundingBox().xlen
    return total / n * (hi - lo) / MM ** 2


def shape_to_cad(shape):
    """Forma en ejes M10 -> ejes SolidWorks: giro de -90 grados alrededor de X, (x, y, z) -> (x, z, -y)."""
    return shape.rotate((0, 0, 0), (1, 0, 0), -90)


def shape_from_cad(shape):
    return shape.rotate((0, 0, 0), (1, 0, 0), 90)


AXES_CAD = {"x": "aft, along the chord (SolidWorks X)", "y": "up, airfoil thickness direction (SolidWorks Y)",
            "z": "along the span, positive to the M10 port side (SolidWorks Z, normal to the Front plane)",
            "origin": "leading edge of the wing root chord at the plane of symmetry; the root airfoil lies in the Front plane (XY) at Z = 0",
            "transform_from_m10": "(X, Y, Z) = (x, z, -y), rotation of -90 degrees about X (determinant +1, no mirror)"}


def _rel(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1e-12)


# --------------------------------------------------------------------------- modulo
def evaluate(project: dict, project_path=None) -> tuple[dict, list]:
    d = project["inputs"].get("m24", {})
    if "m10" not in project["outputs"]:
        raise SystemExit("inputs.m24 needs outputs.m10: run m10 first")
    oml = project["outputs"]["m10"]["result"]
    if oml.get("schema") != "aerosuite-oml/1":
        raise SystemExit(f"M24 reads aerosuite-oml/1, not {oml.get('schema')!r}")
    cq = require_cadquery()
    import numpy
    name = project["name"].replace(" ", "_")
    out_dir = Path(d.get("out_dir", Path("cad") / name))
    if (out_dir / "manifest.json").exists() and not d.get("overwrite", False):
        raise SystemExit(f"{out_dir} already has an M24 export; use another inputs.m24.out_dir (or inputs.m24.overwrite = true)")
    out_dir.mkdir(parents=True, exist_ok=True)
    comps = {c["name"] if c["type"] != "fuselage" else "fuselage": c for c in oml["components"]}
    solids, refs = {}, {}
    for cname, comp in comps.items():
        solids[cname] = build_fuselage(cq, comp) if comp["type"] == "fuselage" else build_surface(cq, comp, d)
        refs[cname] = reference_invariants(comp, d)
    files = {}
    cad = {k: shape_to_cad(v) for k, v in solids.items()}                       # ejes SolidWorks
    for cname, solid in cad.items():
        path = out_dir / f"{name}-{cname}.step"
        cq.exporters.export(cq.Workplane(obj=solid), str(path), exportType="STEP")
        files[cname] = path
    section_txt = {}
    sec_dir = out_dir / "sections"
    sec_dir.mkdir(exist_ok=True)
    for cname, comp in comps.items():
        if comp["type"] == "fuselage":
            continue
        for sf in section_files(comp, d):
            fp = sec_dir / f"{name}-{cname}-sec{sf['index']:02d}.txt"
            fp.write_text("".join(f"{x:.6f}\t{y:.6f}\t{z:.6f}\n" for x, y, z in sf["points_mm"]), encoding="utf-8")
            section_txt.setdefault(cname, []).append(str(fp))
    assy = cq.Assembly(name=name)
    for cname, solid in cad.items():
        assy.add(solid, name=cname)
    full = out_dir / f"{name}.step"
    assy.export(str(full), exportType="STEP")
    # --- validacion: reimportar y comparar con M10 ---
    checks, ok_all = [], True

    def cmp(component, quantity, got, ref, tol):
        nonlocal ok_all
        ok = _rel(got, ref) <= tol
        ok_all &= ok
        checks.append({"component": component, "quantity": quantity, "step": got, "reference": ref, "relative_difference": _rel(got, ref),
                       "tolerance": tol, "ok": ok})

    for cname, comp in comps.items():
        back_cad = cq.importers.importStep(str(files[cname])).val()
        if not back_cad.isValid():
            raise SystemExit(f"M24: the reimported STEP of {cname!r} is not a valid shape")
        bc = _bbox_m(back_cad)                                                  # ejes SolidWorks
        back = shape_from_cad(back_cad)                                         # de vuelta a ejes M10 para comparar con M10
        ref, bb = refs[cname], _bbox_m(back)
        if comp["type"] == "fuselage":
            cmp(cname, "cad_axis_Y_extent_m", bc["y"][1] - bc["y"][0], 2.0 * comp["max_radius_m"], TOL["bbox"])
            cmp(cname, "cad_axis_Z_extent_m", bc["z"][1] - bc["z"][0], 2.0 * comp["max_radius_m"], TOL["bbox"])
        elif comp["type"] == "vertical_tail":
            cmp(cname, "cad_height_along_Y_m", bc["y"][1] - bc["y"][0], ref["height_m"], TOL["span"])
        else:
            cmp(cname, "cad_span_along_Z_m", bc["z"][1] - bc["z"][0], ref["span_m"], TOL["span"])
            ok_sym = abs(bc["z"][1] + bc["z"][0]) < 1e-6 * max(1.0, ref["span_m"])
            ok_all &= ok_sym
            checks.append({"component": cname, "quantity": "cad_midplane_at_Z0_m", "step": 0.5 * (bc["z"][1] + bc["z"][0]),
                           "reference": 0.0, "tolerance": "1e-6*span", "ok": bool(ok_sym)})
        cmp(cname, "volume_m3", volume_mm3(back) / MM ** 3, ref["volume_m3"], TOL["volume"])
        if comp["type"] == "fuselage":
            cmp(cname, "length_m", bb["x"][1] - bb["x"][0], ref["length_m"], TOL["bbox"])
            cmp(cname, "max_diameter_m", bb["y"][1] - bb["y"][0], 2.0 * comp["max_radius_m"], TOL["bbox"])
        else:
            cmp(cname, "planform_area_m2", measure_planform(cq, back, comp), ref["planform_area_m2"], TOL["planform_area"])
            if comp["type"] == "vertical_tail":
                cmp(cname, "height_m", bb["z"][1] - bb["z"][0], ref["height_m"], TOL["span"])
            else:
                cmp(cname, "span_m", bb["y"][1] - bb["y"][0], ref["span_m"], TOL["span"])
    whole = cq.importers.importStep(str(full))
    n_solids = len(whole.solids().vals())
    ok_all &= n_solids == len(comps)
    box = whole.val().BoundingBox()
    wing = next((c for c in comps.values() if c["type"] == "wing"), None)
    if wing is not None:                       # el perfil de la raiz debe quedar en el plano Frontal (XY) en Z = 0
        wing_back = cq.importers.importStep(str(files["wing"])).val()
        root = wing_back.intersect(cq.Face.makePlane(1e5, 1e5, basePnt=cq.Vector(0, 0, 0), dir=cq.Vector(0, 0, 1)))
        rb = root.BoundingBox()
        c_root = wing["sections"][0]["chord_m"] * MM
        ok_root = abs(rb.xlen - c_root) < 1e-3 * c_root and rb.ylen < 0.3 * c_root and rb.ylen > 0
        ok_all &= ok_root
        checks.append({"component": "wing", "quantity": "root_airfoil_in_front_plane", "step": {"chord_mm": rb.xlen, "thickness_mm": rb.ylen},
                       "reference": {"chord_mm": c_root}, "tolerance": "chord 1e-3 relative, thickness < 0.3 chord", "ok": bool(ok_root)})
    raw = Path(project_path).read_bytes() if project_path and Path(project_path).is_file() else None
    result = {
        "level": "conceptual", "units_out": "mm", "units_internal": "SI (m)", "axes": AXES_CAD, "axes_m10": oml["axes"], "origin_of_part": "M10 datum",
        "section_files_xyz_mm": section_txt, "airfoil_curve": "two splines (upper/lower) joined at the leading edge; straight closing segment if te = open",
        "oml_schema": oml["schema"], "out_dir": str(out_dir), "assembly_step": str(full), "component_steps": {k: str(v) for k, v in files.items()},
        "te": d.get("te", "closed"), "profile_points": int(d.get("profile_points", 61)),
        "fuselage_note": "solid of revolution of the M10 stations (frusta, equal to a loft of circles between stations)",
        "assembly_solids": n_solids, "assembly_bbox_mm_cad_axes": {"x": [box.xmin, box.xmax], "y": [box.ymin, box.ymax], "z": [box.zmin, box.zmax]},
        "validation": {"all_ok": bool(ok_all), "tolerances": TOL, "checks": checks,
                       "method": "STEP re-imported with CadQuery; volumes from OpenCASCADE (adaptive integration, eps 1e-8), planform area by 41 slices, bounding boxes; "
                                 "references computed from M10 without CAD"},
        "versions": {"cadquery": cq.__version__, "numpy": numpy.__version__,
                     "ocp": _ocp_version()},
        "source_project": {"path": str(project_path) if project_path else None, "sha256": hashlib.sha256(raw).hexdigest() if raw else None,
                           "m10_result_sha256": prj.digest(oml)}}
    (out_dir / "manifest.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    return result, ["m10"]


def _ocp_version() -> str:
    try:
        from importlib.metadata import version
        return version("cadquery-ocp")
    except Exception:  # pragma: no cover
        return "unknown"


def run(project: dict, project_path=None) -> dict:
    result, depends = evaluate(project, project_path)
    prj.record(project, "m24", result, "conceptual", REFERENCES, depends)
    return result
