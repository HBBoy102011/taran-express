# -*- coding: utf-8 -*-
"""Одноразовый помощник: вырезает и увеличивает фрагменты скриншотов."""
import sys
import pygame

pygame.init()


def crop(src, dst, rect, zoom=3):
    img = pygame.image.load(src)
    part = img.subsurface(pygame.Rect(*rect)).copy()
    part = pygame.transform.scale(part, (part.get_width() * zoom, part.get_height() * zoom))
    pygame.image.save(part, dst)
    print(dst, part.get_size())


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "_s_main2.png"
    crop(name, "_crop_tabs.png", (960, 50, 320, 50), 3)
    crop(name, "_crop_hud.png", (680, 0, 280, 96), 3)
    if len(sys.argv) > 2:
        crop(name, "_crop_extra.png", tuple(int(v) for v in sys.argv[2].split(",")), 3)
