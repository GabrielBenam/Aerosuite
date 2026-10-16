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

### 8.5 M06 (N + U)
`tests/test_m06_weight.py`, 16 pruebas. Método 1, Ejemplo 6-2 (GUD PDF 196): W0 = 6070.6 lbf (libro 6069), We 4173.6 (4172), Wf 797.1 (797); tolerancia ±3 lbf por redondeo del libro. Método 2: pares lbf/kg de las 9 clases coinciden en 6·10⁻⁵; Ec. 6-18 a 1320 lbf da 0.5376 frente a 0.535 de la Tabla 6-1 (±0.005); jet de negocios a 44 556 lbf da 0.5652 (libro 0.5652). Método 3, Ejemplo 6-4 (PDF 202–204): las nueve fracciones de segmento (0.9918, 0.9340, 0.7245, 0.9858, 0.9954, 0.9656, 0.9819, 0.9908, 0.9805) coinciden a 6·10⁻⁵; W_N/W0 = 0.60661 (libro 0.6066); W0 = 44 566 lbf (44 556; +0.02 %), We/W0 0.5652, We 25 189 lbf (25 184), combustible 17 532 lbf (17 528); segunda iteración con r escalado 43 636 lbf (43 619; +0.04 %) y We 24 692 (24 684). Tolerancias 0.05 % y 0.1 %. Eléctrico, Ejemplo 6-3 (PDF 197): L/D mínimo 21.62 y m0 = 6444 kg (libro 6444). Integración: cadena M06 → M04 con detección de desactualización probada. Suite completa: 93 OK (1 omitida); `aerosuite validate` sin errores.
