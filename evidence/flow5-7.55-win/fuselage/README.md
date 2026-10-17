# P-1 (F6): fuselaje en flow5 7.55 y contraste de M16 — salidas reales

Ejecutable flow5 v7.55 (SHA-256 en `../README.md`), 2026-10-16. Geometría ILUSTRATIVA: `flow5-c162-like-fuselage.json` (cuerpo NURBS de marcos elípticos,
nariz en x = −1.2 m, cola en 5.1 m, 1.1 × 1.3 m máx.) sobre el avión de `examples/flow5-c162-like.json` **con la deriva vertical** (Rx = −90°, una sola; D-52).
Todo no viscoso; `scripts/` reproduce las corridas (`p1_run.py`, `p1c.py`, `p1_tail.py`, desde la raíz); cada carpeta de `runs/` es una corrida real
(`flow5-export` + `flow5-run`, ≤ 300 s, 2–10 s las no viscosas). `../fuselage-v1-aleta-horizontal/` es el primer intento, con la deriva horizontal por error: solo historial.

## 1. flow5 acepta el cuerpo, pero solo un método lo resuelve bien
VLM1/VLM2 ignoran los paneles del fuselaje (`polar3ddlg.cpp`), así que se usan métodos de paneles. Con la deriva vertical y alpha −4…8°, paso 2°
(dCL/dα y dCm/dα en 1/rad, CG en x = 0.40 m, c = 1.181 m; x_NP = 0.40 − (dCm/dα)/(dCL/dα)·c):

| Carpeta | Método | Superficies | Fuselaje | Deriva | dCL/dα | dCm/dα | x_NP (m) | Fy máx. con β = 0 (N) |
|---|---|---|---|---|---|---|---|---|
| `v2-nofus` | VLM2 | delgadas | no | sí | 5.161 | −1.320 | 0.702 | 0.002 |
| `q-nofus` / `q-fus` | QUADS | delgadas | no / sí | sí | 5.149 / 5.027 | −1.124 / −1.763 | — | 0.006 / **776** |
| `qt-nofus` / `qt-fus` | QUADS | gruesas | no / sí | sí | 5.634 / 5.091 | −2.857 / −2.755 | — | 0.06 / **1455** |
| `tl-nofus` / `tl-fus` | TRILINEAR | gruesas | no / sí | sí | 5.136 / 4.673 | −2.066 / −1.910 | — | **121** / **415** |
| `tu-fus` | TRIUNIFORM | gruesas | sí | sí | 5.449 | −3.780 | — | 0.39 |
| `c1` / `c2` | QUADS | delgadas | sí / no | no | 5.027 / 5.149 | −1.763 / −1.124 | — | **776** / 0 |
| `c3` / `c4` | TRILINEAR | gruesas | sí / no | no | 4.609 / 5.085 | −1.131 / −1.041 | 0.690 / 0.642 | 0.001 / 0 |
| `c5` / `c6` | QUADS | gruesas | sí / no | no | 4.898 / 5.276 | −2.079 / −1.340 | — | **931** / 0 |
| **`d1` / `d2`** | **TRILINEAR** | gruesas | **sí / no** | no | **4.609 / 5.085** | **−0.676 / −1.041** | **0.573 / 0.642** | 0.001 / 0 |

(`c*` = sin deriva; `d*` = `c*` con `Include_Fuse_Moments = true`, necesario para que el momento del propio fuselaje entre en C_m: sin él, `c3`, el fuselaje solo
actúa por interferencia y sale ligeramente estabilizante.) Los métodos de paneles con fuselaje y la deriva tienen una fuerza lateral de cientos de N con β = 0 en geometría simétrica
(la malla de la deriva o del cuerpo no es simétrica): no se usan. QUADS con fuselaje también la tiene. Quedan utilizables `d1`/`d2` (TRILINEAR, ala + elevador, sin deriva; la deriva no afecta a la estática de cabeceo).
Limitación: la línea base de paneles sin fuselaje (x_NP 0.642 m) no coincide con la de VLM2 (0.702 m); por eso se compara el **incremento** del fuselaje, no el valor absoluto.

## 2. Contraste de M16 con y sin fuselaje (increment del fuselaje)
| | flow5 TRILINEAR (`d1` − `d2`) | M16 Munk-Multhopp (Ecs. 24-100 a 24-108, mismas estaciones) |
|---|---|---|
| ΔC_Mα (1/rad) | +0.365 | +0.298 (−18 %) |
| Δx_NP (m) | −0.0685 | −0.0717 (+4.7 %) |

x_NP completo: M16 sin fuselaje 0.695 m (flow5 VLM2 viscoso con deriva vertical 0.703 m, −1.2 %) y con fuselaje 0.695 − 0.072 = 0.623 m; sumando a la base de VLM2 el incremento de
paneles de flow5 resulta 0.703 − 0.069 = 0.634 m (M16 −1.7 %). El valor absoluto de TRILINEAR con fuselaje (0.573 m) no se usa por la diferencia de línea base.
El resultado es de **nivel conceptual / 3D lineal**; el signo y el orden de magnitud del aporte del fuselaje de M16 coinciden con flow5; no se ajustó ninguna constante.
Cautela: x_NP por punto varía con α en `d1` (0.662 → 0.575 m entre α = −4° y 8°) porque el momento del cuerpo no es lineal; se usó el ajuste lineal en [−4°, 8°].

## 3. Modelo de estela de M16 (∂ε/∂α = 0.39, Ec. 24-91)
`tailz-*` (VLM2, ala + elevador + deriva vertical, cola a z = −0.4, 0, 0.3 y 0.8 m): x_NP = 0.704, 0.696, 0.703, 0.717 m; ∂ε/∂α implícito (con las pendientes de Helmbold)
0.376, 0.390, 0.379, 0.356 contra 0.390 de M16. Es decir, con la deriva correcta el modelo de estela de M16 coincide con el VLM2 a pocas centésimas; la diferencia de +5.3 %
de D-43/D-44 no era de la estela sino de la deriva horizontal del modelo de flow5 (D-52). El VLM2 de estela plana varía poco con la altura de la cola.
