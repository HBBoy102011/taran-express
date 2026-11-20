# -*- coding: utf-8 -*-
"""Рисует логотип и иконки игры «ТАРАН-ЭКСПРЕСС» без внешних картинок.

    py make_logo.py

Результат:
  apk/icon.png             — квадратная иконка для APK (512x512)
  apk/icon_round.png       — круглая иконка для Android 7.1+
  mobile/logo.png          — логотип для экрана загрузки (256x256)
"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
S = 1024                     # рисуем в 2 раза крупнее, потом уменьшаем
SS = S * 2


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def vgrad(size, top, bottom):
    img = Image.new("RGB", (1, size), top)
    px = img.load()
    for y in range(size):
        px[0, y] = lerp(top, bottom, y / max(1, size - 1))
    return img.resize((size, size))


def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return m


def glow_layer(size, shapes, blur, color):
    """shapes — список (x, y, r); возвращает слой со свечением."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x, y, r in shapes:
        d.ellipse((x - r, y - r, x + r, y + r), fill=color)
    return layer.filter(ImageFilter.GaussianBlur(blur))


def draw_logo(size, round_icon=False):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg = vgrad(size, (7, 11, 26), (22, 40, 78)).convert("RGBA")

    # диагональные блики на фоне
    sheen = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen)
    for i in range(-4, 8):
        x = int(size * (i * 0.16))
        sd.polygon([(x, size), (x + int(size * 0.12), 0), (x + int(size * 0.20), 0),
                    (x + int(size * 0.08), size)], fill=(70, 130, 220, 18))
    bg = Image.alpha_composite(bg, sheen)

    # виньетка
    vign = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vign)
    for i in range(26):
        a = int(7 * i)
        vd.ellipse((int(-size * 0.15 + i * size * 0.006), int(-size * 0.1 + i * size * 0.005),
                    size - int(-size * 0.15 + i * size * 0.006), size - int(-size * 0.1 + i * size * 0.005)),
                   outline=(0, 0, 0, min(120, a)), width=max(2, size // 90))
    bg = Image.alpha_composite(bg, vign.filter(ImageFilter.GaussianBlur(size // 110)))

    d = ImageDraw.Draw(bg)

    # ---- скоростные линии ----
    line_col = (90, 220, 255)
    for i, y in enumerate((0.40, 0.48, 0.58, 0.68, 0.76)):
        x0 = int(size * (0.05 + 0.02 * (i % 3)))
        x1 = int(size * (0.26 + 0.07 * (i % 2)))
        a = 90 - abs(i - 2) * 16
        d.rounded_rectangle((x0, int(size * y), x1, int(size * y) + max(6, size // 90)),
                            radius=size // 100, fill=line_col + (max(25, a),))
    for i, y in enumerate((0.36, 0.50, 0.64)):
        x0 = int(size * 0.77)
        x1 = int(size * (0.91 + 0.02 * (i % 2)))
        d.rounded_rectangle((x0, int(size * y), x1, int(size * y) + max(5, size // 110)),
                            radius=size // 110, fill=(255, 205, 90, 55))

    # ---- свечение фар и фартука ----
    bg = Image.alpha_composite(bg, glow_layer(size, [(size * 0.5, size * 0.55, size * 0.30)],
                                              size * 0.045, (70, 210, 255, 60)))
    bg = Image.alpha_composite(bg, glow_layer(size, [(size * 0.5, size * 0.70, size * 0.20)],
                                              size * 0.035, (255, 200, 70, 70)))
    d = ImageDraw.Draw(bg)

    cx = size * 0.5
    # ---- кабина и крыша ----
    cab = (0.355, 0.255, 0.645, 0.455)
    d.rounded_rectangle((int(size * cab[0]), int(size * cab[1]), int(size * cab[2]), int(size * cab[3])),
                        radius=int(size * 0.055), fill=(20, 30, 55, 255),
                        outline=(120, 170, 230, 255), width=max(3, size // 150))
    # лобовое стекло
    d.rounded_rectangle((int(size * 0.385), int(size * 0.285), int(size * 0.615), int(size * 0.425)),
                        radius=int(size * 0.030), fill=(30, 90, 140, 255),
                        outline=(150, 230, 255, 255), width=max(3, size // 180))
    d.polygon([(int(size * 0.40), int(size * 0.300)), (int(size * 0.52), int(size * 0.300)),
               (int(size * 0.43), int(size * 0.410)), (int(size * 0.40), int(size * 0.410))],
              fill=(120, 225, 255, 160))
    d.polygon([(int(size * 0.54), int(size * 0.300)), (int(size * 0.60), int(size * 0.300)),
               (int(size * 0.49), int(size * 0.410)), (int(size * 0.45), int(size * 0.410))],
              fill=(120, 225, 255, 80))

    # ---- труба ----
    d.rounded_rectangle((int(size * 0.455), int(size * 0.175), int(size * 0.545), int(size * 0.285)),
                        radius=int(size * 0.022), fill=(16, 24, 44, 255),
                        outline=(110, 155, 215, 255), width=max(3, size // 180))
    d.rounded_rectangle((int(size * 0.435), int(size * 0.165), int(size * 0.565), int(size * 0.205)),
                        radius=int(size * 0.018), fill=(255, 190, 70, 255),
                        outline=(120, 80, 20, 255), width=max(2, size // 300))

    # ---- корпус ----
    body = (0.285, 0.415, 0.715, 0.665)
    d.rounded_rectangle((int(size * body[0]), int(size * body[1]), int(size * body[2]), int(size * body[3])),
                        radius=int(size * 0.060), fill=(28, 40, 68, 255),
                        outline=(135, 180, 235, 255), width=max(4, size // 130))
    # верхняя золотая полоса
    d.rounded_rectangle((int(size * 0.300), int(size * 0.465), int(size * 0.700), int(size * 0.487)),
                        radius=int(size * 0.010), fill=(255, 196, 76, 255))
    # заклёпки
    for i in range(6):
        x = int(size * (0.315 + i * 0.074))
        d.ellipse((x - size // 110, int(size * 0.520) - size // 110,
                   x + size // 110, int(size * 0.520) + size // 110), fill=(170, 205, 245, 220))
    # центральная фара
    hx, hy, hr = cx, size * 0.555, size * 0.072
    d.ellipse((hx - hr, hy - hr, hx + hr, hy + hr), fill=(255, 235, 160, 255),
              outline=(255, 190, 60, 255), width=max(4, size // 150))
    d.ellipse((hx - hr * 0.58, hy - hr * 0.58, hx + hr * 0.58, hy + hr * 0.58),
              fill=(255, 255, 235, 255))
    d.ellipse((hx - hr * 0.22, hy - hr * 0.25, hx + hr * 0.22, hy + hr * 0.15),
              fill=(255, 255, 255, 255))

    # боковые фары
    for sx in (0.315, 0.685):
        x, y, r = size * sx, size * 0.605, size * 0.030
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 215, 110, 255),
                  outline=(120, 80, 20, 255), width=max(2, size // 320))

    # ---- отвал-таран ----
    plow = [(0.245, 0.665), (0.755, 0.665), (0.835, 0.795), (0.165, 0.795)]
    d.polygon([(int(size * x), int(size * y)) for x, y in plow], fill=(30, 43, 72, 255))
    d.line([(int(size * x), int(size * y)) for x, y in plow] + [(int(size * 0.245), int(size * 0.665))],
           fill=(140, 190, 245, 255), width=max(5, size // 120), joint="curve")
    # золотая кромка отвала
    d.line([(int(size * 0.175), int(size * 0.785)), (int(size * 0.825), int(size * 0.785))],
           fill=(255, 190, 65, 255), width=max(7, size // 85))
    # шевроны на отвале
    for i in range(3):
        x = size * (0.42 + i * 0.08)
        d.polygon([(int(x), int(size * 0.700)), (int(x + size * 0.045), int(size * 0.700)),
                   (int(x + size * 0.010), int(size * 0.770)), (int(x - size * 0.035), int(size * 0.770))],
                  fill=(255, 205, 90, 235))

    # ---- рельсы ----
    rail_y = 0.815
    d.rounded_rectangle((int(size * 0.10), int(size * rail_y), int(size * 0.90), int(size * (rail_y + 0.018))),
                        radius=size // 120, fill=(120, 150, 190, 210))
    d.rounded_rectangle((int(size * 0.14), int(size * (rail_y + 0.035)), int(size * 0.86), int(size * (rail_y + 0.050))),
                        radius=size // 120, fill=(70, 90, 125, 200))
    for i in range(7):
        x = size * (0.16 + i * 0.115)
        d.rounded_rectangle((int(x), int(size * 0.825), int(x + size * 0.028), int(size * 0.868)),
                            radius=size // 200, fill=(55, 65, 88, 230))

    # ---- искры ----
    for (sx, sy, sr, col) in ((0.24, 0.72, 0.011, (255, 220, 120)),
                              (0.76, 0.71, 0.009, (120, 235, 255)),
                              (0.30, 0.80, 0.007, (120, 235, 255)),
                              (0.70, 0.80, 0.012, (255, 220, 120)),
                              (0.21, 0.62, 0.007, (255, 220, 120)),
                              (0.79, 0.61, 0.007, (120, 235, 255))):
        x, y, r = size * sx, size * sy, size * sr
        d.ellipse((x - r, y - r, x + r, y + r), fill=col + (255,))

    # ---- рамка ----
    d.rounded_rectangle((int(size * 0.018), int(size * 0.018), int(size * 0.982), int(size * 0.982)),
                        radius=int(size * 0.115), outline=(255, 196, 76, 235), width=max(5, size // 110))
    d.rounded_rectangle((int(size * 0.038), int(size * 0.038), int(size * 0.962), int(size * 0.962)),
                        radius=int(size * 0.100), outline=(80, 200, 255, 90), width=max(2, size // 300))

    if round_icon:
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out.paste(bg, (0, 0), mask)
        ring = ImageDraw.Draw(out)
        ring.ellipse((int(size * 0.018), int(size * 0.018), int(size * 0.982), int(size * 0.982)),
                     outline=(255, 196, 76, 255), width=max(6, size // 95))
        return out

    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(bg, (0, 0), rounded_mask(size, int(size * 0.115)))
    return out


def main():
    square = draw_logo(SS).resize((512, 512), Image.LANCZOS)
    square.save(os.path.join(HERE, "apk", "icon.png"))

    round_icon = draw_logo(SS, round_icon=True).resize((512, 512), Image.LANCZOS)
    round_icon.save(os.path.join(HERE, "apk", "icon_round.png"))

    logo = square.resize((256, 256), Image.LANCZOS)
    logo.save(os.path.join(HERE, "mobile", "logo.png"))

    print("готово: apk/icon.png, apk/icon_round.png, mobile/logo.png")


if __name__ == "__main__":
    main()
