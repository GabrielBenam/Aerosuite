# AUTONOMOUS_RUN_F4 — corrida autónoma: validación con flow5 real y fase F4

Este archivo manda sobre cualquier otra instrucción de la corrida, salvo `CLAUDE.md` y las instrucciones maestras del proyecto. Las reglas de autonomía, parada, git, cierre y fuentes de `AUTONOMOUS_RUN_F3.md` siguen vigentes en lo que no contradiga este archivo; aquí se repiten las esenciales.

## 1. Alcance
Fase F4 de Gudmundsson (pasos 16 a 21), precedida por una validación del lector de resultados de flow5 con el motor real. Orden:

0. **Validación flow5 real (V-F5)** (§2).
1. **M16** Estabilidad estática y dinámica (pasos 16-17; flow5 polar tipo 7 y derivadas de estabilidad leídas con M-F5R; Caps. 24-25 de Gudmundsson; Etkin para contraste).
2. **M18a** Tren de aterrizaje (paso 18; Cap. 13).
3. **M18b** Controles (paso 18; Sec. 24.4).
4. **M18c** Hipersustentación y flaps (paso 18; Cap. 10; XFOIL).
5. **M19** Pérdida benigna en envergadura (paso 19; flow5 LLT/VLM y XFOIL; Sec. 9.6).
6. **M20** Resistencia por componentes (paso 20; Cap. 16; CDi de flow5 como contraste).
7. **M21** Prestaciones y carga útil-alcance (paso 21; Caps. 17-23; ADRpy solo lo que exista en la versión instalada).

Las secciones y capítulos de esta lista vienen de `ARCHITECTURE.md` §2 y no están comprobados: verifícalos en el libro antes de usarlos y corrige `BIBLIOGRAPHY_MAP.md` si difieren (como ocurrió en D-31). Fuera de alcance: trayectorias de carga y sistemas de control (paso 18, van a Ansys), CAD (M24), optimizador (M22).

## 2. Tarea 0: validación con flow5 real (V-F5)
Estado verificado por el usuario: `python -m aerosuite status` encuentra flow5 en `C:\Users\oscar\Documents\flow5_v7.55_win64\flow5_v7.55_win64\flow5.exe` (variable `AEROSUITE_FLOW5`) y XFOIL en `tools\xfoil\xfoil.exe`. **El ejecutable instalado es flow5 v7.55; el código fuente de `vendor/flow5` y el lector M-F5R están basados en v7.57.** Es la primera vez que se ejecuta flow5 real con AeroSuite.

1. Registra en `TEST_RESULTS.md` la versión instalada de flow5 (ruta, tamaño y SHA-256 del ejecutable; la versión que muestre `flow5.exe` si existe una opción para imprimirla) y la diferencia 7.55 contra 7.57.
2. Ejecuta `python -m aerosuite flow5-export` con `examples/flow5-c162-like.json` y después `flow5-run` con tiempo máximo de 300 s por corrida. Si flow5 abre una ventana o se queda esperando, termina el proceso al agotar el tiempo, registra qué observaste y prueba las variantes de línea de comandos documentadas en `vendor/flow5` (por ejemplo `-s guion.xml -p`). No toques la instalación de flow5 ni `vendor/`.
3. Guarda las salidas reales (CSV/TXT de polares y puntos de operación, bitácora de flow5, XML de entrada) en `evidence/flow5-7.55-win/` con el comando exacto, la fecha y la versión. No incluyas el ejecutable ni sus DLL. Estas salidas son resultados del solucionador real; rotúlalas así y no las mezcles con los fixtures de formato de `tests/test_flow5_results.py`.
4. Pasa `flow5-results` sobre esas salidas. Cada diferencia entre lo que escribe flow5 7.55 y lo que espera `aerosuite/flow5_results.py` se corrige en el lector (tolerante a ambas versiones), con una prueba de regresión que use un archivo real de `evidence/`. Registra cada ajuste en `DECISIONS.md`.
5. Comprueba física básica con las salidas reales: pendiente de sustentación frente a la teoría de ala finita del libro (Cap. 9), CD frente a CD0 + k·CL², signo de Cm-alfa, punto neutro razonable. Informa las diferencias con cifras; no ajustes el lector para "hacer coincidir" resultados.
6. Si flow5 no se puede ejecutar en modo por lotes después de probar las variantes razonables, marca V-F5 como BLOQUEADO con la evidencia del intento y construye M16, M19 y M20 con métodos del libro, con la validación contra flow5 declarada pendiente.
7. Commit: `feat(M-F5R): validación con flow5 7.55 real`.

## 3. Criterio de módulo terminado
Igual que en la corrida F3 (§4 y §5 de `AUTONOMOUS_RUN_F3.md`), y además:
- Donde el módulo use resultados de flow5 o XFOIL, la corrida debe haber ejecutado el solucionador real y conservado la evidencia en `evidence/`. Si no pudo, declara el módulo "pendiente de validación con el motor real".
- Cada módulo escribe en `project.json` con unidades SI y marca de "desactualizado" para sus dependencias: M04, M09b, M10, M12 y M13 alimentan a M16, M19, M20 y M21.
- Un comando de exportación por módulo con `export --module mXX --out archivo.json`.
- Un commit por módulo: `feat(Mxx): ...`.
- Costos: si algún resultado muestra un costo, lleva la nota de 2012 (D-23).

## 4. Reglas especiales
- **Sin simulaciones falsas.** Ningún dato sintético se presenta como resultado aerodinámico.
- **Ecuaciones ilegibles:** reconstrúyelas desde la deducción del libro y verifícalas con un ejemplo resuelto (como en D-20); si no se puede, dato de entrada marcado como supuesto.
- **No inventes** penalizaciones físicas ni criterios no definidos en la fuente.
- **Fuentes, en orden:** carpeta `BIBLIOGRAFIA` local, libros del proyecto, fuentes públicas verificables (USAF DATCOM, NACA/NTRS, 14 CFR Part 23, EASA CS-23).
- **Ejecución sin supervisión:** flow5 es una aplicación con interfaz. Si el equipo tiene la sesión bloqueada y flow5 falla por eso, registra el síntoma exacto; no lo interpretes como un fallo del motor.
- Pendientes heredados (se implementan con dato de entrada marcado como supuesto si hacen falta): factores de carga de Commuter (D-17), bases de datos de M02 de los Caps. 16, 18, 19 y 23, ecuaciones de hélices de M03 y las erratas del libro listadas en el PR de F3.

## 5. Autonomía y parada
Nadie responde durante la corrida: no hagas preguntas. Ante una duda técnica elige la opción más simple que respete a Gudmundsson y a las fuentes primarias, regístrala en `DECISIONS.md` (continúa la numeración desde la última D-xx) y sigue. Detén un módulo, anótalo BLOQUEADO y pasa al siguiente solo si: requiere modificar `vendor/`, borrar archivos validados o reescribir historia de git; la ecuación necesaria no se puede comprobar en ninguna fuente y no hay dato de entrada posible; o una prueba falla tres intentos seguidos por la misma causa.

## 6. Git
- Rama de trabajo: `auto/f4`. Antes de crearla ejecuta `git fetch` y `gh pr list --head auto/f3 --state all --json number,state`:
  - si el PR de `auto/f3` está `MERGED`, crea `auto/f4` desde `origin/main`;
  - si no, crea `auto/f4` desde `auto/f3` (el PR final incluirá esos commits y lo dirás en su descripción).
  Si `auto/f4` ya existe, continúa en ella.
- Los cambios sin confirmar de `AUTONOMOUS_RUN_F4.md` e `INICIAR-AUTONOMO.cmd` van en el primer commit: `chore: plan de la corrida F4`. Añade `evidence/` solo con archivos de salida (no ejecutables) y mantén `tools/` ignorado.
- Un commit por tarea y `git push` de la rama tras cada commit. Nunca `--force`, nunca a `main`, nunca fusiones el PR.
- Si `git push` falla por credenciales, usa `gh auth git-credential` como ayudante de una sola ejecución, sin cambiar la configuración global.
- Tras cada módulo actualiza `PROJECT_STATE.md`, `TEST_RESULTS.md`, `DECISIONS.md`, `CLAUDE_HANDOFF.md` y `ROADMAP.md`. Usa `.venv\Scripts\python` para Python.

## 7. Bitácora de la corrida
La corrida puede reiniciarse varias veces. Al empezar, lee esta sección y retoma donde quedó. Al terminar cada tarea o al detenerte añade una línea:
`- AAAA-MM-DD HH:MM | tarea | TERMINADO / EN CURSO / BLOQUEADO | commit | nota breve`

<!-- BITACORA -->

## 8. Cierre (dispara el correo)
Cuando todas las tareas de §1 estén TERMINADAS o BLOQUEADAS:
1. Push final de `auto/f4`.
2. Escribe `PR_F4.md` (no lo incluyas en git) con: qué se implementó, qué se validó con cifras contra el libro, qué se validó con flow5 y XFOIL reales (con la versión 7.55 declarada), qué quedó como supuesto, qué quedó pendiente y la lista de elementos que el usuario debe verificar.
3. `gh pr create --base main --head auto/f4 --title "[FASE COMPLETA] V-F5 + F4: M16-M21" --body-file PR_F4.md`. Si todo lo pendiente quedó BLOQUEADO, el título es `[BLOQUEADO] V-F5 + F4`.
4. Crea el archivo `FASE_COMPLETA.flag` en la raíz (ignorado por git).
