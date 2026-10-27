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
        """Busca cámaras disponibles en el sistema"""
        devices = glob.glob("/dev/video*")
        device_indexes = []
        for dev in devices:
            try:
                idx = int(dev.replace("/dev/video", ""))
                device_indexes.append(idx)
            except: pass
        device_indexes.sort()
        
        # Probar índices encontrados
        for idx in device_indexes:
            logger.info(f"Probando índice {idx}...")
            # IMPORTANTE: backend V4L2
            temp_cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
            temp_cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            
            if temp_cap.isOpened():
                ret, _ = temp_cap.read()
                temp_cap.release()
                if ret:
                    return idx
        return None

    def connect(self):
        try:
            if self.cap: self.cap.release()
            
            idx = self._find_camera_index()
            if idx is None:
                logger.error("No se detectó cámara USB.")
                return False
                
            self.cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
            # Configuración para velocidad en USB 2.0
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG['resolution'][0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG['resolution'][1])
            
            if not self.cap.isOpened():
                raise IOError(f"No abre video{idx}")
            
            # Warm-up (Estabilizar luz)
            for _ in range(5): self.cap.read()
                
            self.current_index = idx
            logger.info(f"Cámara conectada en índice {idx}")
            return True

        except Exception as e:
            logger.error(f"Error conexión cámara: {e}")
            return False

    def capture_frame(self):
        if not self.cap or not self.cap.isOpened():
            logger.warning("Cámara caída. Reconectando...")
            if not self.connect(): return False, None
        
        try:
            # LIMPIEZA AGRESIVA DE BUFFER (Anti-Ghosting)
            # Descarta 4 frames viejos para obtener el 'ahora' real
            for _ in range(4):
                self.cap.grab()
            
            ret, frame = self.cap.read()
            
            if not ret:
                logger.warning("Frame vacío. Reiniciando...")
                self.connect()
                return False, None
                
            return True, frame

        except Exception as e:
            logger.error(f"Error captura: {e}")
            self.release()
            return False, None

    def stop(self):
        self.release()

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None