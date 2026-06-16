from machine import I2C, Pin

from lib.oled_i2c import OLED12864_I2C
from ir import KEY_BY_RAW, RECV_PIN, decode_nec, read_ir


OLED_SDA = 21
OLED_SCL = 22


def init_oled():
    i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400000)
    devices = i2c.scan()
    print("I2C scan:", [hex(d) for d in devices])

    if not devices:
        raise RuntimeError("No I2C device on SDA={} SCL={}".format(OLED_SDA, OLED_SCL))

    addr = 0x3C if 0x3C in devices else devices[0]
    return OLED12864_I2C(i2c, addr=addr)


def show_idle(oled):
    oled.fill(0)
    oled.text("IR -> OLED", 0, 0)
    oled.text("GPIO {}".format(RECV_PIN), 0, 16)
    oled.text("Press a key...", 0, 40)
    oled.show()


def show_key(oled, key, raw, addr, cmd, count):
    oled.fill(0)
    oled.text("Key:  {}".format(key), 0, 0)
    oled.text("Raw:", 0, 16)
    oled.text("0x{:08X}".format(raw), 0, 28)
    oled.text("a={:02X} c={:02X}".format(addr, cmd), 0, 44)
    oled.text("#{}".format(count), 96, 0)
    oled.show()


def main():
    oled = init_oled()
    print("OLED ready. IR on GPIO {}".format(RECV_PIN))
    show_idle(oled)

    count = 0
    while True:
        pulses = read_ir()
        if not pulses:
            continue

        result = decode_nec(pulses)
        if result == "repeat" or result is None:
            continue
        if not result["valid"]:
            continue

        count += 1
        key = result["key"]
        raw = result["raw"]
        print("key={} raw=0x{:08X} count={}".format(key, raw, count))
        show_key(oled, key, raw, result["address"], result["command"], count)


main()
