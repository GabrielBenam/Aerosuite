# Comparador de perfiles UIUC — primer prototipo

Fuente oficial: https://m-selig.ae.illinois.edu/ads/coord_database.html
ZIP oficial: https://m-selig.ae.illinois.edu/ads/archives/coord_seligFmt.zip

El sitio describe aprox. 1,650 geometrías, y el ZIP del formato Selig como actualizado a 2026-02-23.
**Los datos no se incluyen en este repositorio**: el usuario descarga el archivo directamente de UIUC.
Respeta atribución, derechos y restricciones específicas de datos antes de redistribuirlos.

## Instalación para gráficas
\`\`\`powershell
python -m pip install matplotlib
\`\`\`

## Ejemplo Python
\`\`\`python
from pathlib import Path
from aerosuite.uiuc_library import load_library,catalog
from aerosuite.airfoil_compare import plot_geometry

archive=Path(r"C:\AeroSuite\data\coord_seligFmt.zip")
profiles,errors=load_library(archive)
catalog(archive,Path("results/uiuc-catalog.json"))
print("Importados:",len(profiles),"Rechazados:",len(errors))
choices=[profiles[k] for k in ("ag03","ag04","ag08") if k in profiles]
plot_geometry(choices,Path("results/geometry-comparison.png"))
\`\`\`

**Los archivos de coordenadas pueden contener comentarios '#' en cualquier posición**. Esta primera versión interpreta formato Selig de contorno único y rechaza formatos no compatibles; es intencional para no generar curvas falsas.

Para comparar polares se requieren CSV externos verificados con \`alpha,cl,cd,cm\` y metadatos iguales de Reynolds, Mach, Ncrit y posiciones de transición. El comparador traza: CL/alpha, CD/alpha, CM/alpha, CL/CD y eficiencia CL/CD contra alpha. El componente **no** calcula coeficientes ni valida física por sí mismo.

## Siguientes hitos
- Compatibilidad con archivos Lednicer de dos bloques, validación geométrica exhaustiva y normalización.
- UI de búsqueda/filtro, hasta N perfiles configurables.
- Exportación comprobada de polares desde flow5 o XFoil y captura de convergencia.
- Diagramas Cp y espesor/curvatura con métodos validados.
- Comparación contra video de referencia cuando se pueda inspeccionar visualmente su contenido.
