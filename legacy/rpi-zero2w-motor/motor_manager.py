import time
import digitalio
import logging
from config import CONFIG

logger = logging.getLogger("Motor")

class MotorManager:
    def __init__(self):
        try:
            # Configurar pines del driver L298N
            self.in1 = digitalio.DigitalInOut(CONFIG['motor']['in1_pin'])
            self.in1.direction = digitalio.Direction.OUTPUT
            
            self.in2 = digitalio.DigitalInOut(CONFIG['motor']['in2_pin'])
            self.in2.direction = digitalio.Direction.OUTPUT
            
            self.stop() # Asegurar que arranque apagado
            logger.info("Motor inicializado.")
            
        except Exception as e:
            logger.error(f"Error al iniciar motor: {e}")

    def eject(self):
        """Activa el motor para expulsar la hoja"""
        try:
            logger.info("Expulsando ficha...")
            
            # Configurar giro (Ajusta True/False si gira al revés)
            self.in1.value = True
            self.in2.value = False
            
            # Esperar el tiempo configurado
            time.sleep(CONFIG['motor']['eject_time'])
            
            self.stop()
            
        except Exception as e:
            logger.error(f"Fallo en motor: {e}")
            self.stop()

    def stop(self):
        """Freno de seguridad"""
        self.in1.value = False
        self.in2.value = False