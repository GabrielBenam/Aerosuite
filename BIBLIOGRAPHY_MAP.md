# AeroSuite — Mapa bibliográfico (BIBLIOGRAPHY_MAP)

Fecha de verificación: 2026-10-14. Verificado por búsqueda de texto en las conversiones `* - COMPLETO.md` de la carpeta `BIBLIOGRAFIA` (marcas `[p. N]` = página del PDF) y en el texto extraído con `pdftotext` del PDF de Drela.

**Convención de páginas.** `PDF n` es la página del archivo PDF. `impr. n` es la página impresa del libro, calculada con un desfase comprobado en al menos dos puntos por obra: Gudmundsson impr. = PDF − 45; Drela impr. = PDF − 25; Diston impr. = PDF − 19; Sóbester & Forrester impr. = PDF − 18; Etkin impr. = PDF − 12. Para Anderson no se determinó el desfase: se cita sección y página PDF.

**Alcance.** Cada fila indica qué respalda la referencia, no que AeroSuite implemente la ecuación. Las ecuaciones las ejecutan los motores originales (ADRpy, XFOIL, flow5); la bibliografía sirve para comprobar supuestos, rangos de validez y resultados. No se reproduce texto de las obras.

Abreviaturas: **GUD** Gudmundsson, *General Aviation Aircraft Design: Applied Methods and Procedures*, 2.ª ed. · **DRE** Drela, *Flight Vehicle Aerodynamics*, MIT Press 2014 · **DIS** Diston, *Computational Modelling and Simulation of Aircraft and the Environment*, Vol. 1 · **AND** Anderson, *Fundamentals of Aerodynamics* · **SOB** Sóbester & Forrester, *Aircraft Aerodynamic Design: Geometry and Optimization* · **ETK** Etkin & Reid, *Dynamics of Flight: Stability and Control* · **LY** Ly, *Stability and Control of Flight Vehicle* (notas UW, 1997) · **COR** Corke, *Design of Aircraft*.

## 1. ADRpy 0.2.6 — atmósfera, dimensionamiento y prestaciones

| Función ADRpy (módulo) | Método / ecuación | Referencia comprobada | Aplicación en AeroSuite | Limitaciones |
|---|---|---|---|---|
| `atmospheres.Atmosphere` (ISA, desviación `offset_deg`), `airdens_kgpm3`, `vsound_mps`, `eas2tas` | Atmósfera estándar ISA; altitud geopotencial | DIS Cap. 6 "Atmosphere": Standard Atmosphere Models e ISA Constants and Relationships PDF 256 / impr. 237; Geopotential Altitude PDF 259 / impr. 240. GUD Sec. 17.2 Atmospheric Modeling PDF 801 / impr. 756. DRE Sec. 1.1 Atmospheric Properties impr. 1 | Condiciones de vuelo para todos los motores (ρ, a, μ para Reynolds) | ISA idealizada; humedad no incluida en el modelo estándar |
| `atmospheres.mil_hdbk_310` | Atmósferas de referencia caliente/fría | DIS Cap. 6 Reference Atmospheres PDF 270 / impr. 251 | Casos de día caliente/frío | Solo los perfiles tabulados por ADRpy |
| `constraintanalysis.AircraftConcept.twrequired_to` | T/W para carrera de despegue dada | GUD Sec. 3.2.1, ítem (1) y Ec. (3-1) PDF 104 / impr. 59; deducción PDF 107. GUD Cap. 18, Sec. 18.2 PDF 835 / impr. 790 | Restricción de despegue en el diagrama W/S–T/W | μ de rodadura y CL/CD de despegue son datos de entrada, no se predicen |
| `twrequired_clm` | T/W para régimen de ascenso | GUD Sec. 3.2.1 (constraint analysis) PDF 104–106; Cap. 19, Sec. 19.2 PDF 857 / impr. 812 | Restricción de ascenso | Polar parabólica (CD0 + k·CL²) |
| `twrequired_crs` | T/W para crucero a velocidad y altitud dadas | GUD Sec. 3.2.1 PDF 105; Cap. 20, Sec. 20.2 PDF 879 / impr. 834 | Restricción de crucero | Polar parabólica; sin compresibilidad salvo factor del usuario |
| `twrequired_sec` | T/W para techo de servicio | GUD Sec. 3.2.1 ítem (7), Ec. (3-11) PDF 106 / impr. 61; deducción PDF 108 (techo = ROC 100 ft/min) | Restricción de techo | Definición de techo según el autor; ADRpy usa su propia definición de ROC en el techo (ver docstring) |
| `twrequired_trn` | T/W para viraje sostenido a factor de carga n | GUD Sec. 3.2.1 ítem (4) PDF 105 / impr. 60 | Restricción de viraje | Viraje coordinado estacionario |
| `wsmaxcleanstall_pa`, `vstall_kias` | W/S máxima por velocidad de pérdida | GUD Sec. 3.2.3 (1) CLmax para pérdida deseada PDF 112 / impr. 67 | Límite vertical del diagrama | CLmax es dato de entrada |
| `powerrequired`, `tw2pw` | Conversión T/W ↔ P/W con eficiencia de hélice | GUD Sec. 3.2.2 motores de pistón aspirados PDF 109 / impr. 64; Cap. 15 hélices PDF 642 / impr. 597 (momento: Sec. 15.5 PDF 683) | Dimensionamiento de planta motriz de hélice | ηp constante o dada por el usuario |
| `oswaldspaneff1…4`, `induceddragfact` | Eficiencia de Oswald e factor k | GUD Ec. (9-129), Cap. 9 (aplicada en PDF 113, 380, 429). DRE Sec. 5.6.3 Induced drag relations impr. 108 | Polar parabólica del concepto | Correlaciones empíricas; validar con flow5 (Trefftz) |
| `propulsion.PistonDeck`, `TurbopropDeck`; `atmospheres.pistonpowerfactor`, `turbopropthrustfactor` | Variación de potencia/empuje con altitud | GUD Cap. 7 Selecting the Powerplant PDF 242 / impr. 197; Cap. 14 turbinas PDF 618 / impr. 573 | Lapse de motor en restricciones | Solo motores incluidos en los datos de ADRpy |
| `airworthiness.CertificationSpecifications.flightenvelope` | Diagrama V-n (maniobra y ráfaga) CS-23 | GUD Sec. 17.4 The Structural Envelope y 17.4.1 paso a paso PDF 814 / impr. 769 | Envolvente de vuelo preliminar | Párrafos CS-23 implementados por ADRpy (333, 335, 337, 341); no sustituye la certificación |

Caso de contraste numérico disponible: GUD presenta un ejemplo resuelto de diagrama de restricciones (aeronave con S_G < 640 ft, ROC 880 ft/min, viraje n = 1.155 a 8000 ft, crucero 108 KTAS, techo 15 000 ft; PDF 109 / impr. 64). Es el candidato para validar el comando `size` con unidades convertidas.

## 2. XFOIL 6.99 — análisis 2D de perfiles

| Elemento | Método | Referencia comprobada | Aplicación | Limitaciones |
|---|---|---|---|---|
| Solver inviscido | Método de paneles con vorticidad lineal + condición de Kutta | DRE Cap. 2 (Kutta, Kutta-Joukowsky, PDF 62–67); AND Sec. 4.10 Vortex Panel Numerical Method PDF 392; AND Sec. 3.17 Source Panel Method PDF 307 | Distribución de Cp y CL inviscido | Flujo potencial 2D |
| Acoplamiento viscoso | Capa límite integral acoplada (Newton) | DRE Sec. 4.12.2 Viscous/inviscid coupling PDF 112 / impr. 87; menciona XFOIL y MSES PDF 113 y 116. DRE Sec. 3.5 (modelo de transpiración de XFOIL, figura PDF 78) | CD de perfil, separación | Pierde fiabilidad tras pérdida profunda; puntos no convergidos deben registrarse |
| Transición | Criterio e^N (amplificación de ondas TS, Ncrit) | DRE Sec. 4.14 Transition y 4.14.2 TS-wave natural transition prediction PDF 118 / impr. 93 | Parámetro Ncrit y Xtr forzado | Ncrit depende de turbulencia del túnel/atmósfera |
| Compresibilidad | Corrección Karman-Tsien en XFOIL; teoría Prandtl-Glauert | DRE Sec. 8.6 Prandtl-Glauert Analysis impr. 173 / PDF 198 | Mach < ≈0.5 subsónico | No apto para transónico |
| Efecto de Reynolds y selección de perfiles | Polares, CLmax, efecto de Re | GUD Cap. 8 The Anatomy of the Airfoil PDF 302 / impr. 257; Sec. 8.3.2 Effect of Reynolds Number; menciones a XFOIL PDF 311, 323, 326, 341 | Criterios para comparar perfiles | Comparaciones solo válidas a igual Re, Mach, Ncrit, Xtr |
| Geometría NACA 4 dígitos | Distribución de espesor y curvatura | SOB Cap. 6, NACA Four-Digit Section (índice PDF 10–11) | Generador `naca4` existente | El borde de salida cerrado (a4 = −0.1036) es una variante; registrar cuál se usa |
| Automatización XFOIL desde Python | Archivos `.dat`/`.in` y ejecución por lotes | SOB Cap. 11 Basic Aerofoil Analysis: 11.1 y 11.2 "Running XFOIL from Python" impr. 218–219 / PDF 236–237 | Adaptador `xfoil` de AeroSuite | — |

## 3. flow5 v7.57 — aerodinámica 3D, estabilidad

Métodos declarados en el código original (`flow5-lib/api/enums_objects.h`): `LLT, VLM1, VLM2, QUADS, TRILINEAR, TRIUNIFORM`; tipos de polar `T1…T8` (velocidad fija, sustentación fija, planeo, control, estabilidad, T8).

| Método flow5 | Fundamento | Referencia comprobada | Aplicación | Limitaciones |
|---|---|---|---|---|
| LLT (no lineal, con polares viscosas 2D) | Línea sustentadora de Prandtl; versión numérica no lineal | DRE Sec. 5.5 Lifting-Line Analysis PDF 129 / impr. 104 y Apéndice E Prandtl Lifting-Line Wing Theory impr. 259. AND Sec. 5.3 PDF 459 y Sec. 5.4 Numerical Nonlinear Lifting-Line Method PDF 488. GUD Sec. 9.7 PDF 444 / impr. 399 | Alas rectas de alto alargamiento con polares XFOIL | Inadecuado para flecha alta, bajo AR, superficies múltiples |
| VLM1 / VLM2 | Método de red de vórtices (herradura / anillo) | DRE Sec. 6.5 Vortex Lattice Method impr. 130 / PDF 155; 6.5.6 Trefftz-plane force calculation impr. 135; 6.5.7 Stability and control derivative calculation impr. 136. AND Sec. 5.5 Lifting-Surface Theory and VLM PDF 492–497 | Cargas, CL, Cm, CDi, derivadas de estabilidad | Inviscido; resistencia de perfil solo por interpolación de polares |
| QUADS / TRIUNIFORM / TRILINEAR (paneles 3D) | Paneles de fuente/doblete; estela | DRE Cap. 2 (equivalencia vórtice-doblete, Sec. 2.5 impr. 29) y Sec. 5.8.2 Discrete panel method for a general wake impr. 114; DRE Sec. 7.6 Unsteady Panel Method impr. 149 | Fuselaje + ala, superficies gruesas | Sensible a calidad de malla |
| Resistencia inducida en Trefftz | Integral de campo lejano | DRE Sec. 5.6 Idealized Far-Field Drag impr. 106; 5.8 Trefftz Plane Integral Evaluation impr. 112; 5.10 Minimum Induced Drag impr. 116 | CDi y eficiencia de envergadura | Estela plana idealizada |
| Polares de estabilidad (T7) y modos dinámicos | Derivadas de estabilidad, ecuaciones linealizadas, autovalores | ETK Cap. 5 The Stability Derivatives impr. 129 / PDF 141; Cap. 6 modos (fugoide, período corto, ejemplo PDF 178–179). DRE Cap. 9, Secs. 9.9–9.13 impr. 208–216. LY Cap. 4 Static Longitudinal Stability PDF 38 | Estabilidad estática y dinámica | Derivadas cuasiestáticas lineales |
| Estabilidad estática, punto neutro, margen estático | Momento de cabeceo total | GUD Cap. 24 Sec. 24.2 PDF 976 / impr. 931; Cap. 25 lat-dir PDF 1020 / impr. 975. ETK Cap. 2 (punto neutro, PDF 24 y 36) | Posición de CG y dimensionamiento de cola | — |
| Ejes y transformaciones | Ejes cuerpo/estabilidad/viento, ángulos de Euler | DRE Sec. 6.2 y 9.2 impr. 124 y 201; Apéndice F impr. 265. DIS Cap. 2 Platform Kinematics: Euler Angles PDF 56 / impr. 37 | Intercambio de resultados con convención de signos explícita | Verificar convención de flow5 al exportar |
| Compresibilidad en 3D | Prandtl-Glauert | DRE Sec. 8.6 impr. 173 | Corrección subsónica | — |

## 4. Optimizador (SciPy)

| Elemento | Referencia comprobada | Aplicación | Limitaciones |
|---|---|---|---|
| Jerarquía de objetivos, objetivos en competencia, selección del método de optimización | SOB Sec. 2.7.1–2.7.3 impr. 31–35 / PDF 49–53 (uso de Nelder-Mead PDF 42; híbrido genético + Nelder-Mead PDF 44) | Elección de método (SLSQP con restricciones, Nelder-Mead sin gradiente, evolución diferencial global) | El libro no prescribe un único método |
| Comprobaciones previas a la optimización y parametrización | SOB Sec. 2.2.1 Pre-Optimization Checks PDF 31 / impr. 13; Cap. 7 Aerofoil Parameterization impr. 123 | Variables de decisión acotadas y con sentido físico | — |
| Sensibilidades (diferencias finitas, diferenciación algorítmica) | SOB Cap. 10 Design Sensitivities impr. 199 | Gradientes numéricos con paso controlado | XFOIL produce ruido numérico: gradientes por diferencias finitas pueden ser poco fiables |
| Caso de estudio de optimización aerodinámica con XFOIL | SOB Cap. 12 Human-Powered Aircraft Wing Design (restricciones 12.1, optimización 12.4, NACA 4 dígitos 12.4.1) impr. 223–226 | Referencia de flujo de trabajo para la optimización 2D | Caso específico |
| Optimización conceptual por diagrama de restricciones / estudios de compromiso | GUD Sec. 3.3 Introduction to Trade Studies y 3.4 Introduction to Design Optimization (índice PDF 8) | Optimización W/S–T/W (o P/W) sobre ADRpy | No es optimización aerodinámica 3D |
| Optimización de flow5 | `flow5-app/interfaces/optim/` (enjambre de partículas, diálogo `optimplanedlg`); el README de v7.57 la declara "currently inoperative" | No utilizable de forma fiable en v7.57 | Confirmar en la aplicación antes de usarla |

## 5. Obras complementarias disponibles (no verificadas por capítulo)

Houghton & Carpenter, *Aerodynamics for Engineering Students*; Torenbeek, *Synthesis of Subsonic Airplane Design*; Corke, *Design of Aircraft* (Cap. 3 Wing Loading Selection, índice PDF 7); *Foundations of Aerodynamics* (Kuethe & Chow); Dowell, *A Modern Course in Aeroelasticity*; Zipfel, *Modeling and Simulation of Aerospace Vehicle Dynamics*; *Electric Aircraft Dynamics*; *Fundamentals of Aircraft and Airship Design Vol. 2*. Se consultarán al verificar casos específicos; no se citan sin comprobar la página.

## 6. Limitaciones de este mapa

1. Las conversiones a Markdown contienen ecuaciones marcadas "[verificar fórmula]"; cualquier ecuación que se use para validar debe contrastarse con el PDF original o el anexo de figuras.
2. Hay dos copias de Gudmundsson en BIBLIOGRAFIA (`... Procedu` y `... Procedu (5aca4cf0)`); se usó la segunda. La numeración de páginas PDF corresponde al mismo PDF fuente (1146 páginas).
3. Las páginas impresas de Anderson no se calcularon; usar sección + página PDF.

## 7. Módulos del algoritmo F1–F2 (corrida autónoma)

Verificado el 2026-10-14 contra `General Aviation Aircraft Design ... - COMPLETO.md` (marcas `[p. N]` = página PDF; impresa = PDF − 45).

| Módulo | Contenido | Referencia comprobada |
|---|---|---|
| M01 | Límites de peso, ocupantes y factores de carga por categoría (Commuter/Normal/Utility/Aerobatic) | GUD Tabla 1-2, PDF 58 / impr. 13. Las celdas fusionadas (12 500 lbf, 9 ocupantes) se aplican a Normal, Utility y Aerobatic (DECISIONS D-17). n⁺ Normal = 2.1 + 24000/(W+10000) acotado a 3.8 (base 14 CFR §23.337 citada por el libro) |
| M01 | Niveles de certificación por asientos y nivel de desempeño (V_NO/V_MO > 250 KCAS o M_MO > 0.6) | GUD Tabla 1-3, PDF 58 / impr. 13; casos resueltos del texto (Cessna 172 = Nivel 2 bajo; Eclipse 550 = Nivel 3 alto), PDF 58 |
| M01 | V_SO ≤ 61 KCAS monomotores y multimotores ≤ 6000 lbf | GUD cita §23.2110(c), PDF 57 / impr. 12 |
| M02 | Base de referencia de 17 LSA con We, W0, Qf, Wf y sus razones; promedios y desviaciones | GUD Tabla 6-1, PDF 196 / impr. 151 (datos leídos de la imagen de la tabla; el libro advierte que provienen de sitios de fabricantes y pueden tener pesos erróneos) |
| M02 | Forma de regresión We/W0 = A + B ln W0 y principio de no mezclar clases/propulsión | GUD Sec. 6.2.1 guía y Sec. 6.2.2, PDF 195–198 / impr. 150–153. Coeficientes publicados (kg) 1.4343/−0.1402 y (lbf) 1.5451/−0.1402 de la Ec. 6-18 coinciden con el desplazamiento B·ln(0.45359237) |
