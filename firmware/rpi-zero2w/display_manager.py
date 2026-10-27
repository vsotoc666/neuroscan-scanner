import digitalio
import board
import logging
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import st7735
from config import CONFIG

logger = logging.getLogger("DisplayUI")

class DisplayManager:
    def __init__(self):
        try:
            cs_pin = digitalio.DigitalInOut(board.CE0)
            dc_pin = digitalio.DigitalInOut(board.D24)
            reset_pin = digitalio.DigitalInOut(board.D25)
            spi = board.SPI()

            self.disp = st7735.ST7735R(
                spi, rotation=90, cs=cs_pin, dc=dc_pin, rst=reset_pin,
                baudrate=CONFIG['screen']['baudrate'],
                width=CONFIG['screen']['width'], height=CONFIG['screen']['height'],
                x_offset=CONFIG['screen']['x_offset'], y_offset=CONFIG['screen']['y_offset'],
                bgr=True
            )

            if self.disp.rotation % 180 == 90:
                self.h = self.disp.width; self.w = self.disp.height
            else:
                self.w = self.disp.width; self.h = self.disp.height

            self.image = Image.new("RGB", (self.w, self.h))
            self.draw = ImageDraw.Draw(self.image)

            # Fuentes
            try:
                self.font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
                self.font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
                self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 10)
                self.font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 9)
            except:
                self.font_big = ImageFont.load_default()
                self.font_med = ImageFont.load_default()
                self.font_small = ImageFont.load_default()
                self.font_tiny = ImageFont.load_default()
            
            self.C = {
                'BG_DARK': (30, 30, 30), 'BG_HEADER': (52, 73, 94),
                'ACCENT': (52, 152, 219), 'SUCCESS': (46, 204, 113),
                'WARNING': (241, 196, 15), 'ERROR': (231, 76, 60),
                'TEXT_MAIN': (236, 240, 241), 'TEXT_SUB': (149, 165, 166),
                'BLACK': (0, 0, 0), 'WHITE': (255, 255, 255)
            }

        except Exception as e:
            logger.critical(f"Error UI: {e}")
            raise

    def center_text(self, text, font, y_pos, color):
        try:
            left, top, right, bottom = self.draw.textbbox((0, 0), text, font=font)
            text_width = right - left
        except AttributeError:
            text_width = self.draw.textlength(text, font=font)
        x_pos = (self.w - text_width) // 2
        self.draw.text((x_pos, y_pos), text, font=font, fill=color)

    # --- ICONOS ---
    def _draw_icon_eye(self, x, y, color):
        self.draw.ellipse((x, y+5, x+30, y+25), outline=color, width=2)
        self.draw.ellipse((x+12, y+12, x+18, y+18), fill=color)
    def _draw_icon_cam(self, x, y, color):
        self.draw.rectangle((x, y+5, x+30, y+25), outline=color, width=2)
        self.draw.ellipse((x+10, y+10, x+20, y+20), outline=color, width=2)
        self.draw.rectangle((x+5, y, x+10, y+5), fill=color)
    def _draw_icon_check(self, x, y, color):
        self.draw.line((x, y+10, x+10, y+20), fill=color, width=4)
        self.draw.line((x+10, y+20, x+25, y-5), fill=color, width=4)
    def _draw_icon_cross(self, x, y, color):
        self.draw.line((x, y, x+20, y+20), fill=color, width=4)
        self.draw.line((x, y+20, x+20, y), fill=color, width=4)

    # --- PANTALLAS ---
    def draw_menu(self, options, selected_index):
        self.draw.rectangle((0, 0, self.w, self.h), fill=self.C['BG_DARK'])
        self.draw.rectangle((0, 0, self.w, 25), fill=self.C['BG_HEADER'])
        self.draw.text((10, 6), "MENU PRINCIPAL", font=self.font_small, fill=self.C['ACCENT'])
        
        start_y = 35; line_h = 22
        for i, option in enumerate(options):
            y = start_y + (i * line_h)
            if i == selected_index:
                self.draw.rectangle((2, y-2, self.w-2, y+18), fill=self.C['ACCENT'])
                color = self.C['BLACK']; prefix = ">"
            else:
                color = self.C['TEXT_MAIN']; prefix = " "
            self.draw.text((10, y), f"{prefix} {option}", font=self.font_med, fill=color)
        self.disp.image(self.image)

    # --- NUEVA PANTALLA: DETALLE DE EXAMEN ---
    def draw_exam_detail(self, data):
        self.draw.rectangle((0, 0, self.w, self.h), fill=self.C['BG_DARK'])
        
        # Header
        self.draw.rectangle((0, 0, self.w, 25), fill=self.C['BG_HEADER'])
        self.draw.text((5, 6), f"ID: {data.get('id', '?')}", font=self.font_small, fill=self.C['WHITE'])

        # El servidor no devolvió nota (error HTTP o de red)
        if data.get('status') != 'OK':
            self._draw_icon_cross((self.w // 2) - 10, 40, self.C['ERROR'])
            self.center_text("SIN NOTA", self.font_med, 70, self.C['ERROR'])
            self.center_text(str(data.get('error', 'Error')), self.font_small, 90, self.C['TEXT_SUB'])
            self.draw.rectangle((0, self.h-15, self.w, self.h), fill=self.C['WARNING'])
            self.center_text("[OK] Volver", self.font_small, self.h-12, self.C['BLACK'])
            self.disp.image(self.image)
            return

        # Nota Grande
        score = data.get('nota', 0.0)
        # Color verde si nota > 10, rojo si no (ajustable)
        color_score = self.C['SUCCESS'] if score >= 10.5 else self.C['ERROR']
        
        self.center_text("NOTA FINAL", self.font_small, 35, self.C['TEXT_SUB'])
        self.center_text(f"{score}", self.font_big, 50, color_score)
        
        # Tiempo y Stats
        time_proc = data.get('tiempo', 0.0)
        correctas = data.get('correctas', 0)
        total = data.get('total', 0)
        
        info_str = f"Bien: {correctas}/{total}  |  {time_proc:.2f}s"
        self.center_text(info_str, self.font_tiny, 85, self.C['ACCENT'])
        
        # Footer
        self.draw.rectangle((0, self.h-15, self.w, self.h), fill=self.C['WARNING'])
        self.center_text("[OK] Volver", self.font_small, self.h-12, self.C['BLACK'])
        
        self.disp.image(self.image)

    def draw_grades_list(self, history, scroll_offset, selected_index):
        self.draw.rectangle((0, 0, self.w, self.h), fill=self.C['BG_DARK'])
        self.draw.rectangle((0, 0, self.w, 20), fill=self.C['BG_HEADER'])
        self.draw.text((5, 4), "HISTORIAL", font=self.font_small, fill=self.C['ACCENT'])
        
        if not history:
            self.center_text("Vacio", self.font_med, 60, self.C['TEXT_SUB'])
            self.center_text("[OK] Volver", self.font_small, 110, self.C['WARNING'])
            self.disp.image(self.image)
            return

        start_y = 25; line_h = 20; max_lines = 4
        
        for i in range(max_lines):
            idx = scroll_offset + i
            if idx < len(history):
                item = history[idx]
                y = start_y + (i * line_h)
                
                if idx == selected_index:
                    self.draw.rectangle((0, y-2, self.w, y+18), fill=self.C['ACCENT'])
                    color_txt = self.C['BLACK']
                else:
                    color_txt = self.C['TEXT_MAIN']

                nota_str = str(item.get('nota', '--')) if item.get('status') == 'OK' else "ERR"
                id_str = str(item.get('id', '??'))
                
                self.draw.text((5, y), f"Ex.{id_str}", font=self.font_med, fill=color_txt)
                self.draw.text((90, y), nota_str, font=self.font_med, fill=color_txt)

        self.draw.text((5, self.h-12), "[OK] Ver Detalle", font=self.font_small, fill=self.C['TEXT_SUB'])
        self.disp.image(self.image)

    def draw_stats(self, total_files, cpu_temp="--"):
        self.draw.rectangle((0, 0, self.w, self.h), fill=self.C['BG_DARK'])
        self.draw.text((10, 5), "ESTADISTICAS", font=self.font_med, fill=self.C['ACCENT'])
        self.draw.line((0, 22, self.w, 22), fill=self.C['ACCENT'])
        self.draw.text((10, 35), f"Fichas: {total_files}", font=self.font_small, fill=self.C['TEXT_MAIN'])
        self.draw.text((10, 55), f"Temp: {cpu_temp}'C", font=self.font_small, fill=self.C['TEXT_MAIN'])
        self.draw.rectangle((30, 105, 98, 125), fill=self.C['WARNING'])
        self.center_text("[OK] Volver", self.font_small, 108, self.C['BLACK'])
        self.disp.image(self.image)

    # Nombres que usa main.py -> estado que sabe dibujar esta pantalla
    ALIAS_ESTADOS = {
        "GUARDANDO...": "CAPTURANDO",
        "SUBIENDO...": "SUBIENDO",
        "RETIRE HOJA": "RETIRE PAPEL",
        "INICIANDO...": "INICIANDO",
    }

    def update_scan_ui(self, estado, contador, progreso=0):
        # "ERROR CAM" / "ERROR DISCO" -> estado ERROR con el detalle debajo
        detalle = ""
        if estado.startswith("ERROR"):
            detalle = estado[len("ERROR"):].strip()
            estado = "ERROR"
        estado = self.ALIAS_ESTADOS.get(estado, estado)

        bg = self.C['BG_DARK']
        if estado == "CAPTURANDO": bg = self.C['ACCENT']
        elif estado == "EXITO": bg = self.C['SUCCESS']
        elif estado == "ERROR": bg = self.C['ERROR']
        elif estado == "SUBIENDO": bg = self.C['ACCENT'] # Nuevo Estado

        self.draw.rectangle((0, 0, self.w, self.h), fill=bg)
        self.draw.rectangle((0, 0, self.w, 22), fill=self.C['BG_HEADER'])
        self.draw.text((5, 4), "OMR SCAN", font=self.font_small, fill=self.C['ACCENT'])
        self.draw.text((self.w - 35, 4), f"#{contador:03d}", font=self.font_small, fill=self.C['TEXT_MAIN'])

        cy = self.h // 2; icon_x = (self.w // 2) - 15

        if estado == "ESPERANDO":
            self.draw.ellipse((icon_x, cy-15, icon_x+30, cy+15), outline=self.C['TEXT_SUB'], width=2)
            self.center_text("LISTO", self.font_big, cy + 25, self.C['TEXT_MAIN'])
        elif estado == "VERIFICANDO":
            self._draw_icon_eye(icon_x, cy - 10, self.C['WARNING'])
            # Barra de progreso debajo del icono y texto debajo de la barra (sin solaparse)
            self.center_text("Analizando...", self.font_med, cy + 30, self.C['WARNING'])
            bw = 80; bx = (self.w - bw)//2
            self.draw.rectangle((bx, cy+18, bx+bw, cy+24), fill=(50,50,50))
            fill_w = int(bw * (progreso / 100))
            self.draw.rectangle((bx, cy+18, bx+fill_w, cy+24), fill=self.C['WARNING'])
        # En los estados con fondo de color se dibuja en blanco para que se vea
        elif estado == "INICIANDO":
            self._draw_icon_cam(icon_x, cy - 10, self.C['ACCENT'])
            self.center_text("Iniciando...", self.font_med, cy + 25, self.C['TEXT_MAIN'])
        elif estado == "CAPTURANDO":
            self._draw_icon_cam(icon_x, cy - 10, self.C['WHITE'])
            self.center_text("Capturando", self.font_med, cy + 25, self.C['WHITE'])
        elif estado == "SUBIENDO":
            self._draw_icon_cam(icon_x, cy - 10, self.C['WHITE'])
            self.center_text("Enviando API...", self.font_med, cy + 25, self.C['WHITE'])
        elif estado == "EXITO":
            self._draw_icon_check(icon_x, cy - 10, self.C['WHITE'])
            self.center_text("GUARDADO", self.font_big, cy + 25, self.C['WHITE'])
        elif estado == "ERROR":
            self._draw_icon_cross(icon_x, cy - 10, self.C['WHITE'])
            self.center_text("ERROR", self.font_big, cy + 20, self.C['WHITE'])
            if detalle:
                self.center_text(detalle, self.font_small, cy + 45, self.C['WHITE'])
        elif estado == "RETIRE PAPEL":
            self.draw.polygon([(icon_x+15, cy-10), (icon_x, cy+10), (icon_x+30, cy+10)], fill=self.C['ACCENT'])
            self.center_text("Retire Hoja", self.font_med, cy + 25, self.C['TEXT_MAIN'])

        self.disp.image(self.image)