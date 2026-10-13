# AeroSuite

Suite modular de diseño y análisis aeronáutico en fase inicial.

## Implementado (prototipo Python)
- Generador geométrico de perfiles NACA de cuatro dígitos.
- Exportación de coordenadas normalizadas a CSV y DAT.
- Preselección de perfiles únicamente por criterios geométricos.
- Cinco pruebas unitarias y workflow de GitHub Actions.

**No se ha integrado ni compilado flow5. No hay cálculos aerodinámicos reales en esta versión.**

## Primeros comandos

Requiere Python 3.10+.

```powershell
python -m unittest discover -s tests -v
python -m aerosuite generate 2412 --out results
python -m aerosuite shortlist 0012 2412 4415 0020 --min-thickness 0.10 --max-thickness 0.18 --max-camber 0.04
```

## Motor upstream
- [flow5 v7.57](https://github.com/techwinder/flow5/tree/v7.57)
- [Ejemplo XFoilBatchRun](https://github.com/techwinder/flow5/tree/v7.57/API_examples/XFoilBatchRun)

Consultar [roadmap](docs/ROADMAP.md), [integración con flow5](docs/FLOW5-INTEGRATION.md) y [transferencia a Claude](docs/CLAUDE-HANDOFF.md).

## Licencias
Este repositorio no incorpora código fuente de flow5. Al vincular sus bibliotecas o redistribuir derivados, evaluar las obligaciones de la GPLv3 y las licencias de otros componentes antes de publicar.
