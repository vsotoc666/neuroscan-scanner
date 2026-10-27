import time
import board
import digitalio
import subprocess
import logging
import sys
from config import CONFIG, BASE_DIR

# Rutas absolutas: funciona aunque se ejecute desde otra carpeta
logging.basicConfig(filename=str(BASE_DIR / 'launcher.log'), level=logging.INFO)

def wait_for_start():
    pin_ok = CONFIG['buttons']['OK']
    btn = digitalio.DigitalInOut(pin_ok)
    btn.direction = digitalio.Direction.INPUT
    btn.pull = digitalio.Pull.UP
    
    logging.info("Lanzador esperando OK...")
    while btn.value:
        time.sleep(0.1)
    
    logging.info("Arrancando...")
    btn.deinit()
    
    subprocess.call([sys.executable, str(BASE_DIR / "main.py")], cwd=str(BASE_DIR))

if __name__ == "__main__":
    while True:
        try:
            wait_for_start()
            time.sleep(2)
        except Exception as e:
            logging.error(f"Error lanzador: {e}")
            time.sleep(5)