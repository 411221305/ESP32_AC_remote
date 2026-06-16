# TaiSEIA ESPHome Sample Notes

Reference repo:

```text
https://github.com/xangin/TaiSEIA_ESPhome_samples.git
```

## What The Sample Uses

The Hitachi climate samples do not use an IR transmitter or learned remote codes.
They use the ESPHome external component `taixia` and talk to the air conditioner
through UART.

Important lines from `Hitachi/Climate-ESP32.yaml`:

```yaml
external_components:
  - source: github://tsunglung/taixia@master
    components: [ taixia ]

uart:
  id: uart_taixia
  tx_pin: GPIO17
  rx_pin: GPIO16
  baud_rate: 9600

climate:
  - platform: taixia
    name: "Climate"

taixia:
  sa_id: 1
```

The ESP32C3 sample uses:

```yaml
uart:
  tx_pin: GPIO7
  rx_pin: GPIO6
  baud_rate: 9600
```

## Why This Matters

This is a wired serial control method, not an IR-blaster method.
It can be much more reliable than replaying RS13T1 infrared codes, but it requires
access to the air conditioner's internal TaiSEIA/CN connector and suitable voltage
level handling.

For the current class project goal, the IR approach is still valid because it uses
an external IR transmitter module. The TaiSEIA sample is best used as evidence that
Hitachi units can also be controlled by a direct UART interface.

## Practical Decision

Continue IR if:

- You need a non-invasive project that does not open the AC unit.
- The assignment specifically wants an external IR transmitter.
- You can aim the IR LED directly at the AC receiver.

Consider TaiSEIA/UART if:

- IR remains unreliable after verifying GPIO, polarity, and transmitter power.
- You are allowed to access the AC service connector safely.
- You want two-way state feedback such as indoor temperature, model info, errors,
  energy, and operating hours.

## Current IR Debug Implication

This sample does not provide RS13T1 IR raw codes. It cannot directly fix the IR
timing or learned-code issue. It does suggest that if the target AC supports the
TaiSEIA connector, a UART implementation may be a more reliable second version.
