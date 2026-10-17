# P-3 (F6): polar de estabilidad tipo 7 de flow5 7.55 y contraste de la dinámica de M16

`job/` = corrida real de `examples/flow5-c162-like-stability.json` (ala + elevador a 0.5° + deriva vertical; VLM2 no viscoso; masas puntuales y de superficies ILUSTRATIVAS que dan
un tensor de inercia no nulo: 598.74 kg, CG x = 0.580 m, I_xx 603.6, I_yy 758.2, I_zz 1349.0, I_xz 33.7 kg m²). El equilibrio (Cm = 0, L = W) cae en α = 1.50°, V = 58.13 m/s, C_L = 0.324;
la incidencia del elevador se escogió para que el equilibrio quede en un ángulo razonable (con −2° cae en 12°). flow5 usa **inercia de masa puntual** (sus masas); M16 recibe **la misma inercia**.
`contrast.json` (script `scripts/p3_dynamics.py`, módulo `aerosuite/m16_flow5_contrast.py`) contiene todo el detalle; resumen:

| Derivada | M16 | flow5 | Dif. |
|---|---|---|---|
| C_Xu | −0.0080 | −0.0080 | 0 % |
| C_Xα | 0.203 | 0.195 | +4.1 % |
| C_Zu | −0.648 | −0.648 (de su matriz de estado; la columna `CZu` del archivo, −1.2×10⁻⁵, no concuerda con ella) | 0 % |
| C_Zα | −5.326 | −5.184 | −2.7 % |
| C_Zq | −4.91 | −8.04 | +39 % (M16 omite el aporte del ala, Sec. 24.2.5) |
| C_mα | −0.386 | −0.530 | +27 % (M16 menos estable: margen 7.9 % contra 10.2 %) |
| C_mq | −19.4 | −18.5 | −5.0 % |
| C_Yβ | −0.269 | −0.259 | −4.0 % |
| C_nβ | +0.122 | +0.117 | +4.4 % |

M16 no calcula C_lβ, C_lp, C_lr, C_np, C_nr (D-34): se toman de flow5 y se declara. Cálculo en M16 de C_nβ sin fuselaje (el modelo de flow5 de este caso no tiene).
La diferencia en C_mα es la de la estática: x_NP M16 con el volumen de cola medido desde el CG, como hace `m16_stability.evaluate`, 0.673 m; con el volumen medido desde el CA del ala 0.696 m;
flow5 0.701 m (D-53).

| Modo | flow5 (su log) | M16 con las derivadas de flow5 | M16 propio (+C_lβ… de flow5) |
|---|---|---|---|
| Fugoide f (Hz) / ζ | 0.02746 / 0.00637 | 0.02745 / 0.00638 | 0.0246 / 0.0216 |
| Periodo corto f (Hz) / ζ | 0.8521 / 0.7472 | 0.8531 / 0.7472 | dos raíces reales (−4.55 y −5.66 1/s); sin los términos α̇: 0.812 / 0.817 |
| Balanceo holandés f (Hz) / ζ | 0.6139 / 0.1708 | 0.6139 / 0.1706 | 0.627 / 0.168 |
| Espiral T½ (s) | 229.8 | 229.8 | 244.9 |
| Balanceo (raíz 1/s) | −12.51 | −12.51 | −12.51 |

* Las matrices de Etkin de M16 alimentadas con las derivadas y la inercia de flow5 reproducen los modos de flow5 (fugoide, periodo corto, balanceo holandés, espiral y balanceo) a
  menos de 1 % (frecuencias) y 2 % (amortiguamientos): confirma las ecuaciones de movimiento y la convención de I_xz de M16.
* Con sus propias derivadas, M16 acierta el balanceo holandés y el balanceo (3 %), la espiral con +6.6 %, y difiere en el movimiento longitudinal: menos margen estático (C_mα −27 %), C_zq sin el ala
  y el término C_m_α̇ de M16 (que flow5 no calcula) vuelven sobreamortiguado el periodo corto; la fugoide queda 11 % por debajo en frecuencia y con ζ 3.4 veces mayor.
