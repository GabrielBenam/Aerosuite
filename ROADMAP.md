# AeroSuite — Hoja de ruta (ROADMAP)

Actualizado 2026-10-14. Sustituye a `docs/ROADMAP.md`.

## Etapa 1 — Motores originales verificables (en curso)
- [x] Fuentes flow5 v7.57 y ADRpy 0.2.6 fijadas por SHA en `vendor/`
- [x] ADRpy: restricciones, pérdida, potencia, ISA, Reynolds, contraste con Gudmundsson
- [x] XFOIL real: NACA, Re/Mach/Ncrit/Xtr, barridos, puntos no convergidos, comparación
- [x] Optimizador SciPy con contrato JSON (conceptual y 2D)
- [x] Exportación de aviones/polares/guiones para `flow5 -s`
- [x] Lector de resultados de flow5 (M-F5R) desde el código escritor de flow5
- [x] Ejecución de `flow5 -s` y comprobación de M-F5R con salidas reales de flow5 7.55 (D-32, D-33; `evidence/flow5-7.55-win`)
- [ ] Validación Windows completa con `VALIDAR-WINDOWS.cmd` y flow5 7.57 (el instalado es 7.55)
- [ ] Biblioteca UIUC real (C-6)

## Fase F1–F2 (corrida autónoma, `auto/f1-f2`)
- [x] M01 Requisitos y base regulatoria
- [x] M02 Referencias · [x] M03 Costos · [x] M04 Restricciones (+ aterrizaje) · [x] M06 Peso inicial

## Pendientes anotados
- M03: factor de inflación opcional como dato de entrada del usuario (hoy costos de 2012, D-23); no se asume ninguno.

## Fase F3 (corrida autónoma, `auto/f3`)
- [x] M08 Cola inicial
- [x] M09a Perfiles · [x] M09b Ala · [x] M10 Geometría OML · [x] M11 Planta motriz · [x] M12 Pesos · [x] M13 CG e inercias · [x] M15 Fuselaje

## Fase F4 (corrida autónoma, `auto/f4`)
- [x] V-F5 validación con flow5 7.55 real · [x] M16 Estabilidad · [x] M18a Tren · [x] M18b Controles · [x] M18c Hipersustentación (XFOIL real) · [x] M19 Pérdida benigna · [x] M20 Resistencia · [x] M21 Prestaciones
- [ ] Pendientes: derivadas de estabilidad laterales de flow5 (tipo 7) y modos dinámicos de M16 contra flow5 (hoy solo estática longitudinal); distribución C_l(η) de M19 contra flow5; derivadas de charnela C_Hα, C_Hδ (Refs. [6, 12, 27] del libro); Tabla 10-5 digitalizada; acople de η_p(J) de M11 en M21; trayectorias de carga y sistemas (Ansys, fuera de alcance)

## Etapa 2 — Conexiones entre motores (prioridad en este orden)
1. C-3 lector de resultados flow5 → 2. C-2 dimensionamiento ADRpy → ala flow5 → 3. C-5 CD0/k calculados → 4. C-1 polares XFOIL → flow5 → 5. C-4 optimización 3D con flow5 → 6. C-7 envolvente V-n → 7. C-8 derivadas de estabilidad.

## Etapa 3 — Modelos adicionales fundamentados
- Reactivar el alargamiento en el optimizador conceptual con el modelo W_cap ∝ AR^1.5 de M12 (D-07, C-9): pendiente, fuera de la corrida F3
- Modelo de peso (Gudmundsson Cap. 6) para optimizar AR (C-9)
- Misión, alcance y autonomía (Gudmundsson Cap. 21)
- Validación experimental de polares (fuente pendiente de incorporar a la biblioteca)

## Etapa 4 — Interfaz integrada
Diseñar la interfaz propia sobre los contratos JSON ya probados. No antes de cerrar la Etapa 2.

## Fase F5 (corrida autónoma, `auto/f5`)
- [x] C-1 M16: aporte del fuselaje (Munk-Multhopp)
- [x] C-2 validaciones circulares de F4 verificadas
- [x] V-1 `VERIFICAR.md` (guía de verificación para el usuario)
- [x] M24 exportación STEP de la OML con CadQuery (`requirements-cad.txt`; sin abrir en Ansys)
- [x] M22 optimizador multinivel (motor `project`; 3D opt-in)
- [x] M23 verificación de requisitos (14 CFR 23.2110/2120/2130 leídos; el resto `no evaluable`)
- [x] L-1 lazo completo M01→M21 (`python -m aerosuite loop`)
