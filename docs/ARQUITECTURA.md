# Arquitectura del software

Este documento describe la versión final, que está en [`firmware/rpi-zero2w/`](../firmware/rpi-zero2w).

## Componentes

```mermaid
classDiagram
    class OMRSystem {
        -state: str
        -menu_options: list
        -menu_index: int
        -contador: int
        -sensor: DigitalInOut
        +run()
        +loop_menu()
        +loop_scan()
        +loop_notas()
        +loop_stats()
        +perform_soft_reset()
        +cleanup()
        -_guardar_imagen_seguro(frame)
        -_procesar_estilo_escaneo_leve(frame)
    }
    class DisplayManager {
        +draw_menu(options, idx)
        +update_scan_ui(estado, contador, progreso)
        +draw_grades_list(history, scroll, idx)
        +draw_exam_detail(data)
        +draw_stats(total, temp)
    }
    class CameraManager {
        -cap: VideoCapture
        +connect() bool
        +capture_frame() (bool, frame)
        +stop()
    }
    class InputManager {
        -buttons: dict
        +is_pressed(name) bool
        +get_event() str
    }
    class APIManager {
        -queue: Queue
        -history: list
        +encolar_examen(path)
        +get_history() list
        -_worker()
        -_upload_sync(path) dict
    }
    class CONFIG {
        <<config.py>>
    }
    OMRSystem *-- DisplayManager
    OMRSystem *-- CameraManager
    OMRSystem *-- InputManager
    OMRSystem *-- APIManager
    DisplayManager ..> CONFIG
    CameraManager ..> CONFIG
    InputManager ..> CONFIG
    APIManager ..> CONFIG
```

| Archivo | Responsabilidad |
|---|---|
| `launcher.py` | Bucle infinito: espera a que se presione OK y ejecuta `main.py` como subproceso. Cuando `main.py` termina (al elegir *Salir* o por un error), vuelve a esperar. |
| `main.py` | Clase `OMRSystem`: inicializa el hardware, comprueba la escritura en disco y ejecuta la máquina de estados. |
| `camera_manager.py` | Busca la cámara en `/dev/video*`, la abre con backend V4L2 en MJPEG (más rápido sobre USB 2.0), hace un *warm-up* de 5 frames y, en cada captura, descarta 4 frames del búfer para no fotografiar una imagen vieja (*anti-ghosting*). Si falla, se reconecta sola. |
| `api_manager.py` | Cola FIFO y un hilo *daemon* que sube cada imagen al servidor de IA y guarda en memoria las últimas 50 respuestas. |
| `display_manager.py` | Dibuja todas las pantallas con Pillow y las envía a la TFT ST7735 por SPI. |
| `input_manager.py` | Lee los 4 botones con *pull-up* interno (activos en bajo), con un *debounce* de 150 ms. |
| `config.py` | Pines, resolución, calidad JPEG, tiempo de validación, credenciales de la API (leídas del entorno) y logging rotativo (1 MB × 3). |

## Máquina de estados principal

`OMRSystem.run()` es un bucle que, en cada iteración:

1. Revisa el botón **RESET**. Si está presionado, hace un reinicio suave: apaga la cámara y vuelve a `MENU`.
2. Llama al manejador del estado actual (`loop_menu`, `loop_scan`, `loop_notas` o `loop_stats`).

Cada manejador dibuja su pantalla, lee **un** evento de botón y decide la transición. Ningún manejador bloquea por mucho tiempo; la única excepción es la espera a que se retire la hoja, y dentro de ella también se atienden RESET y OK.

```mermaid
stateDiagram-v2
    [*] --> MENU
    MENU --> MENU: UP / DOWN
    MENU --> SCAN: OK en "Escanear" y cámara conectada
    MENU --> MENU: OK en "Escanear" y ERROR CAM
    MENU --> NOTAS: OK en "Notas"
    MENU --> STATS: OK en "Estadisticas"
    MENU --> [*]: OK en "Salir" (cleanup)

    state NOTAS {
        [*] --> LISTA
        LISTA --> LISTA: UP / DOWN (scroll de 4 filas)
        LISTA --> DETALLE: OK (hay notas)
        DETALLE --> LISTA: OK
    }
    NOTAS --> MENU: OK con historial vacío

    STATS --> MENU: OK
    SCAN --> MENU: OK (apaga cámara)

    note right of MENU
        RESET desde cualquier estado
        apaga la cámara y vuelve a MENU
    end note
```

## Sub-máquina de escaneo (`loop_scan`)

```mermaid
stateDiagram-v2
    [*] --> ESPERANDO
    ESPERANDO --> VERIFICANDO: sensor detecta papel (inicia cronómetro)
    VERIFICANDO --> ESPERANDO: papel retirado antes de 0.6 s
    VERIFICANDO --> VERIFICANDO: barra de progreso 0-100 %
    VERIFICANDO --> CAPTURA: papel quieto >= validation_time (0.6 s)
    CAPTURA --> ERROR_CAM: capture_frame() falla, se reconecta
    ERROR_CAM --> CAPTURA: reintenta en la siguiente iteración
    CAPTURA --> GUARDAR: frame OK
    GUARDAR --> ERROR_DISCO: imwrite falla (pausa 2 s)
    ERROR_DISCO --> ESPERANDO
    GUARDAR --> EXITO: archivo escrito, se encola a la API
    EXITO --> RETIRE_HOJA
    RETIRE_HOJA --> ESPERANDO: sensor ya no ve papel
```

Mientras dura la verificación, se llama a `cap.grab()` en cada iteración para que el búfer de la cámara se mantenga fresco.

### Procesamiento de imagen

Lo hace `_procesar_estilo_escaneo_leve`, antes de guardar:

1. **Escala de grises** (`cv2.cvtColor`): reduce la memoria a la tercera parte.
2. **Recorte** de 100 px a cada lado, para quitar los bordes del soporte.
3. **CLAHE** (`clipLimit=2.0`, `tileGridSize=8×8`): ecualización de contraste local que realza las burbujas marcadas sin saturar la imagen.
4. Se guarda como JPEG con calidad 100 en `scans/scan_AAAAMMDD_HHMMSS_mmm_proc.jpg`.

Después de cada captura se llama a `gc.collect()`, para no agotar los 512 MB de RAM de la Pi Zero 2 W cuando la imagen es 1920×1080.

## Comunicación con el servidor de IA

El modelo de IA que corrige la ficha corre en un servidor externo. **No forma parte de este repositorio**. El dispositivo solo actúa como cliente.

```mermaid
sequenceDiagram
    participant S as OMRSystem (hilo principal)
    participant Q as Cola
    participant W as APIManager._worker (hilo)
    participant IA as Servidor IA
    S->>Q: encolar_examen(ruta.jpg)
    Note over S: continúa escaneando sin esperar
    W->>Q: get()
    W->>IA: POST multipart file=@ruta.jpg<br/>Header X-API-Key
    IA-->>W: 200 JSON
    W->>W: history.append(registro) (máx. 50)
    S->>W: get_history() desde la pantalla "Notas"
```

### Petición

```http
POST {OMR_API_URL}
X-API-Key: {OMR_API_KEY}
Content-Type: multipart/form-data

file=<imagen JPEG>
```

El tiempo de espera es `OMR_API_TIMEOUT` (20 s por defecto).

### Respuesta esperada (HTTP 200)

```json
{
  "score": 14.5,
  "stats": { "correct": 29, "incorrect": 11, "total": 40 },
  "details": [ ... ],
  "process_time_seconds": 0.0599
}
```

### Registro que se guarda en el historial

| Campo | Origen |
|---|---|
| `status` | `OK`, `ERR` (HTTP ≠ 200) o `FAIL` (error de red o archivo inexistente) |
| `id` | Hora de la captura (`HHMMSS`), tomada del nombre del archivo |
| `nota` | `score` |
| `tiempo` | `process_time_seconds` |
| `correctas` / `incorrectas` / `total` | `stats.*` |

En la pantalla de detalle, la nota se pinta en verde si es ≥ 10.5 (aprobado en la escala vigesimal) y en rojo en caso contrario.

## Diagramas originales de la presentación

| Clases (preliminar, con motor) | Clases (final) | Flujo (final, detalle del hilo API) |
|---|---|---|
| ![](img/diagrama-clases-preliminar.png) | ![](img/diagrama-clases-final.png) | ![](img/diagrama-flujo-final.png) |

La presentación completa está en [`presentacion-bma20.pptx`](presentacion-bma20.pptx).

## Limitaciones conocidas

- **El historial vive solo en RAM.** Se pierde al reiniciar. Las subidas que fallan aparecen como `ERR` en el historial, y en el detalle se ve el motivo (por ejemplo `HTTP 500` o `Error Red`), pero no se reintentan.
- Desde la lista de **Notas** con historial, OK abre el detalle; para volver al menú se usa **RESET**.
