# Evidencia flow5 7.55 (Windows) — salidas del solucionador real

Ejecutable: `C:\Users\oscar\Documents\flow5_v7.55_win64\flow5_v7.55_win64\flow5.exe` (8 898 048 bytes,
SHA-256 `4254b851cbda6eaf281b145e7b509756541ee064fd4b38d6b54b79ca1a8d13e1`); la bitácora de flow5 imprime `flow5 v7.55`.
El ejecutable y sus DLL no se incluyen. Fecha: 2026-10-15. Python: `.venv\Scripts\python`, `AEROSUITE_FLOW5` apuntando al exe.

* `run1-planform-ref-zero/`: `flow5-export` + `flow5-run` con el XML original (`Reference_Dimensions=PLANFORM`).
  flow5 aborta en 3.7 s: «reference chord/span/area is 0». No hay polar.
* `run2-custom-ref/`: mismo caso con referencias explícitas (`CUSTOM`, área/envergadura/MAC del ala principal).
  Comando: `python -m aerosuite flow5-export --config examples/flow5-c162-like.json --out <job>` y
  `python -m aerosuite flow5-run --job <job> --timeout 300` (script `flow5.exe -s script.xml -p`). 75 s, 17 puntos, VLM2.
  Son resultados reales de flow5 (no fixtures de formato).
