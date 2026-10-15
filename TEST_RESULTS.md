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
