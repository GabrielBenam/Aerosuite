# AeroSuite — Estado del proyecto (PROJECT_STATE)

Última actualización: 2026-10-14 (2.ª sesión: rama `feat/gudmundsson-base` sobre `main` de GitHub). Base: rama de GitHub entregada como `Github.zip` (versión con `vendor/`, `setup-engines.ps1`, `size/optimize/xfoil`) fusionada con la carpeta local; respaldo de los archivos locales sustituidos en `_respaldo_local_20261014/`.

Estados: **FUNCIONAL** (ejecutado con el motor real y con evidencia), **PARCIAL** (funciona con limitaciones documentadas), **NO PROBADO** (código listo, sin ejecución real), **NO DISPONIBLE**.

## 1. Motores originales

| Motor | Versión fijada | Ubicación | Estado | Evidencia |
|---|---|---|---|---|
| flow5 (fuentes) | v7.57, SHA a9e852c5… | `vendor/flow5` (copia íntegra del tag, con `.git`) | FUNCIONAL como fuente de referencia (sin compilar) | `aerosuite status` → `matches_pin: true` |
| flow5 (ejecutable oficial Windows) | `flow5_v7.57_win64.zip` | `runtime/flow5` (lo descarga `setup-engines.ps1`) | NO PROBADO por Claude hasta la validación Windows | ver TEST_RESULTS §6 |
| ADRpy | 0.2.6, SHA b2beba27… | `vendor/ADRpy` + instalado en `.venv` | FUNCIONAL | reproduce el ejemplo de su docstring con error 0 |
| XFOIL | 6.99 | `runtime/xfoil/xfoil.exe` (MIT, Windows) | FUNCIONAL en Linux (paquete Debian 6.99, mismo código); Windows MIT validado en CI previo (2 puntos) | TEST_RESULTS §3 |
| SciPy | 1.14.1 (requirements: <1.15) | `.venv` | FUNCIONAL | TEST_RESULTS §5 |

## 2. Módulos AeroSuite (`aerosuite/`)

| Módulo | Función | Estado |
|---|---|---|
| `engines.py` | Localiza motores, lee SHA de `vendor/*/.git/HEAD`, comando `status` | FUNCIONAL |
| `airfoils.py` | NACA 4 dígitos (código y paramétrico continuo m, p, t) | FUNCIONAL |
| `uiuc_library.py` | Lector Selig desde el ZIP oficial UIUC | PARCIAL: probado con datos de prueba; el ZIP UIUC no se pudo descargar (sitio bloqueado en este entorno); Lednicer no soportado |
| `xfoil_cli.py` | Ejecuta XFOIL real: Re, Mach, Ncrit, Xtr, barrido α, barrido desde 0°, registro de puntos no convergidos, versión y SHA-256 del ejecutable | FUNCIONAL (Linux) |
| `batch_compare.py`, `airfoil_compare.py` | Comparación CL, CD, CM, CL/CD, eficiencia; rechaza condiciones distintas; modo `--allow-partial` | FUNCIONAL |
| `adrpy_core.py` | Restricciones ADRpy (despegue, ascenso, crucero, techo, viraje), límite de pérdida, potencia (hp), diagrama, tabla ISA, Reynolds | FUNCIONAL |
| `validation.py` | ISA vs ICAO, docstring ADRpy, Ejemplo 3-1 de Gudmundsson | FUNCIONAL |
| `optimizer.py` | Optimizador SciPy con contrato JSON; motores `adrpy` (conceptual) y `xfoil` (2D) | FUNCIONAL; `flow5` (3D) rechazado explícitamente |
| `flow5_results.py` (M-F5R) | Lector de polares y puntos de operación de flow5 v7.57: columnas por encabezado, conversión a SI desde las etiquetas de unidad, derivadas de estabilidad y control, distribuciones en envergadura; ajuste CD0/k (simplificado y ajustado), pendiente de sustentación, margen estático | FUNCIONAL con fixtures de formato tomados del código escritor de flow5; NO PROBADO con salidas reales de flow5 |
| `flow5_xml.py` | Genera perfiles .dat, avión XML, polar XML y guion `xflscript` para `flow5 -s`; ejecuta y registra salidas | Exportación FUNCIONAL (XML válido, estructura de los ejemplos oficiales); ejecución NO PROBADA hasta Windows |
| `flow5_adapter.py` + `integrations/flow5/xfoilbatch_aerosuite.cpp` | Adaptador C++ al API de flow5 (prototipo anterior) | NO PROBADO; en pausa (ver DECISIONS D-03) |
| `desktop.py`, `airfoil_lab_core.py` (Airfoil Lab, Tkinter) | GUI previa de comparación de perfiles | NO PROBADO en esta sesión; no se amplió (sin GUI nueva en esta etapa) |

## 3. Capacidades disponibles de forma independiente

- **flow5**: toda la aplicación original (modelado de alas, fuselajes y aviones; LLT, VLM1, VLM2, paneles QUADS/TRIUNIFORM/TRILINEAR; polares T1–T8; estabilidad; visualización). Se usa en su interfaz original (`aerosuite flow5`) o en modo por lotes. Funciones náuticas presentes en el ejecutable pero fuera del alcance.
- **ADRpy**: atmósferas (ISA y desviaciones, MIL-HDBK-310), análisis de restricciones, potencia requerida, modelos de motor, envolvente V-n CS-23 (`airworthiness.flightenvelope`, aún sin comando AeroSuite).
- **XFOIL**: análisis viscoso 2D de perfiles NACA y Selig.
- **SciPy**: `differential_evolution`, `SLSQP`, malla factorial.

## 4. Conexiones efectivamente operativas

| Conexión | Estado |
|---|---|
| ADRpy ISA → Reynolds/Mach (`aerosuite reynolds`) | FUNCIONAL |
| ADRpy → optimizador conceptual (W/S con límite de pérdida) | FUNCIONAL |
| Generador NACA → XFOIL → CSV/JSON → comparador y gráficas | FUNCIONAL |
| NACA paramétrico → XFOIL → optimizador 2D | FUNCIONAL (con fallas registradas por barridos incompletos) |
| JSON de avión → XML flow5 → `flow5 -s` → `flow5_results.json` | Exportación y lectura FUNCIONALES por separado; cadena completa NO PROBADA (falta ejecutar flow5) |
| ADRpy ISA → fluido de la polar flow5 (densidad, viscosidad cinemática) | FUNCIONAL en la exportación |

## 5. Conexiones pendientes

Ver la lista numerada en `CLAUDE_HANDOFF.md` §5 (C-1 a C-9).

## 6. Hallazgos que afectan el uso

1. El `optimize` heredado lleva el alargamiento a su límite superior: con solo restricciones ADRpy no hay penalización de peso; no es una recomendación (DECISIONS D-07).
2. El `size` anterior elegía el punto de diseño sin límite de pérdida; ahora lo aplica si existen `vstallclean_kcas` y `CLmaxclean`.
3. El paquete Debian de XFOIL activa trampas de punto flotante y se cierra con SIGFPE; en Linux se ejecuta con `LD_PRELOAD` de una función nula (`_gfortran_set_fpe`). No afecta a Windows.
4. XFOIL depende del camino de convergencia: el mismo α puede converger en un barrido y no en otro (NACA 2412, α = 2°, Re 10⁶).

## 7. Módulos del algoritmo F1–F2 (corrida autónoma, rama `auto/f1-f2`)

Núcleo: `aerosuite/project.py` (`project.json` con `inputs`, `outputs` + registro de corrida, `assumptions`, detección de salidas desactualizadas) y `aerosuite/cli_modules.py` (`project-init`, `project-status`, `mXX`). Ejemplo: `examples/projects/c162-inputs.json`.

| Módulo | Comando | Nivel | Estado |
|---|---|---|---|
| M01 Requisitos y base regulatoria | `m01` | conceptual | FUNCIONAL: clasificación Tabla 1-3 validada con los dos casos del libro (Cessna 172, Eclipse 550); límites de la Tabla 1-2 y §23.2110(c) verificados por pruebas unitarias. Categoría Commuter sin factores de carga (celda ilegible en la fuente). |
| M02 Referencias y regresiones | `m02` | conceptual | FUNCIONAL: base `aerosuite/data/gud_table_6_1_lsa.json` (17 LSA de la Tabla 6-1, leída de la figura del libro); medias y desviaciones reproducen la tabla (We/W0 0.535 ± 0.060, Wu/W0 0.465 ± 0.060, Wf/W0 0.093 ± 0.034). Ajuste We/W0 = A + B ln W0 con detección de caso degenerado. Solo esa base; las de los Caps. 16, 18, 19 y 23 no se han cargado (D-18). |
| M03 Costos | `m03` | conceptual | FUNCIONAL: modelo de Eastlake GA de hélice (QDF, CER 1–10, costo fijo/variable, precio mínimo, punto de equilibrio, motor de pistón Ec. 2-21) y costo operativo directo (Ecs. 2-38 a 2-47). Reproduce los Ejemplos 2-1 a 2-5 y la Tabla 2-3 del libro. No incluye aviones de negocio (2.2.2/2.3.2) ni ecuaciones de hélices (D-19). Tarifas y CPI por defecto registrados como supuestos. |
| M04 Restricciones (+ aterrizaje) | `m04` | conceptual | FUNCIONAL: `adrpy_core.size` (ADRpy sin modificar) + límite de pérdida + aterrizaje de Gudmundsson (Ecs. 3-13/3-14, total y solo rodadura, W/S máx. por bisección) + Ec. 3-1 de despegue como contraste. Ejemplo 3-1: W/S máx. de aterrizaje 11.36 lbf/ft² (libro 11.37) y T/W de despegue 0.1869 (exacto). Punto de diseño respeta pérdida y aterrizaje (activo: aterrizaje, 544 Pa). Diferencias ADRpy–libro documentadas (TEST_RESULTS §2.3, §8.4). |
