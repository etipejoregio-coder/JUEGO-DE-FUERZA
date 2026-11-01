"""
BATALLA DE FUERZA - Equipo 1 (Mujeres) vs Equipo 2 (Hombres)
Python 3.10+ / Pygame 2

Todo es editable desde el menu AJUSTES:
  teclas, nombres, reglas (con voz), meta, imagenes, musica y efectos.
Tambien puedes soltar tus archivos en la carpeta "personalizado" (junto al juego)
usando los mismos nombres que los de la carpeta assets.

Teclas fijas: ENTER = jugar/aceptar, ESC = volver/salir, F11 = pantalla completa.
"""
import copy
import json
import math
import os
import random
import shutil
import subprocess
import sys

import pygame

ANCHO, ALTO = 1280, 720
FPS = 60

ROSA = (255, 92, 184)
ROSA_OSC = (170, 20, 110)
AZUL = (60, 150, 255)
AZUL_OSC = (15, 50, 160)
BLANCO = (255, 255, 255)
NEGRO = (0, 0, 0)
DORADO = (255, 205, 40)
VERDE = (30, 160, 80)


# --------------------------------------------------------------------------
# Rutas y configuracion
# --------------------------------------------------------------------------
def carpeta_base():
    """Carpeta donde vive el juego (junto al .exe cuando esta empaquetado)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE = carpeta_base()
CARPETA_USER = os.path.join(BASE, "personalizado")
RUTA_CONFIG = os.path.join(BASE, "config.json")


def ruta_asset(rel):
    """Archivos incluidos dentro del juego (compatible con PyInstaller)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


ARCHIVOS_DEFECTO = {
    "bienvenida": "assets/images/bienvenida.png",
    "fondo_m": "assets/images/fondo_mujeres.png",
    "fondo_h": "assets/images/fondo_hombres.png",
    "img_m": "assets/images/chica.png",
    "img_h": "assets/images/chico.png",
    "victoria_img_m": "assets/images/victoria_mujeres.png",
    "victoria_img_h": "assets/images/victoria_hombres.png",
    "adorno_m1": "assets/images/adorno_m1.png",
    "adorno_m2": "assets/images/adorno_m2.png",
    "adorno_h1": "assets/images/adorno_h1.png",
    "adorno_h2": "assets/images/adorno_h2.png",
    "musica_fondo": "assets/music/fondo.mp3",
    "musica_vic_m": "assets/music/victoria.mp3",
    "musica_vic_h": "assets/music/victoria.mp3",
    "sfx_click": "assets/sfx/click.wav",
    "sfx_conteo": "assets/sfx/conteo.wav",
    "sfx_inicio": "assets/sfx/inicio.wav",
}

REGLAS_DEFECTO = (
    "Bienvenidos a la Batalla de Fuerza.\n"
    "Hay dos equipos: {EQ1} y {EQ2}.\n"
    "Cuando termine el conteo regresivo, cada equipo presiona su tecla lo más rápido que pueda. "
    "El equipo {EQ1} usa la tecla {TECLA1} y el equipo {EQ2} usa la tecla {TECLA2}.\n"
    "El juego se basa únicamente en empujar la barra central hacia el lado de tu equipo.\n"
    "No se cuentan las pulsaciones: gana automáticamente el equipo que arrincone al rival hasta el extremo.\n"
    "La ronda dura 40 segundos; si nadie llega al extremo, gana quien haya avanzado más.\n"
    "Si la barra queda centrada, se juega una prórroga de 10 segundos. El torneo consta de cinco rondas.\n"
    "¡Mucha suerte!"
)

CFG_DEFECTO = {
    "pantalla_completa": False,
    "teclas": {"mujeres": "a", "hombres": "l", "reiniciar": "r", "reglas": "f1"},
    "nombres": ["MUJERES", "HOMBRES"],
    "meta": 30,
    "modo_control": "teclado",
    "velocidad_barra": 1.0,
    "texto_gana": "¡{EQUIPO} GANAN!",
    "reglas": REGLAS_DEFECTO,
    "archivos": {},
}


def cargar_config():
    cfg = copy.deepcopy(CFG_DEFECTO)
    try:
        with open(RUTA_CONFIG, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if isinstance(datos, dict):
            for k, v in datos.items():
                if k in ("teclas", "archivos") and isinstance(v, dict):
                    cfg[k].update(v)
                elif k == "nombres" and isinstance(v, list) and len(v) == 2:
                    cfg[k] = [str(v[0]).upper()[:14], str(v[1]).upper()[:14]]
                elif k == "meta" and isinstance(v, int) and 1 <= v <= 999:
                    cfg[k] = v
                elif k in ("reglas", "texto_gana") and isinstance(v, str) and v.strip():
                    cfg[k] = v
                elif k == "pantalla_completa" and isinstance(v, bool):
                    cfg[k] = v
                elif k == "modo_control" and v in ("teclado", "pulsador"):
                    cfg[k] = v
                elif k == "velocidad_barra" and isinstance(v, (int, float)):
                    cfg[k] = max(0.5, min(3.0, float(v)))
    except Exception:
        pass
    return cfg


def guardar_config(cfg):
    try:
        with open(RUTA_CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def resolver(cfg, clave):
    """Busca el archivo a usar: elegido en ajustes > carpeta personalizado > incluido."""
    candidatos = []
    elegido = cfg["archivos"].get(clave)
    if elegido:
        candidatos.append(os.path.join(CARPETA_USER, elegido))
    defecto = ARCHIVOS_DEFECTO[clave]
    candidatos.append(os.path.join(CARPETA_USER, os.path.basename(defecto)))
    candidatos.append(ruta_asset(defecto))
    for c in candidatos:
        if os.path.isfile(c):
            return c
    return None


# --------------------------------------------------------------------------
# Utilidades de carga, texto y dibujo
# --------------------------------------------------------------------------
def cargar_imagen(ruta, alto):
    if not ruta:
        return None
    try:
        img = pygame.image.load(ruta).convert_alpha()
        esc = alto / img.get_height()
        return pygame.transform.smoothscale(img, (max(1, int(img.get_width() * esc)), alto))
    except Exception:
        return None


def cargar_cubrir(ruta):
    """Imagen de fondo ajustada a pantalla completa (recorta lo que sobre)."""
    if not ruta:
        return None
    try:
        img = pygame.image.load(ruta).convert_alpha()
        esc = max(ANCHO / img.get_width(), ALTO / img.get_height())
        nuevo = pygame.transform.smoothscale(
            img, (int(img.get_width() * esc) + 1, int(img.get_height() * esc) + 1))
        x = (nuevo.get_width() - ANCHO) // 2
        y = (nuevo.get_height() - ALTO) // 2
        return nuevo.subsurface(pygame.Rect(x, y, ANCHO, ALTO)).copy()
    except Exception:
        return None


def cargar_sonido(ruta, vol=0.8):
    if not ruta:
        return None
    try:
        s = pygame.mixer.Sound(ruta)
        s.set_volume(vol)
        return s
    except Exception:
        return None


_cache_fuentes = {}


def fuente(tam, negra=True):
    k = (tam, negra)
    if k not in _cache_fuentes:
        if negra:
            _cache_fuentes[k] = pygame.font.SysFont("arialblack,arial,verdana", tam, bold=True)
        else:
            _cache_fuentes[k] = pygame.font.SysFont("arial,verdana,dejavusans", tam)
    return _cache_fuentes[k]


def escribir(sup, txt, fnt, color, pos, sombra=True, off=4, alin="center"):
    kw = {alin: pos}
    if sombra:
        s = fnt.render(txt, True, NEGRO)
        sup.blit(s, s.get_rect(**kw).move(off, off))
    t = fnt.render(txt, True, color)
    r = t.get_rect(**kw)
    sup.blit(t, r)
    return r


def fuente_ajustada(txt, ancho_max, tam_ini, tam_min=18, negra=True):
    tam = tam_ini
    while tam > tam_min and fuente(tam, negra).size(txt)[0] > ancho_max:
        tam -= 2
    return fuente(tam, negra)


def degradado(w, h, c1, c2):
    sup = pygame.Surface((w, h))
    for y in range(h):
        k = y / max(1, h - 1)
        col = tuple(int(c1[i] + (c2[i] - c1[i]) * k) for i in range(3))
        pygame.draw.line(sup, col, (0, y), (w, y))
    return sup


def estrella(sup, centro, radio, color, ancho=3):
    pts = []
    for i in range(10):
        r = radio if i % 2 == 0 else radio * 0.45
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((centro[0] + r * math.cos(a), centro[1] + r * math.sin(a)))
    pygame.draw.polygon(sup, color, pts, ancho)


def envolver(txt, fnt, ancho):
    lineas = []
    for parrafo in txt.split("\n"):
        actual = ""
        for palabra in parrafo.split(" "):
            prueba = palabra if not actual else actual + " " + palabra
            if fnt.size(prueba)[0] <= ancho:
                actual = prueba
            else:
                if actual:
                    lineas.append(actual)
                actual = palabra
        lineas.append(actual)
    return lineas


def ajustar_texto(txt, ancho, alto, tam_max=40, tam_min=18):
    tam = tam_max
    while True:
        f = fuente(tam, False)
        lineas = envolver(txt, f, ancho)
        inter = int(tam * 1.35)
        if len(lineas) * inter <= alto or tam <= tam_min:
            return f, lineas, inter
        tam -= 2


def dibujar_parrafo(sup, lineas, fnt, x, y, inter, color, restantes):
    for ln in lineas:
        if restantes <= 0:
            break
        parte = ln[:restantes]
        sup.blit(fnt.render(parte, True, NEGRO), (x + 2, y + 2))
        sup.blit(fnt.render(parte, True, color), (x, y))
        restantes -= len(ln) + 1
        y += inter


def portapapeles():
    try:
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        t = r.clipboard_get()
        r.destroy()
        return t
    except Exception:
        return ""


def crear_fondo_neon():
    s = pygame.Surface((ANCHO, ALTO))
    s.blit(degradado(ANCHO // 2, ALTO, (255, 70, 200), (70, 0, 80)), (0, 0))
    s.blit(degradado(ANCHO // 2, ALTO, (50, 150, 255), (5, 15, 90)), (ANCHO // 2, 0))
    capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    for x in (90, 330, 560, 720, 950, 1190):
        pygame.draw.polygon(capa, (255, 255, 255, 26), [(x, 0), (x - 120, ALTO), (x + 120, ALTO)])
    for gx in range(18, 330, 30):
        for gy in range(110, ALTO - 60, 30):
            pygame.draw.circle(capa, (255, 255, 255, 45), (gx, gy), 3)
            pygame.draw.circle(capa, (255, 255, 255, 45), (ANCHO - gx, gy), 3)
    s.blit(capa, (0, 0))
    pygame.draw.line(s, BLANCO, (0, ALTO - 38), (ANCHO, ALTO - 38), 3)
    return s


# --------------------------------------------------------------------------
# Voz (Windows: motor de voz del sistema, sin instalar nada)
# --------------------------------------------------------------------------
class Voz:
    SCRIPT = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "foreach ($v in $s.GetInstalledVoices()) { "
        "if ($v.VoiceInfo.Culture.Name -like 'es*') { $s.SelectVoice($v.VoiceInfo.Name); break } }; "
        "$s.Speak($env:BF_TEXTO)"
    )

    def __init__(self):
        self.proc = None

    def hablar(self, texto):
        self.parar()
        if os.name != "nt" or not texto.strip():
            return False
        try:
            env = dict(os.environ)
            env["BF_TEXTO"] = texto.replace("\n", " ")
            self.proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
                 "-Command", self.SCRIPT],
                env=env, creationflags=0x08000000,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            self.proc = None
            return False

    def hablando(self):
        return self.proc is not None and self.proc.poll() is None

    def parar(self):
        if self.proc is not None:
            try:
                if self.proc.poll() is None:
                    self.proc.terminate()
            except Exception:
                pass
            self.proc = None


# --------------------------------------------------------------------------
# Juego
# --------------------------------------------------------------------------
class Juego:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass
        pygame.display.set_caption("Batalla de Fuerza")
        self.cfg = cargar_config()
        self.pantalla = None
        self.aplicar_pantalla()
        self.reloj = pygame.time.Clock()
        self.voz = Voz()

        self.bg_rosa = degradado(ANCHO, ALTO, (255, 130, 210), ROSA_OSC)
        self.bg_azul = degradado(ANCHO, ALTO, (110, 195, 255), AZUL_OSC)
        self.fondo_oscuro = degradado(ANCHO, ALTO, (34, 22, 70), (8, 8, 22))
        self.fondo_neon = crear_fondo_neon()
        self.velo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        self.velo.fill((0, 0, 0, 80))
        self.panel = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        self.panel.fill((0, 0, 0, 170))

        self.actualizar_codigos()
        self.recargar_recursos()

        self.estado = "menu"
        self.t = 0.0
        self.mujeres = 0
        self.hombres = 0
        self.combo_m = 0
        self.combo_h = 0
        self.mensaje_fuerza = ""
        self.mensaje_fuerza_t = 0.0
        self.ultimo_empuje = None
        self.ultimo_empuje_t = -1.0
        self.barra_pos = 0.5
        self.barra_objetivo = 0.5
        self.pulso_m = 0.0
        self.pulso_h = 0.0
        self.ganador = None
        self.confeti = []
        self.t_conteo = 0.0
        self.ultimo_paso = -1
        self.reglas_t0 = 0.0
        self.esperando = None
        self.editor = None
        self.mensaje = ""
        self.mensaje_t = 0.0
        self.confirmar_t = 0.0
        self.musica_actual = None
        self.vol_base = 0.45
        self._duck = False
        self._botones = []
        self._btn_nuevos = []
        self.poner_musica("fondo")

    # ---------------------------------------------------------------- pantalla
    def aplicar_pantalla(self):
        flags = pygame.SCALED
        if self.cfg["pantalla_completa"]:
            flags |= pygame.FULLSCREEN
        else:
            flags |= pygame.RESIZABLE
        try:
            self.pantalla = pygame.display.set_mode((ANCHO, ALTO), flags)
        except Exception:
            self.pantalla = pygame.display.set_mode((ANCHO, ALTO))

    def alternar_pantalla(self):
        self.cfg["pantalla_completa"] = not self.cfg["pantalla_completa"]
        self.aplicar_pantalla()
        guardar_config(self.cfg)

    # ---------------------------------------------------------------- recursos
    def recargar_recursos(self):
        c = self.cfg
        self.img_bienv = cargar_cubrir(resolver(c, "bienvenida"))
        self.fondo_m_custom = cargar_cubrir(resolver(c, "fondo_m"))
        self.fondo_h_custom = cargar_cubrir(resolver(c, "fondo_h"))
        self.img = {}
        self.victoria_img_m = cargar_cubrir(resolver(c, "victoria_img_m"))
        self.victoria_img_h = cargar_cubrir(resolver(c, "victoria_img_h"))
        self.rayo_super_fuerza = cargar_imagen(resolver(c, "rayo_super_fuerza"), 105)
        for k in ("img_m", "img_h"):
            r = resolver(c, k)
            self.img[k + "_j"] = cargar_imagen(r, 500)
            self.img[k + "_g"] = cargar_imagen(r, 580)
        self.adornos = {}
        for k in ("adorno_m1", "adorno_m2", "adorno_h1", "adorno_h2"):
            self.adornos[k] = cargar_imagen(resolver(c, k), 120)
        self.sfx = {}
        for k in ("click", "conteo", "inicio"):
            self.sfx[k] = cargar_sonido(resolver(c, "sfx_" + k))

    def actualizar_codigos(self):
        self.cod = {}
        for k, defecto in CFG_DEFECTO["teclas"].items():
            nombre = self.cfg["teclas"].get(k, defecto)
            try:
                self.cod[k] = pygame.key.key_code(nombre)
            except Exception:
                self.cfg["teclas"][k] = defecto
                self.cod[k] = pygame.key.key_code(defecto)

    def nombre_tecla(self, k):
        return self.cfg["teclas"][k].upper()

    # ---------------------------------------------------------------- audio
    def aplicar_volumen(self):
        try:
            pygame.mixer.music.set_volume(self.vol_base * (0.25 if self._duck else 1.0))
        except Exception:
            pass

    def poner_musica(self, cual, forzar=False):
        if self.musica_actual == cual and not forzar:
            return
        self.musica_actual = cual
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        claves = {"fondo": "musica_fondo", "vic_m": "musica_vic_m", "vic_h": "musica_vic_h"}
        if cual not in claves:
            return
        self.vol_base = 0.45 if cual == "fondo" else 0.75
        try:
            ruta = resolver(self.cfg, claves[cual])
            if ruta:
                pygame.mixer.music.load(ruta)
                pygame.mixer.music.play(-1)
                self.aplicar_volumen()
        except Exception:
            pass

    def sonar(self, nombre):
        s = self.sfx.get(nombre)
        if s:
            try:
                s.play()
            except Exception:
                pass

    # ---------------------------------------------------------------- textos
    def nombres(self):
        return self.cfg["nombres"][0], self.cfg["nombres"][1]

    def reglas_formateadas(self):
        n1, n2 = self.nombres()
        t = self.cfg["reglas"]
        for a, b in (("{EQ1}", n1), ("{EQ2}", n2), ("{TECLA1}", self.nombre_tecla("mujeres")),
                     ("{TECLA2}", self.nombre_tecla("hombres")), ("{META}", str(self.cfg["meta"]))):
            t = t.replace(a, b)
        return t

    def aviso(self, msg):
        self.mensaje = msg
        self.mensaje_t = 4.0

    # ---------------------------------------------------------------- flujo
    def volver_menu(self):
        self.voz.parar()
        self._duck = False
        self.estado = "menu"
        self.ganador = None
        self.confeti = []
        self.esperando = None
        self.poner_musica("fondo")
        self.aplicar_volumen()

    def abrir_reglas(self):
        self.estado = "reglas"
        self.reglas_t0 = self.t
        self.voz.hablar(self.reglas_formateadas())

    def repetir_reglas(self):
        self.reglas_t0 = self.t
        self.voz.hablar(self.reglas_formateadas())

    def abrir_ajustes(self):
        self.estado = "ajustes"
        self.esperando = None

    def iniciar_conteo(self):
        self.voz.parar()
        self.mujeres = 0
        self.hombres = 0
        self.combo_m = self.combo_h = 0
        self.mensaje_fuerza = ""
        self.mensaje_fuerza_t = 0.0
        self.barra_pos = 0.5
        self.barra_objetivo = 0.5
        self.tiempo_restante = 40.0
        self.tiempo_extra = 0.0
        self.ronda = 1
        self.puntos_ronda = {"m": 0, "h": 0}
        self.pulso_m = self.pulso_h = 0.0
        self.ganador = None
        self.confeti = []
        self.t_conteo = 0.0
        self.ultimo_paso = -1
        self.estado = "conteo"
        self.poner_musica("fondo")

    def sumar(self, quien):
        if self.estado != "juego":
            return
        self.sonar("click")
        self.ultimo_empuje = quien
        self.ultimo_empuje_t = self.t
        if quien == "m":
            self.pulso_m = 0.32
            self.mujeres += 1
            if self.mujeres >= 5:
                self.mujeres = 0
                if self.combo_m == 0:
                    self.barra_objetivo = max(0.015, self.barra_objetivo - 0.045)
                    self.combo_m = 1
                else:
                    self.barra_objetivo = max(0.015, self.barra_objetivo - 0.075)
                    self.combo_m = 0
                    self.mensaje_fuerza = "¡SUPER FUERZA MUJERES!"
                    self.mensaje_fuerza_t = 1.35
        else:
            self.pulso_h = 0.32
            self.hombres += 1
            if self.hombres >= 5:
                self.hombres = 0
                if self.combo_h == 0:
                    self.barra_objetivo = min(0.985, self.barra_objetivo + 0.045)
                    self.combo_h = 1
                else:
                    self.barra_objetivo = min(0.985, self.barra_objetivo + 0.075)
                    self.combo_h = 0
                    self.mensaje_fuerza = "¡SUPER FUERZA HOMBRES!"
                    self.mensaje_fuerza_t = 1.35

    def finalizar_ronda(self, quien):
        if self.estado != "juego":
            return
        self.ganador = quien
        self.puntos_ronda[quien] += 1
        self.estado = "victoria"
        self.poner_musica("vic_" + quien)
        self.crear_confeti()

    def siguiente_ronda(self):
        if self.ronda >= 5:
            self.estado = "final"
            self.ganador = ("m" if self.puntos_ronda["m"] > self.puntos_ronda["h"] else
                            "h" if self.puntos_ronda["h"] > self.puntos_ronda["m"] else None)
            return
        self.ronda += 1
        self.mujeres = self.hombres = 0
        self.combo_m = self.combo_h = 0
        self.mensaje_fuerza = ""
        self.mensaje_fuerza_t = 0.0
        self.barra_objetivo = 0.5
        self.ultimo_empuje = None
        self.ultimo_empuje_t = -1.0
        self.barra_pos = 0.5
        self.tiempo_restante = 40.0
        self.tiempo_extra = 0.0
        self.ganador = None
        self.confeti = []
        self.t_conteo = 0.0
        self.ultimo_paso = -1
        self.estado = "conteo"
        self.poner_musica("fondo")

    def cambiar_velocidad(self, delta):
        self.cfg["velocidad_barra"] = max(0.5, min(3.0, round(float(self.cfg.get("velocidad_barra", 1.0)) + delta, 1)))
        guardar_config(self.cfg)

    def crear_confeti(self):
        cols = [ROSA, BLANCO, DORADO] if self.ganador == "m" else [AZUL, BLANCO, DORADO]
        self.confeti = [
            [random.uniform(0, ANCHO), random.uniform(-ALTO, 0),
             random.uniform(-40, 40), random.uniform(120, 320),
             random.choice(cols), random.randint(6, 12)]
            for _ in range(160)
        ]

    # ---------------------------------------------------------------- ajustes: acciones
    def esperar_tecla(self, k):
        self.esperando = k
        self.aviso("Presiona la tecla que quieres usar (ESC cancela)")

    def asignar_tecla(self, e):
        k = self.esperando
        if e.key == pygame.K_ESCAPE:
            self.esperando = None
            return
        if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_F11):
            self.aviso("Esa tecla está reservada (ENTER, ESC y F11)")
            return
        nombre = pygame.key.name(e.key)
        if not nombre or not nombre.strip():
            self.aviso("Esa tecla no se puede usar")
            return
        for otra, valor in self.cfg["teclas"].items():
            if otra != k and valor == nombre:
                self.aviso("Esa tecla ya la usa otra acción")
                return
        self.cfg["teclas"][k] = nombre
        self.esperando = None
        self.actualizar_codigos()
        guardar_config(self.cfg)
        self.aviso("Tecla guardada: " + nombre.upper())

    def cambiar_modo_control(self):
        self.cfg["modo_control"] = "pulsador" if self.cfg["modo_control"] == "teclado" else "teclado"
        guardar_config(self.cfg)
        self.aviso("Control seleccionado: " + self.cfg["modo_control"].upper())

    def cambiar_meta(self, delta):
        self.cfg["meta"] = max(3, min(999, self.cfg["meta"] + delta))
        guardar_config(self.cfg)

    def dialogo_archivo(self, titulo, filtros):
        estaba_full = self.cfg["pantalla_completa"]
        if estaba_full:
            self.cfg["pantalla_completa"] = False
            self.aplicar_pantalla()
        ruta = ""
        try:
            import tkinter as tk
            from tkinter import filedialog
            raiz = tk.Tk()
            raiz.withdraw()
            raiz.attributes("-topmost", True)
            ruta = filedialog.askopenfilename(title=titulo, filetypes=filtros, parent=raiz)
            raiz.destroy()
        except Exception:
            ruta = ""
        if estaba_full:
            self.cfg["pantalla_completa"] = True
            self.aplicar_pantalla()
        pygame.event.clear()
        return ruta

    def elegir_archivo(self, clave, tipo):
        if tipo == "img":
            filtros = [("Imágenes", "*.png *.jpg *.jpeg *.bmp"), ("Todos", "*.*")]
        else:
            filtros = [("Audio", "*.mp3 *.wav *.ogg"), ("Todos", "*.*")]
        ruta = self.dialogo_archivo("Elige un archivo", filtros)
        if not ruta:
            return
        try:
            os.makedirs(CARPETA_USER, exist_ok=True)
            ext = os.path.splitext(ruta)[1].lower()
            nombre = clave + ext
            destino = os.path.join(CARPETA_USER, nombre)
            if os.path.abspath(ruta) != os.path.abspath(destino):
                shutil.copyfile(ruta, destino)
            self.cfg["archivos"][clave] = nombre
            guardar_config(self.cfg)
            self.aplicar_cambio_archivo(clave)
            self.aviso("Archivo guardado")
        except Exception:
            self.aviso("No se pudo copiar el archivo")

    def archivo_original(self, clave):
        nombre = self.cfg["archivos"].pop(clave, None)
        if nombre:
            try:
                os.remove(os.path.join(CARPETA_USER, nombre))
            except Exception:
                pass
        guardar_config(self.cfg)
        self.aplicar_cambio_archivo(clave)
        self.aviso("Restaurado al original")

    def aplicar_cambio_archivo(self, clave):
        self.recargar_recursos()
        if clave.startswith("musica_"):
            self.poner_musica(self.musica_actual or "fondo", forzar=True)
        elif clave.startswith("sfx_"):
            self.sonar(clave[4:])

    def abrir_carpeta(self):
        try:
            os.makedirs(CARPETA_USER, exist_ok=True)
            os.startfile(CARPETA_USER)  # solo Windows
        except Exception:
            self.aviso("Carpeta: " + CARPETA_USER)

    def restaurar_todo(self):
        if self.confirmar_t <= 0:
            self.confirmar_t = 4.0
            self.aviso("Pulsa RESTAURAR TODO otra vez para confirmar")
            return
        self.confirmar_t = 0
        for nombre in list(self.cfg["archivos"].values()):
            try:
                os.remove(os.path.join(CARPETA_USER, nombre))
            except Exception:
                pass
        self.cfg = copy.deepcopy(CFG_DEFECTO)
        guardar_config(self.cfg)
        self.aplicar_pantalla()
        self.actualizar_codigos()
        self.recargar_recursos()
        self.poner_musica("fondo", forzar=True)
        self.aviso("Todo restaurado a los valores originales")

    # ---------------------------------------------------------------- editor de texto
    def abrir_editor(self, titulo, texto, multilinea, maximo, al_aceptar):
        self.editor = {"titulo": titulo, "texto": texto, "multi": multilinea,
                       "max": maximo, "ok": al_aceptar, "volver": self.estado}
        self.estado = "editor"
        try:
            pygame.key.start_text_input()
        except Exception:
            pass

    def cerrar_editor(self, aceptar):
        ed = self.editor
        try:
            pygame.key.stop_text_input()
        except Exception:
            pass
        self.editor = None
        self.estado = ed["volver"]
        if aceptar:
            ed["ok"](ed["texto"])

    def editar_nombre(self, idx):
        def ok(txt):
            txt = txt.strip().upper()[:14]
            if txt:
                self.cfg["nombres"][idx] = txt
                guardar_config(self.cfg)
        self.abrir_editor("Nombre del equipo %d (ahora: %s)" % (idx + 1, self.cfg["nombres"][idx]),
                          "", False, 14, ok)

    def editar_reglas(self):
        def ok(txt):
            if txt.strip():
                self.cfg["reglas"] = txt
                guardar_config(self.cfg)
        self.abrir_editor("Reglas (usa {EQ1} {EQ2} {TECLA1} {TECLA2} {META})",
                          self.cfg["reglas"], True, 1500, ok)

    def ev_editor(self, e):
        ed = self.editor
        if e.type == pygame.TEXTINPUT:
            t = "".join(ch for ch in e.text if ch.isprintable())
            if len(ed["texto"]) + len(t) <= ed["max"]:
                ed["texto"] += t
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.cerrar_editor(False)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if ed["multi"] and not (e.mod & pygame.KMOD_CTRL):
                    if len(ed["texto"]) < ed["max"]:
                        ed["texto"] += "\n"
                else:
                    self.cerrar_editor(True)
            elif e.key == pygame.K_BACKSPACE:
                ed["texto"] = ed["texto"][:-1]
            elif e.key == pygame.K_v and (e.mod & pygame.KMOD_CTRL):
                t = "".join(ch for ch in portapapeles() if ch.isprintable() or ch == "\n")
                if not ed["multi"]:
                    t = t.replace("\n", " ")
                ed["texto"] = (ed["texto"] + t)[:ed["max"]]

    # ---------------------------------------------------------------- eventos
    def clic(self, pos):
        for rect, accion in reversed(self._botones):
            if rect.collidepoint(pos):
                self.sonar("click")
                accion()
                return True
        return False

    def tecla(self, e):
        """Devuelve False para cerrar el juego."""
        if self.estado == "ajustes" and self.esperando:
            self.asignar_tecla(e)
            return True
        if e.key == pygame.K_ESCAPE:
            if self.estado == "menu":
                return False
            self.volver_menu()
            return True
        enter = e.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
        if self.estado == "menu":
            if enter:
                self.sonar("click")
                self.iniciar_conteo()
            elif e.key == self.cod["reglas"]:
                self.abrir_reglas()
        elif self.estado == "reglas":
            if enter:
                self.iniciar_conteo()
            elif e.key == self.cod["reglas"]:
                self.repetir_reglas()
        elif self.estado == "conteo":
            if e.key == self.cod["reiniciar"]:
                self.volver_menu()
        elif self.estado == "juego":
            if e.key == self.cod["mujeres"]:
                self.sumar("m")
            elif e.key == self.cod["hombres"]:
                self.sumar("h")
            elif e.key == self.cod["reiniciar"]:
                self.volver_menu()
        elif self.estado == "victoria":
            if enter or e.key == self.cod["reiniciar"]:
                self.siguiente_ronda()
        elif self.estado == "final":
            if enter or e.key == self.cod["reiniciar"]:
                self.volver_menu()
        return True

    def eventos(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            if e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                self.alternar_pantalla()
                continue
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                self.clic(e.pos)
                continue
            if self.estado == "editor":
                self.ev_editor(e)
                continue
            if e.type == pygame.KEYDOWN:
                if self.estado == "juego" and self.cfg["modo_control"] == "pulsador":
                    if e.key == self.cod["mujeres"]: self.sumar("m")
                    elif e.key == self.cod["hombres"]: self.sumar("h")
                    elif e.key == self.cod["reiniciar"]: self.volver_menu()
                    continue
                if self.tecla(e) is False:
                    return False
        return True

    # ---------------------------------------------------------------- update
    def actualizar(self, dt):
        self.t += dt
        if self.estado == "juego":
            # La barra viaja suavemente hacia la nueva posición ganada:
            # cada bloque de 5 pulsaciones se siente como un forcejeo, no un salto.
            diferencia = self.barra_objetivo - self.barra_pos
            paso = min(abs(diferencia), 0.085 * dt)
            if diferencia > 0:
                self.barra_pos += paso
            elif diferencia < 0:
                self.barra_pos -= paso
            if self.barra_pos <= 0.015:
                self.barra_pos = 0.015
                self.finalizar_ronda("m")
            elif self.barra_pos >= 0.985:
                self.barra_pos = 0.985
                self.finalizar_ronda("h")
            self.tiempo_restante -= dt
            if self.tiempo_restante <= 0:
                if self.tiempo_extra <= 0 and abs(self.barra_pos - 0.5) < 0.002:
                    self.tiempo_extra = 10.0
                elif self.tiempo_extra > 0:
                    self.tiempo_extra -= dt
                    if self.tiempo_extra <= 0:
                        self.finalizar_ronda("m" if self.barra_pos < 0.5 else "h" if self.barra_pos > 0.5 else (self.ultimo_empuje or "m"))
                else:
                    self.finalizar_ronda("m" if self.barra_pos < 0.5 else "h")
        self.pulso_m = max(0.0, self.pulso_m - dt)
        self.pulso_h = max(0.0, self.pulso_h - dt)
        self.mensaje_fuerza_t = max(0.0, self.mensaje_fuerza_t - dt)
        if self.mensaje_fuerza_t <= 0:
            self.mensaje_fuerza = ""
        if self.mensaje_t > 0:
            self.mensaje_t -= dt
            if self.mensaje_t <= 0:
                self.mensaje = ""
        if self.confirmar_t > 0:
            self.confirmar_t -= dt
        for c in self.confeti:
            c[0] += c[2] * dt
            c[1] += c[3] * dt
            if c[1] > ALTO + 20:
                c[1] = random.uniform(-80, -10)
                c[0] = random.uniform(0, ANCHO)

        if self.estado == "conteo":
            self.t_conteo += dt
            paso = int(self.t_conteo)
            if paso != self.ultimo_paso and paso <= 3:
                self.ultimo_paso = paso
                self.sonar("conteo" if paso < 3 else "inicio")
            if self.t_conteo >= 3.9:
                self.estado = "juego"

        habla = self.estado == "reglas" and self.voz.hablando()
        if habla != self._duck:
            self._duck = habla
            self.aplicar_volumen()

    # ---------------------------------------------------------------- dibujo: utilidades
    def boton(self, rect, txt, accion, color=(40, 60, 120), fnt=None):
        rect = pygame.Rect(rect)
        hover = rect.collidepoint(pygame.mouse.get_pos())
        col = tuple(min(255, c + 45) for c in color) if hover else color
        p = self.pantalla
        pygame.draw.rect(p, NEGRO, rect.move(3, 4), border_radius=12)
        pygame.draw.rect(p, col, rect, border_radius=12)
        pygame.draw.rect(p, BLANCO, rect, 3, border_radius=12)
        fnt = fnt or fuente_ajustada(txt, rect.width - 16, 24)
        escribir(p, txt, fnt, BLANCO, rect.center, sombra=False)
        self._btn_nuevos.append((rect, accion))

    def dibujar_aviso(self, y):
        if self.mensaje:
            escribir(self.pantalla, self.mensaje, fuente(26, False), DORADO, (ANCHO // 2, y))

    # ---------------------------------------------------------------- dibujo: menu
    def dibujar_menu(self):
        p = self.pantalla
        n1, n2 = self.nombres()
        if self.img_bienv:
            p.blit(self.img_bienv, (0, 0))
            p.blit(self.velo, (0, 0))
        else:
            p.blit(self.fondo_neon, (0, 0))
            for x, y, r in ((90, 330, 40), (230, 260, 24), (ANCHO - 90, 330, 40), (ANCHO - 230, 260, 24)):
                estrella(p, (x, y + math.sin(self.t * 2 + x) * 7), r, BLANCO)
            escribir(p, "BATALLA DE FUERZA", fuente(80), DORADO, (ANCHO // 2, 62))
            for nombre, cx, osc in ((n2, ANCHO // 4, AZUL_OSC), (n1, 3 * ANCHO // 4, ROSA_OSC)):
                r = pygame.Rect(0, 0, 440, 100)
                r.center = (cx, 190)
                pygame.draw.rect(p, osc, r, border_radius=28)
                pygame.draw.rect(p, BLANCO, r, 5, border_radius=28)
                escribir(p, nombre, fuente_ajustada(nombre, 400, 62), BLANCO, r.center)
            esc = 1.0 + 0.06 * math.sin(self.t * 5)
            vs = pygame.transform.rotozoom(fuente(110).render("VS", True, DORADO), 0, esc)
            sh = pygame.transform.rotozoom(fuente(110).render("VS", True, NEGRO), 0, esc)
            p.blit(sh, sh.get_rect(center=(ANCHO // 2 + 5, 205)))
            p.blit(vs, vs.get_rect(center=(ANCHO // 2, 200)))
        if int(self.t * 2) % 2 == 0:
            escribir(p, "PRESIONA ENTER PARA INICIAR", fuente(66), BLANCO, (ANCHO // 2, 400))
        y = 500
        self.boton((60, y, 270, 62), "JUGAR  (ENTER)", self.iniciar_conteo, VERDE)
        self.boton((350, y, 270, 62), "REGLAS  (%s)" % self.nombre_tecla("reglas"), self.abrir_reglas)
        self.boton((640, y, 270, 62), "AJUSTES", self.abrir_ajustes)
        self.boton((930, y, 290, 62),
                   "PANTALLA COMPLETA" if not self.cfg["pantalla_completa"] else "SALIR PANT. COMPLETA",
                   self.alternar_pantalla)
        info = "%s: [%s]     %s: [%s]     REINICIAR: [%s]     F11: pantalla completa" % (
            n1, self.nombre_tecla("mujeres"), n2, self.nombre_tecla("hombres"),
            self.nombre_tecla("reiniciar"))
        escribir(p, info, fuente(24, False), BLANCO, (ANCHO // 2, 630))

    # ---------------------------------------------------------------- dibujo: reglas
    def dibujar_reglas(self):
        p = self.pantalla
        p.blit(self.fondo_oscuro, (0, 0))
        escribir(p, "REGLAS DEL JUEGO", fuente(64), DORADO, (ANCHO // 2, 60))
        caja = pygame.Rect(90, 115, ANCHO - 180, 450)
        pygame.draw.rect(p, (20, 20, 52), caja, border_radius=24)
        pygame.draw.rect(p, BLANCO, caja, 4, border_radius=24)
        fnt, lineas, inter = ajustar_texto(self.reglas_formateadas(), caja.width - 70, caja.height - 50)
        restantes = int(max(0.0, self.t - self.reglas_t0 - 0.6) * 16)
        dibujar_parrafo(p, lineas, fnt, caja.x + 35, caja.y + 25, inter, BLANCO, restantes)
        y = 600
        self.boton((90, y, 260, 62), "VOLVER (ESC)", self.volver_menu)
        self.boton((380, y, 340, 62), "REPETIR VOZ (%s)" % self.nombre_tecla("reglas"), self.repetir_reglas)
        self.boton((750, y, 440, 62), "¡JUGAR! (ENTER)", self.iniciar_conteo, VERDE)

    # ---------------------------------------------------------------- dibujo: ajustes
    def dibujar_ajustes(self):
        p = self.pantalla
        n1, n2 = self.nombres()
        p.blit(self.fondo_oscuro, (0, 0))
        escribir(p, "AJUSTES DEL JUEGO", fuente(48), DORADO, (ANCHO // 2, 38))

        # Paneles separados para que cada función se lea con claridad.
        panel_izq = pygame.Rect(28, 82, 600, 520)
        panel_der = pygame.Rect(648, 82, 604, 520)
        for caja in (panel_izq, panel_der):
            pygame.draw.rect(p, (20, 25, 58), caja, border_radius=18)
            pygame.draw.rect(p, (125, 145, 210), caja, 2, border_radius=18)

        escribir(p, "CONTROLES Y PARTIDA", fuente(27), ROSA, (panel_izq.centerx, 108))
        escribir(p, "PERSONALIZACIÓN", fuente(27), AZUL, (panel_der.centerx, 108))
        fe = fuente(20, False)
        y0, paso = 145, 43
        xl = 48

        controles = [
            ("mujeres", "Botón / tecla " + n1),
            ("hombres", "Botón / tecla " + n2),
            ("reiniciar", "Reiniciar partida"),
            ("reglas", "Leer reglas"),
        ]
        for i, (k, etq) in enumerate(controles):
            y = y0 + i * paso
            escribir(p, etq, fe, BLANCO, (xl, y + 20), sombra=False, alin="midleft")
            espera = self.esperando == k
            txt = "PRESIONA..." if espera else self.nombre_tecla(k)
            self.boton((xl + 300, y, 235, 38), txt, lambda k=k: self.esperar_tecla(k),
                       (190, 105, 0) if espera else (40, 60, 120), fuente(19))

        y = y0 + 4 * paso
        escribir(p, "Tipo de control", fe, BLANCO, (xl, y + 20), sombra=False, alin="midleft")
        self.boton((xl + 300, y, 235, 38), self.cfg["modo_control"].upper(),
                   self.cambiar_modo_control, VERDE, fuente(19))
        y += paso
        escribir(p, "Fuerza de empuje", fe, BLANCO, (xl, y + 20), sombra=False, alin="midleft")
        self.boton((xl + 300, y, 48, 38), "-", lambda: self.cambiar_velocidad(-0.2), fnt=fuente(22))
        escribir(p, "%.1fx" % self.cfg.get("velocidad_barra", 1.0), fuente(23), DORADO,
                 (xl + 412, y + 19))
        self.boton((xl + 476, y, 48, 38), "+", lambda: self.cambiar_velocidad(0.2), fnt=fuente(22))
        y += paso
        escribir(p, "Nombre equipo rosa", fe, BLANCO, (xl, y + 20), sombra=False, alin="midleft")
        self.boton((xl + 300, y, 235, 38), n1, lambda: self.editar_nombre(0), (170, 20, 110), fuente(18))
        y += paso
        escribir(p, "Nombre equipo azul", fe, BLANCO, (xl, y + 20), sombra=False, alin="midleft")
        self.boton((xl + 300, y, 235, 38), n2, lambda: self.editar_nombre(1), (15, 50, 160), fuente(18))
        y += paso
        escribir(p, "Texto y voz de reglas", fe, BLANCO, (xl, y + 20), sombra=False, alin="midleft")
        self.boton((xl + 300, y, 235, 38), "EDITAR REGLAS", self.editar_reglas, fnt=fuente(18))
        y += paso
        escribir(p, "Pantalla completa", fe, BLANCO, (xl, y + 20), sombra=False, alin="midleft")
        self.boton((xl + 300, y, 235, 38), "ACTIVADA" if self.cfg["pantalla_completa"] else "DESACTIVADA",
                   self.alternar_pantalla, VERDE if self.cfg["pantalla_completa"] else (90, 40, 40), fuente(17))

        xr = 668
        filas = [
            ("bienvenida", "Imagen de bienvenida", "img"),
            ("img_m", "Personaje equipo rosa", "img"),
            ("img_h", "Personaje equipo azul", "img"),
            ("fondo_m", "Fondo equipo rosa", "img"),
            ("fondo_h", "Fondo equipo azul", "img"),
            ("musica_fondo", "Música durante el juego", "aud"),
            ("victoria_img_h", "Imagen victoria hombres", "img"),
            ("victoria_img_m", "Imagen victoria mujeres", "img"),
            ("rayo_super_fuerza", "Imagen efecto SUPER FUERZA", "img"),
            ("musica_vic_m", "Música victoria mujeres", "aud"),
            ("musica_vic_h", "Música victoria hombres", "aud"),
            ("sfx_click", "Sonido de pulsación", "aud"),
            ("sfx_conteo", "Sonido de cuenta", "aud"),
            ("sfx_inicio", "Sonido de inicio", "aud"),
        ]
        for i, (k, etq, tipo) in enumerate(filas):
            y = 143 + i * 31
            custom = k in self.cfg["archivos"]
            escribir(p, etq + ("  ✓" if custom else ""), fuente(18, False),
                     DORADO if custom else BLANCO, (xr, y + 19), sombra=False, alin="midleft")
            self.boton((xr + 345, y, 92, 28), "CAMBIAR", lambda k=k, t=tipo: self.elegir_archivo(k, t),
                       (40, 70, 125), fuente(14))
            self.boton((xr + 444, y, 92, 28), "ORIGINAL", lambda k=k: self.archivo_original(k),
                       (100, 45, 55), fuente(13))

        if self.mensaje:
            escribir(p, self.mensaje, fuente(18, False), DORADO, (ANCHO // 2, 613))
        escribir(p, "✓ = archivo personalizado", fuente(16, False), (200, 200, 220),
                 (ANCHO // 2, 635), sombra=False)
        self.boton((35, 660, 330, 46), "ABRIR CARPETA PERSONALIZADA", self.abrir_carpeta, fnt=fuente(16))
        self.boton((390, 660, 250, 46), "RESTAURAR TODO", self.restaurar_todo, (140, 40, 40), fuente(17))
        self.boton((665, 660, 580, 46), "VOLVER AL MENÚ", self.volver_menu, VERDE, fuente(20))

    # ---------------------------------------------------------------- dibujo: editor
    def dibujar_editor(self):
        p = self.pantalla
        ed = self.editor
        p.blit(self.fondo_oscuro, (0, 0))
        caja = pygame.Rect(110, 90, ANCHO - 220, 460)
        pygame.draw.rect(p, (20, 20, 52), caja, border_radius=24)
        pygame.draw.rect(p, BLANCO, caja, 4, border_radius=24)
        escribir(p, ed["titulo"], fuente_ajustada(ed["titulo"], caja.width - 40, 34), DORADO,
                 (ANCHO // 2, 55))
        cursor = "|" if int(self.t * 2) % 2 == 0 else " "
        f = fuente(30, False)
        lineas = envolver(ed["texto"] + cursor, f, caja.width - 60)
        inter = 40
        max_lineas = (caja.height - 40) // inter
        for i, ln in enumerate(lineas[-max_lineas:]):
            p.blit(f.render(ln, True, BLANCO), (caja.x + 30, caja.y + 22 + i * inter))
        ayuda = "Escribe el texto. " + ("ENTER = salto de línea, CTRL+ENTER = aceptar." if ed["multi"]
                                       else "ENTER = aceptar.") + " ESC = cancelar. CTRL+V = pegar."
        escribir(p, ayuda, fuente(20, False), (210, 210, 230), (ANCHO // 2, 580), sombra=False)
        self.boton((110, 620, 300, 60), "ACEPTAR", lambda: self.cerrar_editor(True), VERDE)
        self.boton((440, 620, 400, 60), "BORRAR TODO", lambda: ed.__setitem__("texto", ""), (140, 40, 40))
        self.boton((870, 620, 300, 60), "CANCELAR", lambda: self.cerrar_editor(False))

    # ---------------------------------------------------------------- dibujo: juego
    def adorno(self, clave, x, y, fase, derecha=False):
        img = self.adornos.get(clave)
        if not img:
            return
        yy = y + math.sin(self.t * 2.2 + fase) * 8
        xx = x - img.get_width() if derecha else x
        self.pantalla.blit(img, (xx, yy))

    def dibujar_campo(self, div):
        p = self.pantalla
        rosa = self.fondo_m_custom or self.bg_rosa
        azul = self.fondo_h_custom or self.bg_azul
        p.blit(azul, (0, 0), pygame.Rect(0, 0, div, ALTO))
        p.blit(rosa, (div, 0), pygame.Rect(div, 0, ANCHO - div, ALTO))

    def dibujar_nombres(self):
        n1, n2 = self.nombres()
        p = self.pantalla
        escribir(p, n2, fuente_ajustada(n2, 420, 58), BLANCO, (30, 98), alin="midleft")
        escribir(p, n1, fuente_ajustada(n1, 420, 58), BLANCO, (ANCHO - 30, 98), alin="midright")

    def dibujar_juego(self):
        p = self.pantalla
        n1, n2 = self.nombres()
        div = int(ANCHO * self.barra_pos)
        self.dibujar_campo(div)
        pygame.draw.rect(p, BLANCO, (div - 10, 0, 20, ALTO))

        self.adorno("adorno_h1", 60, 230, 0.9)
        self.adorno("adorno_h2", 100, 420, 2.4)
        self.adorno("adorno_m1", ANCHO - 60, 230, 0.0, True)
        self.adorno("adorno_m2", ANCHO - 100, 420, 1.7, True)

        # Animación de embestida: cada pulsación hace que el personaje avance
        # físicamente hacia el rival y regrese suavemente a su posición.
        fuerza_m = math.sin(min(1.0, self.pulso_m / 0.25) * math.pi / 2) * 30
        fuerza_h = math.sin(min(1.0, self.pulso_h / 0.25) * math.pi / 2) * 30
        sacudida_m = math.sin(self.t * 40) * 3 if self.pulso_m > 0 else 0
        sacudida_h = math.sin(self.t * 40) * 3 if self.pulso_h > 0 else 0
        im = self.img.get("img_m_j")
        ih = self.img.get("img_h_j")
        if ih:
            p.blit(ih, (div - 12 - ih.get_width() + fuerza_h + sacudida_h, ALTO - ih.get_height() + 12))
        if im:
            p.blit(im, (div + 12 - fuerza_m + sacudida_m, ALTO - im.get_height() + 12))

        self.dibujar_nombres()

        # contador superior
        pill = pygame.Rect(0, 0, 360, 70)
        pill.center = (ANCHO // 2, 46)
        pygame.draw.rect(p, (20, 20, 44), pill, border_radius=30)
        pygame.draw.rect(p, BLANCO, pill, 4, border_radius=30)
        escribir(p, "RONDA %d/5" % self.ronda, fuente(25), DORADO, (ANCHO // 2, 96))
        reloj_txt = "PRORROGA %02d" % max(0, int(self.tiempo_extra)) if self.tiempo_extra > 0 else "TIEMPO %02d" % max(0, int(self.tiempo_restante))
        escribir(p, reloj_txt, fuente(28), BLANCO, (ANCHO // 2, 130))
        escribir(p, "SERIE %d - %d" % (self.puntos_ronda["m"], self.puntos_ronda["h"]), fuente(22), DORADO, (ANCHO // 2, 160))

        # Indicadores de control: se muestran las teclas, nunca un conteo de pulsaciones.
        escribir(p, "EMPUJA", fuente(25), BLANCO, (190, ALTO - 48))
        escribir(p, "[%s]" % self.nombre_tecla("mujeres"), fuente(22), BLANCO, (190, ALTO - 18))
        escribir(p, "EMPUJA", fuente(25), BLANCO, (ANCHO - 190, ALTO - 48))
        escribir(p, "[%s]" % self.nombre_tecla("hombres"), fuente(22), BLANCO, (ANCHO - 190, ALTO - 18))

        if self.mensaje_fuerza_t > 0:
            # Efecto en la franja inferior para no tapar a los jugadores.
            centro_y = ALTO - 78
            if self.rayo_super_fuerza:
                rayo = self.rayo_super_fuerza
                factor = 1.0 + 0.08 * math.sin(self.t * 24)
                rw = max(1, int(rayo.get_width() * factor))
                rh = max(1, int(rayo.get_height() * factor))
                rayo = pygame.transform.smoothscale(rayo, (rw, rh))
                p.blit(rayo, rayo.get_rect(center=(ANCHO // 2, ALTO - 175)))
            else:
                # Rayo dorado predeterminado dibujado con vectores.
                puntos = [(ANCHO//2-18, ALTO-250), (ANCHO//2+18, ALTO-250),
                          (ANCHO//2+2, ALTO-207), (ANCHO//2+28, ALTO-207),
                          (ANCHO//2-22, ALTO-145), (ANCHO//2-8, ALTO-193),
                          (ANCHO//2-32, ALTO-193)]
                pygame.draw.polygon(p, (255, 150, 20), puntos)
                pygame.draw.polygon(p, (255, 235, 90), puntos, 5)
            escala = 1.0 + 0.07 * math.sin(self.t * 24)
            texto = fuente(42).render(self.mensaje_fuerza, True, DORADO)
            texto = pygame.transform.rotozoom(texto, 0, escala)
            sombra = fuente(42).render(self.mensaje_fuerza, True, NEGRO)
            sombra = pygame.transform.rotozoom(sombra, 0, escala)
            rect = texto.get_rect(center=(ANCHO // 2, centro_y))
            fondo = rect.inflate(38, 18)
            pygame.draw.rect(p, (18, 12, 38), fondo, border_radius=16)
            pygame.draw.rect(p, DORADO, fondo, 3, border_radius=16)
            p.blit(sombra, sombra.get_rect(center=(rect.centerx + 3, rect.centery + 3)))
            p.blit(texto, rect)

        self.boton((ANCHO - 200, 12, 185, 42), "REINICIAR (%s)" % self.nombre_tecla("reiniciar"),
                   self.volver_menu, (200, 40, 60), fuente(18))

    def dibujar_conteo(self):
        p = self.pantalla
        self.dibujar_campo(ANCHO // 2)
        pygame.draw.rect(p, BLANCO, (ANCHO // 2 - 10, 0, 20, ALTO))
        self.dibujar_nombres()
        paso = min(3, int(self.t_conteo))
        frac = self.t_conteo - int(self.t_conteo)
        esc = 1.7 - 0.7 * min(1.0, frac * 2.0)
        if paso < 3:
            txt, tam, col = str(3 - paso), 360, BLANCO
        else:
            txt, tam, col = "¡INICIAMOS!", 150, DORADO
        base = fuente(tam)
        s = pygame.transform.rotozoom(base.render(txt, True, col), 0, esc)
        sh = pygame.transform.rotozoom(base.render(txt, True, NEGRO), 0, esc)
        p.blit(sh, sh.get_rect(center=(ANCHO // 2 + 8, ALTO // 2 + 8)))
        p.blit(s, s.get_rect(center=(ANCHO // 2, ALTO // 2)))
        self.boton((ANCHO - 200, 12, 185, 42), "REINICIAR (%s)" % self.nombre_tecla("reiniciar"),
                   self.volver_menu, (200, 40, 60), fuente(18))

    def dibujar_victoria(self):
        p = self.pantalla
        gana_m = self.ganador == "m"
        fondo_ganador = self.victoria_img_m if gana_m else self.victoria_img_h
        p.blit(fondo_ganador if fondo_ganador else (self.bg_rosa if gana_m else self.bg_azul), (0, 0))
        for c in self.confeti:
            pygame.draw.rect(p, c[4], (c[0], c[1], c[5], c[5] * 1.6))
        img = self.img.get("img_m_g" if gana_m else "img_h_g")
        if img:
            if gana_m:
                p.blit(img, (20, ALTO - img.get_height() + 10))
            else:
                p.blit(img, (ANCHO - img.get_width() - 20, ALTO - img.get_height() + 10))
        self.dibujar_nombres()
        nombre = self.nombres()[0 if gana_m else 1]
        msg = self.cfg["texto_gana"].replace("{EQUIPO}", nombre)
        esc = 1.0 + 0.04 * math.sin(self.t * 6)
        f = fuente_ajustada(msg, ANCHO - 140, 120, 40)
        s = pygame.transform.rotozoom(f.render(msg, True, BLANCO), 0, esc)
        sh = pygame.transform.rotozoom(f.render(msg, True, NEGRO), 0, esc)
        p.blit(sh, sh.get_rect(center=(ANCHO // 2 + 6, 250 + 6)))
        p.blit(s, s.get_rect(center=(ANCHO // 2, 250)))
        escribir(p, "RONDA GANADA", fuente(64), DORADO, (ANCHO // 2, 420))
        if int(self.t * 2) % 2 == 0:
            m = "PRESIONA [%s] PARA SIGUIENTE RONDA" % self.nombre_tecla("reiniciar")
            escribir(p, m, fuente_ajustada(m, ANCHO - 200, 52), BLANCO, (ANCHO // 2, 600))
        self.boton((ANCHO - 200, 12, 185, 42), "SIGUIENTE RONDA",
                   self.siguiente_ronda, (200, 40, 60), fuente(18))

    def dibujar_final(self):
        p = self.pantalla
        p.blit(self.fondo_oscuro, (0, 0))
        m, h = self.puntos_ronda["m"], self.puntos_ronda["h"]
        escribir(p, "TORNEO TERMINADO", fuente(72), DORADO, (ANCHO // 2, 145))
        escribir(p, "%s  %d  -  %d  %s" % (self.nombres()[0], m, h, self.nombres()[1]), fuente_ajustada("RESULTADO", ANCHO - 100, 56), BLANCO, (ANCHO // 2, 300))
        resultado = "EMPATE" if self.ganador is None else self.nombres()[0 if self.ganador == "m" else 1] + " GANAN EL TORNEO"
        escribir(p, resultado, fuente(52), DORADO, (ANCHO // 2, 420))
        self.boton((ANCHO // 2 - 180, 560, 360, 70), "NUEVO TORNEO", self.volver_menu, VERDE)

    # ---------------------------------------------------------------- loop
    def dibujar(self):
        self._btn_nuevos = []
        est = self.estado
        if est == "menu":
            self.dibujar_menu()
        elif est == "reglas":
            self.dibujar_reglas()
        elif est == "ajustes":
            self.dibujar_ajustes()
        elif est == "editor":
            self.dibujar_editor()
        elif est == "conteo":
            self.dibujar_conteo()
        elif est == "juego":
            self.dibujar_juego()
        elif est == "final":
            self.dibujar_final()
        else:
            self.dibujar_victoria()
        self._botones = self._btn_nuevos

    def ejecutar(self):
        corriendo = True
        while corriendo:
            dt = self.reloj.tick(FPS) / 1000.0
            corriendo = self.eventos()
            self.actualizar(dt)
            self.dibujar()
            pygame.display.flip()
        self.voz.parar()
        guardar_config(self.cfg)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Juego().ejecutar()
