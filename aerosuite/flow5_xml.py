"""Exchange files for the ORIGINAL flow5 v7.57 executable (no flow5 code is modified or linked).

AeroSuite writes the input formats that flow5 itself reads:

* foil .dat files (Selig format, first line = foil name);
* plane definition XML (<xflplane>), structure copied from
  vendor/flow5/API_examples/PlaneRun4/xml/plane.xml;
* plane analysis (polar) XML (<xflPlanePolar>), structure copied from the
  PlaneRun4 polar example and flow5-io-lib/xml/xplane/xmlplanepolarwriter.cpp;
* batch script XML (<xflscript>), read by flow5-app/modules/script/xflscriptreader.cpp
  and executed with ``flow5 -s script.xml``.

The aerodynamic analysis (LLT, VLM1, VLM2, panels, viscous interpolation with XFoil
on the fly, stability derivatives) is entirely performed by flow5.

Input (JSON, SI units):
{
  "name": "...",
  "wings": [{"name": "Main wing", "type": "MAINWING", "position_m": [x, y, z],
             "tilt_deg": 0, "symmetric": true,
             "sections": [{"y_m": 0, "chord_m": 1.5, "xoffset_m": 0, "dihedral_deg": 0,
                           "twist_deg": 0, "foil": "NACA 2412", "nx": 13, "ny": 15}]}],
  "fuselage": {"name": "Fuselage", "position_m": [0, 0, 0], "x_panels": 19, "hoop_panels": 7, "mass_kg": 0,
               "stations": [{"x_m": -1.0, "width_m": 0, "height_m": 0, "zc_m": 0},
                            {"x_m": 0.5, "width_m": 1.1, "height_m": 1.3, "zc_m": 0}]},
  "point_masses": [{"tag": "...", "mass_kg": 600, "x_m": 0.4, "y_m": 0, "z_m": 0}],
  "analysis": {"method": "VLM2", "type": "FIXEDSPEEDPOLAR", "velocity_mps": 50,
               "altitude_m": 0, "viscous": true, "xfoil_on_the_fly": true,
               "ncrit": 9, "alpha_deg": [-4, 12, 1], "stability_derivatives": true}
}
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from xml.sax.saxutils import escape

from .airfoils import naca4

METHODS = ("LLT", "VLM1", "VLM2", "QUADS", "TRIUNIFORM", "TRILINEAR")
POLAR_TYPES = ("FIXEDSPEEDPOLAR", "FIXEDLIFTPOLAR", "GLIDEPOLAR", "CONTROLPOLAR", "STABILITYPOLAR", "T8POLAR")
WING_TYPES = ("MAINWING", "SECONDWING", "ELEVATOR", "FIN", "OTHERWING")
NACA_NAME = re.compile(r"^NACA\s?(\d{4})$", re.I)
UNITS_SI = """    <Units>
        <length_unit_to_meter>1</length_unit_to_meter>
        <area_unit_to_m2>1</area_unit_to_m2>
        <mass_unit_to_kg>1</mass_unit_to_kg>
        <speed_unit_to_ms>1</speed_unit_to_ms>
        <inertia_unit_to_kgm2>1</inertia_unit_to_kgm2>
    </Units>
"""


def _f(v: float) -> str:
    return f"{float(v):.6g}"


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") or "item"


def validate(cfg: dict) -> None:
    if not cfg.get("name"):
        raise ValueError("Plane requires a name")
    wings = cfg.get("wings") or []
    if not wings or wings[0].get("type", "MAINWING") != "MAINWING":
        raise ValueError("The first wing must be the MAINWING")
    for w in wings:
        if w.get("type", "MAINWING") not in WING_TYPES:
            raise ValueError(f"Wing type must be one of {WING_TYPES}")
        secs = w.get("sections") or []
        if len(secs) < 2:
            raise ValueError(f"Wing {w.get('name')} needs at least two sections")
        ys = [float(s["y_m"]) for s in secs]
        if ys != sorted(ys) or any(float(s["chord_m"]) <= 0 for s in secs):
            raise ValueError(f"Wing {w.get('name')}: y must be increasing and chords positive")
    a = cfg.get("analysis", {})
    if a.get("method", "VLM2") not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    if a.get("type", "FIXEDSPEEDPOLAR") not in POLAR_TYPES:
        raise ValueError(f"type must be one of {POLAR_TYPES}")
    if a.get("type", "FIXEDSPEEDPOLAR") == "FIXEDSPEEDPOLAR" and not float(a.get("velocity_mps", 0)) > 0:
        raise ValueError("FIXEDSPEEDPOLAR requires velocity_mps > 0")


def foil_names(cfg: dict) -> list[str]:
    names = []
    for w in cfg["wings"]:
        for s in w["sections"]:
            if s["foil"] not in names:
                names.append(s["foil"])
    return names


def write_foil(name: str, folder: Path, points: int = 81) -> Path:
    """Only NACA 4-digit foils are generated here; other foils must be supplied as .dat files."""
    match = NACA_NAME.match(name.strip())
    if not match:
        raise ValueError(f"Foil {name!r}: only 'NACA xxxx' is generated; place {name}.dat in the foils folder")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (_safe(name) + ".dat")
    lines = [name] + [f"{x:.7f} {y:.7f}" for x, y in naca4(match.group(1), points)]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return path


def fuselage_xml(fus: dict) -> list[str]:
    """<body> element (NURBS type, as written by flow5's XflXmlWriter and read by XflXmlReader::readFuseXfl).

    Each station is an ellipse (width_m x height_m, centre at zc_m) described, as flow5 does, by the five points
    of the +y half-section from the top (y = 0) to the bottom (y = 0); width 0 and height 0 give a point (nose/tail tip).
    """
    st = fus["stations"]
    if len(st) < 2 or [float(s["x_m"]) for s in st] != sorted(float(s["x_m"]) for s in st):
        raise ValueError("fuselage needs at least two stations with increasing x_m")
    pos = fus.get("position_m", [0, 0, 0])
    out = ["        <body>", f"            <Name>{escape(fus.get('name', 'Fuselage'))}</Name>",
           f"            <Position>{_f(pos[0])}, {_f(pos[1])}, {_f(pos[2])}</Position>",
           "            <Type>NURBS</Type>",
           f"            <x_panels>{int(fus.get('x_panels', 19))}</x_panels>",
           f"            <hoop_panels>{int(fus.get('hoop_panels', 7))}</hoop_panels>",
           "            <Inertia>", f"                <Volume_Mass>{_f(fus.get('mass_kg', 0))}</Volume_Mass>", "            </Inertia>",
           "            <NURBS>", "                <u_degree>3</u_degree>", "                <v_degree>3</v_degree>",
           "                <uAxis>0</uAxis>", "                <vAxis>2</vAxis>",
           "                <uEdgeWeight>1</uEdgeWeight>", "                <vEdgeWeight>1</vEdgeWeight>",
           "                <Bunch_amplitude>0</Bunch_amplitude>", "                <Bunch_distribution>0.5</Bunch_distribution>"]
    for s in st:
        x, a, c = float(s["x_m"]), 0.5 * float(s["width_m"]), float(s.get("zc_m", 0))
        h = 0.5 * float(s["height_m"])
        out += ["                <frame>", "                    <Angle>0</Angle>", "                    <x_panels>1</x_panels>",
                f"                    <Position>{_f(x)}, 0, 0</Position>"]
        for ang in (90, 45, 0, -45, -90):
            t = math.radians(ang)
            out.append(f"                    <point>{_f(x)}, {_f(a * math.cos(t))}, {_f(c + h * math.sin(t))}</point>")
        out.append("                </frame>")
    out += ["            </NURBS>", "        </body>"]
    return out


def plane_xml(cfg: dict) -> str:
    out = ['<?xml version="1.0" encoding="UTF-8"?>', "<!DOCTYPE flow5>", '<xflplane version="1.0">', UNITS_SI.rstrip("\n"),
           "    <Plane>", f"        <Name>{escape(cfg['name'])}</Name>"]
    masses = cfg.get("point_masses") or []
    if masses:
        out.append("        <Inertia>")
        for m in masses:
            out += ["            <Point_Mass>", f"                <Tag>{escape(m.get('tag', 'mass'))}</Tag>",
                    f"                <Mass>{_f(m['mass_kg'])}</Mass>",
                    f"                <coordinates>{_f(m.get('x_m', 0))}, {_f(m.get('y_m', 0))}, {_f(m.get('z_m', 0))}</coordinates>",
                    "            </Point_Mass>"]
        out.append("        </Inertia>")
    if cfg.get("fuselage"):
        out += fuselage_xml(cfg["fuselage"])
    for w in cfg["wings"]:
        pos = w.get("position_m", [0, 0, 0])
        out += ["        <wing>", f"            <Name>{escape(w.get('name', 'Wing'))}</Name>",
                f"            <Type>{w.get('type', 'MAINWING')}</Type>",
                f"            <Position>{_f(pos[0])}, {_f(pos[1])}, {_f(pos[2])}</Position>",
                f"            <Tip_Strips>{int(w.get('tip_strips', 1))}</Tip_Strips>",
                f"            <Rx_angle>{_f(w.get('rx_deg', 0))}</Rx_angle>",
                f"            <Ry_angle>{_f(w.get('tilt_deg', 0))}</Ry_angle>",
                f"            <symmetric>{str(bool(w.get('symmetric', True))).lower()}</symmetric>",
                f"            <Two_Sided>{str(bool(w.get('two_sided', True))).lower()}</Two_Sided>",
                "            <Inertia>", f"                <Mass>{_f(w.get('mass_kg', 0))}</Mass>", "            </Inertia>",
                "            <Sections>"]
        for s in w["sections"]:
            out += ["                <Section>",
                    f"                    <y_position>{_f(s['y_m'])}</y_position>",
                    f"                    <Chord>{_f(s['chord_m'])}</Chord>",
                    f"                    <xOffset>{_f(s.get('xoffset_m', 0))}</xOffset>",
                    f"                    <Dihedral>{_f(s.get('dihedral_deg', 0))}</Dihedral>",
                    f"                    <Twist>{_f(s.get('twist_deg', 0))}</Twist>",
                    f"                    <x_number_of_panels>{int(s.get('nx', 13))}</x_number_of_panels>",
                    f"                    <x_panel_distribution>{s.get('x_distribution', 'COSINE')}</x_panel_distribution>",
                    f"                    <y_number_of_panels>{int(s.get('ny', 13))}</y_number_of_panels>",
                    f"                    <y_panel_distribution>{s.get('y_distribution', 'UNIFORM')}</y_panel_distribution>",
                    f"                    <Left_Side_FoilName>{escape(s['foil'])}</Left_Side_FoilName>",
                    f"                    <Right_Side_FoilName>{escape(s['foil'])}</Right_Side_FoilName>",
                    "                </Section>"]
        out += ["            </Sections>", "        </wing>"]
    out += ["    </Plane>", "</xflplane>", ""]
    return "\n".join(out)


def main_wing_reference(cfg: dict) -> dict:
    """Area, span and MAC (m) of the main wing from its trapezoidal panels (both semi-spans).

    flow5 7.55 in batch mode leaves the PLANFORM reference at zero and aborts (V-F5, D-35), so the reference
    dimensions are written explicitly as CUSTOM.
    """
    wing = next(w for w in cfg["wings"] if w.get("type", "MAINWING") == "MAINWING")
    secs = wing["sections"]
    area = mac_num = 0.0
    for a, b in zip(secs[:-1], secs[1:]):
        dy = float(b["y_m"]) - float(a["y_m"])
        c1, c2 = float(a["chord_m"]), float(b["chord_m"])
        area += 0.5 * (c1 + c2) * dy
        mac_num += dy * (c1 * c1 + c1 * c2 + c2 * c2) / 3.0
    sym = bool(wing.get("symmetric", True))
    f = 2.0 if sym else 1.0
    return {"area_m2": f * area, "span_m": f * (float(secs[-1]["y_m"]) - float(secs[0]["y_m"])),
            "mac_m": mac_num / area}


def polar_xml(cfg: dict, density: float, viscosity: float) -> tuple[str, str]:
    a = cfg.get("analysis", {})
    method, ptype = a.get("method", "VLM2"), a.get("type", "FIXEDSPEEDPOLAR")
    ref = {**main_wing_reference(cfg), **a.get("reference_dims", {})}
    name = a.get("name") or f"{ptype}-{method}-{_f(a.get('velocity_mps', 0))}mps"
    out = ['<?xml version="1.0" encoding="UTF-8"?>', "<!DOCTYPE flow5>", '<xflPlanePolar version="1.0">', UNITS_SI.rstrip("\n"),
           "    <Polar>", f"        <Polar_Name>{escape(name)}</Polar_Name>",
           f"        <Plane_Name>{escape(cfg['name'])}</Plane_Name>",
           f"        <Type>{ptype}</Type>", f"        <Method>{method}</Method>",
           f"        <Include_Fuse_Moments>false</Include_Fuse_Moments>",
           f"        <Thin_Surfaces>{str(bool(a.get('thin_surfaces', True))).lower()}</Thin_Surfaces>",
           f"        <Ground_Effect>{str(bool(a.get('ground_effect', False))).lower()}</Ground_Effect>",
           f"        <Ground_Height>{_f(a.get('ground_height_m', 0))}</Ground_Height>",
           "        <Wake>", "            <FlatPanelWake>true</FlatPanelWake>",
           f"            <NX>{int(a.get('wake_nx', 5))}</NX>",
           f"            <ProgressionFactor>{_f(a.get('wake_progression', 1.1))}</ProgressionFactor>",
           f"            <LengthFactor>{_f(a.get('wake_length_mac', 30))}</LengthFactor>", "        </Wake>",
           "        <Reference_Dimensions>",
           "            <Reference_Dimensions>CUSTOM</Reference_Dimensions>",
           f"            <Reference_Area>{_f(ref['area_m2'])}</Reference_Area>",
           f"            <Reference_Span_Length>{_f(ref['span_m'])}</Reference_Span_Length>",
           f"            <Reference_Chord_Length>{_f(ref['mac_m'])}</Reference_Chord_Length>",
           "        </Reference_Dimensions>",
           "        <Fluid>", f"            <Viscosity>{viscosity:.6e}</Viscosity>",
           f"            <Density>{density:.6f}</Density>", "        </Fluid>",
           "        <Viscous_Analysis>",
           f"            <Is_Viscous_Analysis>{str(bool(a.get('viscous', True))).lower()}</Is_Viscous_Analysis>",
           f"            <XFoil_OnTheFly>{str(bool(a.get('xfoil_on_the_fly', True))).lower()}</XFoil_OnTheFly>",
           "            <From_CL>false</From_CL>",
           f"            <NCrit>{_f(a.get('ncrit', 9))}</NCrit>",
           f"            <XTrTop>{_f(a.get('xtr_top', 1))}</XTrTop>",
           f"            <XTrBot>{_f(a.get('xtr_bottom', 1))}</XTrBot>",
           "        </Viscous_Analysis>",
           "        <Use_plane_inertia>true</Use_plane_inertia>",
           f"        <Fixed_Velocity>{_f(a.get('velocity_mps', 0))}</Fixed_Velocity>",
           "    </Polar>", "</xflPlanePolar>", ""]
    return name, "\n".join(out)


def script_xml(job_dir: Path, foils: list[Path], plane: Path, polar: Path, cfg: dict) -> str:
    a = cfg.get("analysis", {})
    alpha = a.get("alpha_deg", [-4, 12, 1])
    out = ['<?xml version="1.0" encoding="UTF-8"?>', "<!DOCTYPE flow5>", '<xflscript version="1.0">',
           "    <Metadata>", "        <make_project_file>true</make_project_file>",
           f"        <project_file_name>{escape(_safe(cfg['name']))}.fl5</project_file_name>",
           "        <polar_text_output_format>csv</polar_text_output_format>",
           "        <Directories>", f"            <output_dir>{escape(str(job_dir / 'output'))}</output_dir>",
           "            <recursive_scan>false</recursive_scan>", "        </Directories>",
           "        <MultiThreading>", "            <Allow_Multithreading>true</Allow_Multithreading>",
           f"            <max_threads>{int(a.get('max_threads', 4))}</max_threads>", "        </MultiThreading>",
           "    </Metadata>", "    <Plane_analysis>", "        <Foil_Dat_Files>"]
    out += [f"            <Foil_File_Name>{escape(str(p))}</Foil_File_Name>" for p in foils]
    out += ["        </Foil_Dat_Files>", "        <Plane_Definition_Files>",
            f"            <Plane_File_Name>{escape(str(plane))}</Plane_File_Name>", "        </Plane_Definition_Files>",
            "        <Plane_Analysis_Files>", f"            <Analysis_File_Name>{escape(str(polar))}</Analysis_File_Name>",
            "        </Plane_Analysis_Files>", "        <Plane_Analysis_Data>",
            f"            <Alpha>{_f(alpha[0])}, {_f(alpha[1])}, {_f(alpha[2])}</Alpha>",
            "        </Plane_Analysis_Data>", "        <Plane_Analysis_Output>",
            "            <make_polars_text_file>true</make_polars_text_file>",
            f"            <make_oppoints>{str(bool(a.get('oppoints', False))).lower()}</make_oppoints>",
            f"            <make_oppoints_text_file>{str(bool(a.get('oppoints', False))).lower()}</make_oppoints_text_file>",
            f"            <Compute_derivatives>{str(bool(a.get('stability_derivatives', False))).lower()}</Compute_derivatives>",
            "        </Plane_Analysis_Output>", "    </Plane_analysis>", "</xflscript>", ""]
    return "\n".join(out)


def export(cfg_path: Path, job_dir: Path) -> dict:
    cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
    validate(cfg)
    job_dir = job_dir.resolve()
    if (job_dir / "script.xml").exists():
        raise FileExistsError(f"Refusing to overwrite an existing flow5 job: {job_dir}")
    from .adrpy_core import atmosphere_table
    a = cfg.get("analysis", {})
    atm = atmosphere_table([float(a.get("altitude_m", 0))], float(a.get("isa_offset_deg", 0)))["rows"][0]
    foils_dir = job_dir / "foils"
    foils = []
    for name in foil_names(cfg):
        supplied = foils_dir / (_safe(name) + ".dat")
        foils.append(supplied if supplied.is_file() else write_foil(name, foils_dir))
    (job_dir / "planes").mkdir(parents=True, exist_ok=True)
    (job_dir / "analyses").mkdir(parents=True, exist_ok=True)
    plane = job_dir / "planes" / (_safe(cfg["name"]) + ".xml")
    plane.write_text(plane_xml(cfg), encoding="utf-8")
    polar_name, text = polar_xml(cfg, atm["density_kgm3"], atm["dynamic_viscosity_pas"] / atm["density_kgm3"])
    polar = job_dir / "analyses" / (_safe(polar_name) + ".xml")
    polar.write_text(text, encoding="utf-8")
    script = job_dir / "script.xml"
    script.write_text(script_xml(job_dir, foils, plane, polar, cfg), encoding="utf-8")
    manifest = {"engine": "flow5 v7.57 (official executable, batch script mode)",
                "input_config": str(Path(cfg_path).resolve()), "plane_xml": str(plane), "polar_xml": str(polar),
                "polar_name": polar_name, "foil_files": [str(p) for p in foils], "script_xml": str(script),
                "fluid": {"density_kgm3": atm["density_kgm3"],
                          "kinematic_viscosity_m2s": atm["dynamic_viscosity_pas"] / atm["density_kgm3"],
                          "source": "ADRpy ISA + Sutherland (AeroSuite)"},
                "run_command": f'flow5.exe -s "{script}" -p',
                "status": "EXPORTED (not yet executed)"}
    (job_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def run(job_dir: Path, exe: Path, timeout: int = 1800) -> dict:
    """Execute the official flow5 in script mode and list every output it produced."""
    import subprocess
    import time
    job_dir = job_dir.resolve()
    script = job_dir / "script.xml"
    if not script.is_file():
        raise FileNotFoundError(f"No script.xml in {job_dir}; run flow5-export first")
    before = {p for p in (job_dir / "output").rglob("*")} if (job_dir / "output").exists() else set()
    started = time.time()
    proc = subprocess.run([str(exe), "-s", str(script), "-p"], cwd=str(exe.parent), capture_output=True,
                          text=True, timeout=timeout, errors="replace")
    (job_dir / "flow5_stdout.log").write_text((proc.stdout or "") + "\n--- stderr ---\n" + (proc.stderr or ""),
                                              encoding="utf-8")
    produced = sorted(str(p) for p in (job_dir / "output").rglob("*") if p.is_file() and p not in before) \
        if (job_dir / "output").exists() else []
    from .flow5_results import collect, export_json
    results = collect(job_dir / "output")
    export_json(results, job_dir / "flow5_results.json")
    manifest = json.loads((job_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest["parsed_results"] = {"file": str(job_dir / "flow5_results.json"),
                                  "polars": len(results["polars"]),
                                  "operating_points": len(results["operating_points"]),
                                  "parse_errors": results["errors"]}
    manifest.update({"status": "EXECUTED" if proc.returncode == 0 else f"FAILED (return code {proc.returncode})",
                     "flow5_executable": str(exe), "return_code": proc.returncode,
                     "duration_s": round(time.time() - started, 2), "outputs": produced,
                     "results_verified": False,
                     "note": "Outputs are flow5's own files; inspect them before using any number."})
    (job_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
