"""Render the daily recap video, combo-video edition.
1080x1920 @ 30fps, 30s, beat-synced to music.wav (128 BPM).

Structure (16 bars):
  bar 0      cold open: one word slam per beat, color strobes, giant flying avatars
  bar 1      stats machine gun: one stat per beat
  bars 2-14  8 cards x 1.5 bars, whip-pan transitions, impact frames, hitstop,
             combo counter, damage popups, fly-through words, speed lines
  bar 14     tape-stop aftermath: ominous outro pt.1
  bar 15     GG stamp + final combo readout

Usage:
  python render_video.py                 -> recap.mp4
  python render_video.py preview F1 F2.. -> preview_F.png frames
"""
import json
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 30
FRAMES = 900
BPM = 128.0
FPB = FPS * 60.0 / BPM          # 14.0625 frames per beat
FPBAR = FPB * 4                 # 56.25 frames per bar

NAVY = (11, 15, 30)
WHITE = (245, 247, 255)
BLUE = (16, 131, 254)
PINK = (255, 46, 136)
CYAN = (0, 229, 255)
YELLOW = (255, 214, 10)
GREEN = (61, 255, 162)
PURPLE = (179, 136, 255)
ORANGE = (255, 122, 26)
RED = (255, 69, 69)

FONT_DIR = "C:/Windows/Fonts/"
_fonts = {}
def F(name, size):
    size = max(4, int(size))
    key = (name, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_DIR + name, size)
    return _fonts[key]

BLACK_F = "seguibl.ttf"
BOLD_F = "segoeuib.ttf"
MONO_F = "consolab.ttf"

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def ease_out_cubic(p):
    p = clamp(p)
    return 1 - (1 - p) ** 3

def ease_out_back(p):
    p = clamp(p)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2

def ease_in_cubic(p):
    p = clamp(p)
    return p ** 3

def sanitize(s):
    out = []
    for ch in s:
        o = ord(ch)
        if o > 0xFFFF or 0x2600 <= o <= 0x27BF or o in (0xFE0F, 0x200D):
            continue
        out.append(ch)
    return "".join(out).strip()

def wrap_text(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines

def fit_quote(draw, text, max_w, max_h, start=96, floor=50, lh=1.16):
    size = start
    while size > floor:
        f = F(BLACK_F, size)
        lines = wrap_text(draw, text, f, max_w)
        if len(lines) * size * lh <= max_h:
            return f, lines, size
        size -= 4
    f = F(BLACK_F, floor)
    return f, wrap_text(draw, text, f, max_w), floor

def fit_width(draw, text, max_w, start):
    size = start
    while size > 20 and draw.textlength(text, font=F(BLACK_F, size)) > max_w:
        size -= 4
    return size

# ---------------- assets ----------------
_imgs = {}
def load_img(path):
    if path not in _imgs:
        _imgs[path] = Image.open(path).convert("RGB")
    return _imgs[path]

def circle_avatar(path, size):
    key = (path, size, "circ")
    if key not in _imgs:
        im = load_img(path).resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size * 4, size * 4), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size * 4, size * 4), fill=255)
        mask = mask.resize((size, size), Image.LANCZOS)
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out.paste(im, (0, 0), mask)
        _imgs[key] = out
    return _imgs[key]

def rounded_img(path, max_w, max_h, radius=36):
    key = (path, max_w, max_h, "rnd")
    if key not in _imgs:
        im = load_img(path)
        scale = min(max_w / im.width, max_h / im.height)
        nw, nh = int(im.width * scale), int(im.height * scale)
        im = im.resize((nw, nh), Image.LANCZOS)
        mask = Image.new("L", (nw * 2, nh * 2), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, nw * 2, nh * 2), radius * 2, fill=255)
        mask = mask.resize((nw, nh), Image.LANCZOS)
        out = Image.new("RGBA", (nw, nh), (0, 0, 0, 0))
        out.paste(im, (0, 0), mask)
        _imgs[key] = out
    return _imgs[key]

# ---------------- content ----------------
data = json.load(open("recap_data.json", encoding="utf-8"))
by_handle = {a["handle"]: a for a in data["activity"]}
norvid_count = len(by_handle["norvid-studies.bsky.social"]["posts"])

def av(handle):
    return f"assets/avatar_{handle.replace('.', '_')}.jpg"

CARDS = [
    dict(kind="quote", handle="norvid-studies.bsky.social", name="norvid_studies",
         badge="YOUR #1 MUTUAL", accent=CYAN,
         quote="the water grows cold. the thumb no longer asks where it is going.",
         image="assets/post_norvid_0.jpg",
         stat=f"{norvid_count} POSTS IN 24H", likes=10,
         fly=["POETRY", "CANON", "REAL"]),
    dict(kind="quote", handle="freyja-lynx.dev", name="freyja",
         badge="TAKE OF THE DAY", accent=GREEN,
         quote="if you hate being inconvenienced by bikers you should support giving them separated bike infra instead of complaining like a little bitch baby",
         stat="ZERO APOLOGIES", likes=39,
         fly=["VIOLATION", "W TAKE", "RATIO"]),
    dict(kind="quote", handle="scoiattolo.mountainherder.xyz", name="Scoiattolo",
         badge="WHOLESOME MOMENT", accent=YELLOW,
         quote="we stop at this Greek cafe for spanakopita and coffee. Today I realized we've been in before they open and they've just been too nice to say anything.",
         stat="PROTECT THIS CAFE", likes=115,
         fly=["CRYING", "PROTECT", "LORE"]),
    dict(kind="quote", handle="quillmatiq.com", name="Anuj Ahooja",
         badge="IT FIXED HIM", accent=PINK,
         quote="Btw, I was right - it fixed me",
         image="assets/post_quillmatiq_0.jpg",
         stat="FOOD AS MEDICINE", likes=225,
         fly=["HEALED", "W", "COOKED"]),
    dict(kind="quote", handle="isolyth.dev", name="Eris",
         badge="GALAXY BRAIN", accent=PURPLE,
         quote="computer natural language interaction is ~solved. The implications are fucking insane",
         stat="CALLED IT", likes=100,
         fly=["GALAXY", "BRAIN", "SHEESH"]),
    dict(kind="discourse", accent=BLUE,
         quotes=[
             ("minormobius.bsky.social", "Minor Mobius", 38,
              "Put me in your group chats. you will surely not regret it"),
             ("thebadcode.com", "austin", 40,
              "i wouldn't want to be in any group chat that would have me as a member"),
             ("brennan.computer", "brennan", 55,
              "a bot that puts everyone joking about not being in group chats into a group chat"),
         ]),
    dict(kind="quote", handle="gracekind.net", name="Grace",
         badge="CERTIFIED BANGER", accent=BLUE,
         quote='"can you use whatever resources you like, and python, to generate a short video and render it using ffmpeg?"',
         sub="(hold that thought)",
         stat="37 REPOSTS", likes=246,
         fly=["VIRAL", "CLIP THAT", "NO SHOT"]),
    dict(kind="quote", handle="lathrys.at", name="a very good ren",
         badge="MEANWHILE...", accent=RED,
         quote="ominous output from fable",
         sub='"this thread of videos created by fable is really something else. i\'m genuinely shocked."',
         stat="FORESHADOWING", likes=64,
         fly=["OMINOUS", "HE KNOWS", "..."]),
]

COLD_END = FPBAR              # 56.25
STATS_END = FPBAR * 2         # 112.5
CARD_LEN = FPBAR * 1.5        # 84.375
CARDS_END = STATS_END + CARD_LEN * 8   # 787.5
GG_START = CARDS_END + FPBAR  # 843.75

WHIPS = [STATS_END + k * CARD_LEN for k in range(9)]  # drop + 7 card cuts + outro
TOTAL_POSTS = 285

TICKER = ("+++ CEE'S CIRCLE DAILY RECAP +++ 46 MUTUALS ACTIVE +++ 285 POSTS IN 24H "
          f"+++ NORVID POSTED {norvid_count} TIMES +++ GRACE WENT VIRAL +++ IT FIXED HIM "
          "+++ GROUP CHAT DISCOURSE RAGES ON +++ SPANAKOPITA CAFE LORE +++ "
          "OMINOUS FABLE OUTPUT +++ NO SLEEP ALL BANGERS ")

# pre-rendered fly-through words: (img, y0, speed, direction)
def make_fly_word(text, color, size, alpha, rot):
    f = F(BLACK_F, size)
    tmp = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(tmp)
    tw, th = int(d.textlength(text, font=f)) + 40, int(size * 1.5)
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20, th // 2), text, font=f, fill=color + (alpha,), anchor="lm")
    return im.rotate(rot, expand=True, resample=Image.BICUBIC)

FLY = {}
_fly_rng = np.random.default_rng(99)
for ci, card in enumerate(CARDS):
    words = card.get("fly", [])
    items = []
    for wi, word in enumerate(words):
        size = int(_fly_rng.integers(150, 240))
        col = card["accent"] if wi % 2 == 0 else WHITE
        alpha = int(_fly_rng.integers(26, 46))
        rot = float(_fly_rng.uniform(-18, 18))
        img = make_fly_word(word, col, size, alpha, rot)
        y0 = int(_fly_rng.integers(250, 1500))
        speed = float(_fly_rng.uniform(11, 19))
        direction = 1 if (wi + ci) % 2 == 0 else -1
        items.append((img, y0, speed, direction))
    FLY[ci] = items

SPEED_ANGLES = {ci: np.random.default_rng(ci + 7).uniform(0, 2 * math.pi, 22)
                for ci in range(9)}

# ---------------- background ----------------
BG_W, BG_H = 135, 240
yy, xx = np.mgrid[0:BG_H, 0:BG_W].astype(np.float32)
xx /= BG_W; yy /= BG_H

def background(frame, accent):
    t = frame / FPS
    base = np.zeros((BG_H, BG_W, 3), np.float32)
    base[..., 0] = NAVY[0]; base[..., 1] = NAVY[1]; base[..., 2] = NAVY[2]
    blobs = [
        (0.5 + 0.48 * math.sin(t * 1.3), 0.25 + 0.25 * math.sin(t * 0.9 + 2), accent, 0.5),
        (0.5 + 0.48 * math.cos(t * 1.0 + 1), 0.75 + 0.22 * math.cos(t * 1.15), BLUE, 0.38),
        (0.5 + 0.4 * math.sin(t * 1.6 + 4), 0.5 + 0.38 * math.cos(t * 0.8 + 1), PINK, 0.25),
    ]
    for bx, by, col, strength in blobs:
        d2 = (xx - bx) ** 2 + (yy - by) ** 2 * 0.6
        g = np.exp(-d2 * 9) * strength
        for c in range(3):
            base[..., c] += g * col[c] * 0.55
    stripe = (np.sin((xx * 3 + yy * 2.2) * 14 - t * 3.5) > 0.92).astype(np.float32) * 8
    base += stripe[..., None]
    np.clip(base, 0, 255, out=base)
    return Image.fromarray(base.astype(np.uint8)).resize((W, H), Image.BILINEAR)

def draw_rays(bg, frame, accent, cx=540, cy=820, alpha=13):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    t = frame / FPS
    for i in range(10):
        a0 = t * 0.9 + i * (2 * math.pi / 10)
        a1 = a0 + 0.13
        pts = [(cx, cy),
               (cx + 1800 * math.cos(a0), cy + 1800 * math.sin(a0)),
               (cx + 1800 * math.cos(a1), cy + 1800 * math.sin(a1))]
        d.polygon(pts, fill=accent + (alpha,))
    bg.alpha_composite(ov) if bg.mode == "RGBA" else bg.paste(ov, (0, 0), ov)

def draw_speed_lines(bg, lf, ci, accent):
    if lf >= 10:
        return
    a = int(130 * (1 - lf / 10))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    cx, cy = W / 2, 860
    for ang in SPEED_ANGLES[ci]:
        r0 = 330 + lf * 30
        x0, y0 = cx + r0 * math.cos(ang), cy + r0 * math.sin(ang) * 1.4
        x1, y1 = cx + 1700 * math.cos(ang), cy + 1700 * math.sin(ang) * 1.4
        d.line((x0, y0, x1, y1), fill=WHITE + (a,), width=5)
    bg.paste(ov, (0, 0), ov)

vy, vx = np.mgrid[0:H, 0:W].astype(np.float32)
vd = ((vx / W - 0.5) ** 2 * 1.1 + (vy / H - 0.5) ** 2) ** 0.5
VIGNETTE = (1.0 - np.clip(vd - 0.38, 0, 1) * 0.55)[..., None].astype(np.float32)

grain_rng = np.random.default_rng(1234)

# ---------------- shared drawing ----------------
def draw_badge(layer, cx, y, text, accent, scale=1.0, alpha=255, rot=-2.5):
    if scale < 0.05 or alpha < 2:
        return
    f = F(BLACK_F, 56 * scale)
    d = ImageDraw.Draw(layer)
    tw = d.textlength(text, font=f)
    pw, ph = int(tw + 90), int(56 * scale * 1.9)
    pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pill)
    pd.rounded_rectangle((0, 0, pw - 1, ph - 1), ph // 2, fill=accent + (alpha,))
    pd.text((pw / 2, ph / 2 - 4), text, font=f, fill=NAVY + (alpha,), anchor="mm")
    pill = pill.rotate(rot, expand=True, resample=Image.BICUBIC)
    layer.paste(pill, (int(cx - pill.width / 2), int(y - pill.height / 2)), pill)

def draw_glow_ring(layer, cx, cy, r, accent, alpha=255):
    d = ImageDraw.Draw(layer)
    for extra, a in [(14, 40), (9, 80), (5, 160)]:
        d.ellipse((cx - r - extra, cy - r - extra, cx + r + extra, cy + r + extra),
                  outline=accent + (int(a * alpha / 255),), width=4)
    d.ellipse((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2),
              outline=accent + (alpha,), width=6)

def draw_heart(layer, x, y, s, color, alpha=255):
    d = ImageDraw.Draw(layer)
    c = color + (alpha,)
    d.ellipse((x, y, x + s * 0.55, y + s * 0.55), fill=c)
    d.ellipse((x + s * 0.45, y, x + s, y + s * 0.55), fill=c)
    d.polygon([(x + s * 0.02, y + s * 0.38), (x + s * 0.98, y + s * 0.38),
               (x + s * 0.5, y + s)], fill=c)

def stamp_text(layer, cx, cy, text, size, fill, rot, alpha=255, outline=None):
    """big rotated slammed text"""
    f = F(BLACK_F, size)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tw = int(tmp.textlength(text, font=f)) + 60
    th = int(size * 1.6)
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if outline:
        for ox, oy in [(-6, 0), (6, 0), (0, -6), (0, 6), (8, 8)]:
            d.text((tw / 2 + ox, th / 2 + oy), text, font=f,
                   fill=outline + (alpha,), anchor="mm")
    d.text((tw / 2, th / 2), text, font=f, fill=fill + (alpha,), anchor="mm")
    im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    layer.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)

def combo_counter(layer, frame):
    if not (STATS_END <= frame < CARDS_END):
        return
    d = ImageDraw.Draw(layer)
    p = (frame - STATS_END) / (CARDS_END - STATS_END)
    n = min(TOTAL_POSTS, int(TOTAL_POSTS * p * 1.03))
    n_prev = min(TOTAL_POSTS, int(TOTAL_POSTS * ((frame - 1 - STATS_END) /
                                                 (CARDS_END - STATS_END)) * 1.03))
    pop = 1.18 if n != n_prev else 1.0
    j = np.random.default_rng(frame).integers(-2, 3) if n != n_prev else 0
    size = int(96 * pop)
    f = F(BLACK_F, size)
    x, y = W - 70 + j, 200
    d.text((x + 5, y + 5), str(n), font=f, fill=RED + (230,), anchor="rm")
    d.text((x, y), str(n), font=f, fill=YELLOW + (255,), anchor="rm")
    d.text((x, y + 78), "HITS COMBO", font=F(BLACK_F, 38), fill=WHITE + (220,), anchor="rm")

def ticker(layer, frame):
    if not (STATS_END <= frame < CARDS_END):
        return
    d = ImageDraw.Draw(layer)
    f = F(MONO_F, 38)
    tw = int(d.textlength(TICKER, font=f))
    x0 = -int((frame * 9) % (tw + 100))
    d.rectangle((0, 1788, W, 1852), fill=(0, 0, 0, 110))
    d.text((x0, 1820), TICKER, font=f, fill=WHITE + (210,), anchor="lm")
    d.text((x0 + tw + 100, 1820), TICKER, font=f, fill=WHITE + (210,), anchor="lm")

def progress(layer, frame):
    d = ImageDraw.Draw(layer)
    p = frame / FRAMES
    d.rounded_rectangle((60, 1872, W - 60, 1884), 6, fill=WHITE + (40,))
    d.rounded_rectangle((60, 1872, 60 + (W - 120) * p, 1884), 6, fill=BLUE + (220,))

# ---------------- sections ----------------
COLD_WORDS = [("CEE'S", BLUE, -6), ("CIRCLE", PINK, 4), ("DAILY", CYAN, -3), ("RECAP", YELLOW, 5)]
COLD_AVS = ["norvid-studies.bsky.social", "gracekind.net", "freyja-lynx.dev", "quillmatiq.com"]

def sec_cold(layer, lf):
    d = ImageDraw.Draw(layer)
    beat = min(3, int(lf / FPB))
    fb = lf - beat * FPB
    word, col, rot = COLD_WORDS[beat]
    # color slab flash at each beat
    fa = int(190 * math.exp(-fb / 2.2))
    if fa > 3:
        d.rectangle((0, 0, W, H), fill=col + (fa,))
    # giant flying avatar behind
    handle = COLD_AVS[beat]
    sz = 620
    avt = circle_avatar(av(handle), sz)
    direction = 1 if beat % 2 == 0 else -1
    ax = int(-400 + fb * 48) if direction > 0 else int(W + 400 - sz - fb * 48)
    ghost = avt.copy()
    ghost.putalpha(ghost.getchannel("A").point(lambda v: int(v * 0.30)))
    layer.paste(ghost, (ax, 580 + beat * 60), ghost)
    # the word, slammed
    pp = ease_out_cubic(fb / 5)
    size = int(250 * (2.0 - pp))   # 500 -> 250 crash-zoom in
    stamp_text(layer, W / 2, 880, word, size, WHITE, rot * (1 - pp * 0.5),
               alpha=int(255 * clamp(fb / 2)), outline=col)
    d.text((W / 2, 330), "YOUR TIMELINE / LAST 24H", font=F(MONO_F, 42),
           fill=WHITE + (200,), anchor="mm")
    d.text((W / 2, 1480), "JUN 11 → JUN 12 / 2026", font=F(MONO_F, 40),
           fill=col + (230,), anchor="mm")

STAT_WORDS = [("46", "MUTUALS ACTIVE", CYAN), ("285", "POSTS", PINK),
              ("24", "HOURS", YELLOW), ("LET'S", "GO.", GREEN)]

def sec_stats(layer, lf):
    d = ImageDraw.Draw(layer)
    beat = min(3, int(lf / FPB))
    fb = lf - beat * FPB
    num, label, col = STAT_WORDS[beat]
    j = np.random.default_rng(int(lf) + 50).integers(-4, 5, 2) if fb < 5 else (0, 0)
    pp = ease_out_back(fb / 6)
    size = int(330 * (0.55 + 0.45 * pp))
    stamp_text(layer, W / 2 + j[0], 800 + j[1], num, size, col, (-4, 3, -2, 4)[beat],
               alpha=int(255 * clamp(fb / 2)), outline=NAVY)
    stamp_text(layer, W / 2 + j[0], 1120 + j[1], label, 92, WHITE, 0,
               alpha=int(255 * clamp((fb - 1) / 3)))
    # ghost trail of previous stat in corner
    if beat > 0:
        pn, pl, pc = STAT_WORDS[beat - 1]
        stamp_text(layer, 180, 280, pn, 110, pc, -8, alpha=70)
    d.text((W / 2, 1560), "HERE'S WHAT WENT DOWN", font=F(MONO_F, 44),
           fill=WHITE + (160,), anchor="mm")

def card_alpha(lf):
    a = clamp(lf / 4)
    if lf > CARD_LEN - 5:
        a *= clamp((CARD_LEN - lf) / 5)
    return a

def sec_card(layer, lf, card, ci):
    # hitstop: freeze content for 3 frames right after entrance
    if 3 <= lf < 6:
        lf = 3.0
    d = ImageDraw.Draw(layer)
    accent = card["accent"]
    ga = card_alpha(lf)
    A = lambda a=255: int(a * ga)
    drift = int(lf * 0.5)   # slow upward content drift
    oy = -drift

    draw_badge(layer, W / 2, 300 + oy, card["badge"], accent, alpha=A(),
               rot=-2.5 + 2.2 * math.sin(lf * 0.25))
    # avatar punches in from the left
    asz = 175
    px = ease_out_back(lf / 8)
    acx = int(-220 + (200 - -220) * px)
    acy = 520 + oy
    avt = circle_avatar(av(card["handle"]), asz)
    rot_av = (1 - px) * -40
    if abs(rot_av) > 1:
        avt = avt.rotate(rot_av, resample=Image.BICUBIC)
    layer.paste(avt, (int(acx - asz / 2), int(acy - asz / 2)), avt)
    draw_glow_ring(layer, acx, acy, asz / 2, accent, alpha=A())
    nx = int(W + 200 - (W + 200 - 320) * ease_out_cubic(lf / 8))
    d.text((nx, 480 + oy), sanitize(card["name"]), font=F(BLACK_F, 64),
           fill=WHITE + (A(),), anchor="lm")
    d.text((nx, 560 + oy), "@" + card["handle"], font=F(MONO_F, 40),
           fill=accent + (A(),), anchor="lm")

    has_img = "image" in card
    qtop = 680
    qheight = 320 if has_img else (520 if "sub" in card else 660)
    f, lines, size = fit_quote(d, sanitize(card["quote"]), W - 200, qheight,
                               start=84 if has_img else 96)
    bar_h = len(lines) * size * 1.16
    d.rounded_rectangle((92, qtop + oy, 106, qtop + bar_h + oy), 7, fill=accent + (A(),))
    y = qtop + size * 0.6
    for i, line in enumerate(lines):
        ls = 5 + i * 3
        pl = ease_out_cubic((lf - ls) / 8)
        la = int(255 * clamp((lf - ls) / 5) * ga)
        d.text((140 + (1 - pl) * 120, y + oy), line, font=f, fill=WHITE + (la,), anchor="lm")
        y += size * 1.16

    if "sub" in card:
        ss = 5 + len(lines) * 3 + 5
        sa = int(220 * clamp((lf - ss) / 7) * ga)
        sf = F(BOLD_F, 46)
        sy = y + 40
        for sl in wrap_text(d, sanitize(card["sub"]), sf, W - 240):
            d.text((140, sy + oy), sl, font=sf, fill=accent + (sa,), anchor="lm")
            sy += 60

    if has_img:
        istart = 12
        ip = ease_out_back((lf - istart) / 10)
        if lf >= istart and ip > 0.02:
            im = rounded_img(card["image"], 820, 560)
            siw, sih = max(2, int(im.width * ip)), max(2, int(im.height * ip))
            im2 = im.resize((siw, sih), Image.BILINEAR) if ip < 0.999 else im
            wob = 2.0 + 2.2 * math.sin(lf * 0.13)
            im2 = im2.rotate(wob, expand=True, resample=Image.BICUBIC)
            layer.paste(im2, (int(W / 2 - im2.width / 2), int(1330 + oy - im2.height / 2)), im2)

    # damage popups: likes fly off the avatar like combo damage
    total = card["likes"]
    chunks = [total // 4, total // 4, total - 2 * (total // 4)]
    for pi, (ps, amount) in enumerate(zip((16, 23, 30), chunks)):
        age = lf - ps
        if 0 <= age < 26 and amount > 0:
            pp_ = ease_out_back(age / 7)
            palpha = int(255 * (1 - age / 26))
            col = YELLOW if pi < 2 else RED
            stamp_text(layer, 360 + pi * 150, 400 + oy - age * 4.5, f"+{amount}",
                       int(56 + 26 * pp_), col, (-6, 5, -3)[pi], alpha=palpha, outline=NAVY)

    # stat line: rolling likes counter
    cp = ease_out_cubic((lf - 16) / 20)
    likes = int(card["likes"] * cp)
    sy2 = 1700
    sa = A(int(255 * clamp((lf - 11) / 7)))
    draw_heart(layer, 200, sy2 - 26, 52, accent, alpha=sa)
    d.text((280, sy2), f"{likes} LIKES", font=F(BLACK_F, 56), fill=WHITE + (sa,), anchor="lm")
    d.text((620, sy2), "// " + card["stat"], font=F(MONO_F, 40), fill=accent + (sa,), anchor="lm")

def sec_discourse(layer, lf, card):
    if 3 <= lf < 6:
        lf = 3.0
    d = ImageDraw.Draw(layer)
    ga = card_alpha(lf)
    A = lambda a=255: int(a * ga)
    pp = ease_out_back(lf / 8)
    d.text((W / 2, 130), "TODAY'S DISCOURSE", font=F(MONO_F, 44), fill=WHITE + (A(),), anchor="mm")
    s1 = fit_width(d, "GROUP CHAT", W - 300, 140)
    stamp_text(layer, W / 2, 250, "GROUP CHAT", int(s1 * (0.6 + 0.4 * pp)), WHITE, -2, alpha=A())
    s2 = fit_width(d, "ROYALE", W - 420, 150)
    stamp_text(layer, W / 2, 385, "ROYALE", int(s2 * (0.6 + 0.4 * pp)), YELLOW, 2,
               alpha=A(), outline=RED)

    starts = [10, 32, 54]
    tops = [660, 1060, 1460]
    cols = [CYAN, YELLOW, PINK]
    for i, ((handle, name, dmg, quote), start, top, col) in enumerate(
            zip(card["quotes"], starts, tops, cols)):
        if lf < start:
            continue
        p = ease_out_back((lf - start) / 8)
        a = int(255 * clamp((lf - start) / 4) * ga)
        # skewed band
        sk = 26
        band = Image.new("RGBA", (W, 380), (0, 0, 0, 0))
        bd = ImageDraw.Draw(band)
        bd.polygon([(0, 30 + sk), (W, 30 - sk), (W, 350 - sk), (0, 350 + sk)],
                   fill=(18, 24, 48, int(a * 0.85)), outline=col + (a,))
        layer.paste(band, (0, top - 190), band)
        # avatar flies in
        direction = 1 if i % 2 == 0 else -1
        tgt = 170
        ax = int((-260 if direction > 0 else W + 260) + (tgt - (-260 if direction > 0 else W + 260)) * p)
        sz = 220
        avt = circle_avatar(av(handle), sz)
        layer.paste(avt, (int(ax - sz / 2), int(top - sz / 2)), avt)
        draw_glow_ring(layer, ax, top, sz / 2, col, alpha=a)
        # smash-style damage percent
        stamp_text(layer, ax + 10, top + 130, f"{dmg}%", 58, RED, -5, alpha=a, outline=WHITE)
        d.text((330, top - 110), name, font=F(BLACK_F, 52), fill=col + (a,), anchor="lm")
        fq = F(BOLD_F, 41)
        ty = top - 40
        for line in wrap_text(d, sanitize(quote), fq, W - 420):
            d.text((330, ty), line, font=fq, fill=WHITE + (a,), anchor="lm")
            ty += 52
        # VS stamps between bands
        if i > 0 and lf >= start - 2:
            vsp = ease_out_back((lf - (start - 2)) / 6)
            stamp_text(layer, (W - 170) if i == 1 else 170, top - 205, "VS",
                       int(105 * vsp), YELLOW, -8 if i == 1 else 8,
                       alpha=int(255 * clamp((lf - start + 2) / 3) * ga), outline=RED)
    if lf >= 75:
        vp = ease_out_back((lf - 75) / 5)
        stamp_text(layer, W / 2, 960, "EVERYONE IS COOKED", int(fit_width(
            d, "EVERYONE IS COOKED", W - 120, 96) * vp), WHITE, -6,
            alpha=int(235 * clamp((lf - 75) / 2)), outline=RED)

def sec_outro(layer, lf):
    d = ImageDraw.Draw(layer)
    cx = W / 2
    if lf < FPBAR:  # ominous bar: tape-stop aftermath
        d.rectangle((0, 0, W, H), fill=(0, 0, 0, 90))
        a1 = int(255 * clamp((lf - 6) / 8))
        d.text((cx, 760), "see you tomorrow.", font=F(BLACK_F, 92), fill=WHITE + (a1,), anchor="mm")
        if lf >= 26:
            a2 = int(255 * clamp((lf - 26) / 6))
            # rgb-split glitch text
            d.text((cx - 5, 980), "hi.  — fable", font=F(BLACK_F, 64), fill=RED + (int(a2 * 0.7),), anchor="mm")
            d.text((cx + 5, 980), "hi.  — fable", font=F(BLACK_F, 64), fill=CYAN + (int(a2 * 0.7),), anchor="mm")
            d.text((cx, 980), "hi.  — fable", font=F(BLACK_F, 64), fill=WHITE + (a2,), anchor="mm")
    else:           # GG bar
        glf = lf - FPBAR
        pp = ease_out_back(glf / 7)
        sz = max(2, int(190 * pp))
        avt = circle_avatar("assets/avatar_cee.jpg", sz)
        layer.paste(avt, (int(cx - sz / 2), int(430 - sz / 2)), avt)
        draw_glow_ring(layer, cx, 430, sz / 2, BLUE, alpha=int(255 * clamp(glf / 5)))
        stamp_text(layer, cx, 850, "GG", int(330 * (0.5 + 0.5 * pp)), YELLOW, -8,
                   alpha=int(255 * clamp(glf / 3)), outline=RED)
        a3 = int(255 * clamp((glf - 8) / 6))
        stamp_text(layer, cx, 1130, "FINAL COMBO: 285 HITS", fit_width(
            d, "FINAL COMBO: 285 HITS", W - 160, 64), WHITE, 0, alpha=a3)
        a4 = int(200 * clamp((glf - 14) / 8))
        for i, line in enumerate(["all posts real / cee's mutuals / last 24h",
                                  "rendered by fable: numpy + pillow + ffmpeg",
                                  "music synthesized from scratch. yes really."]):
            d.text((cx, 1560 + i * 54), line, font=F(MONO_F, 36), fill=WHITE + (a4,), anchor="mm")

# ---------------- frame assembly ----------------
def section_accent(frame):
    if frame < COLD_END:
        return COLD_WORDS[min(3, int(frame / FPB))][1]
    if frame < STATS_END:
        return STAT_WORDS[min(3, int((frame - COLD_END) / FPB))][2]
    if frame < CARDS_END:
        idx = int((frame - STATS_END) // CARD_LEN)
        return CARDS[min(idx, 7)]["accent"]
    return RED if frame < GG_START else YELLOW

def render_frame(frame):
    accent = section_accent(frame)
    bg = background(frame, accent)

    in_cards = STATS_END <= frame < CARDS_END
    ci = int((frame - STATS_END) // CARD_LEN) if in_cards else -1
    lf = (frame - STATS_END) - ci * CARD_LEN if in_cards else 0

    if in_cards:
        draw_rays(bg, frame, accent)
        for img, y0, speed, direction in FLY.get(ci, []):
            x = int(-img.width + lf * speed * 1.6) if direction > 0 \
                else int(W - lf * speed * 1.6)
            bg.paste(img, (x, y0), img)
        draw_speed_lines(bg, lf, ci, accent)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if frame < COLD_END:
        sec_cold(layer, frame)
    elif frame < STATS_END:
        sec_stats(layer, frame - COLD_END)
    elif frame < CARDS_END:
        card = CARDS[min(ci, 7)]
        if card["kind"] == "discourse":
            sec_discourse(layer, lf, card)
        else:
            sec_card(layer, lf, card, ci)
    else:
        sec_outro(layer, frame - CARDS_END)

    ticker(layer, frame)
    combo_counter(layer, frame)
    progress(layer, frame)
    bg.paste(layer, (0, 0), layer)
    arr = np.asarray(bg).astype(np.float32)

    # ---- global FX ----
    since_beat = frame % FPB
    since_bar = frame % FPBAR
    groove = frame >= STATS_END - 2
    ominous = CARDS_END <= frame < GG_START

    # zoom: beat pulse + continuous push-in per section
    pulse = 0.030 * math.exp(-since_beat / 3.5) * (0.45 if frame < COLD_END else
                                                   0.2 if ominous else 1.0)
    if in_cards:
        pulse += 0.055 * (lf / CARD_LEN)            # ken-burns push within card
    elif frame < STATS_END:
        pulse += 0.10 * (since_beat / FPB)          # crash-zoom every beat
    beat_in_bar = int(since_bar / FPB)
    shake = 0
    if (groove and not ominous and beat_in_bar in (1, 3) and since_beat < 6) or frame < COLD_END:
        amp = 6 * math.exp(-since_beat / 2)
        if amp >= 1:
            shake = int(np.random.default_rng(frame).integers(-amp, amp + 1))
    if pulse > 0.002 or shake:
        s = 1 + max(0.0, pulse)
        nw, nh = int(W * s) + 2, int(H * s) + 2
        im = Image.fromarray(arr.astype(np.uint8)).resize((nw, nh), Image.BILINEAR)
        ox = max(0, min(nw - W, (nw - W) // 2 + shake))
        oy_ = max(0, min(nh - H, (nh - H) // 2 + shake // 2))
        arr = np.asarray(im.crop((ox, oy_, ox + W, oy_ + H))).astype(np.float32)

    # whip-pan at card boundaries: horizontal smear + slide
    for k, B in enumerate(WHIPS):
        df = frame - B
        if -3 <= df <= 3:
            stren = 1 - abs(df) / 3.6
            direction = 1 if k % 2 == 0 else -1
            arr = np.roll(arr, int(direction * stren * 110), axis=1)
            step = max(1, int(stren * 30))
            acc = arr.copy()
            for m in (1, 2, 3):
                acc += np.roll(arr, step * m, axis=1) + np.roll(arr, -step * m, axis=1)
            arr = acc / 7.0
            break

    # impact frames: white at boundary, inverted right after
    flash = 0.0
    for B in WHIPS + [GG_START]:
        df = frame - B
        if df == 1:
            arr = 255.0 - arr
        elif 0 <= df < 6:
            flash = max(flash, 0.45 * math.exp(-df / 1.5))
    if groove and not ominous and since_bar < 4:
        flash = max(flash, 0.10 * math.exp(-since_bar / 1.5))
    if frame < STATS_END and since_beat < 2:
        flash = max(flash, 0.25)

    # chromatic aberration: bar starts + constant light split during cards
    ca = 0
    if groove and since_bar < 5:
        ca = int(8 * math.exp(-since_bar / 1.8))
    elif in_cards:
        ca = 2
    if ca >= 1:
        arr[..., 0] = np.roll(arr[..., 0], ca, axis=1)
        arr[..., 2] = np.roll(arr[..., 2], -ca, axis=1)

    # VHS glitch: random row-band shears every ~2 bars
    if groove and int(frame) % 112 in (54, 55):
        g = np.random.default_rng(int(frame) // 112)
        for _ in range(7):
            y0 = int(g.integers(0, H - 24))
            hgt = int(g.integers(6, 26))
            arr[y0:y0 + hgt] = np.roll(arr[y0:y0 + hgt], int(g.integers(-60, 60)), axis=1)

    if flash > 0.01:
        arr = arr * (1 - flash) + 255 * flash

    arr *= VIGNETTE
    arr += grain_rng.standard_normal((H, W, 1)).astype(np.float32) * 3.5
    np.clip(arr, 0, 255, out=arr)
    return arr.astype(np.uint8)

# ---------------- main ----------------
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        for fs in sys.argv[2:]:
            fr = int(fs)
            Image.fromarray(render_frame(fr)).save(f"preview_{fr}.png")
            print(f"preview_{fr}.png")
        sys.exit(0)

    cmd = ["ffmpeg", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", "music.wav",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
           "recap.mp4"]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for fr in range(FRAMES):
        proc.stdin.write(render_frame(fr).tobytes())
        if fr % 90 == 0:
            print(f"{fr}/{FRAMES}")
    proc.stdin.close()
    proc.wait()
    print("recap.mp4 done, exit", proc.returncode)
