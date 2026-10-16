# AeroSuite — Resultados de pruebas (TEST_RESULTS)

Tipos de prueba: **U** unitaria · **I** integración (motor real) · **N** validación numérica contra referencia externa · **E** ejecución de solucionador.

## Entorno de la sesión 2026-10-14 (Linux)

VM Ubuntu 22.04 en el equipo del usuario, Python 3.10.12, numpy 1.26.4, scipy 1.14.1, pandas 2.3.3, matplotlib 3.10.9, ADRpy 0.2.6 (instalado desde `vendor/ADRpy`, idéntico al paquete de PyPI). XFOIL 6.99 del paquete Debian `xfoil_6.99.dfsg+1-3_amd64` (SHA-256 del ejecutable f190881a…0798) con `LD_PRELOAD` que anula `_gfortran_set_fpe`. Evidencias en `evidence/2026-10-14-linux-vm/`.

## 1. Suite de pruebas (U + I)

`python -m unittest discover -s tests` → **43 pruebas, OK**. Sin XFOIL disponible: 42 OK + 1 omitida (prueba de XFOIL real). Con XFOIL: 43 OK. Repetida con numpy 2.2.6 / scipy 1.15.3: 43 OK.

## 2. ADRpy (N)

### 2.1 Atmósfera ISA vs ICAO (0 y 11 000 m)
T, p, ρ y a coinciden con los valores ICAO con diferencia relativa máxima 8.2·10⁻⁶. `evidence/.../validation/validation.json`.

### 2.2 Ejemplo del docstring de `twrequired_to` (ADRpy 0.2.6)
Reproducido exactamente: [0.19397876, 0.26758006, 0.33994772, 0.41110154]. Confirma instalación y compatibilidad numérica.

### 2.3 Gudmundsson, Ejemplo 3-1 (Cessna 162), W/S = 10 lbf/ft² = 478.8 Pa, T/W local (sin mapear a nivel del mar)

| Restricción | ADRpy 0.2.6 | Gudmundsson | Diferencia |
|---|---|---|---|
| Despegue (S_G = 640 ft) | 0.1988 | 0.1869 | +6.4 % |
| Ascenso (880 ft/min) | 0.2126 | 0.2140 | −0.7 % |
| Viraje (n = 1.155, 8000 ft) | 0.1235 | 0.1245 | −0.8 % |
| Crucero (108 KTAS, 8000 ft) | 0.1184 | 0.1192 | −0.6 % |
| Techo de servicio | 0.0968 | 0.0943 | +2.7 % |

Causas identificadas (no ajustadas): k inducido de ADRpy = 0.0468 (LESM, crucero) frente a 0.04909 del libro (e = 0.8106, Ec. 9-129); fórmula de despegue distinta (ADRpy: 0.5·CDTO/CLTO + 0.5·μ; libro Ec. 3-1: 0.605/CLmax·(CDTO − μ·CLTO) + μ); el libro evalúa el techo a 17 000 ft aunque el enunciado dice 15 000 ft. Fuente: Gudmundsson 2.ª ed., PDF p.109–111.

### 2.4 Dimensionamiento completo del mismo caso (`examples/gudmundsson-ex3-1-c162.json`)
Cinco restricciones + límite de pérdida (45 KCAS, CLmax limpio 1.68) → W/S máx. = 551.5 Pa (11.5 lbf/ft²). Punto de diseño muestreado: W/S = 502.7 Pa, T/W = 0.212 (nivel del mar, activa: ascenso). Potencia (ADRpy `powerrequired`, η de hélice del ejemplo): mínimo de la muestra 86.8 hp a 12.5 lbf/ft², frente a 89.4 BHP a 11.2 lbf/ft² en el libro (Fig. 3-3). Diagrama: `evidence/.../adrpy/c162-constraint-diagram.png`.

## 3. XFOIL (E + N)

### 3.1 Comparación de cuatro perfiles, Re = 10⁶, M = 0, Ncrit = 9, α = −4…22° (paso 1°), barrido desde 0°

| Perfil | (L/D)máx | α en (L/D)máx | CL máx observado | α | Puntos sin converger |
|---|---|---|---|---|---|
| NACA 4412 | 129.5 | 5° | 1.519 | 16° | — |
| NACA 4415 | 120.7 | 5° | 1.514 | 17° | — |
| NACA 2412 | 103.8 | 5° | 1.420 | 16° | α = 2° |
| NACA 0012 | 76.2 | 8° | 1.297 | 16° | α = 22° |

Gráficas CL-α, CD-α, CM-α, CL-CD y eficiencia: `evidence/.../xfoil/naca-re1e6-a22/comparison/plots/`. En CL-α hay saltos entre 1° y 4° en los perfiles curvados, asociados al desplazamiento de la transición calculado por XFOIL; no se suavizaron.

### 3.2 Efecto de Reynolds, NACA 2412 (−4…20°)

| Re | CL máx (α) | (L/D)máx (α) |
|---|---|---|
| 2·10⁵ | 1.223 (14°) | 67.2 (6°) |
| 5·10⁵ | 1.277 (16°) | 90.1 (5°) |
| 10⁶ | 1.420 (16°) | 103.8 (5°) |
| 3·10⁶ | 1.656 (19°) | 114.4 (4°) |

### 3.3 Comparación entre binarios (misma geometría, SHA-256 idéntico)

| Perfil, α | Debian 6.99 (CL, CD, CM) | MIT 6.99 Windows, CI previo (CL, CD, CM) |
|---|---|---|
| 2412, 0° | 0.2249, 0.00556, −0.0479 | 0.2251, 0.00555, −0.0480 |
| 2412, 2° | 0.4383, 0.00575, −0.0443 | 0.4394, 0.00574, −0.0446 |
| 0012, 0° | 0.0000, 0.00533, 0.0000 | 0.0000, 0.00532, 0.0000 |
| 0012, 2° | 0.1935, 0.00569, 0.0077 | 0.1937, 0.00569, 0.0077 |

### 3.5 XFOIL 6.99 del MIT en Windows (corrida F3, 2026-10-15)
Descargado de `https://web.mit.edu/drela/Public/web/xfoil/XFOIL6.99.zip` (SHA-256 del ZIP `e13e8fe5cc38d8ac2626e9d3b17643bdcfaa63791619f042afdaa7cd103bcb08`); solo se extrajo `xfoil.exe` a `tools/xfoil/` (SHA-256 `c17342f84ae260c2b11a74cd0e2fb8189a5f8954c6bb7a8467a0f27055c7faea`). Uso: `AEROSUITE_XFOIL=tools/xfoil/xfoil.exe`. `aerosuite status` lo detecta (`xfoil_2d: true`) y el `xfoil` de NACA 2412 (Re 10⁶, −2…16°) convergió en los 10 puntos.

### 3.4 Limitaciones
No se contrastó todavía con datos experimentales (Abbott & von Doenhoff no está en la biblioteca). La biblioteca UIUC no se probó con el ZIP real (descarga bloqueada en este entorno).

## 4. flow5 (E)

Exportación `examples/flow5-c162-like.json` → perfiles .dat, `planes/*.xml`, `analyses/*.xml`, `script.xml`: XML bien formado, estructura igual a `API_examples/PlaneRun4` y al lector `xflscriptreader.cpp` (prueba U). Ejecución con el flow5 oficial: **pendiente de la validación Windows** (§6). Los archivos de `evidence/2026-10-14-linux-vm/flow5/` contienen rutas de la VM y no sirven para ejecutar en Windows.

## 5. Optimizador (E)

### 5.1 Conceptual (`examples/opt-conceptual-c162.json`)
Variable W/S ∈ [239.4, 1675.8] Pa; minimizar T/W; restricción W/S ≤ límite de pérdida. `differential_evolution` convergió (31 iteraciones, 582 evaluaciones, 0 fallidas). Óptimo: W/S = 521.8 Pa, T/W = 0.2114, en el cruce despegue–ascenso, con 29.7 Pa de margen a la pérdida.

### 5.2 2D con XFOIL (`examples/opt-xfoil-naca4.json`)
Variables m ∈ [0, 0.05], p ∈ [0.2, 0.6], t ∈ [0.10, 0.16]; maximizar (L/D)máx a Re 3·10⁶, M 0.15; t ≥ 0.12 y CM en (L/D)máx ≥ −0.08. 83 evaluaciones, 33 fallidas (barridos incompletos), 35 factibles, 48 s. El solucionador **no** declaró convergencia (maxiter = 6, demostrativo). Mejor punto muestreado: m = 0.0449, p = 0.266, t = 0.151, L/D = 151.1 a α = 7°, CM = −0.0791 (restricción activa).

### 5.3 `optimize` heredado
AR llega al límite superior (12): artefacto por falta de modelo de peso (DECISIONS D-07).

## 7. Sesión en la nube, rama `feat/gudmundsson-base`

Python 3.13, numpy 2.2.6, scipy 1.15.3, ADRpy 0.2.6, XFOIL 6.99 Debian (mismo SHA-256 f190881a…0798). `python -m unittest discover -s tests` → **50 pruebas, OK** (43 previas + 7 del lector de flow5 con fixtures de formato). Con NumPy 2.5.3 ADRpy falla (DECISIONS D-10).

## 6. Validación en Windows

Pendiente: se ejecuta con `VALIDAR-WINDOWS.cmd` (crea `evidence/windows-<fecha>/`). Esta sección se completará con sus resultados.

## 8. Corrida autónoma F1–F2 (rama `auto/f1-f2`)

Entorno: Windows 11, `.venv` Python 3.11, NumPy 1.26.4, ADRpy 0.2.6. Línea base antes de la corrida: 50 pruebas OK (1 omitida).

### 8.1 M01 (N + U)
`tests/test_m01_requirements.py`, 5 pruebas. Contra el libro (GUD PDF 58): Cessna 172 → Nivel 2/bajo, Eclipse 550 → Nivel 3/alto (coinciden). Fronteras de asientos de la Tabla 1-3 y límites de la Tabla 1-2 comprobados. Suite completa: 55 OK (1 omitida). `aerosuite validate` sin cambios.

### 8.2 M02 (N + U)
`tests/test_m02_references.py`, 5 pruebas. Contra el libro (Tabla 6-1, PDF 196): n = 17; medias We/W0 = 0.5353, Wu/W0 = 0.4647, Wf/W0 = 0.0930 y desviaciones 0.0602, 0.0602, 0.0336 frente a 0.535, 0.465, 0.093 y 0.060, 0.060, 0.034 (tolerancia ±0.0006 = media unidad de la última cifra impresa). Fila Cessna C-162: We/W0 0.632 y Wf/W0 0.109 coinciden. El ajuste logarítmico se prueba con un fixture de algoritmo (recta de la Ec. 6-18, no son datos aerodinámicos) y reproduce el paso kg→lbf del libro (1.4343 → 1.5451). Suite completa: 60 OK (1 omitida).

### 8.3 M03 (N + U)
`tests/test_m03_costs.py`, 8 pruebas contra los Ejemplos 2-1 a 2-5 de Gudmundsson (PDF 85–97; Tabla 2-3 en PDF 90). Horas de trabajo: 205 670 / 190 300 / 1 366 628 (diferencia < 1 h). Costo fijo $36 444 233 (diferencia relativa < 1·10⁻⁶; el libro redondea las horas a 5 cifras); motor $102 526; QDF 0.5998; costo variable $250 311 sin QDF y $196 672 con QDF; precio mínimo $339 255 y $285 617; equilibrio 366 y 238 aviones; costo operativo anual $83 649 (préstamo $42 599). Suite completa: 68 OK (1 omitida).

**Ajuste D-23 (2026-10-15):** el resultado de M03 incluye `anio_base` 2012 y `nota_costos`; pruebas nuevas en `test_m03_costs.py` (nota en `outputs.m03` y en `project-status`). Los valores numéricos no cambian. Suite completa: 95 OK (1 omitida).

### 8.4 M04 (N + U + E)
`tests/test_m04_constraints.py`, 9 pruebas. Aterrizaje (Ejemplo 3-1, paso 8, GUD PDF 111): con W/S = 11.37 lbf/ft² la Ec. 3-13 da 1369.1 ft (objetivo 1369; tolerancia ±1 ft); el inverso da 11.366 lbf/ft² (libro 11.37, tolerancia ±0.01). Despegue Ec. 3-1 en el paso 3: T/W = 0.18692 (libro 0.1869, tolerancia 1·10⁻⁴). Con ISA (ρ = 1.225 kg/m³ = 0.0023769 slug/ft³ en vez de 0.002378) el límite de aterrizaje es 543.95 Pa = 11.36 lbf/ft², inferior al límite de pérdida 551.5 Pa, de modo que el aterrizaje manda el punto de diseño (W/S muestreado 502.7 Pa, T/W 0.212, ascenso activo). Contraste ADRpy 0.2.6 vs libro (T/W local, W/S = 10 lbf/ft²) con tolerancias documentadas: despegue 7 % (observado +6.4 %), ascenso 1 %, viraje 1 %, crucero 1 %, techo 3 % (observado +2.7 %). Suite completa: 77 OK (1 omitida); `aerosuite validate` ejecutado sin errores.
**Ajuste D-22 (2026-10-15):** el despegue del punto de diseño es la Ec. 3-1 (prueba nueva `test_takeoff_curve_is_eq_3_1_and_adrpy_is_contrast`, 10 pruebas en el archivo). Punto de diseño Ejemplo 3-1: antes 502.74 Pa y T/W 0.2118; después 526.68 Pa y T/W 0.2113 (ascenso activo; límite de aterrizaje 543.95 Pa). `contraste_adrpy`: ADRpy +10.1 % a 239 Pa, +5.3 % a 598 Pa, +2.2 % a 1676 Pa respecto de la Ec. 3-1 (media +4.3 %). Suite completa: 94 OK (1 omitida).

### 8.6 M08 (N + U)
`tests/test_m08_tail.py`, 11 pruebas. Contra Gudmundsson Cap. 11 (PDF 556-557, impr. 511-512, Cessna 172: S = 174 ft², b = 36 ft, c_MGC = 4.83 ft, R1 = 2.0 ft, R2 = 0.5 ft, V_HT = 0.761, V_VT = 0.0419): Método 1 (Ej. 11-1) l_HT = 12.76 ft (libro 12.76), S_HT = 50.1 ft² (50.1), b_HT = 12.26 ft con AR 3.0, S_wet = 200.5 ft² (200.5); Método 2 (Ej. 11-2) l_VT = 8.18 ft (8.18), S_VT = 32.1 ft² (32.1), b_VT = 6.58 ft (6.58); Método 3 (Ej. 11-3) l_T = 15.2 ft (15.2), S_HT = 42.2 ft² (42.2), S_VT = 17.3 ft² (17.3). Tolerancias de ±0.01 a ±0.2 (redondeo del libro). Planta trapezoidal: límites λ = 1 (c_MGC = c, y_MGC = b/4) y λ → 0 (c_MGC = 2/3 c_r, y_MGC = b/6) de la Sec. 9.2.2. Método 4: condiciones de frontera del perfil cuadrático (Ecs. 11-31/11-33), integral numérica contra el área lateral exacta de un tronco de cono y óptimo contra búsqueda en rejilla; **sin validación numérica contra el libro** (el Ejemplo 11-5 es una figura de hoja de cálculo que no da θ). Integración: CLI, `export`, dependencia M04 → M08 con marca de desactualizado. Suite completa: 106 OK (1 omitida); `aerosuite validate` sin errores.

### 8.7 M09a (N + U + E)
`tests/test_m09a_airfoils.py`, 8 pruebas. Matriz de decisión contra el ejemplo del libro (Sec. 8.3.9 (10), PDF 360): t/c 0.10/0.12/0.14/0.16 → 0, 0.333, 0.667, 1 (exacto); pesos (Cl_max con peso 3, como sugiere el libro), puntos manuales y exclusión de criterios sin datos. Extracción de métricas con una polar analítica rotulada **fixture de algoritmo (no son datos aerodinámicos)**. **Con XFOIL 6.99 real (Windows)**: NACA 0012 y 2412 a Re 3·10⁶ comparados con teoría de perfil delgado (segunda fuente independiente; el libro no tiene un ejemplo resuelto de selección de perfil con datos de XFOIL): α_ZL de la 2412 −2.15° (XFOIL) contra −2.08° (Glauert); de la 4412 −4.30° contra −4.15°; NACA 0012 α_ZL 0.18°; Cl_α entre 0.93 y 0.99 de 2π (5.86 a 6.19 /rad). Ejemplo completo (`examples/projects/airfoil-selection-ga.json`, Re 3·10⁶, M 0, Ncrit 9, −4…20°, Cl crucero 0.3): Cl_max 1.667 (2412), 1.731 (4412), 1.700 (4415), 1.566 (0012); Cd_min 0.0050, 0.0052, 0.0058, 0.0050; (L/D)máx 115, 157, 152, 99; puntuación total 5.93, 4.55, 4.03, 2.74 (gana la 2412 con pesos 1; depende del Cl objetivo y de los pesos). Barridos incompletos registrados: 2412 sin α = 6°, 4412 sin α = 4° (`missing_alpha`; criterio de XFOIL, D-05). **No se validaron las magnitudes contra datos experimentales** (Abbott & von Doenhoff no está en la biblioteca). Sin ejecutable: prueba de que devuelve `pending_engine` sin polares. Suite completa: 114 OK (3 omitidas sin `AEROSUITE_XFOIL`; 114 OK con él); `aerosuite validate` sin errores.

### 8.8 M09b (N + U)
`tests/test_m09b_wing.py`, 14 pruebas. Planta: Ejemplo 9-3 (S = 130 ft², AR = 8, λ = 0.5) b = 32.25 ft, c_r = 5.375 ft, c_t = 2.687 ft (exacto); Ec. 9-16 verificada contra la geometría de la planta (flechas LE, c/4, c/2) y x_MGC (Ec. 9-14). C_Lα: las ocho filas de la Tabla 9-7 (GUD PDF 413-414) para las Ecs. 9-69, 9-71 y 9-72 coinciden a ±0.006 /rad (p. ej. AR 10, Λc/2 = 28.55°: 5.24 / 5.15 / 4.40; delta AR 2.27: 3.34 / 2.84 / 2.51; disco AR 1.29: 2.46 / 1.85 / 1.83), con κ = 5.9/2π. CL_max (Ejemplo 9-9): 0.9·1.58 = 1.422, 8 % menos que el CL_max0 = 1.54 del POH, y V_S = 53.0 KCAS con W/S del Cessna 172 y CL_max0 = 1.54. e de Raymer (Ec. 9-129): 0.7566 en el Ejemplo 9-4 (AR 10) y 0.8106 / k = 0.04909 del Ejemplo 3-1 (AR 8). AR efectivo por alcance (Ejemplo 9-4): A = 0.02872 (libro 0.02872), AR_e = 7.88 (7.893 con A redondeado), límite de C_L 0.2533 (0.2533). Volumen (Ejemplo 9-3): la integral exacta da 7.04 ft³ por semiala; el libro imprime 10.16 ft³ y solo lo reproduce usando c_r en las constantes A y B (**inconsistencia del libro**, D-26); la conversión a combustible con el volumen impreso da 45.62 gal y 273.7 lbf. Integración: cadena M04 → M09b → M08 con marca de desactualizado; exportación de la configuración flow5 validada con `flow5_xml.validate` y `flow5_xml.export` (XML de intercambio; **flow5 no ejecutado**: pendiente de validación con el motor real). Suite completa: 127 OK (3 omitidas sin XFOIL); `aerosuite validate` sin errores.

### 8.9 M10 (N + U) — sin validación numérica contra un ejemplo del libro
`tests/test_m10_geometry.py`, 8 pruebas. Ni Gudmundsson (Cap. 4, Sec. 9.1.3) ni Sóbester (Caps. 2-4) traen un ejemplo resuelto de ensamble de OML, por lo que se validaron invariantes geométricos recalculados por integración numérica independiente: S = 2∫c dy, c_MGC = (2/S)∫c² dy y y_MGC = (2/S)∫y c dy (Ecs. 9-2, 9-5, 9-6) por cuadratura de punto medio sobre las cuerdas solevadas coinciden con M09b (|ΔS| < 2·10⁻⁵ m², |Δc_MGC| < 2·10⁻⁴ m); brazos y coeficientes de volumen recuperados de las coordenadas ensambladas: l_HT, l_VT idénticos a M08, V_HT = 0.761 y V_VT = 0.0419 a 1·10⁻⁹ (Ejemplo 11-3 de GUD como datos de entrada). Construcción: círculo generalizado de SOB Ec. 2.16 (N = 0.5 es un círculo exacto de diámetro 1), solevado lineal (Ec. 4.1: sección intermedia = promedio), signo y conservación de cuerda en la torsión del contorno, perfil de fuselaje y área mojada. Comprobaciones de robustez: un ala fuera de la altura del fuselaje marca `valid = false`. Cadena M09b/M08 → M10 con marca de desactualizado y `export` (esquema `aerosuite-oml/1`). Suite completa: 135 OK (3 omitidas sin XFOIL); `aerosuite validate` sin errores.

### 8.10 M11 (N + U + E)
`tests/test_m11_powerplant.py`, 12 pruebas. Ejemplo 7-2 (GUD PDF 254): σ = 0.7385 a 10 000 ft, P = 70.4 BHP con Gagg-Ferrar, 68.3 BHP con la Ec. 7-12, 66.3 BHP con la Ec. 7-13 y 65.5 BHP por la vía de la densidad del gas ideal (todos exactos); Fig. 7-8: 75 %, 65 % y 55 % de potencia a 8283, 12 106 y 16 324 ft (±0.001); σ de ADRpy contra la fórmula del libro a 10 000 ft (±0.0005). Ejemplo 7-3: 5800/2.43 = 2387 RPM. Ejemplo 15-2: diámetros de 67.2, 61.6 y 56.0 in y velocidades de punta 675, 618 y 562 ft/s (tolerancia 0.06 in y 1.5 ft/s). Ejemplo 15-3: J = 1.096. Caso LSA de la Sec. 15.3.4: η_p = 0.686. Paso de hélice (Ec. 15-30): constante 1215.36 verificada contra la deducción y en SI (errata del libro, D-28). Cadena M04 → M11 con el ejemplo del Cessna 162 (`examples/projects/c162-m11-inputs.json`): potencia requerida 87.0 hp (restricción de ascenso), motor de 100 BHP con margen +15 %, hélice bipala de madera 63.8 in con M punta 0.718 (supera 0.6 de la madera: se advierte, no se corrige), η_p requerida 0.58 con L/D = 10, contraste IO-540 de ADRpy +5 % a 1500 m y +7 % a 3000 m respecto de Gagg-Ferrar. **Altitud crítica (Ec. 7-10) sin ejemplo del libro: sin validación numérica.** Suite completa: 147 OK (3 omitidas sin XFOIL); `aerosuite validate` sin errores.

### 8.11 M12 (N + U)
`tests/test_m12_weights.py`, 12 pruebas. **Ejemplo 6-5** (GUD PDF 210; S = 130 ft², AR = 8, λ = 0.5, t/c = 0.16, W0 = 1320 lbf, n_z = 6.0): Cessna en voladizo 334.7 lbf (libro 335), con tirantes 212.9 (213), Raymer 179.4 (180), Torenbeek 127.8 (128), USAF 139.2 con V_H = 125 KEAS (139; el ejemplo no lista V_H) y promedio de las tres últimas 148.7 (149). **Ejemplo 6-6** (Bonanza A36, GUD PDF 217-218): b = 33.50 ft, c_MGC = 5.566 ft, y_MGC = 7.536 ft, h = 0.918 ft, M_max = 89 530 ft·lbf, A_cap = 1.500 in², W_cap = 66.3 lbf (todos iguales al libro). **Ejemplo 6-7**: AR 6.2 → 10: M_max = 113 704 ft·lbf (113 703), W_cap = 135.9 lbf (135.9), Δ = 69.6 lbf (69.6; 69.5 con la base sin redondear), W_e = 2317 lbf (2317); y la reevaluación del modelo con AR = 10 coincide con la escala AR^1.5. Las demás ecuaciones de componentes (6-48 a 6-105, 6-106) **no tienen ejemplo resuelto en el libro: sin validación numérica**; se prueban conversión SI↔inglés, ámbitos de validez, pesos conocidos, calibración y datos faltantes. Cessna VT (6-52) arroja 0.9 lbf con el exponente impreso y se excluye por defecto (D-29). Ejemplo ilustrativo (`examples/projects/c172-like-weights-inputs.json`, datos del usuario, no del avión real): suma de 661 kg (1457 lbf) para W0 = 1157 kg; la dispersión entre métodos es amplia (p. ej. tren 41 a 190 lbf, mandos 37 a 145 lbf), como advierte el libro. Suite completa: 159 OK (3 omitidas sin XFOIL); `aerosuite validate` sin errores.

### 8.12 M13 (N + U)
`tests/test_m13_cg.py`, 15 pruebas. **Ejemplo 6-8** (GUD PDF 224): CG en FS 191.3 con el borde de ataque de la MGC en FS 185 y c_MGC = 6.32 ft → 8.31 % MGC (exacto). **Ejemplo 6-9** (Tabla 6-5, leída de la figura): W_tot = 24.50 lbf, M_x = 170.0, M_y = −15.25, M_z = 6.38 ft·lbf, CG (6.939, −0.622, 0.260) ft (igual al libro). **Ejemplo 6-10** (Tabla 6-10): pesos 55.0, 60.0, 65.0 lbf; M_x 317.0, 375.0, 438.0 ft·lbf; X_CG 5.764, 6.250, 6.738 ft (igual al libro). Pesaje (Ecs. 6-138/6-139): consistencia estática (x_N + x_M = x_NM). **Inercias: el libro no trae ejemplo resuelto; segunda fuente independiente (mecánica clásica)**: mancuerna I = 2 m a², teorema de ejes paralelos I = I_cg + M d², barra uniforme discretizada contra M L²/12 (error < 10⁻⁴), ecuaciones de giro (Ec. 6-150) contra recálculo directo con ejes girados (|Δ| < 10⁻⁹) y ángulo principal con I_uv = 0 y extremos iguales a los autovalores, simetría de la matriz, invariancia de la traza y desigualdad triangular de los momentos principales. Envolvente: caja y polígono, aritmética de la nube de cargas (algoritmo, no datos del libro). Cadena M12 → M13 (la masa total es la de M12 a 10⁻⁹), faltantes de posiciones y envolvente sin límites. Ejemplo ilustrativo `examples/projects/c172-like-cg-inputs.json` (datos del usuario): CG vacío 26.8 % c_MGC y nube entre 21.4 % y 29.9 %. Suite completa: 174 OK (3 omitidas sin XFOIL); `aerosuite validate` sin errores.

### 8.13 M15 (N + U)
`tests/test_m15_fuselage.py`, 12 pruebas. **Tabla 12-1** (D = 2, D1 = 2, D2 = 1, L = 3; GUD PDF 578): cilindro elíptico h = 0.1111, S = 14.533, V = 4.712; cilindro uniforme 18.850 y 9.425; paraboloide 13.035 y 4.712; cono 9.935 y 3.142; volumen del tronco 5.498 (todos iguales). **Errata**: el área del tronco impresa (14.902) solo se reproduce con (D1 − D2)² bajo la raíz; la generatriz exacta da 14.332, que coincide con la integración numérica del sólido de revolución (|Δ| < 10⁻⁴) (D-31). Paraboloide y cono contra integración numérica independiente (volumen a 2·10⁻⁴, área a 2·10⁻³); volumen del fuselaje tubular (Ec. 12-14) y renacuajo (Ec. 12-17) contra su forma cerrada; la Ec. 12-1 reconstruida coincide con la Ec. 12-4 en el cilindro. Reglas del texto: 50 cm por persona, pasillo 20 in, lavabos y galleys, rangos de nariz y cola (se informan, no se corrigen), ángulo de golpe de cola y cabeceo en pérdida. Cadena M09b/M08 → M15 → M10: M10 construye el fuselaje dimensionado (longitud, radio y posiciones exactos, `valid`), áreas de los sólidos elementales de M15 contra la polilínea de M10 dentro de 5 %. Ejemplo (`examples/projects/c172-like-fuselage-inputs.json`, datos del usuario): fuselaje de 8.69 m (nariz 1.60 d, cola 3.48 d: fuera del rango ideal 3–3.35 d, se avisa), 22.7 m² mojados y 5.6 m³. Suite completa: 186 OK (3 omitidas sin XFOIL); `aerosuite validate` sin errores.

### 8.5 M06 (N + U)
`tests/test_m06_weight.py`, 16 pruebas. Método 1, Ejemplo 6-2 (GUD PDF 196): W0 = 6070.6 lbf (libro 6069), We 4173.6 (4172), Wf 797.1 (797); tolerancia ±3 lbf por redondeo del libro. Método 2: pares lbf/kg de las 9 clases coinciden en 6·10⁻⁵; Ec. 6-18 a 1320 lbf da 0.5376 frente a 0.535 de la Tabla 6-1 (±0.005); jet de negocios a 44 556 lbf da 0.5652 (libro 0.5652). Método 3, Ejemplo 6-4 (PDF 202–204): las nueve fracciones de segmento (0.9918, 0.9340, 0.7245, 0.9858, 0.9954, 0.9656, 0.9819, 0.9908, 0.9805) coinciden a 6·10⁻⁵; W_N/W0 = 0.60661 (libro 0.6066); W0 = 44 566 lbf (44 556; +0.02 %), We/W0 0.5652, We 25 189 lbf (25 184), combustible 17 532 lbf (17 528); segunda iteración con r escalado 43 636 lbf (43 619; +0.04 %) y We 24 692 (24 684). Tolerancias 0.05 % y 0.1 %. Eléctrico, Ejemplo 6-3 (PDF 197): L/D mínimo 21.62 y m0 = 6444 kg (libro 6444). Integración: cadena M06 → M04 con detección de desactualización probada. Suite completa: 93 OK (1 omitida); `aerosuite validate` sin errores.

### 8.14 M16 (N + U)
`tests/test_m16_stability.py`, 10 pruebas. B747 de Etkin (Secs. 6.2 y 6.7, unidades inglesas): entradas de A y autovalores longitudinales (fugoide −0.003289 ± 0.067231i, periodo corto −0.3719 ± 0.8875i) y laterales (espiral −0.0072973, balanceo −0.56248, holandés −0.033011 ± 0.94655i, periodo 6.64 s) dentro de las tolerancias de la prueba; Lanchester 107 s. Identidades estáticas (CM_α = 0 en h_n; CM_α = −CL_α,W·SM). Cadena M09b→M08→M10→M12→M13→M16, desactualización y exportación. Fixtures de datos publicados, no resultados de AeroSuite. Suite: 199 pruebas OK. Validación con flow5 7.55 (tipo 7): pendiente.

### 8.15 M18a (N + U)
`tests/test_m18a_gear.py`, 14 pruebas. Ejemplo 13-2: R_N estática = 357.5 lbf (W = 1320, x_M = 1.3, x_N = 3.5 ft); Ejemplo 13-3: cola 151.9 lbf = 11.5 % y principal 1168 lbf (la geometría de la figura no es legible: la razón de brazos se despeja del resultado impreso). Equilibrio independiente de fuerzas y momentos de las Ecs. 13-17 y 13-20 reescritas; identidades de radio de giro, vuelco, huella y energía de frenado (constante 0.0443, errata del libro 0.0433); velocidad de descenso contra 4.4 (W/S)^¼. Cadena M09b→…→M13→M18a, desactualización, exportación, tren convencional con rotación. Suite: 213 pruebas OK.

### 8.16 M18b (N + U)
`tests/test_m18b_controls.py`, 11 pruebas. Ejemplo 24-6 (d): τ_e(0.3) = 0.5066 y CL_δe = 2.294 1/rad (0.04004 1/°); identidades (la flotación anula C_H; el factor 1 − τ C_Hα/C_Hδ sale de la flotación; geometría de la ganancia manual; H ∝ q); cadena M09b→M08→M16→M18b, desactualización, exportación y caso sin derivadas (solo geometría). Suite: 224 pruebas OK.

### 8.17 M18c (N + U)
`tests/test_m18c_highlift.py`, 10 pruebas. Ejemplo 10-2: C_lmax = 3.01 (prorrateo, factor 0.90); Ejemplo 10-3: 0.9·2·155.81/144.9 = 1.936 (97.3 % del POH 1.99; la suma 155.81 ft² se lee del ejemplo); Ec. 10-1; geometría de la particion; cadena M09b→M18c con incrementos declarados. **XFOIL 6.99 real** (`tools/xfoil/xfoil.exe`, SHA-256 c17342f8…faea): NACA 2412 con flap c_f/c = 0.30, δ = 10°, Re = 3e6: ΔC_l(α = 0) = 0.621 contra 0.725 de la teoría de perfil delgado (τ = 0.661), es decir 86 %, razonable para un cálculo viscoso. Ejemplo tipo Cessna 172 con XFOIL: C_lmax limpio 1.667 (α = 18°), con flap 10° 1.784 y con flap 30° 2.031 (picos capturados); C_Lmax de ala (particion, flap 12 %–62 % de la semienvergadura) 1.518 al despegue y 1.518 al aterrizaje (los segmentos sin flap limitan por la incidencia de pérdida con flap, Ecs. 8-11/8-12), contra 1.422 limpio con el mismo método. Evidencia en `evidence/xfoil-flaps-win/`. Suite: 234 pruebas OK.

### 8.18 M19 (N + U)
`tests/test_m19_stall.py`, 10 pruebas. Ala elíptica (AR = 7.96): C_Lα de la línea sustentadora 5.02124 frente a 5.02122 de la fórmula cerrada, e = 1; ala rectangular AR = 6: τ ≈ 0.16, δ ≈ 0.05 (Glauert/Anderson); α_0L del NACA 2412 −2.08° (tablas −2.0°); Ecs. 9-139/9-140 inversas; criterios de pérdida benigna sobre distribuciones controladas; cadena M09b→M19 y tendencia del alabeo (más alabeo: la primera pérdida se mueve hacia dentro y α de pérdida crece). Ejemplo tipo Cessna 172 (alabeo 1.5°): C_Lα 4.803 (M09b: 4.796), pérdida del ala a α = 16.0°, C_Lmax 1.461 (el libro estima 1.468 para el 172 real, POH 1.41), primera pérdida en η = 0.25, punta sin perder, benigna. **Contraste con flow5 7.55 real** (`evidence/flow5-7.55-win/run2-custom-ref`, modelo ala + cola, VLM2): C_Lα de flow5 = 5.105 1/rad (ajuste α −4…8°) frente a 4.868 de la línea sustentadora del ala sola, es decir −4.6 %, con la cola aportando pendiente. Suite: 244 pruebas OK.

### 8.19 M20 (N + U)
`tests/test_m20_drag.py`, 17 pruebas. Ejemplo 16-11: FF del ala = 1.3111 (calculado 1.31108); Ejemplo 16-6: x0/c = 0.07290 (0.072896) y, al mismo Re (6.87e6), C_f laminar 0.0005068 y turbulento 0.003185 (Prandtl-Schlichting 0.003191, +0.2 %); límites de Young, Re de corte, aritmética del buildup y del CRUD, escalado de ΔC_D; viscosidad de Sutherland 1.789e-5. Cadena M09b→M08→M20, polar, L/D máx, desactualización, exportación; M16 toma C_D0 de M20. Ejemplo tipo Cessna 172: C_Dmin = 0.0270 (f = 0.437 m²), L/D máx = 13.7 con k de M09b. **Contraste con flow5 7.55 real** (wing-tail, 55.6 m/s, 2438 m): CD_viscous mínimo 0.00743 frente a 0.0119 (todo turbulento) y 0.0068 (transición al 60 %) del buildup sin fuselaje ni CRUD; factor inducido de flow5 0.0368 contra 0.0491 de M09b. Suite: 261 pruebas OK.

## 9. V-F5: flow5 7.55 real (2026-10-15)
Ejecutable `C:\Users\oscar\Documents\flow5_v7.55_win64\flow5_v7.55_win64\flow5.exe`, 8 898 048 bytes, SHA-256 `4254b851cbda6eaf281b145e7b509756541ee064fd4b38d6b54b79ca1a8d13e1`; la bitácora de flow5 imprime «flow5 v7.55» (no hay opción de versión por consola). El código fuente y el lector son de v7.57. Evidencia: `evidence/flow5-7.55-win/` (salidas del solucionador real, no fixtures de formato).
* Corrida 1 (PLANFORM): aborta en 3.7 s por referencias en cero (D-32). Corrida 2 (CUSTOM): `flow5-run` código 0, 75 s, 17 puntos (α −4…12°), VLM2 + XFoil on the fly, V = 55.6 m/s, ρ = 0.9629, ν = 1.778e-5, caso `examples/flow5-c162-like.json` (S = 11.139 m², b = 9.44 m, AR = 8.0, MAC = 1.181 m).
* `flow5-results`: 1 polar, 17 filas, 0 errores. Suite: 189 pruebas OK.
* Física básica (cifras, sin ajustar el lector): C_Lα = 5.113 /rad (α₀L = −1.40°) contra 4.906 /rad de Helmbold con a₀ = 2π (Cap. 9): +4.2 %, razonable porque flow5 incluye el estabilizador y el espesor del perfil. Ajuste CD = CD0 + k·CL²: CD0 = 0.00639, k = 0.0416 (R² = 0.997), es decir e = 1/(π·AR·k) = 0.956. dCm/dα < 0 (Cm 0.208 → 0.033 entre α = 0° y 9°): estable. XNP = 0.66 m; margen estático ≈ 0.215 de MAC (por dCm/dCL y por XNP). Notas: la Cm del polar es respecto al CG supuesto (0.40 m); el CD incluye solo ala y cola (sin fuselaje), por lo que CD0 no es el de la aeronave completa. Cm positivo a α = 0 indica que el estabilizador (−2°) no está compensado; no se usó para ningún cálculo.
