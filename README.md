# AeroSuite — motores aeronáuticos originales (base para Claude)

AeroSuite conserva aquí los motores existentes **sin alterar sus fuentes upstream**. La aplicación original flow5 proporciona toda su interfaz y análisis; AeroSuite añade comandos mínimos para dimensionamiento conceptual ADRpy, optimización SciPy y análisis XFOIL 2D.

## Incluido

- flow5 original v7.57 — código completo en submódulo Git vendor/flow5 y distribución oficial Windows empaquetada por GitHub Actions (incluye todavía menús náuticos originales; AeroSuite sólo se enfoca en aviones).
- ADRpy original v0.2.6 — código completo en submódulo Git vendor/ADRpy.
- XFOIL original MIT v6.99 — descarga a runtime/xfoil por scripts/setup-engines.ps1.
- SciPy differential_evolution — optimización inicial conceptual de W/S y alargamiento, no optimización aerodinámica 3D.
- Antiguo comparador Airfoil Lab, NACA, UIUC y pruebas de XFOIL.

## Instalación Windows

Preferida: GitHub Actions -> "AeroSuite pristine upstream engines + ADRpy and optimizer" -> Artifacts -> AeroSuite-Original-Engines-Source-And-Flow5-Windows. Extraer archivo y ejecutar:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-engines.ps1 -SkipFlow5

Esta instrucción utiliza el flow5 original ya empaquetado y obtiene XFOIL desde MIT; para dimensionamiento necesitas Python 3.11, instalado junto con la versión Python 3.15 si ya la utilizas.

Si trabajas con Git:

    git clone --recurse-submodules https://github.com/GabrielBenam/Aerosuite.git
    cd Aerosuite
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-engines.ps1

**El ZIP normal de GitHub ("Code > Download ZIP") no incluye las fuentes de los submódulos.** Para entregar copia completa a Claude usa el clon recursivo o el artefacto de GitHub Actions.

## Comandos

    .\.venv\Scripts\python.exe -m aerosuite status
    .\.venv\Scripts\python.exe -m aerosuite flow5
    .\.venv\Scripts\python.exe -m aerosuite size --config examples\aircraft-concept.json --out results\sizing.json
    .\.venv\Scripts\python.exe -m aerosuite optimize --config examples\aircraft-concept.json --out results\optimized.json
    .\.venv\Scripts\python.exe -m aerosuite xfoil 2412 0012 --exe runtime\xfoil\xfoil.exe --out results\xfoil

## Alcance técnico

flow5 sigue siendo **su propia aplicación original** con todo su modelado/solver 3D, no una biblioteca compilada y comunicada con AeroSuite. ADRpy y SciPy proporcionan dimensionamiento y optimización conceptual, NO optimización 3D equivalente a los módulos avanzados de flow5. El código no fabrica datos físicos. La interfaz de AeroSuite seguirá siendo mínima hasta que Claude realice la integración definitiva.

Consultar docs/CLAUDE-UPSTREAM-HANDOFF.md para estado, versiones fijadas y tareas de Claude.

## Licencias

flow5 y ADRpy son GPLv3. XFOIL es GPLv2 o posterior en la distribución documentada por Debian. Mantén copyright, fuentes y licencias originales y revisa derechos de redistribución de cada dependencia nativa. flow5 es una marca de su titular original.
