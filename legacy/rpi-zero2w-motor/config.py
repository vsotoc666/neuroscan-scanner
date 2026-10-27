import board
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

BASE_DIR = Path(__file__).parent.absolute()
SCANS_DIR = BASE_DIR / 'scans'
LOG_FILE = BASE_DIR / 'system.log'

CONFIG = {
    'resolution': (1280, 720),
    'save_dir': SCANS_DIR,
    
    # --- MOTOR DE EXPULSIÓN ---
    'motor': {
        'in1_pin': board.D5,    # Pin Físico 29 (Cambia según tu conexión)
        'in2_pin': board.D6,    # Pin Físico 31
        'eject_time': 0.8       # Segundos que dura la expulsión
    },
    # --------------------------

    'validation_time': 0.6,
    'jpeg_quality': 85,
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