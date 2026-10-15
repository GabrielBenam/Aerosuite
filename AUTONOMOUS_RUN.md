# AUTONOMOUS_RUN — corrida autónoma de Claude Code

Este archivo manda sobre cualquier otra instrucción de la corrida, salvo `CLAUDE.md` y las instrucciones maestras del proyecto, que siguen vigentes.

## 1. Fase seleccionada
- Fase: **F1 + F2** del algoritmo de Gudmundsson (Tabla 1-4, pasos 1 a 9).
- Módulos objetivo, en este orden: M01 Requisitos, M02 Referencias, M03 Costos, M04 Restricciones (incluye aterrizaje Ec. 3-13/3-14, App. D), M06 Peso inicial.
- Si la asignación paso→módulo de `ARCHITECTURE.md` §2 difiere de esta lista, manda `ARCHITECTURE.md`; regístralo en `DECISIONS.md`.

## 2. Criterio de "fase terminada"
Cada módulo cuenta como terminado solo si cumple todo lo siguiente:
1. Código en `aerosuite/` (sin tocar `vendor/`), comando CLI en `python -m aerosuite`, lectura/escritura en `project.json`.
2. Ecuaciones con fuente comprobada (autor, obra, capítulo, página impresa) registrada en `BIBLIOGRAPHY_MAP.md`.
3. Pruebas en `tests/` y al menos una validación numérica contra un ejemplo resuelto del libro (M04: Gudmundsson Ex. 3-1 y verificación de aterrizaje; tolerancias documentadas en `TEST_RESULTS.md`).
4. `python -m unittest discover -s tests -v` en verde y `python -m aerosuite validate` sin regresiones.
5. Commit propio con mensaje `feat(Mxx): ...`.

La fase termina cuando los cinco módulos cumplen lo anterior, o cuando quedan bloqueados según §4 y el resto está terminado.

## 3. Autonomía: decide sin preguntar
Nadie va a responder durante la corrida. No uses preguntas al usuario. Ante una duda técnica:
- Elige la opción más simple que respete Gudmundsson y las fuentes primarias de `C:\Users\oscar\Desktop\ESPACIO COWORK\Aerosuite-main\BIBLIOGRAFIA` (prioridad 1), luego libros del proyecto, luego fuentes públicas verificables.
- Registra la decisión en `DECISIONS.md` (D-xx, motivo, alternativa descartada) y sigue.
- Si un dato de entrada no existe en ninguna fuente, usa un valor marcado como `supuesto` en el JSON y en `DECISIONS.md`; nunca lo presentes como resultado.

## 4. Cuándo detenerte (y solo entonces)
Detén ese módulo, anótalo como BLOQUEADO en la bitácora (§6) y pasa al siguiente si:
- requiere modificar `vendor/flow5` o `vendor/ADRpy`, borrar archivos validados o reescribir historia de git;
- la ecuación necesaria no puede comprobarse en ninguna fuente;
- una prueba falla tres intentos seguidos de corrección por la misma causa.

## 5. Flujo de trabajo y git
- Rama: `auto/f1-f2` creada desde `origin/main` actualizado. Si ya existe, continúa en ella.
- Primer commit de la rama: añade `AUTONOMOUS_RUN.md` e `INICIAR-AUTONOMO.cmd`, y agrega a `.gitignore` las líneas `FASE_COMPLETA.flag`, `autonomo.log` y `.venv/`.
- Un commit por módulo terminado; `git push` de la rama tras cada commit (nunca `--force`, nunca a `main`).
- Antes de cada commit ejecuta las pruebas completas; no hagas commit en rojo.
- Al terminar cada módulo actualiza `PROJECT_STATE.md`, `TEST_RESULTS.md`, `DECISIONS.md`, `CLAUDE_HANDOFF.md`, `ROADMAP.md`.

## 6. Bitácora de la corrida
La corrida puede reiniciarse varias veces (límites de uso). Al empezar, lee esta sección y retoma donde quedó. Al terminar cada módulo o al detenerte, añade una línea:
`- AAAA-MM-DD HH:MM | Mxx | TERMINADO / EN CURSO / BLOQUEADO | commit | nota breve`

<!-- BITACORA -->
- 2026-10-14 | M01 | TERMINADO | 670c267 | project.json + CLI m01; Tablas 1-2/1-3 verificadas con casos del libro
- 2026-10-14 | M02 | TERMINADO | 527bc5f | Tabla 6-1 (17 LSA) reproduce medias y desviaciones del libro; regresión A+B·ln W0
- 2026-10-14 | M03 | TERMINADO | 05f01d3 | Ejemplos 2-1 a 2-5 y Tabla 2-3 reproducidos (MSP 285 617 USD, equilibrio 238); sin aviones de negocio ni hélices
- 2026-10-14 | M04 | TERMINADO | c8a1a3f | ADRpy + aterrizaje Ec. 3-13/3-14 (W/S máx 11.37 lbf/ft² del Ej. 3-1 reproducido) + Ec. 3-1; D-20
- 2026-10-15 | M06 | TERMINADO | 34bb815 | Ejemplos 6-2, 6-3 y 6-4 reproducidos (W0 44 566 vs 44 556 lbf); enlace M06→M04; D-21

## 7. Cierre (dispara el correo)
Cuando la fase esté terminada según §2:
1. Push final de la rama.
2. `gh pr create --base main --head auto/f1-f2 --title "[FASE COMPLETA] F1-F2: M01-M06" --body-file` con un resumen: qué se implementó, qué se validó con cifras, qué quedó como supuesto y la lista de elementos que el usuario debe verificar.
3. Crea el archivo `FASE_COMPLETA.flag` en la raíz (no lo incluyas en git).
Si todo lo pendiente está BLOQUEADO, haz lo mismo con título `[BLOQUEADO] F1-F2` y crea igualmente el flag.
