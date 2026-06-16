import bluetooth
import time
from machine import I2C, Pin
from neopixel import NeoPixel

from lib.oled_i2c import OLED12864_I2C


DEVICE_NAME = "ESP32-AIOT"
LED_BUILTIN = 2
NEOPIXEL = 26
NUM_PIXELS = 3
OLED_SDA = 21
OLED_SCL = 22
OLED_LINE_CHARS = 16
OLED_MAX_LINES = 5

IRQ_CENTRAL_CONNECT = 1
IRQ_CENTRAL_DISCONNECT = 2
IRQ_GATTS_WRITE = 3

FLAG_READ = 0x0002
FLAG_WRITE = 0x0008
FLAG_WRITE_NO_RESPONSE = 0x0004
FLAG_NOTIFY = 0x0010

UART_SERVICE_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
UART_TX_UUID = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
UART_RX_UUID = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")

UART_TX = (UART_TX_UUID, FLAG_READ | FLAG_NOTIFY)
UART_RX = (UART_RX_UUID, FLAG_WRITE | FLAG_WRITE_NO_RESPONSE)
UART_SERVICE = (UART_SERVICE_UUID, (UART_TX, UART_RX))


def turn_off_rgb():
    pixels = NeoPixel(Pin(NEOPIXEL), NUM_PIXELS)
    for index in range(NUM_PIXELS):
        pixels[index] = (0, 0, 0)
    pixels.write()


def init_oled():
    i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400000)
    devices = i2c.scan()
    print("OLED devices:", [hex(device) for device in devices])

    if not devices:
        raise RuntimeError("No I2C OLED found on GPIO21/GPIO22")

    addr = 0x3C if 0x3C in devices else devices[0]
    return OLED12864_I2C(i2c, addr=addr)


def oled_safe_text(text):
    chars = []
    for char in text:
        code = ord(char)
        if 32 <= code <= 126:
            chars.append(char)
        else:
            chars.append("?")
    return "".join(chars)


def wrap_oled_text(text):
    text = oled_safe_text(text).replace("\r", " ")
    lines = []

    for part in text.split("\n"):
        if not part:
            lines.append("")
            continue

        while part:
            lines.append(part[:OLED_LINE_CHARS])
            part = part[OLED_LINE_CHARS:]

    if not lines:
        lines = ["<empty>"]

    if len(lines) > OLED_MAX_LINES:
        lines = lines[:OLED_MAX_LINES]
        if len(lines[-1]) >= 2:
            lines[-1] = lines[-1][:-2] + ".."

    return lines


def show_status(oled, status, detail=None):
    oled.fill(0)
    oled.text("BLE -> OLED", 0, 0)
    oled.text(status[:OLED_LINE_CHARS], 0, 16)
    if detail:
        oled.text(detail[:OLED_LINE_CHARS], 0, 32)
    oled.show()


def show_received(oled, text):
    oled.fill(0)
    oled.text("BLE RX:", 0, 0)
    for index, line in enumerate(wrap_oled_text(text)):
        oled.text(line, 0, 16 + index * 10)
    oled.show()


def advertising_payload(name):
    payload = bytearray()

    def append(adv_type, value):
        payload.extend((len(value) + 1, adv_type))
        payload.extend(value)

    append(0x01, b"\x06")  # General discoverable, BR/EDR not supported.
    append(0x09, name.encode())
    return payload


class BLEUartEcho:
    def __init__(self, name, oled):
        self.oled = oled
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self.on_irq)

        ((self.tx_handle, self.rx_handle),) = self.ble.gatts_register_services(
            (UART_SERVICE,)
        )
        self.connections = set()
        self.payload = advertising_payload(name)
        self.led = Pin(LED_BUILTIN, Pin.OUT)
        self.led.value(0)
        self.pending_oled_text = None
        show_status(self.oled, "Advertising", name)
        self.advertise()

    def advertise(self):
        self.ble.gap_advertise(100_000, adv_data=self.payload)
        print("BLE advertising as '{}'".format(DEVICE_NAME))
        print("Use nRF Connect / LightBlue to scan and connect.")
        print("Write text to RX; ESP32 will notify back on TX.")

    def on_irq(self, event, data):
        if event == IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self.connections.add(conn_handle)
            self.led.value(1)
            self.pending_oled_text = "[connected]"
            print("BLE connected:", conn_handle)

        elif event == IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self.connections.discard(conn_handle)
            self.led.value(0)
            self.pending_oled_text = "[advertising]"
            print("BLE disconnected:", conn_handle)
            self.advertise()

        elif event == IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            if value_handle == self.rx_handle:
                received = self.ble.gatts_read(self.rx_handle)
                print("RX:", received)
                try:
                    text = received.decode()
                except UnicodeError:
                    text = repr(received)
                self.pending_oled_text = text
                self.notify("echo: " + text)

    def notify(self, message):
        data = message.encode()
        for conn_handle in self.connections:
            self.ble.gatts_notify(conn_handle, self.tx_handle, data)
        print("TX:", message)

    def update_oled(self):
        if self.pending_oled_text is None:
            return

        text = self.pending_oled_text
        self.pending_oled_text = None

        if text == "[connected]":
            show_status(self.oled, "Connected", "Send text")
        elif text == "[advertising]":
            show_status(self.oled, "Advertising", DEVICE_NAME)
        else:
            show_received(self.oled, text)


def main():
    turn_off_rgb()
    oled = init_oled()
    ble_uart = BLEUartEcho(DEVICE_NAME, oled)
    while True:
        ble_uart.update_oled()
        time.sleep(0.1)


main()
