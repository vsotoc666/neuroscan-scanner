import os
import board
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

BASE_DIR = Path(__file__).parent.absolute()
SCANS_DIR = BASE_DIR / 'scans'
LOG_FILE = BASE_DIR / 'system.log'

CONFIG = {
    # Credenciales del servidor de IA: se leen de variables de entorno
    # (ver .env.example). Nunca escribir la API key directamente aquí.
    'api': {
        'url': os.environ.get('OMR_API_URL', "https://feriafiee.rubbercorp.org.pe/corregir-examen/"),
        'key': os.environ.get('OMR_API_KEY', ""),
        'timeout': int(os.environ.get('OMR_API_TIMEOUT', 20))
    },

    # --- MEJORA DE CALIDAD ---
    # Subimos a Full HD (1920x1080) para que la IA vea bien las marcas.
    'resolution': (1920, 1080), 
    # Subimos calidad JPG para evitar artefactos de compresión.
    'jpeg_quality': 100,
    # -------------------------

    'save_dir': SCANS_DIR,
    'validation_time': 0.6,
    'sensor_pin': board.D16,
    
    'buttons': {
        'UP': board.D23,
        'DOWN': board.D22,
        'OK': board.D27,
        'RESET': board.D17
    },

    'screen': {
        'width': 128,
        'height': 128,
        'baudrate': 32000000,
        'x_offset': 2,
        'y_offset': 3
    }
}

def setup_logging():
    handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)