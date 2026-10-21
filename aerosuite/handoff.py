"""T-1 Paquete de traspaso del diseno preliminar (Gudmundsson Tabla 1-4 paso 27).

Reune, sin copiar libros ni binarios de terceros, lo que sale de AeroSuite para el diseno detallado: project.json con trazabilidad, STEP de M24,
cargas de M26, pesos/CG/inercias (M12/M13), envolvente V-n (M25), informe de requisitos (M23), supuestos y modulos sin validacion, nota de
costos de 2012 (si hay costos), LEEME.md y manifiesto con versiones y SHA-256. No ejecuta modulos: solo empaqueta lo ya calculado y avisa de
lo que falta o esta desactualizado."""
from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import project as prj

SCHEMA = "aerosuite-handoff/1"
# Modulos sin validacion numerica contra un ejemplo resuelto del libro o un motor externo (PROJECT_STATE.md, DECISIONS.md D-24, D-27, D-29, D-49, D-55, D-56)
UNVALIDATED = {
    "m08": "Metodo 4 (perfil de fuselaje cuadratico) sin validacion contra el libro; V_HT y V_VT son valores historicos de partida (D-24)",
    "m10": "sin ejemplo del libro: solo invariantes geometricos independientes (D-27)",
    "m12": "solo las ecuaciones del ala (6-43 a 6-47) reproducen un ejemplo; las demas estan transcritas sin ejemplo resuelto (D-29)",
    "m24": "verificado con OpenCASCADE y por geometria; la apertura en SolidWorks y Ansys la confirma el usuario (D-49, D-54; VERIFICAR.md)",
    "m25": "validado con el Ejemplo 17.4.1; umbrales de categorias utilitaria/acrobatica y factores por carga alar de ADRpy 0.2.6, no del libro (D-55)",
    "m26": "sin ejemplo resuelto del libro; validado por equilibrio interno y contraste con flow5 solo cuando el C_L coincide (D-56)",
}
COST_NOTE_FALLBACK = "Costos en dolares de 2012 (tarifas por defecto de Gudmundsson, Cap. 2); no estan actualizados por inflacion."


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit(root: Path) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=float), encoding="utf-8")


def _result(project: dict, m: str):
    item = project["outputs"].get(m)
    return item["result"] if item else None


def build(project_path: Path, out: Path) -> dict:
    project_path, out = Path(project_path), Path(out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} already exists and is not empty; refusing to overwrite")
    project = prj.load(project_path)
    stale = prj.stale(project)
    included, missing, warnings = {}, [], []
    out.mkdir(parents=True, exist_ok=True)

    def put(rel: str, src: Path | None = None, obj=None, text: str | None = None) -> None:
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src is not None:
            shutil.copyfile(src, dest)
        elif obj is not None:
            _write_json(dest, obj)
        else:
            dest.write_text(text or "", encoding="utf-8")
        included[rel] = _sha(dest)

    put("project.json", src=project_path)
    # --- STEP de M24 ---
    m24 = _result(project, "m24")
    if m24:
        steps = [Path(p) for p in [m24.get("assembly_step"), *m24.get("component_steps", {}).values()] if p]
        found = [p for p in steps if p.is_file()]
        for p in found:
            put(f"cad/{p.name}", src=p)
        mf = Path(m24["out_dir"]) / "manifest.json"
        if mf.is_file():
            put("cad/manifest_m24.json", src=mf)
        if len(found) != len(steps):
            warnings.append("M24: algunos archivos STEP referenciados ya no existen; vuelve a ejecutar m24")
        if not found:
            missing.append("STEP de M24 (archivos no encontrados)")
    else:
        missing.append("STEP de M24 (falta outputs.m24)")
    # --- cargas de M26 ---
    m26 = _result(project, "m26")
    if m26 and m26.get("export"):
        base = Path(m26["export"]["out_dir"])
        for name in m26["export"]["files"]:
            if (base / name).is_file():
                put(f"cargas/{name}", src=base / name)
            else:
                warnings.append(f"M26: no existe {base / name}")
    elif m26:
        put("cargas/m26.json", obj=m26)
    else:
        missing.append("cargas de M26 (falta outputs.m26)")
    # --- pesos, CG e inercias ---
    m12, m13 = _result(project, "m12"), _result(project, "m13")
    if m12 or m13:
        put("masas/pesos_cg_inercias.json", obj={"m12": m12, "m13": m13, "nota": "M13 describe el avion vacio mas las combinaciones de carga de loading_cloud"})
    else:
        missing.append("pesos, CG e inercias (faltan outputs.m12 y m13)")
    # --- envolvente V-n ---
    m25 = _result(project, "m25")
    if m25:
        put("envolvente/envolvente_vn.json", obj=m25)
    else:
        missing.append("envolvente V-n (falta outputs.m25)")
    # --- M23 ---
    m23 = _result(project, "m23")
    if m23:
        put("requisitos/informe_m23.json", obj=m23)
        lines = ["# Informe de requisitos (M23)", "", f"Resultado global: **{m23['overall']}**  ", f"Recuento: {m23['counts']}", "",
                 "| Requisito | Estado | Valor | Limite | Referencia |", "|---|---|---|---|---|"]
        for i in m23["items"]:
            lines.append(f"| {i['requirement']} | {i['status']} | {i.get('value', '')} | {i.get('limit', '')} | {i['reference']} |")
        lines += ["", "Los `no evaluable` no equivalen a cumplir; su razon esta en el JSON.", ""]
        put("requisitos/informe_m23.md", text="\n".join(lines))
    else:
        missing.append("informe de requisitos (falta outputs.m23)")
    # --- supuestos y modulos sin validacion ---
    sup = ["# Supuestos y modulos sin validacion", "", "## Datos supuestos del proyecto (`assumptions`)", ""]
    sup += [f"- [{a.get('module')}] {a.get('key')} = {a.get('value')} - {a.get('reason')}" for a in project.get("assumptions", [])] or ["- (ninguno registrado)"]
    sup += ["", "## Supuestos declarados por cada modulo", ""]
    for m, item in sorted(project["outputs"].items()):
        for a in (item["result"].get("assumptions") or []) if isinstance(item["result"], dict) else []:
            sup.append(f"- [{m}] {a if isinstance(a, str) else json.dumps(a, ensure_ascii=False)}")
    sup += ["", "## Modulos presentes sin validacion completa", ""]
    present = [m for m in UNVALIDATED if m in project["outputs"]]
    sup += [f"- **{m.upper()}**: {UNVALIDATED[m]}" for m in present] or ["- (ninguno de los modulos listados esta en el proyecto)"]
    sup += ["", "## Niveles", "", "Todos los resultados son de nivel conceptual salvo los que declaren 2D (XFOIL) o 3D (flow5) en su registro de ejecucion; "
            "ninguno es estructural, FEA ni CFD.", ""]
    put("SUPUESTOS.md", text="\n".join(sup))
    # --- costos ---
    m03 = _result(project, "m03")
    if m03:
        put("costos/nota_costos.txt", text=m03.get("nota_costos") or COST_NOTE_FALLBACK)
        put("costos/m03.json", obj=m03)
    # --- LEEME y manifiesto ---
    root = Path(__file__).resolve().parents[1]
    names = ["project.json"] + [k for k in included if k != "project.json"]
    leeme = ["# Paquete de traspaso del diseno preliminar - " + project["name"], "",
             f"Generado por AeroSuite el {datetime.now(timezone.utc).isoformat(timespec='seconds')}. Nivel conceptual (Gudmundsson, paso 27 de la Tabla 1-4).", "",
             "## Contenido", ""]
    for rel in names:
        leeme.append(f"- `{rel}`")
    leeme += ["", "## Como usarlo", "",
              "- `cad/*.step`: geometria exterior (M24), en **milimetros**, ejes de SolidWorks: X hacia atras, Y arriba, Z a lo largo de la envergadura.",
              "- `cargas/`: cargas aerodinamicas externas (M26) en los puntos de esquina del diagrama V-n; mismas coordenadas que el STEP (columnas `cad_*_mm`); "
              "fuerzas en N, SI. Se aplican como cargas puntuales por estacion (o distribuidas con `force_per_span_n_per_m`). Son solo aerodinamicas: no hay estructura ni alivio de masa.",
              "- `masas/`: pesos, CG e inercias (M12/M13), SI.",
              "- `envolvente/`: envolvente V-n (M25); velocidades en m/s EAS (tambien KEAS).",
              "- `requisitos/`: verificacion de requisitos (M23).",
              "- `SUPUESTOS.md`: supuestos y modulos sin validacion completa. Leelo antes de usar cualquier cifra.",
              "- `manifest.json`: versiones y SHA-256 de cada archivo."]
    if m03:
        leeme += ["", "## Nota sobre costos", "", m03.get("nota_costos") or COST_NOTE_FALLBACK]
    if missing or warnings or stale:
        leeme += ["", "## Avisos", ""]
        leeme += [f"- Falta: {m}" for m in missing] + [f"- {w}" for w in warnings]
        if stale:
            leeme += [f"- Modulos desactualizados respecto a sus entradas (vuelve a ejecutarlos antes de usar el paquete): {', '.join(sorted(stale))}"]
    leeme += ["", "No se incluyen libros ni binarios de terceros.", ""]
    put("LEEME.md", text="\n".join(leeme))
    versions = {"python": platform.python_version(), "numpy": np.__version__, "aerosuite_commit": _git_commit(root)}
    try:
        import cadquery
        versions["cadquery"] = cadquery.__version__
    except ImportError:
        pass
    manifest = {"schema": SCHEMA, "project": project["name"], "created": datetime.now(timezone.utc).isoformat(timespec="seconds"), "versions": versions,
                "source_project": str(project_path), "source_project_sha256": _sha(project_path), "stale_modules": sorted(stale), "missing": missing,
                "warnings": warnings, "modules_in_project": sorted(project["outputs"]), "files_sha256": dict(sorted(included.items()))}
    _write_json(out / "manifest.json", manifest)
    return manifest
