"""
BATALLA DE FUERZA - Mujeres vs Hombres
Python 3.10+ / Pygame

Controles:
    ENTER  -> iniciar (menu) / volver al menu (pantalla de victoria)
    A      -> suma 1 punto a MUJERES
    L      -> suma 1 punto a HOMBRES
    Clic en "REINICIAR" (arriba a la derecha) -> vuelve al menu
    ESC    -> volver al menu / salir desde el menu
"""
import math
import os
import random
import sys

import pygame

ANCHO, ALTO = 1280, 720
FPS = 60
META = 30

ROSA = (255, 92, 184)
ROSA_OSC = (170, 20, 110)
AZUL = (60, 150, 255)
AZUL_OSC = (15, 50, 160)
BLANCO = (255, 255, 255)
NEGRO = (0, 0, 0)
DORADO = (255, 205, 40)
FONDO_MENU = (14, 14, 24)


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def ruta(rel):
    """Ruta absoluta compatible con PyInstaller (--onefile)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def cargar_imagen(rel, alto):
    try:
        img = pygame.image.load(ruta(rel)).convert_alpha()
        esc = alto / img.get_height()
        return pygame.transform.smoothscale(img, (int(img.get_width() * esc), alto))
    except Exception:
        return None


def cargar_sonido(rel, vol=0.8):
    try:
        s = pygame.mixer.Sound(ruta(rel))
        s.set_volume(vol)
        return s
    except Exception:
        return None


def reproducir_musica(rel, loops=-1, vol=0.5):
    try:
        pygame.mixer.music.load(ruta(rel))
        pygame.mixer.music.set_volume(vol)
        pygame.mixer.music.play(loops)
    except Exception:
        pass


def parar_musica():
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass


def fuente(tam):
    return pygame.font.SysFont("arialblack,arial,verdana", tam, bold=True)


def texto(sup, txt, fnt, color, centro, sombra=True, off=4):
    if sombra:
        s = fnt.render(txt, True, NEGRO)
        sup.blit(s, s.get_rect(center=(centro[0] + off, centro[1] + off)))
    t = fnt.render(txt, True, color)
    r = t.get_rect(center=centro)
    sup.blit(t, r)
    return r


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
        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        self.reloj = pygame.time.Clock()

        self.f_titulo = fuente(96)
        self.f_menu = fuente(70)
        self.f_lado = fuente(64)
        self.f_num = fuente(150)
        self.f_num_g = fuente(180)
        self.f_vs = fuente(110)
        self.f_peq = fuente(28)
        self.f_btn = fuente(26)
        self.f_gana = fuente(110)

        self.bg_rosa = degradado(ANCHO // 2, ALTO, (255, 120, 205), ROSA_OSC)
        self.bg_azul = degradado(ANCHO // 2, ALTO, (90, 190, 255), AZUL_OSC)

        self.img_chica = cargar_imagen("assets/images/chica.png", 360)
        self.img_chico = cargar_imagen("assets/images/chico.png", 360)
        self.img_chica_g = cargar_imagen("assets/images/chica.png", 520)
        self.img_chico_g = cargar_imagen("assets/images/chico.png", 520)

        self.snd_click = cargar_sonido("assets/sfx/click.wav")

        self.boton = pygame.Rect(ANCHO - 220, 18, 200, 54)

        self.estado = "menu"
        self.t = 0.0
        self.mujeres = 0
        self.hombres = 0
        self.barra_pos = 0.5
        self.pulso_m = 0.0
        self.pulso_h = 0.0
        self.ganador = None
        self.confeti = []
        self.musica_actual = None
        self.poner_musica("fondo")

    # ---------------------------------------------------------------- audio
    def poner_musica(self, cual):
        if self.musica_actual == cual:
            return
        self.musica_actual = cual
        if cual == "fondo":
            reproducir_musica("assets/music/fondo.mp3", loops=-1, vol=0.45)
        elif cual == "victoria":
            reproducir_musica("assets/music/victoria.mp3", loops=0, vol=0.7)
        else:
            parar_musica()

    def click(self):
        if self.snd_click:
            try:
                self.snd_click.play()
            except Exception:
                pass

    # ---------------------------------------------------------------- logica
    def iniciar_partida(self):
        self.mujeres = 0
        self.hombres = 0
        self.barra_pos = 0.5
        self.pulso_m = self.pulso_h = 0.0
        self.ganador = None
        self.confeti = []
        self.estado = "juego"
        self.poner_musica("fondo")

    def volver_menu(self):
        self.estado = "menu"
        self.ganador = None
        self.confeti = []
        self.poner_musica(None)
        self.poner_musica("fondo")

    def sumar(self, quien):
        if self.estado != "juego":
            return
        self.click()
        if quien == "m":
            self.mujeres += 1
            self.pulso_m = 0.25
        else:
            self.hombres += 1
            self.pulso_h = 0.25
        if self.mujeres >= META or self.hombres >= META:
            self.ganador = "m" if self.mujeres >= META else "h"
            self.estado = "victoria"
            self.poner_musica(None)
            self.poner_musica("victoria")
            self.crear_confeti()

    def crear_confeti(self):
        cols = [ROSA, AZUL, DORADO, BLANCO] if self.ganador is None else (
            [ROSA, BLANCO, DORADO] if self.ganador == "m" else [AZUL, BLANCO, DORADO])
        self.confeti = [
            [random.uniform(0, ANCHO), random.uniform(-ALTO, 0),
             random.uniform(-40, 40), random.uniform(120, 320),
             random.choice(cols), random.randint(6, 12)]
            for _ in range(160)
        ]

    # ---------------------------------------------------------------- eventos
    def eventos(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if self.estado == "menu":
                        return False
                    self.volver_menu()
                elif self.estado == "menu" and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.click()
                    self.iniciar_partida()
                elif self.estado == "juego":
                    if e.key == pygame.K_a:
                        self.sumar("m")
                    elif e.key == pygame.K_l:
                        self.sumar("h")
                elif self.estado == "victoria" and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.click()
                    self.volver_menu()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.estado != "menu" and self.boton.collidepoint(e.pos):
                    self.click()
                    self.volver_menu()
        return True

    # ---------------------------------------------------------------- update
    def actualizar(self, dt):
        self.t += dt
        objetivo = 0.5 + (self.mujeres - self.hombres) / (2.0 * META)
        objetivo = max(0.04, min(0.96, objetivo))
        self.barra_pos += (objetivo - self.barra_pos) * min(1.0, dt * 8)
        self.pulso_m = max(0.0, self.pulso_m - dt)
        self.pulso_h = max(0.0, self.pulso_h - dt)
        for c in self.confeti:
            c[0] += c[2] * dt
            c[1] += c[3] * dt
            if c[1] > ALTO + 20:
                c[1] = random.uniform(-80, -10)
                c[0] = random.uniform(0, ANCHO)

    # ---------------------------------------------------------------- dibujo
    def dibujar_boton(self):
        hover = self.boton.collidepoint(pygame.mouse.get_pos())
        col = (255, 90, 90) if hover else (220, 40, 60)
        pygame.draw.rect(self.pantalla, NEGRO, self.boton.move(3, 4), border_radius=14)
        pygame.draw.rect(self.pantalla, col, self.boton, border_radius=14)
        pygame.draw.rect(self.pantalla, BLANCO, self.boton, 3, border_radius=14)
        texto(self.pantalla, "REINICIAR", self.f_btn, BLANCO, self.boton.center, sombra=False)

    def dibujar_menu(self):
        p = self.pantalla
        p.fill(FONDO_MENU)
        # circulos suaves de ambiente
        for i, (col, ph) in enumerate(((ROSA_OSC, 0), (AZUL_OSC, 2))):
            cx = ANCHO * (0.25 if i == 0 else 0.75) + math.sin(self.t * 0.8 + ph) * 40
            cy = ALTO * 0.5 + math.cos(self.t * 0.6 + ph) * 30
            s = pygame.Surface((520, 520), pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, 70), (260, 260), 250)
            p.blit(s, (cx - 260, cy - 260))
        texto(p, "BATALLA DE FUERZA", self.f_titulo, DORADO, (ANCHO // 2, 190))
        texto(p, "MUJERES  vs  HOMBRES", self.f_lado, BLANCO, (ANCHO // 2, 290), sombra=False)
        if int(self.t * 2) % 2 == 0:
            texto(p, "PRESIONA ENTER PARA INICIAR", self.f_menu, BLANCO, (ANCHO // 2, 450))
        texto(p, "A = punto para MUJERES     L = punto para HOMBRES     Meta: %d" % META,
              self.f_peq, (200, 200, 220), (ANCHO // 2, 600), sombra=False)

    def caja_numero(self, rect, valor, color, color_osc, pulso):
        p = self.pantalla
        pygame.draw.rect(p, color_osc, rect, border_radius=34)
        pygame.draw.rect(p, BLANCO, rect, 6, border_radius=34)
        pygame.draw.rect(p, color, rect.inflate(-26, -26), 4, border_radius=26)
        f = self.f_num_g if pulso > 0 else self.f_num
        texto(p, str(valor), f, BLANCO, rect.center, off=6)

    def dibujar_juego(self):
        p = self.pantalla
        p.blit(self.bg_rosa, (0, 0))
        p.blit(self.bg_azul, (ANCHO // 2, 0))
        for x, y, r in ((90, 250, 36), (230, 170, 22), (ANCHO - 90, 250, 36), (ANCHO - 230, 170, 22)):
            estrella(p, (x, y + math.sin(self.t * 2 + x) * 6), r, BLANCO)

        # titulos
        for texto_lado, cx, col, osc in (("MUJERES", ANCHO // 4, ROSA, ROSA_OSC),
                                         ("HOMBRES", 3 * ANCHO // 4, AZUL, AZUL_OSC)):
            r = pygame.Rect(0, 0, 440, 100)
            r.center = (cx, 80)
            pygame.draw.rect(p, osc, r, border_radius=28)
            pygame.draw.rect(p, BLANCO, r, 5, border_radius=28)
            texto(p, texto_lado, self.f_lado, BLANCO, r.center)

        # personajes
        if self.img_chica:
            p.blit(self.img_chica, self.img_chica.get_rect(center=(ANCHO // 4 + 120, 345)))
        if self.img_chico:
            p.blit(self.img_chico, self.img_chico.get_rect(center=(3 * ANCHO // 4 - 120, 345)))

        # numeros
        rm = pygame.Rect(0, 0, 230, 230)
        rm.center = (130, 330)
        rh = pygame.Rect(0, 0, 230, 230)
        rh.center = (ANCHO - 130, 330)
        self.caja_numero(rm, self.mujeres, ROSA, ROSA_OSC, self.pulso_m)
        self.caja_numero(rh, self.hombres, AZUL, AZUL_OSC, self.pulso_h)

        # linea divisoria y VS
        pygame.draw.line(p, BLANCO, (ANCHO // 2, 140), (ANCHO // 2, 480), 3)
        esc = 1.0 + 0.06 * math.sin(self.t * 5)
        vs = self.f_vs.render("VS", True, DORADO)
        vs = pygame.transform.rotozoom(vs, 0, esc)
        sh = pygame.transform.rotozoom(self.f_vs.render("VS", True, NEGRO), 0, esc)
        p.blit(sh, sh.get_rect(center=(ANCHO // 2 + 5, 310 + 5)))
        p.blit(vs, vs.get_rect(center=(ANCHO // 2, 310)))

        # barra de fuerza central
        bx, by, bw, bh = 120, 560, ANCHO - 240, 62
        mx = bx + bw * self.barra_pos
        fondo = pygame.Rect(bx - 8, by - 8, bw + 16, bh + 16)
        pygame.draw.rect(p, NEGRO, fondo, border_radius=26)
        pygame.draw.rect(p, ROSA, (bx, by, mx - bx, bh), border_top_left_radius=20,
                         border_bottom_left_radius=20)
        pygame.draw.rect(p, AZUL, (mx, by, bx + bw - mx, bh), border_top_right_radius=20,
                         border_bottom_right_radius=20)
        pygame.draw.line(p, BLANCO, (bx + bw // 2, by - 14), (bx + bw // 2, by + bh + 14), 2)
        radio = 34 + int(3 * math.sin(self.t * 8))
        pygame.draw.circle(p, NEGRO, (int(mx) + 3, by + bh // 2 + 4), radio)
        pygame.draw.circle(p, DORADO, (int(mx), by + bh // 2), radio)
        pygame.draw.circle(p, BLANCO, (int(mx), by + bh // 2), radio, 5)
        estrella(p, (int(mx), by + bh // 2), 18, NEGRO, 0)
        pygame.draw.rect(p, BLANCO, fondo, 4, border_radius=26)
        texto(p, "BARRA DE FUERZA  -  META: %d PUNTOS" % META, self.f_peq, BLANCO,
              (ANCHO // 2, by + bh + 50))
        texto(p, "A = MUJERES", self.f_peq, BLANCO, (170, by + bh + 50), sombra=True)
        texto(p, "L = HOMBRES", self.f_peq, BLANCO, (ANCHO - 170, by + bh + 50), sombra=True)

        self.dibujar_boton()

    def dibujar_victoria(self):
        p = self.pantalla
        mujeres = self.ganador == "m"
        c1, c2 = ((255, 130, 210), ROSA_OSC) if mujeres else ((110, 195, 255), AZUL_OSC)
        p.blit(degradado(ANCHO, ALTO, c1, c2), (0, 0))
        for c in self.confeti:
            pygame.draw.rect(p, c[4], (c[0], c[1], c[5], c[5] * 1.6))
        img = self.img_chica_g if mujeres else self.img_chico_g
        if img:
            if mujeres:
                p.blit(img, (30, ALTO - img.get_height() + 10))
            else:
                p.blit(img, (ANCHO - img.get_width() - 30, ALTO - img.get_height() + 10))
        esc = 1.0 + 0.04 * math.sin(self.t * 6)
        msg = "¡MUJERES GANAN!" if mujeres else "¡HOMBRES GANAN!"
        s = pygame.transform.rotozoom(self.f_gana.render(msg, True, BLANCO), 0, esc)
        sh = pygame.transform.rotozoom(self.f_gana.render(msg, True, NEGRO), 0, esc)
        p.blit(sh, sh.get_rect(center=(ANCHO // 2 + 6, 250 + 6)))
        p.blit(s, s.get_rect(center=(ANCHO // 2, 250)))
        texto(p, "%d  -  %d" % (self.mujeres, self.hombres), self.f_num, DORADO, (ANCHO // 2, 440))
        texto(p, "MUJERES - HOMBRES", self.f_peq, BLANCO, (ANCHO // 2, 540), sombra=False)
        if int(self.t * 2) % 2 == 0:
            texto(p, "ENTER PARA VOLVER AL MENU", self.f_peq, BLANCO, (ANCHO // 2, 640))
        self.dibujar_boton()

    # ---------------------------------------------------------------- loop
    def ejecutar(self):
        corriendo = True
        while corriendo:
            dt = self.reloj.tick(FPS) / 1000.0
            corriendo = self.eventos()
            self.actualizar(dt)
            if self.estado == "menu":
                self.dibujar_menu()
            elif self.estado == "juego":
                self.dibujar_juego()
            else:
                self.dibujar_victoria()
            pygame.display.flip()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Juego().ejecutar()
