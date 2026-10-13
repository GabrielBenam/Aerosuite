# AeroSuite — comparador integral (prototipo)

Rama de trabajo que reúne PR #1 y PR #2 sin modificar \`main\`.

## Funciones operativas en Python
- Lectura y catalogación de archivos Selig DAT desde ZIP oficial UIUC.
- Gráfica de geometrías superpuestas con matplotlib instalado.
- Lectura de polares CSV con columnas alpha,cl,cd,cm.
- Validación de condiciones Reynolds/Mach/Ncrit/transición equivalentes.
- Clasificación por CL/CD máximo observado *en los puntos suministrados*.
- Guardado de \`comparison.json\` y gráficos, si se solicita.

## Ejemplo

Guardar \`ag03.csv\` y \`ag04.csv\` en \`results/polars\`; cada uno requiere \`ag03.json\` / \`ag04.json\` con las claves \`reynolds\`, \`mach\`, \`ncrit\`, \`xtr_top\`, \`xtr_bottom\`, \`solver\` y \`converged\`.

\`\`\`powershell
python -m pip install matplotlib
python -m unittest discover -s tests -v
python -m aerosuite compare ag03 ag04 --polars results/polars --out results/comparison
\`\`\`

Para superponer geometrías además de polares, agregar \`--uiuc-zip C:\AeroSuite\data\coord_seligFmt.zip\`.

**Importante:** hasta compilar y validar el motor flow5 (C++), los CSV deben suministrarse externamente: no se calculan coeficientes aerodinámicos en Python. Una polar se puede usar solo después de comprobar procedencia, condiciones y convergencia. El ranking no equivale a recomendación para fabricación ni certificación.
