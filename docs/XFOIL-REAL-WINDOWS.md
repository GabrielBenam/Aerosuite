# XFOIL real — guía de integración y uso (experimental)

Se incorpora un motor optativo XFOIL ejecutado como proceso externo. No se modifican flow5 ni sus bibliotecas. No se incluye un ejecutable XFOIL ni la biblioteca UIUC.

## Descarga
- MIT XFOIL: https://web.mit.edu/drela/Public/web/xfoil/ (XFOIL6.99.zip para Windows, versión histórica de 32 bits).
- UIUC: https://m-selig.ae.illinois.edu/ads/archives/coord_seligFmt.zip

Descomprime XFOIL y localiza **xfoil.exe**. Confirma que se ejecuta en tu Windows. Es un programa legado de consola, no garantizado compatible con todos los sistemas. Los archivos del ZIP de MIT pueden requerir inspección de contenido y antivirus.

## Prueba inicial: dos perfiles NACA
Abre PowerShell en la raíz del repo (se requiere Python 3.10+ y matplotlib):

```powershell
python -m aerosuite xfoil 2412 0012 --exe "C:\AeroSuite\XFOIL\xfoil.exe" --reynolds 1000000 --alpha-start -2 --alpha-end 8 --alpha-step 2 --out results/xfoil-naca
python -m aerosuite compare naca2412 naca0012 --polars results/xfoil-naca --out results/xfoil-naca-comparison
```

La ruta al ejecutable es EJEMPLO: sustituirla por la ruta real de xfoil.exe. El segundo comando sólo acepta barridos completos reportados por el solver.

## Perfiles UIUC
```powershell
python -m aerosuite xfoil ag03 ag04 --uiuc-zip "C:\AeroSuite\coord_seligFmt.zip" --exe "C:\AeroSuite\XFOIL\xfoil.exe" --reynolds 150000 --alpha-start -2 --alpha-end 8 --alpha-step 2 --out results/xfoil-uiuc
python -m aerosuite compare ag03 ag04 --polars results/xfoil-uiuc --out results/xfoil-uiuc-comparison --uiuc-zip "C:\AeroSuite\coord_seligFmt.zip"
```

## Archivos y validación
Cada perfil genera `id.polar` (polar nativa XFOIL), `id.csv` (columnas alpha,cl,cd,cm), `id.json` (configuración, hashes SHA256, estado de barrido) y `id.log` (salida de consola).
**Si no convergen todos los ángulos solicitados, el comparador rechaza el perfil.** No uses resultados parciales para clasificar. Se requiere además validación física independiente frente a referencias antes de interpretar resultados como base de diseño.

## Límites conocidos
- El comando no incorpora un instalador de XFOIL ni su compilación en Windows.
- El código Python no ejecutó todavía aquí un ejecutable XFOIL real; se verifican mediante CI comandos, parser y casos sintéticos de prueba.
- Los formatos Selig con geometrías defectuosas o no compatibles pueden fallar.
- No hay ejecutable GUI y la compilación de flow5 v7.57 sigue pendiente.
- Los polares pueden no converger para Reynolds bajos, ángulos extremos y ciertas geometrías.
- La licencia GPL del motor XFOIL requiere examinar obligaciones de redistribución si en el futuro se empaqueta.
