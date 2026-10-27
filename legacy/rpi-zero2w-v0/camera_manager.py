import cv2
import time
import glob
import logging
from config import CONFIG

logger = logging.getLogger("Camera")

class CameraManager:
    def __init__(self):
        self.cap = None
        # No conectamos en el __init__ para evitar bloqueos al arranque.
        # Se conectará automáticamente en el primer intento de captura.
        self.current_index = -1

    def _find_camera_index(self):
        """
        Busca automáticamente el índice correcto de la cámara (0, 1, 2...).
        Retorna el índice o None si no encuentra nada.
        """
        # Método 1: Buscar dispositivos en /dev/video*
        devices = glob.glob("/dev/video*")
        device_indexes = []
        for dev in devices:
            try:
                # Extraer el número de /dev/videoX
                idx = int(dev.replace("/dev/video", ""))
                device_indexes.append(idx)
            except:
                pass
        
        device_indexes.sort()
        
        # Método 2: Probar abrir cada índice encontrado
        for idx in device_indexes:
            logger.info(f"Probando cámara en índice {idx}...")
            temp_cap = cv2.VideoCapture(idx)
            if temp_cap.isOpened():
                # Leer un frame para asegurar que es una cámara real y no un loopback
                ret, _ = temp_cap.read()
                temp_cap.release()
                if ret:
                    logger.info(f"¡Cámara encontrada en índice {idx}!")
                    return idx
        
        return None

    def connect(self):
        """Intenta conectar buscando la cámara dinámicamente"""
        try:
            if self.cap:
                self.cap.release()
            
            # Paso 1: Encontrar dónde está la cámara
            new_index = self._find_camera_index()
            
            if new_index is None:
                logger.error("No se detectó ninguna cámara USB conectada.")
                return False
                
            # Paso 2: Conectar
            self.cap = cv2.VideoCapture(new_index)
            
            # Paso 3: Configurar
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG['resolution'][0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG['resolution'][1])
            
            # Paso 4: Verificar stream
            if not self.cap.isOpened():
                raise IOError(f"No se pudo abrir video{new_index}")
            
            # Limpiar buffer inicial (Warm-up)
            # Leemos 5 frames para que el sensor ajuste luz y balance de blancos
            for _ in range(5):
                self.cap.read()
                
            self.current_index = new_index
            logger.info(f"Cámara conectada y lista en /dev/video{new_index}.")
            return True

        except Exception as e:
            logger.error(f"Error crítico al conectar cámara: {e}")
            return False

    def capture_frame(self):
        """
        Captura frame con reconexión automática.
        Retorna: (exito, frame)
        """
        # Si la cámara no existe o está cerrada, intentar conectar
        if not self.cap or not self.cap.isOpened():
            logger.warning("Cámara no disponible, intentando conectar...")
            if not self.connect():
                return False, None
        
        try:
            # Limpiar buffer (leer frame viejo para descartarlo)
            self.cap.grab()
            
            # Leer frame nuevo
            ret, frame = self.cap.read()
            
            if not ret:
                # Si falla la lectura, puede que se haya desconectado o cambiado de ID.
                # Lanzamos advertencia y forzamos reconexión completa.
                logger.warning("Fallo de lectura (frame vacío). Reiniciando cámara...")
                self.connect()
                return False, None
                
            return True, frame

        except Exception as e:
            logger.error(f"Error durante captura: {e}")
            # Liberar para permitir reconexión limpia en el siguiente intento
            self.release()
            return False, None

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None
            logger.info("Recursos de cámara liberados.")