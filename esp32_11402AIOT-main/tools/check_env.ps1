<#
.SYNOPSIS
    ESP32 EZ Start Kit+ 環境檢查工具
.DESCRIPTION
    檢查學生的開發環境是否正確設定：
    Python、uv、套件、USB 驅動、ESP32 連線、MicroPython 韌體
.PARAMETER Fix
    自動修復：安裝套件、下載韌體
.PARAMETER Port
    指定 COM port（預設自動偵測）
#>

param(
    [switch]$Fix,
    [string]$Port
)

$ErrorActionPreference = 'SilentlyContinue'
$projectRoot = Split-Path -Parent $PSScriptRoot

# --- 結果追蹤 ---
$results = @()
function Add-Result($name, $ok, $msg) {
    $script:results += [PSCustomObject]@{ Name = $name; OK = $ok; Msg = $msg }
}

# --- 自動安裝驅動程式 ---
function Install-UartDriver {
    param(
        [string]$ChipType  # 'CP210x', 'CH340', 'FTDI'
    )

    $tempDir = Join-Path $env:TEMP "esp32_driver_$ChipType"
    if (!(Test-Path $tempDir)) { New-Item -ItemType Directory -Path $tempDir | Out-Null }

    switch ($ChipType) {
        'CP210x' {
            $url = "https://www.silabs.com/documents/public/software/CP210x_Universal_Windows_Driver.zip"
            $zipPath = Join-Path $tempDir "cp210x.zip"
            Write-Host "  -> 下載 CP210x 驅動程式 ..." -ForegroundColor Cyan
            try {
                Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
            } catch {
                Write-Host "  !! 下載失敗: $_" -ForegroundColor Red
                return $false
            }

            Write-Host "  -> 解壓縮 ..." -ForegroundColor Cyan
            Expand-Archive -Path $zipPath -DestinationPath $tempDir -Force

            # Find the .inf file (64-bit)
            $infFile = Get-ChildItem -Path $tempDir -Recurse -Filter "silabser.inf" |
                Where-Object { $_.FullName -notmatch '\\x86\\' } |
                Select-Object -First 1

            if (!$infFile) {
                $infFile = Get-ChildItem -Path $tempDir -Recurse -Filter "*.inf" | Select-Object -First 1
            }

            if (!$infFile) {
                Write-Host "  !! 找不到 .inf 安裝檔" -ForegroundColor Red
                return $false
            }

            Write-Host "  -> 安裝驅動程式（需要管理員權限）..." -ForegroundColor Cyan
            Write-Host "     如果跳出 UAC 視窗，請按 [是] 同意" -ForegroundColor Yellow

            # Use pnputil to install driver (requires admin)
            $pnputilCmd = "pnputil /add-driver `"$($infFile.FullName)`" /install"
            $proc = Start-Process -FilePath "powershell" `
                -ArgumentList "-NoProfile", "-Command", $pnputilCmd `
                -Verb RunAs -Wait -PassThru -WindowStyle Hidden

            if ($proc.ExitCode -eq 0) {
                Write-Host "  OK: CP210x 驅動已安裝" -ForegroundColor Green
                Write-Host "     請拔掉 ESP32 USB 後重新插上" -ForegroundColor Yellow
                return $true
            } else {
                Write-Host "  !! 安裝失敗 (Exit: $($proc.ExitCode))" -ForegroundColor Red
                return $false
            }
        }

        'CH340' {
            # CH341SER.EXE silent installer (mirror)
            $urls = @(
                "https://github.com/nodemcu/nodemcu-devkit/raw/master/Drivers/CH341SER_WINDOWS.zip"
            )
            $zipPath = Join-Path $tempDir "ch340.zip"
            Write-Host "  -> 下載 CH340 驅動程式 ..." -ForegroundColor Cyan

            $downloaded = $false
            foreach ($url in $urls) {
                try {
                    Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing -ErrorAction Stop
                    $bytes = [System.IO.File]::ReadAllBytes($zipPath) | Select-Object -First 4
                    if ($bytes[0] -eq 0x50 -and $bytes[1] -eq 0x4B) {
                        $downloaded = $true
                        Write-Host "     來源: $url" -ForegroundColor Gray
                        break
                    }
                } catch {
                    continue
                }
            }

            if (!$downloaded) {
                Write-Host "  !! 自動下載失敗" -ForegroundColor Red
                Write-Host "     請手動下載: https://www.wch-ic.com/downloads/CH341SER_ZIP.html" -ForegroundColor White
                return $false
            }

            Write-Host "  -> 解壓縮 ..." -ForegroundColor Cyan
            try {
                Expand-Archive -Path $zipPath -DestinationPath $tempDir -Force
            } catch {
                Write-Host "  !! 解壓縮失敗: $_" -ForegroundColor Red
                return $false
            }

            # Find CH341SER.EXE (silent installer)
            $exeFile = Get-ChildItem -Path $tempDir -Recurse -Filter "CH341SER.EXE" | Select-Object -First 1

            if (!$exeFile) {
                Write-Host "  !! 找不到 CH341SER.EXE" -ForegroundColor Red
                return $false
            }

            Write-Host "  -> 安裝驅動程式（需要管理員權限）..." -ForegroundColor Cyan
            Write-Host "     如果跳出 UAC 視窗，請按 [是] 同意" -ForegroundColor Yellow

            # CH341SER.EXE supports /S for silent install (requires admin)
            try {
                $proc = Start-Process -FilePath $exeFile.FullName `
                    -ArgumentList "/S" `
                    -Verb RunAs -Wait -PassThru
                if ($proc.ExitCode -eq 0) {
                    Write-Host "  OK: CH340 驅動已安裝" -ForegroundColor Green
                    Write-Host "     請拔掉 ESP32 USB 後重新插上" -ForegroundColor Yellow
                    return $true
                } else {
                    Write-Host "  !! 安裝失敗 (Exit: $($proc.ExitCode))" -ForegroundColor Red
                    Write-Host "     可手動執行: $($exeFile.FullName)" -ForegroundColor Gray
                    return $false
                }
            } catch {
                Write-Host "  !! 安裝失敗: $_" -ForegroundColor Red
                return $false
            }
        }

        'FTDI' {
            $url = "https://ftdichip.com/wp-content/uploads/2024/03/CDM-v2.12.36.4-WHQL-Certified.zip"
            $zipPath = Join-Path $tempDir "ftdi.zip"
            Write-Host "  -> 下載 FTDI 驅動程式 ..." -ForegroundColor Cyan
            try {
                Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
            } catch {
                Write-Host "  !! 下載失敗，請手動下載: https://ftdichip.com/drivers/vcp-drivers/" -ForegroundColor Red
                return $false
            }

            Expand-Archive -Path $zipPath -DestinationPath $tempDir -Force

            $infFile = Get-ChildItem -Path $tempDir -Recurse -Filter "ftdiport.inf" | Select-Object -First 1
            if (!$infFile) {
                Write-Host "  !! 找不到 .inf 安裝檔" -ForegroundColor Red
                return $false
            }

            Write-Host "  -> 安裝驅動程式（需要管理員權限）..." -ForegroundColor Cyan
            $pnputilCmd = "pnputil /add-driver `"$($infFile.FullName)`" /install"
            $proc = Start-Process -FilePath "powershell" `
                -ArgumentList "-NoProfile", "-Command", $pnputilCmd `
                -Verb RunAs -Wait -PassThru -WindowStyle Hidden

            if ($proc.ExitCode -eq 0) {
                Write-Host "  OK: FTDI 驅動已安裝" -ForegroundColor Green
                return $true
            } else {
                return $false
            }
        }

        default {
            Write-Host "  !! 暫不支援自動安裝 $ChipType 驅動" -ForegroundColor Yellow
            return $false
        }
    }
}

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "  ESP32 EZ Start Kit+ 環境檢查" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# Stage 1: Python
# ============================================================
Write-Host "[1/6] 檢查 Python ..." -ForegroundColor Yellow

$pythonCmd = $null
$pythonVer = $null

$pythonCandidates = @()
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonCandidates += @{ Cmd = $venvPython; Label = ".venv Python" }
}
$pythonCandidates += @{ Cmd = "python"; Label = "python" }
$pythonCandidates += @{ Cmd = "python3"; Label = "python3" }

# Prefer the project virtualenv, then fall back to PATH.
foreach ($candidate in $pythonCandidates) {
    try {
        $ver = & $candidate.Cmd --version 2>&1
        if ($ver -match "Python (\d+\.\d+\.\d+)") {
            $pythonCmd = $candidate.Label
            $pythonVer = $Matches[1]
            break
        }
    } catch {}
}

if ($pythonCmd) {
    $major, $minor, $patch = $pythonVer -split '\.'
    if ([int]$major -gt 3 -or ([int]$major -eq 3 -and [int]$minor -ge 11)) {
        Write-Host "  OK: Python $pythonVer ($pythonCmd)" -ForegroundColor Green
        Add-Result "Python" $true "Python $pythonVer ($pythonCmd)"
    } else {
        Write-Host "  !! Python $pythonVer 版本太舊，需要 3.11 以上" -ForegroundColor Red
        Write-Host "     下載: https://www.python.org/downloads/" -ForegroundColor Gray
        Add-Result "Python" $false "版本太舊 ($pythonVer)"
    }
} else {
    Write-Host "  !! 找不到 Python" -ForegroundColor Red
    Write-Host "     請安裝 Python 3.11+: https://www.python.org/downloads/" -ForegroundColor Gray
    Write-Host "     安裝時請勾選 'Add Python to PATH'" -ForegroundColor Gray
    Add-Result "Python" $false "未安裝"
}

# ============================================================
# Stage 2: uv
# ============================================================
Write-Host ""
Write-Host "[2/6] 檢查 uv ..." -ForegroundColor Yellow

$uvCmd = $null
$uvVer = $null
try {
    $uvPathCmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($uvPathCmd) {
        $uvCmd = $uvPathCmd.Source
    } else {
        $localUv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
        if (Test-Path $localUv) {
            $uvCmd = $localUv
        }
    }

    if ($uvCmd) {
        $uvOut = & $uvCmd --version 2>&1
    }
    if ($uvOut -match "uv (\S+)") {
        $uvVer = $Matches[1]
    }
} catch {}

if ($uvVer) {
    Write-Host "  OK: uv $uvVer" -ForegroundColor Green
    Add-Result "uv" $true "uv $uvVer"
} else {
    Write-Host "  !! 找不到 uv" -ForegroundColor Red
    if ($Fix) {
        Write-Host "  -> 正在安裝 uv ..." -ForegroundColor Cyan
        try {
            $installScript = Invoke-RestMethod -Uri "https://astral.sh/uv/install.ps1" -UseBasicParsing
            $scriptBlock = [ScriptBlock]::Create($installScript)
            & $scriptBlock
            Write-Host "  OK: uv 已安裝，請重新開啟終端機再執行一次此腳本" -ForegroundColor Green
            Add-Result "uv" $true "剛安裝，需重啟終端"
        } catch {
            Write-Host "  !! 安裝失敗，請手動安裝" -ForegroundColor Red
            Add-Result "uv" $false "安裝失敗"
        }
    } else {
        $installCmd = 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
        Write-Host "     安裝指令:" -ForegroundColor Gray
        Write-Host "     $installCmd" -ForegroundColor White
        Write-Host "     或加上 -Fix 自動安裝" -ForegroundColor Gray
        Add-Result "uv" $false "未安裝"
    }
}

# ============================================================
# Stage 3: 套件 (mpremote, esptool)
# ============================================================
Write-Host ""
Write-Host "[3/6] 檢查套件 (mpremote, esptool) ..." -ForegroundColor Yellow

$packagesOK = $false

if ($uvVer) {
    # Check if pyproject.toml exists
    $pyprojectPath = Join-Path $projectRoot "pyproject.toml"
    if (Test-Path $pyprojectPath) {
        $venvDir = Join-Path $projectRoot ".venv\Scripts"
        $venvRoot = Join-Path $projectRoot ".venv"

        if ($Fix -or !(Test-Path $venvRoot)) {
        Write-Host "  -> 執行 uv sync ..." -ForegroundColor Cyan
        Push-Location $projectRoot
            & $uvCmd sync 2>&1 | Out-Null
        Pop-Location
        }

        # Verify tools exist
        $hasMpremote = Test-Path (Join-Path $venvDir "mpremote.exe")
        $hasEsptool = Test-Path (Join-Path $venvDir "esptool.exe")

        if ($hasMpremote -and $hasEsptool) {
            Write-Host "  OK: mpremote, esptool 已安裝" -ForegroundColor Green
            $packagesOK = $true
            Add-Result "套件" $true "mpremote, esptool"
        } else {
            Write-Host "  !! 套件不完整，執行 uv sync 修復" -ForegroundColor Red
            Push-Location $projectRoot
            & $uvCmd sync 2>&1
            Pop-Location
            # Re-check
            $hasMpremote = Test-Path (Join-Path $venvDir "mpremote.exe")
            $hasEsptool = Test-Path (Join-Path $venvDir "esptool.exe")
            if ($hasMpremote -and $hasEsptool) {
                Write-Host "  OK: 修復成功" -ForegroundColor Green
                $packagesOK = $true
                Add-Result "套件" $true "已修復"
            } else {
                Add-Result "套件" $false "安裝失敗"
            }
        }
    } else {
        Write-Host "  !! 找不到 pyproject.toml" -ForegroundColor Red
        Add-Result "套件" $false "缺少 pyproject.toml"
    }
} else {
    Write-Host "  -- 跳過（需要先安裝 uv）" -ForegroundColor Gray
    Add-Result "套件" $false "需要先安裝 uv"
}

# ============================================================
# Stage 4: USB 驅動程式
# ============================================================
Write-Host ""
Write-Host "[4/6] 檢查 USB 驅動程式 ..." -ForegroundColor Yellow

$usbDevices = Get-CimInstance Win32_PnPEntity 2>$null |
    Where-Object { $_.Name -match 'CH340|CH341|CP210|CP2102|FTDI|USB-SERIAL|USB Serial|Silicon Labs' }

if ($usbDevices) {
    $okDevices = @($usbDevices | Where-Object { $_.Status -eq 'OK' })
    $errDevices = @($usbDevices | Where-Object { $_.Status -ne 'OK' })

    if ($okDevices.Count -gt 0) {
        foreach ($dev in $okDevices) {
            Write-Host "  OK: $($dev.Name)" -ForegroundColor Green
        }
        Add-Result "USB 驅動" $true $okDevices[0].Name
    } else {
        # Device detected but driver has issues
        foreach ($dev in $errDevices) {
            Write-Host "  !! $($dev.Name) [狀態: $($dev.Status)]" -ForegroundColor Red
        }
        Write-Host "     ESP32 已連接，但驅動程式有問題" -ForegroundColor Yellow

        # Detect chip type
        $isCh340 = @($errDevices | Where-Object { $_.Name -match 'CH34' }).Count -gt 0
        $isCp210 = @($errDevices | Where-Object { $_.Name -match 'CP210|CP2102|Silicon Labs' }).Count -gt 0
        $isFtdi  = @($errDevices | Where-Object { $_.Name -match 'FTDI' }).Count -gt 0

        $installed = $false
        if ($Fix) {
            Write-Host ""
            if ($isCp210) {
                $installed = Install-UartDriver -ChipType 'CP210x'
            } elseif ($isCh340) {
                $installed = Install-UartDriver -ChipType 'CH340'
            } elseif ($isFtdi) {
                $installed = Install-UartDriver -ChipType 'FTDI'
            }
        } else {
            Write-Host "     可能原因：" -ForegroundColor Gray
            Write-Host "     1. 驅動程式未正確安裝" -ForegroundColor Gray
            Write-Host "     2. 開啟 [裝置管理員] 查看是否有黃色驚嘆號" -ForegroundColor Gray
            Write-Host ""
            if ($isCh340) {
                Write-Host "     CH340 驅動下載: https://www.wch-ic.com/downloads/CH341SER_ZIP.html" -ForegroundColor White
            }
            if ($isCp210) {
                Write-Host "     CP210x 驅動下載: https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers" -ForegroundColor White
            }
            if ($isFtdi) {
                Write-Host "     FTDI 驅動下載: https://ftdichip.com/drivers/vcp-drivers/" -ForegroundColor White
            }
            Write-Host ""
            Write-Host "     提示: 加上 -Fix 可自動下載並安裝驅動" -ForegroundColor Yellow
        }

        if ($installed) {
            Add-Result "USB 驅動" $true "已自動安裝 (需重插 USB)"
        } else {
            Add-Result "USB 驅動" $false "驅動異常 ($($errDevices[0].Status))"
        }
    }
} else {
    Write-Host "  !! 找不到 USB-UART 裝置" -ForegroundColor Red
    Write-Host "     請確認：" -ForegroundColor Gray
    Write-Host "     1. ESP32 已用 USB 線連接電腦" -ForegroundColor Gray
    Write-Host "     2. USB 線是資料線（不是只能充電的線）" -ForegroundColor Gray
    Write-Host "     3. 已安裝對應晶片的驅動程式（CH340/CP210x/FTDI）" -ForegroundColor Gray
    Write-Host "     CH340 驅動: https://www.wch-ic.com/downloads/CH341SER_ZIP.html" -ForegroundColor White
    Write-Host "     CP210x 驅動: https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers" -ForegroundColor White
    Add-Result "USB 驅動" $false "未偵測到"
}

# ============================================================
# Stage 5: ESP32 COM Port
# ============================================================
Write-Host ""
Write-Host "[5/6] 偵測 ESP32 COM Port ..." -ForegroundColor Yellow

$detectedPort = $null
$availablePorts = @()  # All openable ports in priority order

if ($Port) {
    $detectedPort = $Port
    $availablePorts = @($Port)
    Write-Host "  OK: 使用指定的 $Port" -ForegroundColor Green
} else {
    $comDevices = Get-CimInstance Win32_PnPEntity 2>$null |
        Where-Object { $_.Name -match '(COM\d+)' -and $_.Name -match 'CH340|CH341|CP210|FTDI|USB-SERIAL|USB Serial|Silicon Labs' }

    if ($comDevices) {
        # Build list of all detected ports (filter to OK status)
        $detectedPortObjs = @()
        foreach ($dev in $comDevices) {
            if ($dev.Name -match '(COM\d+)' -and $dev.Status -eq 'OK') {
                $detectedPortObjs += [PSCustomObject]@{
                    Port = $Matches[1]
                    Name = $dev.Name
                    PortNum = [int]($Matches[1] -replace 'COM','')
                }
            }
        }

        if ($detectedPortObjs.Count -gt 0) {
            # Sort by port number (lowest first)
            $detectedPortObjs = $detectedPortObjs | Sort-Object PortNum

            if ($detectedPortObjs.Count -gt 1) {
                Write-Host "  -- 偵測到多個 ESP32:" -ForegroundColor Yellow
                foreach ($p in $detectedPortObjs) {
                    Write-Host "     $($p.Port) - $($p.Name)" -ForegroundColor Gray
                }
            }

            # Test each port by opening it - keep all that can be opened
            foreach ($p in $detectedPortObjs) {
                try {
                    $sp = New-Object System.IO.Ports.SerialPort $p.Port, 115200, 'None', 8, 'One'
                    $sp.ReadTimeout = 500
                    $sp.Open()
                    $sp.Close()
                    $availablePorts += $p.Port
                } catch {
                    Write-Host "     $($p.Port) 無法開啟（裝置忙碌或不存在）" -ForegroundColor Gray
                }
            }

            if ($availablePorts.Count -gt 0) {
                $detectedPort = $availablePorts[0]
                $portName = ($detectedPortObjs | Where-Object { $_.Port -eq $detectedPort }).Name
                Write-Host "  OK: 偵測到 ESP32 在 $detectedPort ($portName)" -ForegroundColor Green
                if ($availablePorts.Count -gt 1) {
                    Write-Host "       備援 port: $($availablePorts[1..($availablePorts.Count-1)] -join ', ')" -ForegroundColor Gray
                }
            }
        }
    }
}

if ($detectedPort) {
    Add-Result "COM Port" $true $detectedPort
} else {
    Write-Host "  !! 找不到 ESP32" -ForegroundColor Red
    Write-Host "     請確認 ESP32 已透過 USB 連接電腦" -ForegroundColor Gray
    Add-Result "COM Port" $false "未偵測到"
}

# ============================================================
# Stage 6: MicroPython 韌體
# ============================================================
Write-Host ""
Write-Host "[6/6] 檢查 MicroPython 韌體 ..." -ForegroundColor Yellow

$firmwareOK = $false
$firmwareFile = "ESP32_GENERIC-v1.27.0.bin"
$firmwareUrl = "https://micropython.org/resources/firmware/ESP32_GENERIC-20251209-v1.27.0.bin"
$firmwarePath = Join-Path $projectRoot $firmwareFile

if ($detectedPort -and $packagesOK) {
    $mpremotePath = Join-Path $projectRoot ".venv\Scripts\mpremote.exe"
    $esptoolPath = Join-Path $projectRoot ".venv\Scripts\esptool.exe"

    # Helper: check if a port has working MicroPython
    function Test-MicroPython($port) {
        try {
            $mpOut = & $mpremotePath connect $port exec "import sys; print(sys.version)" 2>&1
            $mpOutStr = $mpOut -join "`n"
            if ($mpOutStr -match "\d+\.\d+") {
                return $mpOutStr.Trim()
            }
        } catch {}
        return $null
    }

    # Helper: flash firmware to a specific port
    function Invoke-FlashPort($port, $attempt) {
        Write-Host ""
        if ($attempt -gt 1) {
            Write-Host "  -> 第 $attempt 次嘗試燒錄 $port ..." -ForegroundColor Cyan
        } else {
            Write-Host "  -> 自動燒錄韌體到 $port ..." -ForegroundColor Cyan
        }
        Write-Host "     (大約需要 30-60 秒，請勿拔除 USB)" -ForegroundColor Yellow

        Write-Host "     [1/2] 清除 flash ..." -ForegroundColor Gray
        $eraseProc = Start-Process -FilePath $esptoolPath `
            -ArgumentList "--port", $port, "--connect-attempts", "5", "erase-flash" `
            -Wait -PassThru -NoNewWindow

        if ($eraseProc.ExitCode -ne 0) {
            return @{ Success = $false; Stage = "erase"; ExitCode = $eraseProc.ExitCode }
        }

        Write-Host "     [2/2] 寫入韌體 ..." -ForegroundColor Gray
        $writeProc = Start-Process -FilePath $esptoolPath `
            -ArgumentList "--port", $port, "--baud", "460800", `
                          "--connect-attempts", "5", `
                          "write-flash", "-z", "0x1000", $firmwarePath `
            -Wait -PassThru -NoNewWindow

        if ($writeProc.ExitCode -eq 0) {
            return @{ Success = $true }
        } else {
            return @{ Success = $false; Stage = "write"; ExitCode = $writeProc.ExitCode }
        }
    }

    # Step 1: Check if any port already has MicroPython
    $foundPort = $null
    $foundVersion = $null
    foreach ($p in $availablePorts) {
        $ver = Test-MicroPython $p
        if ($ver) {
            $foundPort = $p
            $foundVersion = $ver
            break
        }
    }

    if ($foundPort) {
        Write-Host "  OK: MicroPython 已燒錄 ($foundPort)" -ForegroundColor Green
        Write-Host "       版本: $foundVersion" -ForegroundColor Gray
        $firmwareOK = $true
        Add-Result "MicroPython" $true "已燒錄 ($foundPort)"
    } else {
        Write-Host "  !! ESP32 上沒有 MicroPython 韌體" -ForegroundColor Red

        # Step 2: Make sure firmware file is available
        $firmwareReady = $false
        if (Test-Path $firmwarePath) {
            Write-Host "  -- 韌體檔案已存在: $firmwareFile" -ForegroundColor Gray
            $firmwareReady = $true
        } elseif ($Fix) {
            Write-Host "  -> 正在下載韌體 ..." -ForegroundColor Cyan
            try {
                Invoke-WebRequest -Uri $firmwareUrl -OutFile $firmwarePath -UseBasicParsing
                Write-Host "  OK: 韌體已下載" -ForegroundColor Green
                $firmwareReady = $true
            } catch {
                Write-Host "  !! 下載失敗，請手動下載:" -ForegroundColor Red
                Write-Host "     $firmwareUrl" -ForegroundColor White
            }
        } else {
            Write-Host "     韌體下載: $firmwareUrl" -ForegroundColor White
            Write-Host "     或加上 -Fix 自動下載並燒錄" -ForegroundColor Gray
        }

        # Step 3: Auto-flash with port fallback
        if ($Fix -and $firmwareReady) {
            $flashSuccess = $false
            $flashedPort = $null
            $lastError = $null

            foreach ($port in $availablePorts) {
                Write-Host ""
                Write-Host "  ====== 嘗試在 $port 燒錄 ======" -ForegroundColor Cyan

                # First attempt
                $result = Invoke-FlashPort $port 1

                # If failed, countdown for BOOT mode and retry
                if (!$result.Success) {
                    Write-Host ""
                    Write-Host "  !! 自動進入下載模式失敗" -ForegroundColor Red
                    Write-Host "     請手動進入下載模式：" -ForegroundColor Yellow
                    Write-Host "     1. 按住 [BOOT] 按鈕不放" -ForegroundColor Gray
                    Write-Host "     2. 短按 [EN] 或 [RST] 按鈕" -ForegroundColor Gray
                    Write-Host "     3. 繼續按住 [BOOT] 直到下方倒數結束" -ForegroundColor Gray
                    Write-Host ""
                    for ($i = 10; $i -gt 0; $i--) {
                        Write-Host "`r     $i 秒後重試 ..." -NoNewline -ForegroundColor Cyan
                        Start-Sleep -Seconds 1
                    }
                    Write-Host "`r     重試中 ...                " -ForegroundColor Cyan
                    $result = Invoke-FlashPort $port 2
                }

                if ($result.Success) {
                    $flashSuccess = $true
                    $flashedPort = $port
                    $detectedPort = $port
                    break
                } else {
                    $lastError = $result
                    if ($availablePorts.Count -gt 1 -and $port -ne $availablePorts[-1]) {
                        Write-Host ""
                        Write-Host "  !! $port 燒錄失敗，嘗試下一個 port ..." -ForegroundColor Yellow
                    }
                }
            }

            if ($flashSuccess) {
                Write-Host ""
                Write-Host "  OK: MicroPython 韌體已燒錄完成 ($flashedPort)" -ForegroundColor Green

                # Wait for ESP32 to reboot
                Write-Host "     等待 ESP32 重啟 ..." -ForegroundColor Gray
                Start-Sleep -Seconds 3

                # Verify
                $ver = Test-MicroPython $flashedPort
                if ($ver) {
                    Write-Host "       版本: $ver" -ForegroundColor Gray
                }

                Add-Result "MicroPython" $true "已自動燒錄 ($flashedPort)"
            } else {
                Write-Host ""
                Write-Host "  !! 所有 port 皆燒錄失敗" -ForegroundColor Red
                Write-Host "     可能原因：" -ForegroundColor Gray
                Write-Host "     1. ESP32 開發板的 flash 晶片有問題" -ForegroundColor Gray
                Write-Host "     2. USB 線品質不佳，請換條好的資料線" -ForegroundColor Gray
                Write-Host "     3. 開發板沒有自動進入下載模式（按住 BOOT 後燒錄）" -ForegroundColor Gray
                Write-Host ""
                Write-Host "     手動燒錄指令:" -ForegroundColor Yellow
                Write-Host "       uv run esptool --port $detectedPort erase-flash" -ForegroundColor White
                Write-Host "       uv run esptool --port $detectedPort --baud 460800 write-flash -z 0x1000 $firmwareFile" -ForegroundColor White
                Add-Result "MicroPython" $false "燒錄失敗"
            }
        } else {
            Write-Host ""
            Write-Host "  燒錄指令（在專案目錄執行）:" -ForegroundColor Yellow
            Write-Host "     uv run esptool --port $detectedPort erase-flash" -ForegroundColor White
            Write-Host "     uv run esptool --port $detectedPort --baud 460800 write-flash -z 0x1000 $firmwareFile" -ForegroundColor White
            Add-Result "MicroPython" $false "未燒錄"
        }
    }
} elseif (!$detectedPort) {
    Write-Host "  -- 跳過（未偵測到 ESP32）" -ForegroundColor Gray
    Add-Result "MicroPython" $false "需要先連接 ESP32"
} else {
    Write-Host "  -- 跳過（套件未安裝）" -ForegroundColor Gray
    Add-Result "MicroPython" $false "需要先安裝套件"
}

# ============================================================
# Summary
# ============================================================
Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "  檢查結果" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

$passCount = 0
$failCount = 0

foreach ($r in $results) {
    if ($r.OK) {
        Write-Host "  [OK] $($r.Name): $($r.Msg)" -ForegroundColor Green
        $passCount++
    } else {
        Write-Host "  [!!] $($r.Name): $($r.Msg)" -ForegroundColor Red
        $failCount++
    }
}

Write-Host ""
if ($failCount -eq 0) {
    Write-Host "  全部通過! 可以開始開發了!" -ForegroundColor Green
    Write-Host "  下一步: 在 VS Code 按 Ctrl+Shift+B 上傳程式到 ESP32" -ForegroundColor Cyan
} else {
    Write-Host "  有 $failCount 個項目需要修正，請參考上方說明" -ForegroundColor Red
    if (!$Fix) {
        Write-Host "  提示: 加上 -Fix 可自動修復部分項目" -ForegroundColor Yellow
        Write-Host "  powershell -ExecutionPolicy Bypass -File tools\check_env.ps1 -Fix" -ForegroundColor White
    }
}
Write-Host ""
