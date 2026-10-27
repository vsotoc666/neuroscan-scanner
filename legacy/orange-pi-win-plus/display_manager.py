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
            # 1. Configuración SPI Específica para Orange Pi
            # Usamos los pines definidos en config.py
            cs_pin = digitalio.DigitalInOut(CONFIG['screen']['cs_pin'])
            dc_pin = digitalio.DigitalInOut(CONFIG['screen']['dc_pin'])
            reset_pin = digitalio.DigitalInOut(CONFIG['screen']['rst_pin'])
            
            # board.SPI() usará automáticamente PD2 (MOSI) y PD1 (CLK) si habilitaste SPI1
            spi = board.SPI()

            # 2. Inicializar Driver
            self.disp = st7735.ST7735R(
                spi,
                rotation=90,
                cs=cs_pin,
                dc=dc_pin,
                rst=reset_pin,
                baudrate=CONFIG['screen']['baudrate'],
                width=CONFIG['screen']['width'],
                height=CONFIG['screen']['height'],
                x_offset=CONFIG['screen']['x_offset'],
                y_offset=CONFIG['screen']['y_offset'],
                bgr=True
            )

            # Ajuste de dimensiones
            if self.disp.rotation % 180 == 90:
                self.h = self.disp.width
                self.w = self.disp.height
            else:
                self.w = self.disp.width
                self.h = self.disp.height

            self.image = Image.new("RGB", (self.w, self.h))
            self.draw = ImageDraw.Draw(self.image)

            # Fuentes y Colores (Igual que antes)
            try:
                self.font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
                self.font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
                self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 10)
            except:
                self.font_big = ImageFont.load_default()
                self.font_med = ImageFont.load_default()
                self.font_small = ImageFont.load_default()
            
            self.C = {
                'BG_DARK': (30, 30, 30), 'BG_HEADER': (52, 73, 94),
                'ACCENT': (52, 152, 219), 'SUCCESS': (46, 204, 113),
                'WARNING': (241, 196, 15), 'ERROR': (231, 76, 60),
                'TEXT_MAIN': (236, 240, 241), 'TEXT_SUB': (149, 165, 166),
                'BLACK': (0, 0, 0), 'WHITE': (255, 255, 255)
            }
            logger.info("Pantalla OPi Inicializada.")

        except Exception as e:
            logger.critical(f"Error UI: {e}")
            raise

    # --- MÉTODOS DE DIBUJO (Iguales a tu versión anterior) ---
    def center_text(self, text, font, y_pos, color):
        try:
            left, top, right, bottom = self.draw.textbbox((0, 0), text, font=font)
            text_width = right - left
        except AttributeError:
            text_width = self.draw.textlength(text, font=font)
        x_pos = (self.w - text_width) // 2
        self.draw.text((x_pos, y_pos), text, font=font, fill=color)

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

    def draw_menu(self, options, selected_index):
        self.draw.rectangle((0, 0, self.w, self.h), fill=self.C['BG_DARK'])
        self.draw.rectangle((0, 0, self.w, 25), fill=self.C['BG_HEADER'])
        self.draw.text((10, 6), "MENU OPi", font=self.font_small, fill=self.C['ACCENT'])
        
        start_y = 35
        line_h = 22
        for i, option in enumerate(options):
            y = start_y + (i * line_h)
            if i == selected_index:
                self.draw.rectangle((2, y-2, self.w-2, y+18), fill=self.C['ACCENT'])
                color = self.C['BLACK']; prefix = ">"
            else:
                color = self.C['TEXT_MAIN']; prefix = " "
            self.draw.text((10, y), f"{prefix} {option}", font=self.font_med, fill=color)
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

    def update_scan_ui(self, estado, contador, progreso=0):
        bg = self.C['BG_DARK']
        if estado == "CAPTURANDO": bg = self.C['ACCENT']
        elif estado == "EXITO": bg = self.C['SUCCESS']
        elif estado == "ERROR": bg = self.C['ERROR']
        
        self.draw.rectangle((0, 0, self.w, self.h), fill=bg)
        self.draw.rectangle((0, 0, self.w, 22), fill=self.C['BG_HEADER'])
        self.draw.text((5, 4), "OMR SCAN", font=self.font_small, fill=self.C['ACCENT'])
        self.draw.text((self.w - 35, 4), f"#{contador:03d}", font=self.font_small, fill=self.C['TEXT_MAIN'])

        cy = self.h // 2
        icon_x = (self.w // 2) - 15

        if estado == "ESPERANDO":
            self.draw.ellipse((icon_x, cy-15, icon_x+30, cy+15), outline=self.C['TEXT_SUB'], width=2)
            self.center_text("LISTO", self.font_big, cy + 25, self.C['TEXT_MAIN'])
        elif estado == "VERIFICANDO":
            self._draw_icon_eye(icon_x, cy - 10, self.C['WARNING'])
            self.center_text("Analizando...", self.font_med, cy + 25, self.C['WARNING'])
            bw = 80; bx = (self.w - bw)//2
            self.draw.rectangle((bx, cy+20, bx+bw, cy+26), fill=(50,50,50))
            fill_w = int(bw * (progreso / 100))
            self.draw.rectangle((bx, cy+20, bx+fill_w, cy+26), fill=self.C['WARNING'])
        elif estado == "CAPTURANDO":
            self._draw_icon_cam(icon_x, cy - 10, self.C['ACCENT'])
            self.center_text("Capturando", self.font_med, cy + 25, self.C['ACCENT'])
        elif estado == "EXITO":
            self._draw_icon_check(icon_x, cy - 10, self.C['SUCCESS'])
            self.center_text("GUARDADO", self.font_big, cy + 25, self.C['SUCCESS'])
        elif estado == "ERROR":
            self._draw_icon_cross(icon_x, cy - 10, self.C['ERROR'])
            self.center_text("ERROR", self.font_big, cy + 25, self.C['ERROR'])
        elif estado == "RETIRE PAPEL":
            self.draw.polygon([(icon_x+15, cy-10), (icon_x, cy+10), (icon_x+30, cy+10)], fill=self.C['ACCENT'])
            self.center_text("Retire Hoja", self.font_med, cy + 25, self.C['TEXT_MAIN'])

        self.disp.image(self.image)