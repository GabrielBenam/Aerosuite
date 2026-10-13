# Upstream flow5 v7.57

Fuente: https://github.com/techwinder/flow5/tree/v7.57

La raíz flow5.pro usa qmake TEMPLATE=subdirs e incluye XFoil-lib, flow5-lib, flow5-io-lib y flow5-app. Los ejemplos API_examples/XFoilRun y API_examples/XFoilBatchRun son puntos de partida para el motor de perfiles.

## Implementación prevista
1. Mantener flow5 separado del código propio.
2. Compilar upstream y ejecutar un ejemplo oficial en Windows.
3. Definir adaptador aerodinámico con entradas explícitas (geometría, Reynolds, Mach, alfa) y salidas verificables (polares, convergencia, errores).
4. Añadir pruebas y casos de referencia antes de automatizar recomendaciones.

Estado: NO está integrado el motor y NO se ha compilado flow5 aquí.

Licencia: flow5 usa GPL-3.0; revisar obligaciones si se incorpora código o se distribuyen componentes enlazados.
