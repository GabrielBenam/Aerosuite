# AeroSuite — base de motores aeronáuticos originales

AeroSuite reúne, sin modificar sus fuentes, **flow5 v7.57** (aerodinámica 3D), **ADRpy 0.2.6** (dimensionamiento conceptual), **XFOIL 6.99** (perfiles 2D) y **SciPy** (optimización), con una interfaz mínima de línea de comandos y archivos JSON. Ámbito: aeronaves de ala fija.

Estado real de cada parte: [PROJECT_STATE.md](PROJECT_STATE.md) · Evidencias: [TEST_RESULTS.md](TEST_RESULTS.md) · Decisiones: [DECISIONS.md](DECISIONS.md) · Hoja de ruta: [ROADMAP.md](ROADMAP.md) · Traspaso: [CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md) · Bibliografía: [BIBLIOGRAPHY_MAP.md](BIBLIOGRAPHY_MAP.md) · Licencias: [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)

## Instalación (Windows)

Requiere Python 3.11. Desde PowerShell en la raíz del proyecto:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-engines.ps1

Descarga el flow5 oficial v7.57 (≈174 MB) y XFOIL 6.99 del MIT a `runtime/`, crea `.venv`, instala ADRpy desde `vendor/ADRpy` y ejecuta las pruebas. Para validar todo y guardar evidencias: doble clic en `VALIDAR-WINDOWS.cmd`.

Las fuentes de `vendor/` son submódulos Git; el ZIP de "Code > Download ZIP" no las incluye. Usar `git clone --recurse-submodules` o la carpeta del proyecto ya completa.

## Comandos (`.\.venv\Scripts\python.exe -m aerosuite <comando>`)

| Comando | Motor | Qué hace |
|---|---|---|
| `status` | — | Versiones fijadas, SHA verificados, ejecutables encontrados |
| `validate` | ADRpy | ISA vs ICAO, ejemplo de ADRpy, Ejemplo 3-1 de Gudmundsson |
| `atmos`, `reynolds` | ADRpy | Tabla ISA; Reynolds y Mach de una condición de vuelo |
| `size --config C --plot P` | ADRpy | Restricciones T/W–W/S, límite de pérdida, potencia, diagrama |
| `xfoil 2412 0012 --reynolds 2e5,1e6 --from-zero --compare` | XFOIL | Polares reales, puntos no convergidos registrados, comparación |
| `compare` | — | Compara polares CSV+JSON con condiciones idénticas |
| `opt --spec S --out D` | SciPy + ADRpy/XFOIL | Optimización conceptual o 2D con contrato JSON |
| `flow5` | flow5 | Abre la aplicación original |
| `flow5-export --config C --out D` | flow5 | Escribe perfiles, avión XML, polar XML y guion |
| `flow5-run --job D` | flow5 | Ejecuta `flow5 -s` y registra sus salidas |
| `generate`, `shortlist` | — | Geometría NACA y filtro geométrico (sin aerodinámica) |
| `optimize` | SciPy + ADRpy | Heredado (ver DECISIONS D-07) |

Ejemplos de entrada en `examples/`. Los resultados de `results/demo` son **sintéticos** (solo prueba de software).

## Alcance técnico

flow5 se usa como su propia aplicación (interfaz o modo por lotes), no como biblioteca enlazada. La optimización disponible es conceptual (ADRpy) o 2D (XFOIL); la optimización 3D con flow5 está pendiente. Ningún resultado constituye evidencia de aeronavegabilidad ni de certificación.
