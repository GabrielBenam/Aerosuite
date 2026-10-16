# AUTONOMOUS_RUN_F5 — corrida autónoma: corrección de M16, lazo completo, M22, M23 y M24

Este archivo manda sobre cualquier otra instrucción de la corrida, salvo `CLAUDE.md` y las instrucciones maestras del proyecto. Las reglas de autonomía, parada, git, cierre, fuentes y "sin simulaciones falsas" de `AUTONOMOUS_RUN_F4.md` y `AUTONOMOUS_RUN_F3.md` siguen vigentes en lo que no contradiga este archivo; aquí se repiten las esenciales.

## 1. Alcance y orden
Fases F5 (pasos 22-24 de Gudmundsson) más el lazo que las conecta. Orden:

1. **C-1** Corrección de M16: contribución del fuselaje (§2).
2. **C-2** Verificación de las dos validaciones circulares de F4 (§3).
3. **L-1** Lazo completo M01→M21 con registro de iteraciones (§4).
4. **M23** Verificación de requisitos (paso 23; §5).
5. **M22** Optimizador multinivel (paso 22; §6).
6. **M24** Exportación CAD a STEP (paso 24; §7).
7. **V-1** Guía de verificación para el usuario (§8).

Fuera de alcance: V-n (M25), cargas para Ansys (M26), dimensionamiento estructural, CFD, interfaz gráfica. Decisión del usuario ya tomada (no se vuelve a consultar): **no se añade factor de seguridad al margen estático**; se corrige el modelo y no se aplican penalizaciones sin fuente.

## 2. C-1: contribución del fuselaje en M16
Hallazgo de F4: M16 da el punto neutro 5.3 % detrás del de flow5 7.55 (0.695 m contra 0.66 m), margen estático 25.0 % contra 21.6 % y C_Mα −1.227 contra −1.097 1/rad, porque falta el aporte desestabilizante del fuselaje (Munk-Multhopp) y la influencia de la estela sobre la cola puede estar simplificada. El error es del lado inseguro.
1. Localiza el método en Gudmundsson (Cap. 24 y capítulo de estabilidad estática; carpeta `BIBLIOGRAFIA` primero), con Etkin y USAF DATCOM como contraste. Verifica cada ecuación contra un ejemplo resuelto; si una ecuación es ilegible, aplica la regla de reconstrucción (§9).
2. Implementa el aporte del fuselaje a C_Mα y a la posición del punto neutro. Entradas del fuselaje desde M15/M10 (volumen, secciones). Sin valores inventados: lo que falte es dato de entrada marcado como supuesto.
3. Repite el contraste con flow5 7.55 usando la evidencia ya guardada en `evidence/flow5-7.55-win/` (y, si hace falta, una corrida nueva con el mismo caso). Informa las diferencias con cifras antes y después. No ajustes constantes para igualar a flow5; si la diferencia persiste, explica la causa verificable (por ejemplo, el flujo del fuselaje en VLM de flow5) o repórtala sin forzarla.
4. Mientras no exista el aporte del fuselaje en una corrida, la salida de M16 marca `punto_neutro_optimista: true`. Una vez implementado, esa marca desaparece solo si la comparación con flow5 queda dentro de una tolerancia que justifiques con la física y registres en `DECISIONS.md`.
5. Commit: `fix(M16): aporte del fuselaje al punto neutro y contraste con flow5`.

## 3. C-2: validaciones circulares de F4
- **Etkin, Tabla 6.6 (coeficientes laterales del B747):** F4 los usó "porque reproducen los autovalores impresos"; eso no valida los coeficientes. Búscalos en el libro de Etkin dentro de `BIBLIOGRAFIA` (lee el PDF con `pdftotext -layout` o con el texto convertido). Si los encuentras, compáralos con los usados, corrige las diferencias y actualiza la prueba. Si no es posible leerlos, deja en `TEST_RESULTS.md` el texto "validación de los modos laterales: solo comprueba el solucionador de autovalores; los coeficientes no están verificados" y mantenla en el resumen del PR.
- **Ejemplo 13-3 de M18a** (razón de brazos despejada del resultado): intenta localizar la figura/datos en el libro. Si no es posible, etiqueta la validación como "solo aritmética" en `TEST_RESULTS.md` y en el resumen del PR.
- Commit: `docs(F4): validaciones circulares verificadas o declaradas`.

## 4. L-1: lazo completo del algoritmo
Objetivo: ejecutar el algoritmo de la Tabla 1-4 (pasos 1-23) de principio a fin sobre un `project.json`, en el orden y con las dependencias ya implementadas (M01, M02, M03, M04, M06, M08, M09a, M09b, M10, M11, M12, M13, M15, M16, M18a-c, M19, M20, M21), registrando cada iteración.
1. Nuevo módulo `aerosuite/loop.py` y comando `python -m aerosuite loop --project proyecto.json --max-iter N`. Usa el mecanismo existente de dependencias y marca de "desactualizado"; no dupliques lógica de los módulos.
2. Una iteración = una pasada por los módulos desactualizados en el orden de la Tabla 1-4. Cada iteración se guarda con su número, sus entradas, salidas y estado; la corrida es reproducible y no sobrescribe iteraciones anteriores.
3. Criterio de parada: el paso 23 del libro (evaluación contra requisitos, §5) cumple, o se alcanza `--max-iter`, o dos iteraciones consecutivas no cambian las salidas más allá de una tolerancia relativa declarada. El libro no impone la regla de actualización de variables entre iteraciones: no la inventes; el lazo solo recalcula con las entradas del proyecto y deja las actualizaciones de diseño al usuario o al optimizador (M22). Documenta esto en `DECISIONS.md`.
4. Caso de validación: Cessna 162 del Ejemplo 3-1 y los ejemplos del libro que ya reproducen los módulos. Ejecuta el lazo completo con `examples/projects/` y compara con las cifras impresas disponibles (W/S, T/W, pesos, áreas de cola, etc.). Las diferencias se informan con cifras; no son error si se explican (supuestos de entrada).
5. Falta de datos: si un módulo necesita un dato que el proyecto no tiene, el lazo se detiene en ese módulo con un mensaje claro y la lista de claves faltantes (nunca rellena con supuestos silenciosos).
6. Comando de ejemplo documentado y prueba de integración. Commit: `feat(L-1): lazo completo del algoritmo de Gudmundsson`.

## 5. M23: verificación de requisitos (paso 23)
1. Entrada: requisitos y base regulatoria de M01 (Tablas 1-2/1-3) más los resultados de los módulos de F2-F4.
2. Salida: para cada requisito, estado `cumple`, `no cumple` o `no evaluable`, con el valor calculado, el límite, el margen y la referencia (norma y apartado, o página del libro).
3. Implementa solo verificaciones cuyo texto normativo hayas leído y citado: eCFR 14 CFR Part 23 (público; puedes consultarlo en internet), EASA CS-23 si es accesible, y lo que traiga Gudmundsson (Cap. 3 y tablas de la Sec. 1.3). Ejemplos esperables: velocidad de pérdida (23.49), distancias de despegue y aterrizaje, gradientes de ascenso, estabilidad estática, límites de carga y de CG declarados. Todo criterio sin texto verificado queda `no evaluable` con la razón; no inventes umbrales.
4. Comando `m23`, exportación `export --module m23`, pruebas con casos construidos a partir de valores del libro y casos límite (justo en el umbral, un poco por debajo y por encima). Commit: `feat(M23): verificación de requisitos con referencias normativas`.

## 6. M22: optimizador multinivel (paso 22)
1. Reutiliza el contrato de `aerosuite/optimizer.py` (especificación JSON con variables, objetivos, restricciones, método; evaluaciones fallidas = objetivo infinito, sin penalizaciones físicas inventadas; `optimization.json` y `evaluations.csv`). No dupliques: añade un motor `project` que evalúa un `project.json` mediante los módulos y el lazo (L-1).
2. Niveles declarados en cada resultado: `conceptual` (módulos del libro y ADRpy), `2D` (XFOIL real) y `3D` (flow5 real, solo si el usuario lo pide con una bandera explícita, con tiempo máximo por evaluación y con límite de evaluaciones por defecto bajo). Un resultado conceptual no se presenta como optimización aerodinámica 3D.
3. Distingue siempre objetivos, restricciones, variables de decisión, convergencia y viabilidad física (por ejemplo, W/S bajo el límite de pérdida y el de aterrizaje; CG dentro de límites; verificación M23).
4. Validación numérica: un problema pequeño con óptimo conocido o verificable por barrido de malla (por ejemplo, minimizar T/W en el cruce de restricciones de M04, ya conocido, o un problema de peso inicial de M06). Compara el resultado de `differential_evolution` y `SLSQP` con el barrido y registra las diferencias.
5. Comando `m22` / `opt --spec` con ejemplos en `examples/`, y pruebas. Commit: `feat(M22): optimizador multinivel sobre el proyecto`.

## 7. M24: exportación CAD (STEP) (paso 24)
Objetivo del usuario: lo conceptual se exporta a CAD para enviarlo luego a Ansys. Solo geometría exterior (OML); sin estructura.
1. **Instalación autorizada para esta tarea:** CadQuery (con su motor OCP/OpenCASCADE), solo desde PyPI, dentro de `.venv`. Crea `requirements-cad.txt` con la versión exacta instalada (la estable más reciente disponible para Python 3.11 en Windows), registra el resultado de `pip install` y la versión en `TEST_RESULTS.md`. El núcleo de AeroSuite no depende de CadQuery: se importa de forma diferida en M24 y, si falta, el módulo da un error claro con la instrucción de instalación; las pruebas de M24 se omiten sin CadQuery. No instales nada más fuera de `requirements-core.txt` y `requirements-cad.txt`.
2. Entrada: el esquema `aerosuite-oml/1` de M10 (ala, cola, fuselaje, con ejes y unidades). Perfiles: coordenadas de M09a/UIUC/generador NACA (cierra el borde de salida según la opción declarada). Unidades de salida: milímetros (convención de STEP), declaradas en el archivo de manifiesto junto con el sistema de ejes.
3. Geometría: ala y colas por loft de secciones con cuerda, torsión, diedro y flecha tal como los define M10; fuselaje por loft de secciones. Una pieza por superficie y un ensamble con nombres claros, sin agregar elementos no definidos en M10.
4. Salidas: `cad/<proyecto>/<proyecto>.step` (ensamble), un STEP por componente, y `cad/<proyecto>/manifest.json` con versiones, unidades, ejes, origen del archivo de proyecto y SHA-256. Marca de "desactualizado" frente a M10.
5. Validación: reimporta el STEP y compara con los invariantes de M10 (área en planta del ala y de las colas, volumen del ala, volumen del fuselaje, envergadura y caja envolvente) con tolerancias declaradas; informa cifras. Si un perfil o sección no genera un sólido válido, el error debe identificar el componente.
6. Comando `m24` y `export --module m24`. Un ejemplo pequeño (el avión tipo C172 de `examples/projects/oml-c172-like.json`) se guarda en `examples/cad/`, solo si pesa poco; los STEP grandes no entran a git.
7. Commit: `feat(M24): exportación STEP de la geometría exterior con CadQuery`.

## 8. V-1: guía de verificación para el usuario
El usuario quiere, al final, verificar solo ciertos elementos. Crea `VERIFICAR.md` en la raíz con: (a) qué módulos están validados contra el libro con cifras, cuáles solo con aritmética, cuáles contra flow5/XFOIL reales y cuáles sin validación; (b) por módulo, las 1 a 3 comprobaciones que el usuario debe hacer en su ejemplar de los libros (ecuación, página impresa, cifra esperada) y el comando que reproduce el cálculo; (c) la lista consolidada de supuestos de proyecto y de erratas del libro detectadas; (d) los pasos para reproducir todo en Windows (`VALIDAR-WINDOWS.cmd`, `python -m aerosuite validate`, `loop`). Escríbelo en español, sin jerga innecesaria, con comandos exactos. Commit: `docs: guía de verificación del usuario`.

## 9. Reglas especiales (heredadas)
- **Ecuaciones ilegibles** (signos o agrupaciones perdidos en la conversión): reconstrúyelas desde la deducción del libro y verifícalas con un ejemplo resuelto; si no se puede, dato de entrada marcado como supuesto. Nunca inventes una ecuación.
- **Fuentes, en orden:** carpeta `BIBLIOGRAFIA` local, libros del proyecto, fuentes públicas verificables.
- **Costos:** cualquier resultado con costo lleva la nota de 2012 (D-23).
- **flow5 y XFOIL:** rutas ya configuradas (`AEROSUITE_FLOW5`, `AEROSUITE_XFOIL`); el flow5 instalado es 7.55 (el código fuente es 7.57). Tiempo máximo de 300 s por corrida; no toques su instalación. Con la sesión de Windows bloqueada flow5 puede fallar; registra el síntoma exacto sin interpretarlo como fallo del motor.
- No modifiques `vendor/`. No inventes penalizaciones físicas ni criterios de ingeniería.

## 10. Autonomía y parada
Nadie responde durante la corrida: no hagas preguntas. Ante una duda técnica elige la opción más simple que respete a Gudmundsson y a las fuentes primarias, regístrala en `DECISIONS.md` (continúa la numeración desde la última D-xx; la última conocida es D-43) y sigue. Detén una tarea, anótala BLOQUEADA y pasa a la siguiente solo si: requiere modificar `vendor/`, borrar archivos validados o reescribir historia de git; la ecuación necesaria no se puede comprobar en ninguna fuente y no hay dato de entrada posible; o una prueba falla tres intentos seguidos por la misma causa. Si CadQuery no se puede instalar tras probar la versión estable más reciente y una anterior compatible, marca M24 BLOQUEADO con el registro del error; implementa la geometría paramétrica sin CAD (puntos de sección) solo si cabe en una exportación intermedia declarada como tal.

## 11. Git
- Rama de trabajo: `auto/f5`. Antes de crearla ejecuta `git fetch` y `gh pr list --head auto/f4 --state all --json number,state`:
  - si el PR de `auto/f4` está `MERGED`, crea `auto/f5` desde `origin/main`;
  - si no, crea `auto/f5` desde `auto/f4` (el PR final incluirá esos commits y lo dirás en su descripción).
  Si `auto/f5` ya existe, continúa en ella.
- Los cambios sin confirmar de `AUTONOMOUS_RUN_F5.md` e `INICIAR-AUTONOMO.cmd` van en el primer commit: `chore: plan de la corrida F5`. Añade `PR_*.md` al `.gitignore` (no se versionan) y no incluyas `PR_F4.md`. `tools/` sigue ignorado.
- Un commit por tarea y `git push` de la rama tras cada commit. Nunca `--force`, nunca a `main`, nunca fusiones el PR.
- Si `git push` falla por credenciales, usa `gh auth git-credential` como ayudante de una sola ejecución, sin cambiar la configuración global.
- Tras cada tarea actualiza `PROJECT_STATE.md`, `TEST_RESULTS.md`, `DECISIONS.md`, `CLAUDE_HANDOFF.md` y `ROADMAP.md`. Usa `.venv\Scripts\python` para Python y ejecuta toda la suite antes de cada commit.

## 12. Bitácora de la corrida
La corrida puede reiniciarse varias veces. Al empezar, lee esta sección y retoma donde quedó. Al terminar cada tarea o al detenerte añade una línea:
`- AAAA-MM-DD HH:MM | tarea | TERMINADO / EN CURSO / BLOQUEADO | commit | nota breve`

- 2026-10-16 05:48 | C-1 | TERMINADO | 1da3531 | Munk-Multhopp verificado con Ej. 24-3; flow5 sin fuselaje: diferencia de D-43 permanece (D-44)
- 2026-10-16 05:49 | C-2 | TERMINADO | e0d5eea | Tabla 6.6 de Etkin verificada en imagen; Ej. 13-3 con brazos impresos y caso dinámico (D-45)
- 2026-10-16 05:55 | L-1 | TERMINADO | 98310e8 | loop.py + comando loop + c162-full-loop.json; cifras Ej. 3-1 (D-46)
<!-- BITACORA -->

## 13. Cierre (dispara el correo)
Cuando todas las tareas de §1 estén TERMINADAS o BLOQUEADAS:
1. Push final de `auto/f5`.
2. Escribe `PR_F5.md` (no se versiona) con: qué se implementó, qué se validó con cifras contra el libro, qué se validó con flow5 y XFOIL reales, resultado del contraste de M16 antes y después, qué quedó como supuesto, qué quedó pendiente y la lista de elementos que el usuario debe verificar (apunta a `VERIFICAR.md`).
3. `gh pr create --base main --head auto/f5 --title "[FASE COMPLETA] F5: M16 corregido, lazo, M22-M24" --body-file PR_F5.md`. Si todo lo pendiente quedó BLOQUEADO, el título es `[BLOQUEADO] F5`.
4. Crea el archivo `FASE_COMPLETA.flag` en la raíz (ignorado por git).
