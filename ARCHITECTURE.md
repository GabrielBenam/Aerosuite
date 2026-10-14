# AeroSuite — Arquitectura (ARCHITECTURE)

Versión 1 · 2026-10-14 · Estado: aprobada por el usuario en orden y estructura; las secciones marcadas **[supuesto]** dependen de la validación Windows de flow5.

## 1. Base funcional: algoritmo de diseño conceptual de Gudmundsson

La ruta de trabajo de AeroSuite es el *Conceptual design algorithm for a GA aircraft* de Gudmundsson (2.ª ed., Sec. 1.4.1, Tabla 1-4 y Fig. 1-11, impresas pp. 15–17, PDF 60–62). Son 27 pasos: una inicialización (1–9), un lazo iterativo (10–23, con retorno al paso 10 si la evaluación del paso 23 falla) y un cierre que congela la geometría exterior (OML) y pasa al diseño preliminar (24–27).

De la Sec. 1.4.2 se adopta el principio de la hoja "General": un concentrador único de parámetros del que dependen todos los cálculos, y modelos compartidos de sustentación, resistencia y empuje como funciones reutilizables. En AeroSuite eso es `project.json` más los modelos publicados por cada módulo.

Fases de la interfaz y del seguimiento de proyectos (agrupación propia de AeroSuite sobre la Tabla 1-4):

| Fase | Pasos | Propósito |
|---|---|---|
| F1 Requisitos | 1–3 | Misión, base regulatoria, referencias, costo |
| F2 Dimensionamiento | 4–9 | Restricciones, peso inicial, ala, cola, perfiles |
| F3 Configuración | 10–15 | Geometría, planta motriz, pesos, CG, fuselaje |
| F4 Análisis | 16–21 | Estabilidad, tren, hipersustentación, pérdida, resistencia, prestaciones |
| F5 Cierre | 22–24 | Optimización, evaluación regulatoria, congelar OML (CAD) |
| F6 Traspaso | 25–27 | V-n, cargas, paquete para Ansys / diseño preliminar |

## 2. Mapeo de pasos a módulos

Estados: E = existe · N = nuevo con fuente bibliográfica · P = parcial · H = decisión humana asistida · X = fuera de alcance.

| Paso (Sec.) | Módulo | Motor / fuente | Estado |
|---|---|---|---|
| 1 Requisitos y base de certificación | M01 Requisitos y base regulatoria | Tablas 1-1 a 1-3; ADRpy `airworthiness` | N |
| 2 Aeronaves similares, configuración, propulsión | M02 Base de referencia y regresiones | Bases de datos 16.6, 18.4, 19.4, 23.3 | N + H |
| 3 Costos | M03 Costos | Cap. 2 (2.2, 2.3) | N |
| 4–5 Diagrama de restricciones | M04 Restricciones (+ aterrizaje Ec. 3-13, Apéndice D) | ADRpy | E + N |
| 6 Peso inicial y misión | M06 Peso inicial y misión | Sec. 6.2, 21.5 | N |
| 7 Área alar y empuje, límite de pérdida | M04 | ADRpy | E |
| 8 Cola inicial (VHT, VVT) | M08 Cola inicial | Sec. 11.4 | N |
| 9 Planta alar y perfil (matriz de decisión) | M09a Perfiles · M09b Ala | XFOIL; Sec. 8.3.9; Cap. 9; flow5 LLT | E + N |
| 10 Configuración candidata | M10 Geometría paramétrica (OML) | Cap. 4; Sóbester Caps. 2–4 | N + H |
| 11 Motor | M11 Planta motriz y hélice | ADRpy `propulsion`; Caps. 7, 14, 15 | P |
| 12 Pesos detallados | M12 Pesos | Sec. 6.3–6.5 | N |
| 13–14 CG, inercias, envolvente de CG | M13 CG e inercias | Sec. 6.6–6.7; flow5 | N |
| 15 Fuselaje | M15 Fuselaje | Sec. 12.3 | N |
| 16–17 Estabilidad estática y dinámica | M16 Estabilidad | flow5 T7; Caps. 24–25; Etkin | E (flow5) + lector |
| 18 Tren, controles, hipersustentación | M18a Tren (Cap. 13) · M18b Controles (24.4) · M18c Flaps (Cap. 10, XFOIL) | — | N |
| 18 Trayectorias de carga, sistemas de control | — | Ansys / preliminar | X |
| 19 Pérdida benigna | M19 Pérdida en envergadura | flow5 + XFOIL; Sec. 9.6 | N |
| 20 Resistencia por componentes | M20 Resistencia | Cap. 16; CDi de flow5 | N |
| 21 Prestaciones y carga útil–alcance | M21 Prestaciones | Caps. 17–23; ADRpy | P → N |
| 22 Optimizar | M22 Optimizador multinivel | SciPy; flow5 como evaluador | E (conceptual, 2D) |
| 23 Evaluación regulatoria | M23 Verificación de requisitos | 14 CFR 23, CS-23, ASTM | P + H |
| 24 Congelar OML | M24 Exportación CAD (STEP) | CadQuery/OCP | N |
| 25 V-n | M25 Envolvente | ADRpy; Sec. 17.4 | E en motor |
| 26 Cargas | M26 Cargas aerodinámicas para Ansys | flow5 | P |
| 27 Diseño preliminar | Paquete de traspaso | — | Entrega |

Fuera de alcance: dimensionamiento estructural y FEA, aeroelasticidad, CFD RANS, sistemas detallados, fabricación.

## 3. Capas

```
5 INTERFAZ (PySide6)        proyectos, tablero, mapa del algoritmo, bancos de módulo
4 API DE APLICACIÓN         aerosuite.app — usada por la CLI y por la interfaz
3 NÚCLEO                    modelo de proyecto · gestor de corridas · unidades · trazabilidad · validación
2 MÓDULOS Y ADAPTADORES     adrpy_core · xfoil_cli · flow5_xml · flow5_results · optimizer · M01…M26
1 MOTORES ORIGINALES        flow5.exe v7.57 · ADRpy 0.2.6 · xfoil.exe 6.99 · SciPy (sin modificar)
```

**Regla de extensión de motores.** Las funciones nuevas viven en módulos de AeroSuite. Si extienden un motor, lo hacen desde fuera (por ejemplo, una clase propia que hereda de `ADRpy.constraintanalysis.AircraftConcept` para la restricción de aterrizaje). `vendor/` no se modifica.

**Contrato de módulo.** Cada módulo Mxx declara: entradas (claves de `project.json` que lee, con unidades), salidas (claves que escribe), modelos publicados (funciones reutilizables, p. ej. `cd(h, V, flap, gear)`), referencias (filas de `BIBLIOGRAPHY_MAP.md`), motor usado y nivel (conceptual / 2D / 3D). Toda ejecución produce una corrida inmutable.

**Modelo de proyecto.** Carpeta por aeronave: `project.json` (fuente única, equivalente a la hoja "General"), `runs/<id>/` (entradas, salidas, manifiesto con versión y SHA del motor, convergencia, fallas), `cad/` (exportaciones), `reports/`. Cada valor guarda la corrida que lo produjo; si cambia una dependencia, los valores dependientes se marcan **desactualizados**. Una iteración del lazo 10→23 se registra como número de iteración del proyecto.

**Gestor de corridas.** Procesos separados, cola, cancelación, límite de tiempo, bitácora en vivo.

## 4. Lector de resultados de flow5 (M-F5R) [supuesto: formatos por confirmar]

- Lectura por encabezados, tolerante a orden y columnas nuevas; detección de unidades.
- Esquema normalizado y versionado: polar 3D (α, CL, CDi, CDv, CD, Cm, Cl, Cn, …), distribuciones en envergadura (y, cuerda, Cl local, Cdi, cortante, flector), derivadas y modos de estabilidad, metadatos (avión, polar, método, tipo, fluido, versión).
- Derivados con calidad de ajuste: CD0 y k por mínimos cuadrados (R², rango de CL), punto neutro y margen estático desde Cm-α.
- Puntos no convergidos marcados.
- Pruebas de regresión con salidas reales de `flow5 -s` como referencia; antes de tenerlas, el diseño del parser se basa en el código de exportación de `vendor/flow5` (`io::exportAllWPolars`, `exportAllPOpps`).
- Consumidores: M16, M19, M20, M21, M22 (3D), M26 y la conexión C-5 (CD0, k a ADRpy).

## 5. Exportación CAD (M24)

Coincide con el paso 24 (congelar la OML). CadQuery/OCP (OpenCascade): solevado de las secciones reales del proyecto (las mismas analizadas por XFOIL y flow5) para ala, cola y fuselaje; sólidos cerrados; ensamble STEP AP214/AP242 con cuerpos nombrados; STL y CSV de secciones. Metadatos: SHA del proyecto y corrida de origen. Destino: SolidWorks, Ansys SpaceClaim/DesignModeler. Pendiente: verificar si flow5 v7.57 exporta STEP para no duplicar. M26 complementa con cargas exportables a Ansys Mechanical (External Data).

## 6. Interfaz

Concepto híbrido tomado de D-MIKE (suite DMAIC del usuario): gestor de proyectos con barra de fases, tablero de indicadores contra requisitos con semáforo, lista de "requiere atención", catálogo de módulos con búsqueda y alta al proyecto, ficha de detalle con historia por iteración. Propuestas visuales en el lienzo "AeroSuite · Propuestas de interfaz".

Reglas: ningún número sin su origen a un clic; datos sintéticos marcados; niveles conceptual / 2D / 3D con colores fijos; nada interpolado en silencio; unidades globales SI/imperial.

## 7. Fuentes [rol propuesto, pendiente de confirmación del usuario]

Gudmundsson: marco metodológico rector. Drela, Diston, Anderson, Etkin, Sóbester: respaldo de métodos específicos. Internet solo para huecos con fuentes públicas verificables (USAF DATCOM, informes NACA en NTRS, eCFR 14 CFR Part 23, EASA CS-23), siempre registradas en `BIBLIOGRAPHY_MAP.md`.

## 8. Orden de construcción

1. Validación Windows + lector flow5 (M-F5R).
2. Lazo central: M01, M04 (aterrizaje), M06, M08, M09b, M10, M24.
3. M12, M13, M15.
4. M16, M19 sobre flow5.
5. M20, M21.
6. M22 nivel 3D.
7. M23, M25, M26.
8. M02, M03, M18.
9. Interfaz (después de que los módulos 1–3 funcionen por CLI).
