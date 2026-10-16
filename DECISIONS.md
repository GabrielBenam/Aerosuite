# AeroSuite — Decisiones técnicas (DECISIONS)

Formato: ID · fecha · decisión · motivo · consecuencias.

**D-01 · 2026-10-14 · Base de código = versión de GitHub (`Github.zip`) fusionada con la carpeta local.**
Motivo: la carpeta local era el prototipo v0.1/0.2; GitHub contenía `vendor/`, `setup-engines.ps1`, `adrpy_core.py`, `xfoil_cli.py` y la GUI Airfoil Lab. Se copiaron encima los archivos de GitHub; los cuatro archivos locales que cambiaban (`README.md`, `.gitignore`, `aerosuite/__main__.py`, `scripts/demo.ps1`) se respaldaron en `_respaldo_local_20261014/`. Se conservaron `real-naca/`, `real-comparison/` y `results/` locales.

**D-02 · 2026-10-14 · `vendor/flow5` y `vendor/ADRpy` se rellenan con clones exactos de los tags v7.57 y 0.2.6.**
Motivo: el ZIP de GitHub no incluye submódulos. Los SHA coinciden con `.gitmodules`/handoff. Se copió también `.git` para que `aerosuite status` verifique el commit sin ejecutar git. Ningún archivo dentro de `vendor/` fue modificado.

**D-03 · 2026-10-14 · flow5 se automatiza con su propio modo por lotes (`flow5 -s guion.xml`), no con el API C++.**
Motivo: el ejecutable oficial v7.57 lee guiones `xflscript` (flow5-app/modules/script) que cargan perfiles .dat, aviones XML y polares XML, ejecutan los análisis y exportan polares en CSV. No requiere compilar Qt/OCCT/Gmsh/MKL y conserva todas las capacidades. El adaptador C++ `integrations/flow5/xfoilbatch_aerosuite.cpp` queda en pausa (el README de flow5 declara su API experimental hasta fines de 2026).

**D-04 · 2026-10-14 · El optimizador de flow5 no se usa.**
Motivo: el README de flow5 v7.57 lo declara "currently inoperative". flow5 entrará al optimizador solo como motor de evaluación 3D (conexión pendiente C-4).

**D-05 · 2026-10-14 · Barridos XFOIL incompletos ya no descartan todo el perfil.**
Antes: un α no convergido hacía fallar la ejecución completa. Ahora se guardan los puntos convergidos y los faltantes en `missing_alpha`; `converged` sigue significando "barrido completo" (compatibilidad). El comparador exige barrido completo salvo `--allow-partial`. El optimizador 2D sigue exigiéndolo (cuenta la evaluación como fallida).

**D-06 · 2026-10-14 · Punto de diseño conceptual = mínimo T/W con W/S ≤ límite de pérdida limpia.**
Motivo: Gudmundsson Sec. 3.2.3 (PDF p.112) advierte que omitir la pérdida produce un óptimo inválido. Se usa `wsmaxcleanstall_pa` de ADRpy; si faltan `vstallclean_kcas` o `CLmaxclean`, el resultado lo declara.

**D-07 · 2026-10-14 · El alargamiento no se ofrece como variable del optimizador conceptual por defecto.**
Motivo: con solo restricciones ADRpy, aumentar AR siempre reduce el T/W requerido; sin modelo de peso del ala el óptimo cae en el límite superior (comprobado: AR = 12 en el `optimize` heredado). Agregar una penalización inventada violaría las reglas del proyecto. Se reactivará cuando exista un modelo de peso fundamentado (Gudmundsson Cap. 6).

**D-08 · 2026-10-14 · Una evaluación fallida no recibe penalización física.**
En `differential_evolution` recibe objetivo +∞ y queda fuera de la clasificación; se registra con su error en `evaluations.csv`.

**D-09 · 2026-10-14 · Viscosidad del aire con la ley de Sutherland (constantes ICAO) en código AeroSuite.**
Motivo: ADRpy 0.2.6 no ofrece viscosidad y se necesita para Reynolds y para el fluido de las polares flow5. Está etiquetado como código propio en las salidas.

**D-10 · 2026-10-14 · Se mantiene el pin NumPy 1.26.4 de `requirements-core.txt`.**
Comprobación: con NumPy 2.2.6 las pruebas pasan y el `size` de ejemplo da resultados idénticos. Con NumPy 2.5.3 (Python 3.13) ADRpy 0.2.6 falla en `twrequired_to`, `twrequired_clm` y otras (`TypeError: only 0-dimensional arrays can be converted to Python scalars`). El pin se mantiene y Python 3.11 sigue siendo el requisito.

**D-11 · 2026-10-14 · Validación Linux con XFOIL 6.99 de Debian.**
Motivo: el sitio del MIT está bloqueado en el entorno de Claude. El binario Debian (mismo código 6.99) coincide con el binario MIT de Windows dentro de 0.25 % en CL y 0.2 % en CD para la misma geometría (TEST_RESULTS §3.3). Requiere `LD_PRELOAD` para desactivar las trampas FPE de su compilación.

**D-12 · 2026-10-14 · Evidencias en `evidence/`, no en `results/`.**
`results/` está en `.gitignore` y contiene la demo sintética; `evidence/` guarda salidas reales de los motores con su configuración.

**D-13 · 2026-10-14 · Sin GUI nueva.** La GUI Airfoil Lab existente se conserva sin cambios ni validación en esta etapa.

**D-14 · 2026-10-14 · El lector de flow5 (M-F5R) se construye desde el código que escribe los archivos.**
Motivo: aún no hay salidas reales de `flow5 -s`. Los formatos se tomaron de `io::exportAllWPolars`, `PlanePolar::exportToString`, `PlanePolar::s_VariableNames` y `PlaneOpp::exportMainDataToString` (vendor/flow5 v7.57). Particularidades conservadas: valores en unidades de presentación del usuario (se convierten a SI desde la etiqueta), 5 cifras significativas en polares, encabezado "CX" que contiene CD en los puntos de operación, separador doble tras "ctrl" y bloque de masa con encabezado y valores en la misma línea. Se validará contra la primera salida real.

**D-15 · 2026-10-14 · Prioridad de fuentes.**
Gudmundsson confirmado como marco rector. Cuando la sesión tiene acceso a la computadora del usuario, las fuentes primarias de su carpeta BIBLIOGRAFIA tienen prioridad sobre cualquier otra; internet solo para huecos.

**D-16 · 2026-10-14 · Repositorio.**
El trabajo de esta etapa vive en la rama `feat/gudmundsson-base` sobre `main` (commit dfc43b7). `CLAUDE.md` en la raíz fija las reglas para Claude Code.

**D-17 · 2026-10-14 · M01: celdas fusionadas de la Tabla 1-2.**
La conversión a Markdown de la Tabla 1-2 conserva solo dos valores de peso máximo (19 000 y 12 500 lbf) y de ocupantes (19 y 9) para cuatro columnas. Se asigna 19 000/19 a Commuter y 12 500/9 a Normal, Utility y Aerobatic (celdas fusionadas). Alternativa descartada: pedir el dato al usuario (corrida sin preguntas). Los factores de carga de Commuter no se leen de la tabla y M01 informa error en vez de inventarlos. Verificar contra la figura de la tabla en el PDF original.

**D-18 · 2026-10-14 · M02: alcance de la base de referencia.**
M02 incluye solo la base de datos que el libro publica de forma legible (Tabla 6-1, LSA). Las bases de los Caps. 16.6, 18.4, 19.4 y 23.3 que cita ARCHITECTURE §2 no se cargaron: el usuario puede aportar su propia base JSON (formato de `aerosuite/data/`). Un ajuste logarítmico con pesos brutos dentro de 10 % se declara degenerado (los 17 LSA están a 1320 lbf ± 0.4 %: la regresión sería ruido de redondeo). La desviación estándar es muestral (ddof = 1), que reproduce las cifras de la tabla. Alternativa descartada: ajustar de todos modos y mostrar R².

**D-19 · 2026-10-14 · M03: alcance y convenciones.**
(1) Solo el modelo de aeronaves GA de hélice (Secs. 2.2.1 y 2.3.1); los de aviones de negocio (2.2.2, 2.3.2) quedan fuera. (2) Las ecuaciones de hélices (2-25 a 2-30) están garbladas en la conversión digital y no se pudieron comprobar, así que el precio de la hélice y de la aviónica son datos de entrada, igual que el libro los trata en el Ejemplo 2-3 ($14 000 y $35 000). (3) La tasa mensual de producción Q_m = round(N/60), el redondeo que usa el Ejemplo 2-1 (1000/60 → 17). (4) El seguro de fabricante = fracción × precio objetivo (Ejemplo 2-3: 15 % de $350 000) y no entra en el punto de equilibrio, igual que en el libro (366 y 238 aviones). (5) Si el usuario no da tarifas ni CPI, se usan las de junio 2012 del libro y se anotan en `assumptions` de project.json. (6) Costos en USD; la masa de la estructura se convierte de kg a lbf en la frontera. W_airframe ≈ 65 % del peso vacío si no se conoce (GUD PDF 85); M03 no lo infiere: lo pide.

**D-20 · 2026-10-14 · M04: reconstrucción de las Ecs. 3-13/3-14 y alcance.**
La conversión digital de las Ecs. 3-13 y 3-14 pierde signos y agrupaciones. Se reconstruyeron desde el Apéndice D: S_LDG = 19.08·h_obst + 0.007923·(W/S)/A + 1.556·τ·√((W/S)/A) + 1.21·(W/S)/(g·A·[0.605/CLmax·(CD_LDG − μ·CL_LDG) + μ + T_gr/W]), con A = ρ·CLmax (la suma 0.01583 − 0.007907 = 0.007923 de la deducción coincide con el coeficiente impreso). Comprobación: con los datos del Ejemplo 3-1 da 1369.1 ft a 11.37 lbf/ft² y W/S máx. = 11.366 lbf/ft² (libro: 11.37). Las constantes son dimensionales: se evalúa en unidades inglesas y se convierte en la frontera SI. Verificar la forma impresa contra el PDF original (figura de la Ec. 3-13) cuando haya acceso. Alcance: M04 no sustituye las fórmulas de ADRpy (que difieren del libro en despegue, k y techo; ver TEST_RESULTS §2.3): añade el contraste con la Ec. 3-1 en lugar de reemplazar el motor. El peso a mitad de misión no se corrige (el libro tampoco en el Ejemplo 3-1).

**D-21 · 2026-10-14 · M06: lectura de las ecuaciones del Cap. 6 y decisiones de modelo.**
(1) Las Ecs. 6-16 a 6-42 se leyeron del PDF original con `pdftotext -layout` (la conversión Markdown las pierde); los signos ambiguos ("�") se resolvieron con la identidad lbf/kg y con los resultados del Ejemplo 6-4. (2) Hélices: se usan las ecuaciones 6-37/6-38/6-41 del libro con η_p y SFC_hp (lbf/(h·hp)) dados; M06 no estima η_p. (3) Las unidades de las ecuaciones de segmentos son las del libro (nm, KTAS, ft, fpm, SFC en 1/h); los pesos de crew/payload van en kg en project.json y la regresión se usa en su forma kg. (4) Empuje por segmento: `r`/`p` fijo, o `r_ref`/`p_ref` = Tmax/W0 escalado por W0/W_{i−1} (Ec. 6-30). Como W_{i−1}/W0 depende solo de segmentos anteriores, el esquema no requiere la segunda iteración manual del libro: el resultado equivale a ella. (5) Ec. 6-29 se resuelve con búsqueda de signo en [1×, 10⁴×] (Wc+Wp) y brentq; si no hay raíz la misión no cierra y se informa error (no se inventa un peso). (6) Las diferencias con el libro (0.02–0.04 %) provienen de que el libro redondea W_N/W0 a 0.6066 y r a cuatro cifras. (7) La Ec. 6-33 "típica" (1 − 0.015·SFC) se ofrece como `typical: true`; las constantes 0.015/0.004 asumen T/W0 = 0.30, P/W0 = 0.08 hp/lbf y T_idle = 10 % (GUD PDF 200). (8) Método 3 omite la carga de combustible adicional (trapped fuel) porque el libro no la incluye en 6-29. (9) El flujo de dependencias: M04 puede leer M06 (`tow_from_m06`) y M06 puede leer M02 (`ratios_from_m02`); `project-status` informa los módulos desactualizados.

**D-22 · 2026-10-15 · M04: la curva de despegue del punto de diseño es la Ec. 3-1 de Gudmundsson (decisión del usuario).**
Motivo: Gudmundsson es el marco rector; la Ec. 3-1 reproduce el Ejemplo 3-1 (T/W 0.18692 contra 0.1869), mientras que la fórmula de despegue de ADRpy da +6.4 % por usar otra formulación. Ascenso, viraje, crucero, techo y límite de pérdida siguen saliendo de ADRpy; el aterrizaje es Gudmundsson (D-20). Cada resultado declara `fuente` por restricción (`gudmundsson` o `adrpy`) y conserva la curva de ADRpy en `contraste_adrpy` con la diferencia porcentual (media +4.3 % en el Ejemplo 3-1, de +10.1 % a W/S = 239 Pa a +2.2 % a 1676 Pa). Comparación del punto de diseño del Ejemplo 3-1 (límite activo: aterrizaje, 544 Pa): antes W/S 502.74 Pa, T/W 0.2118 (ascenso activo, despegue ADRpy 0.2058); después W/S 526.68 Pa, T/W 0.2113 (ascenso activo, despegue Ec. 3-1 0.2011). Cambia porque la curva de despegue baja respecto de ADRpy y el cruce despegue/ascenso, que fija el mínimo de T/W, se desplaza a mayor W/S. Techo: se mantiene con ADRpy a la altitud del enunciado de M04 (el ejemplo usa 17 000 ft = 5181.6 m); el libro dice 15 000 ft en el enunciado pero evalúa el paso 7 a 17 000 ft: inconsistencia de la fuente, no corregida. Limitaciones: (1) la Ec. 3-1 se evalúa con la densidad de la pista y no se lleva a nivel del mar; con `rwyelevation_m` ≠ 0 el resultado lo advierte en `takeoff_note`; (2) `power_required` de ADRpy sigue usando su formulación de despegue y lo declara. `project-status` marca M04 desactualizado (hash de salida distinto) si cambió M06; los módulos que lean el punto de diseño deberán declarar `depends_on: m04`.

**D-23 · 2026-10-15 · M03: costos en dólares de 2012, sin actualización por inflación (decisión del usuario).**
M03 usa las tarifas por defecto de 2012 de Gudmundsson (Cap. 2). Todo resultado incluye `anio_base: 2012` y `nota_costos` ("Costos en dólares de 2012 ... orden de magnitud relativo, no precio actual"); la CLI imprime el resultado completo y `project-status` repite la nota. Las tarifas y el CPI por defecto siguen en `assumptions`, marcadas como supuesto de 2012. No se inventó ningún factor de inflación; `cpi_2012` sigue siendo dato de entrada opcional (ver ROADMAP).

**D-24 · 2026-10-15 · M08: alcance y convenciones.**
(1) Se implementan los Métodos 1 a 4 de la Sec. 11.4 (Ecs. 11-26 a 11-28, Método 4 con el perfil cuadrático de las Ecs. 11-31/11-33 y la integral numérica de la Ec. 11-35). (2) Los coeficientes V_HT y V_VT vienen de la Tabla 11-4 (leída de la figura del libro, PDF 550) o se dan como dato. La Tabla 11-5 (aeronaves individuales) no se carga. (3) No se implementa la estimación de V_HT desde el punto neutro (Sec. 11.4.2, "V_HT = 3.193 − 3.426·√(1.084 − h_n)"): la conversión digital pierde el signo y solo se comprueba de forma aproximada con el texto (V_HT = 0.70 → h_n ≈ 0.55), sin ejemplo resuelto; por la regla de no inventar ecuaciones queda fuera (podrá entrar con el Cap. 24). (4) Los Métodos 1 y 2 dimensionan solo una cola; la otra usa el mismo brazo y M08 lo advierte. (5) AR_HT = 3.0 y AR_VT = 1.35 por defecto son los de los Ejemplos 11-1/11-2 (Cessna 172), registrados como supuesto cuando no se dan; el libro no fija AR de cola por clase. (6) El intervalo de búsqueda del Método 4 es dato de entrada (`fuselage.search_m`, por defecto 0.25 b a 1.5 b): el libro barre l_T en una hoja de cálculo sin fijar el intervalo; si el óptimo cae en el borde se advierte. (7) S_wet de la cola ≈ 2·S_cola (el libro, Ecs. 11-18/11-19). (8) El ala puede darse directamente (S, b, c_MGC) o derivarse del punto de diseño de M04 (S = W0·g/(W/S), AR y λ dados): en ese caso M08 depende de M04 (y M06) y `project-status` lo marca desactualizado si cambian. (9) Se añade el comando genérico `export --module mXX --out archivo.json` (esquema `aerosuite-export/1`, SI, con marca `stale`) como salida para M24.
