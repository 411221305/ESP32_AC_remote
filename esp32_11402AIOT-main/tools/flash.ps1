param(
    [string]$Port = "COM3",
    [Parameter(Mandatory = $true)]
    [string]$Firmware,
    [string]$Chip = "esp32",
    [string]$Address = "0x1000",
    [int]$Baud = 460800
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$esptool = Join-Path $projectRoot ".venv\Scripts\esptool.exe"

if (!(Test-Path $esptool)) {
    Write-Error "esptool not found. Run tools\check_env.ps1 -Fix first."
    exit 1
}

& $esptool --chip $Chip --port $Port erase_flash
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $esptool --chip $Chip --port $Port --baud $Baud write_flash $Address $Firmware
exit $LASTEXITCODE
