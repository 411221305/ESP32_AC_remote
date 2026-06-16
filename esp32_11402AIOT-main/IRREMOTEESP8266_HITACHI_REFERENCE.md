# IRremoteESP8266 Hitachi Reference

Reference repo:

```text
https://github.com/crankyoldgit/IRremoteESP8266
```

Relevant files:

```text
src/ir_Hitachi.h
src/ir_Hitachi.cpp
```

Why it matters:

IRremoteESP8266 supports more Hitachi variants than the first ESPHome examples
we tried. The header lists support for:

- `HITACHI_AC1`
- `HITACHI_AC264`
- `HITACHI_AC296`
- `HITACHI_AC344`
- `HITACHI_AC424`
- `HITACHI_AC3`

The current MicroPython web UI already includes generated AC344 and AC424.
If the learned RS13T1 signal looks like AC1, AC264, or AC296, we should port
that variant next instead of continuing to tune AC344/AC424.

Approximate learned pulse-count guide:

```text
~212 pulses -> Hitachi AC1 / 104-bit candidate
~532 pulses -> Hitachi AC264 / 264-bit candidate
~596 pulses -> Hitachi AC296 / 296-bit candidate
~692 pulses -> Hitachi AC344 / 344-bit candidate
~852 pulses -> Hitachi AC424 / 424-bit candidate
```

The web UI now displays this protocol guess after Learn.
