# Evidencia: XFOIL real con flap (M18c)

**Resultados del solucionador real XFOIL 6.99 (no son fixtures de formato ni datos sinteticos).**

- Fecha: 2026-10-15. Ejecutable: `tools/xfoil/xfoil.exe` (no incluido), SHA-256 `c17342f84ae260c2b11a74cd0e2fb8189a5f8954c6bb7a8467a0f27055c7faea`.
- Entrada: `examples/projects/c172-like-highlift-inputs.json` (NACA 2412, Re = 3e6, Ncrit 9, barrido alpha -4 a 22 deg paso 1; flap con charnela en x/c = 0.70, deflexiones 10 y 30 deg por GDES/FLAP).
- Comando: `python -m aerosuite project-init --project p.json --name h --from-inputs examples/projects/c172-like-highlift-inputs.json`; `python -m aerosuite m09b --project p.json`; `python -m aerosuite m18c --project p.json`; `python -m aerosuite export --project p.json --module m18c --out m18c-export.json`.
- `m18c-export.json` contiene las polares 2D (alpha, CL, CD, CM) del perfil limpio y con flap, y el C_Lmax de ala por el metodo de particion.
- Limitaciones: XFOIL no modela flujo por ranura ni separacion masiva; C_lmax de XFOIL es un indicador (ver D-39). No es validacion contra ensayo.
