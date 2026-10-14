# AeroSuite — traspaso de motores originales a Claude Cowork

## Objetivo

Mantener las capacidades originales de flow5 v7.57 intactas y transferir a Claude la integración definitiva. Por ahora se usan motores independientes con comandos claros, sin modificar las bibliotecas originales ni construir una nueva interfaz grande.

## Fuentes verificadas

| Motor | Versión y SHA exacto | Directorio | Estado |
|---|---|---|---|
| flow5 | v7.57, a9e852c559590188e00e9efe997c35c1dec7209b | vendor/flow5 | Submódulo Git con fuentes originales completas |
| ADRpy | 0.2.6, b2beba274ebff93ec9fb22f046e3fc47356ceac2 | vendor/ADRpy | Submódulo Git con fuentes originales completas |
| XFOIL | MIT 6.99 | runtime/xfoil | Binario descargado del MIT por el instalador |
| SciPy | Instalado por pip | .venv | Optimizador conceptual |

Para obtener fuentes completas mediante Git: git clone --recurse-submodules https://github.com/GabrielBenam/Aerosuite.git

Un ZIP habitual de GitHub no incluye el contenido de los submódulos; utilizar el artefacto completo de GitHub Actions o un clon recursivo.

## Comandos

Ejecutar setup Windows desde PowerShell en la raíz del proyecto:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-engines.ps1

Luego:

    .\.venv\Scripts\python.exe -m aerosuite status
    .\.venv\Scripts\python.exe -m aerosuite flow5
    .\.venv\Scripts\python.exe -m aerosuite size --config examples\aircraft-concept.json --out results\sizing.json
    .\.venv\Scripts\python.exe -m aerosuite optimize --config examples\aircraft-concept.json --out results\optimized.json
    .\.venv\Scripts\python.exe -m aerosuite xfoil 2412 0012 --exe runtime\xfoil\xfoil.exe --reynolds 1000000 --out results\xfoil

Los comandos de ADRpy producen resultados numéricos y unidades explícitas en JSON. No generan geometrías 3D.

## Reglas para Claude

1. NO modificar carpetas vendor/flow5 ni vendor/ADRpy. La versión original será el punto de referencia y sólo habrá extensiones externas cuando se acuerden.
2. NO afirmar que flow5 ha sido integrado a AeroSuite a nivel de biblioteca C++: el comando actual inicia el ejecutable Windows original. Esto conserva todas sus capacidades en la aplicación original.
3. Limitar el ámbito de la futura interfaz AeroSuite a aeronaves de ala fija. El ejecutable flow5 original seguirá conteniendo las secciones náuticas; quitarlas exigiría un fork o modificación.
4. Mantener XFOIL 6.99 externo y no equipararlo automáticamente con la biblioteca XFoil modificada que usa flow5.
5. Utilizar ADRpy 0.2.6 para dimensionamiento, prestaciones y atmósferas; SciPy para optimización de carga alar y alargamiento. El optimizador NO es una optimización de geometría 3D y no incluye peso estructural sin especificación adicional.
6. Verificar convergencia y unidades, guardar condiciones y versiones y evitar datos aerodinámicos sintéticos en resultados reales.
7. Mantener licencias GPLv3 de flow5 y ADRpy, además de licencias de XFOIL y dependencias Qt/OCCT/Gmsh/BLAS.
8. Diseñar la futura interfaz y los contratos entre módulos **después** de que estos motores sean probados de manera aislada. Preferir JSON y CLI iniciales.

## Limitaciones explícitas

La copia íntegra del programa original flow5 funciona como aplicación independiente, no dentro de los botones de AeroSuite. La integración automática con su API C++ y un optimizador aerodinámico 3D siguen pendientes para Claude.

Se incluye el fuente del upstream bajo sus licencias, sin reclamar derechos sobre las marcas ni bibliotecas ajenas.
