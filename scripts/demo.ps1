# AeroSuite end-to-end demo for Windows PowerShell.
# No aerodynamic solver is used: the comparison CSVs are SYNTHETIC TEST DATA.
# Run from extracted project: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\demo.ps1
$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $project

$python = $null
$pythonArgs = @()
if (Get-Command python -ErrorAction SilentlyContinue) {
    & python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) { $python = "python" }
}
if (-not $python -and (Get-Command py -ErrorAction SilentlyContinue)) {
    & py -3.11 -c "import sys" 2>$null
    if ($LASTEXITCODE -eq 0) { $python = "py"; $pythonArgs = @("-3.11") }
}
if (-not $python) {
    throw "Python 3.10+ not found. Install Python 3.11, reopen PowerShell and rerun."
}
Write-Host "AeroSuite demonstration: Python tests" -ForegroundColor Cyan
& $python @pythonArgs -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Unit tests failed" }

Write-Host "Checking matplotlib..." -ForegroundColor Cyan
& $python @pythonArgs -c "import matplotlib" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing matplotlib (requires internet on first use)..." -ForegroundColor Yellow
    & $python @pythonArgs -m pip install matplotlib
    if ($LASTEXITCODE -ne 0) { throw "Could not install matplotlib" }
}

Write-Host "Generating SYNTHETIC demonstration data..." -ForegroundColor Yellow
$generator = @'
from pathlib import Path
import csv
import json
from aerosuite.airfoils import naca4, write_csv, write_dat
from aerosuite.uiuc_library import Airfoil
from aerosuite.airfoil_compare import plot_geometry

root = Path("results/demo")
polars = root / "polars"
polars.mkdir(parents=True, exist_ok=True)
profiles = {"naca2412": "2412", "naca0012": "0012"}
geometries = []
for ident, code in profiles.items():
    write_csv(code, root / f"{ident}-geometry.csv")
    write_dat(code, root / f"{ident}.dat")
    geometries.append(Airfoil(f"NACA {code}", f"{ident}.dat", tuple(naca4(code))))
    with (polars / f"{ident}.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["alpha", "cl", "cd", "cm"])
        for alpha in range(-4, 13, 2):
            # These are intentionally invented numbers for software testing,
            # NOT a predictive aerodynamic equation or validated XFoil results.
            cl = (0.11 * (alpha + 2)) if code == "2412" else 0.10 * alpha
            cd = (0.018 if code == "2412" else 0.017) + 0.012 * cl**2
            cm = -0.05 if code == "2412" else 0.0
            writer.writerow([alpha, f"{cl:.6f}", f"{cd:.6f}", f"{cm:.6f}"])
    metadata = {
        "solver": "SYNTHETIC SOFTWARE TEST DATA — NOT ENGINEERING RESULTS",
        "reynolds": 150000, "mach": 0.0, "ncrit": 9.0,
        "xtr_top": 1.0, "xtr_bottom": 1.0,
        "converged": True,
        "note": "converged is a DEMO placeholder, not a solver convergence result",
    }
    (polars / f"{ident}.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
plot_geometry(geometries, root / "comparison" / "plots" / "geometry.png")
print("Synthetic polar samples and NACA geometry created in", root.resolve())
'@
$generator | & $python @pythonArgs -
if ($LASTEXITCODE -ne 0) { throw "Demo generator failed" }

& $python @pythonArgs -m aerosuite compare naca2412 naca0012 --polars results/demo/polars --out results/demo/comparison
if ($LASTEXITCODE -ne 0) { throw "Comparison failed" }

Write-Host ""
Write-Host "DONE: Results in $project\results\demo\comparison" -ForegroundColor Green
Write-Host "Open comparison.json and plots\geometry.png, plots\cl_alpha.png, plots\cd_alpha.png, plots\cm_alpha.png, plots\cl_cd.png, plots\efficiency_alpha.png"
Write-Host "WARNING: Polar CSV curves are generated from SYNTHETIC examples, not XFoil or flow5." -ForegroundColor Yellow
