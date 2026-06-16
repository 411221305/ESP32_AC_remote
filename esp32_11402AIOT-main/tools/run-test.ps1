param(
    [string]$File = "test_ir_oled.py",
    [string]$Port = "COM3"
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$mpremote = Join-Path $projectRoot ".venv\Scripts\mpremote.exe"

if (Test-Path $mpremote) {
    & $mpremote connect $Port mount . + run $File
    exit $LASTEXITCODE
}

$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    $localUv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
    if (Test-Path $localUv) {
        $uv = [PSCustomObject]@{ Source = $localUv }
    }
}

if (-not $uv) {
    Write-Error "uv not found. Run tools\check_env.ps1 -Fix first."
    exit 1
}

& $uv.Source run mpremote connect $Port mount . + run $File
exit $LASTEXITCODE
