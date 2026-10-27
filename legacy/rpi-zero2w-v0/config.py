import board
import logging

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
CONFIG = {
    # Configuración de Cámara
    'resolution': (1280, 720),      # Resolución de captura
    'save_dir': 'scans',            # Carpeta para guardar las fotos
    
    # Configuración de Lógica
    'validation_time': 0.5,         # Segundos que el papel debe estar quieto
    'sensor_pin': board.D16,        # Pin del sensor TCRT5000
    
    # NUEVO: Configuración de Botones (Menú)
    # Usamos resistencia Pull-Up interna (conectar botón entre Pin y GND)
    'buttons': {
        'UP':   board.D23,          # Pin Físico 16
        'DOWN': board.D22,          # Pin Físico 15
        'OK':   board.D27,
	'RESET': board.D17           # Pin Físico 13
    },

    # Configuración de Pantalla SPI (ST7735S)
    'screen': {
        'width': 128,
        'height': 128,
        'baudrate': 24000000,       # 24 MHz
        'x_offset': 2,              # Ajuste horizontal (varía según fabricante)
        'y_offset': 3               # Ajuste vertical
    }
}

# ==========================================
# CONFIGURACIÓN DE LOGGING
# ==========================================
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )