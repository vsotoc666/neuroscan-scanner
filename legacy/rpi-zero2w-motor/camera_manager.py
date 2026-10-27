import cv2
import time
import glob
import logging
from config import CONFIG

logger = logging.getLogger("Camera")

class CameraManager:
    def __init__(self):
        self.cap = None
        self.current_index = -1

    def _find_camera_index(self):
        # Método 1: Buscar dispositivos en /dev/video*
        devices = glob.glob("/dev/video*")
        device_indexes = []
        for dev in devices:
            try:
                idx = int(dev.replace("/dev/video", ""))
                device_indexes.append(idx)
            except:
                pass
        device_indexes.sort()
        
        # Método 2: Probar abrir cada índice encontrado
        for idx in device_indexes:
            logger.info(f"Probando cámara en índice {idx}...")
            # IMPORTANTE: cv2.CAP_V4L2 es necesario para RPi moderno
            temp_cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
            
            # Configurar MJPG para velocidad en USB 2.0
            temp_cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            
            if temp_cap.isOpened():
                ret, _ = temp_cap.read()
                temp_cap.release()
                if ret:
                    logger.info(f"Cámara encontrada en índice {idx}!")
                    return idx
        return None

    def connect(self):
        try:
            if self.cap:
                self.cap.release()
            
            new_index = self._find_camera_index()
            
            if new_index is None:
                logger.error("No se detectó ninguna cámara USB.")
                return False
                
            self.cap = cv2.VideoCapture(new_index, cv2.CAP_V4L2)
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG['resolution'][0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG['resolution'][1])
            
            if not self.cap.isOpened():
                raise IOError(f"No se pudo abrir video{new_index}")
            
            # Warm-up
            for _ in range(5):
                self.cap.read()
                
            self.current_index = new_index
            logger.info(f"Cámara conectada en /dev/video{new_index}.")
            return True

        except Exception as e:
            logger.error(f"Error crítico al conectar cámara: {e}")
            return False

    def capture_frame(self):
        if not self.cap or not self.cap.isOpened():
            logger.warning("Cámara desconectada, intentando reconectar...")
            if not self.connect():
                return False, None
        
        try:
            # Limpieza agresiva de buffer (Anti-Ghosting)
            for _ in range(5):
                self.cap.grab() 
            
            ret, frame = self.cap.read()
            
            if not ret:
                logger.warning("Fallo de lectura. Reiniciando cámara...")
                self.connect()
                return False, None
                
            return True, frame

        except Exception as e:
            logger.error(f"Error durante captura: {e}")
            self.release()
            return False, None

    def stop(self):
        """Alias para release, para compatibilidad con main.py"""
        self.release()

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None
            logger.info("Recursos de cámara liberados.")