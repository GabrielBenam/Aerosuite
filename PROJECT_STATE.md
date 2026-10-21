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
| `flow5_results.py` (M-F5R) | Lector de polares y puntos de operación de flow5 v7.57: columnas por encabezado, conversión a SI desde las etiquetas de unidad, derivadas de estabilidad y control, distribuciones en envergadura; ajuste CD0/k (simplificado y ajustado), pendiente de sustentación, margen estático | FUNCIONAL; validado con salida real de flow5 7.55 (evidence/flow5-7.55-win, D-33); sigue sin comprobarse contra 7.57 |
| `flow5_xml.py` | Genera perfiles .dat, avión XML, polar XML y guion `xflscript` para `flow5 -s`; ejecuta y registra salidas | Exportación y ejecución FUNCIONALES con flow5 7.55 en lote (referencias CUSTOM, D-32); 7.57 sin probar |
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

## 7. Módulos del algoritmo F1–F3 (corridas autónomas, ramas `auto/f1-f2` y `auto/f3`)

Núcleo: `aerosuite/project.py` (`project.json` con `inputs`, `outputs` + registro de corrida, `assumptions`, detección de salidas desactualizadas) y `aerosuite/cli_modules.py` (`project-init`, `project-status`, `mXX`). Ejemplo: `examples/projects/c162-inputs.json`.

| Módulo | Comando | Nivel | Estado |
|---|---|---|---|
| M01 Requisitos y base regulatoria | `m01` | conceptual | FUNCIONAL: clasificación Tabla 1-3 validada con los dos casos del libro (Cessna 172, Eclipse 550); límites de la Tabla 1-2 y §23.2110(c) verificados por pruebas unitarias. Categoría Commuter sin factores de carga (celda ilegible en la fuente). |
| M02 Referencias y regresiones | `m02` | conceptual | FUNCIONAL: base `aerosuite/data/gud_table_6_1_lsa.json` (17 LSA de la Tabla 6-1, leída de la figura del libro); medias y desviaciones reproducen la tabla (We/W0 0.535 ± 0.060, Wu/W0 0.465 ± 0.060, Wf/W0 0.093 ± 0.034). Ajuste We/W0 = A + B ln W0 con detección de caso degenerado. Solo esa base; las de los Caps. 16, 18, 19 y 23 no se han cargado (D-18). |
| M03 Costos | `m03` | conceptual | FUNCIONAL: modelo de Eastlake GA de hélice (QDF, CER 1–10, costo fijo/variable, precio mínimo, punto de equilibrio, motor de pistón Ec. 2-21) y costo operativo directo (Ecs. 2-38 a 2-47). Reproduce los Ejemplos 2-1 a 2-5 y la Tabla 2-3 del libro. No incluye aviones de negocio (2.2.2/2.3.2) ni ecuaciones de hélices (D-19). Tarifas y CPI por defecto registrados como supuestos de 2012; todo resultado lleva `nota_costos` (D-23). |
| M04 Restricciones (+ aterrizaje) | `m04` | conceptual | FUNCIONAL: `adrpy_core.size` (ADRpy sin modificar) + límite de pérdida + aterrizaje de Gudmundsson (Ecs. 3-13/3-14, total y solo rodadura, W/S máx. por bisección) + Ec. 3-1 de despegue como contraste. Ejemplo 3-1: W/S máx. de aterrizaje 11.36 lbf/ft² (libro 11.37) y T/W de despegue 0.1869 (exacto). Desde D-22 la curva de despegue del punto de diseño es la Ec. 3-1 (`fuente` por restricción; ADRpy en `contraste_adrpy`); punto de diseño 526.7 Pa, T/W 0.2113 (activo: ascenso; límite de aterrizaje 544 Pa). Diferencias ADRpy–libro documentadas (TEST_RESULTS §2.3, §8.4). |
| M08 Cola inicial | `m08` | conceptual | FUNCIONAL: V_HT/V_VT de la Tabla 11-4 o dados; Métodos 1-3 (Ecs. 11-26 a 11-28) reproducen los Ejemplos 11-1 a 11-3 del libro; Método 4 (perfil de fuselaje cuadrático, integral numérica) sin validación contra el libro. Ala dada o derivada del punto de diseño de M04. `export` genera JSON SI para M24. No estima estabilidad (D-24). |
| M09a Perfiles | `m09a` | 2D | FUNCIONAL con XFOIL 6.99 real (Windows): analiza NACA 4 dígitos / `.dat` / ZIP UIUC, extrae Cl_max, Cd_min, (L/D)máx, Cm, caída tras Cl_max y puntúa la matriz de la Sec. 8.3.9 (ejemplo de prorrateo del libro reproducido; α_ZL y Cl_α contra teoría de perfil delgado). Sin XFOIL devuelve `pending_engine`. Sin validación experimental; criterios 3, 5 y 7 del libro solo manuales (D-25). |
| M09b Ala | `m09b` | conceptual | FUNCIONAL a nivel conceptual: planta trapezoidal (S, AR, λ, flecha), MGC, C_Lα (Ecs. 9-69/9-71/9-72, Tabla 9-7 reproducida), CL_max0 y V_S (Ejemplo 9-9), e de Raymer, AR_e por alcance (Ejemplo 9-4), volumen/combustible (inconsistencia del Ejemplo 9-3, D-26), guías de AR/λ/diedro/washout y configuración de intercambio para flow5 LLT. flow5 NO ejecutado (pendiente de validación con el motor real). M08 puede leer su planta. |
| M10 Geometría paramétrica (OML) | `m10` | conceptual | FUNCIONAL: ensambla ala (M09b), cola (M08) y fuselaje en `aerosuite-oml/1` (SI, ejes definidos, secciones, contornos NACA opcionales, comprobaciones de validez); recupera V_HT y V_VT de entrada desde las coordenadas. Sin validación numérica contra un ejemplo del libro (invariantes geométricos independientes). No calcula intersecciones ni CAD (M24). |
| M11 Planta motriz y hélice | `m11` | conceptual | FUNCIONAL solo para motor de pistón con hélice: potencia de M04 vs motor del usuario, altitud (Gagg-Ferrar), temperatura, reductor, hélice de madera (diámetro, punta, paso, J, η_p requerida) con los Ejemplos 7-2, 7-3, 15-2 y 15-3 reproducidos. Altitud crítica sin ejemplo; metal/compuesto, turbinas y eléctrico fuera (D-28). Errata de la Ec. 15-30. Contraste con el deck IO-540 de ADRpy. |
| M12 Pesos detallados | `m12` | conceptual | PARCIAL: 14 componentes con las ecuaciones estadísticas de la Sec. 6.4.1 (aluminio, GA): peso de ala validado con el Ejemplo 6-5 y modelo de cabezas de larguero con los Ejemplos 6-6/6-7; el resto transcrito sin ejemplo del libro (Cessna VT sospechosa, excluida por defecto). Pesos conocidos mandan; faltantes se listan y la suma no se declara completa (D-29). Sin piel/alma/costillas ni turbinas. |
| M13 CG, inercias y envolvente | `m13` | conceptual | FUNCIONAL: CG y % c_MGC (Ejemplos 6-8, 6-9), tolerancias (6-10), inercias con ejes paralelos, matriz y momentos principales (validadas con mecánica clásica, el libro no trae ejemplo), pesaje, nube de cargas y caja/polígono de envolvente. Pesos de M12; posiciones de los componentes y límites de CG son datos del usuario (los límites vendrán de M16). |
| M15 Fuselaje | `m15` | conceptual | FUNCIONAL: cabina mínima, nariz y cola de tubo de presión/renacuajo/tronco, cola exigida por M08, ángulo de golpe de cola, rango de CG de referencia y áreas/volúmenes de sólidos (Tabla 12-1 reproducida; errata del tronco, D-31). Escribe `m10_fuselage` para M10. Diseño interior y ergonomía fuera. |
| M16 Estabilidad | `m16` | conceptual | FUNCIONAL: punto neutro, CM_α, margen estático, límites de CG, CN_β/CY_β de cola vertical y fuselaje, matrices de estado de Etkin con autovalores (B747 reproducido, D-35) y Lanchester. Derivadas laterales Cl_p, Cl_r, Cn_p, Cn_r y CL_β como dato de entrada (D-34). Aporte del fuselaje por Munk-Multhopp (F5, D-44; Ejemplo 24-3 reproducido; marca `punto_neutro_optimista` si falta la geometría). Contraste estático con flow5 7.55 real (D-52: la deriva del modelo de flow5 era horizontal; corregida, NP 0.695 m contra 0.703 m, −1.2 %, C_Mα −7.4 %; con fuselaje el incremento de Munk-Multhopp coincide con flow5 TRILINEAR en el punto neutro, −0.072 contra −0.069 m, D-50); modos dinámicos y derivadas laterales contra flow5 pendientes. |
| M18a Tren de aterrizaje | `m18a` | conceptual | FUNCIONAL: reacciones estáticas y dinámicas (Ecs. 13-17 a 13-22; Ejemplos 13-2 y 13-3), reparto nariz/cola, ángulos de vuelco, golpe de cola y vuelco hacia atrás, holgura de hélice, radio de giro, huella de neumático, energía de frenado y velocidad de descenso. Neumático de catálogo como dato (D-37). |
| M18b Controles | `m18b` | conceptual | FUNCIONAL: geometría de superficies móviles (Tabla 24-6), momento de charnela, fuerza en palanca por ganancia, flotación, factor de pendiente de cola y punto neutro con mando libre. C_Hα y C_Hδ son datos de entrada (D-38). |
| M18c Hipersustentación | `m18c` | conceptual / 2D XFOIL | FUNCIONAL: C_Lmax de ala por particion (Ec. 10-2) con incrementos de seccion de la Tabla 10-5 prorrateada, Ec. 10-1, dato directo o XFOIL real con flap (GDES/FLAP). Evidencia en `evidence/xfoil-flaps-win/` (D-39). |
| M19 Pérdida benigna | `m19` | conceptual | FUNCIONAL: línea sustentadora de Prandtl, avance de la pérdida (C_l frente a C_lmax), criterios de la Sec. 9.6.3, estudio de alabeo y límites de cabeceo ascendente. Contraste de C_Lα con flow5 7.55 real; distribución C_l(η) contra flow5 pendiente (D-40). |
| M20 Resistencia por componentes | `m20` | conceptual | FUNCIONAL: acumulación por componentes (C_f mixto de Young / Prandtl-Schlichting, Re de corte, FF, IF, CRUD), aportes diversos como dato, polar C_Dmin + k C_L² y L/D máximo. M16 puede tomar de aquí C_D0. Contraste con flow5 7.55 real (D-41). |
| M21 Prestaciones | `m21` | conceptual | FUNCIONAL: velocidades de pérdida y máxima, ascenso máximo, techos de servicio y absoluto, alcance y autonomía de Breguet de hélice, diagrama carga útil–alcance, despegue y aterrizaje por M04. Ejemplo 21-6 reproducido (D-42). η_p constante; c_P, masas y reservas son datos. |
| M24 Exportación CAD (STEP) | `m24` | conceptual | FUNCIONAL (F5): OML de M10 a STEP en mm con ejes de SolidWorks (X atrás, Y arriba, Z envergadura; D-54), perfiles como splines, ala, colas por loft recto; fuselaje de revolución circular, más contornos XYZ por sección, una pieza por superficie + ensamble + `manifest.json`; reimportado y comparado con M10. Requiere CadQuery (`requirements-cad.txt`, instalado con `--no-deps`, D-49); no abierto en Ansys. |
| M25 Envolvente V-n | `m25` | conceptual | FUNCIONAL (F6): maniobra + ráfaga (Sec. 17.4.1), puntos de esquina, cargas límite y últimas (1.5), V_A/V_G efectivas; reproduce el Ejemplo 17.4.1 (V_A 94.6 KEAS, n_g +4.60/-2.60). Umbrales de utilitaria/acrobática y de V_C/V_D por carga alar de ADRpy 0.2.6 (supuesto). Con flaps solo línea de pérdida. Fuera del lazo L-1 (D-55). |
| M26 Cargas aerodinámicas (Ansys) | `m26` | conceptual | FUNCIONAL (F6): en cada esquina de M25, sustentación n W, resistencia, equilibrio de cabeceo con la cola, distribución en envergadura (línea sustentadora de M19), cortante y flector aerodinámicos; CSV/JSON/manifiesto con ejes del STEP de M24 (mm). Equilibrio verificado; sin ejemplo del libro; contraste con flow5 solo si el C_L coincide. Sin alivio estructural ni archivos de Ansys (D-56). |
| M22 Optimizador multinivel | `m22` / `opt` | conceptual / 2D / 3D | FUNCIONAL (F5): motor `project` sobre el proyecto con L-1; verificado contra malla (DE y SLSQP coinciden con 551 puntos). 3D con flow5 real solo con bandera explícita, tiempo y tope (ala sola). D-48. |
| M23 Verificación de requisitos | `m23` | conceptual | FUNCIONAL (F5): cumple / no cumple / no evaluable con valor, límite, margen y referencia; solo criterios con texto leído (23.2110, 23.2120, 23.2130, Tablas 1-2/1-3, Secs. 24.3.4 y 25.3) y requisitos del proyecto; CS-23 y el Part 23 anterior no leídos (D-47). |
| L-1 Lazo completo (`loop.py`) | `loop` | conceptual | FUNCIONAL (F5): ejecuta M01-M21 (+M23 si existe) en el orden de la Tabla 1-4 con las dependencias de los módulos, guarda cada iteración y se detiene por falta de datos, convergencia o `--max-iter`. Sin regla de actualización de variables de diseño (D-46). Caso `examples/projects/c162-full-loop.json`. |
| M06 Peso inicial y misión | `m06` | conceptual | FUNCIONAL: Método 1 (Ec. 6-9, con razones de M02 opcionales), Método 2 (9 clases, Ecs. 6-16 a 6-24, formas lbf y kg), Método 3 (cadena de fracciones de peso Ecs. 6-32 a 6-42 + Ec. 6-29, empuje fijo o escalado con Ec. 6-30) y eléctrico (Ecs. 6-12/6-13). Reproduce Ejemplos 6-2, 6-3 y 6-4 (W0 = 44 566 lbf vs 44 556; segunda iteración 43 636 vs 43 619). M04 puede leer su W0 (`tow_from_m06`); `project-status` marca M04 desactualizado si M06 cambia. Sin modelo de hélices con datos del libro más allá de η_p y SFC_hp dados. |
