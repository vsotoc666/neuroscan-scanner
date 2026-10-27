import board
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Rutas Absolutas
BASE_DIR = Path(__file__).parent.absolute()
SCANS_DIR = BASE_DIR / 'scans'
LOG_FILE = BASE_DIR / 'system.log'

CONFIG = {
    'resolution': (1280, 720),
    'save_dir': SCANS_DIR,
    'validation_time': 0.6,
    'jpeg_quality': 85,
    
    # --- PIN SENSOR (Pin Físico 36) ---
    'sensor_pin': board.PB3,
    
    # --- PINES BOTONES ---
    'buttons': {
        'UP':    board.PL9,  # Pin Físico 16
        'DOWN':  board.PH7,  # Pin Físico 15
        'OK':    board.PH4,  # Pin Físico 13
        'RESET': board.PH5   # Pin Físico 11
    },

    # --- MOTOR (Pines Físicos 29 y 31) ---
    'motor': {
        'in1_pin': board.PB4,
        'in2_pin': board.PB5,
        'eject_time': 0.8
    },

    # --- PANTALLA SPI (Pines 19, 23, 24 + 18, 22) ---
    # Nota: Los pines SPI principales (MOSI, CLK) se detectan solos al iniciar board.SPI()
    'screen': {
        'width': 128,
        'height': 128,
        'baudrate': 32000000,
        'x_offset': 2,
        'y_offset': 3,
        'cs_pin': board.PD0,  # Pin Físico 24 (SPI1_CS0)
        'dc_pin': board.PC4,  # Pin Físico 18
        'rst_pin': board.PH6  # Pin Físico 22
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