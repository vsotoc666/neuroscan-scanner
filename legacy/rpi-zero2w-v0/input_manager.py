import digitalio
import time
from config import CONFIG

class InputManager:
    def __init__(self):
        self.buttons = {}
        
        # Inicializar botones con Pull-Up
        for name, pin in CONFIG['buttons'].items():
            btn = digitalio.DigitalInOut(pin)
            btn.direction = digitalio.Direction.INPUT
            btn.pull = digitalio.Pull.UP
            self.buttons[name] = btn

    def is_pressed(self, btn_name):
        """True si el botón está presionado (Lógica inversa por Pull-Up)"""
        if btn_name in self.buttons:
            return not self.buttons[btn_name].value
        return False
            
    def get_event(self):
        """
        Retorna el nombre del botón presionado ('UP', 'DOWN', 'OK') o None.
        Incluye un pequeño 'debounce' para evitar dobles pulsaciones.
        """
        for name in self.buttons:
            if self.is_pressed(name):
                time.sleep(0.15) # Debounce simple
                return name
        return None