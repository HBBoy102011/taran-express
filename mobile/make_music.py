# -*- coding: utf-8 -*-
"""Готовит музыку игры из присланных mp3 в music_src/ -> sound/music/*.ogg.

Зачем конвертация:
  * pygbag/SDL_mixer в WASM надёжно читает OGG Vorbis, а mp3-треки по 4–5 МБ
    весили бы в APK в два раза больше нужного;
  * прогон через loudnorm выравнивает громкость: иначе один трек орёт,
    а другой еле слышно.

Запуск (нужен ffmpeg: либо в PATH, либо пакет imageio-ffmpeg):
    py mobile/make_music.py
Результат лежит в sound/music/ и попадает в веб-сборку/APK как обычный ассет.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "music_src")
DST = os.path.join(ROOT, "sound", "music")

# ключ в игре -> файл-исходник
TRACKS = {
    "intro": "untitled-variant-2.mp3",            # заставка: спокойный, воздушный
    "station_1": "gen_267_v2_ich4xwkfbzgr8.mp3",  # будни экспресса
    "station_2": "gen_271_v2_ioj8sl7cajqhm.mp3",  # вторая тема маршрута
    "station_3": "gen_265_yjfz47c3onjtr.mp3",     # низкая, «ночной экспресс»
    "boss": "gen_279_yp9lteu1onfsu.mp3",          # босс: самый быстрый трек
}

# -16 LUFS — уровень, на котором музыка не перекрывает эффекты.
# 2 канала 44100: сжатие Vorbis q2 даёт ~1.5–2 МБ на трёхминутный трек.
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"


def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def main():
    ff = find_ffmpeg()
    if not ff:
        sys.exit("нет ffmpeg: положи его в PATH или установи imageio-ffmpeg")
    os.makedirs(DST, exist_ok=True)
    total = 0
    for key, name in TRACKS.items():
        src = os.path.join(SRC, name)
        if not os.path.exists(src):
            sys.exit(f"нет исходника: {src}")
        out = os.path.join(DST, key + ".ogg")
        cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-i", src,
               "-af", LOUDNORM, "-ac", "2", "-ar", "44100",
               "-c:a", "libvorbis", "-q:a", "2", out]
        r = subprocess.run(cmd)
        if r.returncode != 0:
            sys.exit(f"ffmpeg не смог собрать {key}")
        size = os.path.getsize(out)
        total += size
        print(f"{key:10s} {name:38s} {size / 1024 / 1024:5.2f} МБ")
    print(f"итого: {total / 1024 / 1024:.2f} МБ в {DST}")


if __name__ == "__main__":
    main()
