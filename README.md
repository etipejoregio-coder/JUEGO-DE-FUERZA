# Batalla de Fuerza

Juego de equipos **Mujeres vs Hombres** hecho con Python y Pygame.
Gana el primer equipo que llegue a la meta de puntos (30 por defecto).

## Requisitos

- Python 3.10 o superior
- Pygame 2 (se instala con `requirements.txt`)

```bat
pip install -r requirements.txt
python main.py
```

## Cómo se juega

1. En la pantalla de bienvenida pulsa **ENTER** (o el botón JUGAR).
2. Empieza el conteo regresivo **3, 2, 1, ¡INICIAMOS!**
3. Cada equipo presiona su tecla lo más rápido que pueda (por defecto **A** y **L**).
   El divisor central se mueve hacia el equipo que va ganando.
4. Al llegar a la meta suena la canción de celebración y aparece el mensaje
   *"PRESIONA [R] PARA REINICIAR"*.

Teclas fijas: `ENTER` jugar/aceptar, `ESC` volver/salir, `F11` pantalla completa.

## Botones del menú

- **JUGAR** · **REGLAS** (se escriben y se **leen en voz alta**) · **AJUSTES** · **PANTALLA COMPLETA**

> La voz de las reglas usa el motor de voz de Windows (no necesita instalar nada).
> Si tienes una voz en español instalada, la usa automáticamente.

## Ajustes (todo editable dentro del juego)

- **Teclas**: haz clic en el botón de la tecla y presiona la que quieras
  (equipo 1, equipo 2, REINICIAR y REGLAS).
- **Nombres** de los equipos, **meta** de puntos y **texto de las reglas**.
  En las reglas puedes usar `{EQ1}`, `{EQ2}`, `{TECLA1}`, `{TECLA2}` y `{META}`.
- **Imágenes**: bienvenida y las de cada equipo (PNG con fondo transparente para los equipos).
- **Música y efectos**: música de fondo, canción de celebración de cada equipo y
  efectos de click, conteo e "iniciamos".
- Cada fila tiene **ELEGIR** (abre el explorador de archivos) y **ORIGINAL** (vuelve al archivo por defecto).
- **CARPETA PERSONALIZADA** abre la carpeta `personalizado` y **RESTAURAR TODO** deja todo como al inicio.

Tus cambios se guardan junto al juego en `config.json` y en la carpeta `personalizado/`.

## Personalizar a mano (opcional)

Suelta archivos en la carpeta `personalizado/` (junto al `.exe` o a `main.py`) con
**el mismo nombre** que los de `assets/` y el juego los usará:

| Archivo | Para qué sirve |
|---|---|
| `bienvenida.png` | Fondo de la pantalla de bienvenida (si no existe se dibuja un fondo neón) |
| `chica.png`, `chico.png` | Personajes de cada equipo |
| `adorno_m1.png`, `adorno_m2.png`, `adorno_h1.png`, `adorno_h2.png` | Adornos de cada lado |
| `fondo.mp3` | Música de fondo |
| `victoria.mp3` | Canción de celebración |
| `click.wav`, `conteo.wav`, `inicio.wav` | Efectos de sonido |

> Los mp3 e imágenes incluidos son **simulados**. El juego no falla si falta o no se
> puede cargar un archivo: simplemente no se muestra o no suena.

## Generar el .exe (Windows)

Haz doble clic en `build_exe.bat`. El ejecutable queda en `dist\BatallaDeFuerza.exe`.
Las carpetas `personalizado/` y el archivo `config.json` se crean junto al `.exe`.
