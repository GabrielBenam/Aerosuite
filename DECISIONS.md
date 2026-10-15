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
