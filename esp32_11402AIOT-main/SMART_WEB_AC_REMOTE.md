# ESP32 智慧網頁冷氣遙控器

## 硬體接線

- IR Transmitter VCC -> ESP32 Vin
- IR Transmitter GND -> ESP32 GND
- IR Transmitter DAT/S -> ESP32 GPIO 25
- IR Receiver -> 內建接收器，程式預設 GPIO 33
- 指示 LED -> GPIO 16 / 12 / 13

## 使用方式

1. 部署程式到 ESP32：

```powershell
powershell -ExecutionPolicy Bypass -File tools\deploy.ps1 -Port COM3
```

2. 手機連線 Wi-Fi：

- SSID: `ESP32-AC-Remote`
- Password: `12345678`

3. 手機開啟：

```text
http://192.168.4.1
```

4. 先按對應按鍵的 `Learn`，把原本冷氣遙控器對準 ESP32 的紅外線接收器並按一下實體按鍵。

5. 錄製成功後，按 `Send`，ESP32 會從 GPIO25 發出 38kHz 紅外線訊號。

## 日立 RS13T1 注意事項

日立冷氣遙控器通常會送出一整包「目前冷氣狀態」，不是只送出單一按鍵命令。
例如 `Temp -` 可能代表「冷氣、25 度、自動風、擺風狀態」整包資料。

建議錄製時用固定流程：

1. 先把原廠遙控器調到想要的狀態。
2. 在網頁按對應的 `Learn`。
3. 對準 ESP32 接收器，按一次原廠遙控器按鍵。
4. 每個常用狀態分別錄製，例如 `Cool 26`、`Cool 25`、`Dry`、`Fan`。

程式已針對 Hitachi A/C 長封包調整：

- `MAX_PULSES = 1300`
- `FRAME_TIMEOUT_US = 1800000`
- `MAX_SEND_US = 2200000`

## 訊號診斷

網頁每個按鍵會顯示：

- `pulses`: 學到的 mark/space 數量。日立冷氣通常應該是數百個以上。
- `ms`: 整段訊號時間。
- `looks ok`: 代表長度看起來合理。
- `too short for Hitachi AC`: 通常代表沒學完整、按太短、接收器沒對準，或接收腳位錯。
- `very long; possible noise`: 可能收到環境雜訊或一直按住太久。

`Probe IR TX` 用來確認 GPIO25 的 IR 發射模組是否真的有出光。測試時請把 IR 發射 LED 對準 ESP32 的 IR 接收器：

- `Probe OK`：ESP32 接收器有看到自己的紅外線輸出。
- `Probe failed`：優先檢查 VCC/GND/DAT、GPIO25、發射模組方向，或在網頁切換 `TX Inverted` 後再測。

按 `Send` 後的 `rx hits` 也可以輔助判斷：

- `rx hits > 0`：發射模組大概率有發出 IR。
- `rx hits = 0`：不一定代表沒發，可能只是發射器沒有對準接收器；但若 Probe 也失敗，就多半是硬體或極性問題。

## 當機排查

日立冷氣訊號很長，若用舊版 tuple 格式存很多筆，ESP32 容易因 RAM 不足當機。
新版會用 compact 格式儲存，只保留 duration，mark/space 用交錯順序推算。

如果你之前已經 Learn 過，建議先清空舊資料後重錄：

```powershell
powershell -ExecutionPolicy Bypass -File tools\deploy.ps1 -Port COM3 -ResetCodes
```

網頁上會顯示 `Free RAM`。如果錄幾筆後 Free RAM 明顯掉到很低，請先只保留 2-4 個最常用狀態，例如 `Power`、`Cool 26`、`Cool 25`、`Dry`。

真正送給冷氣時，程式不再同時讀接收器，避免影響 IR timing；請用 `Probe IR TX` 單獨確認發射模組有出光。

## 清除已錄製訊號

一般部署不會覆蓋 ESP32 上已學習的 `ac_codes.py`。若要清空並重置錄製資料：

```powershell
powershell -ExecutionPolicy Bypass -File tools\deploy.ps1 -Port COM3 -ResetCodes
```

## 調整接收器腳位

如果你的 EZ Start Kit+ 內建紅外線接收器不是 GPIO33，請修改 `main.py`：

```python
IR_RX_PIN = 33
```
