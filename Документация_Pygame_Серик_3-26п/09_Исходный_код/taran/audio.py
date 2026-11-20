# -*- coding: utf-8 -*-
"""Звук и музыка «ТАРАН-ЭКСПРЕСС».

Модуль отвечает только за аудио: эффекты из sound/, зацикленные темы маршрута
и тему босса. Он не знает про игровое состояние — game.py создаёт один
экземпляр `SND = SoundKit(base_dir)` и дёргает методы.

Если микшер недоступен (headless-тесты, сервер без звуковой карты) или файлов
нет, игра работает молча: ни один метод не бросает исключение наружу.
"""
import os

import pygame


class SoundKit:
    """Звуковые эффекты и зацикленная музыка из папки sound/.

    Если микшер недоступен (или файлов нет), игра работает молча — звук
    никогда не должен мешать запуску.
    """

    SFX = ("click", "hit", "crit", "coin", "buy", "power", "error", "boss",
           "boom", "life", "levelup", "train", "train_hit", "rush", "whoosh",
           "tap1", "tap2", "tap3")

    # музыкальные темы из sound/music (см. mobile/make_music.py):
    # заставка, три темы маршрута по кругу и отдельная тема босса.
    STATION_PLAYLIST = ("station_1", "station_2", "station_3")
    MUSIC_VOL = 0.34

    def __init__(self, base_dir=None):
        self.ok = False
        self.muted = False
        self.sounds = {}
        self.music_key = None             # что играет сейчас
        self.music_ok = False             # удалось ли хоть раз запустить музыку
        self.station_idx = 0
        self._music_t0 = 0
        self._last = {}
        self.folder = os.path.join(base_dir or os.path.dirname(os.path.abspath(__file__)),
                                   "sound")
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(22050, -16, 2, 512)
            pygame.mixer.set_num_channels(24)
            pygame.mixer.set_reserved(1)      # канал 0 — только музыка, эффекты его не отбирают
            self.ok = True
        except Exception:
            return
        for name in self.SFX:
            try:
                self.sounds[name] = pygame.mixer.Sound(os.path.join(self.folder, name + ".wav"))
            except Exception:
                pass
        # строка видна в консоли браузера и в logcat на телефоне:
        # по ней сразу понятно, загрузился ли звук
        try:
            print(f"[sound] mixer={pygame.mixer.get_init()} "
                  f"effects={len(self.sounds)}/{len(self.SFX)}")
        except Exception:
            pass

    def play(self, name, vol=0.8):
        if not self.ok or self.muted:
            return
        snd = self.sounds.get(name)
        if snd is None:
            return
        try:
            now = pygame.time.get_ticks()
            if now - self._last.get(name, -1000) < 30:      # не душим каналы одинаковыми щелчками
                return
            self._last[name] = now
            ch = snd.play()
            if ch is not None:
                ch.set_volume(max(0.0, min(1.0, vol)))
        except Exception:
            pass

    # ---------- музыка ----------
    def _music_path(self, key):
        path = os.path.join(self.folder, "music", key + ".ogg")
        return path if os.path.exists(path) else None

    def _music_busy(self):
        try:
            return bool(pygame.mixer.music.get_busy())
        except Exception:
            return False

    def play_music(self, key, fade=900):
        """Включает тему key=MUSIC[...]; повторный вызов того же трека ничего не делает.

        Треки длинные (2–3 минуты), поэтому играем их потоком через mixer.music:
        в памяти телефона держится только буфер, а не вся композиция.
        """
        if not self.ok:
            return
        if self.muted:
            self.music_key = key           # включим, когда звук вернут
            return
        if key == self.music_key and self._music_busy():
            return
        path = self._music_path(key)
        if path is None:
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.MUSIC_VOL)
            try:
                pygame.mixer.music.play(loops=0, fade_ms=fade)
            except TypeError:              # старый pygame без fade_ms
                pygame.mixer.music.play(loops=0)
            self.music_key = key
            self.music_ok = True
            self._music_t0 = pygame.time.get_ticks()
            print(f"[music] {key}")
        except Exception as e:
            self.music_ok = False
            print(f"[music] не удалось: {key}: {e}")

    def tick(self):
        """Каждый кадр: доиграл трек — пускаем следующий из плэйлиста маршрута."""
        if not self.ok or self.muted or not self.music_ok:
            return
        if self.music_key not in self.STATION_PLAYLIST:
            return
        if self._music_busy():
            return
        # сразу после play() get_busy() может ещё отдавать False — даём треку время
        try:
            if pygame.time.get_ticks() - self._music_t0 < 4000:
                return
        except Exception:
            return
        self.station_idx = (self.station_idx + 1) % len(self.STATION_PLAYLIST)
        self.play_music(self.STATION_PLAYLIST[self.station_idx], fade=1200)

    def next_station_music(self):
        """Новая станция — следующая тема маршрута."""
        self.station_idx = (self.station_idx + 1) % len(self.STATION_PLAYLIST)
        self.play_music(self.STATION_PLAYLIST[self.station_idx], fade=1200)

    def station_music(self, fade=1200):
        self.play_music(self.STATION_PLAYLIST[self.station_idx], fade=fade)

    def boss_music(self):
        self.play_music("boss", fade=600)

    def start_music(self):
        self.station_music()

    def stop_music(self):
        try:
            pygame.mixer.music.fadeout(250)
        except Exception:
            pass

    def duck(self, on):
        """Приглушить музыку на паузе, чтобы было слышно эффекты."""
        try:
            pygame.mixer.music.set_volume(0.10 if on else self.MUSIC_VOL)
        except Exception:
            pass

    def sync_pause(self, paused):
        """Громкость меняется только при смене состояния, а не каждый кадр."""
        paused = bool(paused)
        if paused != getattr(self, "_paused", False):
            self._paused = paused
            self.duck(paused)

    def set_muted(self, muted):
        self.muted = bool(muted)
        if self.muted:
            self.stop_music()
        else:
            self.play_music(self.music_key or self.STATION_PLAYLIST[0], fade=600)
        return self.muted

    def toggle(self):
        return self.set_muted(not self.muted)
