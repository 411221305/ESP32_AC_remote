from machine import PWM, Pin
from time import sleep


class Buzzer:
    def __init__(self, pin):
        self.pin = Pin(pin, Pin.OUT)
        self.pwm = None

    def tone(self, frequency, duration=0.2, duty=512):
        self.pwm = PWM(self.pin, freq=frequency, duty=duty)
        sleep(duration)
        self.off()

    def off(self):
        if self.pwm is not None:
            self.pwm.deinit()
            self.pwm = None
