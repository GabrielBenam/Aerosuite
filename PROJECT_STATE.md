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
