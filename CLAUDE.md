# AeroSuite — instrucciones para Claude Code

Lee primero, en este orden: `CLAUDE_HANDOFF.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TEST_RESULTS.md`, `ROADMAP.md`, `BIBLIOGRAPHY_MAP.md`.

## Base funcional y fuentes
- Marco rector: algoritmo de diseño conceptual de Gudmundsson (*General Aviation Aircraft Design*, 2.ª ed., Tabla 1-4 y Fig. 1-11). Cada función nueva es un módulo `Mxx` asociado a uno o más de sus 27 pasos (ver `ARCHITECTURE.md` §2).
- Fuentes, en orden de prioridad: (1) archivos primarios del usuario en `C:\Users\oscar\Desktop\ESPACIO COWORK\Aerosuite-main\BIBLIOGRAFIA` cuando la sesión tiene acceso a esa computadora; (2) libros cargados en el proyecto de Claude; (3) internet solo para huecos, con fuentes públicas verificables (USAF DATCOM, NACA/NTRS, eCFR 14 CFR Part 23, EASA CS-23). Registrar autor, obra, capítulo y página en `BIBLIOGRAPHY_MAP.md`; no citar páginas sin comprobarlas.

## Reglas
- No modificar `vendor/flow5` ni `vendor/ADRpy` (submódulos fijados por SHA). Las extensiones a un motor se escriben en `aerosuite/` (p. ej. subclases de `AircraftConcept`).
- flow5 se usa como ejecutable oficial (interfaz o `flow5 -s guion.xml`); sus resultados se leen con `aerosuite/flow5_results.py`.
- Nada de resultados sintéticos presentados como aerodinámicos. Las pruebas con datos analíticos se rotulan como fixtures de formato.
- Distinguir siempre nivel conceptual / 2D / 3D; no inventar penalizaciones; registrar convergencia, fallas, versiones y unidades (SI interno).
- Sin GUI nueva hasta que los módulos del lazo central funcionen por CLI (ver `ROADMAP.md`).
- Python 3.11 con `requirements-core.txt` (NumPy 1.26.4). ADRpy 0.2.6 falla con NumPy 2.5; con 2.2 funciona.

## Comandos
```
python -m pip install -r requirements-core.txt
python -m pip install --no-deps ./vendor/ADRpy
python -m unittest discover -s tests -v
python -m aerosuite status | validate | size | xfoil | opt | flow5-export | flow5-run | flow5-results
```
XFOIL en Linux (pruebas): paquete Debian `xfoil 6.99.dfsg+1-3` con `LD_PRELOAD` de una función nula `_gfortran_set_fpe` y `AEROSUITE_XFOIL` apuntando al ejecutable (DECISIONS D-11).

## Al terminar cada tarea
Actualizar `PROJECT_STATE.md`, `TEST_RESULTS.md`, `DECISIONS.md`, `CLAUDE_HANDOFF.md` y `ROADMAP.md` si cambian; ejecutar la suite de pruebas; no marcar como validado nada que no se haya ejecutado con el motor real.
