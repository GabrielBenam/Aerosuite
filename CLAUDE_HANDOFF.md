# AeroSuite — Traspaso para retomar el trabajo (CLAUDE_HANDOFF)

Fecha: 2026-10-14. Sustituye a `docs/CLAUDE-HANDOFF.md` y `docs/CLAUDE-UPSTREAM-HANDOFF.md` (se conservan como historial).

## 1. Leer primero
`PROJECT_STATE.md` (estado real), `TEST_RESULTS.md` (evidencias), `DECISIONS.md` (por qué), `ROADMAP.md` (qué sigue), `BIBLIOGRAPHY_MAP.md` (referencias con página).

## 2. Estructura
```
aerosuite/            código propio (CLI python -m aerosuite)
  engines.py          localización y estado de motores
  adrpy_core.py       ADRpy: restricciones, pérdida, potencia, ISA, Reynolds
  xfoil_cli.py        XFOIL real
  batch_compare.py    comparación de polares
  optimizer.py        optimizador SciPy (contrato JSON)
  flow5_xml.py        intercambio con el flow5 oficial (modo -s)
  validation.py       contrastes con referencias
vendor/flow5          flow5 v7.57 original (no modificar)
vendor/ADRpy          ADRpy 0.2.6 original (no modificar)
runtime/              ejecutables descargados por setup (no versionado)
examples/             entradas de ejemplo
evidence/             salidas reales con su configuración
tests/                pruebas
scripts/setup-engines.ps1, scripts/validate-windows.ps1, VALIDAR-WINDOWS.cmd
```

## 3. Instalación y comandos (Windows, PowerShell, raíz del proyecto)
```
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-engines.ps1
.\.venv\Scripts\python.exe -m aerosuite status
.\.venv\Scripts\python.exe -m aerosuite validate
.\.venv\Scripts\python.exe -m aerosuite atmos --alt 0,1000,3000
.\.venv\Scripts\python.exe -m aerosuite reynolds --alt 2438 --speed 55.6 --chord 1.18
.\.venv\Scripts\python.exe -m aerosuite size --config examples\gudmundsson-ex3-1-c162.json --out results\c162.json --plot results\c162.png
.\.venv\Scripts\python.exe -m aerosuite xfoil 0012 2412 4412 --reynolds 1e6 --alpha-start -4 --alpha-end 20 --alpha-step 1 --from-zero --compare --out results\xfoil
.\.venv\Scripts\python.exe -m aerosuite opt --spec examples\opt-conceptual-c162.json --out results\opt-conceptual
.\.venv\Scripts\python.exe -m aerosuite opt --spec examples\opt-xfoil-naca4.json --out results\opt-2d
.\.venv\Scripts\python.exe -m aerosuite flow5-export --config examples\flow5-c162-like.json --out results\flow5-job
.\.venv\Scripts\python.exe -m aerosuite flow5-run --job results\flow5-job
.\.venv\Scripts\python.exe -m aerosuite flow5          # abre la aplicación original
```
Requisito: Python 3.11 (el setup lo exige; ADRpy no está validado en 3.15). Los comandos rechazan sobrescribir resultados existentes: usar una carpeta `--out` nueva.

Linux (VM de Cowork): `pip install -r requirements-core.txt && pip install --no-deps vendor/ADRpy`; XFOIL con `apt-get download xfoil`, `dpkg-deb -x`, y `LD_PRELOAD` de una función nula `_gfortran_set_fpe` (ver DECISIONS D-11); `AEROSUITE_XFOIL` apunta al ejecutable.

## 4. Reglas
No modificar `vendor/`. No presentar resultados sintéticos como aerodinámicos (`results/demo` es sintético). No inventar penalizaciones. Distinguir conceptual / 2D / 3D. Registrar condiciones, versiones y fallas. Sin GUI nueva hasta definir contratos.

## 5. Conexiones entre motores que faltan construir

| ID | Conexión | Situación / punto de partida |
|---|---|---|
| C-1 | Polares XFOIL MIT → flow5 | El guion flow5 admite `xfoil_polars_dir` con polares .txt de XFOIL (xflscriptexec.cpp l.366). Hoy flow5 usa su XFoil interno "on the fly". Probar con los `.polar` de AeroSuite. |
| C-2 | Resultado ADRpy (S, AR, W) → geometría de ala flow5 | Generar `wings[].sections` desde W/S de diseño y MTOW. |
| C-3 | Resultados flow5 (CSV) → AeroSuite | Lector de los CSV que exporta `flow5 -s` (formato a confirmar tras la ejecución Windows). |
| C-4 | flow5 como motor 3D del optimizador | Requiere C-3; `optimizer.py` rechaza hoy `engine: flow5`. |
| C-5 | CD0 y k de ADRpy desde flow5/XFOIL | Sustituir supuestos de `designperformance` por valores calculados, con trazabilidad. |
| C-6 | Biblioteca UIUC real | El usuario descarga `coord_seligFmt.zip` (sitio bloqueado para Claude); probar `--uiuc-zip`. |
| C-7 | Envolvente V-n (ADRpy `airworthiness`) | Exponer comando `vn`; requiere pesos y geometría. |
| C-8 | Derivadas de estabilidad flow5 → dinámica | Exportar con `Compute_derivatives` y leer. |
| C-9 | Modelo de peso del ala para optimizar AR | Gudmundsson Cap. 6; condición para D-07. |

## 5b. Repositorio
Rama `feat/gudmundsson-base` sobre `main` de GitHub (dfc43b7). Reglas para Claude Code en `CLAUDE.md`. Lector de flow5: `aerosuite/flow5_results.py`, comando `flow5-results`; `flow5-run` ya lo invoca y deja `flow5_results.json` en la carpeta del trabajo.

## 6. Pendiente inmediato
Completar `TEST_RESULTS.md` §6 con `evidence/windows-*` (resultado de `VALIDAR-WINDOWS.cmd`), en especial la ejecución real de `flow5 -s` y el formato de sus CSV. Comparar las polares MIT de Windows con las de Debian (§3.3). V-F5 (2026-10-15): flow5 7.55 corre en lote y su salida se lee (TEST_RESULTS §9, D-32/D-33). En la máquina existe flow5 v7.55 (variable AEROSUITE_FLOW5) en `C:\Users\oscar\Documents\flow5_v7.55_win64`; AeroSuite usa v7.57 en `runtime/`.

## 7. Módulos del algoritmo (rama `auto/f1-f2`)
```
.\.venv\Scripts\python.exe -m aerosuite project-init --project results\c162\project.json --name c162 --from-inputs examples\projects\c162-inputs.json
.\.venv\Scripts\python.exe -m aerosuite m01 --project results\c162\project.json
.\.venv\Scripts\python.exe -m aerosuite project-status --project results\c162\project.json
```
Cada `mXX` lee `inputs.mXX` y escribe `outputs.mXX` con su registro de corrida. Estado y bitácora: `PROJECT_STATE.md` §7 y `AUTONOMOUS_RUN.md` §6.

### Módulos F1–F2 disponibles (M01–M04, M06)
```
python -m aerosuite m01|m02|m03|m04|m06 --project <project.json>     # lee inputs.mXX, escribe outputs.mXX
python -m aerosuite project-status --project <project.json>          # salidas y módulos desactualizados
```
Entradas de ejemplo: `examples/projects/c162-inputs.json` (M01, M02, M04, M06; Ejemplo 3-1), `gud-example-2-cost.json` (M03; Ejemplos 2-1 a 2-5), `gud-example-6-4-mission.json` (M06 Método 3; Ejemplo 6-4). Cadena de dependencias: M02 → M06 (`ratios_from_m02`) y M06 → M04 (`tow_from_m06`). Pendientes de la fase y verificaciones humanas: cuerpo del PR `[FASE COMPLETA] F1-F2`, DECISIONS D-17 a D-21. M15 (`m15`, D-31): ejemplo `examples/projects/c172-like-fuselage-inputs.json` (m09b, m08, m15, m10 con `fuselage.from_m15`). M13 (`m13`, D-30): ejemplo `examples/projects/c172-like-cg-inputs.json` (m09b, m08, m10, m12, m13). M12 (`m12`, D-29): ejemplo `examples/projects/c172-like-weights-inputs.json` (m09b, m08, m10, m12). M11 (`m11`, D-28): ejemplo `examples/projects/c162-m11-inputs.json` (m04 y luego m11). M10 (`m10`, D-27): ejemplo `examples/projects/oml-c172-like.json` (ejecutar m09b, m08, m10); `export --module m10`. M09b (`m09b`, D-26): ejemplo `examples/projects/wing-c162-like.json`; cadena M04 → M09b → M08 (`wing_from_m09b`). M09a (`m09a`, D-25): `AEROSUITE_XFOIL=tools/xfoil/xfoil.exe` (binario MIT en `tools/`, no versionado); ejemplo `examples/projects/airfoil-selection-ga.json`. M08 (`m08`, D-24): `python -m aerosuite m08 --project p.json` y `export --module m08 --out m08.json` (JSON SI para M24). Ejemplo: `examples/projects/gud-example-11-tail.json`. M04 (D-22): despegue = Ec. 3-1, `fuente` por restricción y `contraste_adrpy`. Siguiente en ARCHITECTURE §8: M24 CAD (lee `export --module m10`), M16 estabilidad (límites de CG para M13), M18 tren/controles/flaps, M19–M21 y M22 (reactivar AR con W_cap ∝ AR^1.5 de M12). Cadena completa de F3: m04 → m09a → m09b → m08 → m15 → m10 → m11 → m12 → m13 (ver ejemplos `c172-like-*.json`).
