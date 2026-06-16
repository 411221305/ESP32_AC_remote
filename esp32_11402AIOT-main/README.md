# ESP32 MicroPython Project (11402 AIOT)

This project is set up for ESP32 MicroPython development with VS Code, uv, mpremote, and esptool.

## 快速開始（推薦）

### 1. 安裝 uv

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 一鍵環境檢查 + 自動修復

```powershell
powershell -ExecutionPolicy Bypass -File tools\check_env.ps1 -Fix
```

這個指令會自動：
- 檢查 Python（3.11+）+ uv 是否安裝
- 用 `uv sync` 安裝套件（mpremote, esptool）
- 偵測並自動安裝 USB 驅動（CP210x / CH340 / FTDI）
- 偵測 ESP32 COM port（多板子智慧選擇）
- 下載並燒錄 MicroPython 韌體（失敗自動換 port + BOOT 模式重試）

不加 `-Fix` 只檢查不修改：
```powershell
powershell -ExecutionPolicy Bypass -File tools\check_env.ps1
```

### 3. VS Code 快捷任務

按 `Ctrl+Shift+P` → 輸入 "Tasks: Run Task"：

| 任務 | 說明 |
|------|------|
| ESP32: 環境檢查 | 檢查開發環境是否正確 |
| ESP32: 環境設定 (自動修復) | 自動安裝套件、驅動、韌體 |
| ESP32: Deploy | 上傳 boot.py / main.py / lib/ |
| ESP32: Run current MicroPython file | 掛載專案目錄並執行目前焦點的 .py（預設 `test_ir_oled.py`） |
| ESP32: Soft reset | 軟重啟 ESP32 |
| ESP32: Serial monitor | 開啟序列埠監控（mpremote repl） |

> 提示：跑任何 mpremote 指令前要確保 COM3 沒被佔用（關掉 Serial Monitor、其他 REPL 視窗）。

---

## 手動操作（進階）

### 同步套件

```powershell
uv sync
```

檢查工具：

```powershell
uv run python --version
uv run mpremote --help
uv run esptool version
```

### 找 ESP32 Port

```powershell
uv run mpremote connect list
```

### Run Without Writing to Flash

```powershell
uv run mpremote connect COM3 run test_led.py
uv run mpremote connect COM3 run test_sensor.py
uv run mpremote connect COM3 run test_wifi.py
```

### Mount Local Folder

```powershell
uv run mpremote connect COM3 mount . + run main.py
```

### Deploy to ESP32

```powershell
powershell -ExecutionPolicy Bypass -File tools/deploy.ps1 -Port COM3
```

### Flash MicroPython Firmware（手動）

```powershell
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Port COM3 -Firmware .\firmware\ESP32_GENERIC-20260406-v1.28.0.bin
```

> 提示：`tools\check_env.ps1 -Fix` 已包含自動下載 + 燒錄，建議優先使用。

## IR 紅外線遙控

`ir.py` 為 NEC 協定純 Python 解碼器（不依賴 RMT 或外部驅動），用於讀取 38 kHz 紅外線遙控器訊號。

### 1. 硬體接線

IR 接收模組通常是 3 針（VS1838B / TL1838 等同類）：

| IR 模組腳位 | ESP32 接線 |
|-------------|------------|
| **VCC**     | 3.3V       |
| **GND**     | GND        |
| **DATA / OUT** | GPIO `33`（程式內 `RECV_PIN`） |

> 註：`lib/kit_pins.py` 把 `IR_RECEIVER` 標為 `35`，但本擴充板實測為 `33`。若你的接線與 `ir.py` 不同，修改 [ir.py:4](ir.py#L4) 的 `RECV_PIN` 即可。
>
> 接好後可以用手機相機對著遙控器前端按鍵測試 — 看到紫色閃光代表遙控器是好的。

### 2. 三種執行模式

`ir.py` 提供三種模式（預設 `main()` 跑 `confirm_all_keys()`）：

| 函式 | 用途 |
|------|------|
| `confirm_all_keys()` | 對照模式：按一次印一次按鍵名稱與 raw code（首次按出現 `new key:`，重複出現 `again:`） |
| `monitor_keys()` | 監聽模式：持續解碼並印出，包含 `repeat` 訊框與失敗的波形 dump（除錯用） |
| `capture_keys()` | 錄製模式：依序提示按 `*` `#` `UP` `DOWN` `LEFT` `RIGHT` `OK`，最後印出可貼回程式的 `KEY_BY_RAW` 字典 |

要切換模式，編輯 [ir.py:323-324](ir.py#L323-L324)：

```python
def main():
    confirm_all_keys()   # ← 改成 monitor_keys() 或 capture_keys()
```

### 3. 執行 ir.py

**方法 A：VS Code Task（最簡單）**

1. 在編輯器打開 `ir.py`，讓它成為焦點分頁
2. `Ctrl+Shift+P` → `Tasks: Run Task` → `ESP32: Run current MicroPython file`
3. 在 Terminal 面板（`` Ctrl+` ``）看輸出
4. 按遙控器，觀察印出的 raw code

**方法 B：用 record-ir.ps1（會同步存檔）**

```powershell
powershell -ExecutionPolicy Bypass -File tools\record-ir.ps1 -Port COM3
```

輸出會即時顯示在終端，同時 Tee 到 `ir_capture.txt`（已 gitignore）。適合上課示範後留底比對。

**方法 C：手動 mpremote**

```powershell
.\.venv\Scripts\mpremote.exe connect COM3 mount . + run ir.py
```

按 `Ctrl+C` 中斷迴圈，再按 `Ctrl+]` 完整離開 mpremote（**沒按 `Ctrl+]` 的話 COM3 會繼續被佔住**，下次連會失敗）。

### 4. 錄製新遙控器（換遙控器或缺鍵時）

1. 編輯 [ir.py:323](ir.py#L323) 改成 `capture_keys()`
2. 跑 `ir.py`，依照畫面提示一次按一個鍵後放開
3. 程式跑完會印出新的 `KEY_BY_RAW = { ... }` 區塊
4. 把它貼回 [ir.py:12-30](ir.py#L12-L30) 取代原本的字典
5. 把 `main()` 改回 `confirm_all_keys()` 驗證
6. 若需要錄製額外按鍵（如音量鍵、靜音），把鍵名加進 [ir.py:32](ir.py#L32) 的 `CAPTURE_KEYS`

### 5. IR + OLED 即時顯示（test_ir_oled.py）

按下遙控器後，OLED 會顯示按鍵名稱、raw code、address / command、累計次數。

```powershell
# Task 預設就是這個檔
powershell -ExecutionPolicy Bypass -File tools\run-test.ps1 -Port COM3

# 或在 VS Code: Run Task → ESP32: Run current MicroPython file
```

成功時 OLED 顯示：
```
Key:  5             #24
Raw:
0xBF40FF00
a=00 c=BF
```

### 6. 常見問題

| 症狀 | 原因 / 處理 |
|------|------------|
| `failed to access COM3` | COM3 被別人佔用：關閉所有 mpremote / Serial Monitor 視窗，必要時 `Get-Process mpremote \| Stop-Process -Force` |
| 按遙控器沒反應 | 1) 檢查 IR 模組電源 2) 確認 `RECV_PIN` 與實際接線一致 3) 用手機相機檢查遙控器有沒有發紅外光 |
| 印出 `decode failed` | 不是 NEC 協定（如 Sony SIRC、Philips RC-5），目前 `decode_nec` 只支援 NEC |
| 印出 `key=?` 但有 raw code | 這顆鍵還沒登錄 — 把 raw code 加進 [ir.py:KEY_BY_RAW](ir.py#L12) |
| 一直印 `NEC repeat` | 按住按鍵不放會持續送 repeat 訊框，這是正常的；放開即停 |

## Secrets

Copy `config.example.py` to `config.py`, then edit Wi-Fi settings. `config.py` is ignored by Git.
