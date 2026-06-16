from machine import I2C, Pin
from time import sleep

from lib.oled_i2c import OLED12864_I2C
from lib.zh_ndhu_font import HEIGHT, draw_text, text_width


OLED_SDA = 21
OLED_SCL = 22
MESSAGE = "國立東華大學"


i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400000)
devices = i2c.scan()

if not devices:
    raise RuntimeError("No I2C OLED found on GPIO21/GPIO22")

addr = 0x3C if 0x3C in devices else devices[0]
oled = OLED12864_I2C(i2c, addr=addr)

oled.fill(0)

message_width = text_width(MESSAGE)
x = (oled.width - message_width) // 2
y = (oled.height - HEIGHT) // 2

draw_text(oled, MESSAGE, x, y)
oled.show()

print("OLED devices:", [hex(device) for device in devices])
print("Displayed:", MESSAGE)

sleep(10)
