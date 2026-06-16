# Hitachi AC344 IR Reference

Reference repo:

```text
https://github.com/js4jiang5/Hitachi_AC
```

This repo is useful for the IR version of the project. It implements an ESPHome
external component based on Hitachi AC344 IR climate control.

Relevant protocol constants:

```text
Carrier: 38000 Hz
Duty in sample YAML: 50%
Header mark: 3300 us
Header space: 1700 us
Bit mark: 400 us
One space: 1250 us
Zero space: 500 us
State length: 43 bytes / 344 bits
Bit order: LSB first per byte
Footer mark: 400 us
Gap: 100000 us
```

The current `main.py` includes generated Hitachi AC344 buttons:

- Hitachi Off
- Hitachi Cool 25
- Hitachi Cool 26
- Hitachi Dry
- Hitachi Fan

These generated commands do not use learned raw IR data. They are useful when raw
learning is incomplete or unstable.

If these generated buttons work, the learned raw path can stay as a fallback. If
they do not work, the RS13T1 remote or the target AC may use a different Hitachi
protocol variant.

## ESPHome Native AC424 Port

ESPHome's current source also includes `hitachi_ac424`. It has now been ported
into `main.py` as a second generated protocol section.

AC424 constants from ESPHome:

```text
Carrier: 38000 Hz
Header mark: 3416 us
Header space: 1604 us
Bit mark: 463 us
One space: 1208 us
Zero space: 372 us
State length: 53 bytes / 424 bits
Bit order: LSB first per byte
Footer mark: 463 us
Gap: 100000 us
```

The web UI now includes:

- Generated Hitachi AC344
- Generated Hitachi AC424
- Learned Raw Codes
