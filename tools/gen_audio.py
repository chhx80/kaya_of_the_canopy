#!/usr/bin/env python3
"""Generates every sound in the game — all original, no samples.

A tiny PSG-style synth (square / triangle / noise + envelopes) rendered to
16-bit mono WAVs, which is roughly what an AdLib-era PC would have managed.
Run with tools/genaudio.sh.
"""
import math, os, struct, wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX = os.path.join(ROOT, "assets", "audio", "sfx")
MUSIC = os.path.join(ROOT, "assets", "audio", "music")
for d in (SFX, MUSIC):
    os.makedirs(d, exist_ok=True)

SR = 22050


# ---------------------------------------------------------------- primitives
def midi(n):
    """MIDI note number -> Hz."""
    return 440.0 * (2.0 ** ((n - 69) / 12.0))


NOTES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6,
         "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def note(name):
    """'A4' / 'C#5' -> MIDI number. '-' is a rest."""
    if name in ("-", None):
        return None
    i = 2 if len(name) > 2 and name[1] == "#" else 1
    return NOTES[name[:i]] + 12 * (int(name[i:]) + 1)


def adsr(i, n, a=0.01, d=0.06, s=0.65, r=0.12):
    """Envelope value at sample i of n."""
    t = i / SR
    total = n / SR
    rel_start = max(total - r, 0.0)
    if t < a:
        return t / a if a > 0 else 1.0
    if t < a + d:
        return 1.0 - (1.0 - s) * ((t - a) / d if d > 0 else 1.0)
    if t >= rel_start and r > 0:
        return s * max(0.0, 1.0 - (t - rel_start) / r)
    return s


def square(buf, start, freq, dur, vol=0.25, duty=0.5, env=None, glide=0.0):
    n = int(dur * SR)
    phase = 0.0
    for i in range(n):
        f = freq * (1.0 + glide * i / max(1, n))
        phase += f / SR
        v = vol * (1.0 if (phase % 1.0) < duty else -1.0)
        v *= env(i, n) if env else adsr(i, n)
        j = start + i
        if 0 <= j < len(buf):
            buf[j] += v


def triangle(buf, start, freq, dur, vol=0.25, env=None):
    n = int(dur * SR)
    phase = 0.0
    for i in range(n):
        phase += freq / SR
        p = phase % 1.0
        v = vol * (4.0 * abs(p - 0.5) - 1.0)
        v *= env(i, n) if env else adsr(i, n)
        j = start + i
        if 0 <= j < len(buf):
            buf[j] += v


def noise(buf, start, dur, vol=0.25, env=None, step=1):
    """15-bit LFSR noise, the classic PSG percussion source."""
    n = int(dur * SR)
    reg = 0x7FFF
    held = 0.0
    for i in range(n):
        if i % step == 0:
            bit = ((reg ^ (reg >> 1)) & 1)
            reg = (reg >> 1) | (bit << 14)
            held = 1.0 if (reg & 1) else -1.0
        v = vol * held
        v *= env(i, n) if env else adsr(i, n, 0.001, 0.02, 0.4, 0.05)
        j = start + i
        if 0 <= j < len(buf):
            buf[j] += v


def sweep(buf, start, f0, f1, dur, vol=0.25, duty=0.5, env=None):
    n = int(dur * SR)
    phase = 0.0
    for i in range(n):
        f = f0 + (f1 - f0) * (i / max(1, n))
        phase += f / SR
        v = vol * (1.0 if (phase % 1.0) < duty else -1.0)
        v *= env(i, n) if env else adsr(i, n, 0.002, 0.03, 0.6, 0.06)
        j = start + i
        if 0 <= j < len(buf):
            buf[j] += v


def write(path, buf, fade_edges=True):
    if fade_edges:
        k = min(160, len(buf) // 8)
        for i in range(k):
            buf[i] *= i / k
            buf[-1 - i] *= i / k
    frames = bytearray()
    for v in buf:
        s = int(max(-1.0, min(1.0, v)) * 32000)
        frames += struct.pack("<h", s)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))


def blank(seconds):
    return [0.0] * int(seconds * SR)


# ---------------------------------------------------------------- sfx
def sfx(name, seconds, build):
    buf = blank(seconds)
    build(buf)
    write(os.path.join(SFX, name + ".wav"), buf)


def build_sfx():
    short = lambda i, n: max(0.0, 1.0 - i / n) ** 1.5

    sfx("jump", 0.22, lambda b: sweep(b, 0, 330, 700, 0.18, 0.22, 0.5, short))
    sfx("hop", 0.26, lambda b: sweep(b, 0, 220, 540, 0.22, 0.22, 0.25, short))
    sfx("flap", 0.16, lambda b: noise(b, 0, 0.14, 0.16, short, step=3))
    sfx("land", 0.12, lambda b: noise(b, 0, 0.1, 0.14, short, step=6))

    def _hurt(b):
        sweep(b, 0, 520, 140, 0.3, 0.26, 0.5, short)
        noise(b, 0, 0.12, 0.12, short, step=4)
    sfx("hurt", 0.34, _hurt)

    def _die(b):
        sweep(b, 0, 600, 90, 0.75, 0.28, 0.5, short)
        square(b, int(0.05 * SR), midi(52), 0.6, 0.14, 0.25, short)
    sfx("die", 0.85, _die)

    def _gem(b):
        square(b, 0, midi(88), 0.07, 0.2, 0.5, short)
        square(b, int(0.06 * SR), midi(93), 0.12, 0.2, 0.5, short)
    sfx("gem", 0.22, _gem)

    def _heal(b):
        for k, n in enumerate((72, 76, 79, 84)):
            square(b, int(k * 0.055 * SR), midi(n), 0.11, 0.17, 0.5, short)
    sfx("heal", 0.4, _heal)

    def _key(b):
        for k, n in enumerate((81, 86)):
            triangle(b, int(k * 0.07 * SR), midi(n), 0.16, 0.3, short)
    sfx("key", 0.3, _key)

    def _door(b):
        sweep(b, 0, 160, 90, 0.3, 0.24, 0.5, short)
        noise(b, int(0.06 * SR), 0.22, 0.1, short, step=7)
    sfx("door", 0.4, _door)

    sfx("locked", 0.2, lambda b: square(b, 0, midi(45), 0.16, 0.22, 0.25, short))

    def _switch(b):
        square(b, 0, midi(69), 0.05, 0.2, 0.25, short)
        square(b, int(0.05 * SR), midi(81), 0.1, 0.2, 0.25, short)
    sfx("switch", 0.2, _switch)

    sfx("throw", 0.18, lambda b: sweep(b, 0, 900, 380, 0.15, 0.16, 0.25, short))
    sfx("catch", 0.14, lambda b: sweep(b, 0, 420, 880, 0.1, 0.16, 0.25, short))

    def _crate(b):
        noise(b, 0, 0.22, 0.26, short, step=2)
        sweep(b, 0, 260, 100, 0.16, 0.14, 0.5, short)
    sfx("crate_break", 0.3, _crate)

    def _ehit(b):
        noise(b, 0, 0.08, 0.18, short, step=2)
        square(b, 0, midi(64), 0.07, 0.12, 0.25, short)
    sfx("enemy_hit", 0.16, _ehit)

    def _edie(b):
        sweep(b, 0, 480, 120, 0.26, 0.24, 0.5, short)
        noise(b, 0, 0.2, 0.14, short, step=3)
    sfx("enemy_die", 0.34, _edie)

    sfx("spit", 0.16, lambda b: sweep(b, 0, 700, 260, 0.13, 0.16, 0.125, short))
    sfx("bite", 0.14, lambda b: noise(b, 0, 0.12, 0.2, short, step=2))
    sfx("transform", 0.6, lambda b: [
        square(b, int(k * 0.06 * SR), midi(60 + k * 4), 0.14, 0.15, 0.5, short)
        for k in range(7)])

    sfx("blip", 0.07, lambda b: square(b, 0, midi(84), 0.055, 0.16, 0.5, short))

    def _select(b):
        square(b, 0, midi(76), 0.06, 0.18, 0.5, short)
        square(b, int(0.055 * SR), midi(83), 0.1, 0.18, 0.5, short)
    sfx("select", 0.2, _select)

    sfx("enter", 0.35, lambda b: [
        square(b, int(k * 0.06 * SR), midi(64 + k * 5), 0.12, 0.16, 0.5, short)
        for k in range(4)])

    def _clear(b):
        for k, n in enumerate((72, 76, 79, 84, 88)):
            square(b, int(k * 0.11 * SR), midi(n), 0.24, 0.2, 0.5, short)
        triangle(b, int(0.44 * SR), midi(60), 0.7, 0.24, short)
    sfx("level_clear", 1.1, _clear)

    def _gameover(b):
        for k, n in enumerate((67, 64, 60, 55)):
            square(b, int(k * 0.22 * SR), midi(n), 0.34, 0.22, 0.25, short)
        triangle(b, int(0.88 * SR), midi(43), 0.9, 0.26, short)
    sfx("game_over", 1.9, _gameover)

    sfx("boss_phase", 0.5, lambda b: [
        sweep(b, int(k * 0.12 * SR), 200, 420, 0.16, 0.22, 0.25, short) for k in range(3)])
    sfx("boss_jump", 0.3, lambda b: sweep(b, 0, 180, 420, 0.26, 0.24, 0.25, short))

    def _land_big(b):
        noise(b, 0, 0.35, 0.32, short, step=9)
        sweep(b, 0, 140, 50, 0.3, 0.26, 0.5, short)
    sfx("boss_land", 0.45, _land_big)

    def _bossdie(b):
        for k in range(6):
            noise(b, int(k * 0.13 * SR), 0.3, 0.2, short, step=5 + k)
        sweep(b, 0, 420, 60, 1.1, 0.3, 0.5, short)
    sfx("boss_die", 1.4, _bossdie)


# ---------------------------------------------------------------- music
def render_track(bpm, parts, bars_seconds=None):
    """parts: list of dicts {voice, notes:[(name, beats)], vol, duty, octave}."""
    beat = 60.0 / bpm
    length = 0.0
    for p in parts:
        length = max(length, sum(b for _, b in p["notes"]) * beat)
    buf = blank(length + 0.02)
    for p in parts:
        t = 0.0
        for name, beats in p["notes"]:
            dur = beats * beat
            n = note(name)
            if n is not None:
                n += 12 * p.get("octave", 0)
                start = int(t * SR)
                if p["voice"] == "square":
                    square(buf, start, midi(n), dur * 0.92, p.get("vol", 0.16),
                           p.get("duty", 0.5))
                elif p["voice"] == "triangle":
                    triangle(buf, start, midi(n), dur * 0.96, p.get("vol", 0.2))
                elif p["voice"] == "noise":
                    noise(buf, start, dur * 0.5, p.get("vol", 0.12),
                          step=p.get("step", 4))
            t += dur
    return buf


def build_music():
    # ---- TITLE: slow, wide, a little wistful (A minor)
    lead = ("A4 2, C5 1, E5 1, D5 2, C5 2, B4 2, G4 1, A4 1, E4 4, "
            "F4 2, A4 1, C5 1, B4 2, G4 2, A4 4, - 2")
    bass = ("A2 2, A2 2, F2 2, F2 2, C3 2, C3 2, E2 2, E2 2, "
            "F2 2, F2 2, G2 2, G2 2, A2 4, - 2")
    def parse(s):
        out = []
        for tok in s.split(","):
            tok = tok.strip().split()
            out.append((tok[0], float(tok[1])))
        return out
    write(os.path.join(MUSIC, "title.wav"), render_track(96, [
        {"voice": "square", "notes": parse(lead), "vol": 0.15, "duty": 0.5},
        {"voice": "triangle", "notes": parse(bass), "vol": 0.2},
    ]))

    # ---- HUB: bright, walking pace
    hub_lead = ("E5 1, G5 1, A5 1, G5 1, E5 1, D5 1, E5 2, "
                "C5 1, E5 1, G5 1, E5 1, D5 1, C5 1, D5 2, "
                "E5 1, G5 1, A5 1, B5 1, A5 1, G5 1, E5 2, "
                "D5 1, C5 1, D5 1, E5 1, C5 4")
    hub_bass = ("C3 2, G2 2, A2 2, E2 2, F2 2, C3 2, G2 2, G2 2, "
                "C3 2, G2 2, A2 2, E2 2, F2 2, G2 2, C3 4")
    hub_drum = "C2 1, - 1, C2 1, - 1, " * 8
    write(os.path.join(MUSIC, "hub.wav"), render_track(126, [
        {"voice": "square", "notes": parse(hub_lead), "vol": 0.14, "duty": 0.25},
        {"voice": "triangle", "notes": parse(hub_bass), "vol": 0.2},
        {"voice": "noise", "notes": parse(hub_drum.rstrip(", ")), "vol": 0.05, "step": 6},
    ]))

    # ---- WORLD 1: driving jungle march
    w1_lead = ("A4 0.5, A4 0.5, C5 1, B4 0.5, A4 0.5, G4 1, "
               "A4 0.5, C5 0.5, E5 1, D5 0.5, C5 0.5, B4 1, "
               "A4 0.5, A4 0.5, C5 1, E5 0.5, D5 0.5, C5 1, "
               "B4 0.5, G4 0.5, A4 2")
    w1_bass = ("A2 1, A2 1, E2 1, E2 1, F2 1, F2 1, G2 1, G2 1, "
               "A2 1, A2 1, E2 1, E2 1, F2 1, G2 1, A2 2")
    w1_drum = "C2 0.5, - 0.5, " * 16
    write(os.path.join(MUSIC, "world1.wav"), render_track(138, [
        {"voice": "square", "notes": parse(w1_lead), "vol": 0.14, "duty": 0.25},
        {"voice": "triangle", "notes": parse(w1_bass), "vol": 0.2},
        {"voice": "noise", "notes": parse(w1_drum.rstrip(", ")), "vol": 0.05, "step": 5},
    ]))

    # ---- WORLD 2: cooler, more open (water and sky)
    w2_lead = ("D5 1, F5 1, A5 2, G5 1, F5 1, D5 2, "
               "C5 1, E5 1, G5 2, F5 1, E5 1, C5 2, "
               "D5 1, A4 1, D5 2, F5 4")
    w2_bass = ("D3 2, A2 2, B2 2, F2 2, C3 2, G2 2, A2 2, A2 2, "
               "D3 2, A2 2, D3 4")
    write(os.path.join(MUSIC, "world2.wav"), render_track(112, [
        {"voice": "square", "notes": parse(w2_lead), "vol": 0.13, "duty": 0.125},
        {"voice": "triangle", "notes": parse(w2_bass), "vol": 0.2},
    ]))

    # ---- BOSS: fast, low, relentless
    boss_lead = ("E4 0.5, E4 0.5, G4 0.5, E4 0.5, A#4 0.5, A4 0.5, G4 0.5, E4 0.5, "
                 "E4 0.5, E4 0.5, G4 0.5, A4 0.5, C5 0.5, B4 0.5, A4 0.5, G4 0.5, "
                 "E4 0.5, G4 0.5, B4 0.5, E5 0.5, D5 0.5, B4 0.5, G4 0.5, E4 0.5, "
                 "A4 1, G4 1, E4 2")
    boss_bass = "E2 0.5, E2 0.5, " * 24
    boss_drum = "C2 0.5, - 0.5, " * 24
    write(os.path.join(MUSIC, "boss.wav"), render_track(160, [
        {"voice": "square", "notes": parse(boss_lead), "vol": 0.15, "duty": 0.25},
        {"voice": "triangle", "notes": parse(boss_bass.rstrip(", ")), "vol": 0.22},
        {"voice": "noise", "notes": parse(boss_drum.rstrip(", ")), "vol": 0.05, "step": 4},
    ]))

    # ---- VICTORY: short fanfare that loops gently
    vic_lead = ("C5 0.5, E5 0.5, G5 0.5, C6 1.5, B5 0.5, G5 0.5, A5 2, "
                "F5 0.5, A5 0.5, C6 1, G5 1, E5 1, C5 3")
    vic_bass = ("C3 2, G2 2, A2 2, F2 2, C3 2, G2 2, C3 3")
    write(os.path.join(MUSIC, "victory.wav"), render_track(120, [
        {"voice": "square", "notes": parse(vic_lead), "vol": 0.16, "duty": 0.5},
        {"voice": "triangle", "notes": parse(vic_bass), "vol": 0.2},
    ]))


if __name__ == "__main__":
    build_sfx()
    print("sfx: %d files" % len(os.listdir(SFX)))
    build_music()
    print("music: %d files" % len([f for f in os.listdir(MUSIC) if f.endswith('.wav')]))
