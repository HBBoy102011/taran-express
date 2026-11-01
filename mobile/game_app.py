import colorsys
import json
import math
import os
import random
import sys

import asyncio

import pygame

# ---------- размеры ----------
# Игра считает всё в логических координатах 1280x720, а рисует в K раз подробнее
# (на экране 1920x1080 K = 1.5, на 2560x1440 и выше K = 2). Так картинка чёткая,
# а механика, координаты и баланс не зависят от разрешения.
W, H = 1280, 720
GW, PW = 960, 320            # игровая зона и панель магазина
PLAT_TOP, PLAT_BOT = 400, 470
TRAIN_Y = 488                # верх корпуса поезда
TRACK_Y = 596                # высота ног на путях
# в замороженном exe __file__ ведёт во временный распакованный каталог,
# поэтому сохраняем рядом с самим exe — иначе прогресс пропадал бы при выходе
if getattr(sys, "frozen", False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE = os.path.join(_BASE_DIR, "save.json")

# линейная фильтрация при растяжении картинки на весь экран: без неё SDL "рубит" пиксели
os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "linear")
os.environ.setdefault("SDL_HINT_RENDER_SCALE_QUALITY", "linear")
pygame.init()
pygame.display.set_caption("Платформа-кликер HD")
fullscreen = True

# ---------- разрешение рендера ----------
K = 1.0                      # масштаб рендера относительно логических координат
KD = 1.0                     # масштаб текущего рисования (K, а для крупных спрайтов K * зум)
WP, HP, GWP, PWP = W, H, GW, PW      # те же размеры в реальных пикселях
HAS_SCALED = hasattr(pygame, "SCALED")
# Под драйвером dummy (headless-тесты) pygame глючит: повторное создание SCALED-окна
# после полноэкранного роняет процесс с access violation (0xC0000005), а растягивание
# виртуальному дисплею всё равно не нужно — в этом режиме рисуем и масштабируем сами.
# На реальном драйвере (игроки) поведение не меняется.
DUMMY_DRIVER = os.environ.get("SDL_VIDEODRIVER", "").lower() == "dummy"
SCALED_OK = False            # окно создано в режиме SCALED (SDL сам растягивает картинку)
QUALITY = (1.0, 1.5, 2.0, 2.5, 3.0)    # F10 переключает качество


def _cli_scale():
    """--scale=1.5 в командной строке или переменная CLICKER_SCALE — ручной выбор качества."""
    for a in sys.argv[1:]:
        if a.startswith("--scale="):
            try:
                return max(1.0, min(3.0, float(a.split("=", 1)[1])))
            except ValueError:
                pass
    try:
        return max(1.0, min(3.0, float(os.environ.get("CLICKER_SCALE", ""))))
    except ValueError:
        return None


FORCE_K = _cli_scale()


def px(v):
    return int(round(v * K))


def set_scale(k):
    global K, KD, WP, HP, GWP, PWP
    K = KD = float(k)
    WP, HP, GWP, PWP = px(W), px(H), px(GW), px(PW)


def desktop_size():
    try:
        sizes = pygame.display.get_desktop_sizes()
        if sizes:
            return sizes[0]
    except (AttributeError, pygame.error):
        pass
    try:
        info = pygame.display.Info()
        if info.current_w > 0 and info.current_h > 0:
            return info.current_w, info.current_h
    except pygame.error:
        pass
    return W, H


def snap(k):
    return max(1.0, min(2.0, int(k * 4) / 4.0))     # шаг 0.25, от 1 до 2


def scale_fullscreen():
    dw, dh = desktop_size()
    return snap(min(dw / W, dh / H))


def scale_windowed():
    dw, dh = desktop_size()
    return snap(min(dw * 0.92 / W, dh * 0.86 / H))


def make_window(full):
    """SCALED: SDL растягивает картинку на весь экран с сохранением пропорций (чёрные полосы
    по краям); координаты мыши приходят уже в пикселях рендера."""
    global SCALED_OK
    extra = pygame.FULLSCREEN if full else 0
    if HAS_SCALED and not DUMMY_DRIVER:
        for kw in ({"vsync": 1}, {}):
            try:
                surf = pygame.display.set_mode((WP, HP), pygame.SCALED | pygame.RESIZABLE | extra, **kw)
                SCALED_OK = True
                return surf
            except (pygame.error, TypeError):
                continue
    SCALED_OK = False
    if full:
        try:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        except pygame.error:
            pass
    return pygame.display.set_mode((WP, HP), pygame.RESIZABLE)


def set_fullscreen(full):
    """Переключает режим. True — масштаб рендера поменялся (окно и кэши пересозданы)."""
    global win, fullscreen
    newk = FORCE_K or (scale_fullscreen() if full else scale_windowed())
    if abs(newk - K) < 1e-6 and SCALED_OK:
        try:
            if bool(win.get_flags() & pygame.FULLSCREEN) != full:
                pygame.display.toggle_fullscreen()
            win = pygame.display.get_surface()
            fullscreen = bool(win.get_flags() & pygame.FULLSCREEN)
            return False
        except pygame.error:
            pass
    set_scale(newk)
    build_assets()
    win = make_window(full)
    fullscreen = bool(win.get_flags() & pygame.FULLSCREEN)
    return True


def change_scale(k):
    global win, fullscreen
    set_scale(k)
    build_assets()
    win = make_window(fullscreen)
    fullscreen = bool(win.get_flags() & pygame.FULLSCREEN)


# мобильная версия: фиксированный размер полотна, pygbag сам растягивает его на экран
set_scale(1.0)
win = pygame.display.set_mode((WP, HP))
fullscreen = False
clock = pygame.time.Clock()

FN = "arial,dejavusans,liberationsans"
# шрифты лежат рядом с игрой: в браузере SysFont не находит системных шрифтов,
# а без кириллицы весь русский текст превратился бы в квадраты
_HERE = os.path.dirname(os.path.abspath(__file__))
_FONT_REG = os.path.join(_HERE, "fonts", "DejaVuSans.ttf")
_FONT_BOLD = os.path.join(_HERE, "fonts", "DejaVuSans-Bold.ttf")


def mfont(size, bold=False):
    try:
        return pygame.font.Font(_FONT_BOLD if bold else _FONT_REG, px(size))
    except (OSError, pygame.error):
        return pygame.font.SysFont(FN, px(size), bold=bold)
f_big = f_money = f_mid = f_small = None


def make_fonts():
    global f_big, f_money, f_mid, f_small
    f_big = mfont(46, True)
    f_money = mfont(34, True)
    f_mid = mfont(20, True)
    f_small = mfont(15)


# ---------- рисование в логических координатах ----------
def _sc(v):
    return int(round(v * KD))


def _lw(w):
    return max(1, int(math.ceil(w * KD - 1e-6))) if w else 0


def _rect(r):
    x, y, w, h = r
    l, t = _sc(x), _sc(y)
    return (l, t, max(1, _sc(x + w) - l), max(1, _sc(y + h) - t))


def _pt(p):
    return (_sc(p[0]), _sc(p[1]))


class D:
    """Те же примитивы, что pygame.draw, но координаты и толщина задаются в логических пикселях."""

    @staticmethod
    def rect(surf, color, r, width=0, border_radius=0):
        return pygame.draw.rect(surf, color, _rect(r), _lw(width), border_radius=_sc(border_radius))

    @staticmethod
    def circle(surf, color, center, radius, width=0):
        return pygame.draw.circle(surf, color, _pt(center), max(1, _sc(radius)), _lw(width))

    @staticmethod
    def ellipse(surf, color, r, width=0):
        return pygame.draw.ellipse(surf, color, _rect(r), _lw(width))

    @staticmethod
    def line(surf, color, a, b, width=1):
        return pygame.draw.line(surf, color, _pt(a), _pt(b), _lw(width) or 1)

    @staticmethod
    def lines(surf, color, closed, pts, width=1):
        return pygame.draw.lines(surf, color, closed, [_pt(p) for p in pts], _lw(width) or 1)

    @staticmethod
    def polygon(surf, color, pts, width=0):
        return pygame.draw.polygon(surf, color, [_pt(p) for p in pts], _lw(width))

    @staticmethod
    def arc(surf, color, r, a0, a1, width=1):
        return pygame.draw.arc(surf, color, _rect(r), a0, a1, _lw(width))


def new_surf(w, h, alpha=True, zoom=1.0):
    size = (max(1, int(round(w * K * zoom))), max(1, int(round(h * K * zoom))))
    return pygame.Surface(size, pygame.SRCALPHA) if alpha else pygame.Surface(size)


def fast(s, alpha=True):
    """Переводит поверхность в формат экрана — blit становится заметно быстрее."""
    try:
        return s.convert_alpha() if alpha else s.convert()
    except pygame.error:
        return s


def blit(dst, src, pos):
    dst.blit(src, (px(pos[0]), px(pos[1])))


def blit_c(dst, src, cx, cy):
    dst.blit(src, src.get_rect(center=(px(cx), px(cy))))


def vband(surf, x0, x1, y0, y1, c0, c1):
    """Вертикальный градиент: одна строка пикселей = один fill."""
    xa, xb = px(x0), px(x1)
    ya, yb = px(y0), px(y1)
    n = max(1, yb - ya - 1)
    for i in range(yb - ya):
        surf.fill(lerp_c(c0, c1, i / n), (xa, ya + i, xb - xa, 1))


# ---------- вспомогательное ----------
def fmt(n):
    n = int(n)
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 10_000:
        return f"{n / 1000:.1f}k"
    return str(n)


def fmt_time(t):
    """Секундомер: минуты и секунды."""
    t = max(0, int(t))
    return f"{t // 60}:{t % 60:02d}"


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_c(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _ol():
    return max(1, int(K + 0.25))        # толщина обводки текста/спрайтов в пикселях


_TC = {}
_GC = {}
_PC = {}
_GB = [0]                              # объём кэша свечений в байтах
SPR = {}                               # кэш спрайтов людей и боссов
TRAIN_CACHE = {}
_OFFS = ((0, 0), (1, 0), (2, 0), (0, 1), (2, 1), (0, 2), (1, 2), (2, 2), (1, 3), (2, 3))


def _text_img(s, f, color, shadow):
    """Текст с тёмной обводкой; готовые картинки кэшируются."""
    k = (s, id(f), color, shadow)
    img = _TC.get(k)
    if img is None:
        base = f.render(s, True, color)
        if shadow:
            o = _ol()
            ol = f.render(s, True, (8, 8, 16))
            w, h = base.get_size()
            img = pygame.Surface((w + 2 * o, h + 4 * o), pygame.SRCALPHA)
            for dx, dy in _OFFS:
                for ex in range(o):
                    for ey in range(o):
                        img.blit(ol, (dx * o + ex, dy * o + ey))
            img.blit(base, (o, o))
        else:
            img = base
        img = fast(img)
        if len(_TC) > 700:
            _TC.clear()
        _TC[k] = img
    return img


def text(surf, s, f, color, pos, center=False, shadow=True):
    img = _text_img(s, f, color, shadow)
    o = _ol() if shadow else 0
    bw = img.get_width() - 2 * o
    x, y = px(pos[0]), px(pos[1])
    if center:
        x -= bw // 2
    surf.blit(img, (x - o, y - o))
    return bw / K


def twidth(f, s):
    """Ширина строки в логических пикселях."""
    return f.size(s)[0] / K


def _make_glow(r, color, alpha):
    big = r > 120                      # большие свечения строим вдвое-втрое мельче и растягиваем
    rr = r // 3 if big else r
    tmp = pygame.Surface((rr * 2, rr * 2), pygame.SRCALPHA)
    steps = 12
    for i in range(steps):
        rad = int(rr * (1 - i / steps))
        a = max(0, min(255, int(alpha * ((i + 1) / steps) ** 1.4)))
        pygame.draw.circle(tmp, (color[0], color[1], color[2], a), (rr, rr), rad)
    if big:
        tmp = pygame.transform.smoothscale(tmp, (r * 2, r * 2))
    return fast(tmp)


def glow(surf, pos, radius, color, alpha):
    r = int(radius * K)
    if r > 30:
        r = int(round(1.12 ** round(math.log(r) / math.log(1.12))))    # мало разных размеров — кэш работает
    else:
        r = r // 3 * 3
    alpha = int(alpha) // 10 * 10
    if r < 3 or alpha <= 0:
        return
    key = (r, tuple(color), alpha)
    tmp = _GC.get(key)
    if tmp is None:
        tmp = _make_glow(r, color, alpha)
        _GC[key] = tmp
        _GB[0] += r * r * 16
        while _GB[0] > 150_000_000 and len(_GC) > 1:
            old = _GC.pop(next(iter(_GC)))
            _GB[0] -= old.get_width() * old.get_height() * 4
    surf.blit(tmp, (px(pos[0]) - r, px(pos[1]) - r))


def plate(surf, rect, alpha=150, radius=12, color=(10, 12, 24), border=(255, 255, 255, 40)):
    """Полупрозрачная плашка под HUD."""
    rect = pygame.Rect(rect)
    key = (rect.w, rect.h, alpha, radius, color, border, K)
    s = _PC.get(key)
    if s is None:
        s = new_surf(rect.w, rect.h)
        D.rect(s, (*color, alpha), (0, 0, rect.w, rect.h), border_radius=radius)
        if border:
            D.rect(s, border, (0, 0, rect.w, rect.h), 1, border_radius=radius)
        s = fast(s)
        if len(_PC) > 120:
            _PC.clear()
        _PC[key] = s
    surf.blit(s, (px(rect.x), px(rect.y)))


# экранная кнопка паузы: на телефоне нет Esc
MBTN = (GW - 36, H - 34, 19)


def mobile_btn_hit(mx, my):
    return math.hypot(mx - MBTN[0], my - MBTN[1]) <= MBTN[2] + 10


def draw_mobile_button(surf, paused):
    x, y, r = MBTN
    D.circle(surf, (12, 15, 28), (x, y), r + 2)
    D.circle(surf, (170, 190, 240), (x, y), r + 2, 2)
    if paused:
        D.polygon(surf, (255, 255, 255), [(x - 5, y - 8), (x - 5, y + 8), (x + 8, y)])
    else:
        D.rect(surf, (255, 255, 255), (x - 7, y - 8, 5, 16), border_radius=2)
        D.rect(surf, (255, 255, 255), (x + 2, y - 8, 5, 16), border_radius=2)


def draw_heart(surf, x, y, r, filled):
    """Сердечко-жизнь в хардкоре: пустое — уже потрачено."""
    col = (245, 74, 86) if filled else (60, 46, 56)
    D.circle(surf, col, (x - r * 0.5, y - r * 0.3), r * 0.62)
    D.circle(surf, col, (x + r * 0.5, y - r * 0.3), r * 0.62)
    D.polygon(surf, col, [(x - r * 1.05, y), (x + r * 1.05, y), (x, y + r * 1.3)])
    if filled:
        D.circle(surf, (255, 176, 180), (x - r * 0.55, y - r * 0.55), max(1, r * 0.2))


def make_vignette():
    """Карта затемнения по краям; накладывается через BLEND_RGB_MULT (быстрее alpha-blit)."""
    sw, sh = 64, 40
    s = pygame.Surface((sw, sh))
    for y in range(sh):
        for x in range(sw):
            dx = (x / (sw - 1) - 0.5) * 2
            dy = (y / (sh - 1) - 0.5) * 2
            d = math.sqrt(dx * dx * 0.8 + dy * dy)
            a = max(0.0, min(1.0, (d - 0.62) / 0.75)) ** 1.6 * 150 / 255.0
            v = int(255 * (1 - a))
            s.set_at((x, y), (v, v, min(255, v + 4)))
    return fast(pygame.transform.smoothscale(s, (GWP, HP)), False)


def make_cone(w, h, vertical, peak):
    """Конус света: вертикальный (фонарь) или горизонтальный (прожектор поезда)."""
    pw, ph = px(w), px(h)
    s = pygame.Surface((pw, ph), pygame.SRCALPHA)
    if vertical:
        for y in range(ph):
            k = y / ph
            half = int((8 + (w / 2 - 8) * k) * K)
            a = int(peak * (1 - k) ** 1.3)
            pygame.draw.line(s, (255, 240, 170, a), (pw // 2 - half, y), (pw // 2 + half, y))
    else:
        for x in range(pw):
            k = (pw - 1 - x) / pw
            half = int((6 + (h / 2 - 6) * k) * K)
            a = int(peak * (1 - k) ** 1.2)
            pygame.draw.line(s, (255, 244, 190, a), (x, ph // 2 - half), (x, ph // 2 + half))
    return fast(s)


def make_shadow(big):
    if big:
        s = new_surf(90, 22)
        D.ellipse(s, (0, 0, 0, 50), (0, 0, 90, 22))
        D.ellipse(s, (0, 0, 0, 70), (12, 4, 66, 14))
    else:
        s = new_surf(46, 14)
        D.ellipse(s, (0, 0, 0, 40), (0, 0, 46, 14))
        D.ellipse(s, (0, 0, 0, 60), (6, 2, 34, 10))
    return fast(s)


_DIRS8 = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1))


def outlined(fig, col=(14, 14, 24), o=None):
    """Тонкий тёмный контур вокруг спрайта — персонажи читаются на любом фоне."""
    if o is None:
        o = _ol()
    m = pygame.mask.from_surface(fig, 40)
    ol = m.to_surface(setcolor=col + (255,), unsetcolor=(0, 0, 0, 0))
    out = pygame.Surface(fig.get_size(), pygame.SRCALPHA)
    for dx, dy in _DIRS8:
        out.blit(ol, (dx * o, dy * o))
    out.blit(fig, (0, 0))
    return out


# ---------- локации (10 уровней, меняются по числу поездок) ----------
THEMES = [
    dict(name="Утро", kills=0, kind="day", light=0.0,
         top=(110, 185, 245), bot=(220, 240, 252), far=(160, 192, 215), near=(120, 150, 175),
         plat=(158, 158, 168), front=(112, 112, 128), bed=(92, 82, 74), rail=(195, 195, 205),
         train=(205, 50, 50), cloud=(255, 255, 255)),
    dict(name="Закат", kills=20, kind="sunset", light=0.3,
         top=(70, 60, 135), bot=(255, 155, 95), far=(130, 85, 115), near=(80, 52, 88),
         plat=(145, 128, 138), front=(100, 84, 100), bed=(82, 66, 66), rail=(210, 180, 170),
         train=(225, 95, 50), cloud=(255, 190, 170)),
    dict(name="Ночь", kills=60, kind="night", light=1.0,
         top=(8, 12, 38), bot=(42, 52, 105), far=(30, 38, 74), near=(18, 22, 50),
         plat=(72, 78, 98), front=(50, 54, 74), bed=(40, 38, 50), rail=(135, 140, 165),
         train=(60, 110, 205), cloud=(48, 58, 100)),
    dict(name="Зима", kills=120, kind="snow", light=0.2,
         top=(150, 182, 218), bot=(236, 243, 251), far=(192, 207, 224), near=(160, 178, 202),
         plat=(228, 234, 242), front=(172, 182, 198), bed=(192, 197, 208), rail=(150, 156, 172),
         train=(70, 150, 172), cloud=(246, 249, 253)),
    dict(name="Ливень", kills=220, kind="rain", light=0.6,
         top=(46, 54, 68), bot=(104, 114, 126), far=(76, 86, 100), near=(54, 62, 76),
         plat=(96, 100, 108), front=(70, 73, 82), bed=(56, 53, 52), rail=(150, 156, 168),
         train=(172, 62, 62), cloud=(62, 68, 80)),
    dict(name="Неон-сити", kills=400, kind="neon", light=1.0,
         top=(24, 4, 62), bot=(215, 42, 152), far=(72, 20, 112), near=(40, 10, 76),
         plat=(56, 46, 88), front=(36, 28, 62), bed=(30, 22, 50), rail=(0, 232, 232),
         train=(0, 205, 232), cloud=(120, 52, 160)),
    dict(name="Пустыня", kills=650, kind="desert", light=0.0,
         top=(240, 170, 80), bot=(255, 232, 175), far=(222, 172, 112), near=(190, 140, 90),
         plat=(214, 186, 140), front=(170, 140, 100), bed=(150, 120, 85), rail=(210, 200, 185),
         train=(40, 150, 120), cloud=(255, 240, 215)),
    dict(name="Вулкан", kills=950, kind="lava", light=0.8,
         top=(40, 10, 10), bot=(200, 60, 20), far=(90, 30, 25), near=(55, 18, 18),
         plat=(80, 62, 62), front=(56, 42, 44), bed=(44, 32, 32), rail=(255, 140, 60),
         train=(230, 110, 30), cloud=(90, 35, 30)),
    dict(name="Космос", kills=1350, kind="space", light=1.0,
         top=(3, 3, 18), bot=(40, 20, 90), far=(35, 30, 80), near=(22, 18, 60),
         plat=(90, 96, 130), front=(60, 64, 96), bed=(34, 32, 60), rail=(150, 200, 255),
         train=(180, 185, 215), cloud=(50, 40, 110)),
    dict(name="Последняя станция", kills=1900, kind="finale", light=1.0,
         top=(15, 0, 20), bot=(120, 30, 90), far=(50, 15, 60), near=(28, 8, 38),
         plat=(60, 50, 70), front=(40, 30, 52), bed=(28, 20, 36), rail=(255, 255, 255),
         train=(20, 20, 26), cloud=(90, 40, 100)),
]
KEYS = ("top", "bot", "far", "near", "plat", "front", "bed", "rail", "train", "cloud")
STAR_KINDS = ("night", "neon", "space", "finale")


def blend(t0, t1, t):
    d = {k: lerp_c(t0[k], t1[k], t) for k in KEYS}
    d["light"] = lerp(t0["light"], t1["light"], t)
    return d


def stage_for(kills):
    idx = 0
    for i, th in enumerate(THEMES):
        if kills >= th["kills"]:
            idx = i
    return idx


# ---------- боссы: по одному на каждый уровень ----------
BOSSES = [
    dict(name="Начальник станции", hp=40, speed=70, time=45, flags=(),
         color=(200, 40, 40), skin=(245, 210, 170), hair=(40, 30, 25), hat=(30, 30, 40)),
    dict(name="Бегун-спринтер", hp=70, speed=170, time=45, flags=("erratic",),
         color=(60, 200, 90), skin=(225, 180, 135), hair=(30, 30, 30), hat=(255, 80, 80)),
    dict(name="Тень", hp=100, speed=90, time=50, flags=("ghost", "acid"),
         color=(40, 40, 60), skin=(70, 70, 95), hair=(15, 15, 25), hat=None),
    dict(name="Снеговик-гигант", hp=140, speed=60, time=50, flags=("regen",),
         color=(240, 245, 250), skin=(250, 250, 255), hair=(220, 225, 235), hat=(40, 40, 60)),
    dict(name="Громила с зонтом", hp=180, speed=80, time=55, flags=("shield", "acid"),
         color=(30, 50, 110), skin=(190, 140, 100), hair=(30, 30, 30), hat=None),
    dict(name="Киборг-директор", hp=260, speed=110, time=60, flags=("erratic", "shield", "regen"),
         color=(80, 80, 100), skin=(170, 180, 190), hair=(60, 60, 70), hat=None),
    dict(name="Песчаный страж", hp=340, speed=130, time=60, flags=("erratic", "regen", "acid"),
         color=(170, 120, 50), skin=(200, 150, 100), hair=(90, 60, 30), hat=(220, 190, 110)),
    dict(name="Лавовый голем", hp=460, speed=75, time=65, flags=("shield", "regen", "rage"),
         color=(150, 40, 20), skin=(220, 90, 30), hair=(255, 160, 40), hat=None),
    dict(name="Пришелец-капитан", hp=620, speed=150, time=70, flags=("ghost", "erratic", "blink"),
         color=(90, 60, 160), skin=(120, 220, 150), hair=(60, 200, 120), hat=(200, 200, 230)),
    # финальный босс: тёмная кожа, длинные волосы, белая одежда, чёрные джинсы
    dict(name="Хозяйка вокзала", hp=900, speed=140, time=90,
         flags=("erratic", "shield", "regen", "ghost", "rage", "acid"),
         color=(245, 245, 248), skin=(112, 72, 48), hair=(18, 14, 14), hat=None,
         pants=(18, 18, 24), long_hair=True),
]
FINAL_BOSS_KILLS = 2600
BOSS_HP_MULT = 2.2      # во сколько раз больше HP у всех боссов
BOSS_TIME_MULT = 0.9    # чуть меньше времени на босса
BOSS_DMG_MAX = 41       # урон за клик при максимальной прокачке (1 + 2*20)
BOSS_DMG_K = 7.0        # во сколько раз боссы жирнее при максимальном уроне


def boss_dmg_scale(smash_lvl):
    """HP босса растёт прямо пропорционально урону за клик: урон / 41 * K (но не меньше x1)."""
    dmg = 1 + 2 * smash_lvl
    return max(1.0, dmg / BOSS_DMG_MAX * BOSS_DMG_K)


def boss_at(level):
    """Сколько поездок нужно, чтобы вызвать босса этого уровня."""
    return THEMES[level + 1]["kills"] if level < len(THEMES) - 1 else FINAL_BOSS_KILLS


# ---------- улучшения (вкладка 0 — базовые, вкладка 1 — продвинутые) ----------
UPGRADES = [
    dict(key="power", tab=0, req=0, name="Сила толчка", label="Радиус", base=50, growth=1.9, max=10,
         v=lambda l: f"{l * 35}px"),
    dict(key="income", tab=0, req=0, name="Цена билета", label="Доход", base=30, growth=1.6, max=40,
         v=lambda l: f"${round(10 * 1.35 ** l)}"),
    dict(key="flow", tab=0, req=0, name="Поток людей", label="Приток", base=40, growth=1.55, max=15,
         v=lambda l: f"x{1 + 0.25 * l:g}"),
    dict(key="trains", tab=0, req=0, name="Частота поездов", label="Раз в", base=60, growth=1.6, max=12,
         v=lambda l: f"{6 * 0.92 ** l:.1f}с"),
    dict(key="helper", tab=0, req=0, name="Помощник", label="Толкает раз в", base=100, growth=1.7, max=8,
         v=lambda l: "нет" if l == 0 else f"{max(0.6, 6.0 - 0.7 * (l - 1)):.1f}с"),
    dict(key="combo", tab=0, req=0, name="Комбо", label="Макс. множитель", base=80, growth=1.65, max=12,
         v=lambda l: f"x{1.5 + 0.5 * l:g}"),
    dict(key="gold", tab=0, req=0, name="Золотые пассажиры", label="Шанс (x5)", base=120, growth=1.7, max=8,
         v=lambda l: f"{(0.04 + 0.03 * l) * 100:.0f}%"),
    dict(key="smash", tab=0, req=0, name="Удар по боссам", label="Урон за клик", base=60, growth=1.75, max=20,
         v=lambda l: str(1 + 2 * l)),
    # --- продвинутые: открываются по мере прохождения уровней ---
    dict(key="crit", tab=1, req=1, name="Критический клик", label="Шанс крита x3", base=150, growth=1.7, max=10,
         v=lambda l: f"{5 * l}%"),
    dict(key="idle", tab=1, req=2, name="Пассивный доход", label="Доход", base=200, growth=1.65, max=15,
         v=lambda l: f"${3 * l}/с"),
    dict(key="gtrain", tab=1, req=3, name="Золотой поезд", label="Шанс (x3)", base=300, growth=1.75, max=10,
         v=lambda l: f"{4 * l}%"),
    dict(key="timebonus", tab=1, req=4, name="Время на боссов", label="Бонус", base=250, growth=1.7, max=8,
         v=lambda l: f"+{5 * l}с"),
    dict(key="bot", tab=1, req=5, name="Помощник-боец", label="Урон боссу/с", base=400, growth=1.7, max=12,
         v=lambda l: str(2 * l)),
    dict(key="mult", tab=1, req=6, name="Экспресс-билет", label="Весь доход", base=600, growth=1.75, max=20,
         v=lambda l: f"x{1 + 0.15 * l:.2f}"),
    dict(key="cap", tab=1, req=7, name="Вместимость", label="Людей на платформе", base=500, growth=1.8, max=6,
         v=lambda l: str(14 + 2 * l)),
    dict(key="combot", tab=1, req=8, name="Долгое комбо", label="Время комбо", base=700, growth=1.8, max=8,
         v=lambda l: f"{6 + l}с"),
]
TAB_NAMES = ("Базовые", "Продвинутые", "Зелья")
TAB_Y = 36
ROWS_PER_TAB = 8
ROW_Y0, ROW_H = 70, 76
TAB_W, TAB_GAP = 96, 100        # три вкладки помещаются в панель шириной PW
ITEM_TAB = 2
HARD_LIVES = 5           # хардкор: столько жизней после 10-го уровня

# ---------- расходники (вкладка «Зелья») ----------
# dur > 0 — временный эффект, dur == 0 — мгновенное действие
ITEMS = [
    dict(key="p_flow", name="Зелье потока", dur=30, price=260,
         desc="x2 приток людей, 30с"),
    dict(key="p_train", name="Сжатое расписание", dur=45, price=340,
         desc="поезда x2 чаще, 45с"),
    dict(key="p_money", name="Двойная касса", dur=30, price=520,
         desc="x2 весь доход, 30с"),
    dict(key="p_power", name="Супер-толчок", dur=30, price=420,
         desc="радиус клика x2, 30с"),
    dict(key="grenade", name="Граната", dur=0, price=300,
         desc="сбивает всех на платформе"),
    dict(key="antidote", name="Противоядие", dur=0, price=150,
         desc="смывает кислоту босса"),
]
FX_LABELS = {"p_flow": "Поток x2", "p_train": "Поезда x2",
             "p_money": "Касса x2", "p_power": "Радиус x2"}


def item_buy_rect(i):
    """Кнопка покупки внутри строки предмета."""
    return pygame.Rect(GW + PW - 122, ROW_Y0 + i * ROW_H + 34, 102, 26)


def buy_item(s, i, g):
    if not (0 <= i < len(ITEMS)):
        return
    it = ITEMS[i]
    p = item_price(it, s)
    if s["money"] < p:
        return
    s["money"] -= p
    s["items"][it["key"]] = s["items"].get(it["key"], 0) + 1
    g["toast"] = f"Куплено: {it['name']} (x{s['items'][it['key']]})"
    g["toast_col"] = (170, 240, 190)
    g["toast_t"] = 1.4


def use_item(s, i, g):
    """Тратит заряд; если зарядов нет — просто покупает один."""
    if not (0 <= i < len(ITEMS)):
        return
    it = ITEMS[i]
    k = it["key"]
    if s["items"].get(k, 0) <= 0:
        buy_item(s, i, g)
        return
    if k == "antidote":
        if g["acid"] <= 0:
            return                      # кислоты нет — заряд не тратим
        g["acid"] = 0.0
        g["splats"] = None
        msg = "Кислота смыта!"
    elif k == "grenade":
        targets = [p for p in g["people"] if p.state == "walk"]
        if not targets:
            return                      # никого нет — заряд не тратим
        for p in targets:
            p.push(direct=True)
        g["shake"] = 0.45
        for p in targets:
            g["particles"].append(Particle(p.x, p.y - 50, (255, 200, 90)))
        msg = "ГРАНАТА!"
    else:
        g["fx"][k] = max(g["fx"].get(k, 0.0), float(it["dur"]))
        msg = f"{it['name']}: {FX_LABELS[k]} на {it['dur']}с"
    s["items"][k] -= 1
    g["toast"] = msg
    g["toast_col"] = (170, 240, 190)
    g["toast_t"] = 1.8


def tab_items(t):
    return [i for i, u in enumerate(UPGRADES) if u["tab"] == t]


def new_save():
    return dict(money=0, earned=0, kills=0, level=0, won=False, skins=1,
                levels={u["key"]: 0 for u in UPGRADES},
                items={u["key"]: 0 for u in ITEMS})


def _ls():
    """Хранилище браузера: в WebAssembly обычная запись в файл не сохраняется."""
    try:
        import platform
        return platform.window.localStorage
    except Exception:
        return None


def _save_text():
    ls = _ls()
    if ls is not None:
        try:
            raw = ls.getItem("train_game_v1")
            if raw:
                return str(raw)
        except Exception:
            pass
    try:
        with open(SAVE, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _put_text(txt):
    ls = _ls()
    if ls is not None:
        try:
            ls.setItem("train_game_v1", txt)
            return
        except Exception:
            pass
    with open(SAVE, "w", encoding="utf-8") as f:
        f.write(txt)


def load_save():
    s = new_save()
    try:
        d = json.loads(_save_text())
        s["money"] = int(d.get("money", 0))
        # старые сейвы без «earned» берут баланс за стартовую экономику —
        # иначе инфляция обнулилась бы у игрока с 280 миллиардами
        s["earned"] = max(int(d.get("earned", 0)), s["money"])
        s["kills"] = int(d.get("kills", 0))
        s["level"] = max(0, min(len(THEMES) - 1, int(d.get("level", 0))))
        s["won"] = bool(d.get("won", False))
        s["skins"] = max(1, min(len(SKINS), int(d.get("skins", 1))))
        for u in UPGRADES:
            s["levels"][u["key"]] = max(0, min(u["max"], int(d.get("levels", {}).get(u["key"], 0))))
        for u in ITEMS:
            s["items"][u["key"]] = max(0, int(d.get("items", {}).get(u["key"], 0)))
    except (OSError, ValueError, TypeError):
        pass
    return s


def write_save(s):
    try:
        _put_text(json.dumps(s))
    except OSError:
        pass


# ---------- инфляция ----------
# Цены привязаны к накопленному доходу s["earned"], а не к балансу: баланс тратится,
# а инфляция назад не уходит. Израсходовано $10 000 экономики — платим базовую цену,
# дальше множитель растёт линейно с доходом, поэтому граната за 280 млрд не стоит 300.
INFL_DIV = 10_000


def inflation(s):
    """Множитель цен магазина: чем богаче экономика, тем дороже товар."""
    return max(1.0, s.get("earned", s["money"]) / INFL_DIV)


def up_infl(s):
    """Улучшения и так растут с каждым уровнем, поэтому им хватает четвертого корня
    инфляции: полный множитель сделал бы топовые прокачки недоступными — их цена
    росла бы быстрее, чем баланс."""
    return inflation(s) ** 0.25


def item_price(it, s):
    """Цена расходника с учётом инфляции."""
    return int(it["price"] * inflation(s))


def cost(u, lvl, infl=1.0):
    return int(u["base"] * u["growth"] ** lvl * infl)


def buy(s, i, g):
    if not (0 <= i < len(UPGRADES)):
        return
    u = UPGRADES[i]
    if s["level"] < u["req"]:
        return
    l = s["levels"][u["key"]]
    c = cost(u, l, up_infl(s))
    if l < u["max"] and s["money"] >= c:
        s["money"] -= c
        s["levels"][u["key"]] += 1
        if u["key"] == "helper":
            g["helper_t"] = 0.0


# ---------- мир (фон, погода, платформа) ----------
STRIP_H = 244                  # высота полосы с домами (логические пиксели)
KEYCOL = (255, 0, 255)


class World:
    def __init__(self):
        rnd = random.Random(7)
        self.t = 0.0
        self.cache = {}
        self.clouds = [[rnd.uniform(0, GW), rnd.uniform(40, 220), rnd.uniform(0.7, 1.5), rnd.uniform(8, 22)]
                       for _ in range(7)]
        self.stars = [(rnd.uniform(0, GW), rnd.uniform(0, 300), rnd.uniform(0, 6)) for _ in range(90)]
        self.snow = [[random.uniform(0, GW), random.uniform(0, H), random.uniform(40, 90),
                      random.uniform(-15, 15), random.randint(2, 4)] for _ in range(150)]
        self.rain = [[random.uniform(0, GW + 100), random.uniform(0, H), random.uniform(650, 900)]
                     for _ in range(220)]
        self.far = []
        x = 0
        while x < GW + 300:
            w = rnd.randint(50, 110)
            self.far.append((x, w, rnd.randint(60, 170)))
            x += w + rnd.randint(0, 18)
        self.far_span = x
        self.far2 = []
        x = 0
        while x < GW + 300:
            w = rnd.randint(40, 90)
            self.far2.append((x, w, rnd.randint(110, 230)))
            x += w + rnd.randint(0, 10)
        self.far2_span = x
        self.near = []
        x = 0
        while x < GW + 300:
            w = rnd.randint(70, 130)
            self.near.append((x, w, rnd.randint(100, 240), rnd.randint(0, 10 ** 6)))
            x += w + rnd.randint(4, 30)
        self.near_span = x
        self.gravel = [(rnd.randint(0, GW), rnd.randint(TRAIN_Y + 6, H - 4), rnd.randint(1, 3), rnd.random())
                       for _ in range(260)]
        self.flash = 0.0
        self.flash_t = random.uniform(4, 8)
        self.flash_surf = None
        self.flash_k = None

    # --- кэш статичных слоёв: пересобирается только когда меняются цвета локации ---
    def _ck(self, col, extra=()):
        return (K,) + tuple(col[k] for k in KEYS) + (round(col["light"], 3),) + tuple(extra)

    def _put(self, key, val):
        self.cache[key] = val
        while len(self.cache) > 48:
            self.cache.pop(next(iter(self.cache)))
        return val

    def update(self, dt, kind):
        self.t += dt
        for c in self.clouds:
            c[0] += c[3] * dt
            if c[0] > GW + 160:
                c[0] = -160
        if kind == "snow":
            for p in self.snow:
                p[1] += p[2] * dt
                p[0] += p[3] * dt
                if p[1] > H:
                    p[1] = -5
                    p[0] = random.uniform(0, GW)
        if kind == "lava":      # искры летят вверх
            for p in self.snow:
                p[1] -= p[2] * 1.4 * dt
                p[0] += p[3] * dt
                if p[1] < -5:
                    p[1] = H + 5
                    p[0] = random.uniform(0, GW)
        if kind == "rain":
            for d in self.rain:
                d[1] += d[2] * dt
                d[0] -= d[2] * 0.15 * dt
                if d[1] > H:
                    d[1] = -10
                    d[0] = random.uniform(0, GW + 100)
            self.flash_t -= dt
            if self.flash_t <= 0:
                self.flash = 1.0
                self.flash_t = random.uniform(4, 9)
        self.flash = max(0.0, self.flash - dt * 3)

    def flash_surface(self):
        if self.flash_surf is None or self.flash_k != K:
            s = pygame.Surface((GWP, HP))
            s.fill((255, 255, 255))
            self.flash_surf = fast(s, False)
            self.flash_k = K
        return self.flash_surf

    def sky(self, col, kind):
        key = self._ck(col, ("sky", kind))
        s = self.cache.get(key)
        if s is None:
            n = px(PLAT_TOP)
            s = pygame.Surface((GWP, n))
            for y in range(n):
                s.fill(lerp_c(col["top"], col["bot"], (y / n) ** 0.9), (0, y, GWP, 1))
            if kind != "finale":          # у финала светило пульсирует — оно рисуется каждый кадр
                self.draw_body(s, col, kind)
            s = self._put(key, fast(s, False))
        return s

    def haze(self, col):
        key = self._ck(col, ("haze",))
        s = self.cache.get(key)
        if s is None:
            n = px(150)
            s = pygame.Surface((GWP, n), pygame.SRCALPHA)
            c = col["bot"]
            for y in range(n):
                s.fill((c[0], c[1], c[2], int(170 * (y / n) ** 1.7)), (0, y, GWP, 1))
            s = self._put(key, fast(s))
        return s

    def cloud(self, sc, ccol):
        key = ("cloud", K, sc, ccol)
        hit = self.cache.get(key)
        if hit is None:
            ox, oy = 28 * sc, 44 * sc
            s = pygame.Surface((px(116 * sc), px(88 * sc)), pygame.SRCALPHA)
            shade = lerp_c(ccol, (0, 0, 0), 0.10)
            for dx, dy, r in ((0, 4, 26), (28, -6, 32), (60, 4, 26), (30, 12, 28)):
                pygame.draw.circle(s, shade, (px(ox + dx * sc), px(oy + dy * sc)), max(1, px(r * sc)))
            for dx, dy, r in ((0, 0, 26), (28, -10, 32), (60, 0, 26), (30, 8, 28)):
                pygame.draw.circle(s, ccol, (px(ox + dx * sc), px(oy + dy * sc)), max(1, px(r * sc)))
            hit = self._put(key, (fast(s), ox, oy))
        return hit

    def draw_body(self, surf, col, kind):
        """Солнце, луна, планета и прочие светила."""
        if kind == "day":
            glow(surf, (720, 110), 150, (255, 240, 170), 90)
            glow(surf, (720, 110), 80, (255, 245, 200), 120)
            D.circle(surf, (255, 238, 140), (720, 110), 36)
            D.circle(surf, (255, 250, 200), (714, 104), 22)
        elif kind == "sunset":
            glow(surf, (620, 330), 260, (255, 170, 90), 110)
            D.circle(surf, (255, 205, 120), (620, 330), 70)
            D.circle(surf, (255, 232, 160), (612, 322), 44)
        elif kind == "night":
            glow(surf, (730, 100), 120, (200, 210, 255), 70)
            D.circle(surf, (235, 238, 250), (730, 100), 28)
            D.circle(surf, (205, 210, 228), (720, 94), 5)
            D.circle(surf, (205, 210, 228), (738, 108), 7)
            D.circle(surf, (215, 220, 238), (736, 90), 3)
        elif kind == "neon":
            glow(surf, (700, 250), 260, (255, 60, 160), 100)
            D.circle(surf, (255, 110, 170), (700, 250), 85)
            D.circle(surf, (255, 170, 200), (700, 250), 85, 3)
            for k in range(5):
                D.rect(surf, col["near"], (615, 262 + k * 14, 170, 3 + k))
        elif kind == "desert":
            glow(surf, (720, 150), 220, (255, 200, 100), 110)
            D.circle(surf, (255, 218, 110), (720, 150), 54)
            D.circle(surf, (255, 240, 170), (712, 142), 34)
        elif kind == "lava":
            D.polygon(surf, col["near"], [(430, PLAT_TOP), (590, 190), (670, 190), (830, PLAT_TOP)])
            D.polygon(surf, lerp_c(col["near"], (255, 120, 40), 0.18),
                      [(590, 190), (670, 190), (700, 260), (560, 260)])
            glow(surf, (630, 190), 170, (255, 100, 30), 150)
            D.ellipse(surf, (255, 130, 40), (592, 183, 76, 15))
            D.ellipse(surf, (255, 210, 110), (608, 186, 44, 8))
        elif kind == "space":
            glow(surf, (700, 170), 180, (160, 120, 255), 70)
            D.circle(surf, (130, 100, 210), (700, 170), 62)
            D.circle(surf, (160, 130, 235), (686, 156), 40)
            D.ellipse(surf, (210, 190, 255), (606, 152, 188, 38), 3)
            D.circle(surf, (190, 190, 215), (260, 150), 16)
            D.circle(surf, (160, 160, 190), (255, 146), 4)
        elif kind == "finale":
            pulse = 0.5 + 0.5 * math.sin(self.t * 2)
            glow(surf, (700, 170), 230, (255, 60, 200), int(70 + 60 * pulse))
            D.circle(surf, (8, 0, 14), (700, 170), 56)
            D.circle(surf, (255, 200, 240), (700, 170), 56, 3)
            D.circle(surf, (255, 120, 220), (700, 170), 64 + int(4 * pulse), 1)

    # --- полосы с домами: рисуются один раз и просто едут по экрану ---
    def strip(self, which, col, kind):
        key = self._ck(col, ("strip", which, kind))
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        light = col["light"]
        span = {"far2": self.far2_span, "far": self.far_span, "near": self.near_span}[which]
        s = pygame.Surface((px(span), px(STRIP_H)))
        s.fill(KEYCOL)
        if which == "far2":
            pale = lerp_c(col["far"], col["bot"], 0.55)
            for (x, w, h) in self.far2:
                D.rect(s, pale, (x, STRIP_H - h, w, h))
        elif which == "far":
            for (x, w, h) in self.far:
                D.rect(s, col["far"], (x, STRIP_H - h, w, h))
                D.line(s, lerp_c(col["far"], (255, 255, 255), 0.18), (x, STRIP_H - h), (x + w, STRIP_H - h), 2)
        else:
            wcol = lerp_c(col["near"], col["bot"], 0.35)
            for (x, w, h, seed) in self.near:
                top = STRIP_H - h
                D.rect(s, col["near"], (x, top, w, h))
                D.rect(s, lerp_c(col["near"], (255, 255, 255), 0.10), (x, top, 4, h))
                D.rect(s, lerp_c(col["near"], (0, 0, 0), 0.25), (x + w - 5, top, 5, h))
                D.rect(s, lerp_c(col["near"], (255, 255, 255), 0.16), (x, top, w, 4))
                if kind == "neon":
                    D.rect(s, (255, 60, 200), (x, top, w, h), 2)
                if kind == "finale":
                    D.rect(s, (200, 80, 220), (x, top, w, h), 1)
                if light > 0.4:
                    for r in range(h // 22):
                        for c in range(w // 18):
                            hsh = (seed + r * 31 + c * 17) % 5
                            if hsh < 2:
                                if kind == "neon":
                                    wc = (0, 230, 230) if hsh == 0 else (255, 90, 200)
                                elif kind == "lava":
                                    wc = (255, 120, 40)
                                elif kind == "space":
                                    wc = (140, 220, 255)
                                elif kind == "finale":
                                    wc = (255, 120, 220) if hsh == 0 else (255, 255, 255)
                                else:
                                    wc = (255, 215, 120)
                                D.rect(s, wc, (x + 8 + c * 18, top + 10 + r * 22, 7, 10))
                else:
                    # дневные окна: тёмные стёкла
                    for r in range(h // 22):
                        for c in range(w // 18):
                            if (seed + r * 31 + c * 17) % 5 < 3:
                                D.rect(s, wcol, (x + 8 + c * 18, top + 10 + r * 22, 7, 10))
        s = fast(s, False)
        s.set_colorkey(KEYCOL)
        return self._put(key, (s, span))

    def blit_strip(self, surf, which, col, kind, speed):
        s, span = self.strip(which, col, kind)
        bx = -((self.t * speed) % span) - 150
        y = px(PLAT_TOP - STRIP_H)
        surf.blit(s, (px(bx), y))
        if bx + span < GW:
            surf.blit(s, (px(bx + span), y))

    # --- платформа, пути и всё, что лежит ниже горизонта: тоже один раз ---
    def ground(self, col):
        key = self._ck(col, ("ground",))
        s = self.cache.get(key)
        if s is not None:
            return s
        light = col["light"]
        s = pygame.Surface((GWP, HP))
        s.fill((0, 0, 0))
        # платформа: градиент, швы плитки, фаска
        top_c = lerp_c(col["plat"], (255, 255, 255), 0.10)
        bot_c = lerp_c(col["plat"], (0, 0, 0), 0.16)
        vband(s, 0, GW, PLAT_TOP, PLAT_BOT, top_c, bot_c)
        dark = lerp_c(col["plat"], (0, 0, 0), 0.20)
        lite = lerp_c(col["plat"], (255, 255, 255), 0.14)
        for x in range(0, GW, 80):
            D.line(s, dark, (x, PLAT_TOP + 4), (x - 10, PLAT_BOT - 9), 2)
            D.line(s, lite, (x + 2, PLAT_TOP + 4), (x - 8, PLAT_BOT - 9), 1)
        D.line(s, dark, (0, PLAT_TOP + 30), (GW, PLAT_TOP + 30), 1)
        D.line(s, lerp_c(col["plat"], (255, 255, 255), 0.4), (0, PLAT_TOP), (GW, PLAT_TOP), 3)
        # жёлтая полоса безопасности
        D.rect(s, (240, 205, 30), (0, PLAT_BOT - 9, GW, 9))
        D.line(s, (255, 235, 110), (0, PLAT_BOT - 9), (GW, PLAT_BOT - 9), 1)
        for x in range(0, GW, 28):
            D.polygon(s, (60, 50, 10), [(x, PLAT_BOT), (x + 12, PLAT_BOT),
                                        (x + 18, PLAT_BOT - 9), (x + 6, PLAT_BOT - 9)])
        # фронтальная стенка платформы: кирпичная кладка с градиентом
        fw_top = lerp_c(col["front"], (255, 255, 255), 0.06)
        fw_bot = lerp_c(col["front"], (0, 0, 0), 0.30)
        vband(s, 0, GW, PLAT_BOT, TRAIN_Y, fw_top, fw_bot)
        seam = lerp_c(col["front"], (0, 0, 0), 0.38)
        for row in range(3):
            yy = PLAT_BOT + row * 6
            D.line(s, seam, (0, yy), (GW, yy), 1)
            for x in range(12 if row % 2 else 0, GW, 24):
                D.line(s, seam, (x, yy), (x, yy + 6), 1)
        # путевая зона
        bed_top = lerp_c(col["bed"], (0, 0, 0), 0.38)
        bed_bot = lerp_c(col["bed"], (0, 0, 0), 0.12)
        for py in range(px(TRAIN_Y), HP):
            t = min(1.0, (py / K - TRAIN_Y) / 60)
            s.fill(lerp_c(bed_top, bed_bot, t), (0, py, GWP, 1))
        D.rect(s, lerp_c(col["bed"], (0, 0, 0), 0.30), (0, H - 80, GW, 80))
        for (gx, gy, gs, gv) in self.gravel:
            gc = lerp_c(col["bed"], (255, 255, 255) if gv > 0.5 else (0, 0, 0), 0.12 + 0.18 * gv)
            D.rect(s, gc, (gx, gy, gs + 1, gs))
        wood = lerp_c((105, 82, 62), (25, 22, 35), 0.6 * min(1.0, light))
        for x in range(-20, GW, 52):
            D.rect(s, lerp_c(wood, (0, 0, 0), 0.35), (x + 2, 601, 30, 46), border_radius=2)
            D.rect(s, wood, (x, 598, 30, 46), border_radius=2)
            D.line(s, lerp_c(wood, (255, 255, 255), 0.18), (x + 2, 600), (x + 28, 600), 2)
        for ry in (602, 636):
            D.rect(s, lerp_c(col["rail"], (0, 0, 0), 0.45), (0, ry + 3, GW, 5))
            D.rect(s, col["rail"], (0, ry, GW, 6))
            D.line(s, lerp_c(col["rail"], (255, 255, 255), 0.55), (0, ry), (GW, ry), 1)
        return self._put(key, fast(s, False))

    def draw_back(self, surf, col, kind, name):
        light = col["light"]
        surf.blit(self.sky(col, kind), (0, 0))

        if kind in STAR_KINDS:
            sz = max(1, int(K))
            for (x, y, ph) in self.stars:
                v = int(150 + 100 * math.sin(self.t * 2 + ph))
                v = max(0, min(255, v))
                surf.fill((v, v, v), (px(x), px(y), sz, sz))
                if v > 220:
                    glow(surf, (x, y), 6, (200, 210, 255), 90)
        if kind == "finale":
            self.draw_body(surf, col, kind)

        for (x, y, sc, _sp) in self.clouds:
            spr, ox, oy = self.cloud(sc, col["cloud"])
            surf.blit(spr, (px(x - ox), px(y - oy)))

        self.blit_strip(surf, "far2", col, kind, 3)
        self.blit_strip(surf, "far", col, kind, 6)
        self.blit_strip(surf, "near", col, kind, 14)

        # дымка у горизонта
        surf.blit(self.haze(col), (0, px(PLAT_TOP - 150)))

        # платформа и пути (готовая картинка)
        gy = px(PLAT_TOP)
        surf.blit(self.ground(col), (0, gy), (0, gy, GWP, HP - gy))

        # табличка станции
        for p in (200, 410):
            D.rect(surf, (45, 45, 58), (p - 3, 286, 6, PLAT_TOP - 286))
            D.rect(surf, (90, 90, 108), (p - 3, 286, 2, PLAT_TOP - 286))
        if light > 0.4:
            glow(surf, (305, 261), 170, (90, 150, 255), int(70 * light))
        D.rect(surf, (10, 14, 26), (183, 241, 250, 50), border_radius=8)
        D.rect(surf, (24, 60, 110), (180, 236, 250, 50), border_radius=8)
        D.rect(surf, (40, 92, 160), (183, 239, 244, 20), border_radius=6)
        D.rect(surf, (235, 240, 250), (180, 236, 250, 50), 3, border_radius=8)
        for bx in (190, 420):
            D.circle(surf, (255, 235, 150), (bx, 261), 2)
        text(surf, f"Станция «{name}»", f_mid, (255, 255, 255), (305, 250), center=True, shadow=False)

        # фонари
        for lx in (110, 500, 850):
            if light > 0.25:
                cone = LAMP_CONE
                cone.set_alpha(int(255 * min(1.0, light)))
                surf.blit(cone, (px(lx) - cone.get_width() // 2, px(282)))
            D.rect(surf, (40, 40, 52), (lx - 3, 270, 6, PLAT_TOP - 270))
            D.rect(surf, (80, 80, 98), (lx - 3, 270, 2, PLAT_TOP - 270))
            D.rect(surf, (40, 40, 52), (lx - 24, 262, 48, 10), border_radius=4)
            D.rect(surf, (74, 74, 90), (lx - 24, 262, 48, 3), border_radius=2)
            D.circle(surf, lerp_c((200, 200, 185), (255, 235, 160), light), (lx, 278), 7)
            if light > 0.25:
                glow(surf, (lx, 282), 130, (255, 230, 150), int(110 * light))

    def draw_front(self, surf, kind):
        if kind == "snow":
            for (x, y, _s, _d, r) in self.snow:
                D.circle(surf, (255, 255, 255), (int(x), int(y)), r)
                if r > 3:
                    D.circle(surf, (225, 236, 250), (int(x) + 1, int(y) + 1), r - 1)
        elif kind == "lava":
            for (x, y, _s, _d, r) in self.snow:
                glow(surf, (x, y), r * 4, (255, 120, 40), 90)
                D.circle(surf, (255, 190, 80), (int(x), int(y)), max(1, r - 1))
        elif kind == "rain":
            for (x, y, _s) in self.rain:
                D.line(surf, (175, 195, 220), (int(x), int(y)), (int(x) - 4, int(y) + 14), 1)
                if PLAT_BOT - 22 < y < PLAT_BOT - 14:     # всплеск на платформе
                    D.ellipse(surf, (200, 215, 235), (int(x) - 4, int(y) + 6, 8, 3), 1)
            if self.flash > 0:
                fs = self.flash_surface()
                fs.set_alpha(int(150 * self.flash))
                surf.blit(fs, (0, 0))


# ---------- объекты ----------
# обычный, жирный (несколько ударов), летающий (парит), спринтер (быстрый),
# бронированный (падает только от прямого клика), бомба (взрывается и сбивает соседей)
KIND_HP = {"normal": 1, "fat": 3, "fly": 2, "sprint": 1, "armor": 2, "bomb": 1}
KIND_VALUE = {"normal": 1, "fat": 3, "fly": 3, "sprint": 2, "armor": 2.5, "bomb": 2}

# реплики людей на платформе — для веселья
WALK_QUOTES = ("Я опаздываю!", "Где мой кофе?", "Какой хороший день", "Это моя остановка?",
               "Ммм, пончики", "Я забыл утюг!", "Не толкаться!", "Поезд не видели?",
               "Опять задерживают...", "Мама, я в телевизоре!")
FALL_QUOTES = ("А-А-А!", "Мама!", "Мой телефон!", "Только не это!", "Ой-ой-ой!", "Я не хочу!",
               "Передайте жене...")
BOMB_QUOTES = ("Тик-так...", "Я не бомба!", "Не трогай меня!", "Я просто пассажир")

# ---------- скины прохожих: награда за забеги в хардкоре ----------
# 0 («Классика») открыт всегда, остальные выдаются по одному за каждый
# проигранный забег — на платформе бегают люди в этих нарядах.
SKINS = [
    dict(name="Классика"),
    dict(name="Дед Мороз", color=(200, 44, 44), skin=(245, 210, 170), hair=(240, 240, 245), extra="hat"),
    dict(name="Киборг", color=(118, 130, 152), skin=(175, 185, 195), hair=(60, 66, 78), extra="visor"),
    dict(name="Призрак", color=(206, 228, 255), skin=(225, 235, 250), hair=(200, 215, 240),
         glow=(150, 200, 255)),
    dict(name="Неон", color=(40, 255, 200), skin=(198, 255, 240), hair=(20, 40, 36), glow=(0, 255, 200)),
    dict(name="Пират", color=(72, 52, 42), hair=(30, 24, 20), extra="tricorn", eyepatch=True),
    dict(name="Астронавт", color=(234, 240, 248), skin=(200, 210, 225), hair=(180, 190, 205),
         extra="helmet", glow=(180, 210, 255)),
    dict(name="Дьявол", color=(168, 32, 32), skin=(198, 62, 52), hair=(30, 12, 12),
         extra="horns", glow=(255, 70, 40)),
    dict(name="Золотой", color=(252, 202, 44), skin=(252, 224, 132), hair=(150, 110, 30),
         extra="crown", glow=(255, 210, 60)),
    dict(name="Кот", color=(92, 92, 122), hair=(40, 40, 56), extra="ears"),
    dict(name="Король", color=(122, 44, 162), hair=(24, 18, 30), extra="crown", glow=(200, 120, 255)),
    dict(name="Ледяной", color=(122, 192, 242), skin=(214, 238, 255), hair=(230, 246, 255),
         glow=(140, 210, 255)),
]


def pick_skin(s):
    """Шанс украсить прохожего одним из уже открытых нарядов."""
    n = max(1, min(len(SKINS), s.get("skins", 1)))
    if n > 1 and random.random() < 0.3:
        return random.randrange(1, n)
    return 0


def skull_chance(level, base):
    """Череп летит в камеру всё реже — с каждым новым уровнем в 0.7 раза."""
    return max(0.004, base * 0.7 ** level)


def pick_kind(kills):
    """Чем дальше игрок, тем разнообразнее (и злее) публика на платформе."""
    ramp = 1.0 + min(1.0, kills / 2500.0)
    pool = [("normal", 100)]
    for kind, w, need in (("fat", 16, 30), ("bomb", 9, 45), ("sprint", 14, 80),
                          ("fly", 12, 200), ("armor", 12, 400)):
        if kills >= need:
            pool.append((kind, w * ramp))
    total = sum(w for _, w in pool)
    r = random.uniform(0, total)
    for kind, w in pool:
        r -= w
        if r <= 0:
            return kind
    return "normal"


class Person:
    def __init__(self, gold, kind="normal", skin_idx=0):
        self.gold = gold
        self.kind = kind
        self.max_hp = self.hp = KIND_HP[kind]
        self.value = KIND_VALUE[kind]
        self.hit_t = 0.0
        self.dir = random.choice([-1, 1])
        self.x = -30 if self.dir == 1 else GW + 30
        self.y = PLAT_TOP
        self.vx = self.dir * random.uniform(40, 90)
        self.vy = 0
        self.state = "walk"
        self.entered = False           # уже зашёл на платформу (для хардкора)
        self.timer = 0
        self.rot = 0.0
        self.boom = False              # бомба упала и ждёт взрыва
        self.quote = ""
        self.quote_t = 0.0
        self.quote_cd = random.uniform(1.5, 9.0)
        self.color = (255, 200, 0) if gold else random.choice(
            [(220, 70, 70), (70, 140, 220), (90, 190, 100), (230, 130, 60), (170, 90, 200), (60, 180, 180)])
        self.skin = random.choice([(245, 210, 170), (225, 180, 135), (190, 140, 100), (140, 100, 70)])
        self.hair = random.choice([(40, 30, 25), (90, 60, 35), (200, 170, 80), (30, 30, 30), (150, 60, 40)])
        self.hat = random.choice([None, None, None, (60, 60, 80), (200, 60, 60), (60, 120, 200)])
        self.pants = (40, 45, 70)
        self.long_hair = False
        self.phase = random.uniform(0, 6)
        if kind == "armor":
            self.color = (112, 120, 140)          # бронежилет
        elif kind == "fly":
            self.color = (96, 176, 236)           # лётный комбинезон
        elif kind == "fat":
            self.color = random.choice([(210, 120, 60), (150, 90, 170), (70, 150, 130)])
        elif kind == "bomb":
            self.color = (58, 60, 74)             # тёмная куртка со взрывчаткой на груди
        # наряд из награды хардкора перекрашивает человека
        self.skin_idx = skin_idx if 0 < skin_idx < len(SKINS) else 0
        if self.skin_idx and kind != "bomb":
            sk = SKINS[self.skin_idx]
            self.color = sk.get("color", self.color)
            self.skin = sk.get("skin", self.skin)
            self.hair = sk.get("hair", self.hair)
            if sk.get("extra"):
                self.hat = None
        elif kind == "bomb":
            self.skin_idx = 0
        if kind == "sprint":
            self.vx *= 1.9                        # спринтер вдвое быстрее
        elif kind == "fat":
            self.vx *= 0.75                       # жирный волочится

    def say(self, txt, dur=1.8):
        self.quote = txt
        self.quote_t = dur

    def rect(self):
        return pygame.Rect(self.x - 18, self.y - 82, 36, 86)

    def push(self, direct=False):
        """Один удар. True — человек упал на пути."""
        if self.state != "walk":
            return False
        if self.kind == "armor" and not direct:
            return False          # броня держит удар по площади — нужен точный клик
        self.hp -= 1
        self.hit_t = 0.25
        if self.hp > 0:
            self.x -= self.dir * 12      # отшатнулся, но устоял
            return False
        self.state = "fall"
        self.vy = -150
        self.vx = self.dir * 40
        if self.kind == "bomb":
            self.boom = True
            self.say("ТИК-ТАК... БУМ!", 1.0)
        elif random.random() < 0.55:
            self.say(random.choice(FALL_QUOTES), 1.4)
        return True

    def update(self, dt):
        self.phase += dt * 8
        self.hit_t = max(0.0, self.hit_t - dt)
        self.quote_t = max(0.0, self.quote_t - dt)
        if self.state == "walk":
            self.x += self.vx * dt
            if 0 <= self.x <= GW:
                self.entered = True
                self.quote_cd -= dt
                if self.quote_cd <= 0:
                    self.quote_cd = random.uniform(6.0, 13.0)
                    if self.quote_t <= 0 and random.random() < 0.6:
                        pool = BOMB_QUOTES if self.kind == "bomb" else WALK_QUOTES
                        self.say(random.choice(pool), 2.0)
            if self.kind == "fly":
                # летун парит над платформой — сбить его сложнее
                self.y = PLAT_TOP - 68 - 18 * math.sin(self.phase * 0.55)
        elif self.state == "fall":
            self.vy += 900 * dt
            self.y += self.vy * dt
            self.x += self.vx * dt
            self.rot += self.dir * 420 * dt
            if self.y >= TRACK_Y:
                self.y = TRACK_Y
                self.state = "track"
                self.timer = 5.0
                self.vx = 0
                self.rot = 0.0
        elif self.state == "track":
            self.timer -= dt

    def draw(self, surf, warn=False):
        x, y = int(self.x), int(self.y)
        if self.state in ("walk", "track"):
            # тень летуна падает на платформу, а не летит вместе с ним
            gy = PLAT_TOP if (self.kind == "fly" and self.state == "walk") else y
            blit(surf, SHADOW_S, (x - 23, gy - 7))
        if self.gold and self.state == "walk":
            glow(surf, (x, y - 50), 60, (255, 215, 60), 90)
        if self.kind == "bomb" and self.state == "walk":
            blink = int(pygame.time.get_ticks() / 220) % 2 == 0
            glow(surf, (x, y - 44), 46 if blink else 34, (255, 70, 40), 110 if blink else 60)
        sk = SKINS[self.skin_idx] if self.skin_idx else None
        if sk and sk.get("glow") and self.state == "walk":
            glow(surf, (x, y - 50), 58, sk["glow"], 70)   # скин светится
        fig = self.sprite()
        if self.hit_t > 0:            # вспышка при попадании
            fig = fig.copy()
            fig.fill((120, 120, 120), special_flags=pygame.BLEND_RGB_ADD)
        if self.state == "fall":
            fig = pygame.transform.rotate(fig, -self.rot)
        blit_c(surf, fig, x, y - 40)
        if self.max_hp > 1 and self.state == "walk":
            # сколько ударов ещё держится
            bw, gap = 9, 3
            x0 = x - (self.max_hp * (bw + gap) - gap) // 2
            for i in range(self.max_hp):
                c = (240, 90, 80) if i < self.hp else (58, 58, 70)
                D.rect(surf, (10, 10, 16), (x0 + i * (bw + gap) - 1, y - 117, bw + 2, 8), border_radius=3)
                D.rect(surf, c, (x0 + i * (bw + gap), y - 116, bw, 6), border_radius=2)
        if self.state == "track":
            text(surf, "!" if self.timer > 2 else "!!", f_mid, (255, 70, 60), (x - 4, y - 118))
        elif warn and self.state == "walk" and (
                (self.dir > 0 and self.x > GW - 130) or (self.dir < 0 and self.x < 130)):
            # хардкор: человек почти дошёл до края и сейчас уйдёт с платформы
            text(surf, "!", f_mid, (255, 60, 50), (x, y - 134), center=True)
        if self.quote_t > 0 and self.state in ("walk", "fall") and self.quote:
            # облачко с репликой
            bw = int(twidth(f_small, self.quote)) + 16
            by = int(y - 160) if self.state == "walk" else int(y - 130)
            bx = max(2, min(GW - bw - 2, x - bw // 2))
            plate(surf, (bx, by, bw, 22), 235, 9, color=(250, 250, 255), border=(40, 40, 60, 200))
            text(surf, self.quote, f_small, (22, 22, 40), (bx + bw // 2, by + 3), center=True, shadow=False)

    def sprite(self, zoom=1.0, deco=None, deco_key=None):
        """Готовая картинка человека; кадры анимации кэшируются (шаг ноги — 2 px)."""
        d = self.dir
        scared = self.state in ("fall", "track")
        if self.state == "walk":
            swing = math.sin(self.phase) * 10
        elif self.state == "fall":
            swing = math.sin(self.phase * 3) * 22
        else:
            swing = math.sin(self.phase * 2) * 4
        sq = int(round(swing / 2.0)) * 2
        flap = int(round(math.sin(self.phase * 3) * 3.5)) * 2 if self.kind == "fly" else 0
        key = (K, zoom, deco_key, self.kind, d, scared, sq, flap, self.gold, self.skin_idx,
               self.color, self.skin, self.hair, self.hat, self.pants, self.long_hair)
        fig = SPR.get(key)
        if fig is None:
            fig = self._build(sq, flap, scared, zoom, deco)
            SPR[key] = fig
            if len(SPR) > 600:
                for _ in range(150):
                    SPR.pop(next(iter(SPR)))
        return fig

    def _build(self, swing, flap, scared, zoom, deco):
        global KD
        KD = K * zoom
        try:
            fig = new_surf(90, 120, zoom=zoom)
            cx, fy = 45, 100
            d = self.dir
            pants = self.pants
            lo = 10 if self.kind == "fat" else 7      # у жирного пошире стойка
            lw = 8 if self.kind == "fat" else 6
            D.line(fig, pants, (cx, fy - 30), (cx - lo + swing, fy - 3), lw)
            D.line(fig, pants, (cx, fy - 30), (cx + lo - swing, fy - 3), lw)
            shoe = (25, 25, 30)
            D.ellipse(fig, shoe, (int(cx - lo + swing) - 5 + 2 * d, fy - 6, 11, 7))
            D.ellipse(fig, shoe, (int(cx + lo - swing) - 5 + 2 * d, fy - 6, 11, 7))
            if self.kind == "sprint":      # полосы скорости позади
                for k in range(3):
                    yy = fy - 66 + k * 14
                    D.line(fig, (255, 255, 255), (cx - 24 * d, yy), (cx - (36 + 7 * k) * d, yy), 2)
            if self.long_hair:      # длинные волосы за спиной
                D.rect(fig, self.hair, (cx - 14, fy - 83, 28, 52), border_radius=11)
            if self.kind == "fly":       # крылья уходят назад за спину
                for sgn in (-1, 1):
                    wx = cx + sgn * 8
                    pts = [(wx, fy - 60),
                           (wx + sgn * 32, fy - 74 - flap),
                           (wx + sgn * 40, fy - 58),
                           (wx + sgn * 26, fy - 44)]
                    D.polygon(fig, (224, 240, 255), pts)
                    D.polygon(fig, (150, 190, 235), pts, 2)
            D.rect(fig, self.color, (cx - 9, fy - 62, 18, 34), border_radius=6)
            if self.kind == "fat":
                D.rect(fig, self.color, (cx - 17, fy - 58, 34, 40), border_radius=13)
                D.ellipse(fig, lerp_c(self.color, (255, 255, 255), 0.22), (cx - 11, fy - 44, 22, 24))
            else:
                # блик на одежде и ремень
                D.rect(fig, lerp_c(self.color, (255, 255, 255), 0.25), (cx - 7, fy - 60, 4, 26), border_radius=2)
                D.rect(fig, lerp_c(self.color, (0, 0, 0), 0.4), (cx - 9, fy - 34, 18, 4))
            if self.kind == "bomb":       # круглая бомба с красной лампочкой на груди
                D.rect(fig, (200, 60, 50), (cx - 10, fy - 52, 20, 3))
                D.circle(fig, (22, 22, 28), (cx, fy - 44), 9)
                D.circle(fig, (70, 72, 86), (cx - 3, fy - 47), 3)
                D.line(fig, (200, 160, 90), (cx + 3, fy - 52), (cx + 8, fy - 58), 2)
                D.circle(fig, (255, 210, 70), (cx + 8, fy - 58), 2)
                D.circle(fig, (255, 60, 40), (cx, fy - 41), 2)
            arm_y = -44 if scared else -38
            aw = 7 if self.kind == "fat" else 5
            ax = 19 if self.kind == "fat" else 13
            D.line(fig, self.color, (cx, fy - 56), (cx - ax - swing, fy + arm_y), aw)
            D.line(fig, self.color, (cx, fy - 56), (cx + ax + swing, fy + arm_y), aw)
            D.circle(fig, self.skin, (int(cx - ax - swing), fy + arm_y), 4 if aw > 5 else 3)
            D.circle(fig, self.skin, (int(cx + ax + swing), fy + arm_y), 4 if aw > 5 else 3)
            D.circle(fig, self.hair, (cx, fy - 76), 11)
            D.circle(fig, self.skin, (cx, fy - 71), 10)
            D.circle(fig, lerp_c(self.skin, (255, 255, 255), 0.18), (cx - 3 * d, fy - 74), 4)
            if self.long_hair:      # пряди по бокам лица
                D.rect(fig, self.hair, (cx - 12, fy - 77, 4, 26), border_radius=2)
                D.rect(fig, self.hair, (cx + 8, fy - 77, 4, 26), border_radius=2)
            if self.hat:
                D.rect(fig, self.hat, (cx - 11, fy - 86, 22, 6), border_radius=2)
                D.rect(fig, self.hat, (cx - 7, fy - 93, 14, 9), border_radius=3)
                D.rect(fig, lerp_c(self.hat, (255, 255, 255), 0.25), (cx - 7, fy - 93, 14, 2), border_radius=1)
            if self.kind == "armor":      # шлем с визором и наплечники
                D.ellipse(fig, (128, 138, 158), (cx - 22, fy - 64, 13, 16))
                D.ellipse(fig, (128, 138, 158), (cx + 9, fy - 64, 13, 16))
                D.rect(fig, (156, 166, 186), (cx - 13, fy - 87, 26, 13), border_radius=6)
                D.rect(fig, (40, 44, 56), (cx - 11, fy - 79, 22, 5), border_radius=2)
            if scared:
                for ex in (cx + 2 * d, cx + 8 * d):
                    D.circle(fig, (255, 255, 255), (ex, fy - 73), 3)
                    D.circle(fig, (0, 0, 0), (ex, fy - 73), 1)
                D.ellipse(fig, (90, 20, 20), (cx + 4 * d - 3, fy - 67, 6, 5))
            else:
                for ex in (cx + 2 * d, cx + 7 * d):
                    D.circle(fig, (20, 20, 20), (ex, fy - 73), 2)
                D.line(fig, (120, 60, 50), (cx + 3 * d, fy - 66), (cx + 8 * d, fy - 66), 1)
                D.circle(fig, (240, 140, 130), (cx + 8 * d, fy - 69), 2)
            if self.gold:
                D.polygon(fig, (255, 215, 0),
                          [(cx - 9, fy - 84), (cx - 6, fy - 95), (cx, fy - 86), (cx + 6, fy - 95), (cx + 9, fy - 84)])
            if self.skin_idx:      # аксессуары скина поверх обычного наряда
                sk = SKINS[self.skin_idx]
                ex = sk.get("extra")
                if ex == "hat":        # дед-морозовский колпак
                    D.polygon(fig, (200, 44, 44), [(cx - 12, fy - 84), (cx + 12, fy - 84),
                                                   (cx + 5 * d, fy - 99)])
                    D.rect(fig, (242, 244, 250), (cx - 13, fy - 89, 26, 7), border_radius=3)
                    D.circle(fig, (250, 252, 255), (int(cx + 5 * d), fy - 99), 3)
                elif ex == "visor":    # светящийся визор
                    D.rect(fig, (40, 255, 200), (cx - 11, fy - 76, 22, 5), border_radius=2)
                    D.rect(fig, (140, 255, 230), (cx - 10, fy - 76, 10, 2), border_radius=1)
                elif ex == "tricorn":  # пиратская шляпа
                    D.polygon(fig, (45, 35, 30), [(cx - 17, fy - 79), (cx + 17, fy - 79), (cx, fy - 95)])
                    D.line(fig, (82, 64, 50), (cx - 15, fy - 80), (cx + 15, fy - 80), 2)
                elif ex == "helmet":   # стеклянный шлем
                    D.circle(fig, (190, 210, 235), (cx, fy - 72), 16, 2)
                    D.circle(fig, (238, 246, 255), (cx - 5, fy - 80), 3)
                elif ex == "horns":    # рога
                    D.polygon(fig, (255, 90, 60), [(cx - 11, fy - 83), (cx - 4, fy - 84),
                                                   (cx - 10, fy - 96)])
                    D.polygon(fig, (255, 90, 60), [(cx + 11, fy - 83), (cx + 4, fy - 84),
                                                   (cx + 10, fy - 96)])
                elif ex == "ears":     # кошачьи ушки
                    D.polygon(fig, self.color, [(cx - 11, fy - 83), (cx - 3, fy - 85),
                                                (cx - 8, fy - 95)])
                    D.polygon(fig, self.color, [(cx + 11, fy - 83), (cx + 3, fy - 85),
                                                (cx + 8, fy - 95)])
                elif ex == "crown":    # корона
                    D.polygon(fig, (255, 210, 50),
                              [(cx - 10, fy - 84), (cx - 10, fy - 95), (cx - 5, fy - 88),
                               (cx, fy - 97), (cx + 5, fy - 88), (cx + 10, fy - 95), (cx + 10, fy - 84)])
                if sk.get("eyepatch"):
                    D.line(fig, (15, 15, 18), (cx - 10, fy - 78), (cx + 12 * d, fy - 78), 1)
                    D.rect(fig, (15, 15, 18), (cx + 2 * d - 3, fy - 77, 7, 6), border_radius=2)
            fig = outlined(fig)
            if deco:
                deco(fig)
            return fast(fig)
        finally:
            KD = K


class Boss:
    SCALE = 1.8
    secret = False

    def __init__(self, level):
        d = BOSSES[level]
        self.level = level
        self.name = d["name"]
        self.max_hp = self.hp = float(d["hp"]) * BOSS_HP_MULT
        self.speed = d["speed"]
        self.flags = d["flags"]
        self.time_left = float(d["time"]) * BOSS_TIME_MULT
        self.x = GW - 150
        self.y = PLAT_TOP
        self.dir = -1
        self.vx = 0.0
        self.vy = 0.0
        self.rot = 0.0
        self.state = "fight"      # fight / fall / track / gone
        self.timer = 0.0
        self.hit_t = 0.0
        self.regen_t = 0.0
        self.cycle = 0.0
        self.turn_t = 1.5
        self.blink_t = 3.0
        self.hidden = False
        self.shield = False
        self.landed = False
        self.acid_t = random.uniform(4.0, 7.0)   # когда плевнёт кислотой
        self.spit = False                        # main забирает и запускает снаряд
        self.events = []
        self.healing = 0.0
        self.heal_t = random.uniform(5.0, 8.0)
        self.heal_taken = 0.0
        self.steal_t = random.uniform(10.0, 14.0)
        self.frenzy = 0.0
        self.frenzy_t = random.uniform(8.0, 12.0)
        self.wind_used = False
        self.last_dmg = 0
        body = Person(False)
        body.color, body.skin, body.hair, body.hat = d["color"], d["skin"], d["hair"], d["hat"]
        body.pants = d.get("pants", (40, 45, 70))
        body.long_hair = d.get("long_hair", False)
        self.body = body

    def rect(self):
        return pygame.Rect(self.x - 32, self.y - 175, 64, 180)

    def hit(self, dmg):
        if self.state != "fight" or self.hidden:
            return "miss"
        if self.shield:
            return "block"
        if "dodge" in self.flags and random.random() < 0.15:
            return "dodge"
        if "tough" in self.flags:
            dmg = max(1, int(dmg * 0.75))
        self.last_dmg = dmg
        self.hp -= dmg
        self.hit_t = 0.15
        self.regen_t = 2.0
        if self.healing > 0:
            self.heal_taken += dmg
            if self.heal_taken >= self.max_hp * 0.05:
                self.healing = 0.0
                self.events.append(("ПРЕРВАНО!", (255, 220, 90)))
        if "wind" in self.flags and not self.wind_used and 0 < self.hp <= self.max_hp * 0.2:
            self.wind_used = True
            self.hp = self.max_hp * 0.45
            self.events.append(("ВТОРОЕ ДЫХАНИЕ!", (150, 255, 170)))
        if self.hp <= 0:
            self.hp = 0
            self.state = "fall"
            self.vy = -320
            self.vx = self.dir * 70
        return "ok"

    def update(self, dt):
        self.body.phase += dt * 8
        self.hit_t = max(0.0, self.hit_t - dt)
        f = self.flags
        if self.state == "fight":
            self.time_left -= dt
            self.cycle += dt
            if "erratic" in f:
                self.turn_t -= dt
                if self.turn_t <= 0:
                    self.dir = random.choice([-1, 1])
                    self.turn_t = random.uniform(0.8, 2.2)
            spd = self.speed
            if "rage" in f and self.hp < self.max_hp * 0.5:
                spd *= 1.8
            if self.frenzy > 0:
                self.frenzy -= dt
                spd *= 2.0
            if self.healing > 0:
                spd = 0
            self.x += self.dir * spd * dt
            if "blink" in f:
                self.blink_t -= dt
                if self.blink_t <= 0:
                    self.x = random.uniform(150, GW - 150)
                    self.blink_t = random.uniform(2.5, 4.0)
            if self.x < 130:
                self.x, self.dir = 130, 1
            if self.x > GW - 130:
                self.x, self.dir = GW - 130, -1
            if "ghost" in f:
                self.hidden = (self.cycle % 3.0) > 2.0
            if "shield" in f:
                period = 5.0 if "erratic" in f else 4.0
                self.shield = (self.cycle % period) > period - 1.5
            if "regen" in f:
                if self.regen_t > 0:
                    self.regen_t -= dt
                else:
                    self.hp = min(self.max_hp, self.hp + max(4.0, self.max_hp * 0.008) * dt)
            if "acid" in f:                  # плевок кислотой
                self.acid_t -= dt
                if self.acid_t <= 0:
                    self.spit = True
                    self.acid_t = random.uniform(6.0, 9.0)
            if "heal" in f:
                if self.healing > 0:
                    self.healing -= dt
                    self.hp = min(self.max_hp, self.hp + self.max_hp * 0.07 * dt)
                else:
                    self.heal_t -= dt
                    if self.heal_t <= 0:
                        if self.hp < self.max_hp * 0.85:
                            self.healing = 2.5
                            self.heal_taken = 0.0
                            self.events.append(("ЛЕЧИТСЯ!", (150, 255, 170)))
                            self.heal_t = random.uniform(9.0, 13.0)
                        else:
                            self.heal_t = 3.0
            if "timesteal" in f:
                self.steal_t -= dt
                if self.steal_t <= 0:
                    self.steal_t = random.uniform(11.0, 15.0)
                    self.time_left -= 4
                    self.events.append(("-4 СЕК!", (255, 120, 120)))
            if "frenzy" in f and self.frenzy <= 0:
                self.frenzy_t -= dt
                if self.frenzy_t <= 0:
                    self.frenzy = 4.0
                    self.frenzy_t = random.uniform(10.0, 14.0)
                    self.events.append(("ЯРОСТЬ!", (255, 90, 70)))
            if self.time_left <= 0:
                self.state = "gone"
        elif self.state == "fall":
            self.hidden = False
            self.shield = False
            self.vy += 900 * dt
            self.y += self.vy * dt
            self.x += self.vx * dt
            self.rot += self.dir * 300 * dt
            if self.y >= TRACK_Y:
                self.y = TRACK_Y
                self.state = "track"
                self.timer = 20.0
                self.vx = 0.0
                self.rot = 0.0
                self.landed = True
        elif self.state == "track":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "gone"

    def _auras(self, surf, x, cy, ty):
        t = pygame.time.get_ticks()
        if self.healing > 0:
            glow(surf, (x, cy), 120, (90, 255, 130), 110)
            D.circle(surf, (150, 255, 170), (x, cy), int(70 + 8 * math.sin(t / 90.0)), 2)
            text(surf, "ЛЕЧИТСЯ! БЕЙ!", f_small, (150, 255, 170), (x, ty), center=True)
        if self.frenzy > 0:
            glow(surf, (x, cy), 130, (255, 60, 40), 110)
            text(surf, "ЯРОСТЬ!", f_small, (255, 110, 90), (x, ty), center=True)

    def _deco(self, fig):
        """Особые приметы боссов; рисуются в координатах спрайта 90x120 (с зумом)."""
        if self.level == 3:      # морковка-нос
            D.circle(fig, (255, 140, 30), (45 + 12 * self.dir, 28), 3)
        if self.level == 5:      # красный визор
            D.rect(fig, (255, 40, 40), (36, 27, 18, 2))
        if self.level == 8:      # антенны пришельца
            for ax in (-6, 6):
                D.line(fig, (60, 200, 120), (45 + ax, 6), (45 + ax * 2, 3), 2)

    def draw(self, surf):
        S = self.SCALE
        x, y = int(self.x), int(self.y)
        if self.state in ("fight", "track"):
            blit(surf, SHADOW_B, (x - 45, y - 11))
        if self.state == "fight":
            enraged = "rage" in self.flags and self.hp < self.max_hp * 0.5
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 140.0)
            if enraged:
                glow(surf, (x, y - 85), 130, (255, 50, 30), int(80 + 70 * pulse))
            elif self.hp < self.max_hp * 0.25:
                glow(surf, (x, y - 85), 110, (255, 90, 60), 50)
        b = self.body
        b.state = "walk" if self.state == "fight" else ("fall" if self.state == "fall" else "track")
        b.dir = self.dir
        fig = b.sprite(zoom=S, deco=self._deco, deco_key=("boss", self.level))
        if self.hit_t > 0 or self.hidden:
            fig = fig.copy()
            if self.hit_t > 0:
                fig.fill((90, 90, 90), special_flags=pygame.BLEND_RGB_ADD)
            if self.hidden:
                fig.set_alpha(60)
        if self.state == "fall":
            fig = pygame.transform.rotate(fig, -self.rot)
        blit_c(surf, fig, x, int(y - 40 * S))
        self._auras(surf, x, y - 85, y - 218)
        if self.shield:
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 120.0)
            glow(surf, (x, y - 85), 105, (110, 180, 255), 130)
            D.circle(surf, (170, 215, 255), (x, y - 85), 78, 3)
            D.circle(surf, (210, 235, 255), (x, y - 85), 72 + int(4 * pulse), 1)
            if self.level == 4:
                D.line(surf, (60, 60, 70), (x, y - 165), (x, y - 110), 3)
                D.polygon(surf, (40, 60, 140), [(x - 60, y - 165), (x - 40, y - 195),
                                                (x, y - 205), (x + 40, y - 195), (x + 60, y - 165)])
        if self.state == "fight":
            plate(surf, (x - 50, y - 197, 100, 19), 170, 8)
            D.rect(surf, (20, 20, 30), (x - 45, y - 192, 90, 9), border_radius=4)
            if self.hp > 0:
                fw = max(1, int(90 * self.hp / self.max_hp))
                D.rect(surf, (225, 55, 55), (x - 45, y - 192, fw, 9), border_radius=4)
                D.rect(surf, (255, 130, 120), (x - 45, y - 192, fw, 3), border_radius=2)
            D.rect(surf, (255, 255, 255), (x - 45, y - 192, 90, 9), 1, border_radius=4)


# ---------- секретные мини-боссы: по одному на каждый уровень ----------
# Появляются случайно (если не пора на обычного босса), у них больше HP, чем у основного,
# а награда втрое-вчетверо жирнее. Уровень при победе над ними не растёт.
SECRET_BOSSES = [
    dict(name="Голубь-мутант", kind="pigeon", hp=120, speed=100, time=60, flags=("erratic",)),
    dict(name="Кот-ниндзя", kind="cat", hp=200, speed=170, time=60, flags=("erratic",)),
    dict(name="Граф Вампир", kind="bat", hp=290, speed=120, time=65, flags=("ghost", "blink")),
    dict(name="Йети", kind="yeti", hp=400, speed=80, time=65, flags=("regen", "rage")),
    dict(name="Жаба-гроза", kind="frog", hp=520, speed=110, time=70, flags=("shield", "erratic")),
    dict(name="Робот-Терминатор", kind="robot", hp=700, speed=100, time=75, flags=("shield", "regen")),
    dict(name="Король скорпионов", kind="scorpion", hp=900, speed=140, time=75,
         flags=("erratic", "acid", "regen")),
    dict(name="Динозавр", kind="dino", hp=1150, speed=90, time=80, flags=("rage", "regen", "shield")),
    dict(name="Космический осьминог", kind="octopus", hp=1500, speed=130, time=85,
         flags=("ghost", "blink", "acid", "erratic")),
    dict(name="Страж Бездны", kind="skull", hp=2200, speed=150, time=100,
         flags=("erratic", "shield", "regen", "ghost", "rage", "acid", "blink")),
]
_EXTRA = {0: ("heal",), 1: ("dodge",), 2: ("heal",), 3: ("tough", "wind"),
          4: ("dodge", "timesteal"), 5: ("heal", "tough"), 6: ("dodge", "frenzy"),
          7: ("tough", "heal", "timesteal"), 8: ("dodge", "frenzy", "wind"),
          9: ("heal", "dodge", "tough", "timesteal", "frenzy", "wind")}
_EXTRA_S = {0: ("dodge",), 1: ("heal",), 2: ("dodge", "timesteal"), 3: ("tough", "heal"),
            4: ("heal", "wind"), 5: ("dodge", "tough"), 6: ("frenzy", "heal"),
            7: ("timesteal", "tough"), 8: ("heal", "dodge", "wind"),
            9: ("heal", "dodge", "tough", "timesteal", "frenzy", "wind")}
for _i, _f in _EXTRA.items():
    BOSSES[_i]["flags"] = tuple(BOSSES[_i]["flags"]) + _f
for _i, _f in _EXTRA_S.items():
    SECRET_BOSSES[_i]["flags"] = tuple(SECRET_BOSSES[_i]["flags"]) + _f
HOVER = {"bat": -34, "octopus": -26, "skull": -30}      # эти боссы парят над платформой


def _c_pigeon(fig, p, q):
    grey, dk, lt = (150, 160, 178), (108, 118, 138), (196, 204, 218)
    D.polygon(fig, dk, [(52, 128), (14, 148), (18, 168), (60, 158)])
    for sg in (1, -1):
        lx = 110 + sg * 10 + p * sg * 8
        D.line(fig, (240, 150, 50), (110 + sg * 10, 188), (lx, 211), 6)
        D.line(fig, (240, 150, 50), (lx, 211), (lx + 16, 213), 5)
    D.ellipse(fig, grey, (46, 110, 128, 84))
    D.ellipse(fig, lt, (70, 138, 84, 48))
    D.ellipse(fig, dk, (54, 118, 82, 50))
    D.ellipse(fig, (70, 170, 120), (138, 104, 36, 30))
    D.circle(fig, grey, (176, 96), 26)
    D.circle(fig, lt, (168, 90), 8)
    D.polygon(fig, (250, 170, 40), [(196, 92), (228, 102), (196, 112)])
    D.circle(fig, (255, 255, 255), (184, 90), 7)
    D.circle(fig, (210, 30, 30), (186, 91), 4)
    D.line(fig, (20, 20, 30), (174, 80), (194, 88), 3)


def _c_cat(fig, p, q):
    orange, dk, lt = (226, 142, 58), (176, 98, 36), (250, 214, 160)
    D.lines(fig, orange, False, [(54, 140), (26, 120 + p * 10), (20, 86 + p * 12), (36, 60 + p * 10)], 12)
    for lx, off in ((70, p), (92, -p), (148, -p), (170, p)):
        D.rect(fig, dk, (lx - 8 + off * 6, 160, 16, 50), border_radius=6)
        D.ellipse(fig, orange, (lx - 12 + off * 6, 200, 26, 14))
    D.ellipse(fig, orange, (50, 104, 140, 84))
    D.ellipse(fig, lt, (78, 150, 86, 34))
    for sx in (76, 104, 132):
        D.line(fig, dk, (sx, 108), (sx - 6, 132), 5)
    D.circle(fig, orange, (188, 104), 34)
    D.polygon(fig, orange, [(164, 84), (166, 50), (188, 74)])
    D.polygon(fig, orange, [(196, 72), (214, 48), (220, 92)])
    D.polygon(fig, (240, 150, 150), [(168, 78), (169, 60), (182, 74)])
    D.rect(fig, (210, 30, 40), (158, 82, 60, 9))
    D.polygon(fig, (210, 30, 40), [(158, 86), (140, 100 + p * 4), (144, 84)])
    D.ellipse(fig, (255, 235, 60), (190, 96, 16, 12))
    D.ellipse(fig, (255, 235, 60), (166, 98, 14, 11))
    D.line(fig, (10, 10, 10), (198, 94), (198, 108), 3)
    D.circle(fig, (240, 120, 130), (218, 112), 5)
    D.line(fig, (255, 255, 255), (214, 118), (240, 110), 2)
    D.line(fig, (255, 255, 255), (214, 122), (240, 126), 2)


def _c_bat(fig, p, q):
    fl = p * 14
    for sg in (-1, 1):
        c0 = 120
        pts = [(c0 + sg * 14, 96), (c0 + sg * 70, 40 - fl), (c0 + sg * 112, 70 - fl),
               (c0 + sg * 96, 98), (c0 + sg * 78, 92), (c0 + sg * 64, 122),
               (c0 + sg * 44, 106), (c0 + sg * 26, 140)]
        D.polygon(fig, (74, 42, 104), pts)
        D.polygon(fig, (40, 20, 70), pts, 3)
    D.ellipse(fig, (52, 34, 70), (94, 80, 52, 92))
    D.ellipse(fig, (84, 62, 104), (104, 104, 32, 50))
    D.polygon(fig, (150, 20, 40), [(100, 96), (140, 96), (152, 116), (88, 116)])
    D.circle(fig, (62, 42, 84), (120, 72), 26)
    D.polygon(fig, (62, 42, 84), [(100, 60), (96, 26), (116, 50)])
    D.polygon(fig, (62, 42, 84), [(140, 60), (144, 26), (124, 50)])
    for ex in (110, 130):
        D.circle(fig, (255, 40, 40), (ex, 70), 6)
        D.circle(fig, (255, 220, 200), (ex, 69), 2)
    D.polygon(fig, (255, 255, 255), [(113, 86), (118, 86), (115, 99)])
    D.polygon(fig, (255, 255, 255), [(122, 86), (127, 86), (125, 99)])
    D.line(fig, (52, 34, 70), (112, 168), (106, 190), 6)
    D.line(fig, (52, 34, 70), (128, 168), (134, 190), 6)


def _c_yeti(fig, p, q):
    fur, sh, belly = (236, 242, 250), (188, 204, 226), (214, 226, 242)
    D.rect(fig, sh, (84, 170, 32, 40), border_radius=10)
    D.rect(fig, sh, (124, 170, 32, 40), border_radius=10)
    D.ellipse(fig, fur, (76, 198, 44, 18))
    D.ellipse(fig, fur, (120, 198, 44, 18))
    D.line(fig, fur, (86, 100), (52, 150 + p * 12), 24)
    D.line(fig, fur, (154, 100), (192, 150 - p * 12), 24)
    D.circle(fig, sh, (52, 152 + p * 12), 14)
    D.circle(fig, sh, (192, 152 - p * 12), 14)
    D.ellipse(fig, fur, (70, 80, 100, 110))
    D.ellipse(fig, belly, (92, 112, 56, 62))
    D.circle(fig, fur, (120, 68), 34)
    D.ellipse(fig, (128, 160, 214), (98, 56, 44, 40))
    for ex in (110, 130):
        D.circle(fig, (255, 255, 255), (ex, 66), 6)
        D.circle(fig, (20, 40, 90), (ex, 67), 3)
    D.line(fig, (30, 50, 100), (102, 57), (116, 64), 3)
    D.line(fig, (30, 50, 100), (138, 57), (124, 64), 3)
    D.rect(fig, (40, 30, 60), (108, 80, 24, 10), border_radius=3)
    D.polygon(fig, (255, 255, 255), [(110, 80), (115, 80), (112, 88)])
    D.polygon(fig, (255, 255, 255), [(125, 80), (130, 80), (128, 88)])
    D.polygon(fig, (150, 210, 255), [(96, 42), (101, 14), (110, 38)])
    D.polygon(fig, (150, 210, 255), [(144, 42), (139, 14), (130, 38)])


def _c_frog(fig, p, q):
    g1, g2, lt = (84, 164, 72), (54, 120, 50), (196, 230, 140)
    D.ellipse(fig, g2, (40, 140, 60, 66))
    D.rect(fig, g2, (30, 196, 70, 14), border_radius=6)
    D.rect(fig, g2, (150 + p * 4, 170, 18, 40), border_radius=6)
    D.ellipse(fig, g1, (40, 96, 150, 100))
    D.ellipse(fig, lt, (80, 150, 90, 44))
    for wx, wy in ((70, 120), (104, 108), (140, 118), (88, 138)):
        D.circle(fig, g2, (wx, wy), 5)
    D.ellipse(fig, g1, (120, 76, 100, 62))
    for ex in (150, 192):
        D.circle(fig, g1, (ex, 64), 22)
        D.circle(fig, (255, 230, 80), (ex, 64), 14)
        D.ellipse(fig, (10, 10, 10), (ex - 3, 52, 6, 24))
    D.line(fig, (30, 70, 30), (130, 112), (216, 118), 4)
    D.line(fig, (230, 80, 110), (216, 118), (232, 130 + p * 6), 6)
    D.circle(fig, (240, 240, 120), (118, 118), 3)


def _c_robot(fig, p, q):
    steel, dk, neon, mag = (150, 160, 180), (70, 76, 96), (0, 230, 230), (255, 70, 200)
    D.rect(fig, dk, (92, 160, 26, 50))
    D.rect(fig, dk, (124, 160, 26, 50))
    D.rect(fig, steel, (86, 200, 40, 14), border_radius=4)
    D.rect(fig, steel, (120, 200, 40, 14), border_radius=4)
    D.line(fig, dk, (76, 96), (48, 130 + p * 10), 16)
    D.line(fig, dk, (168, 96), (198, 130 - p * 10), 16)
    D.polygon(fig, steel, [(38, 128 + p * 10), (60, 128 + p * 10), (49, 154 + p * 10)])
    D.polygon(fig, steel, [(188, 128 - p * 10), (210, 128 - p * 10), (199, 154 - p * 10)])
    D.rect(fig, steel, (76, 80, 92, 88), border_radius=12)
    D.rect(fig, dk, (88, 96, 68, 50), border_radius=8)
    D.circle(fig, neon, (122, 120), 14)
    D.circle(fig, (220, 255, 255), (122, 120), 6)
    for i in range(3):
        D.rect(fig, mag, (94 + i * 16, 152, 10, 5))
    D.rect(fig, neon, (76, 80, 92, 88), 2, border_radius=12)
    D.rect(fig, steel, (92, 38, 60, 44), border_radius=10)
    D.rect(fig, neon, (98, 52, 48, 12), border_radius=4)
    D.rect(fig, (255, 60, 60), (118 + p * 14, 54, 8, 8))
    D.line(fig, dk, (122, 38), (122, 14), 4)
    D.circle(fig, mag, (122, 12), 6)


def _c_scorpion(fig, p, q):
    tan, dk, lt = (206, 150, 70), (146, 98, 40), (236, 190, 110)
    for i in range(4):
        bx = 70 + i * 24
        sw = p * 6 if i % 2 else -p * 6
        D.lines(fig, dk, False, [(bx, 170), (bx - 10 + sw, 196), (bx - 14, 212)], 6)
    pts = [(54, 150), (30, 132), (24, 100), (40, 70), (70, 52), (98, 56 + p * 4)]
    D.lines(fig, tan, False, pts, 16)
    for i, pt in enumerate(pts):
        D.circle(fig, lt if i % 2 else tan, pt, 9)
    D.polygon(fig, (220, 40, 40), [(96, 42 + p * 4), (130, 64 + p * 4), (98, 72 + p * 4)])
    D.ellipse(fig, tan, (52, 138, 120, 56))
    for sx in (74, 98, 122):
        D.line(fig, dk, (sx, 142), (sx, 190), 3)
    D.ellipse(fig, tan, (150, 146, 44, 42))
    D.circle(fig, (255, 50, 50), (184, 152), 5)
    D.line(fig, dk, (176, 160), (206, 140 + p * 8), 10)
    D.polygon(fig, tan, [(200, 126 + p * 8), (238, 138 + p * 8), (212, 154 + p * 8)])
    D.polygon(fig, dk, [(200, 126 + p * 8), (238, 138 + p * 8), (212, 154 + p * 8)], 2)


def _c_dino(fig, p, q):
    red, dk, lt = (176, 52, 32), (120, 30, 22), (236, 150, 70)
    D.polygon(fig, red, [(70, 120), (8, 168 + p * 4), (14, 186), (86, 168)])
    D.rect(fig, dk, (96 + p * 6, 150, 30, 52), border_radius=8)
    D.ellipse(fig, dk, (90 + p * 6, 196, 52, 18))
    D.rect(fig, dk, (132 - p * 6, 150, 30, 52), border_radius=8)
    D.ellipse(fig, dk, (126 - p * 6, 196, 52, 18))
    D.ellipse(fig, red, (60, 86, 120, 90))
    D.ellipse(fig, lt, (84, 132, 84, 42))
    for i in range(5):
        sx = 76 + i * 18
        D.polygon(fig, (255, 150, 40), [(sx, 94 - i * 2), (sx + 9, 94 - i * 2), (sx + 4, 74 - i * 2)])
    D.polygon(fig, red, [(150, 96), (168, 44), (200, 46), (206, 100)])
    D.polygon(fig, red, [(162, 46), (236, 44), (238, 76), (210, 80), (160, 92)])
    D.polygon(fig, dk, [(170, 84 + p * 3), (236, 80 + p * 3), (228, 100 + p * 3), (176, 102 + p * 3)])
    for tx in range(184, 232, 10):
        D.polygon(fig, (255, 255, 255), [(tx, 78 + p * 2), (tx + 6, 78 + p * 2), (tx + 3, 88 + p * 2)])
    D.circle(fig, (255, 220, 60), (190, 58), 7)
    D.circle(fig, (10, 0, 0), (192, 58), 3)
    D.line(fig, (40, 10, 10), (180, 48), (202, 56), 4)
    D.line(fig, dk, (150, 112), (172, 130), 8)
    D.lines(fig, (255, 170, 50), False, [(100, 100), (112, 116), (104, 130)], 3)
    D.polygon(fig, (255, 140, 40), [(238, 56), (252, 50 + p * 3), (240, 66)])


def _c_octopus(fig, p, q):
    pur, lt = (130, 70, 190), (190, 130, 240)
    ph = math.atan2(p, q)
    for i in range(6):
        bx = 72 + i * 19
        pts = []
        for j in range(6):
            pts.append((bx + math.sin(j * 0.9 + i * 0.7 + ph) * 10 + (i - 2.5) * j * 3, 120 + j * 18))
        D.lines(fig, pur, False, pts, 12)
        D.circle(fig, lt, pts[-1], 7)
    D.circle(fig, pur, (120, 86), 54)
    D.ellipse(fig, lt, (78, 46, 44, 24))
    for ex in (102, 138):
        D.circle(fig, (255, 240, 100), (ex, 92), 14)
        D.ellipse(fig, (10, 0, 20), (ex - 3, 82, 6, 20))
    D.line(fig, (50, 20, 90), (88, 76), (112, 84), 4)
    D.line(fig, (50, 20, 90), (152, 76), (128, 84), 4)
    for sx, sy in ((84, 108), (156, 106), (120, 52), (100, 58)):
        D.circle(fig, (120, 255, 220), (sx, sy), 4)
    D.ellipse(fig, (40, 10, 60), (104, 114, 32, 16))
    D.polygon(fig, (255, 255, 255), [(108, 114), (113, 114), (110, 122)])
    D.polygon(fig, (255, 255, 255), [(127, 114), (132, 114), (130, 122)])
    D.line(fig, pur, (120, 34), (120, 14), 5)
    D.circle(fig, (120, 255, 200), (120, 12), 7)


def _c_skull(fig, p, q):
    robe, robe2 = (60, 30, 110), (110, 60, 180)
    ph = math.atan2(p, q)
    bottom = []
    for i in range(9):
        bottom.append((190 - i * 17.5, 208 + math.sin(i * 1.3 + ph) * 8))
    D.polygon(fig, robe, [(72, 100), (168, 100)] + bottom)
    D.polygon(fig, robe2, [(96, 120), (144, 120), (156, 200), (84, 200)])
    D.ellipse(fig, robe, (36, 108 + p * 6, 34, 64))
    D.ellipse(fig, robe, (170, 108 - p * 6, 34, 64))
    D.circle(fig, (236, 228, 208), (52, 176 + p * 6), 10)
    D.circle(fig, (236, 228, 208), (188, 176 - p * 6), 10)
    img = pygame.transform.smoothscale(SKULL_IMGS[0], (px(116), px(116)))
    fig.blit(img, (px(62), px(26)))


def _c_dragon(fig, p, q):
    body, dk, lt, fire = (60, 150, 200), (30, 90, 140), (170, 225, 245), (255, 150, 40)
    fl = p * 34
    # дальнее крыло
    D.polygon(fig, dk, [(105, 100), (62, 30 - fl), (24, 50 - fl), (48, 80 - fl * 0.4), (32, 100), (72, 112)])
    # хвост
    D.lines(fig, body, False, [(64, 140), (36, 160), (20, 152 + p * 8), (10, 168)], 14)
    D.polygon(fig, fire, [(4, 158 + p * 8), (24, 168 + p * 8), (8, 186 + p * 8)])
    # лапы
    D.line(fig, dk, (100, 170), (96, 198), 8)
    D.line(fig, dk, (140, 170), (146, 196), 8)
    # тело и брюхо
    D.ellipse(fig, body, (56, 100, 130, 80))
    D.ellipse(fig, lt, (80, 132, 90, 40))
    for i in range(5):
        sx = 76 + i * 20
        D.polygon(fig, fire, [(sx, 104 - i), (sx + 10, 104 - i), (sx + 5, 86 - i)])
    # шея и голова
    D.polygon(fig, body, [(150, 104), (170, 62), (198, 66), (186, 116)])
    D.polygon(fig, body, [(168, 60), (232, 62), (236, 84), (200, 92), (170, 86)])
    D.polygon(fig, dk, [(176, 84), (234, 84), (224, 98), (184, 96)])
    for tx in range(190, 228, 10):
        D.polygon(fig, (255, 255, 255), [(tx, 84), (tx + 6, 84), (tx + 3, 92)])
    D.polygon(fig, dk, [(172, 60), (160, 34), (192, 54)])
    D.circle(fig, (255, 220, 60), (198, 70), 7)
    D.circle(fig, (10, 0, 0), (200, 70), 3)
    D.line(fig, (20, 40, 60), (188, 60), (208, 68), 4)
    D.circle(fig, dk, (228, 70), 2)
    # ближнее крыло
    wing = [(118, 98), (84, 22 - fl), (38, 38 - fl), (64, 72 - fl * 0.4), (48, 96), (92, 108)]
    D.polygon(fig, lt, wing)
    D.polygon(fig, dk, wing, 3)


_CREATURES = {"pigeon": _c_pigeon, "cat": _c_cat, "bat": _c_bat, "yeti": _c_yeti, "frog": _c_frog,
              "robot": _c_robot, "scorpion": _c_scorpion, "dino": _c_dino, "octopus": _c_octopus,
              "skull": _c_skull, "dragon": _c_dragon}


def creature_surf(kind, fr, d):
    """Кадр секретного босса (240x240); рисуется лицом вправо, влево — зеркалом."""
    key = ("crt", K, kind, fr, d)
    fig = SPR.get(key)
    if fig is None:
        fig = new_surf(240, 240)
        p = math.sin(fr * math.pi / 2)
        q = math.cos(fr * math.pi / 2)
        _CREATURES[kind](fig, p, q)
        fig = fast(outlined(fig))
        if d < 0:
            fig = pygame.transform.flip(fig, True, False)
        SPR[key] = fig
        if len(SPR) > 600:
            for _ in range(150):
                SPR.pop(next(iter(SPR)))
    return fig


class SecretBoss(Boss):
    """Секретный мини-босс: своё чудище на каждом уровне и очень много здоровья."""
    SCALE = 1.0
    secret = True

    def __init__(self, level):
        Boss.__init__(self, level)
        d = SECRET_BOSSES[level]
        self.name = d["name"]
        self.kind = d["kind"]
        self.max_hp = self.hp = float(d["hp"]) * BOSS_HP_MULT
        self.speed = d["speed"]
        self.flags = d["flags"]
        self.time_left = float(d["time"]) * BOSS_TIME_MULT

    def rect(self):
        return pygame.Rect(self.x - 62, self.y - 190, 124, 195)

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        t = pygame.time.get_ticks()
        if self.state in ("fight", "track"):
            blit(surf, SHADOW_B, (x - 45, y - 11))
        oy = 0
        if self.kind in HOVER and self.state == "fight":
            oy = HOVER[self.kind] + 6 * math.sin(t / 260.0)
        cy = y - 95 + oy
        if self.state == "fight":
            cyc = 0.5 + 0.5 * math.sin(t / 300.0)
            glow(surf, (x, cy), 140, (255, 215, 70), int(40 + 30 * cyc))     # золотая аура — «секрет»
            if "rage" in self.flags and self.hp < self.max_hp * 0.5:
                glow(surf, (x, cy), 140, (255, 50, 30), int(80 + 70 * cyc))
        fr = int(t / 130) % 4
        fig = creature_surf(self.kind, fr, self.dir)
        if self.hit_t > 0 or self.hidden:
            fig = fig.copy()
            if self.hit_t > 0:
                fig.fill((90, 90, 90), special_flags=pygame.BLEND_RGB_ADD)
            if self.hidden:
                fig.set_alpha(60)
        if self.state == "fall":
            fig = pygame.transform.rotate(fig, -self.rot)
        blit_c(surf, fig, x, cy)
        self._auras(surf, x, cy, y - 262)
        if self.shield:
            pulse = 0.5 + 0.5 * math.sin(t / 120.0)
            glow(surf, (x, cy), 120, (110, 180, 255), 130)
            D.circle(surf, (170, 215, 255), (x, cy), 96, 3)
            D.circle(surf, (210, 235, 255), (x, cy), 90 + int(4 * pulse), 1)
        if self.state == "fight":
            text(surf, "СЕКРЕТНЫЙ БОСС", f_small, (255, 215, 70), (x, y - 244), center=True)
            plate(surf, (x - 50, y - 224, 100, 19), 170, 8)
            D.rect(surf, (20, 20, 30), (x - 45, y - 219, 90, 9), border_radius=4)
            if self.hp > 0:
                fw = max(1, int(90 * self.hp / self.max_hp))
                D.rect(surf, (235, 180, 40), (x - 45, y - 219, fw, 9), border_radius=4)
                D.rect(surf, (255, 235, 140), (x - 45, y - 219, fw, 3), border_radius=2)
            D.rect(surf, (255, 255, 255), (x - 45, y - 219, 90, 9), 1, border_radius=4)


class FlyingBoss(Boss):
    """Летающий секретный босс: парит над платформой и периодически пикирует вниз."""
    SCALE = 1.0
    secret = True

    def __init__(self, level):
        Boss.__init__(self, level)
        self.name = "Небесный дракон"
        self.kind = "dragon"
        self.max_hp = self.hp = float(700 + 150 * level) * BOSS_HP_MULT
        self.speed = 120
        self.flags = ("erratic", "acid", "regen")
        self.time_left = 80.0 * BOSS_TIME_MULT
        self.alt = -115.0          # смещение вверх от платформы (отрицательное)

    def rect(self):
        return pygame.Rect(self.x - 62, self.y + self.alt - 190, 124, 195)

    def hit(self, dmg):
        res = Boss.hit(self, dmg)
        if self.state == "fall" and self.alt:
            self.y += self.alt     # падает с той высоты, где его сбили
            self.alt = 0.0
        return res

    def update(self, dt):
        Boss.update(self, dt)
        if self.state == "fight":
            c = self.cycle % 7.0
            base = -115 - 18 * math.sin(self.cycle * 1.7)
            if c > 5.2:            # пике: спускается и становится досягаемым
                k = math.sin((c - 5.2) / 1.8 * math.pi)
                base = lerp(base, -35, k)
            self.alt = base
        else:
            self.alt = 0.0

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        t = pygame.time.get_ticks()
        if self.state in ("fight", "track"):
            blit(surf, SHADOW_B, (x - 45, y - 11))
        cy = y - 95 + self.alt
        if self.state == "fight":
            cyc = 0.5 + 0.5 * math.sin(t / 300.0)
            glow(surf, (x, cy), 140, (255, 215, 70), int(40 + 30 * cyc))
        fig = creature_surf("dragon", int(t / 110) % 4, self.dir)
        if self.hit_t > 0 or self.hidden:
            fig = fig.copy()
            if self.hit_t > 0:
                fig.fill((90, 90, 90), special_flags=pygame.BLEND_RGB_ADD)
            if self.hidden:
                fig.set_alpha(60)
        if self.state == "fall":
            fig = pygame.transform.rotate(fig, -self.rot)
        blit_c(surf, fig, x, cy)
        self._auras(surf, x, cy, cy + 120)
        if self.shield:
            pulse = 0.5 + 0.5 * math.sin(t / 120.0)
            glow(surf, (x, cy), 120, (110, 180, 255), 130)
            D.circle(surf, (170, 215, 255), (x, cy), 96, 3)
            D.circle(surf, (210, 235, 255), (x, cy), 90 + int(4 * pulse), 1)
        if self.state == "fight":
            by = cy + 100               # полоска под драконом, чтобы не лезть под HUD
            text(surf, "ЛЕТАЮЩИЙ БОСС", f_small, (255, 215, 70), (x, by), center=True)
            plate(surf, (x - 50, by + 18, 100, 19), 170, 8)
            D.rect(surf, (20, 20, 30), (x - 45, by + 23, 90, 9), border_radius=4)
            if self.hp > 0:
                fw = max(1, int(90 * self.hp / self.max_hp))
                D.rect(surf, (235, 180, 40), (x - 45, by + 23, fw, 9), border_radius=4)
                D.rect(surf, (255, 235, 140), (x - 45, by + 23, fw, 3), border_radius=2)
            D.rect(surf, (255, 255, 255), (x - 45, by + 23, 90, 9), 1, border_radius=4)


# ---------- босс «Слизень» ----------
# Фаза 1 (100-70%): уклоняется, плюётся кислотой по месту, куда игрок чаще всего кликает.
# Фаза 2 (70-35%): распадается на копии (радиус клика вдвое меньше, пока копии живы),
#                  оставляет липкие лужи, закрывается панцирем, создаёт злой курсор.
# Фаза 3 (35-0%): телепортируется, заливает экран слизью, после уклонения уязвим.
# Последняя истерика (<10%): хаотичные рывки, частые плевки и лужи, урон x2.5 после рывка.
# Всегда: каждое 5-е попадание — телепорт.
class SlimeFake:
    """Ложная копия слизня: лопается с двух кликов, полоски здоровья у неё нет."""

    def __init__(self, x, scale):
        self.x = float(x)
        self.y = float(PLAT_TOP)
        self.scale = scale
        self.hp = 2
        self.dir = random.choice([-1, 1])
        self.speed = random.uniform(55, 120)
        self.turn_t = random.uniform(0.8, 2.0)
        self.hit_t = 0.0
        self.ph = random.uniform(0, 6)

    def rect(self):
        s = self.scale
        return pygame.Rect(int(self.x - 62 * s), int(self.y - 104 * s), int(124 * s), int(108 * s))

    def update(self, dt):
        self.ph += dt
        self.hit_t = max(0.0, self.hit_t - dt)
        self.turn_t -= dt
        if self.turn_t <= 0:
            self.dir = random.choice([-1, 1])
            self.turn_t = random.uniform(0.8, 2.0)
        self.x += self.dir * self.speed * dt
        if self.x < 120:
            self.x, self.dir = 120.0, 1
        if self.x > GW - 120:
            self.x, self.dir = GW - 120.0, -1


def draw_slime(surf, x, y, s, t, hurt=False):
    """Желейное тело слизня; (x, y) — точка на земле под ним, s — масштаб."""
    wob = math.sin(t * 5.0) * 0.07
    w = 124 * s * (1 + wob)
    h = 98 * s * (1 - wob)
    base, dark, lite = (88, 204, 98), (34, 112, 56), (170, 244, 168)
    if hurt:
        base = lerp_c(base, (255, 255, 255), 0.55)
        lite = (255, 255, 255)
    D.ellipse(surf, dark, (x - w * 0.62, y - 9 * s, w * 1.24, 16 * s))
    D.ellipse(surf, dark, (x - w / 2 - 3, y - h - 3, w + 6, h + 6))
    D.ellipse(surf, base, (x - w / 2, y - h, w, h))
    D.ellipse(surf, lerp_c(base, (0, 70, 30), 0.25), (x - w / 2 + 5, y - h * 0.42, w - 10, h * 0.38))
    D.ellipse(surf, lite, (x - w * 0.34, y - h * 0.92, w * 0.28, h * 0.22))
    ey = y - h * 0.56
    for sg in (-1, 1):
        ex = x + sg * w * 0.17
        D.circle(surf, (255, 255, 255), (ex, ey), 11 * s)
        D.circle(surf, (20, 40, 28), (ex + 2 * s, ey + 2 * s), 5 * s)
    D.line(surf, (20, 70, 36), (x - w * 0.1, y - h * 0.26), (x + w * 0.1, y - h * 0.26), 3 * s)
    for i in range(3):          # капли стекают по бокам
        dx = (-0.36 + 0.36 * i) * w
        dy = 5 * s + 4 * s * math.sin(t * 3 + i * 2)
        D.circle(surf, base, (x + dx, y - 2 * s + dy), 5 * s)


class SlimeBoss(Boss):
    """Секретный босс «Слизень»: выходит на платформу вместо обычного секретного."""
    slime = True
    secret = True

    def __init__(self, level):
        Boss.__init__(self, level)
        self.name = "Слизень"
        self.max_hp = self.hp = float(520 + 120 * level) * BOSS_HP_MULT
        self.base_speed = 85.0
        self.speed = self.base_speed
        self.flags = ()
        self.time_left = 100.0 * BOSS_TIME_MULT
        self.x = GW - 200.0
        self.phase = 1
        self.scale = 1.0
        self.splits = 0
        self.fakes = []
        self.zones = []          # липкие лужи: курсор в них вязнет
        self.spots = []          # кислота поверх места кликов: клики туда не проходят
        self.shells = []         # панцирные точки на теле
        self.click_log = []
        self.hits = 0
        self.vuln = 0.0
        self.tantrum_on = False
        self.turn_t = 1.5
        self.spit_t = random.uniform(4.0, 6.0)
        self.puddle_t = random.uniform(3.0, 5.0)
        self.fill_t = random.uniform(10.0, 14.0)
        self.shell_t = random.uniform(9.0, 13.0)
        self.evil_cd = random.uniform(10.0, 14.0)
        self.evil_t = 0.0
        self.evil_ang = 0.0
        self.evil_d = 90.0
        self.tp_t = random.uniform(3.0, 4.5)
        self.dash_t = 1.0

    @property
    def tags(self):
        if self.tantrum_on:
            return ["ИСТЕРИКА!", "рывки", "урон x2.5"]
        if self.phase == 1:
            return ["ФАЗА 1", "уклоняется", "плюётся"]
        if self.phase == 2:
            return ["ФАЗА 2", "копии", "лужи", "панцирь"]
        return ["ФАЗА 3", "телепорт", "заливка"]

    def rect(self):
        s = self.scale
        return pygame.Rect(int(self.x - 62 * s), int(self.y - 104 * s), int(124 * s), int(108 * s))

    def dodge_chance(self):
        if self.tantrum_on:
            return 0.30
        return (0.18, 0.12, 0.28)[self.phase - 1]

    def blocked(self, x, y):
        return any(math.hypot(x - a["x"], y - a["y"]) < a["r"] for a in self.spots)

    def sticky_at(self, x, y):
        return any(math.hypot(x - z["x"], y - z["y"]) < z["r"] for z in self.zones)

    def evil_pos(self, ax, ay):
        return (ax + math.cos(self.evil_ang) * self.evil_d, ay + math.sin(self.evil_ang) * self.evil_d)

    def add_zone(self, x, y, r, t):
        self.zones.append(dict(x=x, y=y, r=r, t=t))
        if len(self.zones) > 8:
            self.zones.pop(0)

    def teleport(self, vuln=0.0):
        old = self.x
        nx = old
        for _ in range(8):
            nx = random.uniform(150, GW - 150)
            if abs(nx - old) > 220:
                break
        self.x = nx
        self.events.append(("ТЕЛЕПОРТ!", (190, 150, 255)))
        if vuln > 0:
            self.vuln = max(self.vuln, vuln)
            self.events.append(("УЯЗВИМ!", (255, 235, 90)))

    def split(self, n, scale):
        self.splits += 1
        self.scale = scale
        self.fakes = []
        for _ in range(n):
            fx = max(130.0, min(GW - 130.0, self.x + random.uniform(-280, 280)))
            self.fakes.append(SlimeFake(fx, scale))
        self.events.append((f"РАСПАД! {n} копии", (150, 255, 150)))

    def hit(self, dmg):
        if self.state != "fight":
            return "miss"
        if self.shells:
            return "block"
        if random.random() < self.dodge_chance():
            self.x = max(130.0, min(GW - 130.0, self.x + random.choice([-1, 1]) * random.uniform(60, 120)))
            if self.phase == 3:
                self.vuln = max(self.vuln, 1.5)
                self.events.append(("УЯЗВИМ!", (255, 235, 90)))
            return "dodge"
        if self.vuln > 0:
            dmg = int(dmg * (2.5 if self.tantrum_on else 2.0))
        self.last_dmg = dmg
        self.hp -= dmg
        self.hit_t = 0.15
        self.hits += 1
        if self.hp <= 0:
            self.hp = 0
            self.state = "fall"
            self.vy = -320
            self.vx = self.dir * 70
            return "ok"
        if self.hits % 5 == 0:                    # скачущий босс
            self.teleport(1.6 if self.tantrum_on else 0.0)
        return "ok"

    def update(self, dt):
        if self.state != "fight":
            self.fakes, self.shells, self.zones, self.spots = [], [], [], []
            self.evil_t = 0.0
            return Boss.update(self, dt)
        self.vuln = max(0.0, self.vuln - dt)
        for z in self.zones:
            z["t"] -= dt
        for a in self.spots:
            a["t"] -= dt
        self.zones = [z for z in self.zones if z["t"] > 0]
        self.spots = [a for a in self.spots if a["t"] > 0]
        frac = self.hp / self.max_hp
        ph = 1 if frac > 0.70 else (2 if frac > 0.35 else 3)
        if ph != self.phase:
            self.phase = ph
            self.events.append((f"ФАЗА {ph}!", (150, 255, 150)))
        tantrum = frac <= 0.10
        if tantrum and not self.tantrum_on:
            self.events.append(("ПОСЛЕДНЯЯ ИСТЕРИКА!", (255, 90, 90)))
        self.tantrum_on = tantrum
        self.speed = self.base_speed * (1.0, 1.25, 1.6)[self.phase - 1] * (2.0 if tantrum else 1.0)
        self.turn_t -= dt
        if self.turn_t <= 0:
            self.dir = random.choice([-1, 1])
            self.turn_t = random.uniform(0.3, 0.8) if tantrum else random.uniform(1.0, 2.4)
        Boss.update(self, dt)
        if self.state != "fight":
            return
        # копии
        if frac <= 0.70 and self.splits < 1:
            self.split(2, 0.78)
        if frac <= 0.35 and self.splits < 2:
            self.split(3, 0.62)
        for fk in self.fakes:
            fk.update(dt)
        # плевок кислотой по месту частых кликов
        self.spit_t -= dt
        if self.spit_t <= 0:
            self.spit_t = (random.uniform(2.2, 3.2) if tantrum else
                           (4.0, 6.5, 4.5)[self.phase - 1] + random.uniform(0, 1.5))
            pts = self.click_log[-6:]
            if pts:
                cx = sum(p[0] for p in pts) / len(pts)
                cy = sum(p[1] for p in pts) / len(pts)
            else:
                cx, cy = self.x, self.y - 60
            small = self.phase == 1
            self.spots.append(dict(x=cx, y=cy, r=38 if small else 54, t=3.0 if small else 4.0))
            self.events.append(("ПЛЕВОК!", (150, 235, 110)))
        # лужи слизи под ногами
        if self.phase >= 2:
            self.puddle_t -= dt
            if self.puddle_t <= 0:
                self.puddle_t = 1.8 if tantrum else (random.uniform(4.0, 6.0) if self.phase == 2
                                                       else random.uniform(3.0, 4.0))
                self.add_zone(self.x, self.y - 40, 78, 9.0)
        # панцирь
        if self.phase >= 2 and not self.shells:
            self.shell_t -= dt
            if self.shell_t <= 0:
                self.shell_t = random.uniform(14.0, 18.0)
                self.shells = [dict(dx=-34, dy=-62, hp=3), dict(dx=30, dy=-44, hp=3),
                               dict(dx=2, dy=-92, hp=3)]
                self.events.append(("ПАНЦИРЬ! Ломай точки!", (200, 210, 230)))
        # большая заливка экрана
        if self.phase == 3:
            self.fill_t -= dt
            if self.fill_t <= 0:
                self.fill_t = random.uniform(7.0, 9.0) if tantrum else random.uniform(13.0, 17.0)
                self.add_zone(random.uniform(250, GW - 250), PLAT_TOP - 80, 330, 6.0)
                self.events.append(("ЗАЛИВКА!", (120, 235, 130)))
        # телепорты и рывки
        if tantrum:
            self.dash_t -= dt
            if self.dash_t <= 0:
                self.dash_t = random.uniform(0.9, 1.5)
                self.x = max(130.0, min(GW - 130.0, self.x + random.choice([-1, 1]) * random.uniform(150, 260)))
                self.vuln = max(self.vuln, 1.6)
        elif self.phase == 3:
            self.tp_t -= dt
            if self.tp_t <= 0:
                self.tp_t = random.uniform(3.0, 4.5)
                self.teleport()
        # злой курсор
        if self.evil_t > 0:
            self.evil_t -= dt
            self.evil_ang += dt * 2.6
            self.evil_d = 85 + 25 * math.sin(self.evil_ang * 1.7)
        elif self.phase >= 2:
            self.evil_cd -= dt
            if self.evil_cd <= 0:
                self.evil_t = 3.2 if self.phase == 3 else 2.5
                self.evil_cd = random.uniform(11, 15) if self.phase == 3 else random.uniform(16, 22)
                self.events.append(("ЗЛОЙ КУРСОР!", (255, 90, 90)))

    def draw(self, surf):
        t = pygame.time.get_ticks() / 1000.0
        x, y, s = int(self.x), int(self.y), self.scale
        for z in self.zones:               # липкие лужи
            k = min(1.0, z["t"] / 1.0)
            glow(surf, (z["x"], z["y"]), z["r"] * 1.1, (70, 210, 90), int(95 * k))
            if k > 0.5:
                D.ellipse(surf, (130, 245, 140),
                          (z["x"] - z["r"], z["y"] - z["r"], z["r"] * 2, z["r"] * 2), 2)
        for a in self.spots:               # кислота, закрывающая клики
            glow(surf, (a["x"], a["y"]), a["r"] * 1.5, (110, 255, 60), 100)
            D.circle(surf, (58, 150, 38), (a["x"], a["y"]), a["r"])
            D.circle(surf, (120, 225, 66), (a["x"] - a["r"] * 0.25, a["y"] - a["r"] * 0.25), a["r"] * 0.55)
            D.circle(surf, (190, 255, 130), (a["x"] - a["r"] * 0.4, a["y"] - a["r"] * 0.4), a["r"] * 0.18)
        if self.state == "fight":
            for fk in self.fakes:
                blit(surf, SHADOW_S, (fk.x - 23, fk.y - 7))
                draw_slime(surf, fk.x, fk.y, fk.scale, t + fk.ph, fk.hit_t > 0)
        if self.state in ("fight", "track"):
            blit(surf, SHADOW_B if s > 0.7 else SHADOW_S, (x - (45 if s > 0.7 else 23), y - (11 if s > 0.7 else 7)))
        if self.state == "fight":
            if self.tantrum_on:
                glow(surf, (x, y - 50 * s), 130, (255, 50, 30), 100)
            if self.vuln > 0:
                glow(surf, (x, y - 50 * s), 110, (255, 235, 90), 110)
        draw_slime(surf, x, y, s, t, self.hit_t > 0)
        if self.shells:
            glow(surf, (x, y - 50 * s), 100, (160, 175, 210), 90)
            for sh in self.shells:
                px_, py_ = self.x + sh["dx"] * s, self.y + sh["dy"] * s
                D.circle(surf, (40, 44, 58), (px_, py_), 19)
                D.circle(surf, (150, 158, 178), (px_, py_), 16)
                D.circle(surf, (205, 212, 228), (px_ - 4, py_ - 5), 6)
                D.circle(surf, (60, 66, 86), (px_, py_), 16, 2)
                for i in range(sh["hp"]):
                    D.circle(surf, (255, 200, 70), (px_ - 6 + i * 6, py_ + 7), 2)
        if self.state == "fight":
            top = y - 104 * s - 46
            if self.vuln > 0:
                text(surf, "УЯЗВИМ!", f_small, (255, 235, 90), (x, top - 20), center=True)
            text(surf, "СЛИЗЕНЬ", f_small, (255, 215, 70), (x, top), center=True)
            plate(surf, (x - 50, top + 18, 100, 19), 170, 8)
            D.rect(surf, (20, 20, 30), (x - 45, top + 23, 90, 9), border_radius=4)
            if self.hp > 0:
                fw = max(1, int(90 * self.hp / self.max_hp))
                D.rect(surf, (90, 210, 100), (x - 45, top + 23, fw, 9), border_radius=4)
                D.rect(surf, (190, 255, 170), (x - 45, top + 23, fw, 3), border_radius=2)
            D.rect(surf, (255, 255, 255), (x - 45, top + 23, 90, 9), 1, border_radius=4)


ABILITY_TAGS = (("heal", "лечится"), ("dodge", "уклоняется"), ("tough", "броня"),
                ("timesteal", "крадёт время"), ("frenzy", "ярость"),
                ("acid", "кислота"), ("wind", "2-е дыхание"))


def draw_boss_bar(surf, b):
    w, x0 = 356, GW // 2 - 178
    tags = list(getattr(b, "tags", None) or [n for k, n in ABILITY_TAGS if k in getattr(b, "flags", ())])
    rows = [tags[i:i + 3] for i in range(0, len(tags), 3)]
    plate(surf, (x0 - 12, 2, w + 24, 88 + 16 * max(0, len(rows) - 1)), 165, 14,
          border=(255, 120, 100, 90))
    if getattr(b, "secret", False):
        text(surf, f"СЕКРЕТ: {b.name}", f_mid, (255, 215, 70), (GW // 2, 6), center=True)
    else:
        text(surf, f"БОСС: {b.name}", f_mid, (255, 130, 110), (GW // 2, 6), center=True)
    D.rect(surf, (20, 20, 30), (x0, 34, w, 16), border_radius=8)
    if b.hp > 0:
        fw = max(2, int(w * b.hp / b.max_hp))
        D.rect(surf, (200, 40, 50), (x0, 34, fw, 16), border_radius=8)
        D.rect(surf, (245, 90, 90), (x0, 34, fw, 8), border_radius=6)
        D.rect(surf, (255, 170, 160), (x0 + 3, 36, max(1, fw - 6), 2), border_radius=1)
    for q in (1, 2, 3):
        D.line(surf, (20, 20, 30), (x0 + w * q // 4, 34), (x0 + w * q // 4, 49), 2)
    D.rect(surf, (255, 255, 255), (x0, 34, w, 16), 2, border_radius=8)
    if b.state == "fight":
        info = f"{int(b.hp)}/{int(b.max_hp)}  •  осталось {int(b.time_left)} с"
    else:
        info = "Босс сброшен на пути — жди поезд!"
    text(surf, info, f_small, (255, 255, 255), (GW // 2, 54), center=True)
    for i, row in enumerate(rows):
        text(surf, " • ".join(row), f_small, (150, 235, 110), (GW // 2, 70 + 16 * i),
             center=True, shadow=False)


def train_sprite(body, night, gold):
    """Корпус поезда рисуется один раз на каждый цвет; по экрану едет готовая картинка."""
    key = (K, body, night, gold)
    hit = TRAIN_CACHE.get(key)
    if hit is not None:
        return hit
    h = 110
    dark = lerp_c(body, (0, 0, 0), 0.35)
    lite = lerp_c(body, (255, 255, 255), 0.22)
    stripe = lerp_c(body, (255, 255, 255), 0.45)
    wc = (255, 226, 140) if night else (170, 214, 245)
    wc2 = (255, 245, 200) if night else (225, 242, 255)
    s = new_surf(Train.LENGTH, h + 10)
    wheels_all = []
    parts = [(0, 230)] + [(238 + i * 198, 190) for i in range(3)]
    for idx, (ox, w) in enumerate(parts):
        r = pygame.Rect(ox, 0, w, h)
        # подвагонная рама
        D.rect(s, (24, 24, 30), (r.x + 8, r.y + h - 14, w - 16, 14), border_radius=4)
        D.rect(s, body, r, border_radius=14 if idx == 0 else 8)
        D.rect(s, lite, (r.x + 4, r.y + 12, w - 8, 10), border_radius=5)
        D.rect(s, dark, (r.x, r.y, w, 10), border_radius=6)
        D.rect(s, dark, (r.x + 2, r.y + h - 24, w - 4, 14), border_radius=5)
        D.rect(s, stripe, (r.x, r.y + h - 38, w, 8))
        D.rect(s, lerp_c(body, (0, 0, 0), 0.2), (r.x, r.y + h - 30, w, 2))
        if idx == 0:
            for wr in ((r.x + 30, r.y + 22, 70, 38), (r.x + 118, r.y + 22, 50, 38)):
                D.rect(s, (20, 22, 30), (wr[0] - 3, wr[1] - 3, wr[2] + 6, wr[3] + 6), border_radius=8)
                D.rect(s, wc, wr, border_radius=6)
                D.polygon(s, wc2, [(wr[0] + 8, wr[1] + wr[3] - 4), (wr[0] + 22, wr[1] + 4),
                                   (wr[0] + 32, wr[1] + 4), (wr[0] + 18, wr[1] + wr[3] - 4)])
        else:
            for k in range(3):
                wr = (r.x + 14 + k * 58, r.y + 22, 44, 36)
                D.rect(s, (20, 22, 30), (wr[0] - 3, wr[1] - 3, wr[2] + 6, wr[3] + 6), border_radius=7)
                D.rect(s, wc, wr, border_radius=5)
                D.polygon(s, wc2, [(wr[0] + 5, wr[1] + wr[3] - 3), (wr[0] + 16, wr[1] + 3),
                                   (wr[0] + 24, wr[1] + 3), (wr[0] + 13, wr[1] + wr[3] - 3)])
            # дверь
            dx = r.x + w - 22
            D.rect(s, dark, (dx, r.y + 18, 14, 54), border_radius=3)
            D.line(s, lerp_c(dark, (255, 255, 255), 0.3), (dx + 7, r.y + 20), (dx + 7, r.y + 70), 1)
        # заклёпки
        for rx in range(r.x + 12, r.x + w - 8, 26):
            D.circle(s, lerp_c(body, (0, 0, 0), 0.25), (rx, r.y + 6), 2)
        wheels = [r.x + 28, r.x + w - 28] + ([r.x + w // 2] if idx == 0 else [])
        for wx in wheels:
            cy = h - 6
            D.circle(s, (30, 30, 36), (wx, cy), 12)
            D.circle(s, (70, 70, 80), (wx, cy), 12, 2)
            D.circle(s, (120, 120, 130), (wx, cy), 5)
            wheels_all.append((wx, cy))
    for ex in (230, 428, 626):
        D.rect(s, (40, 40, 46), (ex, 88, 10, 8))
    D.circle(s, (255, 245, 170), (6, 66), 7)
    D.circle(s, (255, 255, 235), (5, 65), 3)
    if len(TRAIN_CACHE) > 8:
        TRAIN_CACHE.clear()
    hit = (fast(s), wheels_all)
    TRAIN_CACHE[key] = hit
    return hit


class Train:
    LENGTH = 824

    def __init__(self, gold=False):
        self.x = GW + 20
        self.speed = 1100
        self.gold = gold

    def rect(self):
        return pygame.Rect(self.x, TRAIN_Y, self.LENGTH, 110)

    def update(self, dt):
        self.x -= self.speed * dt

    def done(self):
        return self.x + self.LENGTH < 0

    def draw(self, surf, col, light):
        x = int(self.x)
        y = TRAIN_Y
        body = (235, 190, 40) if self.gold else col["train"]
        spr, wheels = train_sprite(body, light > 0.4, self.gold)
        # прожектор спереди
        if light > 0.3 or self.gold:
            HEAD_CONE.set_alpha(int(255 * max(light, 0.6 if self.gold else 0)))
            surf.blit(HEAD_CONE, (px(x + 6) - HEAD_CONE.get_width(), px(y + 68) - HEAD_CONE.get_height() // 2))
        # линии скорости позади
        for k in range(5):
            ly = y + 16 + k * 20
            ln = 60 + 26 * ((k * 7) % 4)
            D.line(surf, lerp_c(col["bed"], (255, 255, 255), 0.35),
                   (x + self.LENGTH + 6, ly), (x + self.LENGTH + 6 + ln, ly), 2)
        blit(surf, spr, (x, y))
        ang = self.x * 0.08
        for (wx, cy) in wheels:
            D.line(surf, (170, 170, 180), (x + wx, y + cy),
                   (x + wx + math.cos(ang) * 10, y + cy + math.sin(ang) * 10), 2)
        if light > 0.3 or self.gold:
            glow(surf, (x - 10, y + 66), 110, (255, 240, 170), int(130 * max(light, 0.6 if self.gold else 0)))
        if self.gold:
            for k in range(4):                # блестящие искорки на золотом поезде
                sx = x + 40 + ((pygame.time.get_ticks() // 7 + k * 211) % (self.LENGTH - 80))
                D.circle(surf, (255, 255, 220), (sx, y + 12 + (k * 23) % 60), 2)


class Effect:
    def __init__(self, x, y, txt, color=(255, 255, 255)):
        self.x, self.y, self.t, self.txt, self.color = x, y, 0.9, txt, color

    def update(self, dt):
        self.t -= dt

    def draw(self, surf):
        age = 0.9 - self.t
        img = _text_img(self.txt, f_mid, self.color, True).copy()
        img.set_alpha(255 if self.t > 0.3 else max(0, int(255 * self.t / 0.3)))
        o = _ol()
        bw = img.get_width() - 2 * o
        surf.blit(img, (px(self.x) - bw // 2 - o, px(self.y - 110 - age * 50) - o))


class Particle:
    def __init__(self, x, y, color):
        a = random.uniform(0, math.tau)
        sp = random.uniform(80, 260)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a) * sp, math.sin(a) * sp - 150
        self.life = self.max = random.uniform(0.5, 1.0)
        self.color = color
        self.size = random.randint(3, 6)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 600 * dt
        self.life -= dt

    def draw(self, surf):
        r = max(1, int(self.size * self.life / self.max))
        D.circle(surf, self.color, (int(self.x), int(self.y)), r)
        if r > 2:
            D.circle(surf, lerp_c(self.color, (255, 255, 255), 0.5),
                               (int(self.x) - 1, int(self.y) - 1), max(1, r // 2))


class Coin:
    """Золотая монета падает с неба и подпрыгивает на платформе — кликни, пока не исчезла."""

    def __init__(self):
        self.x = random.uniform(90, GW - 90)
        self.y = -20.0
        self.vy = 0.0
        self.t = 8.0
        self.floor = random.uniform(PLAT_TOP + 20, PLAT_TOP + 55)
        self.spin = random.uniform(0, 6)

    def update(self, dt):
        self.t -= dt
        self.spin += dt * 6
        self.vy += 900 * dt
        self.y += self.vy * dt
        if self.y >= self.floor:
            self.y = self.floor
            self.vy = -self.vy * 0.55 if abs(self.vy) > 140 else 0.0

    def draw(self, surf):
        if self.t < 2.0 and int(self.t * 8) % 2 == 0:
            return                              # мигает перед исчезновением
        x, y = int(self.x), int(self.y)
        wob = abs(math.cos(self.spin))          # монета вращается
        rw = max(3, int(17 * (0.35 + 0.65 * wob)))
        glow(surf, (x, y), 52, (255, 215, 60), 110)
        D.ellipse(surf, (200, 150, 20), (x - rw - 1, y - 18, rw * 2 + 2, 36))
        D.ellipse(surf, (255, 205, 40), (x - rw, y - 17, rw * 2, 34))
        D.ellipse(surf, (255, 240, 150), (x - rw + 3, y - 13, max(2, rw - 2), 12))
        if wob > 0.6:
            text(surf, "$", f_mid, (160, 105, 10), (x, y - 11), center=True, shadow=False)


# ---------- кровь, череп и кислота ----------
class Decal:
    """Пятно крови на путях: остаётся на несколько секунд и медленно тает."""

    def __init__(self, x, y, big=False):
        self.max = self.t = random.uniform(6.0, 10.0)
        w = random.randint(36, 62) if big else random.randint(22, 42)
        h = max(8, int(w * 0.45))
        s = new_surf(w, h)
        for _ in range(random.randint(4, 7)):
            rw = random.randint(max(6, w // 3), max(7, w * 2 // 3))
            rh = random.randint(max(4, h // 3), max(5, h * 2 // 3))
            D.ellipse(s, (135 + random.randint(0, 45), 12, 16, random.randint(130, 205)),
                      (random.randint(0, max(0, w - rw)), random.randint(0, max(0, h - rh)), rw, rh))
        for _ in range(4):                      # брызги вокруг пятна
            D.circle(s, (120, 10, 14, random.randint(80, 150)),
                     (random.randint(1, w - 2), random.randint(1, h - 2)),
                     random.randint(2, 5))
        self.surf = fast(s)
        self.x, self.y = x - w // 2, y - h // 2

    def update(self, dt):
        self.t -= dt

    def draw(self, surf):
        k = max(0.0, self.t / self.max)
        self.surf.set_alpha(255 if k > 0.35 else int(255 * k / 0.35))
        surf.blit(self.surf, (px(self.x), px(self.y)))


def make_skull(jaw=0):
    """Череп с запасом по разрешению (576 px): он летит в камеру и растягивается на весь экран.
    Объёмная кость с градиентом, трещины, злые пылающие глаза, клыки и челюсть, которая щёлкает."""
    S = 6
    s = pygame.Surface((96 * S, 96 * S), pygame.SRCALPHA)
    dr = pygame.draw

    def R(x, y, w, h):
        return (int(x * S), int(y * S), int(w * S), int(h * S))

    def P(*pts):
        return [(int(x * S), int(y * S)) for x, y in pts]

    bone = (238, 230, 210)
    mid = (208, 198, 172)
    shade = (152, 140, 118)
    deep = (92, 82, 70)
    hi = (255, 252, 240)
    black = (8, 6, 10)
    jy = 9 * jaw                       # на сколько опущена челюсть

    # --- нижняя челюсть (рисуется первой, она позади черепа) ---
    dr.rect(s, shade, R(24, 70 + jy, 48, 19), border_radius=9 * S)
    dr.rect(s, bone, R(25, 70 + jy, 46, 16), border_radius=8 * S)
    dr.rect(s, mid, R(25, 79 + jy, 46, 7), border_radius=6 * S)
    dr.line(s, deep, (48 * S, 79 * S + jy * S), (48 * S, 87 * S + jy * S), S)    # шов подбородка
    # тёмный рот
    dr.rect(s, black, R(26, 62, 44, 12 + jy), border_radius=4 * S)
    # нижние зубы
    for i in range(8):
        tx = 28.5 + i * 5.2
        dr.rect(s, hi, R(tx, 69 + jy, 4, 7), border_radius=S)
        dr.rect(s, shade, R(tx, 69 + jy, 4, 7), max(1, S // 3), border_radius=S)

    # --- череп: объём из слоёв, свет сверху-слева ---
    dr.ellipse(s, deep, R(9, 2, 78, 68))
    dr.ellipse(s, shade, R(11, 3, 74, 65))
    layers = 9
    for i in range(layers):
        k = i / (layers - 1)
        c = lerp_c(mid, hi, k)
        dr.ellipse(s, c, R(12 + i * 1.3, 4 + i * 1.0, 72 - i * 3.4, 60 - i * 3.2))
    # скулы и верхняя челюсть
    dr.rect(s, shade, R(21, 47, 54, 24), border_radius=10 * S)
    dr.rect(s, bone, R(22, 47, 52, 22), border_radius=9 * S)
    for cx_ in (12, 66):
        dr.ellipse(s, shade, R(cx_, 38, 19, 20))
        dr.ellipse(s, bone, R(cx_ + 1, 38, 17, 18))
        dr.ellipse(s, hi, R(cx_ + 3, 40, 7, 6))

    # --- шов на лбу и трещины ---
    dr.lines(s, deep, False, P((49, 6), (46, 12), (51, 18), (47, 25)), int(S * 1.2))
    dr.lines(s, deep, False, P((64, 7), (60, 14), (66, 21), (61, 30), (63, 36)), int(S * 1.6))
    dr.lines(s, deep, False, P((60, 14), (54, 17)), S)
    dr.lines(s, deep, False, P((24, 13), (29, 20), (26, 26)), S)

    # --- глазницы: злые, скошенные внутрь ---
    left = [(16, 31), (31, 26), (46, 37), (43, 52), (28, 55), (17, 46)]
    right = [(96 - x, y) for x, y in left]
    for pts in (left, right):
        dr.polygon(s, deep, P(*pts))
        inner = [((x - 48) * 0.88 + 48 if x < 48 else (x - 48) * 0.88 + 48, y) for x, y in pts]
        dr.polygon(s, black, P(*inner))
    # пылающие зрачки
    for ex in (31, 65):
        dr.circle(s, (90, 6, 6), (ex * S, 42 * S), 9 * S)
        dr.circle(s, (200, 24, 14), (ex * S, 42 * S), 6.5 * S)
        dr.circle(s, (255, 110, 30), (ex * S, 42 * S), 4.2 * S)
        dr.circle(s, (255, 225, 120), (ex * S, 41 * S), 2 * S)
    # тяжёлые брови над глазницами
    dr.line(s, deep, (14 * S, 29 * S), (46 * S, 37 * S), int(S * 2.2))
    dr.line(s, deep, (82 * S, 29 * S), (50 * S, 37 * S), int(S * 2.2))

    # --- нос: перевёрнутое сердечко ---
    dr.polygon(s, black, P((48, 51), (42, 61), (45, 66), (48, 62), (51, 66), (54, 61)))

    # --- верхние зубы и клыки ---
    for i in range(8):
        tx = 28.5 + i * 5.2
        dr.rect(s, hi, R(tx, 61, 4, 9), border_radius=S)
        dr.rect(s, shade, R(tx, 61, 4, 9), max(1, S // 3), border_radius=S)
    for fx in (30.5, 65.5):            # клыки
        dr.polygon(s, hi, P((fx - 2.5, 62), (fx + 2.5, 62), (fx, 74 + jy * 0.5)))
        dr.polygon(s, shade, P((fx - 2.5, 62), (fx + 2.5, 62), (fx, 74 + jy * 0.5)), max(1, S // 3))

    # тёмная кромка, чтобы череп «держал» объём
    dr.ellipse(s, deep, R(9, 2, 78, 68), S)
    return fast(outlined(s, (6, 4, 8), o=S))


class SkullFly:
    """Череп летит в камеру: от маленькой точки до всего экрана, щёлкает челюстью."""

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.t = 0.0
        self.dur = 1.1
        self.rot = 0.0
        self.spin = random.uniform(-220, 220)

    def update(self, dt):
        self.t += dt
        # вращение гасится, чтобы к концу череп смотрел «в лицо»
        self.rot += self.spin * dt * max(0.0, 1.0 - self.t / self.dur)

    def draw(self, surf):
        k = min(1.0, self.t / self.dur)
        size = max(8, int(96 * (0.4 + 4.6 * k * k)))
        base = SKULL_IMGS[int(self.t * 16) % 2]
        spx = max(8, px(size))
        img = pygame.transform.smoothscale(base, (spx, spx))
        if k > 0.8:
            img.set_alpha(max(0, int(255 * (1 - (k - 0.8) / 0.2))))
        if abs(self.rot) > 1:
            img = pygame.transform.rotate(img, self.rot)
        cx = lerp(self.x, W * 0.5, k)
        cy = lerp(self.y, H * 0.48, k)
        # дрожь, нарастающая к концу
        if k > 0.3:
            amp = int(2 + 8 * k)
            cx += random.randint(-amp, amp)
            cy += random.randint(-amp, amp)
        if 0.45 < k < 1.0:                     # красная вспышка по всему экрану
            fa = int(110 * math.sin((k - 0.45) / 0.55 * math.pi))
            if fa > 0:
                RED_FLASH.set_alpha(fa)
                surf.blit(RED_FLASH, (0, 0))
        pulse = 0.5 + 0.5 * math.sin(self.t * 30)
        glow(surf, (cx, cy), min(size * 0.95, 280), (255, 30, 30), int(60 + 40 * pulse) // 20 * 20)
        blit_c(surf, img, cx, cy)


class Acid:
    """Плевок босса летит по дуге в камеру и заливает экран зелёным."""

    def __init__(self, x, y):
        self.x0, self.y0 = float(x), float(y)
        self.tx = random.uniform(W * 0.28, W * 0.78)
        self.ty = random.uniform(H * 0.35, H * 0.72)
        self.t = 0.0
        self.dur = random.uniform(1.0, 1.35)
        self.done = False

    def update(self, dt):
        self.t = min(self.dur, self.t + dt)
        if self.t >= self.dur:
            self.done = True

    def _pt(self, k):
        return (lerp(self.x0, self.tx, k),
                lerp(self.y0, self.ty, k) - math.sin(k * math.pi) * 150)

    def draw(self, surf):
        k = self.t / self.dur
        x, y = self._pt(k)
        r = 10 + 18 * k
        glow(surf, (x, y), r * 2.6, (120, 255, 60), 80)
        for i in range(4):                     # шлейф из капель
            tx, ty = self._pt(max(0.0, k - 0.06 * (i + 1)))
            D.circle(surf, (150 - i * 22, 240 - i * 34, 44),
                               (int(tx), int(ty)), max(2, int(r * (1 - 0.2 * i))))
        D.circle(surf, (210, 255, 130), (int(x), int(y)), max(3, int(r * 0.55)))


def make_acid_overlay():
    """Кислота на «стекле» камеры: капли и потёки поверх всего экрана."""
    s = new_surf(W, H)
    for _ in range(random.randint(7, 10)):
        r = random.randint(80, 210)
        x, y = random.randint(-30, W - 30), random.randint(-30, H - 30)
        D.circle(s, (66, 185, 38, 150), (x, y), r)
        D.circle(s, (120, 225, 66, 110), (x - r // 4, y - r // 4), max(6, r * 2 // 3))
        D.circle(s, (185, 250, 120, 70), (x - r // 3, y - r // 3), max(4, r // 3))
        for _ in range(6):
            D.circle(s, (90, 210, 50, random.randint(70, 145)),
                     (x + random.randint(-r, r), y + random.randint(-r, r)),
                     random.randint(3, 13))
        # потёк вниз
        fx = x + random.randint(-r // 2, r // 2)
        fh = random.randint(40, 150)
        D.rect(s, (86, 205, 46, 130), (fx, y, random.randint(6, 14), fh), border_radius=6)
    return fast(s)


# ---------- интерфейс ----------

def build_panel_bg():
    base = pygame.Surface((PWP, HP))
    vband(base, 0, PW, 0, H, (40, 43, 62), (16, 18, 28))
    # едва заметная диагональная текстура
    tex = pygame.Surface((PWP, HP))
    for i in range(-H, PW, 22):
        D.line(tex, (255, 255, 255), (i, 0), (i + H, H), 1)
    tex.set_alpha(9)
    base.blit(tex, (0, 0))
    # шапка
    vband(base, 0, PW, 0, 34, (62, 68, 104), (40, 43, 62))
    return fast(base, False)


def card(surf, r, base, border, accent=None):
    D.rect(surf, (8, 9, 16), r.move(0, 3), border_radius=10)
    D.rect(surf, base, r, border_radius=10)
    D.line(surf, lerp_c(base, (255, 255, 255), 0.14), (r.x + 10, r.y + 2), (r.right - 10, r.y + 2), 1)
    D.rect(surf, border, r, 2, border_radius=10)
    if accent:
        D.rect(surf, accent, (r.x + 3, r.y + 10, 4, r.h - 20), border_radius=2)


def draw_panel(surf, s, mouse, tab):
    now = pygame.time.get_ticks() / 1000.0
    pulse = 0.5 + 0.5 * math.sin(now * 4)
    inf = inflation(s)
    upf = up_infl(s)
    surf.blit(PANEL_BG, (GWP, 0))
    D.line(surf, (90, 96, 130), (GW, 0), (GW, H), 2)
    D.line(surf, (20, 22, 34), (GW + 2, 0), (GW + 2, H), 2)
    text(surf, "Магазин", f_mid, (255, 255, 255), (GW + 16, 8), shadow=False)
    lab = f"Инфляция x{fmt(int(inf))}"
    text(surf, lab, f_small, (255, 214, 90),
         (GW + PW - 12 - twidth(f_small, lab), 11), shadow=False)

    # вкладки
    for t in range(len(TAB_NAMES)):
        r = pygame.Rect(GW + 10 + t * TAB_GAP, TAB_Y, TAB_W, 26)
        active = (t == tab)
        D.rect(surf, (70, 90, 150) if active else (44, 47, 66), r, border_radius=8)
        if active:
            D.rect(surf, (96, 120, 190), (r.x + 3, r.y + 2, r.w - 6, 8), border_radius=6)
        D.rect(surf, (140, 160, 230) if active else (70, 74, 98), r, 2, border_radius=8)
        text(surf, TAB_NAMES[t], f_small, (255, 255, 255) if active else (170, 176, 205),
             (r.centerx, r.y + 5), center=True, shadow=False)
        ready = False
        if t == ITEM_TAB:
            ready = any(s["money"] >= item_price(it, s) for it in ITEMS)
        else:
            for gi in tab_items(t):
                u = UPGRADES[gi]
                lvl = s["levels"][u["key"]]
                if s["level"] >= u["req"] and lvl < u["max"] and s["money"] >= cost(u, lvl, upf):
                    ready = True
                    break
        if ready and not active:      # жёлтая точка — есть что купить
            glow(surf, (r.right - 8, r.y + 8), 9, (255, 200, 60), 150)
            D.circle(surf, (255, 200, 60), (r.right - 8, r.y + 8), 4)

    for k, gi in enumerate(tab_items(tab)):
        u = UPGRADES[gi]
        lvl = s["levels"][u["key"]]
        r = pygame.Rect(GW + 10, ROW_Y0 + k * ROW_H, PW - 20, ROW_H - 8)
        locked = s["level"] < u["req"]
        if locked:
            card(surf, r, (32, 34, 48), (54, 57, 78))
            text(surf, f"{k + 1}. {u['name']}", f_mid, (120, 124, 146), (r.x + 10, r.y + 6), shadow=False)
            text(surf, f"Откроется на уровне {u['req'] + 1}", f_small, (150, 154, 178),
                 (r.x + 10, r.y + 36), shadow=False)
            # замок
            lx, ly = r.right - 26, r.y + 30
            D.rect(surf, (110, 114, 140), (lx, ly, 16, 13), border_radius=3)
            D.arc(surf, (110, 114, 140), (lx + 2, ly - 9, 12, 14), 0, math.pi, 2)
            continue
        maxed = lvl >= u["max"]
        c = cost(u, lvl, upf)
        can = (not maxed) and s["money"] >= c
        bg = (44, 100, 64) if can else (48, 51, 70)
        if maxed:
            bg = (60, 56, 40)
        if can and r.collidepoint(mouse):
            bg = (62, 130, 86)
        border = lerp_c((96, 160, 112), (170, 240, 150), pulse) if can else ((130, 112, 56) if maxed else (70, 74, 98))
        card(surf, r, bg, border, (110, 220, 140) if can else ((240, 200, 80) if maxed else None))
        text(surf, f"{k + 1}. {u['name']}", f_mid, (255, 255, 255), (r.x + 12, r.y + 6), shadow=False)
        lvs = f"Ур. {lvl}/{u['max']}"
        text(surf, lvs, f_small, (190, 196, 224), (r.right - twidth(f_small, lvs) - 10, r.y + 9), shadow=False)
        line = f"{u['label']}: {u['v'](lvl)}" + ("" if maxed else f" → {u['v'](lvl + 1)}")
        text(surf, line, f_small, (210, 215, 235), (r.x + 12, r.y + 30), shadow=False)
        price = "МАКС" if maxed else f"${fmt(c)}"
        pcol = (255, 226, 90) if (can or maxed) else (150, 152, 170)
        text(surf, price, f_mid, pcol, (r.x + 12, r.y + 42), shadow=False)
        bx, bw = r.x + 110, r.w - 122
        D.rect(surf, (22, 24, 36), (bx, r.y + 54, bw, 8), border_radius=4)
        if lvl > 0:
            fw = max(4, int(bw * lvl / u["max"]))
            D.rect(surf, (96, 190, 120), (bx, r.y + 54, fw, 8), border_radius=4)
            D.rect(surf, (170, 240, 190), (bx + 2, r.y + 55, max(1, fw - 4), 2), border_radius=1)
        D.rect(surf, (60, 64, 88), (bx, r.y + 54, bw, 8), 1, border_radius=4)
    # вкладка «Зелья»: строка — применить, кнопка справа — купить
    if tab == ITEM_TAB:
        for k, it in enumerate(ITEMS):
            r = pygame.Rect(GW + 10, ROW_Y0 + k * ROW_H, PW - 20, ROW_H - 8)
            cnt = s["items"].get(it["key"], 0)
            p = item_price(it, s)
            can = s["money"] >= p
            bg = (44, 100, 64) if cnt > 0 else (48, 51, 70)
            if r.collidepoint(mouse):
                bg = (62, 130, 86) if cnt > 0 else (58, 62, 84)
            card(surf, r, bg, (96, 160, 112) if cnt > 0 else (70, 74, 98),
                 (110, 220, 140) if cnt > 0 else None)
            text(surf, f"{k + 1}. {it['name']}", f_mid, (255, 255, 255), (r.x + 12, r.y + 6),
                 shadow=False)
            bs_ = f"x{cnt}"
            text(surf, bs_, f_small, (255, 226, 90) if cnt else (150, 152, 170),
                 (r.right - twidth(f_small, bs_) - 12, r.y + 9), shadow=False)
            text(surf, it["desc"], f_small, (210, 215, 235), (r.x + 12, r.y + 32), shadow=False)
            br = item_buy_rect(k)
            D.rect(surf, (78, 96, 150) if can else (44, 47, 64), br, border_radius=8)
            if can:
                D.rect(surf, (104, 124, 184), (br.x + 3, br.y + 2, br.w - 6, 8), border_radius=6)
            D.rect(surf, (140, 165, 225) if can else (70, 74, 98), br, 2, border_radius=8)
            text(surf, f"${fmt(p)}", f_small,
                 (255, 255, 255) if can else (140, 144, 168),
                 (br.centerx, br.y + 5), center=True, shadow=False)
        text(surf, "Тап по строке — применить", f_small, (130, 136, 165),
             (GW + 16, H - 66), shadow=False)
    text(surf, "Тап по вкладке или строке магазина", f_small, (130, 136, 165),
         (GW + 16, H - 42), shadow=False)
    text(surf, "Прогресс сохраняется сам", f_small, (130, 136, 165), (GW + 16, H - 24), shadow=False)


# ---------- ресурсы, зависящие от разрешения ----------
VIGNETTE = LAMP_CONE = HEAD_CONE = SHADOW_S = SHADOW_B = RED_FLASH = PANEL_BG = PAUSE_DIM = None
SKULL_IMGS = ()
canvas_buf = world_surf = None


def build_assets():
    """Пересоздаёт всё, что зависит от масштаба рендера (при старте и при смене режима)."""
    global VIGNETTE, LAMP_CONE, HEAD_CONE, SHADOW_S, SHADOW_B, RED_FLASH, PANEL_BG
    global SKULL_IMGS, canvas_buf, world_surf, PAUSE_DIM
    make_fonts()
    pd = pygame.Surface((WP, HP))
    pd.fill((2, 4, 14))
    PAUSE_DIM = fast(pd, False)
    PAUSE_DIM.set_alpha(165)
    for c in (_TC, _GC, _PC, SPR, TRAIN_CACHE):
        c.clear()
    _GB[0] = 0
    VIGNETTE = make_vignette()
    LAMP_CONE = make_cone(230, 170, True, 85)
    HEAD_CONE = make_cone(300, 120, False, 120)
    SHADOW_S = make_shadow(False)
    SHADOW_B = make_shadow(True)
    if not SKULL_IMGS:                      # череп не зависит от масштаба — строим один раз
        SKULL_IMGS = (make_skull(0), make_skull(1))
    rf = pygame.Surface((WP, HP))
    rf.fill((150, 0, 10))
    RED_FLASH = fast(rf, False)
    PANEL_BG = build_panel_bg()
    canvas_buf = pygame.Surface((WP, HP)).convert()
    world_surf = pygame.Surface((GWP, HP)).convert()


build_assets()

RUSH_DUR = 15.0          # «Час пик»: толпа и доход удваиваются
COMBO_MILESTONES = (10, 25, 50, 100, 200)

# ---------- заставка: оригинальное видео и титры «Режиссёр Айс» ----------
# В самом начале игры (и после полного сброса прогресса) проигрывается
# оригинальное видео с кроликом: кадры лежат в папке intro_frames рядом с игрой,
# в exe они вшиты внутрь. После видео — титры «Режиссёр Айс», и только потом
# начинается основной геймплей. Любой клик или клавиша пропускает всё.
# Если кадров найти не удалось — играет запасная цветная анимация кролика.
INTRO_FPS = 10                       # частота кадров оригинального видео
def _frames_dir():
    """В exe кадры лежат рядом с распакованными файлами, в браузере — прямо в архиве."""
    for c in ("intro_frames", os.path.join(_BASE_DIR, "intro_frames")):
        try:
            if any(n.endswith(".png") for n in os.listdir(c)):
                return c
        except OSError:
            pass
    return os.path.join(_BASE_DIR, "intro_frames")


INTRO_FRAMES_DIR = _frames_dir()
INTRO_FRAME_CACHE = None             # кадры держим в памяти только на время заставки
INTRO_RUN = 4.4                      # длительность запасной анимации, если кадров нет
INTRO_GAP = 0.5                      # пауза между кроликом и титрами
INTRO_CREDIT = 2.4                   # сколько держатся титры
INTRO_FADE = 0.7                     # затемнение в начале и в конце
INTRO_END = INTRO_RUN + INTRO_GAP + INTRO_CREDIT + INTRO_FADE
INTRO_HOPS = 5                       # прыжков через экран
HOP_H = (115, 170, 140, 190, 155)    # высота каждого прыжка
BUNNY_ZOOM = 0.62                    # размер кролика относительно нарисованного


def _hsv(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
    return (int(r * 255), int(g * 255), int(b * 255))


def intro_frames():
    """Кадры оригинального видео (10 к/с). Пустой список — нет файлов,
    в этом случае заставка играет запасную анимацию кролика."""
    global INTRO_FRAME_CACHE
    if INTRO_FRAME_CACHE is not None:
        return INTRO_FRAME_CACHE
    out = []
    try:
        for name in sorted(n for n in os.listdir(INTRO_FRAMES_DIR) if n.endswith(".png")):
            out.append(pygame.image.load(os.path.join(INTRO_FRAMES_DIR, name)).convert())
    except (OSError, pygame.error, ValueError):
        out = []
    INTRO_FRAME_CACHE = out
    return out


def bunny_sprite(ear=0.0, squash=1.0, blink=False, tuck=False):
    """Кролик из заставки: бело-розовое пушение, розовые уши и лапки.
    ear — насколько уши отведены назад (в полёте), squash — сплющивание при приземлении."""
    key = ("bunny", K, int(ear / 6), round(squash, 1), blink, tuck)   # грубая квантовка — меньше кэш
    fig = SPR.get(key)
    if fig is None:
        global KD
        KD = K * BUNNY_ZOOM
        try:
            fig = new_surf(140, 180, zoom=BUNNY_ZOOM)
            cx, fy = 68, 168           # середина и линия земли в координатах спрайта
            sy = max(0.55, min(1.3, squash))
            sx = 1.0 + (1.0 - sy) * 0.7      # приседая, кролик расплющивается вширь
            fur = (255, 240, 247)
            fur2 = (255, 253, 255)
            pink = (255, 170, 200)
            pink_d = (232, 120, 160)
            ink = (54, 34, 70)

            def P(u, v):                 # точка: u — от центра, v — вверх от земли
                return (cx + u * sx, fy - v * sy)

            def box(u0, v0, u1, v1):
                x0, y1 = P(u0, v0)
                x1, y0 = P(u1, v1)
                return (x0, y0, max(1.0, x1 - x0), max(1.0, y1 - y0))

            def put_ear(anchor, ang):    # ухо: рисуется отдельно и поворачивается вокруг основания
                e = new_surf(46, 84, zoom=BUNNY_ZOOM)
                D.ellipse(e, fur, (13, 12, 20, 66))
                D.ellipse(e, pink, (18, 20, 10, 48))
                D.ellipse(e, fur2, (15, 15, 6, 22))
                e = pygame.transform.rotate(e, ang)   # положительный угол — верх уха назад
                fig.blit(e, e.get_rect(midbottom=(int(anchor[0] * KD), int(anchor[1] * KD))))

            put_ear(P(-7, 58), 24 + ear * 0.8)                   # дальний ухо
            D.circle(fig, fur2, P(-34, 26), max(3, int(11 * (sx + sy) / 2)))   # хвост
            if tuck:                                             # в полёте лапки поджаты
                D.ellipse(fig, fur, box(-19, 3, -3, 14))
                D.ellipse(fig, fur, box(3, 3, 19, 14))
            else:
                D.ellipse(fig, fur, box(-25, 0, -4, 13))
                D.ellipse(fig, fur, box(4, 0, 25, 13))
            D.ellipse(fig, pink, box(-21, 0, -9, 7))
            D.ellipse(fig, pink, box(9, 0, 21, 7))
            D.ellipse(fig, fur, box(-31, 8, 31, 68))             # тело
            D.ellipse(fig, fur2, box(-25, 15, 5, 46))            # светлый живот
            put_ear(P(9, 60), 8 + ear * 1.3)                     # ближний ухо
            D.circle(fig, pink, P(7, 33), max(2, int(6 * (sx + sy) / 2)))      # щёчка
            ex, ey = P(17, 50)
            if blink:
                D.rect(fig, ink, (ex - 4.5, ey - 1.5, 9, 3), border_radius=1)
            else:
                D.circle(fig, ink, (ex, ey), max(2, int(5.5 * min(sx, sy))))
                D.circle(fig, (255, 255, 255), (ex + 1.5, ey + 2), max(1, int(2 * min(sx, sy))))
            D.ellipse(fig, pink_d, box(26, 44, 34, 51))          # нос
            D.line(fig, ink, P(26, 43), P(32, 41), 2)
            D.line(fig, ink, P(32, 45), P(46, 47), 1)            # усы
            D.line(fig, ink, P(32, 47), P(47, 53), 1)
            D.line(fig, ink, P(15, 37), P(25, 41), 2)            # рот
            return fast(outlined(fig, ink))
        finally:
            KD = K
    return fig


async def run_intro():
    """Заставка перед геймплеем: оригинальное видео с кроликом (или запасная
    анимация), затем титры «Режиссёр Айс». Пропуск — любая клавиша или клик."""
    global win, INTRO_FRAME_CACHE
    state = {"black": None, "vid_idx": -1, "vid_cur": None}
    fonts = {}

    def rebuild():                        # после смены разрешения шрифты и плёнка создаются заново
        fonts["big"] = mfont(86, True)
        fonts["mid"] = mfont(36, True)
        fonts["sml"] = mfont(16)
        b = pygame.Surface((WP, HP))
        b.fill((0, 0, 0))
        state["black"] = fast(b, False)

    rebuild()

    def txt_a(dst, s_, f, col, cx_, cy_, a_):
        if a_ <= 0:
            return
        img = _text_img(s_, f, col, True).copy()
        img.set_alpha(int(255 * max(0.0, min(1.0, a_))))
        dst.blit(img, img.get_rect(center=(px(cx_), px(cy_))))

    frames = intro_frames()            # кадры оригинального видео (или пусто)
    use_video = bool(frames)
    run_dur = len(frames) / float(INTRO_FPS) if use_video else INTRO_RUN
    end_t = run_dur + INTRO_GAP + INTRO_CREDIT + INTRO_FADE
    if use_video:                      # видео вписываем в экран по высоте, по бокам белое
        vw, vh = frames[0].get_size()
        scv = min(WP / vw, HP / vh)
        vid_size = (max(1, int(vw * scv)), max(1, int(vh * scv)))
        vid_pos = ((WP - vid_size[0]) // 2, (HP - vid_size[1]) // 2)
    ground = H * 0.74
    hue0 = random.random()
    t = 0.0
    running = True
    last_hp = 0.0
    parts = []                            # разноцветный след кролика
    puffs = []                            # пыль при приземлении
    sparkles = [(random.uniform(0, W), random.uniform(30, H * 0.62), random.uniform(0, 6.3))
                for _ in range(44)]
    bokeh = [(random.uniform(-60, W + 60), random.uniform(60, H - 90),
              random.uniform(45, 130), random.random(), random.uniform(0.4, 1.6))
             for _ in range(11)]

    while running and t < end_t:
        dt = min(clock.tick(60) / 1000, 0.05)
        await asyncio.sleep(0)          # отдаём кадр браузеру, иначе вкладка зависнет
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.VIDEORESIZE and not fullscreen and not SCALED_OK:
                win = pygame.display.set_mode((max(320, e.w), max(180, e.h)), pygame.RESIZABLE)
            elif e.type == pygame.KEYDOWN and (
                    e.key == pygame.K_F11 or (e.key == pygame.K_RETURN and e.mod & pygame.KMOD_ALT)):
                set_fullscreen(not fullscreen)
                rebuild()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F10:
                change_scale(next((q for q in QUALITY if q > K + 1e-6), QUALITY[0]))
                rebuild()
            elif e.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                running = False           # пропуск: любая клавиша или клик
        t += dt

        canvas = win if SCALED_OK else canvas_buf
        if use_video:
            # --- оригинальное видео: кадры 10 к/с по центру белого экрана ---
            canvas.fill((255, 255, 255))
            if t < run_dur:
                idx = min(len(frames) - 1, int(t * INTRO_FPS))
                if idx != state["vid_idx"]:      # новый кадр — один раз масштабируем
                    state["vid_idx"] = idx
                    state["vid_cur"] = pygame.transform.smoothscale(frames[idx], vid_size)
                canvas.blit(state["vid_cur"], vid_pos)
        else:
            # --- цветной переливающийся фон запасной анимации ---
            c0 = _hsv(hue0 + t * 0.03, 0.60, 0.40)
            c1 = _hsv(hue0 + 0.14 + t * 0.03, 0.72, 0.85)
            vband(canvas, 0, W, 0, H, c0, c1)
            for i, (bx, by, br, bh, bst) in enumerate(bokeh):
                glow(canvas, (bx + 46 * math.sin(t * 0.5 + i * 1.7),
                              by + 26 * math.cos(t * 0.42 + i * 2.1)),
                     br, _hsv(round((hue0 + bh + t * 0.04) * 36) / 36, 0.7, 1.0), 55)
            for (sx_, sy_, ph) in sparkles:
                a = 0.5 + 0.5 * math.sin(t * 3.0 + ph)
                if a > 0.5:
                    glow(canvas, (sx_, sy_), 12, (255, 255, 255), int(110 * a))
            # --- земля, по которой бегает кролик ---
            gy = int(ground)
            gcol = lerp_c(c1, (0, 0, 0), 0.45)
            vband(canvas, 0, W, gy, H, gcol, lerp_c(c0, (0, 0, 0), 0.62))
            stripe = _hsv(hue0 + t * 0.45, 0.85, 1.0)
            D.rect(canvas, lerp_c(stripe, (0, 0, 0), 0.25), (0, gy - 5, W, 7))
            D.rect(canvas, stripe, (0, gy - 5, W, 3))
            D.rect(canvas, (255, 255, 255), (0, gy - 5, W, 1))

        # --- кролик перепрыгивает экран (запасная анимация, если кадров нет) ---
        if not use_video and t < INTRO_RUN:
            p = t / INTRO_RUN
            x = lerp(-80, W + 80, p)
            hp = (p * INTRO_HOPS) % 1.0
            i = min(INTRO_HOPS - 1, int(p * INTRO_HOPS))
            hgt = HOP_H[i] * math.sin(math.pi * hp)
            y = ground - hgt
            tw = max(10, 36 - hgt * 0.14)                      # тень на земле
            D.ellipse(canvas, lerp_c(gcol, (0, 0, 0), 0.55), (x - tw, gy - 4, tw * 2, 11))
            if hp < last_hp and t > 0.1:                       # приземлился — пыль
                for _ in range(7):
                    puffs.append([x + random.uniform(-16, 16), gy - 2,
                                  random.uniform(8, 20), 1.0])
            last_hp = hp
            sq = 1.0 - 0.20 * math.cos(2 * math.pi * hp)       # сплющился на земле, тянется в воздухе
            in_air = 0.1 < hp < 0.9
            ear = 34 * math.sin(math.pi * hp) if in_air else 10 * math.sin(t * 11 + i)
            rot = 360.0 * hp if i in (1, 3) else 26 * math.sin(math.pi * hp)   # парочка сальто
            fig = bunny_sprite(ear, sq, blink=(t % 3.2) < 0.13, tuck=in_air)
            if abs(rot) > 0.4:
                fig = pygame.transform.rotate(fig, -rot)       # вперёд — по часовой стрелке
            blit_c(canvas, fig, x, y - 78 * BUNNY_ZOOM)        # 78 — половина высоты до лап
            if random.random() < 0.5:                          # разноцветный искристый след
                parts.append(Particle(x - 24, y - 34,
                                      _hsv(hue0 + t * 0.6 + random.random() * 0.12, 0.9, 1.0)))
        for pf in puffs:
            pf[1] -= 22 * dt
            pf[2] += 34 * dt
            pf[3] -= dt * 1.5
        puffs = [pf for pf in puffs if pf[3] > 0]
        for pf in puffs:
            glow(canvas, (pf[0], pf[1]), pf[2], (255, 255, 255), int(80 * pf[3]))
        for pt_ in parts:
            pt_.update(dt)
            pt_.draw(canvas)
        parts = [pt_ for pt_ in parts if pt_.life > 0][-160:]

        # --- титры «Режиссёр Айс» ---
        ct = t - (run_dur + INTRO_GAP)
        if ct >= 0:
            a = max(0.0, min(1.0, ct / 0.6) * min(1.0, (end_t - t) / INTRO_FADE))
            state["black"].set_alpha(int(215 * a))     # экран темнеет из белого — и титры
            canvas.blit(state["black"], (0, 0))
            pulse = 0.5 + 0.5 * math.sin(t * 3.2)
            glow(canvas, (W // 2, H // 2 + 6), 300, (255, 210, 90), int((60 + 45 * pulse) * a))
            txt_a(canvas, "РЕЖИССЁР", fonts["mid"], (255, 238, 180), W // 2, H // 2 - 74, a)
            txt_a(canvas, "АЙС", fonts["big"], (255, 255, 255), W // 2, H // 2 + 6, a)
            lw_ = int(320 * a)                                # линия под титрами растёт из центра
            D.rect(canvas, (255, 214, 96), (W // 2 - lw_ // 2, H // 2 + 74, lw_, 4))
            if lw_ > 10:
                D.circle(canvas, (255, 240, 170), (W // 2 - lw_ // 2, H // 2 + 76), 5)
                D.circle(canvas, (255, 240, 170), (W // 2 + lw_ // 2, H // 2 + 76), 5)

        # --- подсказка о пропуске и затемнение ---
        if running and t < run_dur:
            txt_a(canvas, "пропустить — тап по экрану", fonts["sml"],
                  (70, 70, 95) if use_video else (240, 240, 255), W - 235, H - 22, 0.45)
        if not use_video and t < INTRO_FADE:      # у видео вход и так начинается с белого
            state["black"].set_alpha(int(255 * (1 - t / INTRO_FADE)))
            canvas.blit(state["black"], (0, 0))
        if t > end_t - INTRO_FADE:
            state["black"].set_alpha(int(255 * min(1.0, (t - (end_t - INTRO_FADE)) / INTRO_FADE)))
            canvas.blit(state["black"], (0, 0))

        ww, wh = win.get_size()
        sc = 1.0 if SCALED_OK else min(ww / WP, wh / HP)
        dw, dh = max(1, int(WP * sc)), max(1, int(HP * sc))
        ox, oy = (ww - dw) // 2, (wh - dh) // 2
        if not SCALED_OK:
            win.fill((0, 0, 0))
            if (dw, dh) == (WP, HP):
                win.blit(canvas_buf, (ox, oy))
            else:
                win.blit(pygame.transform.smoothscale(canvas_buf, (dw, dh)), (ox, oy))
        pygame.display.flip()

    INTRO_FRAME_CACHE = None          # кадры видео не держим в памяти после заставки


async def main():
    global win, fullscreen
    await run_intro()               # заставка: видео и титры «Режиссёр Айс»
    s = load_save()
    world = World()
    st = s["level"]
    g = dict(people=[], effects=[], particles=[], rings=[], train=None, spawn=0.5, next_train=4.0,
             warn=0.0, combo=0, combo_t=0.0, helper_t=0.0, shake=0.0,
             stage=st, prev=st, trans=1.0, toast="", toast_t=0.0, toast_col=(255, 235, 120),
             boss=None, boss_cd=0.0, tab=0, idle=0.0, bot_t=0.0,
             fx={k: 0.0 for k in FX_LABELS}, acid=0.0, splats=None,
             acids=[], skulls=[], decals=[],
             lives=HARD_LIVES, hard_t=0.0, life_flash=0.0,
             coins=[], coin_t=random.uniform(12, 22), rush=0.0, rush_t=random.uniform(45, 75),
             coins_got=0, paused=False, confirm_until=0,
             secret_t=random.uniform(50, 100))
    save_t = 5.0

    def lv(k):
        return s["levels"][k]

    def scale_boss(b):
        """HP босса умножается на коэффициент от урона за клик (см. boss_dmg_scale)."""
        f = boss_dmg_scale(lv("smash"))
        b.max_hp *= f
        b.hp = b.max_hp

    def earn(n):
        """Весь заработок копится и в s["earned"] — от него считается инфляция."""
        s["money"] += n
        s["earned"] += n

    def lose_lives(xs):
        """Хардкор: каждый ушедший с платформы — минус жизнь; ноль жизней — новый забег."""
        for x in xs:
            g["lives"] -= 1
            g["life_flash"] = 0.5
            g["shake"] = max(g["shake"], 0.6)
            g["effects"].append(Effect(max(60, min(GW - 60, x)), PLAT_TOP,
                                       "-1 ЖИЗНЬ", (255, 80, 70)))
            if g["lives"] <= 0:
                t = g["hard_t"]
                g["lives"] = HARD_LIVES
                g["hard_t"] = 0.0
                g["combo"] = 0
                g["combo_t"] = 0.0
                g["people"].clear()       # новый забег начинается с пустой платформы
                # награда за забег: открывается следующий скин для прохожих
                new_skin = None
                if s["skins"] < len(SKINS):
                    s["skins"] += 1
                    new_skin = SKINS[s["skins"] - 1]["name"]
                if new_skin:
                    g["toast"] = f"СКИН «{new_skin}»! Забег {fmt_time(t)}"
                    g["toast_col"] = (255, 220, 120)
                else:
                    g["toast"] = f"ЗАБЕГ ОКОНЧЕН! Продержался {fmt_time(t)}"
                    g["toast_col"] = (255, 90, 80)
                g["toast_t"] = 3.0
                g["shake"] = 1.0
                g["life_flash"] = 1.0
                write_save(s)
                return                    # остальные ушедшие этого кадра уже не считаются

    def income_mult():
        m = 1 + 0.15 * lv("mult")
        if g["fx"]["p_money"] > 0:
            m *= 2
        if g["rush"] > 0:
            m *= 2
        return m

    def push_radius():
        """Радиус толчка (зелье «Супер-толчок» его удваивает)."""
        r = lv("power") * 35
        r = r * 2 if g["fx"]["p_power"] > 0 else r
        bsr = g["boss"]
        if bsr is not None and getattr(bsr, "slime", False) and bsr.state == "fight" and bsr.fakes:
            r *= 0.5                      # пока живы копии слизня, радиус клика вдвое меньше
        return r

    def slime_pos(bs, mx, my):
        """Куда на самом деле попадёт клик: вязкий курсор отстаёт, злой курсор подменяет."""
        ax, ay = g.get("aim", (mx, my))
        if math.hypot(ax - mx, ay - my) > 3:
            mx, my = ax, ay
        if bs.evil_t > 0 and random.random() < 0.5:
            ex, ey = bs.evil_pos(mx, my)
            mx, my = max(0.0, min(GW - 1.0, ex)), max(0.0, min(H - 1.0, ey))
            g["effects"].append(Effect(mx, my, "ПОДМЕНА!", (255, 90, 90)))
        return mx, my

    def slime_click(bs, mx, my, rad):
        """Клик по слизню: кислота, панцирные точки, ложные копии, настоящий босс."""
        if bs.blocked(mx, my):
            g["effects"].append(Effect(mx, my, "ЗАЛИТО!", (150, 235, 110)))
            return
        bs.click_log.append((mx, my))
        del bs.click_log[:-8]
        sc_ = bs.scale
        for sh in bs.shells[:]:
            if math.hypot(mx - (bs.x + sh["dx"] * sc_), my - (bs.y + sh["dy"] * sc_)) < 24:
                sh["hp"] -= 1
                g["effects"].append(Effect(mx, my, "ТРЕСК!", (200, 210, 230)))
                for _ in range(6):
                    g["particles"].append(Particle(mx, my, (190, 198, 218)))
                if sh["hp"] <= 0:
                    bs.shells.remove(sh)
                    if not bs.shells:
                        bs.vuln = max(bs.vuln, 1.5)
                        g["effects"].append(Effect(bs.x, bs.y - 40, "ПАНЦИРЬ СЛОМАН!", (255, 235, 90)))
                return
        for fk in bs.fakes[:]:
            if fk.rect().inflate(rad, rad).collidepoint(mx, my):
                fk.hp -= 1
                fk.hit_t = 0.2
                if fk.hp <= 0:
                    bs.fakes.remove(fk)
                    g["effects"].append(Effect(fk.x, fk.y - 40, "ПУФ! копия", (150, 255, 150)))
                    for _ in range(14):
                        g["particles"].append(Particle(fk.x, fk.y - 40, (110, 230, 120)))
        if bs.rect().inflate(rad, rad).collidepoint(mx, my):
            dmg = 1 + 2 * lv("smash")
            crit = random.random() < 0.05 * lv("crit")
            if crit:
                dmg *= 3
            smash(bs, dmg, mx, my, crit)

    def spawn_slime():
        sb = SlimeBoss(s["level"])
        sb.time_left += 5 * lv("timebonus")
        scale_boss(sb)
        g["boss"] = sb
        g["toast"] = "СЕКРЕТНЫЙ БОСС: Слизень!"
        g["toast_col"] = (140, 255, 150)
        g["toast_t"] = 3.5
        g["shake"] = 0.5
        confetti(GW - 150, 260, 30)

    def confetti(x, y, n=40):
        palette = [(255, 90, 90), (255, 220, 60), (90, 220, 120), (90, 170, 255),
                   (220, 110, 255), (255, 160, 60)]
        for _ in range(n):
            g["particles"].append(Particle(x, y, random.choice(palette)))

    def smash(bs, dmg, x, y, crit=False):
        res = bs.hit(dmg)
        if res == "dodge":
            g["effects"].append(Effect(x, bs.y - 60, "УВЕРНУЛСЯ!", (200, 200, 255)))
        elif res == "block":
            g["effects"].append(Effect(x, bs.y - 60, "БЛОК!", (120, 190, 255)))
        elif res == "ok":
            dmg = bs.last_dmg
            g["effects"].append(Effect(x, bs.y - 60, f"КРИТ! -{dmg}" if crit else f"-{dmg}",
                                       (255, 200, 60) if crit else (255, 120, 100)))
            for _ in range(5 if not crit else 12):
                g["particles"].append(Particle(x, y, (255, 220, 60)))
            for _ in range(4 if not crit else 9):
                g["particles"].append(Particle(x + random.uniform(-6, 6), y - 6,
                                               (random.randint(140, 205), 18, 22)))
            if bs.state == "fall":
                g["shake"] = 0.5
                g["toast"] = "Босс повержен! Дождись поезда!"
                g["toast_col"] = (255, 235, 120)
                g["toast_t"] = 3.0
        return res

    def explode(b):
        """Бомба-пассажир рвётся: сбивает всех рядом, цепная реакция, урон боссу."""
        g["shake"] = max(g["shake"], 0.55)
        g["effects"].append(Effect(b.x, b.y - 20, "БУМ!", (255, 160, 60)))
        for _ in range(45):
            g["particles"].append(Particle(b.x, b.y - 40, random.choice(
                [(255, 220, 90), (255, 140, 40), (255, 80, 40), (90, 90, 100)])))
        hit = 0
        for q in g["people"]:
            if q is not b and q.state == "walk" and abs(q.x - b.x) < 135:
                q.push(direct=True)
                if q.state == "fall":
                    hit += 1
        bs_ = g["boss"]
        if bs_ and bs_.state == "fight" and abs(bs_.x - b.x) < 150:
            smash(bs_, 6 + 3 * lv("smash"), bs_.x, bs_.y - 90)
        if hit >= 3:
            g["effects"].append(Effect(b.x, b.y - 70, f"ЦЕПНАЯ РЕАКЦИЯ x{hit}!", (255, 210, 90)))

    def collect_coin(c):
        reward = round(10 * 1.35 ** lv("income") * 12 * income_mult())
        earn(reward)
        g["coins_got"] += 1
        g["effects"].append(Effect(c.x, c.y, f"МОНЕТА! +${fmt(reward)}", (255, 225, 60)))
        for _ in range(22):
            g["particles"].append(Particle(c.x, c.y, random.choice(
                [(255, 215, 0), (255, 245, 150), (255, 255, 255)])))
        g["coins"].remove(c)

    def after_scale():
        """Смена разрешения: готовые поверхности старого размера больше не годятся."""
        g["decals"].clear()
        g["splats"] = make_acid_overlay() if g["acid"] > 0 else None

    def pause_rects():
        return [pygame.Rect(W // 2 - 170, 230 + i * 68, 340, 54) for i in range(3)]

    def reset_progress():
        """Полный сброс: новое сохранение и чистое игровое состояние."""
        fresh = new_save()
        s.clear()
        s.update(fresh)
        for k in ("people", "effects", "particles", "rings", "acids", "skulls", "decals", "coins"):
            g[k] = []
        g.update(train=None, spawn=0.5, next_train=4.0, warn=0.0, combo=0, combo_t=0.0,
                 helper_t=0.0, shake=0.0, stage=0, prev=0, trans=1.0, boss=None, boss_cd=0.0,
                 idle=0.0, bot_t=0.0, acid=0.0, splats=None, lives=HARD_LIVES, hard_t=0.0,
                 life_flash=0.0, rush=0.0, rush_t=random.uniform(45, 75),
                 coin_t=random.uniform(12, 22), coins_got=0, confirm_until=0,
                 secret_t=random.uniform(50, 100))
        for k in g["fx"]:
            g["fx"][k] = 0.0
        g["intro_pending"] = True      # после сброса заставка показывается заново
        g["toast"] = "Прогресс сброшен — начинаем заново!"
        g["toast_col"] = (255, 235, 120)
        g["toast_t"] = 3.0
        write_save(s)

    def pause_click(mx, my):
        for i, r in enumerate(pause_rects()):
            if not r.collidepoint(mx, my):
                continue
            if i == 0:
                g["paused"] = False
            elif i == 1:
                if pygame.time.get_ticks() < g["confirm_until"]:   # второй клик — подтверждение
                    reset_progress()
                    g["paused"] = False
                else:
                    g["confirm_until"] = pygame.time.get_ticks() + 3500
            else:
                write_save(s)
                pygame.quit()
                sys.exit()
            return

    while True:
        dt = min(clock.tick(60) / 1000, 0.05)
        await asyncio.sleep(0)
        ww, wh = win.get_size()
        # SCALED: окно уже в пикселях рендера, мышь приходит в тех же координатах;
        # запасной режим (старый pygame): масштабируем картинку сами
        sc = 1.0 if SCALED_OK else min(ww / WP, wh / HP)
        dw, dh = max(1, int(WP * sc)), max(1, int(HP * sc))
        ox, oy = (ww - dw) // 2, (wh - dh) // 2

        def mp(pos):
            return ((pos[0] - ox) / sc / K, (pos[1] - oy) / sc / K)

        mouse = mp(pygame.mouse.get_pos())

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                write_save(s)
                pygame.quit()
                sys.exit()
            elif e.type == pygame.KEYDOWN:
                idx = e.key - pygame.K_1
                if e.key == pygame.K_F11 or (e.key == pygame.K_RETURN and e.mod & pygame.KMOD_ALT):
                    if set_fullscreen(not fullscreen):
                        after_scale()
                elif e.key == pygame.K_ESCAPE:          # Esc — пауза / продолжить
                    g["paused"] = not g["paused"]
                    g["confirm_until"] = 0
                elif e.key == pygame.K_F10:         # качество картинки: 1x → 1.5x → 2x
                    change_scale(next((q for q in QUALITY if q > K + 1e-6), QUALITY[0]))
                    after_scale()
                elif g["paused"]:
                    pass                                # на паузе игровые клавиши не работают
                elif e.key == pygame.K_TAB:
                    g["tab"] = (g["tab"] + 1) % len(TAB_NAMES)
                elif 0 <= idx < ROWS_PER_TAB:
                    if g["tab"] == ITEM_TAB:
                        use_item(s, idx, g)
                    else:
                        buy(s, g["tab"] * ROWS_PER_TAB + idx, g)
            elif e.type == pygame.VIDEORESIZE and not fullscreen and not SCALED_OK:
                win = pygame.display.set_mode((max(320, e.w), max(180, e.h)), pygame.RESIZABLE)
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = mp(e.pos)
                if mobile_btn_hit(mx, my):
                    g["paused"] = not g["paused"]
                    g["confirm_until"] = 0
                elif g["paused"]:
                    pause_click(mx, my)
                elif mx < GW:
                    g["rings"].append([mx, my, 0.3])
                    coin = next((c for c in g["coins"] if math.hypot(mx - c.x, my - c.y) < 38), None)
                    if coin:
                        collect_coin(coin)          # монета ловится вместо толчка
                    else:
                        rad = push_radius()
                        for p in g["people"]:
                            if p.state != "walk":
                                continue
                            direct = p.rect().collidepoint(mx, my)
                            if direct or p.rect().inflate(rad * 2, rad * 2).collidepoint(mx, my):
                                p.push(direct=direct)
                        bs = g["boss"]
                        if bs and bs.state == "fight" and bs.rect().inflate(rad, rad).collidepoint(mx, my):
                            dmg = 1 + 2 * lv("smash")
                            crit = random.random() < 0.05 * lv("crit")
                            if crit:
                                dmg *= 3
                            smash(bs, dmg, mx, my, crit)
                else:
                    if TAB_Y <= my < TAB_Y + 26:
                        g["tab"] = max(0, min(len(TAB_NAMES) - 1,
                                              int((mx - (GW + 10)) // TAB_GAP)))
                    else:
                        k = int((my - ROW_Y0) // ROW_H)
                        if g["tab"] == ITEM_TAB:
                            if 0 <= k < len(ITEMS):
                                if item_buy_rect(k).collidepoint(mx, my):
                                    buy_item(s, k, g)
                                else:
                                    use_item(s, k, g)
                        elif 0 <= k < ROWS_PER_TAB:
                            buy(s, g["tab"] * ROWS_PER_TAB + k, g)

        if g.get("intro_pending"):
            # после полного сброса прогресса кролик и титры идут заново
            g["intro_pending"] = False
            g["paused"] = False
            await run_intro()

        if g["paused"]:
            dt = 0.0                  # пауза: время в игре стоит
        # хардкор включается сразу после 10-го уровня: идут секундомер и жизни
        hard = bool(s["won"])
        if hard:
            g["hard_t"] += dt
        g["life_flash"] = max(0.0, g["life_flash"] - dt)

        # «Час пик»: случайное событие — народу и денег вдвое больше
        if g["rush"] > 0:
            g["rush"] = max(0.0, g["rush"] - dt)
            if g["rush"] <= 0:
                g["toast"] = "Час пик закончился"
                g["toast_col"] = (200, 210, 235)
                g["toast_t"] = 1.6
        else:
            g["rush_t"] -= dt
            if g["rush_t"] <= 0:
                g["rush"] = RUSH_DUR
                g["rush_t"] = random.uniform(70, 110)
                g["toast"] = "ЧАС ПИК! Толпа и доход x2!"
                g["toast_col"] = (255, 190, 90)
                g["toast_t"] = 3.0
                g["shake"] = max(g["shake"], 0.25)
                confetti(GW // 2, 200, 30)

        # падающие монеты
        g["coin_t"] -= dt
        if g["coin_t"] <= 0:
            g["coin_t"] = random.uniform(16, 30)
            g["coins"].append(Coin())
            if random.random() < 0.3:
                g["coins"].append(Coin())
        for c in g["coins"]:
            c.update(dt)
        g["coins"] = [c for c in g["coins"] if c.t > 0]

        # спавн: зелье потока удваивает поток, дальше по платформе — всё пёстрее
        g["spawn"] -= dt
        flow = 1 + 0.25 * lv("flow")
        boosted = g["fx"]["p_flow"] > 0
        if boosted:
            flow *= 2
        if g["rush"] > 0:
            flow *= 2
        # в хардкоре народу в разы больше: и поток чаще, и вместимость выше
        crowd = 4 if hard else 1
        max_people = min(90 if hard else 46,
                         (14 + 2 * lv("cap")) * (2 if (boosted or g["rush"] > 0) else 1) * crowd)
        if g["spawn"] <= 0 and len(g["people"]) < max_people:
            gold = random.random() < 0.04 + 0.03 * lv("gold")
            g["people"].append(Person(gold, pick_kind(s["kills"]), pick_skin(s)))
            g["spawn"] = random.uniform(1.2, 2.2) / (flow * (1 + min(0.5, s["kills"] / 4000.0))
                                                     * (2.5 if hard else 1))

        # пассивный доход
        if lv("idle") > 0:
            g["idle"] += 3 * lv("idle") * dt
            n = int(g["idle"])
            if n:
                earn(n)
                g["idle"] -= n

        # помощник
        if lv("helper") > 0:
            g["helper_t"] += dt
            if g["helper_t"] >= max(0.6, 6.0 - 0.7 * (lv("helper") - 1)):
                g["helper_t"] = 0.0
                walkers = [p for p in g["people"] if p.state == "walk" and 20 < p.x < GW - 20]
                if walkers:
                    random.choice(walkers).push()

        # поезд: зелье «Сжатое расписание» ускоряет подход поезда
        hurry = 2 if g["fx"]["p_train"] > 0 else 1
        if g["train"] is None:
            g["next_train"] -= dt * hurry
            if g["next_train"] <= 2.0:
                g["warn"] = g["next_train"]
            if g["next_train"] <= 0:
                g["train"] = Train(random.random() < 0.04 * lv("gtrain"))
                g["warn"] = 0
                g["effects"].append(Effect(GW - 140, 500, "ТУ-ТУУУ!", (255, 235, 120)))
                g["shake"] = max(g["shake"], 0.15)
        else:
            g["train"].update(dt)
            if g["train"].done():
                g["train"] = None
                g["next_train"] = random.uniform(5, 7) * 0.92 ** lv("trains") * (0.5 if hurry > 1 else 1)

        # босс
        if g["boss_cd"] > 0:
            g["boss_cd"] -= dt
        if (g["boss"] is None and g["boss_cd"] <= 0 and not s["won"]
                and s["kills"] >= boss_at(s["level"])):
            g["boss"] = Boss(s["level"])
            g["boss"].time_left += 5 * lv("timebonus")
            scale_boss(g["boss"])
            g["toast"] = f"БОСС: {g['boss'].name}!"
            g["toast_col"] = (255, 110, 90)
            g["toast_t"] = 3.0
            g["shake"] = 0.4
        # секретный мини-босс: изредка выходит на платформу, если пора не на основного
        if (g["boss"] is None and g["boss_cd"] <= 0
                and not (not s["won"] and s["kills"] >= boss_at(s["level"]))):
            g["secret_t"] -= dt
            if g["secret_t"] <= 0:
                g["secret_t"] = random.uniform(80, 150)
                if s["kills"] >= 8 and random.random() < 0.7:
                    sb = FlyingBoss(s["level"]) if random.random() < 0.35 else SecretBoss(s["level"])
                    sb.time_left += 5 * lv("timebonus")
                    scale_boss(sb)
                    g["boss"] = sb
                    g["toast"] = f"СЕКРЕТНЫЙ БОСС: {sb.name}!"
                    g["toast_col"] = (255, 215, 70)
                    g["toast_t"] = 3.5
                    g["shake"] = 0.5
                    confetti(GW - 150, 260, 30)
        bs = g["boss"]
        if bs:
            # помощник-боец
            if lv("bot") > 0 and bs.state == "fight":
                g["bot_t"] += dt
                if g["bot_t"] >= 1.0:
                    g["bot_t"] = 0.0
                    smash(bs, 2 * lv("bot"), bs.x, bs.y - 90)
            bs.update(dt)
            for _txt, _col in bs.events:
                g["effects"].append(Effect(bs.x, bs.y - 90, _txt, _col))
            bs.events.clear()
            if getattr(bs, "spit", False):          # плевок кислотой в камеру
                bs.spit = False
                g["acids"].append(Acid(bs.x, bs.y - 150))
                g["toast"] = "Босс плевётся кислотой!"
                g["toast_col"] = (165, 255, 95)
                g["toast_t"] = 1.6
            if bs.landed:
                bs.landed = False
                if g["train"] is None:
                    g["next_train"] = min(g["next_train"], 2.5)
            if bs.state == "gone":
                g["boss"] = None
                g["boss_cd"] = 8.0
                g["toast"] = ("Секретный босс сбежал..." if bs.secret
                              else "Босс ушёл! Он скоро вернётся...")
                g["toast_col"] = (255, 235, 120)
                g["toast_t"] = 3.0
            elif (bs.state in ("fall", "track") and g["train"] and bs.y > 430
                  and g["train"].rect().inflate(0, 40).colliderect(bs.rect())):
                reward = round(250 * (bs.level + 1) ** 2 * income_mult() * (4 if bs.secret else 1) * 1.5)
                earn(reward)
                s["kills"] += 8 if bs.secret else 3
                g["shake"] = 0.7
                g["effects"].append(Effect(bs.x, bs.y, ("СЕКРЕТНЫЙ БОСС ПОВЕРЖЕН! " if bs.secret else "БОСС ПОВЕРЖЕН! ")
                                           + f"+${fmt(reward)}", (255, 225, 60)))
                for _ in range(60):
                    g["particles"].append(Particle(bs.x, bs.y - 60, random.choice(
                        [(255, 255, 255), (255, 220, 60), (255, 150, 60), (255, 90, 90)])))
                for _ in range(40):
                    g["particles"].append(Particle(bs.x + random.uniform(-24, 24), bs.y - 70,
                                                   (random.randint(120, 190), 14, 18)))
                confetti(bs.x, bs.y - 90, 50)
                g["decals"].append(Decal(bs.x, TRACK_Y + 8, big=True))
                if random.random() < skull_chance(s["level"], 0.35):      # череп босса летит в камеру
                    g["skulls"].append(SkullFly(bs.x, bs.y - 100))
                if bs.secret:
                    g["toast"] = f"СЕКРЕТНЫЙ БОСС «{bs.name}» ПОВЕРЖЕН!"
                elif s["level"] < len(THEMES) - 1:
                    s["level"] += 1
                    g["toast"] = f"УРОВЕНЬ {s['level'] + 1}: {THEMES[s['level']]['name']}"
                    newly = [u["name"] for u in UPGRADES if u["req"] == s["level"]]
                    if newly:
                        g["toast"] += "  •  новое улучшение!"
                else:
                    s["won"] = True
                    g["toast"] = "ПОБЕДА! ХАРДКОР: ушёл = -1 жизнь!"
                g["toast_col"] = (255, 235, 120)
                g["toast_t"] = 4.0
                g["boss"] = None
                g["boss_cd"] = 10.0 if bs.secret else 3.0
                if bs.secret:
                    g["secret_t"] = random.uniform(100, 170)
                write_save(s)

        # люди и столкновения с поездом
        escapes = []
        for p in g["people"]:
            p.update(dt)
            if p.boom and p.state in ("fall", "track"):
                p.boom = False
                explode(p)
            if (hard and p.state == "walk" and p.entered
                    and (p.x < -55 or p.x > GW + 55)):
                p.state = "gone"
                escapes.append(p.x)
            if g["train"] and p.state in ("fall", "track") and p.y > 430:
                if g["train"].rect().inflate(0, 40).colliderect(p.rect()):
                    g["combo"] += 1
                    g["combo_t"] = 6.0 + lv("combot")
                    cap = 1.5 + 0.5 * lv("combo")
                    mult = min(1 + 0.1 * g["combo"], cap)
                    reward = round(10 * 1.35 ** lv("income") * mult * (5 if p.gold else 1)
                                   * (3 if g["train"].gold else 1) * income_mult())
                    earn(reward)
                    s["kills"] += 1
                    g["shake"] = 0.3
                    g["effects"].append(Effect(p.x, p.y, f"БАМ! +${fmt(reward)}",
                                               (255, 225, 60) if p.gold else (255, 255, 255)))
                    # серия: за каждую круглую отметку комбо — премия и конфетти
                    if g["combo"] in COMBO_MILESTONES:
                        bonus = round(reward * g["combo"])
                        earn(bonus)
                        g["effects"].append(Effect(GW // 2, 330, f"СЕРИЯ x{g['combo']}! +${fmt(bonus)}",
                                                   (255, 150, 90)))
                        g["toast"] = f"СЕРИЯ x{g['combo']}!  Премия ${fmt(bonus)}"
                        g["toast_col"] = (255, 170, 100)
                        g["toast_t"] = 2.2
                        confetti(p.x, p.y - 60, 45)
                    for _ in range(16):
                        pc = (255, 215, 0) if p.gold else random.choice(
                            [(255, 255, 255), (255, 220, 60), (255, 150, 60)])
                        g["particles"].append(Particle(p.x, p.y - 40, pc))
                    # кровь: брызги вокруг и пятно на путях
                    for _ in range(20):
                        g["particles"].append(Particle(p.x + random.uniform(-10, 10), p.y - 34,
                                                       (random.randint(120, 195), 14, 18)))
                    g["decals"].append(Decal(p.x + random.uniform(-16, 16),
                                             TRACK_Y + random.uniform(-12, 16), big=p.value > 1))
                    if len(g["decals"]) > 60:
                        g["decals"].pop(0)
                    if random.random() < skull_chance(s["level"], 0.07):   # череп в камеру
                        g["skulls"].append(SkullFly(p.x, p.y - 70))
                    p.state = "gone"
        if escapes:
            lose_lives(escapes)
        if g["combo"] > 0:
            g["combo_t"] -= dt
            if g["combo_t"] <= 0:
                g["combo"] = 0
        for ef in g["effects"]:
            ef.update(dt)
        for pt in g["particles"]:
            pt.update(dt)
        for rg in g["rings"]:
            rg[2] -= dt
        for a in g["acids"]:
            a.update(dt)
            if a.done:
                g["acid"] = 5.0                     # 5 секунд слепоты
                g["splats"] = make_acid_overlay()
                g["shake"] = max(g["shake"], 0.5)
                g["toast"] = "КИСЛОТА В ГЛАЗА!"
                g["toast_col"] = (165, 255, 95)
                g["toast_t"] = 2.5
        g["acids"] = [a for a in g["acids"] if not a.done]
        g["acid"] = max(0.0, g["acid"] - dt)
        if g["acid"] <= 0:
            g["splats"] = None
        for k in g["fx"]:
            if g["fx"][k] > 0:
                g["fx"][k] = max(0.0, g["fx"][k] - dt)
        for dc in g["decals"]:
            dc.update(dt)
        for sk in g["skulls"]:
            sk.update(dt)
        g["decals"] = [dc for dc in g["decals"] if dc.t > 0][-60:]
        if any(sk.t >= sk.dur for sk in g["skulls"]):
            g["shake"] = max(g["shake"], 0.25)
        g["skulls"] = [sk for sk in g["skulls"] if sk.t < sk.dur]
        g["shake"] = max(0.0, g["shake"] - dt)
        g["people"] = [p for p in g["people"]
                       if p.state != "gone"
                       and not (p.state == "track" and p.timer <= 0)
                       and -60 < p.x < GW + 60]
        g["effects"] = [ef for ef in g["effects"] if ef.t > 0]
        g["particles"] = [pt for pt in g["particles"] if pt.life > 0][-600:]
        g["rings"] = [rg for rg in g["rings"] if rg[2] > 0]

        # смена локации
        new_stage = s["level"]
        if new_stage != g["stage"]:
            g["prev"] = g["stage"]
            g["stage"] = new_stage
            g["trans"] = 0.0
        if g["trans"] < 1.0:
            g["trans"] = min(1.0, g["trans"] + dt / 3.0)
            if g["trans"] >= 1.0:
                g["prev"] = g["stage"]
        g["toast_t"] = max(0.0, g["toast_t"] - dt)
        e_t = g["trans"] * g["trans"] * (3 - 2 * g["trans"])
        if g["trans"] < 1.0:
            e_t = round(e_t * 24) / 24      # 24 шага перехода: слои фона не пересобираются каждый кадр
        col = blend(THEMES[g["prev"]], THEMES[g["stage"]], e_t)
        cur = THEMES[g["stage"]] if g["trans"] > 0.4 else THEMES[g["prev"]]
        kind, name = cur["kind"], cur["name"]
        world.update(dt, kind)

        # автосохранение
        save_t -= dt
        if save_t <= 0:
            write_save(s)
            save_t = 5.0

        # ---------- отрисовка мира ----------
        canvas = win if SCALED_OK else canvas_buf
        amp = int(8 * g["shake"] / 0.3)
        # без тряски рисуем прямо в экран; при тряске — в буфер, который потом сдвигаем
        wsurf = world_surf if amp else canvas.subsurface((0, 0, GWP, HP))
        world.draw_back(wsurf, col, kind, name)
        # светофор
        on = g["warn"] > 0 and int(g["warn"] * 6) % 2 == 0
        D.rect(wsurf, (50, 50, 58), (GW - 62, 300, 14, PLAT_TOP - 300))
        D.rect(wsurf, (90, 90, 104), (GW - 62, 300, 3, PLAT_TOP - 300))
        D.rect(wsurf, (30, 30, 36), (GW - 76, 242, 42, 66), border_radius=7)
        D.rect(wsurf, (80, 82, 96), (GW - 76, 242, 42, 66), 2, border_radius=7)
        D.circle(wsurf, (255, 50, 50) if on else (100, 25, 25), (GW - 55, 262), 12)
        D.circle(wsurf, (60, 230, 100) if not on and g["warn"] <= 0 else (20, 70, 36),
                           (GW - 55, 292), 10)
        if on:
            glow(wsurf, (GW - 55, 262), 70, (255, 60, 60), 160)
            D.circle(wsurf, (255, 170, 160), (GW - 58, 258), 4)
        for p in g["people"]:
            p.draw(wsurf, warn=hard)
        for c in g["coins"]:
            c.draw(wsurf)
        if g["boss"]:
            g["boss"].draw(wsurf)
        if g["train"]:
            g["train"].draw(wsurf, col, col["light"])
        for dc in g["decals"]:
            dc.draw(wsurf)
        for pt in g["particles"]:
            pt.draw(wsurf)
        for ef in g["effects"]:
            ef.draw(wsurf)
        for rg in g["rings"]:
            k = 1 - rg[2] / 0.3
            D.circle(wsurf, (255, 255, 255), (int(rg[0]), int(rg[1])), int(8 + 26 * k), 2)
            D.circle(wsurf, (255, 235, 150), (int(rg[0]), int(rg[1])), int(4 + 14 * k), 1)
        rad = push_radius()
        if rad > 0 and 0 <= mouse[0] < GW:
            glow(wsurf, mouse, rad, (255, 255, 255), 30)
            D.circle(wsurf, (255, 255, 255), (int(mouse[0]), int(mouse[1])), rad, 1)
        world.draw_front(wsurf, kind)
        if g["rush"] > 0:                 # час пик: тёплая пульсация по краям
            pr = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 220.0)
            glow(wsurf, (GW // 2, PLAT_TOP + 20), 520, (255, 170, 60), int(30 + 20 * pr))
        wsurf.blit(VIGNETTE, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        if amp:                      # тряска: сдвигаем готовый кадр мира
            canvas.fill((0, 0, 0))
            canvas.blit(wsurf, (px(random.randint(-amp, amp)), px(random.randint(-amp, amp))))

        # ---------- HUD ----------
        money_s = fmt(s["money"])
        mw = int(twidth(f_money, money_s))
        plate(canvas, (10, 6, max(210, 76 + mw), 76), 150, 14)
        glow(canvas, (34, 32), 26, (255, 210, 60), 90)
        D.circle(canvas, (255, 205, 40), (34, 32), 15)
        D.circle(canvas, (200, 150, 20), (34, 32), 15, 3)
        D.circle(canvas, (255, 235, 140), (29, 27), 4)
        text(canvas, "$", f_mid, (160, 110, 10), (28, 21), shadow=False)
        text(canvas, money_s, f_money, (255, 255, 255), (58, 12))
        text(canvas, f"Всего поездок: {fmt(s['kills'])}", f_small, (225, 230, 245), (22, 56), shadow=False)
        # хардкор: секундомер и жизни
        if hard:
            plate(canvas, (252, 6, 252, 76), 150, 14, border=(255, 96, 96, 110))
            text(canvas, "ХАРДКОР", f_small, (255, 120, 110), (264, 12), shadow=False)
            if g["lives"] <= 2 and int(pygame.time.get_ticks() / 250) % 2 == 0:
                glow(canvas, (378, 46), 120, (255, 40, 40), 120)   # мало жизней — пульс
            for i in range(HARD_LIVES):
                draw_heart(canvas, 278 + i * 30, 42, 10, i < g["lives"])
            tt = fmt_time(g["hard_t"])
            text(canvas, tt, f_mid, (255, 255, 255), (490 - twidth(f_mid, tt), 36), shadow=False)
        if g["combo"] > 1:
            cap = 1.5 + 0.5 * lv("combo")
            glow(canvas, (105, 104), 95, (255, 120, 60), 60)   # огненное свечение комбо
            mult = min(1 + 0.1 * g["combo"], cap)
            text(canvas, f"Комбо x{mult:.1f} ({g['combo']})", f_mid, (255, 130, 95), (20, 92))
            bw = int(170 * max(0.0, min(1.0, g["combo_t"] / (6.0 + lv("combot")))))
            D.rect(canvas, (20, 20, 30), (20, 118, 170, 6), border_radius=3)
            D.rect(canvas, (255, 140, 90), (20, 118, bw, 6), border_radius=3)
            nxt = next((m for m in COMBO_MILESTONES if m > g["combo"]), None)
            if nxt:
                text(canvas, f"до премии: {nxt - g['combo']}", f_small, (255, 205, 160), (20, 128),
                     shadow=False)
        if g["train"] and g["train"].gold:
            text(canvas, "ЗОЛОТОЙ ПОЕЗД! x3", f_mid, (255, 215, 60), (20, 150))
        # уровень и прогресс до босса
        plate(canvas, (GW - 296, 6, 288, 84), 150, 14)
        text(canvas, f"Уровень {s['level'] + 1}/{len(THEMES)}: {name}", f_mid, (255, 255, 255), (GW - 286, 12))
        bs = g["boss"]
        if s["won"]:
            text(canvas, f"ХАРДКОР идёт — секундомер {fmt_time(g['hard_t'])}", f_small,
                 (255, 235, 120), (GW - 286, 46))
        elif bs:
            text(canvas, "Босс на платформе!", f_small, (255, 120, 100), (GW - 286, 46))
        else:
            lo = THEMES[s["level"]]["kills"]
            hi = boss_at(s["level"])
            frac = max(0.0, min(1.0, (s["kills"] - lo) / max(1, hi - lo)))
            D.rect(canvas, (20, 20, 30), (GW - 286, 42, 268, 10), border_radius=5)
            if frac > 0:
                fw = max(2, int(268 * frac))
                D.rect(canvas, (230, 110, 90), (GW - 286, 42, fw, 10), border_radius=5)
                D.rect(canvas, (255, 175, 150), (GW - 284, 43, max(1, fw - 4), 3), border_radius=2)
            D.rect(canvas, (255, 255, 255), (GW - 286, 42, 268, 10), 1, border_radius=5)
            left = hi - s["kills"]
            text(canvas, "Босс идёт!" if left <= 0 else f"До босса: {left}", f_small,
                 (255, 255, 255), (GW - 286, 62))
        # активные зелья и события
        ay = 98
        if g["rush"] > 0:
            plate(canvas, (GW - 296, ay - 2, 288, 20), 140, 8, border=(255, 190, 90, 120))
            text(canvas, "ЧАС ПИК x2", f_small, (255, 200, 110), (GW - 288, ay), shadow=False)
            tw = max(0.0, min(1.0, g["rush"] / RUSH_DUR))
            D.rect(canvas, (44, 32, 20), (GW - 200, ay + 5, 110, 7), border_radius=3)
            D.rect(canvas, (255, 180, 80), (GW - 200, ay + 5, int(110 * tw), 7), border_radius=3)
            text(canvas, f"{g['rush']:.0f}с", f_small, (255, 255, 255), (GW - 80, ay), shadow=False)
            ay += 22
        for k, label in FX_LABELS.items():
            if g["fx"][k] > 0:
                plate(canvas, (GW - 296, ay - 2, 288, 20), 130, 8)
                text(canvas, f"{label}", f_small, (150, 250, 165), (GW - 288, ay), shadow=False)
                tw = max(0.0, min(1.0, g["fx"][k] / 45.0))
                D.rect(canvas, (24, 40, 30), (GW - 200, ay + 5, 110, 7), border_radius=3)
                D.rect(canvas, (110, 220, 140), (GW - 200, ay + 5, int(110 * tw), 7), border_radius=3)
                text(canvas, f"{g['fx'][k]:.0f}с", f_small, (255, 255, 255), (GW - 80, ay), shadow=False)
                ay += 22
        if g["acid"] > 0:
            text(canvas, f"КИСЛОТА В ГЛАЗАХ: {g['acid']:.0f}с", f_mid, (165, 255, 95),
                 (GW // 2, H - 56), center=True)
        if bs:
            draw_boss_bar(canvas, bs)
        plate(canvas, (10, H - 34, 700, 26), 120, 10)
        text(canvas, "Тап — столкнуть  |  лови монеты $  |  кнопка справа — пауза",
             f_small, (235, 238, 250), (20, H - 30), shadow=False)
        if g["toast_t"] > 0:
            tw = int(twidth(f_big, g["toast"]))
            ta = min(1.0, g["toast_t"] / 0.4)
            plate(canvas, (GW // 2 - tw // 2 - 28, 138, tw + 56, 66), int(160 * ta), 18,
                  border=(255, 255, 255, int(60 * ta)))
            text(canvas, g["toast"], f_big, g["toast_col"], (GW // 2, 146), center=True)

        draw_mobile_button(canvas, g["paused"])

        draw_panel(canvas, s, mouse, g["tab"])

        # ---------- всё, что летит в камеру, поверх интерфейса ----------
        for a in g["acids"]:
            a.draw(canvas)
        for sk in g["skulls"]:
            sk.draw(canvas)
        if g["acid"] > 0 and g["splats"] is not None:
            g["splats"].set_alpha(min(235, int(235 * min(1.0, g["acid"] / 1.5))))
            canvas.blit(g["splats"], (0, 0))
        # потеря жизни: красная вспышка по всему экрану
        if g["life_flash"] > 0:
            RED_FLASH.set_alpha(int(140 * min(1.0, g["life_flash"])))
            canvas.blit(RED_FLASH, (0, 0))

        # ---------- меню паузы ----------
        if g["paused"]:
            canvas.blit(PAUSE_DIM, (0, 0))
            plate(canvas, (W // 2 - 230, 110, 460, 400), 210, 22, border=(255, 255, 255, 70))
            text(canvas, "ПАУЗА", f_big, (255, 255, 255), (W // 2, 128), center=True)
            armed = pygame.time.get_ticks() < g["confirm_until"]
            labels = [
                "Продолжить",
                "Точно сбросить? Нажми ещё раз" if armed else "Сбросить прогресс",
                "Выйти из игры",
            ]
            for i, r in enumerate(pause_rects()):
                hot = r.collidepoint(mouse)
                if i == 1:
                    base = (150, 40, 44) if armed else (70, 44, 52)
                    edge = (255, 110, 100) if armed else (130, 80, 88)
                else:
                    base = (60, 90, 140) if hot else (44, 52, 82)
                    edge = (140, 165, 230) if hot else (80, 90, 130)
                if hot and i == 1 and not armed:
                    base = (100, 50, 58)
                card(canvas, r, base, edge)
                text(canvas, labels[i], f_mid, (255, 255, 255), (r.centerx, r.y + 15),
                     center=True, shadow=False)
            text(canvas, "Прогресс сохраняется автоматически",
                 f_small, (170, 176, 205), (W // 2, 490), center=True, shadow=False)

        # ---------- вывод на экран с масштабированием ----------
        if not SCALED_OK:
            win.fill((0, 0, 0))
            if (dw, dh) == (WP, HP):
                win.blit(canvas_buf, (ox, oy))
            else:
                win.blit(pygame.transform.smoothscale(canvas_buf, (dw, dh)), (ox, oy))
        pygame.display.flip()


if __name__ == "__main__":
    asyncio.run(main())