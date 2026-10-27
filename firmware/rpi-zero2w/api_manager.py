import requests
import logging
import threading
import queue
import time
import os
from config import CONFIG

logger = logging.getLogger("API")

class APIManager:
    def __init__(self):
        self.url = CONFIG['api']['url']
        self.headers = {"X-API-Key": CONFIG['api']['key']}
        self.timeout = CONFIG['api']['timeout']
        if not CONFIG['api']['key']:
            logger.warning("OMR_API_KEY no definida: el servidor rechazará las fichas (ver .env.example)")

        self.queue = queue.Queue()
        self.history = [] 
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def encolar_examen(self, image_path):
        logger.info(f"Encolando archivo: {image_path}")
        self.queue.put(image_path)

    def get_history(self):
        return list(reversed(self.history))

    def _worker(self):
        logger.info("Worker API iniciado.")
        while self.running:
            try:
                image_path = self.queue.get(timeout=1)
            except queue.Empty:
                continue

            resultado = self._upload_sync(image_path)
            
            if resultado:
                self.history.append(resultado)
                if len(self.history) > 50:
                    self.history.pop(0)
            
            self.queue.task_done()

    @staticmethod
    def _id_desde_archivo(image_path):
        # Nombre: scan_AAAAMMDD_HHMMSS_mmm_proc.jpg -> se usa la hora (HHMMSS)
        partes = os.path.basename(str(image_path)).split('_')
        return partes[2] if len(partes) > 2 else '??'

    def _upload_sync(self, image_path):
        identificador = self._id_desde_archivo(image_path)
        try:
            if not os.path.exists(image_path):
                return {'status': 'FAIL', 'id': identificador, 'error': 'No File'}

            with open(image_path, 'rb') as f:
                response = requests.post(
                    self.url, 
                    files={'file': f}, 
                    headers=self.headers, 
                    timeout=self.timeout
                )

            if response.status_code == 200:
                data = response.json()
                # --- PROCESAMIENTO DEL JSON DE LA IA ---
                # Estructura recibida:
                # {'score': 1.43, 'stats': {...}, 'details': [...], 'process_time_seconds': 0.0599}
                
                nota = data.get('score', 0.0)
                tiempo = data.get('process_time_seconds', 0.0)
                stats = data.get('stats', {})

                registro = {
                    'status': 'OK',
                    'id': identificador,
                    'nota': nota,
                    'tiempo': tiempo,
                    'correctas': stats.get('correct', 0),
                    'incorrectas': stats.get('incorrect', 0),
                    'total': stats.get('total', 0)
                }
                
                logger.info(f"API OK: Nota {nota} ({tiempo}s)")
                return registro
            
            else:
                logger.error(f"API Error {response.status_code}")
                return {'status': 'ERR', 'id': identificador, 'error': f"HTTP {response.status_code}"}

        except Exception as e:
            logger.error(f"Excepción API: {e}")
            return {'status': 'FAIL', 'id': identificador, 'error': 'Error Red'}

    def stop(self):
        self.running = False
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)