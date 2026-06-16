# ESP32 智慧網頁冷氣遙控器開發紀錄

日期：2026-06-16

這是一份盡量完整的專案開發紀錄，目的是把整個 ESP32 智慧冷氣遙控器從構想到完成的過程留下來，方便後續維護、交接、回顧與延伸。

本專案重點：

- 保留 MicroPython
- 用 ESP32 建立本地 AP + HTTP 網頁控制
- 透過 IR Transmitter 發出實體紅外線訊號控制冷氣
- 以 Hitachi `RAS-40HQP` / 遙控器 `RS13T1` 為主要可用路徑
- 最終確認 `Hitachi344 Cool 26`、`Hitachi344 Off`、學習後重送都可用

---

## 1. 專案目標與設計初衷

這個專案的出發點很單純：

1. 舊型冷氣沒有網路功能
2. 手機大多也沒有 IR Blaster
3. 需要一個小型、低成本、可放在家裡長期使用的橋接裝置

因此選擇：

- ESP32 當核心
- 用 MicroPython 寫控制邏輯
- 用手機連到 ESP32 自架 AP
- 透過網頁按鈕送出 IR 指令

這樣的好處是：

- 不需要依賴雲端
- 不需要另外裝 App
- 手機開瀏覽器就能用
- 可以保留本地控制
- 遙控器沒在手邊時也能操作

---

## 2. 專案硬體配置

### 2.1 核心硬體

- ESP32 開發板
- EZ Start Kit+ 擴充板
- 外接 IR 發射模組
- 內建 IR 接收器
- 內建 LED 與 NeoPixel 作為狀態指示

### 2.2 最終接線

IR Transmitter：

- `VCC -> Vin`
- `GND -> GND`
- `DAT/S -> GPIO 25`

IR Receiver：

- `DATA -> GPIO 33`

板載 LED / 狀態：

- `LED_OK = 16`
- `LED_ERROR = 12`
- `LED_READY = 13`
- `NEOPIXEL_PIN = 26`

### 2.3 為什麼選 GPIO 25

原本曾嘗試其他腳位，後來改到 `GPIO 25`，原因是：

- 接線比較安全
- 避開板上其他用途可能衝突的腳位
- 在測試中可以正常輸出 IR

### 2.4 為什麼最後會換 IR 發射器

最早遇到的主要問題不是協定，而是輸出太弱：

- 手機照看不到明顯閃爍
- 冷氣完全沒反應
- 即使 probe 看起來有訊號，實際距離一拉開就失效

後來把 IR 發射器換成：

- 內建放大電路的 IR 發射模組

換完後才真正穩定。

這一點是整個專案最關鍵的轉折。

---

## 3. 初期工作內容

專案最一開始不是冷氣控制，而是整個 ESP32 + MicroPython 工程環境的建立與測試。  
包含：

- `main.py`
- `boot.py`
- `ac_codes.py`
- `ir.py`
- `test_ir_oled.py`
- `test_led.py`
- `test_wifi.py`
- `tools/deploy.ps1`
- `tools/flash.ps1`
- `tools/run-test.ps1`
- `tools/record-ir.ps1`
- `tools/check_env.ps1`

這些工具的作用是：

- 確認板子連線
- 測試 LED / Wi-Fi / IR / OLED
- 用 `mpremote` 上傳與執行程式
- 用 `esptool` 燒錄 MicroPython

---

## 4. 一開始的錯誤方向與排查歷程

### 4.1 看起來有送訊號，但冷氣不動

最早的狀況是：

- 頁面按了有反應
- LED 會亮
- IR 模組也似乎有動作
- 但冷氣就是不理

當時一度懷疑：

- 協定錯了
- 學習不完整
- 發送碼格式有問題
- 波形不對
- 舊模型不支援

### 4.2 Learn 偶爾報錯但又像有學到

學習流程曾出現過幾個錯誤訊息，例如：

- `learn failed local variable referenced before assignment`
- `Blast failed: 'TimeoutError' isn't defined`
- `Blast failed: IR send timeout`

這些錯誤讓人一度以為：

- 程式本身不穩
- Learn 取得的內容是壞的
- 發送端或封包生成有問題

但後來逐步證明：

- Learn 有時仍然有抓到完整資料
- 問題不一定在學習邏輯本身
- 更大可能是發射端強度不足或送出的變體不是冷氣接受的那組

### 4.3 當機與 timeout

在測試其他訊號時曾有：

- 當機
- timeout
- repeated send 超時

後來把 `TimeoutError` 改成 `RuntimeError`，因為 MicroPython 環境中那個例外並不保證存在。

同時也調整了傳送 timeout 的計算方式，避免 repeat 時太早誤判失敗。

---

## 5. 參考資料比對過程

整個專案過程中，有比對過下列參考：

- `cwstedctw/esp32_11402AIOT`
- `xangin/TaiSEIA_ESPhome_samples`
- `js4jiang5/Hitachi_AC`
- `crankyoldgit/IRremoteESP8266`

### 5.1 參考的價值

這些資料幫助確認幾件事：

- Hitachi 冷氣確實有多個變體
- `AC344` 與 `AC424` 都可能相關
- ESPHome 與 IRremoteESP8266 都有相關實作思路
- 不是每台 Hitachi 都是同一個協定版本

### 5.2 最後的判斷

後來實際測出：

- `Hitachi344 Cool 26` 距離近時可用
- 代表 `AC344` 方向是對的
- 問題重點轉成：
  - IR 強度
  - 發送穩定性
  - off 行為
  - UI 結構

---

## 6. 重要的協定與機型判斷

### 6.1 冷氣與遙控器型號

最後確認的資訊：

- 冷氣型號：`RAS-40HQP`
- 遙控器型號：`RS13T1`

### 6.2 手動辨識到的候選

曾經出現過的判斷方向包括：

- `691 pulses, 437 ms, hitachi AC344 / 344-bit candidate`
- `424`
- `344`

最後實際有效的是：

- `Hitachi344`

### 6.3 為什麼不繼續硬猜 ESPHome

當時一度懷疑可不可以直接靠 ESPHome 內建 Hitachi 類別解決。  
但最後沒有走那條路，原因是：

- 專案目標是保留 MicroPython
- 現在這套已經能工作
- 再轉平台風險更高
- 需要的只是把可用狀態穩定化

所以最後整體策略是：

- 維持 MicroPython
- 維持本地 web UI
- 維持自訂 IR 生成與學習流程

---

## 7. 真正找到原因：IR 輸出功率不足

這是整個專案最重要的結論。

### 7.1 為什麼前面一直失敗

因為當時的 IR Transmitter：

- 功率太弱
- 距離稍微一遠就失效
- 近距離可能看似正常，但不夠實際使用

### 7.2 直接證據

後來實測發現：

- `Hitachi344 Cool 26` 在距離冷氣接收窗約 `15 cm` 時可以成功遙控

這代表：

- 協定沒有大方向錯誤
- 訊號本體是可用的
- 真正問題在輸出端

### 7.3 硬體修正

更換成：

- 內建放大電路的 IR 發射模組

之後：

- `344 Cool 26` 正常
- Learn 正常
- Off 正常
- 網頁控制開始變成可用工具，而不是實驗品

---

## 8. 程式架構的演進

### 8.1 早期結構

最初的 `main.py` 偏向測試台，包含很多診斷按鈕：

- `Stop IR Output`
- `Probe IR TX`
- `TX Normal`
- `TX Inverted`
- `Hitachi424 Cool 26`
- `Hitachi424 Off`
- `Hitachi344 Cool 26`
- `Hitachi344 Off`
- `Learn Power`
- `Learn Cool`
- `Send Learned Power`
- `Send Learned Cool`
- `Blast Learned Power x5`
- `Blast Hitachi424 Cool26 x5`

這樣雖然方便測試，但不適合日常使用。

### 8.2 介面正式化

後來把首頁重整成三層：

1. 主控制
2. 已學習控制
3. 備援與診斷

這樣的好處：

- 最常用的按鈕一眼可見
- 次要功能不會干擾日常操作
- debug 不會和正式控制混在一起

### 8.3 結果頁也同步整理

不只首頁，`action_page()` 也一起改成一致風格，讓按完按鈕後的結果頁不會再跳回老舊樣式。

---

## 9. Hitachi 344 細調控制的加入

後來為了讓日常更好用，加入了 344 的細調能力。

### 9.1 可調項目

目前能辨識並控制的細項有：

- 模式：`Cool / Dry / Fan`
- 溫度：`16 - 32°C`
- 風速：`Auto / Low`
- 電源：`On / Off`
- 微調：`Temp + / Temp -`

### 9.2 快捷按鈕

為了方便操作，頁面上還加了常用溫度快捷鍵：

- `22C`
- `24C`
- `26C`
- `28C`

### 9.3 狀態記憶

`LAST_HITACHI344` 會記住上一次的：

- mode
- temp
- fan
- power

這樣你按 `Temp +`、`Temp -` 不必每次都從頭設定。

---

## 10. Off 行為的修正歷程

### 10.1 第一個 off 問題

一開始發現：

- `Hitachi344 Off` 不一定會被冷氣接受
- `Learned Off` 也不一定穩

### 10.2 off 的改法

後來把 off 改成：

- 先套用一個完整的冷房狀態
- 再把 power bit 切成 off

這比單純把某個 byte 改掉更穩定。

### 10.3 第二個 off 問題

後來在 344 細調頁面又遇到一個 bug：

- 上一次的 `power=off` 狀態會黏住
- 之後按溫度或風速，冷氣也會一起關掉

### 10.4 最後修正

最後修成：

- 只要是在調 mode / temp / fan，就自動回 `power=on`
- 只有明確按 `Off` 才送 `power=off`

這才把整個操作邏輯理順。

---

## 11. 學習流程與重送流程

### 11.1 Learn 的作用

`Learn` 是用來從原始遙控器抓取脈衝，並存到 `ac_codes.py`。

### 11.2 學習後的行為

學到的資料會：

- 存進 `AC_CODES`
- 寫入 `ac_codes.py`
- 之後可用 `Send Learned ...` 重送

### 11.3 會遇到的情況

在開發過程中，學習曾有過這些現象：

- `local variable referenced before assignment`
- `No IR signal captured`
- 表面看似學到，但不確定完整性

最後解法不是一直追錯學習流程，而是：

- 驗證原始遙控器實際輸出
- 確認有沒有打到冷氣
- 用更強的發射器
- 再把學習按鍵整理進正式 UI

---

## 12. 網頁與路由演進

### 12.1 初期頁面

早期首頁是測試導向，方便逐一排查：

- probe IR
- polarity 切換
- blast 重送
- hitachi / hitachi424 生成碼

### 12.2 正式首頁

最後首頁變成：

- `Primary control`
- `Hitachi 344 Fine Tune`
- `Learned controls`
- `Secondary control`
- `Advanced tools`

### 12.3 新增的 344 路由

後來新增 `/hitachi344`：

- 讓細調按鈕可以用 query string 操作
- 可記住上一組狀態
- 可直接送出調整後的完整訊號

這個路由是正式版的重要一環。

---

## 13. 發生過的代表性訊息與現象

以下是開發過程中實際出現過、值得記錄的問題類型：

- `learn failed local variable referenced before assignment`
- `Blast failed: 'TimeoutError' isn't defined`
- `Blast failed: IR send timeout`
- `192.168.4.1` 拒絕連線
- `ESP32 wifi 連線失敗`
- `冷氣還是沒反應`
- `冷氣沒收到訊號`
- `off` 不穩
- `細調會黏住 power off`

這些問題最後大多不是單一 bug，而是：

- 硬體
- 協定
- 目標機型
- UI 狀態傳遞
- 程式例外處理

幾個因素一起造成的。

---

## 14. 部署與連線資訊

### 14.1 常見序列埠

後來確認 ESP32 USB 序列埠是：

- `COM4`

### 14.2 部署方式

常用部署指令：

```powershell
powershell -ExecutionPolicy Bypass -File tools\deploy.ps1 -Port COM4
```

部署內容包含：

- `boot.py`
- `main.py`
- `ac_codes.py`
- `lib/`

### 14.3 部署後行為

部署完成後，ESP32 會重啟，然後提供：

- AP SSID：`ESP32-AC-Remote`
- 預設網址：`http://192.168.4.1`

---

## 15. 目前 `main.py` 的角色

現在 `main.py` 已經不是單純測試檔，而是正式控制核心，包含：

- HTTP server
- AP 啟動
- IR 發送
- IR 學習
- Hitachi 344 / 424 生成碼
- Learned code 重送
- 344 細調控制
- 狀態顯示

---

## 16. 最終可用結果

專案現在已經達到這些目標：

### 16.1 已穩定可用

- 網頁控制冷氣
- `Hitachi344 Cool 26`
- `Hitachi344 Off`
- 學習按鍵
- 重送學習按鍵
- 344 模式 / 溫度 / 風速細調

### 16.2 已證實的可用範圍

- 344 協定可用
- Learn 可用
- Off 可用
- 細調可用
- 需要強 IR 發射器才足夠穩定

### 16.3 沒有再追的方向

以下方向目前沒有必要再繼續深入：

- ESPHome 轉換
- 完全重寫協定
- 繼續猜測硬體故障

原因是：

- 現有方案已經能實際使用
- 問題根源已經找到
- 再換系統不會增加太多價值

---

## 17. 之後如果要再擴充，可以做什麼

如果未來要繼續做，建議方向如下：

1. 再拆更多 344 細項
   - 例如更細的風速檔位
   - 擺風
   - 其他模式

2. 建立常用 preset
   - `Sleep`
   - `Quick Cool`
   - `Eco`

3. 做更完整的 learned profile 管理
   - 每個按鍵單獨保存
   - 顯示學到的 bytes / pulses / duration

4. UI 再分區
   - 日常區
   - 快速區
   - 高級區

5. 進一步整理成真正的使用說明
   - 例如 README 的精簡版
   - 或使用手冊

---

## 18. 最後的總結

這個專案最重要的不是某一段程式碼，而是整個排查過程最後得到的判斷：

1. 一開始以為是協定錯
2. 後來發現其實是 IR 發射功率不足
3. 換成有放大電路的發射器後，問題大幅改善
4. `Hitachi344` 才是真正可用的主要路徑
5. `Off` 與細調頁面曾有狀態綁定問題，但已修正
6. 這套 MicroPython ESP32 網頁遙控器已經能實際使用

這份紀錄保留下來的目的，就是讓之後再回來看時，不會只知道「最後能用」，而是知道「為什麼能用、之前卡在哪裡、怎麼解開的」。

---

## 附錄 A. 事件時間線

這裡把整個開發過程用更接近日誌的方式重新排列一次，方便回頭查。

### A1. 先建立 ESP32 + MicroPython + AP 網頁架構

最初先把基礎骨架建立起來：

- ESP32 啟動成 AP
- 網頁伺服器在 `192.168.4.1`
- 手機可連線開控制頁
- 用 `main.py` 處理 HTTP 請求
- 用 `boot.py` 保持開機行為簡單穩定

這一步的重點不是冷氣，而是先證明：

- ESP32 可以穩定當伺服器
- 網頁控制路由可以正常回應
- 板子可以重啟後自動起服務

### A2. 先試原始 IR 學習與播放

接著做 IR 相關測試：

- 讀取紅外線接收器脈衝
- 把脈衝存成資料
- 再把資料送回去

這階段的主要想法是：

- 先證明學習功能可以抓到資料
- 再證明重送功能可以吐出訊號

此時曾出現的誤判是：

- 以為 `learn` 報錯就代表沒有學到
- 以為 `blast` timeout 就代表訊號不完整

後來證明這些都不完全正確。

### A3. 進入 Hitachi 協定比對

之後開始比對 Hitachi 相關協定：

- AC344
- AC424
- 可能的 ESPHome Hitachi 類別
- IRremoteESP8266 的 Hitachi 分支

這段時間的重點不是「哪個名字對」，而是：

- 哪一組實際能讓冷氣動
- 哪一組脈衝長度與格式比較接近
- 哪一組在學習後能夠穩定重送

### A4. 第一個成功訊號

後來終於出現第一個確定有效的方向：

- `Hitachi344 Cool 26`
- 且在近距離下可以控制冷氣

這是整個專案的重要里程碑，因為它證明：

- 方向對了
- 協定類型大致對了
- 不是完全寫錯 IR

但是它也立刻暴露下一個問題：

- 發射強度不夠

### A5. 換 IR 發射器

這是第二個關鍵里程碑。

換成有放大電路的 IR 發射模組之後：

- 距離容忍度變好
- 成功率變高
- 不需要把發射頭貼太近

這時候專案才真的從「能看」變成「能用」。

### A6. Off 與 learned power 的整理

當確認 Cool 26 可用後，就開始處理另一個現實問題：

- `Off` 不穩
- 學習的 `off` 也不穩

這段修正的結果是：

- `Hitachi344 Off` 改成完整狀態再送
- `Learn Off` 與 `Send Learned Off` 納入流程
- 讓關機不只是口頭上的按鈕，而是能真的進入冷氣接受的格式

### A7. UI 從測試台變正式介面

原本頁面很像除錯工具箱，按鈕很多：

- probe
- polarity
- blast
- learn
- send
- hitachi
- hitachi424

後來整理成正式介面：

- 主控制
- 細調
- 學習按鈕
- 備援控制
- 進階工具折疊

這樣的好處是：

- 平常只看到真正常用的功能
- 但維修時又找得到測試工具

### A8. 344 細調與記憶狀態

之後加入 `LAST_HITACHI344`：

- 記住 mode
- 記住 temp
- 記住 fan
- 記住 power

再加上 `/hitachi344` 路由後，終於能直接按：

- `Temp +`
- `Temp -`
- `Fan Auto`
- `Fan Low`
- `Cool / Dry / Fan`

這讓 344 從固定預設按鈕變成真正可操作的控制器。

### A9. 細調 bug 修正

後來又發現：

- 如果前一個狀態是 `off`
- 細調按鈕有時會把 `power=off` 一起帶下去

造成結果是：

- 你按了溫度
- 冷氣卻還是被關掉

這個 bug 的本質是「狀態傳遞污染」。

修法是：

- 只要是調整 mode / temp / fan，就強制 `power=on`
- 只有按 `Off` 才送 `power=off`

這個修正完成後，細調功能才真正穩。

---

## 附錄 B. 各路由用途總表

### B1. ` / `

首頁，正式使用入口。

### B2. `/hitachi?cmd=...`

傳統 344 預設命令：

- `off`
- `cool25`
- `cool26`
- `dry`
- `fan`

### B3. `/hitachi344? ...`

344 細調控制，支援：

- `op=mode`
- `op=temp_up`
- `op=temp_down`
- `fan=auto`
- `fan=low`
- `power=on`
- `power=off`
- `temp=xx`

### B4. `/learn?cmd=...`

學習原始 IR 脈衝並寫入 `ac_codes.py`

### B5. `/send?cmd=...`

送出已學習的按鍵

### B6. `/blast?kind=...`

重複送出，用於測試強度或穩定性

### B7. `/probe`

用接收器驗證發射端是否有真的打出 IR

### B8. `/polarity`

切換 TX 正常 / 反相，用來排查輸出邏輯

### B9. `/stop`

停止 IR 輸出

### B10. `/hitachi424`

備援生成路徑，保留對照測試用途

---

## 附錄 C. 重要檔案說明

### C1. `main.py`

最核心的檔案，負責：

- AP 啟動
- Web server
- 按鈕頁面
- IR 發送
- IR 學習
- Hitachi 協定生成

### C2. `ac_codes.py`

學習結果儲存檔，內容是：

- 按鍵名稱
- 對應脈衝序列

### C3. `boot.py`

負責開機時的基本設定。

### C4. `SMART_WEB_AC_REMOTE.md`

專案對外說明版，偏向簡明使用說明。

### C5. `ESP32_AC_REMOTE_DEV_LOG.md`

這份檔案，偏向開發過程與排障紀錄。

