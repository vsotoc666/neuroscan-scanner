import digitalio
import time
from config import CONFIG

class InputManager:
    def __init__(self):
        self.buttons = {}
        for name, pin in CONFIG['buttons'].items():
            btn = digitalio.DigitalInOut(pin)
            btn.direction = digitalio.Direction.INPUT
            btn.pull = digitalio.Pull.UP
            self.buttons[name] = btn

    def is_pressed(self, btn_name):
        if btn_name in self.buttons:
            return not self.buttons[btn_name].value
        return False
            
    def get_event(self):
        for name in self.buttons:
            if self.is_pressed(name):
                time.sleep(0.15) # Debounce
                return name
        return None