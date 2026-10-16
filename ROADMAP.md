# AeroSuite — Hoja de ruta (ROADMAP)

Actualizado 2026-10-14. Sustituye a `docs/ROADMAP.md`.

## Etapa 1 — Motores originales verificables (en curso)
- [x] Fuentes flow5 v7.57 y ADRpy 0.2.6 fijadas por SHA en `vendor/`
- [x] ADRpy: restricciones, pérdida, potencia, ISA, Reynolds, contraste con Gudmundsson
- [x] XFOIL real: NACA, Re/Mach/Ncrit/Xtr, barridos, puntos no convergidos, comparación
- [x] Optimizador SciPy con contrato JSON (conceptual y 2D)
- [x] Exportación de aviones/polares/guiones para `flow5 -s`
- [x] Lector de resultados de flow5 (M-F5R) desde el código escritor de flow5
- [ ] Validación Windows completa (`VALIDAR-WINDOWS.cmd`), incluida la ejecución de `flow5 -s` y la comprobación de M-F5R con salidas reales
- [ ] Biblioteca UIUC real (C-6)

## Fase F1–F2 (corrida autónoma, `auto/f1-f2`)
- [x] M01 Requisitos y base regulatoria
- [x] M02 Referencias · [x] M03 Costos · [x] M04 Restricciones (+ aterrizaje) · [x] M06 Peso inicial

## Pendientes anotados
- M03: factor de inflación opcional como dato de entrada del usuario (hoy costos de 2012, D-23); no se asume ninguno.

## Fase F3 (corrida autónoma, `auto/f3`)
- [x] M08 Cola inicial
- [x] M09a Perfiles · [x] M09b Ala · [x] M10 Geometría OML · [x] M11 Planta motriz · [x] M12 Pesos · [x] M13 CG e inercias · [x] M15 Fuselaje

## Etapa 2 — Conexiones entre motores (prioridad en este orden)
1. C-3 lector de resultados flow5 → 2. C-2 dimensionamiento ADRpy → ala flow5 → 3. C-5 CD0/k calculados → 4. C-1 polares XFOIL → flow5 → 5. C-4 optimización 3D con flow5 → 6. C-7 envolvente V-n → 7. C-8 derivadas de estabilidad.

## Etapa 3 — Modelos adicionales fundamentados
- Reactivar el alargamiento en el optimizador conceptual con el modelo W_cap ∝ AR^1.5 de M12 (D-07, C-9): pendiente, fuera de la corrida F3
- Modelo de peso (Gudmundsson Cap. 6) para optimizar AR (C-9)
- Misión, alcance y autonomía (Gudmundsson Cap. 21)
- Validación experimental de polares (fuente pendiente de incorporar a la biblioteca)

## Etapa 4 — Interfaz integrada
Diseñar la interfaz propia sobre los contratos JSON ya probados. No antes de cerrar la Etapa 2.
