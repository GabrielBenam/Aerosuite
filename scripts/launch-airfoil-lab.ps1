$ErrorActionPreference = "Stop"
$root=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
python -m pip install matplotlib Pillow
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
python -m aerosuite.desktop
if ($LASTEXITCODE -ne 0) { throw "AeroSuite desktop failed" }
