# Cómo probar AeroSuite en Windows

## Importante
AeroSuite es actualmente un **prototipo ejecutado desde Python**, no un instalador ni una aplicación de escritorio. La demo usa curvas aerodinámicas **sintéticas y no validadas**: sirve para comprobar la interfaz de comandos, procesamiento, CSV y gráficos, no para diseñar o certificar aeronaves.

## Preparación
1. Instala Python 3.11 para Windows desde https://www.python.org/downloads/windows/ y activa la opción para añadirlo al PATH.
2. Descarga el ZIP del repositorio desde la rama `feat/airfoil-end-to-end`: https://github.com/GabrielBenam/Aerosuite/tree/feat/airfoil-end-to-end (Code > Download ZIP). Extrae su contenido.
3. Abre PowerShell dentro de la carpeta que contiene `aerosuite`, `tests` y `scripts`.

## Prueba completa con un comando
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\demo.ps1
```
El script ejecuta unittest, instala matplotlib si falta (necesita internet solo durante la instalación), genera dos NACA y datos sintéticos claramente rotulados, compara las polares y guarda el informe.

## Resultados
- `results/demo/comparison/comparison.json`: ranking por máximo CL/CD de los puntos sintéticos.
- `results/demo/comparison/plots/geometry.png`: geometrías NACA.
- `results/demo/comparison/plots/cl_alpha.png`, `cd_alpha.png`, `cm_alpha.png`, `cl_cd.png` y `efficiency_alpha.png`: gráficos sintéticos.
- `results/demo/polars`: CSV y JSON de prueba.

## Comandos individuales
```powershell
python -m unittest discover -s tests -v
python -m aerosuite generate 2412 --out results/naca
python -m aerosuite shortlist 0012 2412 4415 --min-thickness 0.1 --max-thickness 0.18
python -m aerosuite compare naca2412 naca0012 --polars results/demo/polars --out results/demo/comparison
```

## Biblioteca UIUC
Descarga el archivo oficial desde https://m-selig.ae.illinois.edu/ads/archives/coord_seligFmt.zip . Puedes utilizarlo después para superponer geometrías en comparaciones con polares cuyos identificadores correspondan exactamente a los perfiles del ZIP. El comparador no calcula actualmente los coeficientes desde las geometrías importadas.

## Lo que todavía no funciona
- No hay ejecutable/instalador de AeroSuite.
- El adaptador C++ de flow5 sigue sin compilarse y verificarse.
- El botón/flujo automático UIUC -> XFoil -> polares aún no está disponible.
- El resultado de la demo **no es una medición ni una simulación física**.
