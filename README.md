# Batalla de Fuerza

Juego de equipos **Mujeres vs Hombres** hecho con Python y Pygame.
Gana el primer equipo que llegue a **30 puntos**.

## Requisitos

- Python 3.10 o superior
- Pygame (se instala con `requirements.txt`)

## Instalación y ejecución

```bat
pip install -r requirements.txt
python main.py
```

## Controles

| Tecla / acción            | Qué hace                                   |
|---------------------------|--------------------------------------------|
| `ENTER`                   | Iniciar (menú) / volver al menú (victoria) |
| `A`                       | +1 punto para **MUJERES** (rosa, izquierda)|
| `L`                       | +1 punto para **HOMBRES** (azul, derecha)  |
| Clic en **REINICIAR**     | Vuelve al menú (esquina superior derecha)  |
| `ESC`                     | Volver al menú / salir desde el menú       |

La barra de fuerza central se mueve hacia el equipo que va ganando.

## Personalizar (todo editable)

Reemplaza estos archivos por los tuyos conservando el mismo nombre:

- `assets/images/chica.png` y `assets/images/chico.png` (PNG con fondo transparente, se escalan solos)
- `assets/music/fondo.mp3` (música de fondo, en bucle)
- `assets/music/victoria.mp3` (se reproduce al ganar)
- `assets/sfx/click.wav` (sonido al sumar punto / pulsar botones)

> Los mp3 incluidos son **marcadores de posición** (simulados). El juego no falla si
> un archivo falta o no se puede cargar: simplemente no suena. Pon tus mp3 reales
> para tener música.

Para cambiar la meta de puntos, edita `META = 30` al inicio de `main.py`.

## Generar el .exe (Windows)

Haz doble clic en `build_exe.bat`. Al terminar, el ejecutable estará en
`dist\BatallaDeFuerza.exe` (incluye la carpeta `assets`).
