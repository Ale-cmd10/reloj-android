"""
Reloj de iOS — versión Android (Kivy)
=====================================
Clon del Reloj de iPhone con estética "Liquid Glass": fondo degradado,
tarjetas de cristal translúcido (alfa real), barra de pestañas inferior.

Funciones:
  1. Reloj mundial  — varias zonas horarias (añadir / eliminar).
  2. Alarma         — crear alarmas con interruptor; suenan a su hora (vibra).
  3. Cronómetro     — iniciar/parar/reiniciar + vueltas.
  4. Temporizador   — anillo de progreso y alerta al terminar.

Se empaqueta como APK con Buildozer (ver buildozer.spec).
También se puede previsualizar en PC:  python main.py
"""

from datetime import datetime, timezone, timedelta
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse, Rectangle
from kivy.graphics.texture import Texture
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.switch import Switch
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.utils import platform

# --- Vibración / sonido en Android (con respaldo en PC) --------------------
try:
    from plyer import vibrator, notification
except Exception:
    vibrator = None
    notification = None


def alerta(msg="Alarma"):
    try:
        if vibrator:
            vibrator.vibrate(0.6)
    except Exception:
        pass
    try:
        if notification:
            notification.notify(title="Reloj", message=msg, timeout=5)
    except Exception:
        pass


# --- Zonas horarias (zoneinfo + tzdata; respaldo offset fijo) --------------
ZONEINFO_OK = False
try:
    from zoneinfo import ZoneInfo
    try:
        ZoneInfo("America/New_York")
        ZONEINFO_OK = True
    except Exception:
        ZONEINFO_OK = False
except ImportError:
    ZoneInfo = None


def hora_zona(iana, fixed):
    """Devuelve (datetime_en_la_zona, offset_segundos)."""
    now_utc = datetime.now(timezone.utc)
    if ZONEINFO_OK:
        try:
            t = now_utc.astimezone(ZoneInfo(iana))
            return t, t.utcoffset().total_seconds()
        except Exception:
            pass
    t = now_utc + timedelta(hours=fixed)
    return t, fixed * 3600


CIUDADES = {
    "Cupertino": ("America/Los_Angeles", -8),
    "Nueva York": ("America/New_York", -5),
    "Ciudad de Mexico": ("America/Mexico_City", -6),
    "Bogota": ("America/Bogota", -5),
    "Lima": ("America/Lima", -5),
    "Santiago": ("America/Santiago", -4),
    "Buenos Aires": ("America/Argentina/Buenos_Aires", -3),
    "Sao Paulo": ("America/Sao_Paulo", -3),
    "Londres": ("Europe/London", 0),
    "Madrid": ("Europe/Madrid", 1),
    "Paris": ("Europe/Paris", 1),
    "Berlin": ("Europe/Berlin", 1),
    "Roma": ("Europe/Rome", 1),
    "Moscu": ("Europe/Moscow", 3),
    "Dubai": ("Asia/Dubai", 4),
    "Nueva Delhi": ("Asia/Kolkata", 5),
    "Bangkok": ("Asia/Bangkok", 7),
    "Pekin": ("Asia/Shanghai", 8),
    "Tokio": ("Asia/Tokyo", 9),
    "Sidney": ("Australia/Sydney", 11),
    "Auckland": ("Pacific/Auckland", 13),
}

# --- Paleta (rgba 0..1) — oscura y poco saturada ---------------------------
GRAD = [(0.035, 0.039, 0.055), (0.059, 0.067, 0.094),
        (0.086, 0.098, 0.133), (0.063, 0.071, 0.102),
        (0.039, 0.043, 0.063)]
BLANCO = (1, 1, 1, 1)
TENUE = (0.60, 0.63, 0.71, 1)
NARANJA = (1, 0.62, 0.04, 1)
VERDE = (0.19, 0.82, 0.35, 1)
ROJO = (1, 0.27, 0.23, 1)


def _interp(t):
    t = max(0.0, min(1.0, t))
    n = len(GRAD) - 1
    seg = t * n
    i = min(int(seg), n - 1)
    f = seg - i
    a, b = GRAD[i], GRAD[i + 1]
    return tuple(a[k] + (b[k] - a[k]) * f for k in range(3))


def gradiente_textura(altura=128):
    tex = Texture.create(size=(1, altura), colorfmt="rgba")
    buf = bytearray()
    for y in range(altura):
        r, g, b = _interp(y / (altura - 1))
        buf += bytes((int(r * 255), int(g * 255), int(b * 255), 255))
    tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    tex.wrap = "clamp_to_edge"
    return tex


# ===========================================================================
#  COMPONENTES DE CRISTAL
# ===========================================================================
class Glass(BoxLayout):
    """Tarjeta translúcida con esquinas redondeadas y borde brillante."""
    def __init__(self, radius=22, alpha=0.14, borde=0.35, base=(1, 1, 1),
                 **kw):
        super().__init__(**kw)
        self._r = dp(radius)
        with self.canvas.before:
            self._c = Color(base[0], base[1], base[2], alpha)
            self._rect = RoundedRectangle(radius=[self._r])
            self._bc = Color(1, 1, 1, borde)
            self._line = Line(width=1.1)
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *a):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._rect.radius = [self._r]
        x, y = self.pos
        w, h = self.size
        self._line.rounded_rectangle = (x, y, w, h, self._r)


class GButton(ButtonBehavior, Label):
    """Botón de cristal (o de color acento)."""
    def __init__(self, radius=22, accent=None, alpha=0.22, **kw):
        super().__init__(**kw)
        self._r = dp(radius)
        if accent:
            r, g, b = accent[0], accent[1], accent[2]
            a = 0.92
            bd = 0.25
        else:
            r, g, b, a, bd = 1, 1, 1, alpha, 0.45
        with self.canvas.before:
            self._c = Color(r, g, b, a)
            self._rect = RoundedRectangle(radius=[self._r])
            self._bc = Color(1, 1, 1, bd)
            self._line = Line(width=1.1)
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *a):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._rect.radius = [self._r]
        x, y = self.pos
        w, h = self.size
        self._line.rounded_rectangle = (x, y, w, h, self._r)


def auto_text(lbl):
    """Hace que text_size siga al tamaño del widget (alineado y responsive)."""
    lbl.bind(size=lambda w, *a: setattr(w, "text_size", w.size))
    return lbl


def titulo(texto):
    lbl = Label(text=texto, font_size="26sp", bold=True, color=BLANCO,
                halign="left", valign="middle", size_hint_y=None,
                height=dp(54))
    return auto_text(lbl)


# ===========================================================================
#  RELOJ MUNDIAL
# ===========================================================================
class PantallaMundial(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.ciudades = ["Cupertino", "Nueva York", "Londres", "Tokio"]
        self.filas = {}
        root = BoxLayout(orientation="vertical", padding=[dp(16), dp(10)],
                         spacing=dp(8))
        cab = BoxLayout(size_hint_y=None, height=dp(48))
        cab.add_widget(auto_text(Label(text="Reloj mundial", font_size="24sp",
                                       bold=True, color=BLANCO, halign="left",
                                       valign="middle")))
        mas = GButton(text="+", radius=18, font_size="22sp", color=BLANCO,
                      size_hint=(None, None), size=(dp(44), dp(44)))
        mas.bind(on_release=lambda *_: self.popup_anadir())
        cab.add_widget(mas)
        root.add_widget(cab)

        sv = ScrollView()
        self.lista = GridLayout(cols=1, spacing=dp(8), size_hint_y=None,
                                padding=[0, dp(4)])
        self.lista.bind(minimum_height=self.lista.setter("height"))
        sv.add_widget(self.lista)
        root.add_widget(sv)
        self.add_widget(root)

        self._construir()
        Clock.schedule_interval(self._tick, 1)

    def _construir(self):
        self.lista.clear_widgets()
        self.filas = {}
        for ciudad in self.ciudades:
            card = Glass(orientation="horizontal", size_hint_y=None,
                         height=dp(74), padding=[dp(16), dp(8)])
            izq = BoxLayout(orientation="vertical", size_hint_x=0.62)
            off = auto_text(Label(text="", font_size="11sp", color=TENUE,
                                  halign="left", valign="bottom"))
            nom = auto_text(Label(text=ciudad, font_size="20sp", color=BLANCO,
                                  halign="left", valign="top"))
            izq.add_widget(off)
            izq.add_widget(nom)
            card.add_widget(izq)
            hora = auto_text(Label(text="--:--", font_size="34sp", color=BLANCO,
                                   halign="right", valign="middle",
                                   size_hint_x=0.38))
            card.add_widget(hora)
            quitar = GButton(text="x", radius=14, font_size="16sp", color=ROJO,
                             size_hint=(None, 1), width=dp(34))
            quitar.bind(on_release=lambda *_a, c=ciudad: self._quitar(c))
            card.add_widget(quitar)
            self.lista.add_widget(card)
            self.filas[ciudad] = (off, hora)

    def _tick(self, *a):
        local = datetime.now(timezone.utc).astimezone()
        loff = local.utcoffset().total_seconds()
        ldate = local.date()
        for ciudad, (off, hora) in self.filas.items():
            iana, fixed = CIUDADES[ciudad]
            t, secs = hora_zona(iana, fixed)
            hora.text = t.strftime("%H:%M")
            dif = round((secs - loff) / 3600)
            dia = ("Manana" if t.date() > ldate
                   else "Ayer" if t.date() < ldate else "Hoy")
            off.text = f"{dia}, {'+' if dif >= 0 else ''}{dif} H"

    def _quitar(self, c):
        if c in self.ciudades and len(self.ciudades) > 1:
            self.ciudades.remove(c)
            self._construir()

    def popup_anadir(self):
        disp = [c for c in CIUDADES if c not in self.ciudades]
        if not disp:
            return
        cont = BoxLayout(orientation="vertical", spacing=dp(10),
                         padding=dp(12))
        sp = Spinner(text=disp[0], values=disp, size_hint_y=None, height=dp(44))
        cont.add_widget(sp)
        bo = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        pop = Popup(title="Anadir ciudad", content=cont,
                    size_hint=(0.85, None), height=dp(200))
        bcan = GButton(text="Cancelar", radius=12)
        bok = GButton(text="Anadir", radius=12, accent=NARANJA)
        bcan.bind(on_release=pop.dismiss)

        def add(*_):
            self.ciudades.append(sp.text)
            self._construir()
            pop.dismiss()
        bok.bind(on_release=add)
        bo.add_widget(bcan)
        bo.add_widget(bok)
        cont.add_widget(bo)
        pop.open()


# ===========================================================================
#  ALARMA
# ===========================================================================
class Alarma:
    def __init__(self, h, m, etq="Alarma", activa=True):
        self.h, self.m, self.etq, self.activa = h, m, etq, activa
        self.ultimo = None


class PantallaAlarma(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.alarmas = [Alarma(7, 0, "Despertador", False)]
        root = BoxLayout(orientation="vertical", padding=[dp(16), dp(10)],
                         spacing=dp(8))
        cab = BoxLayout(size_hint_y=None, height=dp(48))
        cab.add_widget(auto_text(Label(text="Alarma", font_size="24sp",
                                       bold=True, color=BLANCO, halign="left",
                                       valign="middle")))
        mas = GButton(text="+", radius=18, font_size="22sp", color=BLANCO,
                      size_hint=(None, None), size=(dp(44), dp(44)))
        mas.bind(on_release=lambda *_: self.popup_nueva())
        cab.add_widget(mas)
        root.add_widget(cab)

        sv = ScrollView()
        self.lista = GridLayout(cols=1, spacing=dp(8), size_hint_y=None,
                                padding=[0, dp(4)])
        self.lista.bind(minimum_height=self.lista.setter("height"))
        sv.add_widget(self.lista)
        root.add_widget(sv)
        self.add_widget(root)

        self._construir()
        Clock.schedule_interval(self._tick, 1)

    def _construir(self):
        self.lista.clear_widgets()
        for al in self.alarmas:
            card = Glass(orientation="horizontal", size_hint_y=None,
                         height=dp(80), padding=[dp(16), dp(8)])
            izq = BoxLayout(orientation="vertical")
            col = BLANCO if al.activa else TENUE
            izq.add_widget(auto_text(Label(text=f"{al.h:02d}:{al.m:02d}",
                                           font_size="36sp", color=col,
                                           halign="left", valign="bottom")))
            izq.add_widget(auto_text(Label(text=al.etq, font_size="12sp",
                                           color=TENUE, halign="left",
                                           valign="top")))
            card.add_widget(izq)
            sw = Switch(active=al.activa, size_hint_x=None, width=dp(80))
            sw.bind(active=lambda w, v, a=al: self._toggle(a, v))
            card.add_widget(sw)
            quitar = GButton(text="x", radius=14, font_size="16sp", color=ROJO,
                             size_hint=(None, 1), width=dp(34))
            quitar.bind(on_release=lambda *_a, a=al: self._quitar(a))
            card.add_widget(quitar)
            self.lista.add_widget(card)

    def _toggle(self, al, v):
        al.activa = v

    def _quitar(self, al):
        if al in self.alarmas:
            self.alarmas.remove(al)
            self._construir()

    def _tick(self, *a):
        ahora = datetime.now()
        clave = (ahora.date(), ahora.hour, ahora.minute)
        for al in self.alarmas:
            if (al.activa and al.h == ahora.hour and al.m == ahora.minute
                    and al.ultimo != clave):
                al.ultimo = clave
                alerta(f"{al.etq} {al.h:02d}:{al.m:02d}")

    def popup_nueva(self):
        ahora = datetime.now()
        cont = BoxLayout(orientation="vertical", spacing=dp(10),
                         padding=dp(12))
        fila = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        sh = Spinner(text=f"{ahora.hour:02d}",
                     values=[f"{i:02d}" for i in range(24)])
        sm = Spinner(text=f"{ahora.minute:02d}",
                     values=[f"{i:02d}" for i in range(60)])
        fila.add_widget(sh)
        fila.add_widget(Label(text=":", font_size="24sp", size_hint_x=None,
                              width=dp(16)))
        fila.add_widget(sm)
        cont.add_widget(fila)
        etq = TextInput(text="Alarma", multiline=False, size_hint_y=None,
                        height=dp(40))
        cont.add_widget(etq)
        bo = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        pop = Popup(title="Nueva alarma", content=cont, size_hint=(0.85, None),
                    height=dp(260))
        bcan = GButton(text="Cancelar", radius=12)
        bok = GButton(text="Guardar", radius=12, accent=NARANJA)
        bcan.bind(on_release=pop.dismiss)

        def add(*_):
            self.alarmas.append(Alarma(int(sh.text), int(sm.text),
                                       etq.text or "Alarma", True))
            self._construir()
            pop.dismiss()
        bok.bind(on_release=add)
        bo.add_widget(bcan)
        bo.add_widget(bok)
        cont.add_widget(bo)
        pop.open()


# ===========================================================================
#  CRONÓMETRO
# ===========================================================================
class PantallaCrono(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.corriendo = False
        self.acum = 0.0
        self.inicio = 0.0
        self.vueltas = []
        self.t_vuelta = 0.0

        root = BoxLayout(orientation="vertical", padding=[dp(16), dp(10)],
                         spacing=dp(10))
        root.add_widget(titulo("Cronometro"))
        self.lbl = Label(text="00:00.00", font_size="56sp", color=BLANCO,
                         size_hint_y=None, height=dp(150))
        root.add_widget(self.lbl)
        bo = BoxLayout(size_hint_y=None, height=dp(64), spacing=dp(30),
                       padding=[dp(20), 0])
        self.b_vuelta = GButton(text="Vuelta", radius=32, color=BLANCO)
        self.b_inicio = GButton(text="Iniciar", radius=32, accent=VERDE)
        self.b_vuelta.bind(on_release=lambda *_: self._vuelta())
        self.b_inicio.bind(on_release=lambda *_: self._iniciar_parar())
        bo.add_widget(self.b_vuelta)
        bo.add_widget(self.b_inicio)
        root.add_widget(bo)

        sv = ScrollView()
        self.laps = GridLayout(cols=1, spacing=dp(2), size_hint_y=None,
                               padding=[dp(8), dp(6)])
        self.laps.bind(minimum_height=self.laps.setter("height"))
        sv.add_widget(self.laps)
        root.add_widget(sv)
        self.add_widget(root)
        Clock.schedule_interval(self._tick, 1 / 30.)

    def _t(self):
        if self.corriendo:
            return self.acum + (time.perf_counter() - self.inicio)
        return self.acum

    @staticmethod
    def _fmt(s):
        return (f"{int(s // 60):02d}:{int(s % 60):02d}."
                f"{int((s - int(s)) * 100):02d}")

    def _iniciar_parar(self):
        if self.corriendo:
            self.acum = self._t()
            self.corriendo = False
            self.b_inicio.text = "Iniciar"
            self.b_inicio._c.rgba = VERDE
            self.b_vuelta.text = "Reiniciar"
        else:
            self.inicio = time.perf_counter()
            self.corriendo = True
            self.b_inicio.text = "Detener"
            self.b_inicio._c.rgba = ROJO
            self.b_vuelta.text = "Vuelta"

    def _vuelta(self):
        if self.corriendo:
            t = self._t()
            self.vueltas.append(t - self.t_vuelta)
            self.t_vuelta = t
            self._pintar_laps()
        else:
            self.acum = 0.0
            self.t_vuelta = 0.0
            self.vueltas = []
            self.b_vuelta.text = "Vuelta"
            self._pintar_laps()

    def _pintar_laps(self):
        self.laps.clear_widgets()
        if not self.vueltas:
            return
        rapida, lenta = min(self.vueltas), max(self.vueltas)
        for i, t in enumerate(reversed(self.vueltas)):
            num = len(self.vueltas) - i
            col = BLANCO
            if len(self.vueltas) > 1 and t == rapida:
                col = VERDE
            elif len(self.vueltas) > 1 and t == lenta:
                col = ROJO
            fila = BoxLayout(size_hint_y=None, height=dp(28))
            fila.add_widget(Label(text=f"Vuelta {num}", font_size="13sp",
                                  color=col, halign="left",
                                  text_size=(dp(140), None)))
            fila.add_widget(Label(text=self._fmt(t), font_size="14sp",
                                  color=col, halign="right",
                                  text_size=(dp(140), None)))
            self.laps.add_widget(fila)

    def _tick(self, *a):
        self.lbl.text = self._fmt(self._t())


# ===========================================================================
#  TEMPORIZADOR
# ===========================================================================
class Anillo(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.frac = 0.0
        with self.canvas:
            self._bc = Color(1, 1, 1, 0.28)
            self._base = Line(width=dp(5))
            self._pc = Color(*NARANJA)
            self._prog = Line(width=dp(5))
        self.bind(pos=self._upd, size=self._upd)

    def set_frac(self, f):
        self.frac = max(0.0, min(1.0, f))
        self._upd()

    def _upd(self, *a):
        cx = self.center_x
        cy = self.center_y
        r = min(self.width, self.height) / 2 - dp(6)
        self._base.circle = (cx, cy, r)
        self._prog.circle = (cx, cy, r, 0, 360 * self.frac)


class PantallaTimer(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.activo = False
        self.restante = 0.0
        self.total = 0.0
        self.ult = 0.0
        self.sel = [0, 5, 0]

        root = BoxLayout(orientation="vertical", padding=[dp(16), dp(10)],
                         spacing=dp(8))
        root.add_widget(titulo("Temporizador"))

        wrap = FloatLayout(size_hint_y=None, height=dp(230))
        self.anillo = Anillo(size_hint=(None, None), size=(dp(210), dp(210)),
                             pos_hint={"center_x": 0.5, "center_y": 0.5})
        wrap.add_widget(self.anillo)
        self.lbl = Label(text="05:00", font_size="40sp", color=BLANCO,
                         pos_hint={"center_x": 0.5, "center_y": 0.5})
        wrap.add_widget(self.lbl)
        root.add_widget(wrap)

        self.steppers = BoxLayout(size_hint_y=None, height=dp(120),
                                  spacing=dp(8))
        self.val_lbls = []
        for i, et in enumerate(["horas", "min", "seg"]):
            col = BoxLayout(orientation="vertical")
            up = GButton(text="+", radius=14, font_size="18sp",
                         size_hint_y=None, height=dp(34))
            up.bind(on_release=lambda *_a, i=i: self._aj(i, +1))
            v = Label(text=f"{self.sel[i]:02d}", font_size="26sp", color=BLANCO)
            self.val_lbls.append(v)
            et_l = Label(text=et, font_size="11sp", color=TENUE,
                         size_hint_y=None, height=dp(18))
            dn = GButton(text="-", radius=14, font_size="18sp",
                         size_hint_y=None, height=dp(34))
            dn.bind(on_release=lambda *_a, i=i: self._aj(i, -1))
            col.add_widget(up)
            col.add_widget(v)
            col.add_widget(et_l)
            col.add_widget(dn)
            self.steppers.add_widget(col)
        root.add_widget(self.steppers)

        bo = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(20),
                       padding=[dp(10), 0])
        self.b_cancel = GButton(text="Cancelar", radius=28, color=BLANCO)
        self.b_accion = GButton(text="Iniciar", radius=28, accent=VERDE)
        self.b_cancel.bind(on_release=lambda *_: self._cancelar())
        self.b_accion.bind(on_release=lambda *_: self._iniciar_pausar())
        bo.add_widget(self.b_cancel)
        bo.add_widget(self.b_accion)
        root.add_widget(bo)
        self.add_widget(root)
        Clock.schedule_interval(self._tick, 0.1)
        self._refrescar_idle()

    @staticmethod
    def _fmt(s):
        s = max(0, int(round(s)))
        h, m, sec = s // 3600, (s % 3600) // 60, s % 60
        return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"

    def _aj(self, i, d):
        tope = [23, 59, 59][i]
        self.sel[i] = (self.sel[i] + d) % (tope + 1)
        self.val_lbls[i].text = f"{self.sel[i]:02d}"
        self._refrescar_idle()

    def _refrescar_idle(self):
        if not self.activo and self.restante <= 0:
            total = self.sel[0] * 3600 + self.sel[1] * 60 + self.sel[2]
            self.lbl.text = self._fmt(total)
            self.anillo.set_frac(0.0)

    def _iniciar_pausar(self):
        if self.activo:
            self.activo = False
            self.b_accion.text = "Reanudar"
            self.b_accion._c.rgba = NARANJA
        else:
            if self.restante <= 0:
                self.total = (self.sel[0] * 3600 + self.sel[1] * 60
                              + self.sel[2])
                if self.total <= 0:
                    return
                self.restante = self.total
            self.activo = True
            self.ult = time.perf_counter()
            self.b_accion.text = "Pausa"
            self.b_accion._c.rgba = NARANJA
            self.steppers.opacity = 0
            self.steppers.disabled = True

    def _cancelar(self):
        self.activo = False
        self.restante = 0.0
        self.total = 0.0
        self.b_accion.text = "Iniciar"
        self.b_accion._c.rgba = VERDE
        self.steppers.opacity = 1
        self.steppers.disabled = False
        self._refrescar_idle()

    def _tick(self, *a):
        if self.activo:
            ahora = time.perf_counter()
            self.restante -= (ahora - self.ult)
            self.ult = ahora
            if self.restante <= 0:
                self.restante = 0
                self.activo = False
                self.anillo.set_frac(0.0)
                self.lbl.text = "00:00"
                self.b_accion.text = "Iniciar"
                self.b_accion._c.rgba = VERDE
                self.steppers.opacity = 1
                self.steppers.disabled = False
                alerta("Tiempo terminado")
                return
            self.lbl.text = self._fmt(self.restante)
            self.anillo.set_frac(self.restante / self.total
                                 if self.total else 0)


# ===========================================================================
#  RAÍZ con barra de pestañas
# ===========================================================================
class Raiz(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        self._tex = gradiente_textura()
        with self.canvas.before:
            self._gc = Color(1, 1, 1, 1)
            self._grect = Rectangle(texture=self._tex)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        self.sm = ScreenManager(transition=NoTransition())
        self.pantallas = [
            ("Mundial", PantallaMundial(name="Mundial")),
            ("Alarma", PantallaAlarma(name="Alarma")),
            ("Cronometro", PantallaCrono(name="Cronometro")),
            ("Timer", PantallaTimer(name="Timer")),
        ]
        for _, p in self.pantallas:
            self.sm.add_widget(p)
        self.add_widget(self.sm)

        nav = Glass(orientation="horizontal", size_hint_y=None, height=dp(64),
                    radius=26, alpha=0.18)
        self.botones = {}
        for nombre, _ in self.pantallas:
            b = GButton(text=nombre, alpha=0.0, font_size="12sp",
                        color=TENUE, radius=20)
            b.bind(on_release=lambda *_a, n=nombre: self.mostrar(n))
            self.botones[nombre] = b
            nav.add_widget(b)
        self.add_widget(nav)
        self.mostrar("Mundial")

    def _upd_bg(self, *a):
        self._grect.pos = self.pos
        self._grect.size = self.size

    def mostrar(self, nombre):
        self.sm.current = nombre
        for n, b in self.botones.items():
            if n == nombre:
                b._c.rgba = NARANJA
                b._c.a = 0.9
                b.color = BLANCO
                b.bold = True
            else:
                b._c.a = 0.0
                b.color = TENUE
                b.bold = False


class RelojApp(App):
    def build(self):
        self.title = "Reloj"
        return Raiz()


if __name__ == "__main__":
    Window.clearcolor = (0.035, 0.039, 0.055, 1)
    # SOLO en escritorio fijamos un tamaño para previsualizar. En Android/iOS
    # NUNCA tocamos Window.size (si no, la app sale en miniatura en pantallas
    # grandes como el Galaxy Fold).
    if platform not in ("android", "ios"):
        Window.size = (400, 720)
    RelojApp().run()
