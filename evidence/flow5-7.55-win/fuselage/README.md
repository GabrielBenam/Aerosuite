# P-1 (F6): fuselaje en flow5 7.55 — salidas reales

Ejecutable: flow5 v7.55 (`AEROSUITE_FLOW5`, SHA-256 en `../README.md`). Fecha: 2026-10-16. Geometría: `examples/flow5-c162-like-fuselage.json`
(avión de `flow5-c162-like.json` más un cuerpo NURBS de marcos elípticos; geometría ILUSTRATIVA). Todas las carpetas son corridas reales
(`flow5-export` + `flow5-run`, ≤ 300 s); los scripts que las generan están en `scripts/` (`p1_run.py`, `p1_tail.py`, ejecutar desde la raíz).
Todas son no viscosas salvo `fus-quads` (viscosa; no terminó en 300 s: XFoil en el vuelo fallaba en la cola, puntos descartados).

| Carpeta | Método | Superficies | Fuselaje | dCL/dα (1/rad) | dCm/dα (1/rad) | XNP del log |
|---|---|---|---|---|---|---|
| `v2-nofus` | VLM2 | delgadas | no | 5.10 | −1.087 | 0.65 m |
| `q-nofus` | QUADS | delgadas | no | 5.45 | −2.199 | 0.96 m |
| `q-nofus-thick` | QUADS | gruesas | no | 5.64 | −1.945 | 0.62 m |
| `q-fus-thick` | QUADS | gruesas | sí | 5.09 | −2.485 | 0.66 m |
| `fus-quads-inviscid` | QUADS | delgadas | sí | ≈3.9 | Cm crece con α | −11.98 m |
| `t-nofus` / `t-fus` | TRIUNIFORM | gruesas | no / sí | −105 / −380 | sin sentido | 5.4 / 5.9 m |
| `tl-nofus` | TRILINEAR | gruesas | no | 5.69 | −1.964 | 0.71 m |
| `tl-fus` | TRILINEAR | gruesas | sí | 5.20 | −2.319 | 0.79 m |

Hallazgos:
1. **flow5 7.55 acepta el cuerpo** del XML (`<body>`, `Type NURBS`) y lo ensambla (908 elementos); VLM1/VLM2 ignoran los paneles del fuselaje
   (texto de `polar3ddlg.cpp`), por eso hay que usar QUADS o triangulares.
2. **Los métodos de paneles no dan un resultado utilizable para el contraste**: con superficies delgadas que cruzan el cuerpo, QUADS da XNP −12 m
   y un Cm que crece con α; con superficies gruesas y fuselaje, QUADS tiene fuerza lateral no nula con β = 0 en geometría simétrica (`Fy_sum` ≠ 0, `Vz` de
   decenas de m/s a α = 0); TRIUNIFORM da pendientes absurdas; TRILINEAR da C_D negativo y un XNP por punto que cae de 1.04 a 0.80 m al subir α.
   La línea base sin fuselaje cambia con el método (XNP 0.65 / 0.62 / 0.71 m) más que el efecto buscado, y dCm/dα no cumple dCm/dα = −dCL/dα·SM
   (p. ej. −1.95 contra −1.04). Con fuselaje, dCm/dα sale más estable en ambos métodos que sí resuelven (−1.95 → −2.49; −1.96 → −2.32), contrario
   al signo físico de Munk-Multhopp; no se interpreta como efecto del fuselaje, sino como ruido del ensamble ala-cola-cuerpo de 7.55 en modo por lotes.
   **Contraste de M16 con fuselaje: BLOQUEADO** (M16 no se altera).
3. **Diagnóstico del modelo de estela** (`tailz-*`, VLM2 sin fuselaje, cola a z = −0.4, 0, 0.3 y 0.8 m): con XNP = x_CG − (dCm/dα / dCL/dα) c:
   0.657, 0.640, 0.652, 0.661 m (variación 0.02 m en 1.2 m de altura; el VLM2 de estela plana casi no ve la altura). Con M16 (0.695 m) la diferencia
   es 0.043 m. El ∂ε/∂α que reproduce el XNP de flow5 con las pendientes de Helmbold es 0.43–0.48 frente a 0.39 de la Ec. 24-91 (con la pendiente de flow5,
   5.11, en lugar de la de Helmbold, 4.91: 0.42–0.46). Es decir, la diferencia de +5.3 % es compatible con una estela más intensa en el VLM2 (interferencia
   ala-cola resuelta) que en la cantidad de movimiento, pero el valor implícito mezcla también la pendiente de la cola; es solo diagnóstico.
