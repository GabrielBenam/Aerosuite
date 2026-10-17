# P-3 (F6): distribución C_l(η) de M19 contra flow5 7.55

Ala sola de `examples/flow5-c162-like.json` (NACA 2412, S = 11.14 m², b = 9.44 m, torsión −1.5° en la punta, incidencia 1°), V = 55.6 m/s a 2438 m.
Corridas reales (`examples/flow5-wing-only-vlm2.json`, `flow5-wing-only-llt.json`; `flow5-export` + `flow5-run`): `vlm2-ala-sola/` (VLM2 no viscoso, α 0-10°,
puntos de operación con tabla por estación) y `llt-ala-sola/` (LLT con polares 2D de XFoil calculadas por flow5, α 0-20°, D-51). `scripts/p3_m19.py` calcula la
comparación (`m19_vs_flow5.json`); M19 usa C_lα = 2π y α_ZL = −2.08° (perfil delgado), sin viscosidad.

* **VLM2 (flow5 7.55) contra M19:** a α = 0, 4 y 10°, C_L 0.195 / 0.523 / 1.004 contra 0.204 / 0.544 / 1.053 (+4.3 %, +4.0 %, +4.9 %). Diferencia cuadrática media de C_l(η)
  (semienvergadura, 19 estaciones de flow5): 0.010, 0.025 y 0.066; el máximo de C_l se da en la raíz en ambos (η = 0.03-0.10) y M19 lo sobreestima 6 % (0.261 contra 0.246 a 0°).
* **LLT (flow5, con polar viscosa real) contra M19:** C_L 0.134 / 0.439 / 0.963 frente a 0.204 / 0.544 / 1.053 (a 0°: +52 %; a 10°: +9 %); la diferencia es la de la polar real del
  perfil (α_ZL y C_lα de XFoil frente a perfil delgado), no de la distribución en envergadura.
* **Avance de la pérdida:** con el C_lmax(Re) de las polares 2D de flow5 (1.475, 1.574, 1.629, 1.666, 1.695 a Re 1-5×10⁶; 1.658 en la raíz y 1.644 en la punta a Re 3.8 y 3.4×10⁶), la
  relación C_l/C_lmax de LLT sube en la estación más interior (η = 0.156) y alcanza 1 a α ≈ 20° (0.914 a 16°, 0.969 a 18°, 0.999 a 20°; C_L = 1.55); M19 con los mismos C_lmax predice el
  primer contacto a α = 15.0° (marco de flow5), en η = 0.1, con C_L = 1.48. Las dos son perdida desde la raíz, que avanza hacia la punta (criterio de la Sec. 9.6.3); M19 sale unos 5° antes
  porque su C_l es lineal (la polar real se aplana antes de C_lmax) y da C_Lmax 4.5 % menor que el máximo de LLT (conservador en C_L, adelantado en α). No hay datos de flow5 post-pérdida.
