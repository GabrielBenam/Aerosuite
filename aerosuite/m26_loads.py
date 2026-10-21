"""M26 Cargas aerodinamicas externas para Ansys (Gudmundsson Tabla 1-4 paso 26; no es dimensionamiento estructural).

Nivel conceptual. Para cada punto de esquina de M25 (V_EAS y n limite) y la masa de M25, se calculan sobre la geometria exterior:
  * sustentacion total n W (cuasi-estatica, vuelo simetrico, sustentacion vertical; se desprecia la componente de empuje), resistencia
    D = q S (C_Dmin + k C_L^2) con C_Dmin y k de M20 (polar parabolica, sin compresibilidad), y momentos con la cola;
  * equilibrio de momentos de cabeceo respecto al CG: L_w (x_cg - x_ac) + M_ac,w + L_t (x_cg - x_t) = 0, L_w + L_t = n W, con el centro
    aerodinamico del ala en c/4 de la CMG (Sec. 24.2 de la estabilidad del libro: h_ac,w = 0.25), M_ac,w = C_m,ac q S c_MGC con C_m,ac de la
    teoria de perfil delgado del perfil de raiz (NACA de 4 digitos) o dato; el fuselaje y el empuje no aportan momento (supuesto declarado);
  * distribucion en la envergadura con la linea sustentadora de Prandtl de M19 (`m19_stall.llt_solve`) a la incidencia que da el C_L del ala,
    con fuerza por estacion q c C_l dy, cortante y flector de la seccion (integrados hacia la punta), y, si hay un punto de operacion de
    flow5 (VLM2) cuyo C_L coincide con el de la condicion, la distribucion de flow5 leida con M-F5R, rotulada por origen;
  * cargas de inercia n m_i g de la lista de masas de M13 (+ cargas utiles de la combinacion mas cercana), sin alivio estructural: el
    cortante y el flector son solo aerodinamicos.
Ejes: M10 (x atras, y estribor, z arriba, origen en el borde de ataque de la raiz del ala); STEP de M24 en mm con ejes de SolidWorks
(X atras, Y arriba, Z envergadura): (x, y, z) -> (1000 x, 1000 z, -1000 y). SI interno."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from . import m19_stall as m19
from . import project as prj
from .m24_cad import to_cad_xyz

REFERENCES = [
    "GUD Sec. 9.7.3, Ecs. 9-166 a 9-172 (linea sustentadora de Prandtl; via M19)",
    "GUD Sec. 17.4.1 (condiciones de esquina del diagrama V-n; via M25) y Cap. 24 (centro aerodinamico del ala en 0.25 c_MGC; via M16)",
    "Teoria de perfil delgado: C_m,c/4 = -(pi/4)(A1 - A2) con A_n = (2/pi) int (dz/dx) cos(n theta) dtheta (Anderson, Fundamentals of Aerodynamics, Sec. 4.8; fuente externa conocida, pagina no verificada)",
    "flow5 7.55 (VLM2) puntos de operacion, tabla por estacion (M-F5R `parse_plane_opp`), solo contraste cuando el C_L coincide",
]
G = 9.80665
MM = 1000.0


def cm_ac_naca4(code: str, n: int = 4001) -> float:
    """C_m,c/4 de un NACA de 4 digitos por teoria de perfil delgado."""
    m, p = int(code[0]) / 100.0, int(code[1]) / 10.0
    if m == 0.0 or p == 0.0:
        return 0.0
    th = np.linspace(0.0, math.pi, n)
    x = 0.5 * (1.0 - np.cos(th))
    dz = np.where(x < p, 2.0 * m / p ** 2 * (p - x), 2.0 * m / (1.0 - p) ** 2 * (p - x))
    a = [2.0 / math.pi * float(np.sum(0.5 * ((dz * np.cos(k * th))[1:] + (dz * np.cos(k * th))[:-1]) * np.diff(th))) for k in (1, 2)]
    return -math.pi / 4.0 * (a[0] - a[1])


def _interp(sections, key, y):
    ys = [s["y_m"] for s in sections]
    return float(np.interp(y, ys, [s[key] for s in sections]))


def wing_loads(pf: dict, wing_comp: dict, airfoils: dict, azl_deg, washout_deg: float, cl_wing: float, q: float, n_terms: int = 40,
               n_stations: int = 21) -> dict:
    """Distribucion en la envergadura (semiala) con la linea sustentadora para un C_L de ala dado."""
    span = pf["span_m"]
    hb = span / 2.0
    cla_r, cla_t = (airfoils[e].get("cl_alpha_per_rad", 2 * math.pi) for e in ("root", "tip"))
    chords, cla, azl, twist, clmax = m19._distributions(pf, airfoils, washout_deg, azl_deg, cla_r, cla_t)
    s0 = m19.llt_solve(span, chords, cla, azl, twist, 0.0, n_terms)
    s1 = m19.llt_solve(span, chords, cla, azl, twist, 0.1, n_terms)
    slope = (s1["cl_total"] - s0["cl_total"]) / 0.1
    alpha = (cl_wing - s0["cl_total"]) / slope
    sol = m19.llt_solve(span, chords, cla, azl, twist, alpha, n_terms)
    secs = wing_comp["sections"]
    sw = wing_comp["semi_span_m"]

    def at(eta):
        y = eta * hb
        c = chords(eta)
        return {"eta": eta, "y_m": y, "chord_m": c, "cl": sol["cl_of"](eta), "clmax_section": clmax(eta),
                "x_c4_m": _interp(secs, "x_le_m", y * secs[-1]["y_m"] / hb) + 0.25 * c, "z_m": _interp(secs, "z_le_m", y * secs[-1]["y_m"] / hb)}

    # integracion fina en phi (y = hb cos phi, la serie de Fourier es regular alli)
    ph = np.linspace(0.0, math.pi / 2.0, 801)
    eta_f = np.cos(ph)
    lp = np.array([q * chords(e) * sol["cl_of"](e) for e in eta_f])          # fuerza por unidad de envergadura (N/m)
    y_f = hb * eta_f                                                         # decreciente en phi
    order = np.argsort(y_f)
    yy, ll = y_f[order], lp[order]
    seg = 0.5 * (ll[1:] + ll[:-1]) * np.diff(yy)
    shear_f = np.concatenate([np.cumsum(seg[::-1])[::-1], [0.0]])            # V(y) = int_y^hb l' dy'
    arm = 0.5 * (yy[1:] + yy[:-1])
    bend_f = np.concatenate([np.cumsum((0.5 * (ll[1:] + ll[:-1]) * np.diff(yy) * (arm))[::-1])[::-1], [0.0]])
    bend_f = bend_f - yy * shear_f                                           # M(y) = int_y^hb l'(y')(y' - y) dy'
    total_half = float(shear_f[0])
    etas = np.linspace(0.0, 1.0, n_stations + 1)
    edges = etas * hb
    rows = []
    for i in range(n_stations):
        em = 0.5 * (etas[i] + etas[i + 1])
        row = at(em)
        dy = edges[i + 1] - edges[i]
        v_in = float(np.interp(edges[i], yy, shear_f))
        v_out = float(np.interp(edges[i + 1], yy, shear_f))
        row.update({"y_in_m": float(edges[i]), "y_out_m": float(edges[i + 1]), "dy_m": float(dy), "force_n": v_in - v_out,
                    "force_per_span_n_per_m": (v_in - v_out) / dy, "shear_in_n": v_in,
                    "bending_in_nm": float(np.interp(edges[i], yy, bend_f)), "exceeds_clmax": bool(row["cl"] > row["clmax_section"])})
        rows.append(row)
    return {"alpha_root_deg": math.degrees(alpha), "cl_total_llt": sol["cl_total"], "e_induced": sol["e"], "area_llt_m2": sol["area_m2"],
            "half_wing_force_n": total_half, "stations": rows,
            "max_cl_over_clmax": max(r["cl"] / r["clmax_section"] for r in rows)}


def flow5_compare(opp_path, y_hb: list, cl_llt: list, cl_required: float, tol: float = 0.03) -> dict:
    """Lee un punto de operacion de flow5 y, si su C_L coincide con el requerido, devuelve la distribucion C_l(y)."""
    from .flow5_results import parse_plane_opp
    o = parse_plane_opp(Path(opp_path))
    wing = next(iter(o.span.values()), None)
    cl_f5 = o.scalars.get("CL")
    out = {"file": str(opp_path), "flow5_cl": cl_f5, "cl_required": cl_required, "tolerance": tol}
    if wing is None or cl_f5 is None:
        return {**out, "used": False, "reason": "el archivo no tiene tabla por estacion o C_L"}
    rows = [r for r in wing["rows"] if r["y_m"] >= 0]
    out["rows"] = len(rows)
    out["used"] = abs(cl_f5 / cl_required - 1.0) <= tol if cl_required else False
    if not out["used"]:
        out["reason"] = f"C_L de flow5 ({cl_f5:.4f}) no coincide con el de la condicion ({cl_required:.4f}) dentro de {tol:.0%}"
        return out
    out["stations"] = [{"y_m": r["y_m"], "cl": r["Cl"], "force_n": r.get("F_z")} for r in rows]
    return out


def evaluate(project: dict) -> tuple[dict, list]:
    d = project["inputs"].get("m26", {})
    out = project["outputs"]
    for need in ("m25", "m09b", "m10", "m13"):
        if need not in out:
            raise SystemExit(f"outputs.{need} is missing: run {need} first (M26 reads the M25 corner points, wing, OML and M13 mass/CG)")
    depends = ["m25", "m09b", "m10", "m13"]
    env = out["m25"]["result"]
    wing = out["m09b"]["result"]
    pf = wing["planform"]
    m9in = project["inputs"].get("m09b", {})
    airfoils = m9in.get("airfoils")
    if not airfoils:
        raise SystemExit("inputs.m09b.airfoils is missing")
    oml = out["m10"]["result"]
    comps = {c["name"] if c["type"] != "fuselage" else "fuselage": c for c in oml["components"]}
    wing_comp = comps["wing"]
    ht_comp = comps.get("horizontal_tail")
    if ht_comp is None:
        raise SystemExit("the OML has no horizontal_tail: the pitching-moment equilibrium needs it")
    assumptions = []
    # --- CG y masas ---
    m13 = out["m13"]["result"]
    cg_empty = m13["cg_m"]
    cloud = m13.get("loading_cloud", [])
    # --- propiedades aerodinamicas ---
    azl = None
    washout = m9in.get("washout_deg", 0.0)
    if "m19" in out:
        iu = out["m19"]["result"]["inputs_used"]
        azl, washout = iu["alpha_zl_deg"], iu["washout_deg"]
        depends.append("m19")
    else:
        azl = []
        for end in ("root", "tip"):
            code = airfoils[end].get("id", "").lower().replace("naca", "")
            if len(code) != 4 or not code.isdigit():
                raise SystemExit("run m19 or give 4-digit NACA airfoils in inputs.m09b.airfoils (alpha_ZL)")
            azl.append(m19.alpha_zl_naca4_deg(code))
        assumptions.append("alpha_ZL from thin-airfoil theory (M19 not run)")
    if "cm_ac_wing" in d:
        cm_ac, cm_src = d["cm_ac_wing"], "dato del usuario"
    else:
        code = airfoils["root"].get("id", "").lower().replace("naca", "")
        if len(code) != 4 or not code.isdigit():
            raise SystemExit("inputs.m26.cm_ac_wing is required for a non 4-digit root airfoil")
        cm_ac, cm_src = cm_ac_naca4(code), "teoria de perfil delgado del perfil de raiz " + airfoils["root"]["id"]
        assumptions.append(f"C_m,ac of the wing = {cm_ac:.4f} ({cm_src}); wing twist and fuselage effect on the moment not included")
    if "m20" in out:
        cd0, k_ind = out["m20"]["result"]["buildup"]["cd_min"], out["m20"]["result"]["induced"]["k"]
        depends.append("m20")
    else:
        cd0, k_ind = d.get("cd_min"), d.get("k_induced")
        if cd0 is None or k_ind is None:
            raise SystemExit("run m20 or give inputs.m26.cd_min and k_induced")
    s = pf["area_m2"]
    cmgc = pf["cmgc_m"]
    x_ac = pf["xmgc_le_m"] + 0.25 * cmgc
    ht_secs = ht_comp["sections"]
    m08 = out.get("m08", {}).get("result", {}).get("horizontal_tail", {})
    ymgc_ht = m08.get("ymgc_m", 0.0)
    if m08:
        depends.append("m08")
    c_ht = float(np.interp(ymgc_ht, [x["y_m"] for x in ht_secs], [x["chord_m"] for x in ht_secs]))
    x_t = float(np.interp(ymgc_ht, [x["y_m"] for x in ht_secs], [x["x_le_m"] for x in ht_secs])) + 0.25 * c_ht
    z_t = float(np.interp(ymgc_ht, [x["y_m"] for x in ht_secs], [x["z_le_m"] for x in ht_secs]))
    # --- lista de masas para las fuerzas de inercia ---
    from .m13_cg import _items_from_inputs
    items = _items_from_inputs(project, project["inputs"].get("m13", {}), [])
    if "m12" in out:
        depends.append("m12")
    flow5_inputs = {f["condition"]: f for f in d.get("flow5", [])}
    wanted = d.get("conditions")
    res = {"level": "conceptual (potencial lineal, cuasi-estatico, sin estructura ni alivio estructural)", "units": "SI",
           "axes_m10": oml["axes"], "axes_cad": "STEP de M24: mm; X atras, Y arriba, Z envergadura; (x, y, z)_M10 -> (1000 x, 1000 z, -1000 y)",
           "assumptions": assumptions, "wing": {"area_m2": s, "cmgc_m": cmgc, "x_ac_wing_m": x_ac, "cm_ac": cm_ac, "cm_ac_source": cm_src},
           "tail": {"x_ac_m": x_t, "z_m": z_t, "ymgc_m": ymgc_ht, "chord_m": c_ht}, "drag": {"cd_min": cd0, "k": k_ind}, "cases": []}
    assumptions += ["lift is taken vertical (wind axes ~ body axes): no thrust or alpha component; D, thrust and fuselage give no pitching moment",
                    "section shear and bending are aerodynamic only: no wing mass relief or structural response (outside the scope of M26)",
                    "total drag only (no spanwise drag distribution)"]
    for case in env["cases"]:
        mass = case["mass_kg"]
        w = mass * G
        if cloud:
            near = min(cloud, key=lambda c: abs(c["mass_kg"] - mass))
            cg_x, cg_src = d.get("cg_x_m", near["x_cg_m"]), f"M13 loading_cloud '{near['id']}' (masa {near['mass_kg']:.1f} kg, la mas cercana)"
            if "cg_x_m" in d:
                cg_src = "dato del usuario"
        else:
            cg_x, cg_src = d.get("cg_x_m", cg_empty[0]), "M13 (avion vacio)" if "cg_x_m" not in d else "dato del usuario"
        loads = []
        for c in case["corner_points"]:
            if wanted and c["name"] not in wanted:
                continue
            v, n = c["v_eas_mps"], c["n_limit"]
            q = 0.5 * 1.225 * v * v
            lift = n * w
            # equilibrio de cabeceo: L_t = (-M_ac - n W (x_cg - x_ac)) / (x_ac - x_t)
            m_ac = cm_ac * q * s * cmgc
            l_t = (-m_ac - lift * (cg_x - x_ac)) / (x_ac - x_t)
            l_w = lift - l_t
            cl_w = l_w / (q * s)
            cl_total = lift / (q * s)
            drag = q * s * (cd0 + k_ind * cl_total ** 2)
            wl = wing_loads(pf, wing_comp, airfoils, azl, washout, cl_w, q, n_stations=d.get("n_stations", 21))
            f5 = None
            if c["name"] in flow5_inputs:
                f5in = flow5_inputs[c["name"]]
                f5 = flow5_compare(f5in["opp"], [], [], cl_w, f5in.get("tolerance", 0.03))
                if f5.get("used"):
                    hb = pf["span_m"] / 2.0
                    diff = [r["cl"] - wing_cl for r in f5["stations"] for wing_cl in [float(np.interp(r["y_m"], [x["y_m"] for x in wl["stations"]],
                                                                                                         [x["cl"] for x in wl["stations"]]))]]
                    f5["rms_cl_difference_vs_lifting_line"] = float(np.sqrt(np.mean(np.square(diff))))
            stations = wl["stations"]
            sum_force = 2.0 * sum(r["force_n"] for r in stations)
            # momento de cabeceo de las estaciones respecto al CG (independiente del equilibrio): fuerzas en c/4 local + M_ac + cola + inercia
            mom_stations = 2.0 * sum(r["force_n"] * (cg_x - r["x_c4_m"]) for r in stations) + m_ac + l_t * (cg_x - x_t)
            loads.append({
                "name": c["name"], "v_eas_mps": v, "v_keas": c["v_keas"], "n_limit": n, "n_ultimate": c["n_ultimate"], "q_pa": q,
                "mass_kg": mass, "weight_n": w, "cg_x_m": cg_x, "cg_source": cg_src,
                "totals": {"lift_n": lift, "lift_wing_n": l_w, "tail_load_n": l_t, "drag_n": drag, "cl_aircraft": cl_total, "cl_wing": cl_w,
                           "pitching_moment_wing_ac_nm": m_ac, "root_bending_half_wing_nm": wl["stations"][0]["bending_in_nm"]},
                "wing_alpha_root_deg": wl["alpha_root_deg"], "span_distribution": {"source": "M19 lifting line (Prandtl)", **{k: wl[k] for k in (
                    "half_wing_force_n", "area_llt_m2", "max_cl_over_clmax")}, "stations": stations},
                "flow5_contrast": f5,
                "equilibrium": {"force_residual_n": sum_force + l_t - lift, "force_residual_relative": (sum_force + l_t - lift) / abs(lift) if lift else 0.0,
                                "pitch_residual_nm": mom_stations, "pitch_residual_relative_to_nWc": mom_stations / abs(lift * cmgc) if lift else 0.0,
                                "wing_station_force_n": sum_force, "wing_force_target_n": l_w}})
        masses = []
        for it in items:
            masses.append({"name": it["name"], "mass_kg": it["mass_kg"], "x_m": it["x_m"], "y_m": it["y_m"], "z_m": it["z_m"]})
        res["cases"].append({"name": case["case"], "mass_kg": mass, "conditions": loads, "inertia": {
            "inertia_about_cg_kgm2": m13["inertia_about_cg_kgm2"], "inertia_note": "avion vacio de M13 (sin cargas utiles de la combinacion)",
            "items": masses,
            "inertial_force_rule": "F_i = -n m_i g (opuesta a la sustentacion), en el CG de cada elemento"}})
    return res, sorted(set(depends))


def _write_files(result: dict, out_dir: Path, project: dict, project_path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for case in result["cases"]:
        for cond in case["conditions"]:
            for side, sgn in (("starboard", 1.0), ("port", -1.0)):
                for st in cond["span_distribution"]["stations"]:
                    y = sgn * st["y_m"]
                    cx, cy, cz = to_cad_xyz([st["x_c4_m"], y, st["z_m"]])
                    rows.append({"case": case["name"], "condition": cond["name"], "side": side, "n_limit": cond["n_limit"], "v_eas_mps": cond["v_eas_mps"],
                                 "y_m": y, "x_c4_m": st["x_c4_m"], "z_m": st["z_m"], "chord_m": st["chord_m"], "cl": st["cl"],
                                 "force_up_n": st["force_n"], "force_per_span_n_per_m": st["force_per_span_n_per_m"],
                                 "shear_n": st["shear_in_n"], "bending_nm": st["bending_in_nm"],
                                 "cad_x_mm": cx * MM, "cad_y_mm": cy * MM, "cad_z_mm": cz * MM, "cad_force_y_n": st["force_n"], "source": "M19 lifting line"})
    csv_path = out_dir / "stations.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    json_path = out_dir / "loads.json"
    payload = {"schema": "aerosuite-loads/1", "units": "SI (N, m, kg, Pa); CAD columns in mm", "axes_m10": result["axes_m10"], "axes_cad": result["axes_cad"],
               "force_direction": "force_up_n positive up (M10 +z = CAD +Y)", **{k: result[k] for k in ("level", "wing", "tail", "drag", "assumptions", "cases")}}
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    raw = Path(project_path).read_bytes() if project_path and Path(project_path).is_file() else None
    files = {}
    for p in (csv_path, json_path):
        files[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = {"schema": "aerosuite-loads-manifest/1", "module": "m26", "project": project["name"], "files_sha256": files,
                "source_project_sha256": hashlib.sha256(raw).hexdigest() if raw else None,
                "traceability": {"m25": project["outputs"]["m25"]["run"]["timestamp"], "m10_sha256": prj.digest(project["outputs"]["m10"]["result"])},
                "coordinate_transformation": result["axes_cad"], "ansys_input_files": "none generated (only CSV/JSON; point or distributed loads)"}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"out_dir": str(out_dir), "files": sorted(files) + ["manifest.json"]}


def run(project: dict, project_path=None) -> dict:
    result, depends = evaluate(project)
    d = project["inputs"].get("m26", {})
    if d.get("out_dir") or project_path:
        out_dir = Path(d.get("out_dir", Path("loads") / project["name"].replace(" ", "_")))
        result["export"] = _write_files(result, out_dir, project, project_path)
    prj.record(project, "m26", result, "conceptual", REFERENCES, depends)
    return result
