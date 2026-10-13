# Adaptador nativo flow5 v7.57 (experimental)

Este directorio contiene un ejecutable C++ separado basado en las llamadas públicas del ejemplo oficial [XFoilBatchRun](https://github.com/techwinder/flow5/blob/v7.57/API_examples/XFoilBatchRun/xfoilbatchrun.cpp). No se ha compilado ni ejecutado aquí: requiere flow5, sus bibliotecas y dependencias nativas configuradas en Windows.

## Compilación recomendada
1. Compila el proyecto original de flow5 v7.57 y confirma la ejecución del ejemplo XFoilBatchRun SIN modificaciones.
2. Copia el CMakeLists.txt de API_examples/XFoilBatchRun a un directorio de build externo al repositorio, ajustando allí rutas de Qt, Gmsh, OCCT, MKL y bibliotecas de flow5 a tu instalación; el ejemplo oficial contiene rutas absolutas del autor.
3. Cambia la entrada `xfoilbatchrun.cpp` por `xfoilbatch_aerosuite.cpp` mediante una variable CMake o una copia local del CMakeLists. No edites el upstream original.
4. Genera la configuración con Visual Studio 2022 / MSVC y CMake. Compila en Release. Revisa dependencias dinámicas en runtime.
5. Ejecuta `aerosuite-xfoilbatch --help` y un caso básico antes de conectarlo a Python.

## CLI del adaptador

```text
aerosuite-xfoilbatch --naca 2412 --reynolds 100000,200000 --alpha-start -4 --alpha-end 12 --alpha-step 1 --mach 0 --output C:/AeroSuite/results/test.fl5
```

Genera un proyecto flow5 `.fl5`, **no** un CSV de coeficientes CL/CD. Estos deben obtenerse luego mediante una API/exportador verificado; no se deben inventar ni derivar de texto libre de consola.

**Advertencia:** en esta fase se verifica la interfaz de código fuente, no la compatibilidad binaria ni la convergencia numérica. Están pendientes pruebas en Windows, límites físicos de los modelos y pruebas con polares conocidas.

Licencia: revisar GPLv3 de flow5 y redistribución del adaptador C++ enlazado.
