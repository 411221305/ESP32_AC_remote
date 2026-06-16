param(
    [string]$Port = "COM3",
    [switch]$ResetCodes
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$mpremote = Join-Path $projectRoot ".venv\Scripts\mpremote.exe"

if (!(Test-Path $mpremote)) {
    Write-Error "mpremote not found. Run tools\check_env.ps1 -Fix first."
    exit 1
}

& $mpremote connect $Port cp boot.py :
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $mpremote connect $Port cp main.py :
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($ResetCodes -and (Test-Path (Join-Path $projectRoot "ac_codes.py"))) {
    & $mpremote connect $Port cp ac_codes.py :
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $mpremote connect $Port cp -r ./lib :
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $mpremote connect $Port reset
exit $LASTEXITCODE
