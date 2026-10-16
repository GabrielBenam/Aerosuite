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

## 3b. Módulos del algoritmo F3 (corrida F3, comprobado contra `BIBLIOGRAFIA` local)

Convención: en `COMPLETO.md` de GUD la marca `[p. N]` es la página del PDF; impr. = PDF − 45 (coincide con el índice del Cap. 11: 11.4 en impr. 505).

| Módulo | Ecuación / dato | Referencia comprobada | Nota |
|---|---|---|---|
| M08 | Ecs. 11-5 y 11-6, volúmenes de cola | GUD Sec. 11.2.2, PDF 530 / impr. 485 | |
| M08 | Tabla 11-4, V_HT y V_VT por clase | GUD Sec. 11.4.1, PDF 550 / impr. 505 | leída de la figura (imagen 680) |
| M08 | Ecs. 11-14 a 11-26 (Método 1), Ejemplo 11-1 | GUD Sec. 11.4.3-11.4.4, PDF 555-556 / impr. 510-511 | Ejemplo reproducido |
| M08 | Ec. 11-27 (Método 2), Ejemplo 11-2 | GUD PDF 556 / impr. 511 | reproducido |
| M08 | Ec. 11-28 (Método 3), Ejemplo 11-3 | GUD Sec. 11.4.6, PDF 557 / impr. 512 | reproducido |
| M08 | Ecs. 11-29 a 11-35 (Método 4), Ejemplo 11-5 | GUD Sec. 11.4.7, PDF 558-560 / impr. 513-515 | solo prueba de algoritmo (Ej. 11-5 es una figura de hoja de cálculo) |
| M08 | Ecs. 9-3, 9-8 a 9-13, 9-28, 9-29 (planta trapezoidal) | GUD Sec. 9.2.2 y 9.2.5, PDF 369-371 / impr. 324-326 | los títulos del Cap. 9 de ARCHITECTURE §2 coinciden |
| M09a | Sec. 8.3.9, criterios (1)-(11), matriz y ejemplo de prorrateo | GUD PDF 355-361 / impr. 310-316 | ejemplo reproducido (t/c) |
| M09a | Tabla 8-12 (clases de perfil) | GUD PDF 356-357 / impr. 311-312 | figura; solo se registra la clase elegida |
| M09a | Sec. 8.1.4 definiciones (Cl_max, Cl_α = 2π máx., α_ZL, Cl_max/Cd_min) | GUD PDF 305-306 / impr. 260-261 | |
| M09a | Ec. 8-64 (M_crit de Shevell) y 8-67 (Korn) | GUD PDF 355-356 | 8-64 garbleada: no usada (D-25) |
| M09b | Ecs. 9-3, 9-8 a 9-16, 9-28 a 9-31; Ejemplo 9-3 | GUD Sec. 9.2.2 y 9.2.5, PDF 369-375 / impr. 324-330 | reproducido (b, c_r, c_t) |
| M09b | Ecs. 9-35 y 9-36 (volumen del ala) | GUD Sec. 9.2.6, PDF 374-375 / impr. 329-330 | el ejemplo impreso es inconsistente (D-26) |
| M09b | Tablas 9-4, 9-5; Secs. 9.3.3-9.3.5 (AR, λ, flecha, diedro, washout) | GUD PDF 377-385 / impr. 332-340 | guías |
| M09b | Ecs. 9-37 a 9-40 y Ejemplo 9-4 (AR_e por alcance) | GUD PDF 379-380 / impr. 334-335 | reproducido |
| M09b | Ecs. 9-68 a 9-73, Tabla 9-7 (C_Lα) | GUD Sec. 9.5.4, PDF 412-414 / impr. 367-369 | Tabla 9-7 reproducida (8 filas) |
| M09b | Ecs. 9-74 a 9-78, Ejemplo 9-9 (CL_max) | GUD Sec. 9.5.5, PDF 415-417 / impr. 370-372 | reproducido |
| M09b | Ecs. 9-122, 9-129; Ejemplo 9-4 y 3-1 (e) | GUD Sec. 9.5.12, PDF 428-430 / impr. 383-385 | reproducido; 9-130 no implementada |
| M10 | Dato (origen) en el borde de ataque de la raíz del ala | GUD Sec. 9.1.3, PDF 367 / impr. 322 | |
| M10 | Brazos l_HT y l_VT entre c_MGC/4 del ala y de la cola (Figs. 11-1, 11-2) | GUD Sec. 11.2.1-11.2.2, PDF 529-530 / impr. 484-485 | |
| M10 | Forma y escala; comprobaciones previas; concisión, robustez, flexibilidad | SOB Sec. 2.1.1, 2.2.1, 2.3, PDF 31-36 / impr. 13-18 | principios, no ecuaciones |
| M10 | Círculo generalizado Y(Z) = Z^N1 (1−Z)^N2 (Ec. 2.16) y fuselaje 3D por secciones | SOB Sec. 2.4.1 y 2.4.3, PDF 36-46 / impr. 18-28 | |
| M10 | Solevado lineal L(u,t) = (1−u)B1(t) + uB2(t) (Ec. 4.1) | SOB Sec. 4.1, PDF 85 / impr. 67 | |
| M11 | Ecs. 7-7 y 7-8 (Gagg-Ferrar), Fig. 7-8, Ejemplo 7-2 | GUD Sec. 7.2.1(2)-(4), PDF 252-254 / impr. 207-209 | reproducidos |
| M11 | Ecs. 7-9 y 7-10 (altitud crítica) | GUD PDF 253 / impr. 208 | reconstruida; sin ejemplo (D-28) |
| M11 | Ecs. 7-12 y 7-13 (temperatura) | GUD PDF 254 / impr. 209 | reproducidas (Ej. 7-2) |
| M11 | Ecs. 7-14 a 7-17, Ejemplo 7-3 (reductor) | GUD Sec. 7.2.3, PDF 254-255 / impr. 209-210 | reproducido |
| M11 | Ecs. 15-24 a 15-26, Ejemplo 15-2 (diámetro, velocidad de punta) | GUD Sec. 15.3.1-15.3.2, PDF 665-666 / impr. 620-621 | reproducidos |
| M11 | Ec. 15-30 (paso) y Ejemplo 15-3 (J) | GUD Sec. 15.3.3-15.3.5, PDF 666-669 / impr. 621-624 | errata de 1251 por 1215 (D-28) |
| M11 | Ec. 15-32 (η_p requerida) | GUD Sec. 15.3.4, PDF 669 / impr. 624 | caso LSA reproducido |
| M12 | Ecs. 6-43 a 6-47 (ala) y Ejemplo 6-5 | GUD Sec. 6.4.1, PDF 205-210 / impr. 160-165 | reproducidos (leídas del PDF con pdftotext) |
| M12 | Ecs. 6-48 a 6-105 (colas, fuselaje, tren, planta motriz, sistemas), Ec. 6-106 | GUD Sec. 6.4.1-6.4.2, PDF 206-210 / impr. 161-165 | transcritas, sin ejemplo; 6-52 sospechosa (D-29) |
| M12 | Ecs. 6-109 a 6-127, Ejemplos 6-6 y 6-7 (cajón directo, variación con AR) | GUD Sec. 6.5, PDF 212-221 / impr. 167-176 | reproducidos |
| M12 | Sec. 6.3 (pesos conocidos, promedio de métodos, factores de escala) | GUD PDF 204-205 / impr. 159-160 | reglas de uso |
| M13 | Ecs. 6-128 a 6-137, Ejemplos 6-8 y 6-9 (CG, % c_MGC) | GUD Sec. 6.6.3-6.6.5, PDF 222-225 / impr. 177-180 | reproducidos |
| M13 | Ecs. 6-138 y 6-139 (pesaje) | GUD Sec. 6.6.6, PDF 225 / impr. 180 | consistencia estática |
| M13 | Ecs. 6-140 a 6-151 (inercias, ejes paralelos, principales) | GUD Sec. 6.6.7-6.6.10, PDF 225-228 / impr. 180-183 | sin ejemplo; 6-150 con signo reconstruido (D-30) |
| M13 | Sec. 6.7, Tabla 6-6, Figs. 6-26 a 6-31 (envolvente, nube de cargas) | GUD PDF 228-236 / impr. 183-191 | límites son dato (M16) |
| M13 | Ecs. 6-152 a 6-157, Ejemplo 6-10 (tolerancias) | GUD Sec. 6.7.6, PDF 237-239 / impr. 192-194 | reproducido |
| M15 | Sec. 12.2.2 (nariz 1.45-1.75 d, cola 3-3.35 d) y Sec. 12.3.1-12.3.2 (procedimiento y refinamiento) | GUD PDF 564-571 / impr. 519-526 | reglas y rangos |
| M15 | Sec. 12.3.3-12.3.4 (22x43x65 in, pasillo 20x76 in, 20 in por persona) | GUD PDF 571-573 / impr. 526-528 | reglas |
| M15 | Ecs. 12-1 a 12-17, Tabla 12-1 (áreas y volúmenes de sólidos) | GUD Sec. 12.4, PDF 575-580 / impr. 530-535 | reproducidas; errata del tronco (D-31) |
| M08 | Sec. 11.4.2 (V_HT desde h_n) | GUD PDF 553 / impr. 508 | ecuación garbleada: no implementada (D-24) |

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
| M03 | Modelo de costo de desarrollo de Eastlake (QDF, CER 1–10) y fijo/variable | GUD Sec. 2.2.1, Ecs. 2-7 a 2-20, PDF 84–88 / impr. 39–43; tarifas de 2012 ($92/$61/$53 por h), PDF 86 |
| M03 | Costo de motor de pistón (Ec. 2-21), descuento de tren fijo ($17 500), precio de hélices e aviónica como datos | GUD PDF 88–90 / impr. 43–45; Tabla 2-2 de aviónica es un rango de precios (dato de entrada) |
| M03 | Costo operativo directo de aeronave privada | GUD Sec. 2.3.1, Ecs. 2-38 a 2-47, PDF 95–97 / impr. 50–52 |
| M04 | Aterrizaje: distancia total (Ec. 3-13) y de rodadura (Ec. 3-14), con S_A, S_F, S_FR, S_BR | GUD Sec. 3.2.1 ítem (9), PDF 106 / impr. 61; deducción Apéndice D "Step 5/6", PDF 1121–1122 / impr. 1076–1077. Las ecuaciones digitales están garbladas: se reconstruyó a partir de la deducción (tan 3° = 1/19.08; V_BR = 1.1 V_S0, 1.21 = 1.1², 1.556 = 1.1·√2, q medio = 0.605 (W/S)/CLmax) y se comprobó con el paso 8 del Ejemplo 3-1 (D-20) |
| M04 | Despegue Ec. 3-1 y Ejemplo 3-1 (Cessna 162) | GUD Sec. 3.2.1 Ec. 3-1, PDF 104 / impr. 59; Ejemplo 3-1 pasos 1–10, PDF 109–111 / impr. 64–66 |
| M06 | Método 1: peso bruto con razones históricas (Ec. 6-9), Ejemplo 6-2 | GUD Sec. 6.2.1, PDF 195–196 / impr. 150–151 |
| M06 | Método 2: We/W0 = A + B ln W0 por clase (sailplane, powered sailplane, LSA tierra/anfibio, GA monomotor, bimotor pistón, bimotor turbohélice, agrícola, jet de negocios) | GUD Ecs. 6-16 a 6-24, PDF 197–198 / impr. 152–153. Coeficientes leídos del PDF original con `pdftotext`; signos y pares lbf/kg verificados por la identidad A_kg = A_lbf + B·ln(2.2046) |
| M06 | Método 3: fracciones por segmento (taxi/despegue, ascenso, crucero, descenso, espera, reserva, aterrizaje), Ec. 6-29 y Ejemplo 6-4 | GUD Sec. 6.2.3, Ecs. 6-25 a 6-42, PDF 198–201 / impr. 153–156; Ejemplo 6-4, PDF 202–204 / impr. 157–159 |
| M06 | Aeronave eléctrica (Hepperle): Ecs. 6-10 a 6-15 y Ejemplo 6-3 | GUD PDF 196–197 / impr. 151–152 |

## Fase F4 (M16, M18a-c, M19, M20, M21)
Convención: PDF = marcador `[p. N]` del texto convertido (`COMPLETO.md`) de cada libro; impreso = PDF − 46 en Gudmundsson y PDF − 13 en Etkin; ±1 página. Las páginas de ecuaciones sueltas no se verificaron una a una (se cita el rango de la sección).

| Módulo | Contenido | Fuente (autor, obra, capítulo, PDF) |
|---|---|---|
| M16 | Gradiente de estela, punto neutro, CM_α, CM0, SM | Gudmundsson, *General Aviation Aircraft Design* 2.ª ed., Cap. 24 (Secs. 24.2.5, 24.2.8, 24.3.4, Ejemplo 24-6), PDF 987–1010 |
| M16 | CN_β y CY_β de cola vertical y fuselaje | Gudmundsson, Cap. 25 (Sec. 25.3), PDF 1034 y ss. (ecuaciones 25-12 a 25-14, 25-27 a 25-29; K_YVT central reconstruido, D-36) |
| M16 | Matrices de estado, B747 (fugoide, periodo corto, espiral, balanceo, holandés), fugoide de Lanchester | Etkin y Reid, *Dynamics of Flight* 3.ª ed., Secs. 4.9, 6.2, 6.3, 6.7, PDF 120, 178, 185, 201 (coeficientes laterales de la Tabla 6.6 no están en el texto convertido: se validan por los autovalores impresos, D-35) |
| M18a | Tren de aterrizaje: trazado, vuelco, cargas, giro, huella, frenos | Gudmundsson, Cap. 13 (Secs. 13.2, 13.3; Ejemplos 13-2 y 13-3), PDF 590–615; 14 CFR §23.725, §23.735, §23.925(a) citados por el libro (no consultados directamente) |
| M18b | Momentos de charnela, ganancias, flotación, τ_e | Gudmundsson, Sec. 24.4 y Ec. 24-86, Tabla 24-6, Ejemplo 24-6 (d), PDF 990, 1009, 1013–1017 |
| M18c | Flaps: Ec. 10-1, Tabla 10-5 (datos de entrada), partición del ala | Gudmundsson, Cap. 10 (Secs. 10.3, 10.4; Ejemplos 10-2 y 10-3), PDF 479–507; XFOIL 6.99 (Drela) con GDES/FLAP |
| M19 | Línea sustentadora, perdida en envergadura, criterios | Gudmundsson, Secs. 9.5.4, 9.6, 9.7.3 (Ejemplos 9-9 y 9-10), PDF 416–452; Anderson, *Fundamentals of Aerodynamics* Sec. 5.3 (conocimiento externo, no verificado en la carpeta) |
| M20 | Resistencia por componentes | Gudmundsson, Cap. 16 (Secs. 16.3.1 a 16.3.9; Ejemplos 16-6, 16-7, 16-11), PDF 726–758 |
| M21 | Prestaciones, alcance, carga útil–alcance | Gudmundsson, Secs. 3.2, 7 (Gagg-Ferrar), Caps. 19–21 (Ejemplos 21-2 y 21-6), PDF 107, 253, 858–925 |
