import time
import os
import digitalio
import cv2
import logging
from config import CONFIG, setup_logging
from display_manager import DisplayManager
from camera_manager import CameraManager
from input_manager import InputManager

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
        self.cam = None 
        
        self.sensor = digitalio.DigitalInOut(CONFIG['sensor_pin'])
        self.sensor.direction = digitalio.Direction.INPUT
        self.sensor.pull = digitalio.Pull.UP
        
        os.makedirs(CONFIG['save_dir'], exist_ok=True)
        
    def run(self):
        while self.running:
            # Chequeo de Reset Global
            if self.input.is_pressed('RESET'):
                self.perform_soft_reset()
                continue

            if self.state == "MENU":
                self.loop_menu()
            elif self.state == "SCAN":
                self.loop_scan()
            elif self.state == "STATS":
                self.loop_stats()
        
        self.cleanup()

    def perform_soft_reset(self):
        """Reinicio suave al menú"""
        logger.warning(">>> RESET SOLICITADO <<<")
        
        # --- CORRECCIÓN AQUÍ ---
        self.ui.draw.rectangle((0, 0, self.ui.w, self.ui.h), fill=self.ui.C['ERROR'])
        # Ahora usamos center_text (público) y el color WHITE (ya definido)
        self.ui.center_text("REINICIANDO...", self.ui.font_big, 60, self.ui.C['WHITE'])
        self.ui.disp.image(self.ui.image)
        
        if self.cam:
            self.cam.release()
            self.cam = None
        
        self.state = "MENU"
        self.menu_index = 0
        time.sleep(1.0)

    def loop_menu(self):
        self.ui.draw_menu(self.menu_options, self.menu_index)
        event = self.input.get_event()
        
        if event == "RESET": self.perform_soft_reset(); return
        if event == "UP": self.menu_index = (self.menu_index - 1) % len(self.menu_options)
        elif event == "DOWN": self.menu_index = (self.menu_index + 1) % len(self.menu_options)
        elif event == "OK":
            opcion = self.menu_options[self.menu_index]
            if opcion == "Escanear":
                self.state = "SCAN"
                self.cam = CameraManager()
            elif opcion == "Estadisticas":
                self.state = "STATS"
            elif opcion == "Salir":
                self.running = False

    def loop_scan(self):
        event = self.input.get_event()
        if event == "RESET": self.perform_soft_reset(); return
        if event == "OK":
            self.state = "MENU"
            if self.cam: self.cam.release()
            self.cam = None
            return

        papel_presente = not self.sensor.value
        if papel_presente:
            if not hasattr(self, 'tiempo_validacion') or self.tiempo_validacion is None:
                self.tiempo_validacion = time.monotonic()
            
            transcurrido = time.monotonic() - self.tiempo_validacion
            if transcurrido >= CONFIG['validation_time']:
                self.ui.update_scan_ui("CAPTURANDO", self.contador)
                ret, frame = self.cam.capture_frame()
                if ret:
                    timestamp = time.strftime("%H%M%S")
                    cv2.imwrite(f"{CONFIG['save_dir']}/scan_{timestamp}.jpg", frame)
                    self.contador += 1
                    self.ui.update_scan_ui("EXITO", self.contador)
                    time.sleep(1.5)
                    while not self.sensor.value:
                        self.ui.update_scan_ui("RETIRE PAPEL", self.contador)
                        ev = self.input.get_event()
                        if ev == "RESET": self.perform_soft_reset(); return
                        if ev == "OK": self.state = "MENU"; return
                        time.sleep(0.1)
                else:
                    self.ui.update_scan_ui("ERROR", self.contador)
                    time.sleep(1)
            else:
                progreso = int((transcurrido / CONFIG['validation_time']) * 100)
                self.ui.update_scan_ui("VERIFICANDO", self.contador, progreso)
        else:
            self.tiempo_validacion = None
            self.ui.update_scan_ui("ESPERANDO", self.contador)
        time.sleep(0.05)

    def loop_stats(self):
        try:
            num_files = len([n for n in os.listdir(CONFIG['save_dir']) if os.path.isfile(os.path.join(CONFIG['save_dir'], n))])
        except: num_files = 0
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = round(int(f.read()) / 1000, 1)
        except: temp = "??"

        self.ui.draw_stats(num_files, temp)
        event = self.input.get_event()
        if event == "RESET": self.perform_soft_reset()
        elif event == "OK": self.state = "MENU"
        time.sleep(0.1)

    def cleanup(self):
        if self.cam: self.cam.release()
        try:
            self.ui.draw.rectangle((0,0,128,128), fill=(0,0,0))
            self.ui.disp.image(self.ui.image)
        except: pass

if __name__ == "__main__":
    app = OMRSystem()
    app.run()