# Versiones anteriores

Estas carpetas se conservan como registro de cómo evolucionó el proyecto. **Ninguna envía las imágenes a la IA**: solo capturan y guardan las fichas en `scans/`. La versión que se mantiene está en [`firmware/rpi-zero2w`](../firmware/rpi-zero2w).

| Carpeta | Placa | Diferencias principales |
|---|---|---|
| `rpi-zero2w-v0/` | Raspberry Pi Zero 2 W | Primera versión. La cámara se crea al entrar a escanear y la pantalla de reinicio es roja. No tiene motor. |
| `orange-pi-win-plus/` | Orange Pi Win Plus | Pines Allwinner (`PB3`, `PL9`, …). Agrega un **motor de expulsión** (`motor_manager.py` + L298N) que se activa 0,8 s después de cada captura. |
| `rpi-zero2w-motor/` | Raspberry Pi Zero 2 W | Adapta la versión con motor a la Pi (GPIO 5/6) y corrige los nombres de los métodos de la cámara. Captura con V4L2 + MJPEG. |

> **Nota:** originalmente, `orange-pi-win-plus/main.py` llamaba a `cam.start()`, `cam.get_frame()` y `cam.stop()`, que su `camera_manager.py` no define, y fallaba al entrar a *Escanear*. Ya está corregido: usa `connect()` y `capture_frame()`, y se agregó `stop()`. Las mejoras de pantalla de la versión final (estados que no se dibujaban, iconos invisibles sobre fondos de color) **no** se llevaron a estas versiones.
