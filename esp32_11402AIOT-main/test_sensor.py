from machine import ADC, Pin
from time import sleep

import dht


DHT11_PIN = 15
LIGHT_PIN = 39
POT_PIN = 34

dht11 = dht.DHT11(Pin(DHT11_PIN))
light = ADC(Pin(LIGHT_PIN))
pot = ADC(Pin(POT_PIN))

light.atten(ADC.ATTN_11DB)
pot.atten(ADC.ATTN_11DB)

while True:
    try:
        dht11.measure()
        temperature = dht11.temperature()
        humidity = dht11.humidity()
    except OSError as exc:
        temperature = None
        humidity = None
        print("DHT11 read failed:", exc)

    print("temperature:", temperature, "humidity:", humidity)
    print("light:", light.read(), "pot:", pot.read())
    sleep(2)
