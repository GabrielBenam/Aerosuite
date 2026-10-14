# AeroSuite Airfoil Lab — Windows

Nueva interfaz Tkinter para comparar perfiles NACA y UIUC con XFOIL real.

## Descargar versión Windows
1. Abre GitHub Actions y entra en AeroSuite Airfoil Lab Desktop.
2. Selecciona una ejecución completada correctamente.
3. Descarga el artefacto AeroSuite-Airfoil-Lab-Windows.
4. Extrae todo el ZIP y ejecuta AeroSuite-Airfoil-Lab.exe. Conserva su carpeta _internal.

## Utilización
1. Descarga XFOIL desde MIT mediante el botón dentro de la aplicación, o selecciona tu xfoil.exe local.
2. Descarga la biblioteca oficial UIUC o selecciona el ZIP que ya tengas.
3. Busca nombres de perfiles y añade de 2 a 24 a la comparación.
4. Ajusta Reynolds, Mach, Ncrit, ángulo inicial -5, final 15, incremento, iteraciones y procesos.
5. Ejecuta el análisis; se guarda un directorio independiente en %LOCALAPPDATA%/AeroSuite/runs.
6. Revisa las pestañas Progreso y Gráficas y el archivo report.json.

## Alternativa desde fuente
Abre PowerShell en la raíz del proyecto y ejecuta:

    python -m pip install matplotlib Pillow
    python -m aerosuite.desktop

## Límites
El solver incluido como integración es XFOIL descargado bajo demanda desde MIT; flow5 no está compilado ni enlazado.
Las simulaciones pueden no converger y no constituyen validación experimental. El ranking excluye perfiles con barridos incompletos.
Los archivos ZIP UIUC y el ejecutable XFOIL no se redistribuyen dentro del paquete Windows. La aplicación no instala servicios en segundo plano.