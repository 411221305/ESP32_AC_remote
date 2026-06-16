# ESPHome Native Hitachi IR Test

ESPHome's official IR Remote Climate component lists native Hitachi platforms:

- `hitachi_ac344`
- `hitachi_ac424`

Reference:

```text
https://esphome.io/components/climate/climate_ir/
```

The project now includes two ESPHome test configs:

- `esphome-hitachi-ac344.yaml`
- `esphome-hitachi-ac424.yaml`

Both use:

```yaml
remote_transmitter:
  id: ir_tx
  pin: GPIO25
  carrier_duty_percent: 50%

remote_receiver:
  id: ir_rx
  pin:
    number: GPIO33
    inverted: true
    mode:
      input: true
      pullup: true
  tolerance: 55%
```

## How To Test

1. Edit `YOUR_WIFI_SSID` and `YOUR_WIFI_PASSWORD` in one YAML.
2. Flash `esphome-hitachi-ac344.yaml` first.
3. Open the ESPHome web server or Home Assistant climate entity.
4. Send Cool 26 / Off.
5. If AC344 does not work, flash `esphome-hitachi-ac424.yaml` and repeat.

ESPHome is worth testing because its remote transmitter timing is handled by the
ESPHome native IR stack instead of MicroPython `sleep_us()` loops.

On this MicroPython build, keep `TX Normal` as the default. If `TX Inverted`
leaves the transmitter LED continuously on, treat that as a polarity mismatch
for the module and do not use it as the working mode.
