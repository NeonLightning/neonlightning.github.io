import pwnagotchi
import logging
import os
import io
import subprocess
import pwnagotchi.plugins as plugins
import RPi.GPIO as GPIO

class lcdhatcontrols(plugins.Plugin):
    __author__ = 'NeonLightning'
    __version__ = '0.0.1'
    __license__ = 'GPL3'
    __description__ = 'lcdhat controls'

    KEY_PRESS_PIN = 13
    KEY1_PIN = 21
    KEY2_PIN = 20
    KEY3_PIN = 16

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.KEY_PRESS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.KEY1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.KEY2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.KEY3_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    @staticmethod
    def get_input(pin):
        return not GPIO.input(pin)

    def on_loaded(self):
        self.loaded = True
        while self.loaded:
            self._buttons_()

    def on_unloaded(self):
        logging.info("[Controls] unloaded")
        self.loaded = False

    def _buttons_(self):
        if self.get_input(self.KEY_PRESS_PIN) != 0:
            if self.get_input(self.KEY3_PIN) != 0:
                logging.info(f"resetting service(auto)")
                subprocess.run(["sudo", "touch", "/root/.pwnagotchi-auto"])
                subprocess.run(["sudo", "systemctl", "restart", "pwnagotchi.service"])
            if self.get_input(self.KEY1_PIN) != 0:
                logging.info(f"reboot")
                subprocess.run(['sudo', 'reboot'])
            if self.get_input(self.KEY2_PIN) != 0:
                logging.info(f"shutdown")
                subprocess.run(['sudo', 'shutdown', '-h', 'now'])
            logging.info(f"resend telegram qrcodes")
            subprocess.run(['sudo', 'rm', '-rf', '/home/pi/qrcodes', '/home/pi/.qrlist'])
