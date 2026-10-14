# AeroSuite - Windows validation of the original engines (PowerShell 5.1+).
# Runs setup-engines.ps1 (flow5 v7.57 official zip, MIT XFOIL 6.99, Python .venv with pinned ADRpy),
# then executes every AeroSuite connection and stores the evidence in evidence\windows-<timestamp>.
# Nothing in vendor\ is modified. Run by double-clicking VALIDAR-WINDOWS.cmd in the project root.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ev = Join-Path $root ("evidence\windows-" + $stamp)
New-Item -ItemType Directory -Force -Path $ev | Out-Null
Start-Transcript -Path (Join-Path $ev "transcript.txt") -Force | Out-Null
$steps = @()
function Step($name, [scriptblock]$block) {
    Write-Host ""
    Write-Host "=== $name" -ForegroundColor Cyan
    $t0 = Get-Date
    $log = Join-Path $ev ("log-" + ($name -replace '[^A-Za-z0-9_-]','_') + ".txt")
    & $block 2>&1 | Tee-Object -FilePath $log | Out-Host
    $code = $LASTEXITCODE
    $script:steps += [pscustomobject]@{step=$name; exit_code=$code; seconds=[math]::Round(((Get-Date)-$t0).TotalSeconds,1); log=$log}
    Write-Host "=== $name -> exit code $code" -ForegroundColor Yellow
}
Step "environment" { cmd /c ver; $PSVersionTable.PSVersion.ToString(); py -0p; where.exe python; cmd /c "exit 0" }
Step "setup-engines" { powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\setup-engines.ps1") }
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "SETUP DID NOT CREATE .venv - see log-setup-engines.txt" -ForegroundColor Red
} else {
    $env:PYTHONWARNINGS = "ignore"
    Step "status" { & $py -m aerosuite status }
    Step "unittest" { & $py -m unittest discover -s tests -v }
    Step "validate" { & $py -m aerosuite validate --out (Join-Path $ev "validation\validation.json") }
    Step "adrpy-size" { & $py -m aerosuite size --config examples\gudmundsson-ex3-1-c162.json --out (Join-Path $ev "adrpy\c162-sizing.json") --plot (Join-Path $ev "adrpy\c162-constraint-diagram.png") }
    Step "xfoil-compare" { & $py -m aerosuite xfoil 0012 2412 4412 4415 --reynolds 1000000 --alpha-start -4 --alpha-end 22 --alpha-step 1 --iterations 250 --from-zero --compare --allow-partial --out (Join-Path $ev "xfoil\naca-re1e6-a22") }
    Step "xfoil-crosscheck" { & $py -m aerosuite xfoil 2412 0012 --reynolds 1000000 --alpha-start 0 --alpha-end 2 --alpha-step 2 --iterations 200 --out (Join-Path $ev "xfoil\cross-check") }
    Step "opt-conceptual" { & $py -m aerosuite opt --spec examples\opt-conceptual-c162.json --out (Join-Path $ev "optimizer\conceptual-c162") }
    Step "opt-xfoil" { & $py -m aerosuite opt --spec examples\opt-xfoil-naca4.json --out (Join-Path $ev "optimizer\xfoil-naca4") }
    Step "flow5-export" { & $py -m aerosuite flow5-export --config examples\flow5-c162-like.json --out (Join-Path $ev "flow5\c162-like-job") }
    Step "flow5-run" { & $py -m aerosuite flow5-run --job (Join-Path $ev "flow5\c162-like-job") --timeout 1200 }
}
$steps | Export-Csv -NoTypeInformation -Path (Join-Path $ev "steps.csv")
$steps | Format-Table -AutoSize | Out-Host
Write-Host "Evidence folder: $ev" -ForegroundColor Green
Stop-Transcript | Out-Null
