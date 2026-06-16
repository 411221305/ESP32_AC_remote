from machine import Pin
from time import sleep


LED_BUILTIN = 2
LED_RED = 16
LED_YELLOW = 12
LED_GREEN = 13
BUTTON_A = 5

led_builtin = Pin(LED_BUILTIN, Pin.OUT)
led_red = Pin(LED_RED, Pin.OUT)
led_yellow = Pin(LED_YELLOW, Pin.OUT)
led_green = Pin(LED_GREEN, Pin.OUT)
button_a = Pin(BUTTON_A, Pin.IN, Pin.PULL_UP)

leds = [led_builtin, led_red, led_yellow, led_green]

while True:
    if button_a.value() == 0:
        led_red.value(1)
        sleep(0.05)
        continue

    for led in leds:
        led.value(1)
        sleep(0.2)
        led.value(0)
