# Componentes de terceros y licencias

| Componente | Versión | Licencia | Ubicación / obtención | Observaciones |
|---|---|---|---|---|
| flow5 (André Deperrois) | v7.57, a9e852c | GPL-3.0 (`vendor/flow5/LICENSE`) | `vendor/flow5`; binario oficial desde GitHub releases a `runtime/flow5` | Sin modificaciones. El binario Windows incluye bibliotecas de terceros (Qt, OCCT, Gmsh, BLAS/MKL) con sus propias licencias: revisar antes de redistribuir. "flow5" es nombre de su titular. |
| ADRpy (A. Sóbester et al.) | 0.2.6, b2beba2 | GPL-3.0 (`vendor/ADRpy/LICENSE.md`) | `vendor/ADRpy`, instalado en `.venv` | Sin modificaciones. |
| XFOIL (M. Drela, H. Youngren) | 6.99 | GPL-2.0 o posterior (según el paquete Debian; distribución MIT sin texto de licencia separado verificado) | Descargado por el usuario del MIT a `runtime/xfoil`; no se redistribuye | En Linux se usó el paquete Debian 6.99.dfsg+1-3 solo para pruebas. |
| UIUC Airfoil Coordinates Database | — | Condiciones del sitio UIUC | Descarga del usuario | No se redistribuye. |
| NumPy, SciPy, pandas, matplotlib | ver `requirements-core.txt` | BSD / PSF compatibles | PyPI | — |

AeroSuite invoca flow5 y XFOIL como programas independientes y usa ADRpy como biblioteca Python. Si AeroSuite se distribuye junto con ADRpy o con los binarios, aplicar las obligaciones de la GPL correspondiente (código fuente, avisos de copyright, licencia).
