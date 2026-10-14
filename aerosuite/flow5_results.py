"""M-F5R — reader for the result files written by the ORIGINAL flow5 v7.57.

The formats are taken from the flow5 source that writes them (vendor/flow5, tag v7.57):

* plane polars: ``io::exportAllWPolars`` (flow5-io-lib/io/flow5-io.cpp) writes
  ``<output>/<plane>/<polar>.csv|.txt`` = ``PlanePolar::getProperties`` (free text)
  followed by ``PlanePolar::exportToString`` (flow5-lib/objects3d/analysis3d/planepolar.cpp):
  plane name, polar name, speed or alpha line, one header row with the 58
  ``PlanePolar::s_VariableNames`` and one row per operating point;
* operating points: ``io::exportAllPOpps`` writes ``<output>/<plane>/<polar>/<opp>.csv|.txt``
  with ``PlaneOpp::exportMainDataToString`` (planeopp.cpp): flight state, coefficients,
  centre of pressure / neutral point, mass and inertia, stability and control derivatives
  (polar types 1,2,3,5,7,8), flap moments and one span-distribution table per wing.

Rules of this reader
--------------------
* Columns are identified by their header text, never by position.
* flow5 writes values in the user's DISPLAY units (Units::mtoUnit, NtoUnit, ...);
  the unit is read from each header label and every value is converted to SI.
  Unknown units are kept as read and reported in ``unconverted``.
* CSV separator is detected (flow5 default ``,``; user-configurable), TXT uses
  two or more spaces. Empty fields (flow5 writes a trailing separator, and a
  double separator after ``ctrl`` in operating points) are ignored.
* Nothing is interpolated or invented. Derived quantities (drag-polar fit,
  lift slope, static margin) carry the data range and fit quality used.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json
import math
import re
from pathlib import Path

SCHEMA = "aerosuite-flow5-results"
SCHEMA_VERSION = 1

# --- display units -> SI factors (inverse of flow5 Units::*toUnit), flow5-lib/utils/units.cpp
LENGTH = {"mm": 1e-3, "cm": 1e-2, "dm": 1e-1, "m": 1.0, "in": 0.0254, "ft": 0.3048}
SPEED = {"m/s": 1.0, "km/h": 1000 / 3600, "ft/s": 0.3048, "kt": 0.514444, "mph": 1609.344 / 3600}
MASS = {"g": 1e-3, "kg": 1.0, "oz": 2.83495e-2, "lb": 0.45359237}
FORCE = {"N": 1.0, "kN": 1000.0, "ton": 1000.0 * 9.81, "lbf": 4.44822}
MOMENT = {"N.m": 1.0, "lbf.in": 4.44822 * 0.0254, "lbf.ft": 4.44822 * 12 * 0.0254}
INERTIA = {"kg.m²": 1.0, "lbm.ft²": 0.45359237 * 0.3048 ** 2}
UNIT_TABLES = {**LENGTH, **SPEED, **MASS, **FORCE, **MOMENT, **INERTIA, "W": 1.0, "Hz": 1.0, "°": 1.0, "%": 1.0}
SI_LABEL = {**{k: "m" for k in LENGTH}, **{k: "m/s" for k in SPEED}, **{k: "kg" for k in MASS},
            **{k: "N" for k in FORCE}, **{k: "N.m" for k in MOMENT}, **{k: "kg.m²" for k in INERTIA},
            "W": "W", "Hz": "Hz", "°": "deg", "%": "%"}

# --- canonical names for the PlanePolar variables (planepolar.cpp s_VariableNames)
POLAR_CANONICAL = {
    "ctrl": "ctrl", "α": "alpha_deg", "β": "beta_deg", "φ": "phi_deg",
    "cl": None,  # resolved case-sensitively below (CL vs Cl)
    "cd": "CD", "cd_viscous": "CD_viscous", "cd_induced": "CD_induced", "cy": "CY",
    "cm": "Cm", "cm_viscous": "Cm_viscous", "cm_pressure": "Cm_pressure",
    "cn": "Cn", "cn_viscous": "Cn_viscous", "cn_pressure": "Cn_pressure",
    "cl/cd": "CL_CD", "cl^(3/2)/cd": "CL32_CD", "1/sqrt(cl)": "inv_sqrt_CL",
    "lift": "lift_N", "drag": "drag_N",
    "fx_ff_wind": "Fx_FF_wind_N", "fy_ff_wind": "Fy_FF_wind_N", "fz_ff_wind": "Fz_FF_wind_N",
    "fx_sum_wind": "Fx_sum_wind_N", "fy_sum_wind": "Fy_sum_wind_N", "fz_sum_wind": "Fz_sum_wind_N",
    "extra drag": "extra_drag_N", "fuse drag": "fuse_drag_N", "cf_fuse": "Cf_fuse",
    "vx": "Vx_mps", "vz": "Vz_mps", "v": "V_mps", "gamma": "glide_angle_deg",
    "l": "L_roll_Nm", "m": "M_pitch_Nm", "n": "N_yaw_Nm",
    "cpx": "CPx_m", "cpy": "CPy_m", "cpz": "CPz_m", "bm": "root_bending_Nm",
    "m.g.vz": "mgVz_W", "drag x v": "dragV_W", "efficiency": "span_efficiency", "xcp.cl": "XCp_Cl",
    "xnp": "XNP_m", "phugoid freq.": "phugoid_freq_Hz", "phugoid damping": "phugoid_damping",
    "short period freq.": "short_period_freq_Hz", "short period damping ratio": "short_period_damping_ratio",
    "dutch roll freq.": "dutch_roll_freq_Hz", "dutch roll damping": "dutch_roll_damping",
    "roll damping": "roll_damping", "spiral damping": "spiral_damping",
    "mass": "mass_kg", "cog_x": "CoG_x_m", "cog_z": "CoG_z_m",
}
NUMBER = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$|^[-+]?(inf|nan)$", re.I)
LABEL_UNIT = re.compile(r"^(.*?)\s*\(([^()]*)\)\s*$")


def _is_number(token: str) -> bool:
    return bool(NUMBER.match(token.strip()))


def _split(line: str, sep: str | None) -> list[str]:
    parts = line.split(sep) if sep else re.split(r"\s{2,}|\t", line.strip())
    return [p.strip() for p in parts if p.strip() != ""]


def detect_separator(text: str) -> str | None:
    """Return the CSV separator, or None for flow5's space-aligned TXT format."""
    for line in text.splitlines():
        if line.lstrip().lower().startswith(("ctrl", "α", "y(")):
            for cand in (",", ";", "\t", "|"):
                if line.count(cand) >= 2:
                    return cand
            return None
    for cand in (",", ";", "\t"):
        if text.count(cand) > 10:
            return cand
    return None


def split_label(label: str) -> tuple[str, str | None]:
    """'Lift (N)' -> ('Lift', 'N'); 'CP.x(m)' -> ('CP.x', 'm'); 'α (°)' -> ('α', '°')."""
    m = LABEL_UNIT.match(label.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return label.strip(), None


def to_si(value: float, unit: str | None) -> tuple[float, str | None, bool]:
    if unit is None or unit not in UNIT_TABLES:
        return value, unit, unit is None
    return value * UNIT_TABLES[unit], SI_LABEL[unit], True


@dataclass
class Flow5Polar:
    path: str
    plane: str
    polar: str
    polar_type: str | None
    condition_line: str
    properties_text: str
    columns: list[dict]
    rows: list[dict]
    unconverted: list[str] = field(default_factory=list)
    schema: str = SCHEMA
    schema_version: int = SCHEMA_VERSION

    def column(self, key: str) -> list[float]:
        return [r[key] for r in self.rows if key in r and r[key] is not None]

    def to_dict(self) -> dict:
        return asdict(self)


def _canonical_polar(name: str) -> str:
    base = name.strip()
    if base == "CL":
        return "CL"
    if base == "Cl":
        return "Cl_roll"
    key = POLAR_CANONICAL.get(base.lower())
    return key if key else re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_")


def parse_plane_polar(path: Path) -> Flow5Polar:
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    sep = detect_separator(text)
    lines = text.splitlines()
    header_index = next((i for i, l in enumerate(lines) if _split(l, sep)[:1] == ["Ctrl"]), None)
    if header_index is None:
        raise ValueError(f"{path}: no flow5 plane-polar header row starting with 'Ctrl'")
    # exportToString writes: plane, polar, speed/alpha line, blank, header
    preface = [l.strip() for l in lines[:header_index] if l.strip()]
    # fixed-speed and fixed-aoa polars add a condition line; other types do not
    if preface and preface[-1].startswith(("Freestream speed", "Alpha =")):
        condition, polar, plane = preface[-1], preface[-2] if len(preface) > 1 else "", \
            preface[-3] if len(preface) > 2 else ""
    else:
        condition, polar, plane = "", preface[-1] if preface else "", preface[-2] if len(preface) > 1 else ""
    props = "\n".join(lines[:max(0, header_index - 4)])
    ptype = next((m.group(0) for m in re.finditer(r"Type \d+: [^\n]+", props)), None)
    labels = _split(lines[header_index], sep)
    columns, unconverted = [], []
    for label in labels:
        if label.strip().lower() in POLAR_CANONICAL:  # e.g. '1/sqrt(CL)': parentheses are not a unit
            name, unit = label.strip(), None
        else:
            name, unit = split_label(label)
        key = _canonical_polar(name)
        _, si_unit, ok = to_si(1.0, unit)
        if not ok:
            unconverted.append(label)
        columns.append({"label": label, "key": key, "unit_read": unit, "unit_si": si_unit})
    rows = []
    for line in lines[header_index + 1:]:
        fields = _split(line, sep)
        if not fields:
            continue
        if len(fields) != len(columns) or not all(_is_number(f) for f in fields):
            continue  # flow5 writes nothing else after the table; skip stray lines
        row = {}
        for col, raw in zip(columns, fields):
            value = float(raw)
            row[col["key"]] = to_si(value, col["unit_read"])[0] if col["unit_si"] else value
        rows.append(row)
    if not rows:
        raise ValueError(f"{path}: header found but no complete numeric data rows")
    return Flow5Polar(str(path), plane, polar, ptype, condition, props, columns, rows, unconverted)


# ------------------------------------------------------------------ operating points
@dataclass
class Flow5OperatingPoint:
    path: str
    plane: str
    polar: str
    scalars: dict
    derivatives: dict
    control_derivatives: dict
    flap_moments: dict
    span: dict
    unconverted: list[str] = field(default_factory=list)
    schema: str = SCHEMA
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


OPP_KEYS = {"α": "alpha_deg", "β": "beta_deg", "φ": "phi_deg", "ctrl": "ctrl", "VInf": "V_mps",
            "CL": "CL", "CX": "CD",  # planeopp.cpp writes AF.CD() under the header "CX"
            "CY": "CY", "CD_inviscid": "CD_induced", "CD_viscous": "CD_viscous",
            "Cl": "Cl_roll", "Cm_inviscid": "Cm_pressure", "Cm_viscous": "Cm_viscous",
            "Cn_inviscid": "Cn_pressure", "Cn_viscous": "Cn_viscous",
            "CP.x": "CPx_m", "CP.y": "CPy_m", "CP.z": "CPz_m", "NP.x": "XNP_m",
            "mass": "mass_kg", "CoG.x": "CoG_x_m", "CoG.y": "CoG_y_m", "CoG.z": "CoG_z_m",
            "CoG_Ixx": "Ixx_kgm2", "CoG_Iyy": "Iyy_kgm2", "CoG_Izz": "Izz_kgm2", "CoG_Ixz": "Ixz_kgm2"}
DERIVATIVES = {"CXu", "CZu", "Cmu", "CXa", "CZa", "Cma", "CXq", "CZq", "Cmq",
               "Cyb", "Clb", "Cnb", "Cyp", "Clp", "Cnp", "Cyr", "Clr", "Cnr"}
CONTROL = {"CXd", "CYd", "CZd", "Cld", "Cmd", "Cnd"}
SPAN_KEYS = {"y": "y_m", "Re": "Re", "Ai": "alpha_induced_deg", "Cd_i": "Cd_induced", "Cd_v": "Cd_viscous",
             "Cl": "Cl", "CP.x": "xcp_percent_chord", "Trans.top": "xtr_top", "Trans.bot": "xtr_bottom",
             "Cm_i": "Cm_induced", "Cm_v": "Cm_viscous", "Bending.mom": "bending_moment",
             "Vd.x": "Vd_x", "Vd.y": "Vd_y", "Vd.z": "Vd_z", "F.x": "F_x", "F.y": "F_y", "F.z": "F_z", "Γ": "gamma"}


def parse_plane_opp(path: Path) -> Flow5OperatingPoint:
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    sep = detect_separator(text)
    lines = text.splitlines()
    nonblank = [l for l in lines if l.strip()]
    plane = nonblank[0].strip() if nonblank else ""
    polar = nonblank[1].strip() if len(nonblank) > 1 else ""
    scalars, derivs, controls, flaps, span, unconverted = {}, {}, {}, {}, {}, []
    pending_control = None
    i = 0
    while i < len(lines):
        tokens = _split(lines[i], sep)
        if not tokens:
            i += 1
            continue
        names = [t for t in tokens if not _is_number(t)]
        values = [t for t in tokens if _is_number(t)]
        # span table: a single non-numeric line (wing name) followed by the 'y(...)' header
        if len(tokens) == 1 and not _is_number(tokens[0]) and i + 1 < len(lines) \
                and _split(lines[i + 1], sep)[:1] and _split(lines[i + 1], sep)[0].startswith("y("):
            wing = tokens[0]
            header = _split(lines[i + 1], sep)
            cols = []
            for label in header:
                name, unit = split_label(label)
                key = SPAN_KEYS.get(name, re.sub(r"[^A-Za-z0-9]+", "_", name))
                cols.append((key, unit))
            rows, j = [], i + 2
            while j < len(lines):
                f = _split(lines[j], sep)
                if not f or not all(_is_number(x) for x in f):
                    break
                row = {}
                for (key, unit), raw in zip(cols, f):
                    row[key] = to_si(float(raw), unit)[0] if unit in UNIT_TABLES else float(raw)
                rows.append(row)
                j += 1
            span[wing] = {"columns": [c[0] for c in cols], "rows": rows,
                          "note": "bending moment, Vd and F are written by flow5 without unit conversion"}
            i = j
            continue
        if len(tokens) == 1 and not _is_number(tokens[0]) and i + 1 < len(lines) \
                and set(_split(lines[i + 1], sep)) <= CONTROL | {""} and _split(lines[i + 1], sep):
            pending_control = tokens[0]
            i += 1
            continue
        if " - flap moments (" in lines[i]:
            wing, unit = lines[i].split(" - flap moments (")
            unit = unit.rstrip(")\n ")
            hdr = _split(lines[i + 1], sep) if i + 1 < len(lines) else []
            vals = _split(lines[i + 2], sep) if i + 2 < len(lines) else []
            flaps[wing.strip()] = {h: to_si(float(v), unit)[0] for h, v in zip(hdr, vals) if _is_number(v)}
            i += 3
            continue
        if names and values and len(names) == len(values):  # header and values on one line (mass block)
            pairs = list(zip(names, values))
            i += 1
        elif names and not values and i + 1 < len(lines):
            nxt = [t for t in _split(lines[i + 1], sep)]
            if nxt and all(_is_number(t) for t in nxt):
                pairs = list(zip(names, nxt))
                i += 2
            else:
                i += 1
                continue
        else:
            i += 1
            continue
        for label, raw in pairs:
            name, unit = split_label(label)
            value = float(raw)
            if name in DERIVATIVES:
                derivs[name] = value
            elif name in CONTROL and pending_control:
                controls.setdefault(pending_control, {})[name] = value
            else:
                si, _u, ok = to_si(value, unit)
                if not ok:
                    unconverted.append(label)
                scalars[OPP_KEYS.get(name, re.sub(r"[^A-Za-z0-9]+", "_", name))] = si
        if names and set(names) <= CONTROL:
            pending_control = None
    return Flow5OperatingPoint(str(path), plane, polar, scalars, derivs, controls, flaps, span, unconverted)


# ------------------------------------------------------------------ job scan
def collect(output_dir: Path) -> dict:
    """Read every polar and operating point that flow5 wrote under ``output_dir``."""
    output_dir = Path(output_dir)
    polars, opps, errors = [], [], []
    for plane_dir in sorted(p for p in output_dir.iterdir() if p.is_dir()) if output_dir.is_dir() else []:
        for f in sorted(plane_dir.glob("*")):
            if f.is_file() and f.suffix.lower() in (".csv", ".txt"):
                try:
                    polars.append(parse_plane_polar(f).to_dict())
                except ValueError as exc:
                    errors.append({"file": str(f), "error": str(exc)})
            elif f.is_dir():
                for g in sorted(f.glob("*")):
                    if g.suffix.lower() in (".csv", ".txt"):
                        try:
                            opps.append(parse_plane_opp(g).to_dict())
                        except (ValueError, IndexError) as exc:
                            errors.append({"file": str(g), "error": str(exc)})
    return {"schema": SCHEMA, "schema_version": SCHEMA_VERSION, "source": str(output_dir),
            "engine": "flow5 v7.57 (original executable)", "polars": polars,
            "operating_points": opps, "errors": errors}


# ------------------------------------------------------------------ derived quantities
def _lstsq(xs: list[float], ys: list[float], degree: int) -> tuple[list[float], float]:
    import numpy as np
    coef = np.polyfit(xs, ys, degree)
    pred = np.polyval(coef, xs)
    ss_res = float(((np.asarray(ys) - pred) ** 2).sum())
    ss_tot = float(((np.asarray(ys) - np.mean(ys)) ** 2).sum())
    return [float(c) for c in coef], (1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")


def fit_drag_polar(polar: Flow5Polar, cl_min: float | None = None, cl_max: float | None = None) -> dict:
    """Fit CD(CL) from flow5 points.

    simplified: CD = CD0 + k CL^2          (Gudmundsson Ch. 16, simplified drag model)
    adjusted:   CD = CDmin + k (CL - CL_minD)^2  (cambered wings; same chapter)
    Only points inside [cl_min, cl_max] are used; the range and R^2 are reported.
    VLM/panel CD is inviscid + interpolated viscous drag; the result is only as
    complete as the flow5 analysis (no fuselage friction unless enabled, no
    interference, no excrescence drag).
    """
    pts = [(r["CL"], r["CD"]) for r in polar.rows if "CL" in r and "CD" in r]
    if cl_min is not None:
        pts = [p for p in pts if p[0] >= cl_min]
    if cl_max is not None:
        pts = [p for p in pts if p[0] <= cl_max]
    if len(pts) < 4:
        raise ValueError("At least 4 points are needed to fit a drag polar")
    cl = [p[0] for p in pts]
    cd = [p[1] for p in pts]
    (a, b, c), r2_s = _lstsq(cl, cd, 2)
    simple_k, simple_cd0, r2_simple = _simplified(cl, cd)
    cl_mind = -b / (2 * a) if a else float("nan")
    cd_min = c - b * b / (4 * a) if a else float("nan")
    return {"model_simplified": {"CD0": simple_cd0, "k": simple_k, "R2": r2_simple},
            "model_adjusted": {"CDmin": cd_min, "k": a, "CL_minD": cl_mind, "R2": r2_s},
            "points_used": len(pts), "CL_range": [min(cl), max(cl)],
            "source": {"file": polar.path, "plane": polar.plane, "polar": polar.polar},
            "reference": "Gudmundsson, GA Aircraft Design 2nd ed., Ch. 16 (drag modelling)"}


def _simplified(cl: list[float], cd: list[float]) -> tuple[float, float, float]:
    import numpy as np
    x = np.asarray(cl) ** 2
    A = np.vstack([x, np.ones_like(x)]).T
    (k, cd0), *_ = np.linalg.lstsq(A, np.asarray(cd), rcond=None)
    pred = k * x + cd0
    ss_res = float(((np.asarray(cd) - pred) ** 2).sum())
    ss_tot = float(((np.asarray(cd) - np.mean(cd)) ** 2).sum())
    return float(k), float(cd0), (1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")


def lift_slope(polar: Flow5Polar, alpha_min: float = -2.0, alpha_max: float = 6.0) -> dict:
    pts = [(r["alpha_deg"], r["CL"]) for r in polar.rows
           if "alpha_deg" in r and "CL" in r and alpha_min <= r["alpha_deg"] <= alpha_max]
    if len(pts) < 3:
        raise ValueError("At least 3 points in the linear range are needed")
    (slope, cl0), r2 = _lstsq([p[0] for p in pts], [p[1] for p in pts], 1)
    return {"CL_alpha_per_deg": slope, "CL_alpha_per_rad": slope * 180 / math.pi,
            "alpha_zero_lift_deg": -cl0 / slope if slope else float("nan"), "R2": r2,
            "alpha_range_deg": [alpha_min, alpha_max], "points_used": len(pts)}


def static_margin(polar: Flow5Polar, mac_m: float, alpha_min: float = -2.0, alpha_max: float = 6.0) -> dict:
    """Two independent estimates, both from flow5 output:
    (a) -dCm/dCL from the polar (moment reference = CoG, as flow5 computes Cm about the CoG);
    (b) (XNP - CoG_x)/MAC using flow5's own neutral point column.
    MAC must be supplied (from the AeroSuite geometry), it is not in the polar file.
    """
    rows = [r for r in polar.rows if alpha_min <= r.get("alpha_deg", 1e9) <= alpha_max]
    out = {"alpha_range_deg": [alpha_min, alpha_max], "mac_m": mac_m,
           "reference": "Gudmundsson Ch. 24 (static longitudinal stability); Etkin Ch. 2"}
    if len(rows) >= 3 and all("Cm" in r and "CL" in r for r in rows):
        (dcm, _), r2 = _lstsq([r["CL"] for r in rows], [r["Cm"] for r in rows], 1)
        out["from_dCm_dCL"] = {"static_margin": -dcm, "R2": r2}
    xnp = [r["XNP_m"] - r["CoG_x_m"] for r in rows if "XNP_m" in r and "CoG_x_m" in r]
    if xnp and mac_m > 0:
        out["from_XNP"] = {"static_margin_mean": sum(xnp) / len(xnp) / mac_m,
                           "static_margin_min": min(xnp) / mac_m, "points": len(xnp)}
    return out


def export_json(data: dict, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    return destination
