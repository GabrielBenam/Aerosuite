# P-2 (F6): LLT de flow5 7.55 — diagnóstico y soporte

Ejecutable flow5 v7.55; ala de `examples/flow5-c162-like.json` sola (NACA 2412, S = 11.14 m², b = 9.44 m, torsión −1.5° en la punta, incidencia 1°),
V = 55.6 m/s a 2438 m, α = −2…10°. Comandos: `flow5-export --config llt-config.json` y `flow5-run --timeout 300`.

* `a-sin-polares-2d-falla/`: LLT sin polares 2D. Mensaje exacto de flow5 en el log: `LLT analysis completed ... Errors encountered` (0 puntos).
  Causa (código fuente, `flow5-lib/analysis3d/llttask.cpp`): LLT no usa panel ni XFoil en el vuelo; interpola C_l(α, Re), C_d, C_m del perfil en las
  polares 2D tipo 1 de la base de datos de objetos (`Objects2d::getPlrPointFromAlpha`) y, si no hay polar para el perfil, la interpolación falla y la
  corrida termina con error. El script de lotes no crea esas polares por sí solo.
* `c-con-polares-2d/`: mismo caso con `analysis.foil_polars` (nuevo en `flow5_xml.py`): el script incluye una sección `<Foil_analysis>` con
  polares tipo 1 de XFoil (Re = 1, 2, 3, 4, 5 × 10⁶, N_crit 9, α −8…18° cada 0.5°) que flow5 calcula antes del análisis del avión. Resultado:
  `LLT analysis completed successfully`, 5 puntos de operación, 16 s. El Re de la mitad del ala (3.9×10⁶) queda dentro del rango.
* `vlm2-ala-sola-no-viscoso/`: VLM2 del mismo ala sola, no viscoso.

| α (°) | C_L LLT (flow5) | C_D LLT | C_L VLM2 (flow5) | C_D VLM2 | C_L línea sustentadora M19 |
|---|---|---|---|---|---|
| −2 | −0.0324 | 0.00672 | 0.0306 | 0.00007 | 0.0337 |
| 0 | 0.1341 | 0.00728 | 0.1952 | 0.00145 | 0.2036 |
| 4 | 0.4385 | 0.0152 | 0.5227 | 0.01044 | 0.5435 |
| 10 | 0.9632 | 0.04795 | 1.0037 | 0.03862 | 1.0533 |

Pendiente C_Lα (1/rad, ajuste lineal −2…10°): LLT 4.743; VLM2 4.650; M19 4.868 (M19 contra VLM2 +4.7 %, contra LLT +2.6 %). M19 usa C_lα de perfil 2π,
α_ZL = −2.08° (teoría de perfil delgado) y ninguna viscosidad; el C_L de LLT es 0.06-0.09 menor a incidencias bajas por la polar viscosa real de XFoil
(α_ZL y C_lα del perfil reales, Re 1-5×10⁶). C_D de LLT incluye el arrastre de perfil de XFoil; el de VLM2 es solo inducido. La comparación es de nivel
conceptual / 3D lineal; ninguna cifra se ajustó.
