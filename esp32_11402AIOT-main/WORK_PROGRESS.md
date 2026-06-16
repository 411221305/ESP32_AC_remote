# Work Progress

Date: 2026-05-13

## Today's Work: IR Remote + OLED Display

### Goal

Decode an NEC infrared remote on the ESP32 and show each key press on the
SSD1306 128x64 I2C OLED in real time.

### Hardware

- Board connection: `COM3`
- IR receiver: GPIO `33` (pull-up enabled)
- OLED: I2C bus 0, SDA `21`, SCL `22`, address `0x3C`
- Remote: 17-key NEC remote (already mapped in `ir.py:KEY_BY_RAW`)

### What Was Built

- `ir.py` — pure-Python NEC decoder. Reads raw pulses from GPIO 33, decodes
  the 32-bit address/command frame, and exposes three entry points:
  `capture_keys()`, `monitor_keys()`, `confirm_all_keys()`.
- `test_ir_oled.py` — integration test. Imports `read_ir`, `decode_nec`,
  `KEY_BY_RAW`, `RECV_PIN` from `ir.py`, initialises the OLED, and refreshes
  the screen on every valid key press with key name, raw code, address,
  command, and a press counter.
- `tools/record-ir.ps1` — wraps `mpremote run ir.py` with `Tee-Object` so a
  capture session is logged to `ir_capture.txt`.
- `tools/run-test.ps1` — default `-File` switched from `test_led.py` to
  `test_ir_oled.py`, so the `Run current MicroPython file` task works
  out-of-the-box.

### Verified Behavior

Live on hardware (24 key presses across 1, 2, 4, 5, 6, UP, LEFT, RIGHT):

```
I2C scan: ['0x3c']
OLED ready. IR on GPIO 33
key=2 raw=0xB946FF00 count=1
key=UP raw=0xE718FF00 count=2
...
key=5 raw=0xBF40FF00 count=24
```

OLED idle screen:
```
IR -> OLED
GPIO 33
Press a key...
```

OLED after key press:
```
Key:  5             #24
Raw:
0xBF40FF00
a=00 c=BF
```

### Debugging Notes

- Initial "OLED 黑屏" symptom turned out to be `mpremote: failed to access
  COM3 (it may be in use by another program)` — another mpremote / Serial
  Monitor session was holding the port. Closing it unblocked everything.
- `lib/kit_pins.py` lists `IR_RECEIVER = 35` with a "confirm before use"
  note. The actual working pin on this expansion board is `33`. Did not
  edit `kit_pins.py` yet to avoid breaking other potential callers.

### Commands Used

```powershell
# Run the integration test (mounts project, streams device prints)
.\.venv\Scripts\mpremote.exe connect COM3 mount . + run test_ir_oled.py

# Record an IR capture session to ir_capture.txt
powershell -ExecutionPolicy Bypass -File tools\record-ir.ps1 -Port COM3

# Open REPL (Ctrl+] to exit, otherwise COM3 stays held)
.\.venv\Scripts\mpremote.exe connect COM3 repl
```

---

## Previous Work: RGB NeoPixel Blink (2026-05-06)

- `main.py` runs an RGB NeoPixel blink on boot:
  pixel 1 red, pixel 2 green, pixel 3 blue at brightness `64`,
  1 s on / 1 s off, 10 cycles, all off at end.
- Status LEDs (red `16`, yellow `12`, green `13`) are turned off before the
  RGB test starts.
- `test_rgb_once.py` reproduces the same behaviour for `mpremote run`.
