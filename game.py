import colorsys
import math
import os
import random
import sys

import pygame

import progression as P
import prog_ui as UI
P.bind(sys.modules[__name__])

# статические данные и геометрия живут в отдельном модуле;
# звёздочный импорт сохраняет прежние имена game.W, game.THEMES и т.д.
from taran.config import *  # noqa: E402,F401,F403
from taran.ui.theme import *  # noqa: E402,F401,F403
from taran.audio import SoundKit  # noqa: E402
import taran.assets as ASSETS  # noqa: E402
from taran.assets import (  # noqa: E402,F401
    build_panel_bg, make_acid_overlay, make_cone, make_shadow, make_skull,
    make_vignette,
)

ASSETS.bind(sys.modules[__name__])

import taran.creatures as CREATURES  # noqa: E402
from taran.creatures import creature_surf  # noqa: E402,F401

CREATURES.bind(sys.modules[__name__])

import taran.train as TRAIN  # noqa: E402
from taran.train import Train, TRAIN_CACHE, train_sprite  # noqa: E402,F401

TRAIN.bind(sys.modules[__name__])

import taran.effects as EFFECTS  # noqa: E402
from taran.effects import (  # noqa: E402,F401
    Acid, Coin, Decal, Effect, Particle, SkullFly, TapFX,
)

EFFECTS.bind(sys.modules[__name__])

import taran.world as WORLD  # noqa: E402
from taran.world import World  # noqa: E402

WORLD.bind(sys.modules[__name__])


from taran.logic import (  # noqa: F401  (реэкспорт старых имён game.*)
    boss_at, boss_dmg_scale, cost, inflation, item_buy_rect, item_price,
    new_save, pick_kind, pick_skin, skull_chance, stage_for, tab_items, up_infl,
)
import taran.saves as SAVES  # noqa: E402
from taran.ui.hud import (  # noqa: E402,F401  (реэкспорт для старых вызовов)
    _HEART, draw_boss_bar, draw_heart, draw_mute_button, mute_hit,
)

import taran.ui.shop as SHOP
from taran.ui.shop import (  # noqa: F401  (реэкспорт для тестов и старого кода)
    draw_panel, card, ui_pill, ui_badge, ui_bar, ui_key,
    _PANEL_FRAME, _PULSE, ITEM_COLS, TAB_COLORS,
)
SHOP.bind(sys.modules[__name__])


# В браузере (pygbag/WASM) отрисовка заметно дороже, чем на десктопе:
# этот флаг включает экономные варианты погоды и эффектов.
WEB = sys.platform == "emscripten"
WEB_K = 0.75                 # внутреннее разрешение веб-версии (960×540)

# табличка станции (World.station): реплики прохожих не должны её перекрывать
SIGN_RECT = pygame.Rect(180, 236, 252, 52)
QUOTE_BOXES = []             # облачка, уже нарисованные в текущем кадре
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
# маленький буфер — звук без заметной задержки; 22050 Гц хватает для чиптюна
try:
    # в браузере буфер больше: музыка не захлёбывается, когда кадр подвис
    pygame.mixer.pre_init(22050, -16, 2, 1024 if WEB else 512)
except Exception:
    pass
pygame.init()
pygame.display.set_caption("ТАРАН-ЭКСПРЕСС")
fullscreen = True


# ---------- звук и музыка (см. taran/audio.py) ----------
SND = SoundKit(_BASE_DIR)


def web_boot_done():
    """Сообщает странице загрузки, что игра сейчас покажет первый кадр."""
    try:
        import platform
        platform.window.__gameBootDone()
    except Exception:
        pass


_BACKDROP = {"key": None}


def sync_backdrop(theme):
    """Заливает чёрные поля по бокам продолжением сцены.

    Кадр игры — 16:9, а экран телефона шире (примерно 20:9). Раньше по краям
    оставались чёрные полосы; теперь фон страницы собирается из цветов текущей
    локации (небо, платформа, насыпь), и картинка выглядит цельной.
    Меняется только при переходе на другую станцию.
    """
    if not WEB:
        return
    key = theme.get("name")
    if _BACKDROP["key"] == key:
        return
    _BACKDROP["key"] = key
    try:
        import platform
        css = ("linear-gradient(180deg, rgb{} 0%, rgb{} 54%, rgb{} 56%, "
               "rgb{} 65%, rgb{} 66%, rgb{} 84%, rgb{} 100%)").format(
            tuple(theme["top"]), tuple(theme["bot"]), tuple(theme["plat"]),
            tuple(theme["plat"]), tuple(theme["front"]), tuple(theme["bed"]),
            tuple(theme["bed"]))
        doc = platform.window.document
        doc.documentElement.style.background = css
        doc.body.style.background = css
    except Exception:
        pass

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


def snap(k, lo=1.0):
    return max(lo, min(2.0, int(k * 4) / 4.0))     # шаг 0.25


def scale_fullscreen():
    if WEB:
        # WASM на телефоне не тянет 1280×720 каждый кадр. 0.75 — это 960×540:
        # на экране телефона разницы почти не видно, а рисуется на 44% меньше.
        return WEB_K
    dw, dh = desktop_size()
    return snap(min(dw / W, dh / H))


def scale_windowed():
    if WEB:
        return WEB_K
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


set_scale(FORCE_K or scale_fullscreen())
win = make_window(fullscreen)
fullscreen = bool(win.get_flags() & pygame.FULLSCREEN)
clock = pygame.time.Clock()

FN = "arial,dejavusans,liberationsans"
f_big = f_money = f_mid = f_small = None


def make_fonts():
    global f_big, f_money, f_mid, f_small
    f_big = pygame.font.SysFont(FN, px(46), bold=True)
    f_money = pygame.font.SysFont(FN, px(34), bold=True)
    f_mid = pygame.font.SysFont(FN, px(20), bold=True)
    f_small = pygame.font.SysFont(FN, px(15))


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


_PRESENT = {"size": None, "surf": None}


def present(canvas_buf, win, ox, oy, dw, dh):
    """Вывод кадра в окно без лишних аллокаций.

    При совпадении размеров — прямой blit. Иначе smoothscale пишет в одну
    переиспользуемую поверхность: раньше каждый кадр создавалась новая, и
    сборщик мусора тратил на это заметную часть времени.
    """
    if (dw, dh) == canvas_buf.get_size():
        win.blit(canvas_buf, (ox, oy))
        return
    st = _PRESENT
    if st["surf"] is None or st["size"] != (dw, dh):
        st["surf"] = pygame.Surface((dw, dh))
        try:
            st["surf"] = st["surf"].convert()
        except pygame.error:
            pass
        st["size"] = (dw, dh)
    pygame.transform.smoothscale(canvas_buf, (dw, dh), st["surf"])
    win.blit(st["surf"], (ox, oy))


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
_OFFS = ((0, 0), (1, 0), (2, 0), (0, 1), (2, 1), (0, 2), (1, 2), (2, 2), (1, 3), (2, 3))


def spr_trim():
    """Держит кэш спрайтов в разумных рамках.

    Раньше при переполнении разом удалялось 150 картинок — на следующем кадре
    они строились заново, из-за чего были заметны рывки. Теперь лимит выше
    (на WEB рендер мельче, значит картинки дешевле), а чистим понемногу.
    """
    limit = 1000 if K <= 1.0 else (760 if K <= 1.5 else 560)
    if len(SPR) <= limit:
        return
    for _ in range(80):
        if not SPR:
            break
        SPR.pop(next(iter(SPR)))


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


_TWC = {}                      # ширина строки по (шрифт, текст) — size() дорогой


def twidth(f, s):
    """Ширина строки в логических пикселях (с кэшем: size() зовётся один раз).

    twidth вызывается каждый кадр для облачков, HUD и подписей в панели,
    а Font.size — одна из самых дорогих операций pygame: без кэша на 10 людях
    с репликами уходило ~1,2 мс кадра.
    """
    key = (f, s)
    w = _TWC.get(key)
    if w is None:
        w = f.size(s)[0] / K
        if len(_TWC) > 3000:
            _TWC.clear()
        _TWC[key] = w
    return w


def ellipsize(f, s, maxw):
    """Обрезает строку по ширине и ставит «…», чтобы она не заезжала под кнопку."""
    if maxw <= 0:
        return ""
    if twidth(f, s) <= maxw:
        return s
    while s and twidth(f, s + "…") > maxw:
        s = s[:-1]
    return s.rstrip() + "…"


def fit_font(s, maxw, fonts=None):
    """Самый крупный шрифт из списка, при котором строка влезает в maxw.

    На телефоне экран узкий, и длинные сообщения («Прогресс сброшен —
    начинаем заново!») уезжали за край: вместо обрезки уменьшаем кегль.
    """
    cands = fonts or (f_big, f_money, f_mid, f_small)
    for f in cands:
        if f is not None and twidth(f, s) <= maxw:
            return f
    return cands[-1]


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




def blend(t0, t1, t):
    d = {k: lerp_c(t0[k], t1[k], t) for k in KEYS}
    d["light"] = lerp(t0["light"], t1["light"], t)
    return d


def buy_item(s, i, g):
    if not (0 <= i < len(ITEMS)):
        return
    it = ITEMS[i]
    p = item_price(it, s)
    if s["money"] < p:
        return
    s["money"] -= p
    s["items"][it["key"]] = s["items"].get(it["key"], 0) + 1
    SND.play("buy", 0.8)
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
    SND.play("power", 0.8)
    g["toast"] = msg
    g["toast_col"] = (170, 240, 190)
    g["toast_t"] = 1.8


def load_save():
    """Обёртка: путь к сейву остаётся в game.py (SAVE можно подменить в тестах)."""
    return SAVES.load_save(SAVE)


def write_save(s):
    return SAVES.write_save(s, SAVE)


def buy(s, i, g, times=1):
    """Покупка уровня улучшения. times > 1 — Shift+клик: до 10 уровней сразу."""
    if not (0 <= i < len(UPGRADES)):
        return 0
    u = UPGRADES[i]
    if s["level"] < u["req"]:
        return 0
    n = 0
    for _ in range(max(1, int(times))):
        l = s["levels"][u["key"]]
        if l >= u["max"]:
            break
        c = cost(u, l, up_infl(s))
        if s["money"] < c:
            break
        s["money"] -= c
        s["levels"][u["key"]] += 1
        n += 1
    if n:
        SND.play("buy", 0.75)
        if u["key"] == "helper":
            g["helper_t"] = 0.0
    return n


# ---------- мир (фон, погода, платформа) ----------


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
            # облачко с репликой; табличку станции и соседние облачка не перекрываем
            bw = int(twidth(f_small, self.quote)) + 16
            by = int(y - 160) if self.state == "walk" else int(y - 130)
            bx = max(2, min(GW - bw - 2, x - bw // 2))
            box = pygame.Rect(bx, by, bw, 22)
            if not box.colliderect(SIGN_RECT) and not any(box.colliderect(q) for q in QUOTE_BOXES):
                QUOTE_BOXES.append(box)
                plate(surf, (bx, by, bw, 22), 235, 9, color=(250, 250, 255),
                      border=(40, 40, 60, 200))
                text(surf, self.quote, f_small, (22, 22, 40), (bx + bw // 2, by + 3),
                     center=True, shadow=False)

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
            spr_trim()
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
            if self.kind == "fly":       # крылья: три пера с переливом
                for sgn in (-1, 1):
                    wx = cx + sgn * 9
                    for fi, (ln, up, lift) in enumerate(((29, 14, 0.0), (23, 22, 0.14), (16, 28, 0.26))):
                        tipx = wx + sgn * (ln - fi * 5)
                        tipy = fy - 48 - up - flap
                        pts = [(wx, fy - 56), (tipx, tipy),
                               (tipx - sgn * 7, tipy + 13 + fi * 2), (wx + sgn * 5, fy - 44)]
                        D.polygon(fig, lerp_c((204, 226, 250), (255, 255, 255), lift), pts)
                        D.polygon(fig, (146, 184, 228), pts, 2)
                    D.circle(fig, (198, 220, 246), (wx, fy - 52), 4)
            # плечи, затем корпус
            D.rect(fig, self.color, (cx - 11, fy - 63, 22, 8), border_radius=4)
            D.rect(fig, lerp_c(self.color, (0, 0, 0), 0.22), (cx - 11, fy - 61, 22, 2), border_radius=1)
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
            if not scared:      # ведущий глаз и рот — лицо читается даже крошечным
                eye = lerp_c(self.skin, (0, 0, 0), 0.76)
                D.circle(fig, eye, (cx + 4 * d, fy - 74), 2)
                D.circle(fig, lerp_c(self.skin, (0, 0, 0), 0.34), (cx + 1 * d, fy - 70), 1)
                D.line(fig, lerp_c(self.skin, (0, 0, 0), 0.40),
                       (cx + 2 * d, fy - 66), (cx + 6 * d, fy - 66), 1)
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




class SecretBoss(Boss):
    """Секретный мини-босс: своё чудище на каждом уровне и очень много здоровья."""
    SCALE = 1.0
    secret = True

    def __init__(self, level):
        Boss.__init__(self, level)
        # на дальних станциях секретные боссы повторяются, но становятся злее
        level = min(level, len(SECRET_BOSSES) - 1)
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




# ---------- интерфейс ----------

# палитра живёт в taran/ui/theme.py и импортирована звёздочкой выше:
# game.UI_GOLD, game.UI_LINE и остальные имена работают как раньше




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
    for c in (_TC, _GC, _PC, _HEART, SPR, TRAIN_CACHE, _TWC):
        c.clear()
    _PULSE["key"] = None
    _PRESENT["size"] = None
    _PRESENT["surf"] = None
    _GB[0] = 0
    VIGNETTE = make_vignette()
    LAMP_CONE = make_cone(250, 190, True, 56)
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


# ---------- заставка: оригинальное видео и титры «Режиссёр Айс» ----------
# В самом начале игры (и после полного сброса прогресса) проигрывается
# оригинальное видео с кроликом: кадры лежат в папке intro_frames рядом с игрой,
# в exe они вшиты внутрь. После видео — титры «Режиссёр Айс», и только потом
# начинается основной геймплей. Любой клик или клавиша пропускает всё.
# Если кадров найти не удалось — играет запасная цветная анимация кролика.
INTRO_FPS = 10                       # частота кадров оригинального видео
INTRO_FRAMES_DIR = os.path.join(getattr(sys, "_MEIPASS", _BASE_DIR), "intro_frames")
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


def run_intro():
    """Заставка перед геймплеем: оригинальное видео с кроликом (или запасная
    анимация), затем титры «Режиссёр Айс». Пропуск — любая клавиша или клик."""
    global win, INTRO_FRAME_CACHE
    SND.play("whoosh", 0.5)
    SND.play_music("intro", fade=1200)
    state = {"black": None, "vid_idx": -1, "vid_cur": None}
    fonts = {}

    def rebuild():                        # после смены разрешения шрифты и плёнка создаются заново
        fonts["big"] = pygame.font.SysFont(FN, px(86), bold=True)
        fonts["mid"] = pygame.font.SysFont(FN, px(36), bold=True)
        fonts["sml"] = pygame.font.SysFont(FN, px(16))
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
            txt_a(canvas, "пропустить — любая клавиша или клик", fonts["sml"],
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
            present(canvas_buf, win, ox, oy, dw, dh)
        pygame.display.flip()

    INTRO_FRAME_CACHE = None          # кадры видео не держим в памяти после заставки


def main():
    global win, fullscreen
    web_boot_done()                 # экран загрузки в браузере/APK можно убирать
    run_intro()                     # заставка: видео и титры «Режиссёр Айс»
    s = load_save()
    P.ensure(s)
    off_gain, off_dt = P.catch_up(s)
    SND.set_muted(s.get("muted", False))
    SND.start_music()
    world = World()
    st = s["level"]
    g = dict(people=[], effects=[], particles=[], rings=[], taps=[], train=None, spawn=0.5, next_train=4.0,
             warn=0.0, combo=0, combo_t=0.0, helper_t=0.0, shake=0.0,
             revived=False,
             stage=st, prev=st, trans=1.0, toast="", toast_t=0.0, toast_col=(255, 235, 120),
             banner="", banner_sub="", banner_t=0.0, banner_dur=4.2,
             boss=None, boss_cd=0.0, tab=0, idle=0.0, bot_t=0.0,
             fx={k: 0.0 for k in FX_LABELS}, acid=0.0, splats=None,
             acids=[], skulls=[], decals=[],
             lives=P.start_lives(s), hard_t=0.0, life_flash=0.0,
             coins=[], coin_t=random.uniform(12, 22), rush=0.0, rush_t=random.uniform(45, 75),
             coins_got=0, paused=False, confirm_until=0,
             depot=False, depot_tab=0, depot_confirm=0,
             earn_acc=0.0, rate_t=0.0, rate_show=float(P.ensure(s).get("income_rate", 0.0)),
             autobuy_t=0.0, autopush_t=0.0,
             secret_t=random.uniform(50, 100))
    save_t = 12.0               # реже пишем в localStorage: это заметно на телефоне

    if off_gain > 0:
        hrs = off_dt / 3600.0
        g["toast"] = f"ОФЛАЙН: +${fmt(off_gain)} за {hrs:.1f} ч"
        g["toast_col"] = (255, 224, 120)
        g["toast_t"] = 6.0
    elif P.has_pending_relic(s):
        g["toast"] = "Выберите реликвию в Депо (P)"
        g["toast_col"] = (255, 214, 110)
        g["toast_t"] = 5.0
    elif P.can_rebirth(s):
        g["toast"] = "Перерождение доступно: Депо (P)"
        g["toast_col"] = (255, 214, 110)
        g["toast_t"] = 4.0

    def lv(k):
        return s["levels"][k]

    def scale_boss(b):
        """HP босса умножается на коэффициент от урона за клик и модификатор рейса."""
        f = boss_dmg_scale(lv("smash")) * P.boss_hp_mult(s)
        b.max_hp *= f
        b.hp = b.max_hp

    def earn(n):
        """Весь заработок копится и в s["earned"] — от него считается инфляция."""
        s["money"] += n
        s["earned"] += n
        g["earn_acc"] += n
        P.track(s, "earn", n)

    def lose_lives(xs):
        """Хардкор: каждый ушедший с платформы — минус жизнь; ноль жизней — новый забег."""
        SND.play("life", 0.8)
        for x in xs:
            g["lives"] -= 1
            g["life_flash"] = 0.5
            g["shake"] = max(g["shake"], 0.6)
            g["effects"].append(Effect(max(60, min(GW - 60, x)), PLAT_TOP,
                                       "-1 ЖИЗНЬ", (255, 80, 70)))
            if g["lives"] <= 0:
                # «Второе дыхание» из Депо: раз за рейс забег не сбрасывается
                if not g.get("revived") and P.revive_charges(s) > 0:
                    g["revived"] = True
                    g["lives"] = 1
                    g["life_flash"] = 1.0
                    g["effects"].append(Effect(GW // 2, PLAT_TOP - 40,
                                               "ВТОРОЕ ДЫХАНИЕ!", (150, 230, 255)))
                    g["toast"] = "ВТОРОЕ ДЫХАНИЕ! Жизни восстановлены"
                    g["toast_col"] = (150, 230, 255)
                    g["toast_t"] = 2.5
                    return
                t = g["hard_t"]
                g["lives"] = P.start_lives(s)
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
        m = (1 + 0.15 * lv("mult")) * P.income_mult(s)
        if g["fx"]["p_money"] > 0:
            m *= 2
        if g["rush"] > 0:
            m *= 2
        return m

    def push_radius():
        """Радиус толчка (зелье «Супер-толчок» его удваивает)."""
        r = lv("power") * 35 + P.click_radius_bonus(s)
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
            dmg = P.click_damage(s, bs)
            crit = random.random() < P.crit_chance(s)
            if crit:
                dmg = int(dmg * P.crit_mult(s))
            smash(bs, dmg, mx, my, crit)

    def spawn_slime():
        sb = SlimeBoss(s["level"])
        sb.time_left += 5 * lv("timebonus") + P.boss_time_bonus(s)
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
            SND.play("whoosh", 0.5)
        elif res == "block":
            g["effects"].append(Effect(x, bs.y - 60, "БЛОК!", (120, 190, 255)))
            SND.play("hit", 0.55)
        elif res == "ok":
            dmg = bs.last_dmg
            SND.play("crit" if crit else "hit", 0.85 if crit else 0.65)
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
        SND.play("boom", 0.9)
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
        reward = round(10 * 1.35 ** lv("income") * 12 * income_mult() * P.coin_mult(s))
        earn(reward)
        P.on_coin(s)
        SND.play("coin", 0.85)
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
        return [pygame.Rect(W // 2 - 170, 230 + i * 68, 340, 54) for i in range(4)]

    def reset_progress():
        """Полный сброс: новое сохранение и чистое игровое состояние."""
        fresh = new_save()
        s.clear()
        s.update(fresh)
        for k in ("people", "effects", "particles", "rings", "taps", "acids", "skulls",
                  "decals", "coins"):
            g[k] = []
        g.update(train=None, spawn=0.5, next_train=4.0, warn=0.0, combo=0, combo_t=0.0,
                 revived=False,
                 helper_t=0.0, shake=0.0, stage=0, prev=0, trans=1.0, boss=None, boss_cd=0.0,
                 idle=0.0, bot_t=0.0, acid=0.0, splats=None, lives=HARD_LIVES, hard_t=0.0,
                 life_flash=0.0, rush=0.0, rush_t=random.uniform(45, 75),
                 coin_t=random.uniform(12, 22), coins_got=0, confirm_until=0,
                 banner="", banner_sub="", banner_t=0.0,
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
            SND.play("click", 0.7)
            if i == 0:
                g["paused"] = False
            elif i == 1:
                if set_fullscreen(not fullscreen):
                    after_scale()
            elif i == 2:
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
                    if g["depot"]:
                        g["depot"] = False
                    else:
                        g["paused"] = not g["paused"]
                    g["confirm_until"] = 0
                    SND.play("click", 0.7)
                elif e.key == pygame.K_p:               # P — Депо (мета-прогрессия)
                    g["depot"] = not g["depot"]
                    g["depot_confirm"] = 0
                    SND.play("click", 0.75)
                elif e.key == pygame.K_m:               # M — звук вкл/выкл
                    s["muted"] = SND.toggle()
                    write_save(s)
                elif e.key == pygame.K_F10:         # качество картинки: 1x → 1.5x → 2x
                    change_scale(next((q for q in QUALITY if q > K + 1e-6), QUALITY[0]))
                    after_scale()
                elif g["depot"]:
                    if 0 <= idx < 4:                # 1–4 — вкладки Депо
                        g["depot_tab"] = idx
                        SND.play("click", 0.6)
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
                if g["depot"]:
                    UI.depot_click(s, g, mx, my)
                elif not g["paused"] and UI.depot_hit(mx, my):
                    g["depot"] = True
                    g["depot_confirm"] = 0
                    SND.play("click", 0.75)
                elif globals().get("mobile_btn_hit") and mobile_btn_hit(mx, my):
                    g["paused"] = not g["paused"]
                    g["confirm_until"] = 0
                    SND.play("click", 0.7)
                elif not g["paused"] and mute_hit(mx, my):
                    s["muted"] = SND.toggle()
                    write_save(s)
                elif g["paused"]:
                    pause_click(mx, my)
                elif mx < GW:
                    tap = TapFX(mx, my)
                    g["taps"].append(tap)
                    SND.play(random.choice(("tap1", "tap2", "tap3")), 0.5)
                    coin = next((c for c in g["coins"] if math.hypot(mx - c.x, my - c.y) < 38), None)
                    if coin:
                        tap.color = (255, 226, 120)
                        tap.power = 1.35
                        collect_coin(coin)          # монета ловится вместо толчка
                    else:
                        rad = push_radius()
                        hit_direct = fell = False
                        falls = 0
                        for p in g["people"]:
                            if p.state != "walk":
                                continue
                            direct = p.rect().collidepoint(mx, my)
                            if direct or p.rect().inflate(rad * 2, rad * 2).collidepoint(mx, my):
                                hit_direct = hit_direct or direct
                                if p.push(direct=direct):
                                    fell = True
                                    falls += 1
                        if hit_direct:
                            tap.power = 1.45
                            tap.color = (255, 224, 150)
                        if fell:
                            SND.play("hit", 0.42)
                            P.on_push(s, falls)
                        bs = g["boss"]
                        if bs and bs.state == "fight" and bs.rect().inflate(rad, rad).collidepoint(mx, my):
                            dmg = P.click_damage(s, bs)
                            crit = random.random() < P.crit_chance(s)
                            if crit:
                                dmg = int(dmg * P.crit_mult(s))
                            if smash(bs, dmg, mx, my, crit) == "ok":
                                tap.power = 1.6
                                tap.color = (255, 205, 120) if not crit else (255, 150, 90)
                else:
                    if TAB_Y - 4 <= my < TAB_Y + 34:
                        g["tab"] = max(0, min(len(TAB_NAMES) - 1,
                                              int((mx - (GW + 12)) // TAB_GAP)))
                    else:
                        k = int((my - ROW_Y0) // ROW_H)
                        if g["tab"] == ITEM_TAB:
                            if 0 <= k < len(ITEMS):
                                if item_buy_rect(k).collidepoint(mx, my):
                                    buy_item(s, k, g)
                                else:
                                    use_item(s, k, g)
                        elif 0 <= k < ROWS_PER_TAB:
                            buy(s, g["tab"] * ROWS_PER_TAB + k, g,
                                10 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1)

        if g.get("intro_pending"):
            # после полного сброса прогресса кролик и титры идут заново
            g["intro_pending"] = False
            g["paused"] = False
            run_intro()

        if g["paused"] or g["depot"]:
            dt = 0.0                  # пауза/Депо: время в игре стоит
        # хардкор включается после 10-го уровня и остаётся в новых циклах:
        # маршрут уже знаком, поэтому секундомер и жизни идут с 1-й станции
        hard = bool(s["won"] or P.ensure(s).get("reborn", 0) > 0)
        if hard:
            g["hard_t"] += dt
            P.on_hard_time(s, g["hard_t"])
        g["life_flash"] = max(0.0, g["life_flash"] - dt)

        # оценка дохода для офлайна и HUD (раз в 2 секунды)
        g["rate_t"] += dt
        if g["rate_t"] >= 2.0:
            rate = g["earn_acc"] / max(0.001, g["rate_t"])
            P.set_income_rate(s, rate)
            g["rate_show"] = rate
            g["earn_acc"] = 0.0
            g["rate_t"] = 0.0

        # уведомления из мета-слоя (контракты, достижения, перерождение)
        if g["toast_t"] <= 0:
            msg = P.pop_notice(s)
            if msg:
                g["toast"] = msg
                g["toast_col"] = (255, 224, 120)
                g["toast_t"] = 2.8

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
                g["rush"] = RUSH_DUR * P.rush_scale(s)
                g["rush_t"] = random.uniform(70, 110) / P.rush_scale(s)
                SND.play("rush", 0.8)
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
        flow = (1 + 0.25 * lv("flow")) * P.run_flow_mult(s)
        boosted = g["fx"]["p_flow"] > 0
        if boosted:
            flow *= 2
        if g["rush"] > 0:
            flow *= 2
        # в хардкоре народу в разы больше: и поток чаще, и вместимость выше
        crowd = 4 if hard else 1
        max_people = min(90 if hard else 46,
                         (14 + 2 * lv("cap") + P.capacity_bonus(s))
                         * (2 if (boosted or g["rush"] > 0) else 1)
                         * crowd * P.run_flow_mult(s))
        if g["spawn"] <= 0 and len(g["people"]) < max_people:
            gold = random.random() < 0.04 + 0.03 * lv("gold") + P.gold_chance_bonus(s)
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
                    P.on_push(s)

        # автоматизация из Депо: автотолчок и автозакупка
        ap = P.auto_push_interval(s)
        if ap > 0:
            g["autopush_t"] += dt
            if g["autopush_t"] >= ap:
                g["autopush_t"] = 0.0
                walkers = [p for p in g["people"] if p.state == "walk" and 20 < p.x < GW - 20]
                if walkers:
                    random.choice(walkers).push()
                    P.on_push(s)
                    g["rings"].append([random.choice(walkers).x, PLAT_TOP + 20, 0.3])
        ab = P.auto_buy_interval(s)
        if ab > 0:
            g["autobuy_t"] += dt
            if g["autobuy_t"] >= ab:
                g["autobuy_t"] = 0.0
                idx = P.autobuy_pick(s)
                if idx is not None:
                    buy(s, idx, g)

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
            g["boss"].time_left += 5 * lv("timebonus") + P.boss_time_bonus(s)
            scale_boss(g["boss"])
            SND.play("boss", 0.9)
            SND.boss_music()
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
                    sb.time_left += 5 * lv("timebonus") + P.boss_time_bonus(s)
                    scale_boss(sb)
                    g["boss"] = sb
                    SND.play("boss", 0.8)
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
                reward = round(250 * (bs.level + 1) ** 2 * income_mult() * (4 if bs.secret else 1) * 1.5
                               * P.boss_loot_mult(s))
                earn(reward)
                P.on_boss(s, secret=bs.secret)
                s["kills"] += 8 if bs.secret else 3
                SND.play("levelup", 0.95)
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
                    P.on_station(s)
                    newly = [u["name"] for u in UPGRADES if u["req"] == s["level"]]
                    g["banner"] = f"СТАНЦИЯ {s['level'] + 1}"
                    g["banner_sub"] = THEMES[s["level"]]["name"] + \
                        ("  •  новое улучшение: " + ", ".join(newly) if newly else "")
                    g["banner_t"] = g["banner_dur"] = 4.2
                    SND.next_station_music()      # на каждой станции своя тема маршрута
                    g["toast_t"] = 0.0
                else:
                    s["won"] = True
                    P.on_station(s)
                    g["banner"] = "ФИНАЛ РЕЙСА!"
                    g["banner_sub"] = "20 станций пройдено  •  Депо (P) → Перерождение  •  дальше ХАРДКОР"
                    g["banner_t"] = g["banner_dur"] = 5.5
                    g["toast_t"] = 0.0
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
                    SND.play("train_hit", 0.62)
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
                        P.on_combo(s, g["combo"])
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
        for tf in g["taps"]:
            tf.update(dt)
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
        g["effects"] = [ef for ef in g["effects"] if ef.t > 0][-90 if WEB else -140:]
        g["particles"] = [pt for pt in g["particles"] if pt.life > 0][-280 if WEB else -420:]
        g["rings"] = [rg for rg in g["rings"] if rg[2] > 0]
        g["taps"] = [tf for tf in g["taps"] if tf.t > 0]

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
        g["banner_t"] = max(0.0, g["banner_t"] - dt)
        e_t = g["trans"] * g["trans"] * (3 - 2 * g["trans"])
        if g["trans"] < 1.0:
            e_t = round(e_t * 24) / 24      # 24 шага перехода: слои фона не пересобираются каждый кадр
        col = blend(THEMES[g["prev"]], THEMES[g["stage"]], e_t)
        cur = THEMES[g["stage"]] if g["trans"] > 0.4 else THEMES[g["prev"]]
        kind, name = cur["kind"], cur["name"]
        sync_backdrop(cur)
        world.update(dt, kind)
        # босс ушёл/повержен — возвращаемся к теме маршрута
        if g["boss"] is None and SND.music_key == "boss":
            SND.station_music()
        SND.sync_pause(g["paused"] or g["depot"])
        SND.tick()

        # автосохранение
        save_t -= dt
        if save_t <= 0:
            write_save(s)
            save_t = 12.0

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
        QUOTE_BOXES.clear()
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
        for tf in g["taps"]:
            tf.draw(wsurf)
        for rg in g["rings"]:
            k = 1 - rg[2] / 0.3
            D.circle(wsurf, (255, 255, 255), (int(rg[0]), int(rg[1])), int(8 + 26 * k), 2)
            D.circle(wsurf, (255, 235, 150), (int(rg[0]), int(rg[1])), int(4 + 14 * k), 1)
        rad = push_radius()
        if rad > 0 and 0 <= mouse[0] < GW:
            glow(wsurf, mouse, rad, (255, 255, 255), 30)
            D.circle(wsurf, (255, 255, 255), (int(mouse[0]), int(mouse[1])), rad, 1)
        world.draw_front(wsurf, kind)
        UI.draw_atmosphere(wsurf, col, kind, world.t, g["rush"] > 0)
        if g["rush"] > 0:                 # час пик: тёплая пульсация по краям
            pr = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 220.0)
            glow(wsurf, (GW // 2, PLAT_TOP + 20), 520, (255, 170, 60), int(30 + 20 * pr))
        wsurf.blit(VIGNETTE, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        if amp:                      # тряска: сдвигаем готовый кадр мира
            canvas.fill((0, 0, 0))
            canvas.blit(wsurf, (px(random.randint(-amp, amp)), px(random.randint(-amp, amp))))

        # ---------- HUD 3.0 ----------
        UI.draw_hud(canvas, s, g, mouse, name, hard)
        bs = g["boss"]

        # ---- активные эффекты: компактные чипы слева под HUD ----
        chips = []
        if g["combo"] > 1:
            cap = 1.5 + 0.5 * lv("combo")
            mult = min(1 + 0.1 * g["combo"], cap)
            chips.append((f"СЕРИЯ x{mult:.1f} ({g['combo']})",
                          max(0.0, min(1.0, g["combo_t"] / (6.0 + lv("combot")))),
                          f"{g['combo_t']:.0f}с", (255, 140, 86)))
        if g["rush"] > 0:
            chips.append(("ЧАС ПИК x2",
                          max(0.0, min(1.0, g["rush"] / (RUSH_DUR * P.rush_scale(s)))),
                          f"{g['rush']:.0f}с", (255, 186, 80)))
        for k, label in FX_LABELS.items():
            if g["fx"][k] > 0:
                chips.append((label, max(0.0, min(1.0, g["fx"][k] / 45.0)),
                              f"{g['fx'][k]:.0f}с", (116, 226, 148)))
        if g["train"] and g["train"].gold:
            chips.append(("ЗОЛОТОЙ ПОЕЗД x3", 1.0, "", (255, 214, 70)))
        if g["acid"] > 0:
            chips.append(("КИСЛОТА", max(0.0, min(1.0, g["acid"] / 5.0)),
                          f"{g['acid']:.0f}с", (160, 246, 100)))
        cy = 98
        for label, ratio, tm, col in chips[:5]:
            w = int(twidth(f_small, label) + twidth(f_small, tm) + 32)
            w = max(172, min(238, w))
            plate(canvas, (12, cy, w, 25), 150, 8, border=(col[0], col[1], col[2], 120))
            D.rect(canvas, col, (18, cy + 9, 4, 7), border_radius=2)
            text(canvas, label, f_small, col, (27, cy + 2), shadow=False)
            if tm:
                text(canvas, tm, f_small, (235, 240, 250),
                     (w + 1 - twidth(f_small, tm), cy + 2), shadow=False)
            D.rect(canvas, (26, 28, 40), (27, cy + 19, w - 31, 3), border_radius=2)
            D.rect(canvas, col, (27, cy + 19, int((w - 31) * ratio), 3), border_radius=2)
            cy += 28

        if g["acid"] > 0:
            text(canvas, f"КИСЛОТА В ГЛАЗАХ: {g['acid']:.0f}с", f_mid, (165, 255, 95),
                 (GW // 2, H - 56), center=True)
        if bs:
            draw_boss_bar(canvas, bs)
        hint = "Клик — столкнуть  ·  монеты $  ·  P — Депо  ·  Esc — пауза  ·  F11 — экран"
        plate(canvas, (10, H - 34, min(GW - 20, int(twidth(f_small, hint)) + 26), 26),
              150, 10, border=(60, 68, 92, 110))
        text(canvas, hint, f_small, (196, 206, 232), (20, H - 30), shadow=False)

        # ---- баннер новой станции ----
        if g["banner_t"] > 0:
            bdur = g.get("banner_dur", 4.2)
            age = max(0.0, bdur - g["banner_t"])
            a = max(0.0, min(1.0, age / 0.25, g["banner_t"] / 0.55))
            dy = int((1.0 - min(1.0, age / 0.35)) * 26)
            fb = fit_font(g["banner"], GW - 150)
            bw = max(360, int(twidth(fb, g["banner"])) + 92)
            by = 178 + dy
            plate(canvas, (GW // 2 - bw // 2, by, bw, 92), int(205 * a), 18,
                  border=(255, 210, 120, int(150 * a)))
            D.rect(canvas, (255, 206, 96), (GW // 2 - bw // 2 + 18, by + 10, bw - 36, 2),
                   border_radius=1)
            text(canvas, g["banner"], fb, (255, 244, 214), (GW // 2, by + (92 - fb.get_height() / K) / 2),
                 center=True)
            sub = g["banner_sub"]
            if sub:
                text(canvas, sub, fit_font(sub, GW - 120, (f_mid, f_small)), (255, 214, 150),
                     (GW // 2, by + 66), center=True, shadow=False)
        # ---- компактный тост сверху: не перекрывает сцену и не спорит с баннером ----
        if g["toast_t"] > 0:
            maxw = GW - 160
            ft = fit_font(g["toast"], maxw, (f_mid, f_small))
            msg = g["toast"]
            if twidth(ft, msg) > maxw:
                msg = ellipsize(ft, msg, maxw)
            tw = int(twidth(ft, msg))
            ta = min(1.0, g["toast_t"] / 0.4)
            pl = pygame.Rect(GW // 2 - tw // 2 - 24, 104, tw + 48, 38)
            plate(canvas, pl, int(195 * ta), 12,
                  border=(255, 255, 255, int(65 * ta)))
            D.rect(canvas, g["toast_col"], (pl.x + 8, pl.y + 9, 4, pl.h - 18),
                   border_radius=2)
            th = ft.get_height() / K
            text(canvas, msg, ft, g["toast_col"],
                 (GW // 2, pl.y + (pl.h - th) / 2), center=True)

        draw_panel(canvas, s, mouse, g["tab"])
        draw_mute_button(canvas, SND.muted, mute_hit(mouse[0], mouse[1]))

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

        # ---------- Депо: постоянное наследие ----------
        if g["depot"]:
            UI.draw_depot(canvas, s, g, mouse)

        # ---------- меню паузы ----------
        if g["paused"]:
            canvas.blit(PAUSE_DIM, (0, 0))
            plate(canvas, (W // 2 - 270, 96, 540, 430), 218, 24,
                  border=(150, 175, 230, 90))
            D.rect(canvas, (66, 104, 190), (W // 2 - 246, 108, 492, 2), border_radius=1)
            text(canvas, "ПАУЗА", f_big, (255, 255, 255), (W // 2, 116), center=True)
            text(canvas, f"СТАНЦИЯ {s['level'] + 1} / {len(THEMES)}   •   {name}",
                 f_mid, (152, 196, 255), (W // 2, 166), center=True, shadow=False)
            # короткая сводка прогресса
            stat_y = 192
            D.rect(canvas, (26, 30, 46), (W // 2 - 220, stat_y, 440, 26), border_radius=9)
            D.rect(canvas, (54, 62, 90), (W // 2 - 220, stat_y, 440, 26), 1, border_radius=9)
            text(canvas, f"Баланс ${fmt(s['money'])}", f_small, (255, 224, 120),
                 (W // 2 - 202, stat_y + 5), shadow=False)
            text(canvas, f"Поездок {fmt(s['kills'])}", f_small, (214, 222, 244),
                 (W // 2 - 34, stat_y + 5), shadow=False)
            text(canvas, f"Станций {s['level'] + 1}/{len(THEMES)}", f_small,
                 (214, 222, 244), (W // 2 + 128, stat_y + 5), shadow=False)
            armed = pygame.time.get_ticks() < g["confirm_until"]
            labels = [
                "Продолжить  (Esc)",
                f"Полный экран: {'вкл' if fullscreen else 'выкл'}  (F11)",
                "Точно сбросить? Нажми ещё раз" if armed else "Сбросить прогресс",
                "Выйти из игры",
            ]
            for i, r in enumerate(pause_rects()):
                hot = r.collidepoint(mouse)
                if i == 2:
                    base = (150, 40, 44) if armed else (70, 44, 52)
                    edge = (255, 110, 100) if armed else (130, 80, 88)
                else:
                    base = (60, 90, 140) if hot else (44, 52, 82)
                    edge = (140, 165, 230) if hot else (80, 90, 130)
                if hot and i == 2 and not armed:
                    base = (100, 50, 58)
                card(canvas, r, base, edge, edge)
                # номер пункта слева и стрелка справа — без привязки к смыслу кнопки
                D.circle(canvas, lerp_c(base, (255, 255, 255), 0.16),
                         (r.x + 28, r.centery), 15)
                D.circle(canvas, edge, (r.x + 28, r.centery), 15, 1)
                text(canvas, str(i + 1), f_small, (240, 246, 255),
                     (r.x + 21, r.centery - 8), shadow=False)
                text(canvas, labels[i], f_mid, (255, 255, 255), (r.centerx, r.y + 15),
                     center=True, shadow=False)
                D.line(canvas, edge, (r.right - 30, r.centery),
                       (r.right - 22, r.centery), 2)
                D.line(canvas, edge, (r.right - 26, r.centery - 4),
                       (r.right - 22, r.centery), 2)
                D.line(canvas, edge, (r.right - 26, r.centery + 4),
                       (r.right - 22, r.centery), 2)
            text(canvas, f"Качество: x{K:g} (F10)   •   прогресс сохраняется автоматически",
                 f_small, (170, 176, 205), (W // 2, 490), center=True, shadow=False)

        # ---------- вывод на экран с масштабированием ----------
        if not SCALED_OK:
            win.fill((0, 0, 0))
            present(canvas_buf, win, ox, oy, dw, dh)
        pygame.display.flip()


if __name__ == "__main__":
    main()