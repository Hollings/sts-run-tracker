"""Synthesize the 45s story arc track: 128 BPM, 24 bars, A minor.

Arc (matches render_video.py acts):
  bars 0-1   cinematic intro: dark pad, booms on narration slams
  bars 2-5   ACT 1 light groove (cozy vignettes)
  bar  6     the turn: drums cut, snare roll, riser
  bars 7-13  ACT 2/3 full groove, peak at 12 (grace goes viral)
  bars 14-15 darkening (eris -> ren ominous)
  bar  16    TAPE STOP -> bars 16-17 drone + heartbeat (the reveal)
  bars 18-19 the build: accelerating roll + riser
  bars 20-21 THE DROP (you're watching it)
  bars 22-23 outro: final hits, ring out
Output: music.wav (stereo 44.1k)
"""
import numpy as np
from scipy import signal
import wave

SR = 44100
BPM = 128.0
BEAT = 60.0 / BPM
BAR = BEAT * 4
NBARS = 24
TOTAL = BAR * NBARS            # 45.0 s
N = int(SR * TOTAL)

rng = np.random.default_rng(20260612)


def t_axis(dur):
    return np.arange(int(SR * dur)) / SR


def place(buf, start_s, snd, gain=1.0):
    i = int(start_s * SR)
    if i >= len(buf) or i < 0:
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


# ---------- drums ----------
def kick():
    t = t_axis(0.35)
    f = 150 * np.exp(-t * 22) + 44
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.tanh(np.sin(ph) * np.exp(-t * 11) * 2.4) * 0.9
    click = highpass(rng.standard_normal(len(t)) * np.exp(-t * 250), 3000)
    return body + click * 0.45


def clap():
    t = t_axis(0.30)
    n = rng.standard_normal(len(t))
    env = np.zeros(len(t))
    for d, g in [(0.0, 1.0), (0.012, 0.8), (0.025, 0.65)]:
        i = int(d * SR)
        env[i:] += g * np.exp(-(t[: len(t) - i]) * 38)
    env += 0.5 * np.exp(-t * 9)
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
def midi_f(m):
    return 440.0 * 2 ** ((m - 69) / 12)

PROG = [
    (45, [57, 60, 64]),   # Am
    (41, [57, 60, 65]),   # F
    (48, [55, 60, 64]),   # C
    (43, [55, 59, 62]),   # G
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
    return out * np.minimum(1, t * 12) * np.minimum(1, (dur - t) * 12)


def riser(dur):
    t = t_axis(dur)
    n = rng.standard_normal(len(t))
    bright = highpass(n, 6000)
    mid = bandpass(n, 800, 5000)
    x = mid * (1 - t / dur) + bright * (t / dur)
    amp = (t / dur) ** 2.2
    tone = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (2 * t / dur)) / SR) * 0.25
    return (x * 0.8 + tone) * amp


def crackle(dur):
    """sparse vinyl ticks"""
    out = np.zeros(int(SR * dur))
    n_ticks = int(dur * 28)
    for pos in rng.uniform(0, dur, n_ticks):
        i = int(pos * SR)
        ln = int(0.004 * SR)
        if i + ln < len(out):
            out[i:i + ln] += rng.standard_normal(ln) * np.exp(-np.arange(ln) / (0.0006 * SR))
    return highpass(out, 2500) * 0.5


# ---------- arrangement ----------
drums = np.zeros(N)
music = np.zeros(N)

def bar_t(bar, beat=0.0):
    return bar * BAR + beat * BEAT

K, CL, HC, HO = kick(), clap(), hat(False), hat(True)

def groove_bar(bar, kick_g=1.0, claps=True, hats=True, bass=True, pads=True,
               arp=False, cutoff=1600, arp_oct=0, double_hats=False):
    root, tones = PROG[(bar - 2) % 4]
    for b in range(4):
        place(drums, bar_t(bar, b), K, kick_g)
    if claps:
        place(drums, bar_t(bar, 1), CL, 0.9)
        place(drums, bar_t(bar, 3), CL, 0.9)
    if hats:
        for b in range(4):
            place(drums, bar_t(bar, b + 0.5), HO, 0.5)
            qs = (0.25, 0.75) if not double_hats else (0.125, 0.25, 0.375, 0.625, 0.75, 0.875)
            for q in qs:
                place(drums, bar_t(bar, b + q), HC, 0.25)
    if bass:
        rf = midi_f(root)
        for i, mult in enumerate([1, 1, 2, 1, 1, 2, 1, 1]):
            place(music, bar_t(bar, i * 0.5), bass_note(rf * mult, 0.26), 0.85)
    if pads:
        place(music, bar_t(bar), pad_chord(tones, BAR, cutoff=cutoff), 0.45)
    if arp:
        seq = [tones[0] + 12, tones[1] + 12, tones[2] + 12, tones[1] + 24]
        for i in range(16):
            m = seq[i % 4] + arp_oct + (12 if i % 8 >= 4 else 0)
            place(music, bar_t(bar, i * 0.25), pluck(midi_f(m)), 0.30)

# --- bars 0-1: cinematic intro ---
place(music, bar_t(0), pad_chord([33, 45, 52, 57], BAR * 2, cutoff=650), 0.85)  # deep Am
for b in range(8):
    place(drums, bar_t(0, b + 0.5), HC, 0.18)   # ticking
for b in (0, 2, 4, 6):                           # booms under narration slams
    place(drums, bar_t(0, b), impact(), 0.75)
    place(drums, bar_t(0, b), K, 0.7)
place(music, bar_t(1), riser(BAR), 0.8)

# --- bars 2-5: ACT 1 light groove (vignettes) ---
place(drums, bar_t(2), crash(), 0.6)
for bar in range(2, 6):
    groove_bar(bar, kick_g=0.85, claps=(bar >= 4), hats=True, bass=True,
               pads=True, cutoff=1100, arp=(bar == 5))
    place(music, bar_t(bar) - 0.3, riser(0.3), 0.35)   # vignette whooshes
    place(drums, bar_t(bar), impact(), 0.3)

# --- bar 6: the turn ---
place(drums, bar_t(6, 0), K, 1.0)
place(drums, bar_t(6, 0), impact(), 0.8)
for i in range(8):                                  # accelerating roll
    place(drums, bar_t(6, 2 + i * 0.25), CL, 0.35 + 0.09 * i)
place(music, bar_t(6), riser(BAR), 0.95)

# --- bars 7-13: ACT 2/3 full groove ---
place(drums, bar_t(7), crash(), 0.8)
place(drums, bar_t(7), impact(), 0.9)
for bar in range(7, 14):
    peak = bar >= 12
    groove_bar(bar, kick_g=1.0, arp=(bar >= 8), cutoff=1600 if not peak else 1900,
               arp_oct=12 if peak else 0, double_hats=peak)
# tension bar 11: pull the bass out, big riser
# (groove_bar already placed bass; cheap fix: duck music around bar 11 via automation below)
place(music, bar_t(11), riser(BAR), 0.9)
place(drums, bar_t(12), crash(), 0.7)
# segment whooshes at story beats
for bt in (bar_t(7), bar_t(8), bar_t(11), bar_t(12), bar_t(14), bar_t(15)):
    place(music, bt - 0.3, riser(0.3), 0.4)
    place(drums, bt, impact(), 0.35)

# --- bars 14-15: darkening ---
dt = t_axis(BAR * 2)
tension = np.sin(2 * np.pi * 58.27 * dt) * np.minimum(1, dt * 0.7)   # creeping minor 2nd
place(music, bar_t(14), tension, 0.30)
for bar in (14, 15):
    groove_bar(bar, kick_g=1.0, arp=False, pads=True, cutoff=850)
for i in range(8):
    place(drums, bar_t(15, 2 + i * 0.25), CL, 0.3 + 0.1 * i)

# --- bars 16-17: post tape-stop void (drone + heartbeat) ---
dt2 = t_axis(BAR * 2)
drone = (np.sin(2 * np.pi * 55 * dt2) + 0.5 * np.sin(2 * np.pi * 82.5 * dt2)
         + 0.35 * np.sin(2 * np.pi * 58.27 * dt2))
place(music, bar_t(16), drone * np.minimum(1, dt2 * 6) * 0.5, 0.9)
place(music, bar_t(16), crackle(BAR * 2), 0.7)
for bar in (16, 17):
    for bt_, g in [(0, 0.8), (0.45, 0.5), (2, 0.8), (2.45, 0.5)]:
        place(drums, bar_t(bar, bt_), K, g)

# --- bars 18-19: THE BUILD ---
for b in range(8):
    place(drums, bar_t(18, b), K, 0.55 + b * 0.06)
# accelerating snare roll: 8ths -> 16ths -> 32nds
pos = 0.0
step = 0.5
while pos < 8.0:
    g = 0.3 + 0.5 * (pos / 8)
    place(drums, bar_t(18, pos), CL, g)
    if pos > 4:
        step = 0.25
    if pos > 6.5:
        step = 0.125
    pos += step
place(music, bar_t(18), riser(BAR * 2), 1.1)
place(music, bar_t(18), pad_chord([45, 57, 60, 64], BAR * 2, cutoff=900), 0.4)

# --- bars 20-21: THE DROP ---
place(drums, bar_t(20), crash(2.0), 1.0)
place(drums, bar_t(20), impact(), 1.2)
for bar in (20, 21):
    groove_bar(bar, kick_g=1.05, arp=True, arp_oct=12, cutoff=2100, double_hats=True)

# --- bars 22-23: outro ---
groove_bar(22, kick_g=0.95, arp=True, cutoff=1500)
for i in range(4):
    place(drums, bar_t(22, 3 + i * 0.25), CL, 0.5 + 0.12 * i)
place(drums, bar_t(23), crash(2.4), 0.9)
place(drums, bar_t(23), impact(), 1.1)
place(drums, bar_t(23), K, 1.0)
place(music, bar_t(23), pad_chord([45, 57, 60, 64, 69], BAR, cutoff=2000), 0.75)
place(drums, bar_t(23, 3.5), K, 0.6)

# ---------- automation: duck music in tension bar 11 first half ----------
i0, i1 = int(bar_t(11) * SR), int(bar_t(11, 2) * SR)
ramp = np.linspace(0.35, 1.0, i1 - i0)
music[i0:i1] *= ramp

# ---------- sidechain ----------
beat_idx = (np.arange(N) / SR) % BEAT
duck = 1 - 0.55 * np.exp(-beat_idx * 18)
soft = np.ones(N)
soft[:int(bar_t(2) * SR)] = 0.5
soft[int(bar_t(16) * SR):int(bar_t(18) * SR)] = 0.2
duck = 1 - (1 - duck) * soft
music *= duck

# ---------- mix + tape stop + master ----------
mono = drums * 0.9 + music * 0.8
mono = np.tanh(mono * 1.4) * 0.85

ts_end = int(bar_t(16) * SR)
ts_len = int(0.45 * SR)
seg = mono[ts_end - ts_len:ts_end].copy()
speed = np.linspace(1.0, 0.02, ts_len)
idx = np.clip(np.cumsum(speed), 0, ts_len - 1).astype(int)
mono[ts_end - ts_len:ts_end] = seg[idx] * np.linspace(1.0, 0.4, ts_len)

delay = int(0.012 * SR)
wet = np.zeros(N)
wet[delay:] = mono[:-delay]
left = mono * 0.92 + wet * 0.10
right = mono * 0.86 + wet * 0.18
peak = max(np.abs(left).max(), np.abs(right).max())
left /= peak / 0.95
right /= peak / 0.95
fade = np.ones(N)
nf = int(0.5 * SR)
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
