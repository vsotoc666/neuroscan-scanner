import time
import os
import digitalio
import cv2
import logging
import sys
from pathlib import Path
from config import CONFIG, setup_logging
from display_manager import DisplayManager
from camera_manager import CameraManager
from input_manager import InputManager
from motor_manager import MotorManager

setup_logging()
logger = logging.getLogger("Main")

class OMRSystem:
    def __init__(self):
        self.running = True
        self.state = "MENU"
        self.menu_options = ["Escanear", "Estadisticas", "Salir"]
        self.menu_index = 0
        self.contador = 0
        
        self.ui = DisplayManager()
        self.input = InputManager()
        self.cam = CameraManager()
        self.motor = MotorManager()
        
        self.sensor = digitalio.DigitalInOut(CONFIG['sensor_pin'])
        self.sensor.direction = digitalio.Direction.INPUT
        self.sensor.pull = digitalio.Pull.UP
        
        # Verificación de disco al inicio
        try:
            CONFIG['save_dir'].mkdir(parents=True, exist_ok=True)
            test_file = CONFIG['save_dir'] / '.speedtest'
            test_file.touch()
            test_file.unlink()
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
                
                time.sleep(0.001) 
                
        except Exception as e:
            logger.critical(f"Crash: {e}", exc_info=True)
        finally:
            self.cleanup()

    def _guardar_imagen_seguro(self, frame):
        try:
            ts = time.strftime("%Y%m%d_%H%M%S")
            ms = int((time.time() % 1) * 1000)
            fname = CONFIG['save_dir'] / f"scan_{ts}_{ms:03d}.jpg"
            str_fname = str(fname)

            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), CONFIG['jpeg_quality']]
            exito_escritura = cv2.imwrite(str_fname, frame, encode_param)
            
            if not exito_escritura: return False
            if fname.exists() and fname.stat().st_size > 0: return True
            return False

        except Exception as e:
            logger.error(f"Error Save: {e}")
            return False

    def loop_scan(self):
        event = self.input.get_event()
        if event == "OK":
            self.cam.stop() # Detiene recursos si es necesario
            self.state = "MENU"
            return

        papel_presente = not self.sensor.value
        
        if papel_presente:
            if not hasattr(self, 'tiempo_val') or self.tiempo_val is None:
                self.tiempo_val = time.monotonic()
            
            delta = time.monotonic() - self.tiempo_val
            
            # --- CORRECCIÓN DE SEGURIDAD ---
            # Solo intentamos mantener despierta la cámara si existe la conexión
            if self.cam.cap and self.cam.cap.isOpened():
                try:
                    self.cam.cap.grab()
                except:
                    pass
            # -------------------------------

            if delta >= CONFIG['validation_time']:
                # CORRECCIÓN: Usar el nombre correcto del método
                ret, frame = self.cam.capture_frame()
                
                if ret:
                    self.ui.update_scan_ui("GUARDANDO...", self.contador)
                    
                    if self._guardar_imagen_seguro(frame):
                        self.contador += 1
                        self.ui.update_scan_ui("EXITO", self.contador)
                        
                        self.ui.update_scan_ui("EXPULSANDO...", self.contador)
                        self.motor.eject()
                        
                        while not self.sensor.value and self.running:
                            self.ui.update_scan_ui("RETIRE HOJA", self.contador)
                            if self.input.is_pressed('RESET'): 
                                self.perform_soft_reset(); return
                            if self.input.get_event() == "OK": 
                                self.cam.stop(); self.state = "MENU"; return
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

    def perform_soft_reset(self):
        self.ui.draw_menu(["RESETEANDO..."], 0)
        self.cam.stop()
        self.motor.stop()
        time.sleep(0.2)
        self.state = "MENU"
        self.menu_index = 0

    def loop_menu(self):
        self.ui.draw_menu(self.menu_options, self.menu_index)
        event = self.input.get_event()
        if event == "UP": self.menu_index = (self.menu_index - 1) % len(self.menu_options)
        elif event == "DOWN": self.menu_index = (self.menu_index + 1) % len(self.menu_options)
        elif event == "OK":
            opcion = self.menu_options[self.menu_index]
            if opcion == "Escanear":
                self.ui.update_scan_ui("INICIANDO...", self.contador)
                if self.cam.connect(): # Usamos connect() directo
                    self.state = "SCAN"
                else: 
                    self.ui.update_scan_ui("ERROR CAM", 0)
                    time.sleep(1)
            elif opcion == "Estadisticas": self.state = "STATS"
            elif opcion == "Salir": self.running = False

    def loop_stats(self):
        try: num = len(list(CONFIG['save_dir'].glob('*.jpg')))
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
        self.motor.stop()
        try:
            self.ui.draw.rectangle((0,0,128,128), fill=(0,0,0))
            self.ui.disp.image(self.ui.image)
        except: pass
        sys.exit(0)

if __name__ == "__main__":
    app = OMRSystem()
    app.run()