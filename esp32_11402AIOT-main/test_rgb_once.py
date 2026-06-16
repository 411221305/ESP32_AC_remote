from machine import Pin
from neopixel import NeoPixel
from time import sleep


LED_RED = 16
LED_YELLOW = 12
LED_GREEN = 13
NEOPIXEL = 26
NUM_PIXELS = 3
BLINK_COUNT = 10
BLINK_SECONDS = 1

status_leds = [
    Pin(LED_RED, Pin.OUT),
    Pin(LED_YELLOW, Pin.OUT),
    Pin(LED_GREEN, Pin.OUT),
]
pixels = NeoPixel(Pin(NEOPIXEL), NUM_PIXELS)

for led in status_leds:
    led.value(0)

for _ in range(BLINK_COUNT):
    pixels[0] = (64, 0, 0)
    pixels[1] = (0, 64, 0)
    pixels[2] = (0, 0, 64)
    pixels.write()
    sleep(BLINK_SECONDS)

    for index in range(NUM_PIXELS):
        pixels[index] = (0, 0, 0)
    pixels.write()
    sleep(BLINK_SECONDS)

for index in range(NUM_PIXELS):
    pixels[index] = (0, 0, 0)
pixels.write()
