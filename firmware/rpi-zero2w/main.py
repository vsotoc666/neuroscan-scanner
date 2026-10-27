import time
import os
import digitalio
import cv2
import logging
import sys
import gc
from pathlib import Path
from config import CONFIG, setup_logging
from display_manager import DisplayManager
from camera_manager import CameraManager
from input_manager import InputManager
from api_manager import APIManager

setup_logging()
logger = logging.getLogger("Main")

class OMRSystem:
    def __init__(self):
        self.running = True
        self.state = "MENU"
        self.menu_options = ["Escanear", "Notas", "Estadisticas", "Salir"]
        self.menu_index = 0
        self.contador = 0
        
        logger.info("Iniciando hardware...")
        self.ui = DisplayManager()
        self.input = InputManager()
        self.cam = CameraManager()
        self.api = APIManager() 
        
        self.sensor = digitalio.DigitalInOut(CONFIG['sensor_pin'])
        self.sensor.direction = digitalio.Direction.INPUT
        self.sensor.pull = digitalio.Pull.UP
        
        try:
            CONFIG['save_dir'].mkdir(parents=True, exist_ok=True)
            test_file = CONFIG['save_dir'] / '.speedtest'
            test_file.touch(); test_file.unlink()
        except Exception as e:
            logger.critical(f"ERROR DISCO: {e}")
            self.ui.update_scan_ui("ERROR DISCO", 0)
            sys.exit(1)
        
    def run(self):
        try:
            while self.running:
                if self.input.is_pressed('RESET'):
                    self.perform_soft_reset()
                    continue

                if self.state == "SCAN":
                    self.loop_scan()
                elif self.state == "MENU":
                    self.loop_menu()
                elif self.state == "STATS":
                    self.loop_stats()
                elif self.state == "NOTAS":
                    self.loop_notas()
                
                time.sleep(0.001)
        except Exception as e:
            logger.critical(f"Crash: {e}", exc_info=True)
        finally:
            self.cleanup()

    def _guardar_imagen_seguro(self, frame):
        try:
            # Procesamos (Crop + CLAHE)
            frame_procesado = self._procesar_estilo_escaneo_leve(frame)

            # --- SIN ROTACIÓN ---
            # La imagen se guarda tal cual sale del recorte (horizontal)

            ts = time.strftime("%Y%m%d_%H%M%S")
            ms = int((time.time() % 1) * 1000)
            fname = CONFIG['save_dir'] / f"scan_{ts}_{ms:03d}_proc.jpg"
            str_fname = str(fname)

            # Guardamos con alta calidad
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), CONFIG['jpeg_quality']]
            exito = cv2.imwrite(str_fname, frame_procesado, encode_param)
            
            # Limpieza obligatoria
            del frame_procesado
            del frame
            gc.collect()
            
            if not exito: return False, None
            if fname.exists() and fname.stat().st_size > 0: return True, fname
            return False, None

        except Exception as e:
            logger.error(f"Error Save: {e}")
            gc.collect()
            return False, None

    def loop_scan(self):
        if self.input.get_event() == "OK":
            self.cam.stop()
            self.state = "MENU"
            return

        papel_presente = not self.sensor.value
        
        if papel_presente:
            if not hasattr(self, 'tiempo_val') or self.tiempo_val is None:
                self.tiempo_val = time.monotonic()
            
            delta = time.monotonic() - self.tiempo_val
            
            if self.cam.cap and self.cam.cap.isOpened():
                try: self.cam.cap.grab()
                except: pass

            if delta >= CONFIG['validation_time']:
                ret, frame = self.cam.capture_frame()
                if ret:
                    self.ui.update_scan_ui("GUARDANDO...", self.contador)
                    guardado_ok, filepath = self._guardar_imagen_seguro(frame)
                    
                    if guardado_ok:
                        self.contador += 1
                        
                        # Mostramos que estamos subiendo
                        self.ui.update_scan_ui("SUBIENDO...", self.contador)
                        
                        # Encolar para API
                        self.api.encolar_examen(filepath)
                        
                        self.ui.update_scan_ui("EXITO", self.contador)
                        
                        del frame
                        gc.collect()
                        
                        while not self.sensor.value and self.running:
                            self.ui.update_scan_ui("RETIRE HOJA", self.contador)
                            if self.input.is_pressed('RESET'): self.perform_soft_reset(); return
                            if self.input.get_event() == "OK": self.cam.stop(); self.state = "MENU"; return
                            time.sleep(0.1)
                        self.tiempo_val = None
                    else:
                        self.ui.update_scan_ui("ERROR DISCO", self.contador)
                        time.sleep(2.0)
                        self.tiempo_val = None
                else:
                    self.ui.update_scan_ui("ERROR CAM", self.contador)
                    self.cam.connect()
            else:
                prog = int((delta / CONFIG['validation_time']) * 100)
                self.ui.update_scan_ui("VERIFICANDO", self.contador, prog)
        else:
            self.tiempo_val = None
            self.ui.update_scan_ui("ESPERANDO", self.contador)
        time.sleep(0.001)

    def loop_notas(self):
        if not hasattr(self, 'notas_scroll'): self.notas_scroll = 0
        if not hasattr(self, 'notas_selected'): self.notas_selected = 0
        if not hasattr(self, 'viewing_detail'): self.viewing_detail = False
        
        historial = self.api.get_history()
        
        # SUB-LOOP: Viendo detalle de una nota
        if self.viewing_detail:
            if self.notas_selected < len(historial):
                item = historial[self.notas_selected]
                self.ui.draw_exam_detail(item)
            
            if self.input.get_event() == "OK":
                self.viewing_detail = False
            return
        
        # LOOP: Lista de notas
        self.ui.draw_grades_list(historial, self.notas_scroll, self.notas_selected)
        
        event = self.input.get_event()
        if event == "UP":
            if self.notas_selected > 0:
                self.notas_selected -= 1
                if self.notas_selected < self.notas_scroll:
                    self.notas_scroll = self.notas_selected
        elif event == "DOWN":
            if self.notas_selected < len(historial) - 1:
                self.notas_selected += 1
                if self.notas_selected >= self.notas_scroll + 4:
                    self.notas_scroll += 1
        elif event == "OK":
            if len(historial) > 0:
                self.viewing_detail = True
            else:
                self.state = "MENU"
        # RESET (volver al menú) lo atiende run() -> perform_soft_reset()

        time.sleep(0.05)

    def perform_soft_reset(self):
        self.ui.draw_menu(["RESETEANDO..."], 0)
        self.cam.stop()
        time.sleep(0.5)
        self.state = "MENU"
        self.menu_index = 0
        self.notas_scroll = 0; self.notas_selected = 0; self.viewing_detail = False

    def loop_menu(self):
        self.ui.draw_menu(self.menu_options, self.menu_index)
        event = self.input.get_event()
        if event == "UP": self.menu_index = (self.menu_index - 1) % len(self.menu_options)
        elif event == "DOWN": self.menu_index = (self.menu_index + 1) % len(self.menu_options)
        elif event == "OK":
            opcion = self.menu_options[self.menu_index]
            if opcion == "Escanear":
                self.ui.update_scan_ui("INICIANDO...", self.contador)
                if self.cam.connect(): self.state = "SCAN"
                else: 
                    self.ui.update_scan_ui("ERROR CAM", 0)
                    time.sleep(1)
            elif opcion == "Notas":
                self.state = "NOTAS"
            elif opcion == "Estadisticas":
                self.state = "STATS"
            elif opcion == "Salir":
                self.running = False

    def loop_stats(self):
        try: num = sum(1 for _ in CONFIG['save_dir'].glob('*.jpg'))
        except: num = 0
        try: 
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = round(int(f.read())/1000, 1)
        except: temp = 0.0
        self.ui.draw_stats(num, temp)
        if self.input.get_event() == "OK": self.state = "MENU"
        time.sleep(0.1)

    def cleanup(self):
        self.cam.stop()
        self.api.stop()
        try:
            self.ui.draw.rectangle((0,0,128,128), fill=(0,0,0))
            self.ui.disp.image(self.ui.image)
        except: pass
        sys.exit(0)
    
    
    def _procesar_estilo_escaneo_leve(self, frame):
        """
        Procesamiento ligero: Grises -> Recorte (Crop) -> CLAHE.
        Sin rotación. Resolución base esperada: 1280x720.
        """
        gc.collect() # Limpieza preventiva de RAM

        try:
            # 1. Convertir a Escala de Grises
            # Reduce la memoria inmediatamente a 1/3 (aprox 0.9 MB en 720p)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 2. RECORTAR (CROP) - 100 píxeles a cada lado
            # Obtenemos dimensiones (Alto, Ancho)
            h, w = gray.shape
            
            pixels_corte = 100 # Cantidad a cortar de izquierda y derecha
            
            # Verificamos que la imagen sea suficientemente ancha para cortar
            if w > (pixels_corte * 2):
                # Slicing de Numpy: [InicioY:FinY, InicioX:FinX]
                # Cortamos desde pixel 100 hasta (Ancho - 100)
                cropped = gray[:, pixels_corte : w - pixels_corte]
            else:
                logger.warning("Imagen muy angosta para recortar, se usa completa.")
                cropped = gray

            del gray # Liberamos la imagen completa original

            # 3. Realce Leve (CLAHE)
            # Esto mejora el contraste de la ficha sin quemar la imagen
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(cropped)

            return enhanced

        except Exception as e:
            logger.error(f"Error procesamiento: {e}")
            gc.collect()
            # Si falla, devolvemos frame original convertido a gris si es posible
            if 'frame' in locals() and len(frame.shape) == 3:
                 return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return frame
        
    

if __name__ == "__main__":
    app = OMRSystem()
    app.run()