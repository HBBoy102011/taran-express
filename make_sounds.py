# -*- coding: utf-8 -*-
"""Генерирует звук и музыку для игры без внешних файлов.

Все эффекты и музыкальный трек синтезируются из синусов, меандров и шума,
поэтому в репозитории не нужны лицензионные аудиофайлы: достаточно запустить

    py make_sounds.py

Скрипт кладёт WAV-файлы в sound/ (десктоп) и mobile/sound/ (веб-сборка).
Музыка — зацикленный чиптюн на 16 тактов (126 BPM, ~30 с) с бесшовным стыком.
"""
import os
import shutil
import wave

import numpy as np

SR = 22050
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = [os.path.join(HERE, "sound"), os.path.join(HERE, "mobile", "sound")]

rng = np.random.default_rng(20261101)


def t_axis(dur):
    return np.arange(int(SR * dur), dtype=np.float64) / SR


def note(midi):
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def sine(f, t):
    return np.sin(2 * np.pi * f * t)


def square(f, t, duty=0.5):
    return np.where((t * f) % 1.0 < duty, 1.0, -1.0)


def saw(f, t):
    return 2.0 * ((t * f) % 1.0) - 1.0


def tri(f, t):
    return 2.0 * np.abs(2.0 * ((t * f) % 1.0) - 1.0) - 1.0


def noise(dur):
    return noise_n(int(SR * dur))


def noise_n(n):
    return rng.uniform(-1.0, 1.0, n)


def lowpass(x, k):
    if k <= 1:
        return x
    return np.convolve(x, np.ones(k, dtype=np.float64) / k, mode="same")


def env(n, attack=0.004, decay=0.2, curve=3.0, sustain=0.0):
    """Р‘С‹СЃС‚СЂР°СЏ Р°С‚Р°РєР° Рё СЌРєСЃРїРѕРЅРµРЅС†РёР°Р»СЊРЅС‹Р№ СЃРїР°Рґ (РІ СЃРµРєСѓРЅРґР°С…)."""
    t = np.arange(n) / SR
    a = max(1, int(attack * SR))
    e = np.empty(n, dtype=np.float64)
    e[:a] = np.linspace(0.0, 1.0, a)
    d = np.maximum(1, n - a)
    e[a:] = (1.0 - sustain) * np.exp(-curve * np.arange(d) / d) + sustain
    return e


def mix_at(dst, src, at, gain=1.0, pan=0.0):
    """РљР»Р°РґС‘С‚ РјРѕРЅРѕ-СЃРёРіРЅР°Р» РІ СЃС‚РµСЂРµРѕ-Р±СѓС„РµСЂ СЃ РїР°РЅРѕСЂР°РјРѕР№ -1..1."""
    i = max(0, int(at * SR))
    j = min(len(dst), i + len(src))
    if j <= i:
        return
    seg = src[: j - i] * gain
    left = np.sqrt(0.5 * (1.0 - pan))
    right = np.sqrt(0.5 * (1.0 + pan))
    dst[i:j, 0] += seg * left
    dst[i:j, 1] += seg * right


def save_wav(name, stereo, peak=0.92):
    stereo = np.asarray(stereo, dtype=np.float64)
    m = float(np.max(np.abs(stereo))) or 1.0
    stereo = stereo / m * peak
    pcm = np.clip(stereo, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype("<i2")
    for folder in OUT:
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, name + ".wav")
        with wave.open(path, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
    print("  ", name + ".wav", f"{len(pcm) * 4 / 1024:.0f} РљР‘")


def sfx(name, dur, fn):
    """fn(t) -> РјРѕРЅРѕ-СЃРёРіРЅР°Р»; СЃРѕС…СЂР°РЅСЏРµРј РєР°Рє СЃС‚РµСЂРµРѕ СЃ Р»С‘РіРєРёРј СЃС‚РµСЂРµРѕ-СЌС„С„РµРєС‚РѕРј."""
    t = t_axis(dur)
    x = fn(t)
    st = np.stack([x, np.roll(x, 24)], axis=1)
    save_wav(name, st)


def build_sfx():
    print("СЌС„С„РµРєС‚С‹:")

    # РєР»РёРє РїРѕ РёРЅС‚РµСЂС„РµР№СЃСѓ: РєРѕСЂРѕС‚РєРёР№ СЃСѓС…РѕР№ С‰РµР»С‡РѕРє
    def _click(t):
        f = 1250 * np.exp(-t * 14) + 420
        x = square(1, t, 0.35) * 0 + sine(f, t) * 0.55
        x += lowpass(noise_n(len(t)), 3)[: len(t)] * np.exp(-t * 90) * 0.5
        return x * env(len(t), 0.001, 0.05)

    sfx("click", 0.09, _click)

    # СѓРґР°СЂ РїРѕ РїСЂРѕС…РѕР¶РµРјСѓ / Р±РѕСЃСЃСѓ
    def _hit(t):
        f = 190 * np.exp(-t * 9) + 62
        x = sine(f, t) * 0.9 + saw(f * 0.5, t) * 0.25
        n = lowpass(noise_n(len(t)), 8)[: len(t)]
        x += n * np.exp(-t * 45) * 0.85
        return np.tanh(x * 1.7) * env(len(t), 0.002, 0.12)

    sfx("hit", 0.16, _hit)

    # РєСЂРёС‚РёС‡РµСЃРєРёР№ СѓРґР°СЂ: С‚РѕС‚ Р¶Рµ СѓРґР°СЂ + Р·РІРѕРЅРєРёР№ РїСЂРёР·РІСѓРє
    def _crit(t):
        f = 220 * np.exp(-t * 8) + 70
        x = sine(f, t) * 0.8 + sine(1760, t) * 0.35 * np.exp(-t * 12)
        n = lowpass(noise_n(len(t)), 6)[: len(t)]
        x += n * np.exp(-t * 40) * 0.8
        return np.tanh(x * 1.8) * env(len(t), 0.002, 0.2)

    sfx("crit", 0.26, _crit)

    # РјРѕРЅРµС‚Р°: РІРѕСЃС…РѕРґСЏС‰РµРµ Р°СЂРїРµРґР¶РёРѕ
    def _coin(t):
        out = np.zeros_like(t)
        for i, m in enumerate((84, 88, 91, 96)):
            at = i * 0.045
            mask = t >= at
            tt = t[mask] - at
            out[mask] += sine(note(m), tt) * np.exp(-tt * 11) * 0.42
        return out

    sfx("coin", 0.42, _coin)

    # РїРѕРєСѓРїРєР°: РјСЏРіРєР°СЏ РІРѕСЃС…РѕРґСЏС‰Р°СЏ С‚РµСЂС†РёСЏ
    def _buy(t):
        out = np.zeros_like(t)
        for i, m in enumerate((72, 76, 79, 84)):
            at = i * 0.055
            mask = t >= at
            tt = t[mask] - at
            out[mask] += (square(note(m), tt, 0.35) * 0.16 + sine(note(m), tt) * 0.28) * np.exp(-tt * 8)
        return out

    sfx("buy", 0.38, _buy)

    # Р·РµР»СЊРµ / СѓСЃРёР»РµРЅРёРµ: РІРѕСЃС…РѕРґСЏС‰РёР№ СЃРІРёРї
    def _power(t):
        f = 260 + 1400 * (t / max(t[-1], 1e-6)) ** 1.5
        x = sine(f, t) * 0.45 + tri(f * 0.5, t) * 0.18
        x += noise_n(len(t)) * np.exp(-t * 8) * 0.12
        return x * env(len(t), 0.01, max(t[-1], 0.1))

    sfx("power", 0.55, _power)

    # РѕС€РёР±РєР° / РЅРµС‚ РґРµРЅРµРі
    def _error(t):
        out = np.zeros_like(t)
        for i, m in enumerate((55, 49)):
            at = i * 0.11
            mask = t >= at
            tt = t[mask] - at
            out[mask] += square(note(m), tt, 0.45) * 0.32 * np.exp(-tt * 10)
        return out

    sfx("error", 0.34, _error)

    # РїРѕСЏРІР»РµРЅРёРµ Р±РѕСЃСЃР°: РЅРёР·РєРёР№ С‚СЂРµРІРѕР¶РЅС‹Р№ РіРѕСЂРЅ
    def _boss(t):
        vib = 1.0 + 0.012 * np.sin(2 * np.pi * 5 * t)
        x = saw(78 * vib, t) * 0.4 + square(117 * vib, t, 0.3) * 0.22
        x += sine(39, t) * 0.4
        x += lowpass(noise_n(len(t)), 24) * np.exp(-t * 4) * 0.25
        return np.tanh(x * 1.4) * env(len(t), 0.02, max(t[-1], 0.1), 1.2)

    sfx("boss", 0.95, _boss)

    # РІР·СЂС‹РІ
    def _boom(t):
        n = lowpass(noise_n(len(t)), 5)[: len(t)]
        x = n * np.exp(-t * 7) * 1.2
        x += sine(58 * np.exp(-t * 2), t) * np.exp(-t * 5) * 0.8
        return np.tanh(x * 1.3)

    sfx("boom", 0.75, _boom)

    # РїРѕС‚РµСЂСЏ Р¶РёР·РЅРё: РїР°РґР°СЋС‰Р°СЏ РЅРѕС‚Р°
    def _life(t):
        f = 440 * np.exp(-t * 1.8) + 70
        x = tri(f, t) * 0.4 + sine(f, t) * 0.3
        return np.tanh(x * 1.2) * env(len(t), 0.005, max(t[-1], 0.1), 2.0)

    sfx("life", 0.6, _life)

    # РїРѕР±РµРґР° / РЅРѕРІС‹Р№ СѓСЂРѕРІРµРЅСЊ: РєРѕСЂРѕС‚РєР°СЏ С„Р°РЅС„Р°СЂР°
    def _levelup(t):
        out = np.zeros_like(t)
        for i, m in enumerate((72, 76, 79, 84, 88, 91)):
            at = i * 0.075
            mask = t >= at
            tt = t[mask] - at
            x = square(note(m), tt, 0.4) * 0.16 + sine(note(m), tt) * 0.26
            out[mask] += x * np.exp(-tt * 7)
        return out

    sfx("levelup", 0.95, _levelup)

    # РіСѓРґРѕРє РїРѕРµР·РґР° В«С‚Сѓ-С‚СѓСѓВ»
    def _train(t):
        out = np.zeros_like(t)
        for i, m in enumerate((57, 57)):
            at = i * 0.28
            mask = t >= at
            tt = t[mask] - at
            dur = 0.42
            e = np.where(tt < dur, np.minimum(1.0, tt / 0.03) * np.minimum(1.0, (dur - tt) / 0.06), 0.0)
            vib = 1.0 + 0.018 * np.sin(2 * np.pi * 6 * tt)
            x = saw(note(m) * vib, tt) * 0.34 + square(note(m) * 2 * vib, tt, 0.3) * 0.1
            out[mask] += np.clip(x * e, -0.9, 0.9)
        return out

    sfx("train", 0.95, _train)

    # СѓРґР°СЂ РїРѕРµР·РґР° РїРѕ РїСЂРѕС…РѕР¶РµРјСѓ
    def _train_hit(t):
        n = lowpass(noise_n(len(t)), 4)[: len(t)]
        x = n * np.exp(-t * 30) * 0.8 + sine(105, t) * np.exp(-t * 16) * 0.7
        x += sine(1480, t) * np.exp(-t * 22) * 0.18
        return np.tanh(x * 1.5)

    sfx("train_hit", 0.24, _train_hit)

    # С‡Р°СЃ РїРёРє: Р±РѕРґСЂС‹Р№ РїРµСЂРµР·РІРѕРЅ
    def _rush(t):
        out = np.zeros_like(t)
        for i, m in enumerate((69, 72, 76, 81, 84)):
            at = i * 0.07
            mask = t >= at
            tt = t[mask] - at
            out[mask] += (sine(note(m), tt) * 0.3 + square(note(m), tt, 0.3) * 0.1) * np.exp(-tt * 6)
        return out

    sfx("rush", 0.7, _rush)

    # РєРѕСЂРѕС‚РєРёР№ СЃРІРёСЃС‚ РїСЂРё СЃС‚Р°СЂС‚Рµ Р·Р°СЃС‚Р°РІРєРё
    def _whoosh(t):
        n = noise_n(len(t))
        x = lowpass(n, 40) * np.sin(np.pi * t / max(t[-1], 1e-6)) ** 2
        return x * 0.8

    sfx("whoosh", 0.55, _whoosh)


    # --- тап по толпе: три мягких «ток»-звука, чтобы серия кликов не звучала одинаково ---
    def _tap(name, hi, lo, dec, namp, harm, dur):
        def fn(t):
            f = lo + (hi - lo) * np.exp(-t * dec * 1.15)
            x = sine(f, t) * np.exp(-t * dec) * 0.78
            x += sine(f * 2.01, t) * np.exp(-t * dec * 1.7) * harm
            x += sine(lo * 0.5, t) * np.exp(-t * dec * 0.65) * 0.22
            x += lowpass(noise_n(len(t)), 2)[: len(t)] * np.exp(-t * 190) * namp
            return np.tanh(x * 1.25) * env(len(t), 0.0008, dur, 2.4)

        sfx(name, dur, fn)

    _tap("tap1", 920, 300, 52, 0.42, 0.16, 0.10)      # звонкий щелчок
    _tap("tap2", 1240, 430, 66, 0.36, 0.20, 0.085)    # повыше и короче
    _tap("tap3", 620, 205, 38, 0.30, 0.11, 0.12)      # мягкий «тук»


def add_note(dst, midi, at, dur, gain=1.0, kind="square", pan=0.0, duty=0.5,
             attack=0.005, decay=2.4):
    t = t_axis(dur)
    if kind == "square":
        x = square(note(midi), t, duty)
    elif kind == "tri":
        x = tri(note(midi), t)
    elif kind == "saw":
        x = saw(note(midi), t)
    else:
        x = sine(note(midi), t)
    e = env(len(t), attack, dur, decay)
    mix_at(dst, np.tanh(x * 1.15) * e, at, gain, pan)


if __name__ == "__main__":
    build_sfx()
    print("РіРѕС‚РѕРІРѕ:", ", ".join(OUT))

