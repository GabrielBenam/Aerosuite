# AeroSuite engine bootstrap (Windows PowerShell 5.1+)
# Installs exact vendor ADRpy and optional official flow5/XFOIL binaries.
# Does NOT modify upstream source files or your other Python installations.
param(
    [switch]$SkipFlow5,
    [switch]$SkipXFoil,
    [switch]$SkipPython,
    [switch]$OpenFlow5
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$runtime = Join-Path $root "runtime"
New-Item -ItemType Directory -Force -Path $runtime | Out-Null

if (-not $SkipFlow5) {
    $flowFolder = Join-Path $runtime "flow5"
    $existing = @(Get-ChildItem -Path $flowFolder -Recurse -File -Filter flow5.exe -ErrorAction SilentlyContinue)
    if ($existing.Count -eq 0) {
        Write-Host "Downloading official flow5 v7.57 Windows distribution (approx. 174 MB)..." -ForegroundColor Cyan
        $url = "https://github.com/techwinder/flow5/releases/download/v7.57/flow5_v7.57_win64.zip"
        $archive = Join-Path $runtime "flow5_v7.57_win64.zip"
        Invoke-WebRequest -Uri $url -OutFile $archive -UseBasicParsing
        Expand-Archive -LiteralPath $archive -DestinationPath $flowFolder -Force
    }
    $flowExe = Get-ChildItem -Path $flowFolder -Recurse -File -Filter "flow5.exe" | Select-Object -First 1
    if (-not $flowExe) { throw "Cannot find flow5.exe in official Windows ZIP. Inspect archive." }
    $location = Join-Path $runtime "flow5-location.txt"
    [System.IO.File]::WriteAllText($location,$flowExe.FullName,[System.Text.Encoding]::UTF8)
    Write-Host "flow5 original v7.57: $($flowExe.FullName)" -ForegroundColor Green
}

if (-not $SkipXFoil) {
    $xfoilFolder = Join-Path $runtime "xfoil"
    New-Item -ItemType Directory -Force -Path $xfoilFolder | Out-Null
    $exe = Join-Path $xfoilFolder "xfoil.exe"
    if (-not (Test-Path $exe)) {
        Write-Host "Downloading MIT XFOIL 6.99..." -ForegroundColor Cyan
        $archive = Join-Path $runtime "XFOIL6.99.zip"
        Invoke-WebRequest -Uri "https://web.mit.edu/drela/Public/web/xfoil/XFOIL6.99.zip" -OutFile $archive -UseBasicParsing
        $temp = Join-Path $runtime "xfoil-expanded"
        Expand-Archive -LiteralPath $archive -DestinationPath $temp -Force
        $found = Get-ChildItem -Path $temp -Recurse -File -Filter xfoil.exe | Select-Object -First 1
        if (-not $found) { throw "MIT XFOIL ZIP does not contain xfoil.exe." }
        Copy-Item -LiteralPath $found.FullName -Destination $exe
    }
    Write-Host "XFOIL external CLI: $exe" -ForegroundColor Green
}

if (-not $SkipPython) {
    $python = $null
    $pyArgs = @()
    # On Windows PowerShell 5.1, native stderr can be promoted to a terminating
    # error under Stop even if the caller intends to check only LASTEXITCODE.
    $priorPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3.11 -c "import sys; print(sys.version)" 2>$null
            if ($LASTEXITCODE -eq 0) { $python = "py"; $pyArgs = @("-3.11") }
        }
        if (-not $python -and (Get-Command python -ErrorAction SilentlyContinue)) {
            & python -c "import sys; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { $python = "python" }
        }
    } finally {
        $ErrorActionPreference = $priorPreference
    }
    if (-not $python) { throw "Install Python 3.11 from python.org (3.15 is not ADRpy validated) and rerun." }
    Write-Host "Creating isolated .venv for ADRpy, SciPy and NumPy..." -ForegroundColor Cyan
    & $python @pyArgs -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create virtual environment" }
    $venvPython = Join-Path $root ".venv\Scripts\python.exe"
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
    & $venvPython -m pip install -r requirements-core.txt pandas cycler
    if ($LASTEXITCODE -ne 0) { throw "Scientific Python dependencies failed to install" }
    $vendoredADRpy = Join-Path $root "vendor\ADRpy\setup.py"
    if (-not (Test-Path $vendoredADRpy)) { throw "Complete ADRpy submodule missing; use recursive git clone or full GitHub Actions bundle." }
    & $venvPython -m pip install --no-deps (Join-Path $root "vendor\ADRpy")
    if ($LASTEXITCODE -ne 0) { throw "Pinned ADRpy local installation failed" }
    & $venvPython -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "AeroSuite Python unit tests failed" }
    & $venvPython -m aerosuite size --config examples\aircraft-concept.json --out results\conceptual-sizing.json
    if ($LASTEXITCODE -ne 0) { throw "ADRpy sizing validation failed" }
    Write-Host "Core ready. Use .venv\Scripts\python.exe -m aerosuite --help" -ForegroundColor Green
}
if ($OpenFlow5) {
    $exePath = Join-Path $runtime "flow5-location.txt"
    if (-not (Test-Path $exePath)) { throw "Official flow5 executable was not installed" }
    $actualExe = Get-Content -LiteralPath $exePath -Encoding UTF8 -Raw
    Start-Process -FilePath $actualExe.Trim() -WorkingDirectory (Split-Path -Parent $actualExe.Trim())
}
Write-Host "Finished. Upstream repositories stay unchanged." -ForegroundColor Green
