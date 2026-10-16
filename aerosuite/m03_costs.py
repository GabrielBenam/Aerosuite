"""M03 Costos (Gudmundsson Tabla 1-4 paso 3; Cap. 2, Secs. 2.2.1 y 2.3.1).

Nivel conceptual. Modelo de Eastlake para aeronaves GA de hélice (Ecs. 2-7 a 2-21) y costo operativo directo
de una aeronave privada (Ecs. 2-38 a 2-47). Las ecuaciones del libro usan lbf, KTAS y dólares; project.json
guarda masa en kg y este módulo convierte en la frontera. No se incluyen: la variante para aviones de negocio
(Secs. 2.2.2 y 2.3.2) ni las ecuaciones de hélices (ilegibles en la fuente digital; el precio de la hélice se
ingresa como dato).
"""
import math

from . import project as prj

LBF_PER_KG = 2.2046226218
REFERENCES = [
    "GUD Sec. 2.2.1 Eastlake: QDF Ec. 2-7, CER 1-10 Ecs. 2-8 a 2-18, PDF 84-87 / impr. 39-42",
    "GUD Sec. 2.2.1 costo fijo/variable, motor de pistón Ec. 2-21, Ejemplos 2-1 a 2-4, PDF 88-92 / impr. 43-47",
    "GUD Sec. 2.3.1 costo operativo directo, Ecs. 2-38 a 2-47 y Ejemplo 2-5, PDF 95-97 / impr. 50-52",
]
BASE_YEAR = 2012
COST_NOTE = ("Costos en dólares de 2012 (tarifas por defecto de Gudmundsson, Cap. 2); no están actualizados por "
             "inflación. Interpretar como orden de magnitud relativo, no como precio actual.")
RATE_DEFAULTS = {"r_engr": 92.0, "r_tool": 61.0, "r_mfg": 53.0}  # USD/h, junio 2012 (GUD PDF 86)


def qdf(n_units: float, f_exp: float = 0.95) -> float:
    """Ec. 2-7: factor de descuento por cantidad."""
    return f_exp ** (1.4427 * math.log(n_units))


def piston_engine_cost(n_eng: int, n_cyl: int, bhp: float, cpi_2019: float = 1.0) -> float:
    """Ec. 2-21 (GUD PDF 88-90): costo de motor(es) de pistón. Ejemplo 2-3: 6 cil., 310 BHP -> USD 102 526."""
    return n_eng * cpi_2019 * (-203900.0 + 155800.0 * n_cyl - 22620.0 * n_cyl ** 2 + 1007.0 * n_cyl ** 3
                               - 1394.0 * bhp + 8.654 * bhp ** 2 - 0.01447 * bhp ** 3)


def development_cost(w_airframe_kg, v_h_ktas, n_units, n_prototypes, q_m=None, certification="part23",
                     complex_flap=False, f_comp=0.0, pressurized=False, tapered_wing=True, cpi_2012=1.0,
                     rates=None, flight_test_usd=None) -> dict:
    """CER 1-10 del modelo de Eastlake. flight_test_usd: costo de pruebas en vuelo conocido (sustituye Ec. 2-13)."""
    if certification not in ("part23", "lsa"):
        raise ValueError("certification must be 'part23' or 'lsa'")
    r = {**RATE_DEFAULTS, **(rates or {})}
    lsa, cf, press = certification == "lsa", complex_flap, pressurized
    w, v, n, npr = w_airframe_kg * LBF_PER_KG, float(v_h_ktas), float(n_units), float(n_prototypes)
    qm = q_m if q_m is not None else round(n / 60.0)   # GUD Ej. 2-1: 1000/60 -> 17 aviones por mes
    h_engr = (0.0396 * w ** 0.791 * v ** 1.526 * n ** 0.183 * (0.67 if lsa else 1.0) * (1.03 if cf else 1.0)
              * (1.0 + f_comp) * (1.03 if press else 1.0))                                           # Ec. 2-8
    h_tool = (1.0032 * w ** 0.764 * v ** 0.899 * n ** 0.178 * qm ** 0.066 * (1.02 if cf else 1.0)
              * (1.0 + f_comp) * (1.01 if press else 1.0) * (1.0 if tapered_wing else 0.95))         # Ec. 2-9
    h_mfg = (9.6613 * w ** 0.74 * v ** 0.543 * n ** 0.524 * (0.75 if lsa else 1.0) * (1.01 if cf else 1.0)
             * (1.0 + 0.25 * f_comp))                                                                # Ec. 2-10
    c_engr = h_engr * r["r_engr"] * cpi_2012                                                         # Ec. 2-11
    c_dev = (0.06458 * w ** 0.873 * v ** 1.89 * npr ** 0.346 * cpi_2012 * (0.5 if lsa else 1.0)
             * (1.01 if cf else 1.0) * (1.0 + 0.5 * f_comp) * (1.03 if press else 1.0))             # Ec. 2-12
    c_ft = (flight_test_usd if flight_test_usd is not None else
            0.009646 * w ** 1.16 * v ** 1.3718 * npr ** 1.281 * cpi_2012 * (10.0 if lsa else 5.0))  # Ec. 2-13
    c_tool = h_tool * r["r_tool"] * cpi_2012                                                         # Ec. 2-15
    c_mfg = h_mfg * r["r_mfg"] * cpi_2012                                                            # Ec. 2-16
    c_qc = 0.13 * c_mfg * (0.5 if lsa else 1.0) * (1.0 + 0.5 * f_comp)                               # Ec. 2-17
    c_mat = (24.896 * w ** 0.689 * v ** 0.624 * n ** 0.792 * cpi_2012 * (0.75 if lsa else 1.0)
             * (1.02 if cf else 1.0) * (1.01 if press else 1.0))                                     # Ec. 2-18
    return {"workhours": {"engineering": h_engr, "tooling": h_tool, "manufacturing": h_mfg},
            "fixed": {"engineering": c_engr, "development_support": c_dev, "flight_test": c_ft, "tooling": c_tool,
                      "total": c_engr + c_dev + c_ft + c_tool},
            "variable_total_production": {"manufacturing": c_mfg, "quality_control": c_qc, "materials": c_mat},
            "monthly_rate_used": qm, "engineers_average_5y": h_engr / (5 * 48 * 40)}


def unit_costs(dev: dict, n_units, vsc: dict, f_exp=0.95, use_qdf=True, target_price_usd=None,
               insurance_fraction=0.15) -> dict:
    """Costo variable y total por unidad, precio mínimo y punto de equilibrio (Ecs. 2-19, 2-20; Ej. 2-3 y 2-4).

    vsc: componentes de proveedor por unidad sin QDF (USD), p. ej. {"avionics": 35000, "engine": 102526, ...}.
    El descuento por tren fijo (-17 500 USD, GUD PDF 88) va en vsc como valor negativo si aplica.
    """
    factor = qdf(n_units, f_exp) if use_qdf else 1.0
    var = dev["variable_total_production"]
    in_house = (var["manufacturing"] + var["quality_control"] + var["materials"]) / n_units
    vsc_total = sum(vsc.values()) * factor
    c_var = in_house + vsc_total
    c_fix = dev["fixed"]["total"]
    c_unit = c_var + c_fix / n_units
    out = {"qdf": factor, "variable_in_house_per_unit": in_house, "vsc_per_unit": vsc_total,
           "variable_per_unit": c_var, "fixed_per_unit": c_fix / n_units, "total_cost_per_unit": c_unit}
    if target_price_usd is not None:
        insurance = insurance_fraction * target_price_usd
        out.update({"insurance_per_unit": insurance, "minimum_selling_price": c_unit + insurance,
                    "target_price": target_price_usd,
                    "break_even_units": c_fix / (target_price_usd - c_var) if target_price_usd > c_var else None})
    return out


def operating_cost(p: dict) -> dict:
    """Costo operativo directo por año y por hora de vuelo (Ecs. 2-38 a 2-47)."""
    f = (0.30 + (-0.15 if p.get("owner_maintained") else 0.0) + (0.02 if p.get("difficult_engine_access") else 0.0)
         + (0.02 if p.get("retractable_gear") else 0.0) + (0.02 if p.get("vfr_radios") else 0.0)
         + (0.04 if p.get("ifr_radios") else 0.0) + (0.01 if p.get("integral_tanks") else 0.0)
         + (0.02 if p.get("complex_flap") else 0.0) + (0.10 if p.get("certification") == "lsa" else 0.0))   # Ec. 2-39
    q = p["flight_hours_per_year"]
    c_ap = f * p["mechanic_rate_usd_h"] * q                                                            # Ec. 2-38
    c_stor = 12.0 * p["storage_usd_month"]                                                             # Ec. 2-40
    c_fuel = p["fuel_flow_gal_h"] * q * p["fuel_price_usd_gal"]                                        # Ec. 2-41
    c_ins = 500.0 + 0.015 * p["aircraft_price_usd"]                                                    # Ec. 2-42
    c_insp = 500.0                                                                                     # Ec. 2-43
    c_over = 5.0 * p.get("n_engines", 1) * q                                                           # Ec. 2-44
    c_loan = 0.0
    if p.get("loan_apr") and p.get("loan_years"):
        i, n = p["loan_apr"] / 12.0, 12 * p["loan_years"]
        c_loan = 12.0 * p["aircraft_price_usd"] * i / (1.0 - (1.0 + i) ** -n)                           # Ec. 2-46
    total = c_ap + c_stor + c_fuel + c_ins + c_insp + c_over + c_loan                                  # Ec. 2-47
    return {"maintenance_ratio_fmf": f, "maintenance": c_ap, "storage": c_stor, "fuel": c_fuel, "insurance": c_ins,
            "inspection": c_insp, "engine_overhaul_fund": c_over, "loan": c_loan, "total_per_year": total,
            "per_flight_hour": total / q}


def run(project: dict) -> dict:
    d = prj.need_inputs(project, "m03", ["airframe_mass_kg", "vh_ktas", "units_5y", "prototypes"])
    dev = development_cost(d["airframe_mass_kg"], d["vh_ktas"], d["units_5y"], d["prototypes"], d.get("monthly_rate"),
                           d.get("certification", "part23"), d.get("complex_flap", False), d.get("f_comp", 0.0),
                           d.get("pressurized", False), d.get("tapered_wing", True), d.get("cpi_2012", 1.0),
                           d.get("rates"), d.get("flight_test_usd"))
    result = {"anio_base": BASE_YEAR, "nota_costos": COST_NOTE, "development": dev}
    if "vsc_usd" in d:
        vsc = dict(d["vsc_usd"])
        if "piston_engine" in d:
            e = d["piston_engine"]
            vsc["engine"] = piston_engine_cost(e["n_engines"], e["n_cylinders"], e["bhp"], e.get("cpi_2019", 1.0))
        result["unit"] = {mode: unit_costs(dev, d["units_5y"], vsc, d.get("f_exp", 0.95), mode == "with_qdf",
                                           d.get("target_price_usd"), d.get("insurance_fraction", 0.15))
                          for mode in ("without_qdf", "with_qdf")}
        result["vsc_usd_per_unit_without_qdf"] = vsc
    if "operation" in d:
        result["operation"] = operating_cost(d["operation"])
    if "rates" not in d:
        prj.add_assumption(project, "m03", "rates", RATE_DEFAULTS,
                           "supuesto de 2012: tarifas de junio 2012 del libro (GUD PDF 86), sin actualizar por inflación (D-23)")
    if "cpi_2012" not in d:
        prj.add_assumption(project, "m03", "cpi_2012", 1.0, "supuesto de 2012: sin ajuste de inflación (D-23); el libro usa 1.10 para abril 2019 solo en su ejemplo")
    prj.record(project, "m03", result, "conceptual", REFERENCES)
    return result
