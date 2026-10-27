import time
import board
import digitalio
import subprocess
import logging
import sys  # <--- IMPORTANTE: Necesario para saber qué Python usar
from config import CONFIG

# Logs en archivo para debug
logging.basicConfig(filename='launcher.log', level=logging.INFO)

def wait_for_start():
    pin_ok = CONFIG['buttons']['OK']
    
    btn = digitalio.DigitalInOut(pin_ok)
    btn.direction = digitalio.Direction.INPUT
    btn.pull = digitalio.Pull.UP
    
    logging.info("Lanzador listo. Esperando botón OK...")
    
    # Esperar pulsación (False = presionado)
    while btn.value:
        time.sleep(0.1)
    
    logging.info("Botón presionado! Lanzando sistema principal...")
    
    # Liberar pin para que main.py lo use
    btn.deinit()
    
    # --- CORRECCIÓN AQUÍ ---
    # Usamos sys.executable en lugar de "python".
    # Esto asegura que se use /home/cubesat/proyecto/venv/bin/python
    interpreter = sys.executable
    script_path = "main.py" # Asumimos que está en la misma carpeta
    
    subprocess.call([interpreter, script_path])

if __name__ == "__main__":
    while True:
        try:
            wait_for_start()
            time.sleep(2)
        except Exception as e:
            logging.error(f"Error en lanzador: {e}")
            time.sleep(5)