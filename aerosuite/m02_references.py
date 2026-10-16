"""M02 Base de referencia y regresiones (Gudmundsson Tabla 1-4 paso 2; Sec. 6.2.1, Tabla 6-1).

Nivel conceptual. Calcula razones de peso (We/W0, Wu/W0, Wf/W0) y su estadística sobre una base de aeronaves
similares, y ajusta We/W0 = A + B ln W0 por mínimos cuadrados (forma de las Ecs. 6-16 a 6-24) cuando la base
tiene pesos brutos distintos. La selección de las aeronaves es una decisión del diseñador (el libro exige no
mezclar clases): M02 rechaza bases que mezclan `class` o `propulsion`.
"""
import json
from pathlib import Path

import numpy as np

from . import project as prj

KG_PER_LBF = 0.45359237
MIN_LN_SPREAD = 0.095  # ln(1.10): a fit over a narrower W0 range is dominated by rounding of the data
DATA_DIR = Path(__file__).parent / "data"
REFERENCES = ["GUD Sec. 6.2.1 Method 1 y Tabla 6-1, PDF 195-196 / impr. 150-151",
              "GUD Sec. 6.2.2 forma We/W0 = A + B ln W0 (Ecs. 6-16 a 6-24), PDF 197-198 / impr. 152-153"]


def load_database(spec) -> dict:
    """spec: nombre de un archivo en aerosuite/data (sin .json), ruta a un JSON, o un dict ya cargado."""
    if isinstance(spec, dict):
        return spec
    path = Path(spec)
    if not path.exists():
        path = DATA_DIR / f"{spec}.json"
    if not path.exists():
        raise SystemExit(f"reference database not found: {spec}")
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(db: dict) -> list[dict]:
    classes = {a.get("class", db.get("class")) for a in db["aircraft"]}
    engines = {a.get("propulsion", db.get("propulsion")) for a in db["aircraft"]}
    if len(classes) > 1 or len(engines) > 1:
        raise ValueError(f"database mixes classes {sorted(map(str, classes))} or propulsion "
                         f"{sorted(map(str, engines))} (Gudmundsson Sec. 6.2.1 guidance)")
    rows = []
    for a in db["aircraft"]:
        we, w0 = a["we_lbf"] * KG_PER_LBF, a["w0_lbf"] * KG_PER_LBF
        wf = a["wf_lbf"] * KG_PER_LBF
        rows.append({"name": a["name"], "we_kg": we, "w0_kg": w0, "wf_kg": wf,
                     "we_w0": a["we_lbf"] / a["w0_lbf"], "wu_w0": 1.0 - a["we_lbf"] / a["w0_lbf"],
                     "wf_w0": a["wf_lbf"] / a["w0_lbf"]})
    return rows


def regression(w0_kg, ratio) -> dict:
    """Least squares of ratio = A + B ln(W0). Reports kg and lbf forms (A_lbf = A_kg + B ln(kg/lbf))."""
    x, y = np.log(np.asarray(w0_kg, float)), np.asarray(ratio, float)
    if len(x) < 3 or np.ptp(x) < MIN_LN_SPREAD:
        return {"status": "degenerate", "reason": "need >= 3 aircraft whose gross weights differ by >= 10 %", "n": int(len(x))}
    b, a = np.polyfit(x, y, 1)
    resid = y - (a + b * x)
    r2 = 1.0 - float(resid @ resid) / float(((y - y.mean()) ** 2).sum())
    return {"status": "ok", "n": int(len(x)), "A_kg": float(a), "B": float(b), "A_lbf": float(a + b * np.log(KG_PER_LBF)),
            "r2": r2, "rms_residual": float(np.sqrt(np.mean(resid ** 2)))}


def analyze(db: dict) -> dict:
    rows = _rows(db)
    out = {"database": db.get("name"), "source": db.get("source"), "n": len(rows), "aircraft": rows}
    for key in ("we_w0", "wu_w0", "wf_w0"):
        v = np.array([r[key] for r in rows])
        out[key] = {"mean": float(v.mean()), "std": float(v.std(ddof=1)) if len(v) > 1 else None,
                    "min": float(v.min()), "max": float(v.max())}
    out["regression_we_w0"] = regression([r["w0_kg"] for r in rows], [r["we_w0"] for r in rows])
    out["suggested_for_m06"] = {"we_w0": out["we_w0"]["mean"], "wf_w0": out["wf_w0"]["mean"],
                                "basis": "mean of the database (Method 1); review Wf/W0 against full-seat payload (GUD Note 2)"}
    return out


def run(project: dict) -> dict:
    d = prj.need_inputs(project, "m02", ["database"])
    result = analyze(load_database(d["database"]))
    prj.record(project, "m02", result, "conceptual", REFERENCES)
    return result
