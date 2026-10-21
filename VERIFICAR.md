# VERIFICAR — guía para comprobar AeroSuite con tus libros

Esta guía dice **qué está comprobado y cómo**, y qué comprobaciones conviene que hagas tú en tu ejemplar. Todos los comandos se ejecutan en PowerShell desde la carpeta raíz del proyecto (`Aerosuite`). Los números de página de Gudmundsson son las páginas **impresas** (impr.), calculadas como página del PDF − 46; los de Etkin, PDF − 13. Pueden diferir en ±1 página: si no ves la ecuación en la página indicada, mira la anterior y la siguiente. Los números de ecuación y de ejemplo sí son exactos.

Convención de estados en la tabla (a):
- **LIBRO** = reproduce cifras impresas de un ejemplo resuelto del libro.
- **ARITMÉTICA** = solo comprueba que el cálculo repite la aritmética del libro con sus datos (no valida el modelo).
- **MOTOR REAL** = contrastado con flow5 7.55 o XFOIL 6.99 reales (resultados de los programas, no inventados).
- **SIN VALIDAR** = sin ejemplo ni motor con el que compararlo; solo pruebas de coherencia.

## (a) Qué está validado y con qué

| Módulo | Qué hace | Estado de validación |
|---|---|---|
| M01 Requisitos | Categorías Tablas 1-2/1-3 | LIBRO (Cessna 172 → nivel 2, Eclipse 550 → nivel 3). La cita «§23.2110(c) = 61 KCAS» es del Part 23 anterior; el eCFR vigente ya no la trae (D-47). |
| M02 Referencias | Estadísticas de la Tabla 6-1 | LIBRO (medias y desviaciones de la tabla). Solo esa base. |
| M03 Costos | Eastlake, Cap. 2 | LIBRO (Ejemplos 2-1 a 2-5). Valores en dólares de 2012 (D-23). |
| M04 Restricciones | Despegue, ascenso, crucero, techo, viraje, aterrizaje | LIBRO para despegue (0.1869) y aterrizaje (11.37 lbf/ft²); ascenso, viraje, crucero y techo salen de ADRpy y se contrastan con el libro (1-3 %); crucero/techo en T/W equivalente a nivel del mar. |
| M06 Peso inicial | Métodos 1, 2, 3 y eléctrico | LIBRO (Ejemplos 6-2, 6-3, 6-4; diferencias ≤ 0.04 %). |
| M08 Cola | Métodos 1-3 | LIBRO (Ejemplos 11-1 a 11-3). Método 4: SIN VALIDAR contra el libro. |
| M09a Perfiles | Matriz de decisión + XFOIL | LIBRO (prorrateo de la matriz) y MOTOR REAL (XFOIL contra teoría de perfil delgado). Las magnitudes de XFOIL no se validaron contra experimento. |
| M09b Ala | Planta, C_Lα, C_Lmax, e, volumen | LIBRO (Ejemplo 9-3, Tabla 9-7, Ejemplos 9-4 y 9-9). El volumen del Ejemplo 9-3 tiene una inconsistencia del libro (D-26). |
| M10 Geometría OML | Ensamble ala-cola-fuselaje | SIN VALIDAR contra el libro (el libro no trae ejemplo); invariantes geométricos recalculados por integración independiente. |
| M11 Planta motriz | Potencia, reductor, hélice | LIBRO (Ejemplos 7-2, 7-3, 15-2, 15-3). Altitud crítica: SIN VALIDAR. |
| M12 Pesos | 14 componentes | LIBRO solo para el ala (Ejemplos 6-5 a 6-7); el resto de ecuaciones SIN VALIDAR (sin ejemplo). |
| M13 CG e inercias | CG, envolvente, inercias | LIBRO (Ejemplos 6-8, 6-9, 6-10). Inercias: coherencia con mecánica clásica. Límites de CG: datos del usuario. |
| M15 Fuselaje | Cabina, nariz, cola, sólidos | LIBRO (Tabla 12-1; errata del tronco, D-31). |
| M16 Estabilidad | Punto neutro, C_Mα, modos | LIBRO: B747 de Etkin con **coeficientes verificados contra la página** (Tablas 6.1 y 6.6, D-45) y fuselaje por Munk-Multhopp con el Ejemplo 24-3 (D-44). MOTOR REAL: punto neutro +5.3 % y C_Mα +11.8 % respecto de flow5 7.55 (el modelo de flow5 no tenía fuselaje; no se ajustó nada). Modos dinámicos y derivadas laterales contra flow5: pendientes. |
| M18a Tren | Reacciones, vuelco, neumáticos | LIBRO (Ejemplo 13-2; Ejemplo 13-3 estático y dinámico a 40 KTAS con la Ec. 13-20, D-45). |
| M18b Mandos | Momento de charnela, fuerzas | LIBRO solo para τ_e (Ejemplo 24-6); C_Hα y C_Hδ son datos tuyos. |
| M18c Hipersustentación | Partición del ala, flaps | LIBRO (Ejemplos 10-2 y 10-3) y MOTOR REAL (XFOIL con flap, 86 % de la teoría). |
| M19 Pérdida benigna | Línea sustentadora, criterios | ARITMÉTICA/teoría (elíptica y rectangular contra fórmulas cerradas); MOTOR REAL: C_Lα con flow5 −4.6 %. |
| M20 Resistencia | Acumulación por componentes | LIBRO (Ejemplos 16-6, 16-11); MOTOR REAL: C_D viscoso mínimo contra flow5 (no comparables 1:1: flow5 sin fuselaje). |
| M21 Prestaciones | Velocidades, techos, alcance | LIBRO (Ejemplo 21-6: 737.4 / 768.2 / 950.4 nm; errata del L/D, D-42). Ascenso y techos: coherencia con formas cerradas. |
| L-1 Lazo | M01→M23 en orden de la Tabla 1-4 | LIBRO para las cifras del Ejemplo 3-1 que pasan por el lazo (S = 120 ft², W/S 11, T/W de despegue 0.1869, aterrizaje 11.37); el resto son datos ilustrativos. |
| M22 Optimizador | Motor `project` (conceptual; 3D opt-in) | Validado por **malla** (551 puntos): DE y SLSQP dan V* = 34.003 m/s y 934.2186 km frente a 34.000 y 934.2185 de la malla. 3D con flow5 7.55 real solo con bandera explícita (ala sola). |
| M23 Verificación | cumple / no cumple / no evaluable | Solo criterios con texto leído: 14 CFR 23.2110, 23.2120, 23.2130 (eCFR vigente), Tablas 1-2/1-3 y reglas del libro. El resto: `no evaluable`. No es una demostración de cumplimiento. |
| M24 STEP | OML de M10 a CAD (mm) | Reimportado con OpenCASCADE y comparado con M10 (volúmenes, áreas, envergadura, caja). **No abierto en Ansys.** |
| M25 Envolvente V-n | Maniobra + ráfaga, esquinas, carga última | LIBRO (Ejemplo 17.4.1, Tabla 17-6: V_Cmin 105.2, V_G 67.5, μ_g 14.77, K_g 0.6476, n_g +4.60/−2.60, V_A nueva 94.6 KEAS). Umbrales de categorías utilitaria/acrobática y factores de V_C/V_D por carga alar: de ADRpy 0.2.6, SIN verificar en el libro. Con flaps solo la línea de pérdida (D-55). |
| M26 Cargas para Ansys | Cargas aerodinámicas externas en las esquinas de M25 | ARITMÉTICA (equilibrio de fuerzas y de cabeceo < 1e-6, flector recalculado). SIN ejemplo del libro. MOTOR REAL (flow5 7.55 VLM2): contraste de C_l(y) solo si el C_L coincide. Solo aerodinámicas: sin estructura ni alivio de masa (D-56). |
| T-1 Traspaso | `handoff`: paquete con manifiesto SHA-256 | Prueba de integración con el ejemplo completo (no valida física). |
| P-4 M22 con peso de ala | AR con OEW de M12 | Óptimo interior verificado contra malla en el motor `project` (prueba lenta `AEROSUITE_SLOW=1`, D-57). Nivel conceptual. |
| M23 (F6) | 23.2145 | Se añadió 23.2145(a)/(b) como comprobación de signos (texto leído 2026-10-20); 23.2135 y 23.2150 siguen `no evaluable` (D-58). |

## (b) Comprobaciones que debes hacer en tu ejemplar

Para cada módulo: qué mirar en el libro y qué comando reproduce el cálculo. Las pruebas automáticas (`python -m unittest tests.test_xxx -v`) imprimen cada comprobación; los comandos de `project-init` + `mXX` usan los ejemplos de `examples/projects/` y escriben en `results\...` (usa una carpeta nueva si ya existe).

Preparación común (una vez por ejemplo):
```
.\.venv\Scripts\python.exe -m aerosuite project-init --project results\v\c162.json --name c162 --from-inputs examples\projects\c162-inputs.json
```

**M04 — Gudmundsson, Cap. 3, Ejemplo 3-1 (impr. 64-66)**
1. Paso 3, Ec. 3-1 con W/S = 10 lbf/ft²: T/W de despegue = **0.1869**.
2. Paso 8: W/S máximo de aterrizaje = **11.37 lbf/ft²** (M04 da 11.36 con ISA, ρ = 1.225 kg/m³).
3. Paso 4: T/W de ascenso = 0.2140 (M04/ADRpy da 0.2126).
```
.\.venv\Scripts\python.exe -m aerosuite m06 --project results\v\c162.json
.\.venv\Scripts\python.exe -m aerosuite m04 --project results\v\c162.json
.\.venv\Scripts\python.exe -m unittest tests.test_m04_constraints -v
```

**M06 — Cap. 6, Ejemplos 6-2 y 6-4 (impr. 151 y 156-158)**: W0 = 6069 lbf (Método 1) y 44 556 lbf (Método 3, nueve fracciones de segmento, Ec. 6-32 a 6-42). Comando: `.\.venv\Scripts\python.exe -m unittest tests.test_m06_weight -v`.

**M08 — Cap. 11, Ejemplos 11-1 a 11-3 (impr. 511-512)**: l_HT = 12.76 ft, S_HT = 50.1 ft², S_VT = 32.1 ft² (Método 2), 42.2 y 17.3 ft² (Método 3).
```
.\.venv\Scripts\python.exe -m aerosuite project-init --project results\v\tail.json --name tail --from-inputs examples\projects\gud-example-11-tail.json
.\.venv\Scripts\python.exe -m aerosuite m08 --project results\v\tail.json
```

**M09b — Cap. 9, Tabla 9-7 (impr. 367-369) y Ejemplo 9-3 (impr. 329-330)**: C_Lα de las filas de la tabla (AR 10, Λc/2 = 28.55°: 5.24 / 5.15 / 4.40 /rad); b = 32.25 ft, c_r = 5.375 ft. Mira también la **errata**: el libro imprime 10.16 ft³ de volumen de semiala; la integral exacta da 7.04 ft³ (D-26). Comando: `.\.venv\Scripts\python.exe -m unittest tests.test_m09b_wing -v`.

**M11 — Cap. 7, Ejemplo 7-2 (impr. 208-209) y Cap. 15, Ejemplo 15-2 (impr. 620-621)**: 70.4 BHP a 10 000 ft (Gagg-Ferrar), diámetros de hélice 67.2 / 61.6 / 56.0 in. Comando: `.\.venv\Scripts\python.exe -m unittest tests.test_m11_powerplant -v`.

**M12 — Cap. 6, Ejemplo 6-5 (impr. 165) y Ejemplos 6-6/6-7 (impr. 167-176)**: peso de ala en voladizo 335 lbf, con tirantes 213 lbf; W_cap = 66.3 lbf (Bonanza). Comando: `tests.test_m12_weights`. Las demás ecuaciones de peso (6-48 a 6-105) no tienen ejemplo: compáralas tú, componente por componente, con tu libro.

**M13 — Cap. 6, Ejemplos 6-8 a 6-10 (impr. 177-180, 192-194)**: 8.31 % MGC; Tabla 6-5: CG (6.939, −0.622, 0.260) ft. Comando: `tests.test_m13_cg`.

**M15 — Cap. 12, Tabla 12-1 (impr. 532)**: con D = 2, D1 = 2, D2 = 1, L = 3: cono S = 9.935, V = 3.142; **errata** del área del tronco (impreso 14.902; exacto 14.332, D-31). Comando: `tests.test_m15_fuselage`.

**M16 — Cap. 24 (Ejemplos 24-3 y 24-6) y Etkin Caps. 6**
1. Ejemplo 24-3 (SR22, Tabla 24-4, impr. 949-950): C_M0,FUS = **−0.003381** y C_Mα,FUS = **0.008671 por grado** (la Ec. 24-108 no lleva k2 − k1). Ojo con la **errata de la Ec. 24-104**: sus valores para los segmentos 1-3 de la tabla no salen de la ecuación (D-44).
2. Ejemplo 24-6 (impr. 962-964): h_n = 0.5917, C_Mα = −0.3721 /rad, C_M0 = −0.005675.
3. Etkin, Tabla 6.6 (impr. 187): C_Yβ −0.8771, C_lβ −0.2797, C_nβ 0.1946, C_lp̂ −0.3295, C_np̂ −0.04073, C_lr̂ 0.304, C_nr̂ −0.2737; autovalores de las Secs. 6.2 y 6.7 (impr. 165-188).
Comando: `.\.venv\Scripts\python.exe -m unittest tests.test_m16_stability -v`.

**M18a — Cap. 13, Ejemplos 13-2 y 13-3 (impr. 564-570)**: R_N = 357.5 lbf; cola 151.9 lbf (11.5 %) y, a 40 KTAS con δe = 0, R_T = −167.5 lbf (el texto digitalizado pierde el signo; el libro dice que la rueda de cola ya está en el aire) y R_M = 555.2 lbf. Comando: `tests.test_m18a_gear`. **Errata**: constante de energía de frenado 0.0443 (el libro imprime 0.0433).

**M18b y M18c — Cap. 24, Ejemplo 24-6 (d) (impr. 963) y Cap. 10, Ejemplos 10-2/10-3 (impr. 454-461)**: τ_e = 0.5066; C_lmax = 3.01 y C_Lmax = 1.936 (SR22). Comandos: `tests.test_m18b_controls`, `tests.test_m18c_highlift`.

**M19 — Cap. 9, Sec. 9.6.3 y Ecs. 9-139/9-140 (impr. 391-396)**: criterios de pérdida de raíz a punta, lavado de 1-4°; las Ecs. 9-139/9-140 se reconstruyeron por inversión (el signo de (2 − λ) no era legible). Comando: `tests.test_m19_stall`.

**M20 — Cap. 16, Ejemplos 16-6 y 16-11 (impr. 687-691 y 706)**: x0/c = 0.0729; FF del ala = 1.3111. Comando: `tests.test_m20_drag`.

**M21 — Cap. 21, Ejemplo 21-6 (impr. 873-879)**: 737, 768 y 950 nm. **Errata**: el libro imprime L/D máx = 19.0; el resultado (950 nm) corresponde a 15.42 (D-42). Comando: `tests.test_m21_performance`.

**M23 — 14 CFR Part 23**: lee tú mismo en https://www.ecfr.gov/current/title-14/part-23 los §23.2110, §23.2120 (8.3 % / 4 % / 3 %) y §23.2130 (50 ft) y compáralos con `python -m aerosuite m23` (cada elemento trae su referencia). Todo lo demás sale `no evaluable` a propósito.

**M25 — Cap. 17, Sec. 17.4.1, Tabla 17-6 (W = 1320 lbf, S = 130 ft²)**: comprueba (1) Paso 7: μ_g = 2(W/S)/(ρ c_MGC C_Lα g) = 14.77 y K_g = 0.88 μ_g/(5.3 + μ_g) = 0.6476 (Ec. 17-42/17-43); (2) Paso 8: n_g(V_C = 107 KEAS) = 1 + K_g U_de V C_Lα/(498 W/S) = +4.60 y −2.60 (Ec. 17-44); (3) Paso 10: la cuadrática 2.362 V² − 170.0 V − 5057 = 0 da V_A = 94.6 KEAS (Ec. 17-45). Páginas impresas ≈ 775-777 (PDF 820-822, ±1). **Errata**: la Tabla 17-6 imprime C_Lmax = 1.45, pero V_S+ = 46.3 KEAS y el Paso 10 implican 1.4 (se usó 1.4). El punto A queda en n = 4.18 (línea de pérdida a 94.6 KEAS); la Fig. 17-21 lo rotula 4.22. Comando: `python -m aerosuite m25 --project p.json`; prueba: `tests.test_m25_envelope`.

**M26 — sin cifras del libro**: comprueba (1) que la suma de fuerzas por estación de `stations.csv` (ambos semiplanos, una condición) es la sustentación del ala de `loads.json` (`totals.lift_wing_n`); (2) que n·W de cada condición es sustentación del ala + carga de cola (`tail_load_n`, negativa si es hacia abajo); (3) que el flector en la raíz es ≈ 0.42 × (fuerza de la semiala × b/2) (elíptica: 4/(3π) = 0.424) en condiciones con |C_L| > 1. Comando: `m26`; prueba: `tests.test_m26_loads`. Las columnas `cad_*_mm` usan la transformación (x, y, z) → (1000 x, 1000 z, −1000 y) del STEP de M24.

**T-1 — traspaso**: `python -m aerosuite handoff --project p.json --out paquete\` y revisa `LEEME.md`, `SUPUESTOS.md` y que `manifest.json` lista el SHA-256 de cada archivo (`Get-FileHash`). Prueba: `tests.test_handoff`.

**P-4 — M22 con peso de ala**: `python -m aerosuite m22 --spec examples\opt-project-wing-weight.json --out results\m22-wing` (≈ 5 s por evaluación). Comprueba en `evaluations.csv` que el alcance con carga máxima sube y luego baja con AR y que el peso del ala de M12 (Ecs. 6-43 a 6-47, ya validadas con el Ejemplo 6-5) crece con AR.

**M23 (F6)**: lee 14 CFR 23.2145 en el eCFR (estabilidad estática en los tres ejes y dinámica de corto periodo y balanceo holandés, texto cualitativo sin umbrales) y compara con los elementos `stability_23_2145a` y `longitudinal_divergence_23_2145b` de `python -m aerosuite m23`: solo comprueban el signo, no las fuerzas de mando.

**Contrastes con flow5 7.55 (F6)**: P-1 fuselaje (D-50, D-52): punto neutro de M16 contra flow5 con cuerpo, −1.2 % tras corregir la deriva; P-2 LLT (D-51); P-3 dinámica de M16 y C_l(η) de M19 (D-53). Las salidas reales están en `evidence/flow5-7.55-win/` (versión 7.55; el código fuente es 7.57). Puedes reproducirlas con `flow5-export` y `flow5-run`.

**M22 y M24**: no tienen cifras del libro; verifica (1) que la malla y el optimizador coinciden (`python -m unittest tests.test_m22_project_optimizer -v`) y (2) abre los STEP en tu CAD o en Ansys y comprueba que las unidades son milímetros y que la envergadura y la longitud son las de M10 (`manifest.json` las lista).

## (c) Supuestos del proyecto y erratas detectadas

**Supuestos (datos ilustrativos o del usuario, no del avión real).** Cada archivo de `examples/projects/` lleva un campo `_source` que dice qué es dato del libro y qué es supuesto; las salidas guardan `assumptions` en `project.json`. Los principales:
- Cessna 162 (Ej. 3-1): solo `m01`, `m02`, `m04`, `m06` son datos del libro; en `c162-full-loop.json` todo lo demás es ilustrativo: λ = 0.7, diedro 2°, lavado 1.5°, perfil NACA 2412 con C_lmax 1.58 y C_lα = 6.1 /rad, volúmenes de cola del Cessna 172 (0.761 y 0.0419), radios de fuselaje, posiciones de componentes, motor de 100 BHP, cargas, tren, mandos y derivadas de charnela.
- Cessna 172 (`c172-like-*.json`): pesos conocidos, motor de 160 BHP, posición de la nariz, alturas z del ala y de la cola, C_D0 de M16, límites de CG de M13 (15 %-35 %), derivadas de charnela.
- M09b: factor de eficiencia de Raymer (Ec. 9-129); M16: C_Xu = −2 C_D, C_Zu = −2 C_L, C_Mu = 0, sin efecto de hélice; derivadas laterales C_lp, C_lr, C_np, C_nr y C_lβ son dato de entrada (no hay ecuaciones legibles en el Cap. 25).
- M20: rugosidad, transición, factor CRUD 1.25 (Sec. 16.3.8), áreas parásitas; M21: η_p constante, c_P = 0.304 kg/(kW h), reservas y fracciones de combustible; M24: perfil NACA generado, borde de salida cerrado.
- Costos de M03: dólares de 2012 sin inflación (D-23).

**Erratas del libro y datos del libro que no se pudieron reproducir** (las referencias de cada una están en `DECISIONS.md`):
1. Ej. 9-3: volumen de semiala impreso 10.16 ft³ frente a 7.04 ft³ exacto (D-26).
2. Ec. 15-30: constante del paso de hélice 1215.36 (D-28).
3. Ec. 6-52 (peso de la cola vertical del Cessna): da 0.9 lbf con el exponente impreso; excluida por defecto (D-29).
4. Tabla 12-1: área del tronco de cono 14.902 impresa frente a 14.332 exacta (D-31).
5. Ec. 13-6: constante 0.0443 frente a 0.0433 impresa.
6. Ej. 3-1: el enunciado dice techo de 15 000 ft y el paso 7 usa 17 000 ft (se usa 17 000 ft).
7. Ej. 21-6: L/D máx = 19.0 impreso; el resultado corresponde a 15.42 (D-42).
8. Ec. 24-104: sus valores no reproducen los segmentos 1-3 de la Tabla 24-4 (D-44); y la Ec. 24-108 aparece sin k2 − k1, como confirma el ejemplo.
9. Ec. 25-13 (K_YVT, tramo central) y signo de (2 − λ) en 9-139/9-140: reconstruidos, no leídos (D-36, D-40).
10. «§23.2110(c) = 61 KCAS» (cita del libro): ya no figura en el eCFR vigente (D-47).
11. Ej. 13-3: el texto digitalizado pierde el signo de R_T (la rueda de cola está en el aire).

**Supuestos añadidos en F6.** M25: umbrales de ADRpy (ver arriba) y Part 23 vigente sin cifras (se usan las del libro, del Part 23 anterior a la Enmienda 23-64); M26: C_m,ac del ala por teoría de perfil delgado del perfil de raíz (−0.053 para NACA 2412), centro aerodinámico del ala en 0.25 c_MGC, fuselaje y empuje sin momento de cabeceo, sustentación vertical, resistencia solo total; M12/M21 (P-4): MTOW de M21 = 700 kg en el ejemplo para que quepan OEW + carga + combustible. **Erratas añadidas**: 12. Tabla 17-6: C_Lmax 1.45 impreso frente a 1.4 implícito en V_S+ y en el Paso 10; 13. Fig. 17-21: n del punto A rotulado 4.22 (valor de la fórmula) frente a 4.18 de la línea de pérdida.

## (d) Cómo reproducir todo en Windows

1. Instalación (una vez): `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-engines.ps1` (crea `.venv`, instala NumPy 1.26.4 y ADRpy y descarga flow5 7.57/XFOIL). Para M24: `.\.venv\Scripts\python.exe -m pip install --no-deps -r requirements-cad.txt`.
2. Motores: flow5 7.55 en `C:\Users\oscar\Documents\flow5_v7.55_win64\flow5_v7.55_win64\flow5.exe` (variable `AEROSUITE_FLOW5`) y `AEROSUITE_XFOIL` apuntando a `tools\xfoil\xfoil.exe`. Comprueba con `.\.venv\Scripts\python.exe -m aerosuite status`.
3. Validación general: doble clic en `VALIDAR-WINDOWS.cmd` o `.\.venv\Scripts\python.exe -m aerosuite validate`.
4. Pruebas: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` (la de flow5 real del optimizador es opcional: `$env:AEROSUITE_FLOW5_TESTS = "1"`).
5. Lazo completo (Cessna 162):
```
.\.venv\Scripts\python.exe -m aerosuite project-init --project results\c162-full\project.json --name c162-full --from-inputs examples\projects\c162-full-loop.json
.\.venv\Scripts\python.exe -m aerosuite loop --project results\c162-full\project.json --max-iter 5
.\.venv\Scripts\python.exe -m aerosuite export --project results\c162-full\project.json --module m23 --out results\c162-full\m23.json
```
   El lazo deja `results\c162-full\project.loop\run-001\iter-001.json` y `loop.json`. En este ejemplo M23 da `no cumple` por la envolvente de CG (el peso vacío estadístico de M12, 395.6 kg, hace que las cargas superen el MTOW del ejemplo): es el resultado esperado de los datos ilustrativos, no un error.
6. Optimizador y CAD: `... -m aerosuite m22 --spec examples\opt-project-range-speed.json --out results\m22-range` y, con el proyecto del Cessna 172: `project-init` con `examples\projects\oml-c172-like.json` + `m09b`, `m08`, `m10` y `m24` (agrega antes `"m24": {"out_dir": "results\\cad"}` a las entradas si quieres otra carpeta).

## Abrir el STEP en SolidWorks (M24, D-54)
Abre `cad\<proyecto>\<proyecto>.step` (o `examples\cad\oml-c172-like\oml-c172-like.step`) con Archivo > Abrir; en el cuadro de diálogo, tipo de archivo «STEP AP203/214/242», y pulsa Opciones si te pregunta cómo importarlo (elige «Importar como sólido»). Comprueba: (1) el ala está horizontal, con la punta a la derecha y a la izquierda, y el fuselaje avanza a lo largo de X; (2) el perfil de la raíz está en el plano Frontal (el ala sale perpendicular a ese plano, hacia ±Z); (3) los bordes de ataque y las superficies superior e inferior se ven lisos (no facetados); (4) Evaluar > Propiedades físicas del ala: envergadura (caja envolvente) igual a la de `manifest.json`. Si quieres reconstruir el ala con operaciones nativas como en el tutorial, usa los archivos de `sections\*.txt` con Insertar > Curva > Curva por puntos XYZ (unidades: milímetros).

## Abrir el STEP en SolidWorks y en Ansys (M24, D-54)
**SolidWorks**: sigue el apartado anterior. **Ansys** (SpaceClaim o DesignModeler): Archivo > Abrir > `*.step`, o desde Workbench: Geometry > Import Geometry. Comprueba, en este orden:
1. **Unidades**: al importar, el sistema de unidades del proyecto debe ser milímetros (si Workbench está en metros, el ala medirá 9 440 000 m: cámbialo a mm antes de importar). Mide la envergadura con la herramienta de medida: debe ser la de `manifest.json` de M24 (p. ej. 9 443.9 mm en el Cessna 162 del ejemplo).
2. **Ejes**: X hacia atrás, Y hacia arriba, Z a lo largo de la envergadura (ala simétrica respecto de Z = 0). Es la misma convención de las columnas `cad_x_mm`, `cad_y_mm`, `cad_z_mm` de las cargas de M26.
3. **Sólidos válidos**: cada pieza (ala, estabilizador horizontal, deriva, fuselaje) debe aparecer como un sólido (no como superficies abiertas); el ensamble tiene tantos sólidos como componentes (`assembly_solids` en `manifest.json`). Sin errores de «reparar geometría» al compartir topología.
4. **Volúmenes**: el volumen del ala en Ansys debe coincidir con `validation.checks` de `manifest.json` (tolerancia 1 %).
5. **Cargas**: para aplicar `cargas/stations.csv`, usa `force_up_n` en `+Y` como fuerza remota o puntual en `(cad_x_mm, cad_y_mm, cad_z_mm)`; la suma por condición debe ser la sustentación del ala. Estas cargas son solo aerodinámicas: la estructura y la inercia las aplicas tú en Ansys.
