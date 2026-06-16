param(
    [string]$Port = "COM3",
    [string]$Log = "ir_capture.txt"
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$mpremote = Join-Path $projectRoot ".venv\Scripts\mpremote.exe"
$logPath = Join-Path $projectRoot $Log

if (!(Test-Path $mpremote)) {
    Write-Error "mpremote not found. Run tools\check_env.ps1 -Fix first."
    exit 1
}

Write-Host "Logging IR capture to $logPath"
& $mpremote connect $Port run ir.py 2>&1 | Tee-Object -FilePath $logPath
exit $LASTEXITCODE
