# AUTONOMOUS_RUN_F3 — corrida autónoma: cierre de F2 y fase F3

Este archivo manda sobre cualquier otra instrucción de la corrida, salvo `CLAUDE.md` y las instrucciones maestras del proyecto. Las reglas de autonomía, parada, git y cierre de `AUTONOMOUS_RUN.md` (corrida F1-F2) siguen vigentes en lo que no contradiga este archivo; aquí se repiten las esenciales.

## 1. Alcance
La corrida F1-F2 terminó solo M01, M02, M03, M04 y M06. Los pasos 8 y 9 de Gudmundsson (cola y planta alar/perfil) quedaron pendientes y F3 depende de ellos, de modo que esta corrida cubre el cierre de F2 y la fase F3 (pasos 10 a 15), en este orden:

0. **Ajustes previos** (§2 y §3): M04 con despegue de Gudmundsson como resultado principal, y nota de costos 2012 en M03.
1. **M08** Cola inicial (paso 8; Sec. 11.4: coeficientes de volumen VHT y VVT, brazos y áreas).
2. **M09a** Perfiles (paso 9; XFOIL + biblioteca UIUC + generador NACA; criterios de Cap. 8 y matriz de decisión).
3. **M09b** Ala (paso 9; Sec. 8.3.9 y Cap. 9: planta alar, alargamiento, estrechamiento, torsión, diedro; nivel conceptual con relaciones del libro; flow5 LLT solo por archivos de intercambio).
4. **M10** Geometría paramétrica (OML) (paso 10; Cap. 4; Sóbester Caps. 2-4): ensambla ala, cola y fuselaje en una geometría única dentro de `project.json`, con unidades SI y orientación definida.
5. **M11** Planta motriz y hélice (paso 11; Caps. 7, 14, 15; ADRpy `propulsion` solo lo que exista en la versión instalada).
6. **M12** Pesos detallados (paso 12; Sec. 6.3-6.5).
7. **M13** CG, inercias y envolvente de CG (pasos 13-14; Sec. 6.6-6.7).
8. **M15** Fuselaje (paso 15; Sec. 12.3).

Las secciones y capítulos de esta lista vienen de `ARCHITECTURE.md` §2 y no están comprobados: verifícalos en el libro antes de usarlos y corrige la lista en `BIBLIOGRAPHY_MAP.md` si difieren. Si un número de módulo o paso de `ARCHITECTURE.md` difiere de esta lista, manda `ARCHITECTURE.md`; regístralo en `DECISIONS.md`.

## 2. Ajuste previo A: M04, resultado principal = despegue de Gudmundsson (decisión D-22, ya tomada)
Decisión del usuario, no se vuelve a consultar. Motivos: Gudmundsson es el marco rector; la Ec. 3-1 reproduce el Ejemplo 3-1 (T/W 0.18692 contra 0.1869), mientras que la fórmula de despegue de ADRpy da +6.4 % por usar otra formulación; ADRpy queda como motor de apoyo y contraste.

Implementar en `aerosuite/m04_constraints.py`, sin tocar `vendor/`:
- La curva de despegue que define el punto de diseño es la Ec. 3-1 del libro. Ascenso, viraje, crucero y techo siguen saliendo de ADRpy (dentro de 1 % a 3 % del libro), junto con el límite de pérdida y el de aterrizaje (Ecs. 3-13/3-14).
- La curva de despegue de ADRpy se conserva en el resultado como `contraste_adrpy`, con la diferencia porcentual contra la Ec. 3-1.
- El techo se mantiene con ADRpy a la altitud del enunciado: el libro lo evalúa a 17 000 ft aunque el enunciado dice 15 000 ft; registra esa diferencia en `DECISIONS.md`.
- Cada resultado de M04 declara qué curva viene de cuál fuente (`fuente` por restricción: `gudmundsson` o `adrpy`).
- Actualizar pruebas: el Ejemplo 3-1 debe seguir reproduciendo 0.1869 y 11.366 lbf/ft²; el punto de diseño cambia y se documenta con cifras. Si M06 o cualquier módulo lee el punto de diseño, `project-status` debe marcar lo dependiente como desactualizado.
- Registrar en `DECISIONS.md` como D-22, con la comparación numérica antes y después. Commit propio: `feat(M04): despegue Ec. 3-1 como resultado principal, ADRpy como contraste`.

## 3. Ajuste previo B: costos de 2012 (decisión D-23, ya tomada)
Decisión del usuario: M03 usa las tarifas de 2012 y no se actualizan por inflación ni se sustituyen por valores de otro año. Implementar:
- Todo resultado de M03 incluye `nota_costos` con este sentido: "Costos en dólares de 2012 (tarifas por defecto de Gudmundsson, Cap. 2); no están actualizados por inflación. Interpretar como orden de magnitud relativo, no como precio actual." y el año base `2012`.
- La CLI, el resumen de proyecto y cualquier reporte que muestre un costo de M03 repiten esa nota.
- Las tarifas por defecto siguen en `assumptions`, marcadas como supuesto de 2012.
- No inventes un factor de inflación. Si el usuario quiere uno, será un dato de entrada opcional futuro; anótalo en `ROADMAP.md`.
- Registrar en `DECISIONS.md` como D-23. Commit propio: `docs(M03): nota de costos base 2012`.

## 4. Criterio de módulo terminado
Igual que en la corrida F1-F2, y además:
1. Código en `aerosuite/` (sin tocar `vendor/`), comando CLI en `python -m aerosuite`, lectura y escritura en `project.json` con unidades SI y las dependencias marcadas para la marca de "desactualizado".
2. Ecuaciones con fuente comprobada (autor, obra, capítulo, página impresa) en `BIBLIOGRAPHY_MAP.md`. Prioridad de fuentes: carpeta `BIBLIOGRAFIA` local (prioridad 1), libros del proyecto, fuentes públicas verificables (USAF DATCOM, NACA/NTRS, 14 CFR Part 23, EASA CS-23).
3. Pruebas en `tests/` y al menos una validación numérica contra un ejemplo resuelto del libro. Si el libro no tiene ejemplo resuelto para el módulo, valida contra una segunda fuente independiente y dilo en `TEST_RESULTS.md`; si no existe ninguna, marca el módulo como "sin validación numérica".
4. `python -m unittest discover -s tests -v` en verde y `python -m aerosuite validate` sin regresiones.
5. Un commit por módulo: `feat(Mxx): ...`.
6. Un comando por módulo que exporte su geometría o resultado de forma que M24 (CAD) pueda leerlo después (JSON con unidades SI). No construyas M24 en esta corrida.

## 5. Reglas especiales de esta corrida
- **Sin simulaciones falsas.** Si un módulo necesita XFOIL o flow5 y el ejecutable no está disponible, implementa el módulo con los métodos del libro, deja la ejecución del solucionador como "pendiente de validación con el motor real" y no presentes datos sintéticos como resultado aerodinámico.
- **XFOIL en Windows.** Si `python -m aerosuite status` no encuentra XFOIL, puedes descargar solo el binario oficial XFOIL 6.99 de `https://web.mit.edu/drela/Public/web/xfoil/XFOIL6.99.zip` (la misma fuente de la integración continua) en `tools/xfoil/` (añádelo a `.gitignore`), registrar su SHA-256 en `TEST_RESULTS.md` y usarlo con `AEROSUITE_XFOIL`. No descargues nada más de internet que no sea documentación pública o paquetes de `requirements-core.txt`.
- **flow5.** Úsalo solo si `flow5.exe` está instalado. Si no, genera y valida los archivos de intercambio (`flow5-export`) y deja la corrida del ejecutable como pendiente.
- **Ecuaciones ilegibles** en las conversiones digitales (signos y agrupaciones perdidos): reconstrúyelas desde la deducción del libro y verifica contra un ejemplo resuelto, como en D-20. Si no se puede verificar, el valor pasa a ser dato de entrada marcado como supuesto; nunca inventes una ecuación.
- **No inventes penalizaciones físicas** ni criterios de ingeniería no definidos en la fuente.
- Los factores de carga de Commuter (D-17), las bases de datos de los Caps. 16, 18, 19 y 23 de M02 y las ecuaciones de hélice de M03 siguen pendientes: si un módulo de esta corrida las necesita, impleméntalo con dato de entrada marcado como supuesto.

## 6. Autonomía y parada
Nadie responde durante la corrida. No hagas preguntas. Ante una duda técnica elige la opción más simple que respete a Gudmundsson y las fuentes primarias, regístrala en `DECISIONS.md` (D-24 en adelante) y sigue. Detén un módulo, anótalo BLOQUEADO y pasa al siguiente solo si: requiere modificar `vendor/`, borrar archivos validados o reescribir historia de git; la ecuación necesaria no se puede comprobar en ninguna fuente y no hay dato de entrada posible; o una prueba falla tres intentos seguidos por la misma causa.

## 7. Git
- Rama de trabajo: `auto/f3`. Antes de crearla ejecuta `git fetch` y `gh pr view 10 --json state -q .state`:
  - si el PR #10 está `MERGED`, crea `auto/f3` desde `origin/main`;
  - si no, crea `auto/f3` desde `auto/f1-f2` (el PR final incluirá esos commits y lo dirás en su descripción).
  Si `auto/f3` ya existe, continúa en ella.
- Los cambios sin confirmar de `AUTONOMOUS_RUN_F3.md` e `INICIAR-AUTONOMO.cmd` van en el primer commit de la rama: `chore: plan de la corrida F3`.
- Un commit por módulo y un `git push` de la rama tras cada commit. Nunca `--force`, nunca a `main`, nunca fusiones el PR.
- Si `git push` falla por credenciales, usa `gh auth git-credential` como ayudante de una sola ejecución, sin cambiar la configuración global.
- Si ves un archivo `.lock` huérfano dentro de `.git` y ningún git en ejecución, renómbralo, no lo borres en masa.
- Tras cada módulo actualiza `PROJECT_STATE.md`, `TEST_RESULTS.md`, `DECISIONS.md`, `CLAUDE_HANDOFF.md` y `ROADMAP.md`. Usa `.venv\Scripts\python` para Python.

## 8. Bitácora de la corrida
La corrida puede reiniciarse varias veces. Al empezar, lee esta sección y retoma donde quedó. Al terminar cada paso o al detenerte añade una línea:
`- AAAA-MM-DD HH:MM | Mxx | TERMINADO / EN CURSO / BLOQUEADO | commit | nota breve`

<!-- BITACORA -->
- 2026-10-15 | Ajuste A (D-22) | TERMINADO | feat(M04) | despegue Ec. 3-1 principal; punto de diseño 526.7 Pa / T/W 0.2113
- 2026-10-15 | Ajuste B (D-23) | TERMINADO | 589d478 | nota_costos 2012 en M03 y project-status

## 9. Cierre (dispara el correo)
Cuando todos los pasos de §1 estén TERMINADOS o BLOQUEADOS:
1. Push final de `auto/f3`.
2. Escribe `PR_F3.md` (no lo incluyas en git) con: qué se implementó, qué se validó con cifras contra el libro, qué quedó como supuesto, qué quedó pendiente de validación con el motor real (XFOIL o flow5) y la lista de elementos que el usuario debe verificar (incluye las decisiones D-22 y D-23 y cualquier ecuación reconstruida).
3. `gh pr create --base main --head auto/f3 --title "[FASE COMPLETA] F2-resto + F3: M08-M15" --body-file PR_F3.md`. Si todo lo pendiente quedó BLOQUEADO, usa el título `[BLOQUEADO] F2-resto + F3`.
4. Crea el archivo `FASE_COMPLETA.flag` en la raíz (ignorado por git).
