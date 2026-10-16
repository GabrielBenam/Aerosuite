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
