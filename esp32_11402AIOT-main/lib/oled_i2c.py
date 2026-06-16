from framebuf import FrameBuffer, MONO_VLSB
from time import sleep_ms


class OLED12864_I2C(FrameBuffer):
    """Small SSD1306 128x64 I2C OLED driver."""

    def __init__(self, i2c, addr=0x3C, width=128, height=64):
        self.i2c = i2c
        self.addr = addr
        self.width = width
        self.height = height
        self.pages = height // 8
        self.buffer = bytearray(width * self.pages)
        super().__init__(self.buffer, width, height, MONO_VLSB)
        self.init_display()

    def write_cmd(self, cmd):
        self.i2c.writeto(self.addr, bytes((0x80, cmd)))

    def write_data(self, buf):
        self.i2c.writeto(self.addr, b"\x40" + buf)

    def init_display(self):
        for cmd in (
            0xAE,  # display off
            0xD5, 0x80,
            0xA8, self.height - 1,
            0xD3, 0x00,
            0x40,
            0x8D, 0x14,  # SSD1306 charge pump on
            0x20, 0x00,  # horizontal addressing mode
            0xA1,
            0xC8,
            0xDA, 0x12,
            0x81, 0xCF,
            0xD9, 0xF1,
            0xDB, 0x40,
            0xA4,
            0xA6,
            0xAF,  # display on
        ):
            self.write_cmd(cmd)
        self.fill(0)
        self.show()
        sleep_ms(50)

    def poweroff(self):
        self.write_cmd(0xAE)

    def poweron(self):
        self.write_cmd(0xAF)

    def contrast(self, contrast):
        self.write_cmd(0x81)
        self.write_cmd(contrast & 0xFF)

    def show(self):
        self.write_cmd(0x21)
        self.write_cmd(0)
        self.write_cmd(self.width - 1)
        self.write_cmd(0x22)
        self.write_cmd(0)
        self.write_cmd(self.pages - 1)

        for start in range(0, len(self.buffer), 32):
            self.write_data(self.buffer[start:start + 32])
