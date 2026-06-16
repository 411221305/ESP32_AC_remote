# ESP32 MicroPython + VS Code + uv + mpremote 開發計畫

## 0. 整體架構

```text
電腦端
├── VS Code              # 寫程式
├── uv                   # 管理 Python 專案環境
├── mpremote             # 連線 ESP32、REPL、上傳、執行
├── esptool              # 燒錄 MicroPython 韌體
└── Git                  # 版本控管

ESP32 端
├── MicroPython 韌體
├── boot.py
├── main.py
└── lib/
```

簡單講：

```text
Python / uv / mpremote / esptool 裝在電腦
MicroPython 韌體燒進 ESP32
.py 程式用 VS Code 寫
測試時用 mpremote run
定案時才 cp 到 ESP32
```

---

## 0.1 開發板規格：Circus EZ Start Kit+（NodeMCU-32S）

本計畫使用的開發板為 **Circus EZ Start Kit+**，主控板為 **NodeMCU-32S（CP2102）**，搭配 EZ Start Kit+ 三合一擴展板。

### 板載元件一覽

| 元件 | 說明 |
|---|---|
| NodeMCU-32S | ESP32-WROOM-32 模組，CP2102 USB 轉串口晶片 |
| 單色 LED × 3 | 紅、黃、綠 |
| RGB LED × 3 | WS2812 型，單訊號線控制 |
| DHT11 | 溫濕度感測器（0–50°C，20–90%RH） |
| 光感測器 | 光敏電阻，ADC 讀值範圍 0–4095 |
| 無源蜂鳴器 | PWM 控制頻率，可播放旋律 |
| 紅外線接收器 | 搭配附件遙控器使用 |
| 1.3 吋 OLED | 128×64，I2C 介面，SH1106 驅動 |
| 繼電器 | 可控制 110V 以下大電流負載 |
| 可變電阻 | ADC 讀值範圍 0–4095 |
| 按鍵 A / B | 按下為 LOW，放開為 HIGH |

### GPIO 腳位對照表（NodeMCU-32S + EZ Start Kit+）

| 元件 | GPIO | 說明 |
|---|---|---|
| NodeMCU-32S 內建藍色 LED | GPIO 2 | 高電位亮燈 |
| 按鍵 A | GPIO 5 | 按下為 LOW，需擴展板供電 |
| 按鍵 B | GPIO 36 | 按下為 LOW，需擴展板供電，Input Only |
| 紅色 LED | GPIO 16 | 高電位亮燈，需擴展板供電 |
| 黃色 LED | GPIO 12 | 高電位亮燈，需擴展板供電 |
| 綠色 LED | GPIO 13 | 高電位亮燈，需擴展板供電 |
| RGB LED（WS2812） | GPIO 26 | 單訊號線，NeoPixel 協定 |
| DHT11 溫濕度 | GPIO 15 | 單線數位協定 |
| 光感測器 | GPIO 39 | ADC1，Input Only，可與 Wi-Fi 同時使用 |
| 可變電阻 | GPIO 34 | ADC1，Input Only，可與 Wi-Fi 同時使用 |
| 無源蜂鳴器 | GPIO 14 | PWM 輸出 |
| 繼電器 | GPIO 25 | 高電位啟動（線圈通電） |
| OLED SDA | GPIO 21 | I2C 預設 SDA |
| OLED SCL | GPIO 22 | I2C 預設 SCL |
| 紅外線接收器 | GPIO 35 ⚠️ | 請對照擴展板背面腳位圖確認 |

> ⚠️ **紅外線接收器**的 GPIO 編號各版本擴展板可能不同，請以擴展板背面印刷的腳位對照表為準。上表的 GPIO 35 為參考值，實際使用前務必確認。

### 腳位使用注意事項

```text
GPIO 36、39 為 Input Only，不能輸出，但可與 Wi-Fi 同時做 ADC 讀取
GPIO 34、35 為 Input Only，ADC1，可與 Wi-Fi 同時使用
GPIO 12 為 Strapping Pin，燒錄時不可接任何裝置，燒錄完成後再接回
GPIO 6–11 已連接內部 SPI Flash，請勿使用
按鍵、LED、繼電器、蜂鳴器等元件需透過擴展板 Micro USB 供電才能正常使用
ADC2（GPIO 25、26、27 等）啟用 Wi-Fi 後無法讀取類比值，改用 ADC1
```

### 板子型號與燒錄設定

| 項目 | 設定 |
|---|---|
| 晶片型號 | ESP32（原版） |
| 燒錄 `--chip` | `esp32` |
| 燒錄起始地址 | `0x1000` |
| USB 驅動晶片 | CP2102（Silicon Labs） |
| MicroPython 韌體 | `ESP32_GENERIC` |

---

## 1. 安裝 uv

### Windows PowerShell

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

安裝後關掉 PowerShell，再重新開一個 PowerShell，檢查：

```powershell
uv --version
```

如果看到版本號，代表成功。

### macOS / Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

檢查：

```bash
uv --version
```

---

## 2. 建立 ESP32 MicroPython 專案

建議用 `uv init` 建立專案。

```powershell
uv init esp32-micropython-project
cd esp32-micropython-project
```

這會產生類似：

```text
esp32-micropython-project/
├── .git/
├── .gitignore
├── .python-version
├── README.md
├── main.py
└── pyproject.toml
```

接著加入 ESP32 開發需要的工具：

```powershell
uv add mpremote esptool
```

這兩個工具的用途：

| 工具 | 安裝位置 | 用途 |
|---|---|---|
| `mpremote` | 電腦端 uv 環境 | 連線 ESP32、進入 REPL、上傳檔案、執行測試 |
| `esptool` | 電腦端 uv 環境 | 燒錄或清除 ESP32 韌體 |
| MicroPython 韌體 | ESP32 Flash | 讓 ESP32 可以執行 MicroPython 程式 |

---

## 3. 建議專案資料夾結構

建議整理成：

```text
esp32-micropython-project/
├── .gitignore
├── .python-version
├── pyproject.toml
├── uv.lock
├── README.md
├── boot.py
├── main.py
├── config.example.py
├── config.py
├── test_led.py
├── test_wifi.py
├── test_sensor.py
├── lib/
│   ├── motor.py
│   └── dht.py
└── tools/
    ├── flash.ps1
    └── deploy.ps1
```

各檔案用途：

| 檔案 | 用途 |
|---|---|
| `pyproject.toml` | uv 專案設定與依賴 |
| `uv.lock` | 鎖定依賴版本，讓大家環境一致 |
| `.python-version` | 指定專案使用的 Python 版本 |
| `boot.py` | ESP32 開機後先執行，適合放 Wi-Fi 初始化 |
| `main.py` | ESP32 主程式入口 |
| `config.py` | 真實 Wi-Fi、MQTT、API 設定，不上傳 Git |
| `config.example.py` | 設定範例，可上傳 Git |
| `test_led.py` | LED 測試 |
| `test_wifi.py` | Wi-Fi 測試 |
| `test_sensor.py` | 感測器測試 |
| `lib/` | 自訂模組與感測器驅動 |
| `tools/` | 自動化腳本 |

---

## 4. `.gitignore` 建議

```gitignore
# uv / Python
.venv/
__pycache__/
*.pyc

# Secrets
config.py
secrets.py
wifi_config.py

# Firmware
*.bin

# OS / Editor
.DS_Store
Thumbs.db
.vscode/
```

注意：  
`.venv/` 不上傳，因為 uv 可以依照 `pyproject.toml` 和 `uv.lock` 重建環境。

---

## 5. 確認 uv 環境

不需要手動啟用 `.venv`，可以直接用：

```powershell
uv run python --version
```

檢查 `mpremote`：

```powershell
uv run mpremote --help
```

檢查 `esptool`：

```powershell
uv run esptool --version
```

如果 `esptool` 指令不可用，試：

```powershell
uv run esptool.py --version
```

---

## 6. 安裝 ESP32 USB 驅動

### Windows

ESP32 接到電腦後，Windows 裝置管理員應該要看到 COM Port，例如：

```text
USB-SERIAL CH340 (COM3)
Silicon Labs CP210x USB to UART Bridge (COM4)
```

常見晶片：

| 晶片 | 驅動 |
|---|---|
| CP2102 / CP210x | Silicon Labs CP210x VCP Driver |
| CH340 / CH341 | WCH CH341SER Driver |

如果看不到 COM Port，優先檢查：

```text
1. USB 線是不是只能充電
2. 驅動是否安裝
3. ESP32 是否有正常供電
4. 是否換一個 USB 孔
```

### macOS

Port 名稱通常長這樣：

```text
/dev/tty.usbserial-*
/dev/tty.SLAB_USBtoUART
```

確認方法：

```bash
ls /dev/tty.usb*
```

### Linux

Port 名稱通常長這樣：

```text
/dev/ttyUSB0
/dev/ttyACM0
```

確認方法：

```bash
ls /dev/ttyUSB*
```

Linux 若出現 Permission denied，加入 dialout 群組：

```bash
sudo usermod -aG dialout $USER
# 登出後重新登入才生效
```

後續範例指令以 Windows `COM3` 示範；macOS / Linux 請把 `COM3` 換成對應的 Port，例如 `/dev/tty.usbserial-0001`。

---

## 7. 燒錄 MicroPython 韌體

這一步只在以下情況需要做：

```text
首次安裝 MicroPython
升級 MicroPython 韌體
換 ESP32 型號
Flash 損壞或要重置
```

平常開發不需要一直燒錄韌體。

### 7.1 下載 MicroPython 韌體

到 MicroPython 官方 ESP32 下載頁選擇合適版本：

```text
ESP32_GENERIC
ESP32_GENERIC_SPIRAM
ESP32_GENERIC_S3
ESP32_GENERIC_C3
```

一般 ESP32 DevKit 通常選：

```text
ESP32_GENERIC
```

下載後會得到 `.bin` 檔，例如：

```text
ESP32_GENERIC-20250415-v1.25.0.bin
```

### 7.2 擦除 Flash

**注意：`--chip` 請依照實際板子型號填寫**，常見對應：

| 板子型號 | `--chip` 參數 |
|---|---|
| ESP32（原版 DevKit） | `esp32` |
| ESP32-S2 | `esp32s2` |
| ESP32-S3 | `esp32s3` |
| ESP32-C3 | `esp32c3` |

假設 ESP32 原版，Port 為 `COM3`：

```powershell
uv run esptool --chip esp32 --port COM3 erase_flash
```

### 7.3 燒錄韌體

**注意：燒錄起始地址依晶片型號不同，請勿混用：**

| 晶片 | 起始地址 |
|---|---|
| ESP32（原版） | `0x1000` |
| ESP32-S2 / S3 / C3 | `0x0` |

ESP32 原版：

```powershell
uv run esptool --chip esp32 --port COM3 --baud 460800 write_flash 0x1000 ESP32_GENERIC-20250415-v1.25.0.bin
```

ESP32-S3 / C3（起始地址改為 `0x0`）：

```powershell
uv run esptool --chip esp32s3 --port COM3 --baud 460800 write_flash 0x0 ESP32_GENERIC_S3-20250415-v1.25.0.bin
```

如果燒錄失敗，先不加 `--baud` 讓 esptool 自動選速：

```powershell
uv run esptool --chip esp32 --port COM3 write_flash 0x1000 ESP32_GENERIC-20250415-v1.25.0.bin
```

有些 ESP32 板子燒錄時要按住 `BOOT` 鍵，開始寫入後再放開。

---

## 8. 確認 ESP32 連線

列出可用裝置：

```powershell
uv run mpremote connect list
```

進入 REPL：

```powershell
uv run mpremote connect COM3 repl
```

如果看到：

```text
MicroPython v1.xx.x on xxxx-xx-xx; ESP32 module with ESP32
Type "help()" for more information.
>>>
```

代表成功。

離開 REPL：

```text
Ctrl + ]
```

在 REPL 中軟重啟：

```text
Ctrl + D
```

---

## 9. 核心工作流

### 模式 A：RAM 測試，不寫入 Flash

適合開發初期。

```powershell
uv run mpremote connect COM3 run test_led.py
```

這會把電腦上的 `test_led.py` 送到 ESP32 的 RAM 執行，不會永久存到 ESP32。

### 模式 B：掛載本機資料夾開發

當程式開始拆成多個檔案，例如 `lib/motor.py`、`lib/dht.py`，可以用：

```powershell
uv run mpremote connect COM3 mount . + run main.py
```

ESP32 會直接讀取電腦目前的專案目錄，不用一直把 `lib/` 複製到板子上。

若要在掛載後進入 REPL 手動測試，可以：

```powershell
uv run mpremote connect COM3 mount . + repl
```

進入 REPL 後按 `Ctrl + D` 軟重啟，ESP32 會從掛載的目錄載入 `main.py`。

### 模式 C：正式部署到 ESP32

當程式穩定後，上傳到 ESP32：

```powershell
uv run mpremote connect COM3 cp boot.py :
uv run mpremote connect COM3 cp main.py :
uv run mpremote connect COM3 cp -r ./lib :
uv run mpremote connect COM3 reset
```

之後 ESP32 斷電重開也會自動執行。

---

## 10. 常用指令表

| 功能 | 指令 |
|---|---|
| 查看裝置 | `uv run mpremote connect list` |
| 進入 REPL | `uv run mpremote connect COM3 repl` |
| RAM 執行本機檔案 | `uv run mpremote connect COM3 run test_led.py` |
| 掛載並執行 main.py | `uv run mpremote connect COM3 mount . + run main.py` |
| 列出板子根目錄檔案 | `uv run mpremote connect COM3 ls :` |
| 上傳檔案 | `uv run mpremote connect COM3 cp main.py :` |
| 上傳資料夾 | `uv run mpremote connect COM3 cp -r ./lib :` |
| 下載檔案 | `uv run mpremote connect COM3 cp :main.py ./main_from_board.py` |
| 刪除檔案 | `uv run mpremote connect COM3 rm :main.py` |
| 建立資料夾 | `uv run mpremote connect COM3 mkdir :lib` |
| 移除資料夾 | `uv run mpremote connect COM3 rmdir :lib` |
| 安裝 MicroPython 套件到板子 | `uv run mpremote connect COM3 mip install 套件名稱` |
| 重啟板子 | `uv run mpremote connect COM3 reset` |

注意：

```text
uv add 是安裝電腦端 Python 套件
mpremote mip install 是安裝 MicroPython 套件到 ESP32
```

兩者不要混在一起。

---

## 11. VS Code 建議擴充套件

| 擴充套件 | 用途 |
|---|---|
| **Pylance** | Python 語法提示、型別檢查 |
| **Python** (Microsoft) | Python 語言基礎支援 |
| **MicroPico** 或 **RT-Thread MicroPython** | MicroPython 專用語法補全，可辨識 `machine`、`network` 等模組 |

> 注意：MicroPython 的 `machine`、`utime` 等模組在電腦端不存在，Pylance 會標紅色。安裝 MicroPython 擴充套件後可以載入正確的 stub 消除誤報。

安裝方式：VS Code 左側 Extensions（`Ctrl+Shift+X`）搜尋套件名稱安裝即可。

---

## 12. 最小測試程式

建立 `test_led.py`：

```python
from machine import Pin
from time import sleep

# EZ Start Kit+ 擴展板紅色 LED（GPIO 16）
# 注意：需接上擴展板 Micro USB 供電，燈才會亮
led = Pin(16, Pin.OUT)

while True:
    led.value(1)
    sleep(0.5)
    led.value(0)
    sleep(0.5)
```

執行：

```powershell
uv run mpremote connect COM3 run test_led.py
```

如果擴展板上的紅色 LED 閃爍，代表：

```text
uv 正常
mpremote 正常
ESP32 MicroPython 正常
COM Port 正常
擴展板供電正常
```

> 如果燈沒有亮，先確認擴展板的 Micro USB 有接上電源。若要改用 NodeMCU-32S 內建藍色 LED（不需擴展板供電），把 `Pin(16)` 改成 `Pin(2)` 即可。

---

## 13. 正式版 `main.py`

```python
from machine import Pin
from time import sleep

led = Pin(2, Pin.OUT)

def main():
    while True:
        led.value(1)
        sleep(0.5)
        led.value(0)
        sleep(0.5)

main()
```

部署：

```powershell
uv run mpremote connect COM3 cp main.py :
uv run mpremote connect COM3 reset
```

---

## 14. Wi-Fi 設定範例

### `config.example.py`

```python
WIFI_SSID = "your-wifi-ssid"
WIFI_PASSWORD = "your-wifi-password"
```

### `config.py`

```python
WIFI_SSID = "你的 Wi-Fi 名稱"
WIFI_PASSWORD = "你的 Wi-Fi 密碼"
```

`config.py` 不上傳 Git。

### `boot.py`

```python
import network
import time
from config import WIFI_SSID, WIFI_PASSWORD

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        timeout = 10
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1

    if wlan.isconnected():
        print("Wi-Fi connected")
        print("IP:", wlan.ifconfig()[0])
    else:
        print("Wi-Fi connection failed")

connect_wifi()
```

部署：

```powershell
uv run mpremote connect COM3 cp boot.py :
uv run mpremote connect COM3 cp config.py :
uv run mpremote connect COM3 reset
```

---

## 15. 團隊開發流程

### 第一次建立專案的人

```powershell
uv init esp32-micropython-project
cd esp32-micropython-project
uv add mpremote esptool
git add .
git commit -m "Initialize ESP32 MicroPython project with uv"
```

### 其他組員拿到專案後

```powershell
git clone 專案網址
cd esp32-micropython-project
uv sync
uv run mpremote connect list
```

`uv sync` 會依據 `pyproject.toml` 和 `uv.lock` 建立或同步專案環境。

---

## 16. 日常開發節奏

建議每天這樣做：

```text
1. 開 VS Code
2. 開 Terminal
3. 確認 ESP32 COM Port
4. 寫 test_xxx.py
5. 用 uv run mpremote ... run 測試
6. 測穩後整合進 main.py 或 lib/
7. 正式部署到 ESP32
8. git commit
```

實際指令：

```powershell
uv run mpremote connect list
uv run mpremote connect COM3 run test_led.py
uv run mpremote connect COM3 run test_sensor.py
uv run mpremote connect COM3 cp main.py :
uv run mpremote connect COM3 cp -r ./lib :
uv run mpremote connect COM3 reset
git add .
git commit -m "Add sensor and LED control"
```

---

## 17. 常見錯誤處理

### 17.1 找不到 `uv`

重新開 PowerShell，或確認 uv 安裝路徑已加入 PATH。

檢查：

```powershell
uv --version
```

### 17.2 找不到 `mpremote`

不要直接打：

```powershell
mpremote connect list
```

先用：

```powershell
uv run mpremote connect list
```

因為 `mpremote` 是裝在 uv 專案環境裡。

### 17.3 找不到 COM Port

檢查：

```text
1. USB 線是否支援資料傳輸（充電線無法傳輸資料）
2. 驅動是否正確安裝
3. 裝置管理員是否看到 COM3 / COM4（Windows）
4. ls /dev/tty.usb* 是否看到裝置（macOS）
5. ls /dev/ttyUSB* 是否看到裝置（Linux）
6. 是否被 Thonny、Arduino IDE、其他 Terminal 占用
7. 是否換一個 USB 孔
```

### 17.4 Serial Port Occupied

錯誤類似：

```text
could not open port COM3
Access is denied
```

解法：

```text
關掉 Thonny
關掉 Arduino Serial Monitor
關掉其他 mpremote repl
拔掉重插 ESP32
```

### 17.5 燒錄失敗（Wrong address / 無法連線）

常見原因：

```text
1. --chip 型號填錯
2. 起始地址用錯（ESP32 原版 0x1000，S2/S3/C3 用 0x0）
3. 沒有按住 BOOT 鍵
4. baud rate 太高，降速或移除 --baud 參數
```

### 17.6 `ImportError`

如果程式有：

```python
from lib.motor import Motor
```

但沒有上傳 `lib/`，會失敗。

解法一（上傳到板子）：

```powershell
uv run mpremote connect COM3 cp -r ./lib :
```

解法二（掛載目錄開發時）：

```powershell
uv run mpremote connect COM3 mount . + run main.py
```

---

## 18. 建議的 `pyproject.toml`

執行 `uv add mpremote esptool` 後，大概會像這樣：

```toml
[project]
name = "esp32-micropython-project"
version = "0.1.0"
description = "ESP32 MicroPython project using VS Code, uv, mpremote, and esptool"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "esptool",
    "mpremote",
]
```

如果你們要固定 Python 版本，可以使用：

```powershell
uv python pin 3.12
```

這會更新 `.python-version`。

---

## 19. 可選：加入自動部署腳本

### `tools/deploy.ps1`

```powershell
$PORT = "COM3"

uv run mpremote connect $PORT cp boot.py :
uv run mpremote connect $PORT cp main.py :
uv run mpremote connect $PORT cp -r ./lib :
uv run mpremote connect $PORT reset
```

執行：

```powershell
powershell -ExecutionPolicy Bypass -File tools/deploy.ps1
```

### `tools/run-test.ps1`

```powershell
param(
    [string]$File = "test_led.py",
    [string]$Port = "COM3"
)

uv run mpremote connect $Port run $File
```

執行：

```powershell
powershell -ExecutionPolicy Bypass -File tools/run-test.ps1 test_led.py COM3
```

---

## 20. 最推薦的標準流程

### 第一次設定

```powershell
uv init esp32-micropython-project
cd esp32-micropython-project
uv add mpremote esptool
uv run mpremote connect list
```

### 每次開發

```powershell
uv run mpremote connect COM3 run test_led.py
```

### 正式部署

```powershell
uv run mpremote connect COM3 cp boot.py :
uv run mpremote connect COM3 cp main.py :
uv run mpremote connect COM3 cp -r ./lib :
uv run mpremote connect COM3 reset
```

### 團隊同步

```powershell
git pull
uv sync
uv run mpremote connect list
```

---

## 21. EZ Start Kit+ 各元件快速測試範例

以下範例皆可直接用 `uv run mpremote connect COM3 run xxx.py` 測試，不需寫入 Flash。

### 21.1 按鍵控制 LED

```python
from machine import Pin
from time import sleep

button_a = Pin(5, Pin.IN, Pin.PULL_UP)   # 按鍵 A
led_r    = Pin(16, Pin.OUT)               # 紅 LED

while True:
    if button_a.value() == 0:   # 按下為 LOW
        led_r.value(1)
    else:
        led_r.value(0)
    sleep(0.05)
```

### 21.2 三色 LED 輪流亮（紅綠燈練習）

```python
from machine import Pin
from time import sleep

led_r = Pin(16, Pin.OUT)
led_y = Pin(12, Pin.OUT)
led_g = Pin(13, Pin.OUT)

for led in [led_r, led_y, led_g]:
    led.value(1)
    sleep(0.5)
    led.value(0)
```

### 21.3 DHT11 讀取溫濕度

```python
import dht
from machine import Pin
from time import sleep

sensor = dht.DHT11(Pin(15))

while True:
    sensor.measure()
    print(f"溫度: {sensor.temperature()}°C  濕度: {sensor.humidity()}%")
    sleep(2)
```

### 21.4 光感測器與可變電阻

```python
from machine import ADC, Pin
from time import sleep

light = ADC(Pin(39))
light.atten(ADC.ATTN_11DB)   # 量測範圍 0–3.3V

pot = ADC(Pin(34))
pot.atten(ADC.ATTN_11DB)

while True:
    print(f"光感測器: {light.read()}  可變電阻: {pot.read()}")
    sleep(0.5)
```

### 21.5 無源蜂鳴器播放音符

```python
from machine import Pin, PWM
from time import sleep

buzzer = PWM(Pin(14), freq=440, duty=512)   # 440Hz = La

sleep(0.5)
buzzer.deinit()   # 停止
```

### 21.6 OLED 顯示文字

```python
# 先安裝驅動到 ESP32：
# uv run mpremote connect COM3 mip install ssd1306

from machine import I2C, Pin
import ssd1306

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

oled.fill(0)
oled.text("Hello NDHU!", 0, 0)
oled.text("ESP32 Ready", 0, 16)
oled.show()
```

> 注意：EZ Start Kit+ 的 OLED 驅動晶片為 SH1106（非 SSD1306），若畫面顯示異常，請改裝 `sh1106` 驅動並使用對應函式庫。

### 21.7 RGB LED（WS2812 / NeoPixel）

```python
from machine import Pin
from neopixel import NeoPixel
from time import sleep

np = NeoPixel(Pin(26), 3)   # 3 顆 RGB LED，NeoPixel 已內建於 MicroPython

colors = [(255, 0, 0), (255, 200, 0), (0, 255, 0)]   # 紅、黃、綠
for i, c in enumerate(colors):
    np[i] = c
np.write()
sleep(1)

for i in range(3):
    np[i] = (0, 0, 0)
np.write()
```

> NeoPixel 模組已內建於 MicroPython，不需另行安裝。

---

## 22. 一句話總結

**用 uv 管理電腦端 Python 工具，用 mpremote 跟 ESP32 對話；測試時跑 RAM，完成後才寫入 ESP32 Flash。**
