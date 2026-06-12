"""Synthesize a 30s hype track: 128 BPM, 16 bars, A minor.

Structure:
  bars 1-2   intro: filtered pads + riser + building kicks
  bar  3     DROP (stats card slams in)
  bars 3-14  full groove: 4-on-floor, bass, arps, claps
  bar  15    riser + ominous low drone (lathrys card)
  bar  16    final hit + outro tail
Output: music.wav (stereo 44.1k)
"""
import numpy as np
from scipy import signal
import wave

SR = 44100
BPM = 128.0
BEAT = 60.0 / BPM            # 0.46875 s
BAR = BEAT * 4               # 1.875 s
TOTAL = BAR * 16             # 30.0 s
N = int(SR * TOTAL)

rng = np.random.default_rng(20260612)


def t_axis(dur):
    return np.arange(int(SR * dur)) / SR


def place(buf, start_s, snd, gain=1.0):
    i = int(start_s * SR)
    if i >= len(buf):
        return
    seg = snd[: len(buf) - i] * gain
    buf[i:i + len(seg)] += seg


def lowpass(x, fc, order=4):
    sos = signal.butter(order, fc / (SR / 2), "low", output="sos")
    return signal.sosfilt(sos, x)


def highpass(x, fc, order=4):
    sos = signal.butter(order, fc / (SR / 2), "high", output="sos")
    return signal.sosfilt(sos, x)


def bandpass(x, lo, hi, order=2):
    sos = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], "band", output="sos")
    return signal.sosfilt(sos, x)


# ---------- drum sounds ----------
def kick():
    t = t_axis(0.35)
    f = 150 * np.exp(-t * 22) + 44
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 11)
    click = highpass(rng.standard_normal(len(t)) * np.exp(-t * 250), 3000)
    return body * 1.0 + click * 0.4


def clap():
    t = t_axis(0.30)
    n = rng.standard_normal(len(t))
    env = np.zeros(len(t))
    for d, g in [(0.0, 1.0), (0.012, 0.8), (0.025, 0.65)]:
        i = int(d * SR)
        env[i:] += g * np.exp(-(t[: len(t) - i]) * 38)
    env += 0.5 * np.exp(-t * 9)  # tail
    return bandpass(n * env, 900, 7500) * 1.4


def hat(open_=False):
    dur = 0.18 if open_ else 0.055
    t = t_axis(dur)
    n = rng.standard_normal(len(t))
    return highpass(n, 8000) * np.exp(-t * (14 if open_ else 70)) * 0.8


def crash(dur=1.8):
    t = t_axis(dur)
    n = rng.standard_normal(len(t))
    return highpass(n, 4500) * np.exp(-t * 2.6) * 0.9


def impact():
    t = t_axis(0.9)
    f = 90 * np.exp(-t * 10) + 38
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 4.5) * 1.3


# ---------- tonal ----------
NOTE = {"A1": 55.0, "C2": 65.41, "D2": 73.42, "E2": 82.41, "F2": 87.31,
        "G2": 98.0, "A2": 110.0}

# chord progression per bar (root, chord tones as freq ratios of A4-relative midi)
def midi_f(m):
    return 440.0 * 2 ** ((m - 69) / 12)

# Am  F  C  G  (midi roots 45, 41, 48, 43)
PROG = [
    (45, [57, 60, 64]),   # Am: A3 C4 E4
    (41, [57, 60, 65]),   # F:  A3 C4 F4
    (48, [55, 60, 64]),   # C:  G3 C4 E4
    (43, [55, 59, 62]),   # G:  G3 B3 D4
]


def saw(freq, dur, detune=0.0):
    t = t_axis(dur)
    ph = (t * freq * (1 + detune)) % 1.0
    return 2 * ph - 1


def bass_note(freq, dur):
    s = saw(freq, dur) + 0.5 * saw(freq * 0.5, dur) + 0.3 * np.sin(2 * np.pi * freq * t_axis(dur))
    s = lowpass(s, 350)
    env = np.minimum(1, t_axis(dur) * 400) * np.exp(-t_axis(dur) * 6)
    return s * env


def pluck(freq, dur=0.22):
    t = t_axis(dur)
    s = signal.square(2 * np.pi * freq * t, duty=0.35) + 0.6 * saw(freq * 2.003, dur)
    s = lowpass(s, 5000)
    return s * np.exp(-t * 16) * np.minimum(1, t * 600)


def pad_chord(tones, dur, cutoff=1400):
    out = np.zeros(int(SR * dur))
    for m in tones:
        f = midi_f(m)
        for dt in (-0.004, 0.0, 0.004):
            out += saw(f, dur, dt)
    out = lowpass(out, cutoff) / (len(tones) * 3)
    t = t_axis(dur)
    a = np.minimum(1, t * 12)
    r = np.minimum(1, (dur - t) * 12)
    return out * a * r


def riser(dur):
    t = t_axis(dur)
    n = rng.standard_normal(len(t))
    # rising noise: amplitude + brightness via time-varying mix of HP'd versions
    bright = highpass(n, 6000)
    mid = bandpass(n, 800, 5000)
    x = mid * (1 - t / dur) + bright * (t / dur)
    amp = (t / dur) ** 2.2
    tone = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (2 * t / dur)) / SR) * 0.25
    return (x * 0.8 + tone) * amp


# ---------- arrangement ----------
mix = np.zeros(N)
drums = np.zeros(N)
music = np.zeros(N)

def bar_t(bar, beat=0.0):  # bar is 0-indexed
    return bar * BAR + beat * BEAT

K, CL, HC, HO = kick(), clap(), hat(False), hat(True)

# --- intro (bars 0-1): sparse kicks building, pad swell, riser ---
place(music, bar_t(0), pad_chord([45, 57, 60, 64], BAR * 2, cutoff=900), 0.7)
for b, g in [(0, 0.5), (1, 0.6), (2, 0.7), (3, 0.8), (4, 0.9), (5, 0.95), (6, 1.0), (7, 1.0)]:
    place(drums, bar_t(0, b * 1.0), K, g * 0.8)
# snare roll, last half of bar 2
for i in range(8):
    place(drums, bar_t(1, 2 + i * 0.25), CL, 0.3 + 0.08 * i)
place(music, bar_t(0), riser(BAR * 2), 0.9)

# --- drop + groove (bars 2-13) ---
place(drums, bar_t(2), crash(), 0.8)
place(drums, bar_t(2), impact(), 1.0)
place(drums, bar_t(8), crash(), 0.55)

for bar in range(2, 14):
    root, tones = PROG[(bar - 2) % 4]
    # kick 4-on-floor
    for b in range(4):
        place(drums, bar_t(bar, b), K, 1.0)
    # clap on 2 and 4
    place(drums, bar_t(bar, 1), CL, 0.9)
    place(drums, bar_t(bar, 3), CL, 0.9)
    # hats: offbeat open, 16th closed (skip hats bars 8-9 for variation)
    if bar not in (8, 9):
        for b in range(4):
            place(drums, bar_t(bar, b + 0.5), HO, 0.5)
            for q in (0.25, 0.75):
                place(drums, bar_t(bar, b + q), HC, 0.25)
    # fill at end of bar 7 and 13
    if bar in (7, 13):
        for i in range(4):
            place(drums, bar_t(bar, 3 + i * 0.25), CL, 0.5 + 0.12 * i)
    # bass: 8ths root with octave pops
    rf = midi_f(root)
    pattern = [1, 1, 2, 1, 1, 2, 1, 1]  # octave multiplier per 8th
    for i, mult in enumerate(pattern):
        place(music, bar_t(bar, i * 0.5), bass_note(rf * mult, 0.26), 0.85)
    # pads
    place(music, bar_t(bar), pad_chord(tones, BAR, cutoff=1600), 0.45)
    # arp: 16ths cycling chord tones (octave up), bars 4+
    if bar >= 4:
        seq = [tones[0] + 12, tones[1] + 12, tones[2] + 12, tones[1] + 24]
        for i in range(16):
            m = seq[i % 4] + (12 if (bar >= 10 and i % 8 >= 4) else 0)
            place(music, bar_t(bar, i * 0.25), pluck(midi_f(m)), 0.30)

# --- bar 14: ominous turn (lathrys "ominous output from fable") ---
# keep kick, drop everything bright, add dark drone + riser
for b in range(4):
    place(drums, bar_t(14, b), K, 1.0)
place(drums, bar_t(14, 1), CL, 0.8)
place(drums, bar_t(14, 3), CL, 0.8)
dt = t_axis(BAR)
drone = (np.sin(2 * np.pi * 55 * dt) + 0.5 * np.sin(2 * np.pi * 55 * 1.5 * dt)
         + 0.3 * np.sin(2 * np.pi * 58.27 * dt))  # adds a minor-second beat = unease
place(music, bar_t(14), drone * np.minimum(1, dt * 8) * 0.5, 0.9)
place(music, bar_t(14), riser(BAR), 0.85)
for i in range(8):
    place(drums, bar_t(14, 2 + i * 0.25), CL, 0.35 + 0.1 * i)

# --- bar 15: final hit + outro chord ---
place(drums, bar_t(15), crash(2.2), 0.9)
place(drums, bar_t(15), impact(), 1.1)
place(drums, bar_t(15), K, 1.0)
place(music, bar_t(15), pad_chord([45, 57, 60, 64, 69], BAR, cutoff=2000), 0.7)
place(music, bar_t(15, 2), K * 0.0, 0)  # nothing: let it ring
place(drums, bar_t(15, 3.5), K, 0.7)    # heartbeat button

# ---------- sidechain music to kick ----------
beat_idx = (np.arange(N) / SR) % BEAT
duck = 1 - 0.55 * np.exp(-beat_idx * 18)
groove_mask = np.ones(N)
intro_end = int(bar_t(2) * SR)
groove_mask[:intro_end] = 0.75  # gentler duck in intro
duck = 1 - (1 - duck) * groove_mask
music *= duck

# ---------- mix, stereo, master ----------
mono = drums * 0.9 + music * 0.8
mono = np.tanh(mono * 1.4) * 0.85

# cheap stereo: haas-delayed copy mixed differently per side
delay = int(0.012 * SR)
wet = np.zeros(N)
wet[delay:] = mono[:-delay]
left = mono * 0.92 + wet * 0.10
right = mono * 0.86 + wet * 0.18

peak = max(np.abs(left).max(), np.abs(right).max())
left /= peak / 0.95
right /= peak / 0.95

# fade-out last 0.4s so the file ends clean
fade = np.ones(N)
nf = int(0.4 * SR)
fade[-nf:] = np.linspace(1, 0, nf)
left *= fade
right *= fade

stereo = np.empty(N * 2, dtype=np.int16)
stereo[0::2] = (left * 32767).astype(np.int16)
stereo[1::2] = (right * 32767).astype(np.int16)

with wave.open("music.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(stereo.tobytes())

print(f"music.wav written: {TOTAL:.2f}s, {N} samples")
