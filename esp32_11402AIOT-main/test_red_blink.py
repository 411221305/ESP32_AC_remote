from machine import Pin
from time import sleep


LED_RED = 16
LED_YELLOW = 12
LED_GREEN = 13

leds = [
    Pin(LED_RED, Pin.OUT),
    Pin(LED_YELLOW, Pin.OUT),
    Pin(LED_GREEN, Pin.OUT),
]

for _ in range(10):
    for led in leds:
        led.value(1)
    sleep(1)
    for led in leds:
        led.value(0)
    sleep(1)

for led in leds:
    led.value(0)
