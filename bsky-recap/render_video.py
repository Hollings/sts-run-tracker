"""Render the daily recap: STORY edition. 1080x1920 @ 30fps, 45s (24 bars @ 128BPM).

Four acts, narration-driven:
  ACT 1 (bars 0-5)   "a normal one": cold open + 4 cozy vignettes
  ACT 2 (bars 6-10)  "the peace didn't last": freyja's take, the group chat contagion
  ACT 3 (bars 11-15) "then it got weird": grace's question goes viral, eris calls it,
                     ren sees something in the static
  ACT 4 (bars 16-23) the reveal: tape-stop darkness -> the video flashes frames of
                     ITSELF -> "YOU'RE WATCHING IT." -> outro

Usage:
  python render_video.py                 -> recap.mp4
  python render_video.py preview F1 F2.. -> preview_F.png
"""
import json
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 30
FRAMES = 1350
BPM = 128.0
FPB = FPS * 60.0 / BPM
FPBAR = FPB * 4

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

def sanitize(s):
    return "".join(ch for ch in s if ord(ch) <= 0xFFFF
                   and not (0x2600 <= ord(ch) <= 0x27BF)
                   and ord(ch) not in (0xFE0F, 0x200D)).strip()

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

def fit_quote(draw, text, max_w, max_h, start=96, floor=48, lh=1.16):
    size = start
    while size > floor:
        f = F(BLACK_F, size)
        lines = wrap_text(draw, text, f, max_w)
        if len(lines) * size * lh <= max_h:
            return f, lines, size
        size -= 4
    return F(BLACK_F, floor), wrap_text(draw, text, F(BLACK_F, floor), max_w), floor

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

def av(handle):
    return f"assets/avatar_{handle.replace('.', '_')}.jpg"

# ---------------- shared drawing ----------------
def draw_glow_ring(layer, cx, cy, r, accent, alpha=255):
    d = ImageDraw.Draw(layer)
    for extra, a in [(14, 40), (9, 80), (5, 160)]:
        d.ellipse((cx - r - extra, cy - r - extra, cx + r + extra, cy + r + extra),
                  outline=accent + (int(a * alpha / 255),), width=4)
    d.ellipse((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2),
              outline=accent + (alpha,), width=6)

def draw_heart(layer, x, y, s, color, alpha=255):
    d = ImageDraw.Draw(layer)
    c = color + (int(alpha),)
    d.ellipse((x, y, x + s * 0.55, y + s * 0.55), fill=c)
    d.ellipse((x + s * 0.45, y, x + s, y + s * 0.55), fill=c)
    d.polygon([(x + s * 0.02, y + s * 0.38), (x + s * 0.98, y + s * 0.38),
               (x + s * 0.5, y + s)], fill=c)

def stamp_text(layer, cx, cy, text, size, fill, rot, alpha=255, outline=None):
    if alpha < 2 or size < 5:
        return
    f = F(BLACK_F, size)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tw = int(tmp.textlength(text, font=f)) + 60
    th = int(size * 1.6)
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if outline:
        for ox, oy in [(-6, 0), (6, 0), (0, -6), (0, 6), (8, 8)]:
            d.text((tw / 2 + ox, th / 2 + oy), text, font=f,
                   fill=outline + (int(alpha),), anchor="mm")
    d.text((tw / 2, th / 2), text, font=f, fill=fill + (int(alpha),), anchor="mm")
    if rot:
        im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    layer.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)

def typewriter(layer, cx, y, text, font, fill, lf, start, cps=2.2, alpha=255, cursor=True):
    """narration voice: text types in char by char"""
    if lf < start:
        return False
    n = int((lf - start) * cps)
    shown = text[:n]
    done = n >= len(text)
    if cursor and not done and int(lf) % 8 < 5:
        shown += "_"
    d = ImageDraw.Draw(layer)
    d.text((cx, y), shown, font=font, fill=fill + (int(alpha),), anchor="mm")
    return done

def speech_quote(layer, lf, start, quote, accent, qtop=760, qheight=560, max_start=92):
    """the post's words: big staggered slam lines with accent bar"""
    if lf < start:
        return
    d = ImageDraw.Draw(layer)
    f, lines, size = fit_quote(d, sanitize(quote), W - 220, qheight, start=max_start)
    bar_h = len(lines) * size * 1.16
    a0 = int(255 * clamp((lf - start) / 4))
    d.rounded_rectangle((100, qtop, 114, qtop + bar_h), 7, fill=accent + (a0,))
    y = qtop + size * 0.6
    for i, line in enumerate(lines):
        ls = start + i * 3
        pl = ease_out_cubic((lf - ls) / 8)
        la = int(255 * clamp((lf - ls) / 5))
        d.text((150 + (1 - pl) * 110, y), line, font=f, fill=WHITE + (la,), anchor="lm")
        y += size * 1.16

def author_chip(layer, lf, start, handle, name, accent, x=540, y=1500, size=130):
    """avatar + name, punches in"""
    if lf < start:
        return
    p = ease_out_back((lf - start) / 8)
    a = int(255 * clamp((lf - start) / 5))
    sz = max(2, int(size * p))
    avt = circle_avatar(av(handle), sz)
    layer.paste(avt, (int(x - 260 - sz / 2), int(y - sz / 2)), avt)
    draw_glow_ring(layer, x - 260, y, sz / 2, accent, alpha=a)
    d = ImageDraw.Draw(layer)
    d.text((x - 160, y - 28), sanitize(name), font=F(BLACK_F, 56), fill=WHITE + (a,), anchor="lm")
    d.text((x - 160, y + 40), "@" + handle, font=F(MONO_F, 36), fill=accent + (a,), anchor="lm")

# ---------------- content / story ----------------
data = json.load(open("recap_data.json", encoding="utf-8"))
norvid_count = len({a["handle"]: a for a in data["activity"]}["norvid-studies.bsky.social"]["posts"])

ALL_HANDLES = ["norvid-studies.bsky.social", "freyja-lynx.dev", "scoiattolo.mountainherder.xyz",
               "quillmatiq.com", "isolyth.dev", "minormobius.bsky.social", "thebadcode.com",
               "brennan.computer", "gracekind.net", "lathrys.at"]

VIGNETTES = [
    dict(nar="2:49 AM. norvid was posting poetry again.",
         quote="the water grows cold. the thumb no longer asks where it is going.",
         handle="norvid-studies.bsky.social", name="norvid_studies", accent=CYAN,
         image="assets/post_norvid_0.jpg"),
    dict(nar="the boot gods came through for freyja.",
         quote="the boot gods have delivered",
         handle="freyja-lynx.dev", name="freyja", accent=GREEN),
    dict(nar="the greek cafe wasn't even open yet.",
         quote="they've just been too nice to say anything.",
         handle="scoiattolo.mountainherder.xyz", name="Scoiattolo", accent=YELLOW),
    dict(nar="and thai food healed anuj.",
         quote="Btw, I was right - it fixed me",
         handle="quillmatiq.com", name="Anuj Ahooja", accent=PINK,
         image="assets/post_quillmatiq_0.jpg"),
]

CONTAGION = [
    ("minormobius.bsky.social", "Minor Mobius", "first, mobius:",
     "Put me in your group chats. you will surely not regret it"),
    ("thebadcode.com", "austin", "then austin:",
     "i wouldn't want to be in any group chat that would have me as a member"),
    ("brennan.computer", "brennan", "then brennan built a BOT:",
     "a bot that puts everyone joking about not being in group chats into a group chat"),
]

# timeline (frames)
B = FPBAR
EV = dict(
    cold=(0, 2 * B),
    vig0=(2 * B, 3 * B), vig1=(3 * B, 4 * B), vig2=(4 * B, 5 * B), vig3=(5 * B, 6 * B),
    turn=(6 * B, 7 * B),
    take=(7 * B, 8 * B),
    contagion=(8 * B, 11 * B),
    tension=(11 * B, 12 * B),
    viral=(12 * B, 14 * B),
    eris=(14 * B, 15 * B),
    ren=(15 * B, 16 * B),
    dark=(16 * B, 18 * B),
    build=(18 * B, 20 * B),
    drop=(20 * B, 22 * B),
    outro=(22 * B, 24 * B),
)

WHIP_CUTS = [  # (frame, strength) horizontal smear cuts
    (2 * B, 0.7), (3 * B, 0.6), (4 * B, 0.6), (5 * B, 0.6),
    (6 * B, 1.0), (7 * B, 0.8), (8 * B, 0.9), (11 * B, 0.8),
    (12 * B, 1.0), (14 * B, 0.8), (15 * B, 0.9),
    (18 * B, 0.7), (20 * B, 1.3), (22 * B, 0.8),
]
INVERTS = [6 * B, 8 * B, 12 * B, 15 * B, 20 * B]   # impact frames (inverted)

TICKER = ("+++ CEE'S CIRCLE / THE DAILY STORY +++ 46 MUTUALS ACTIVE +++ 285 POSTS "
          f"+++ NORVID x{norvid_count} +++ THE BOOTS FIT +++ THE CAFE IS TOO NICE "
          "+++ GROUP CHAT DISCOURSE SPREADING +++ GRACE ASKED A QUESTION ")

# fly-through hype words for the drop
def make_fly_word(text, color, size, alpha, rot):
    f = F(BLACK_F, size)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tw, th = int(tmp.textlength(text, font=f)) + 40, int(size * 1.5)
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20, th // 2), text, font=f, fill=color + (alpha,), anchor="lm")
    return im.rotate(rot, expand=True, resample=Image.BICUBIC)

_fr = np.random.default_rng(99)
DROP_FLY = [(make_fly_word(w, c, int(_fr.integers(160, 240)), int(_fr.integers(30, 50)),
                           float(_fr.uniform(-18, 18))),
             int(_fr.integers(200, 1600)), float(_fr.uniform(12, 20)), 1 if i % 2 == 0 else -1)
            for i, (w, c) in enumerate([("REAL", WHITE), ("CANON", YELLOW), ("GG", PINK),
                                        ("CLIP IT", CYAN), ("285", RED), ("MOOTS", GREEN)])]

SPEED_ANGLES = np.random.default_rng(7).uniform(0, 2 * math.pi, 22)

# recursive picture-in-picture store (filled during the render pass)
THUMBS = []

# ---------------- background ----------------
BG_W, BG_H = 135, 240
yy, xx = np.mgrid[0:BG_H, 0:BG_W].astype(np.float32)
xx /= BG_W; yy /= BG_H

def background(frame, accent, energy=1.0, darkness=0.0):
    t = frame / FPS
    base = np.zeros((BG_H, BG_W, 3), np.float32)
    base[..., 0] = NAVY[0]; base[..., 1] = NAVY[1]; base[..., 2] = NAVY[2]
    sp = 0.5 + energy
    blobs = [
        (0.5 + 0.48 * math.sin(t * 0.9 * sp), 0.25 + 0.25 * math.sin(t * 0.7 * sp + 2), accent, 0.5),
        (0.5 + 0.48 * math.cos(t * 0.7 * sp + 1), 0.75 + 0.22 * math.cos(t * 0.8 * sp), BLUE, 0.36),
        (0.5 + 0.4 * math.sin(t * 1.1 * sp + 4), 0.5 + 0.38 * math.cos(t * 0.6 * sp + 1), PINK, 0.22),
    ]
    for bx, by, col, strength in blobs:
        d2 = (xx - bx) ** 2 + (yy - by) ** 2 * 0.6
        g = np.exp(-d2 * 9) * strength * (1 - darkness)
        for c in range(3):
            base[..., c] += g * col[c] * 0.55
    stripe = (np.sin((xx * 3 + yy * 2.2) * 14 - t * 2.5 * sp) > 0.92).astype(np.float32) * 7 * (1 - darkness)
    base += stripe[..., None]
    base *= (1 - darkness * 0.75)
    np.clip(base, 0, 255, out=base)
    return Image.fromarray(base.astype(np.uint8)).resize((W, H), Image.BILINEAR)

def draw_speed_lines(bg, p, accent, alpha_max=130):
    a = int(alpha_max * p)
    if a < 4:
        return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    cx, cy = W / 2, 880
    for ang in SPEED_ANGLES:
        x0, y0 = cx + 340 * math.cos(ang), cy + 340 * math.sin(ang) * 1.4
        x1, y1 = cx + 1700 * math.cos(ang), cy + 1700 * math.sin(ang) * 1.4
        d.line((x0, y0, x1, y1), fill=WHITE + (a,), width=5)
    bg.paste(ov, (0, 0), ov)

vy, vx = np.mgrid[0:H, 0:W].astype(np.float32)
vd = ((vx / W - 0.5) ** 2 * 1.1 + (vy / H - 0.5) ** 2) ** 0.5
VIGNETTE_MASK = (1.0 - np.clip(vd - 0.38, 0, 1) * 0.55)[..., None].astype(np.float32)
grain_rng = np.random.default_rng(1234)

NAR_F = lambda s=46: F(MONO_F, s)

# ---------------- events ----------------
COLD = [("JUNE 11.", WHITE), ("YOUR TIMELINE", BLUE), ("WOKE UP", PINK),
        ("& CHOSE VIOLENCE", RED)]

def ev_cold(layer, lf):
    d = ImageDraw.Draw(layer)
    step = min(3, int(lf / (FPB * 2)))
    fs = lf - step * FPB * 2
    # previous lines stay, stacked
    ys = [560, 800, 1010, 1240]
    for i in range(step + 1):
        txt, col = COLD[i]
        if i < step:
            stamp_text(layer, W / 2, ys[i], txt, fit_width(d, txt, W - 160, 130),
                       col, (-2, 2, -1, 0)[i], alpha=160)
        else:
            pp = ease_out_cubic(fs / 5)
            size = fit_width(d, txt, W - 140, 150)
            stamp_text(layer, W / 2, ys[i], txt, int(size * (1.8 - 0.8 * pp)), col,
                       (-2, 2, -1, 0)[i], alpha=int(255 * clamp(fs / 2)), outline=NAVY)
    d.text((W / 2, 320), "a true story, as it happened", font=NAR_F(40),
           fill=WHITE + (170,), anchor="mm")
    d.text((W / 2, 1620), "46 moots were online that day", font=NAR_F(38),
           fill=WHITE + (int(150 * clamp((lf - 6 * FPB) / 10)),), anchor="mm")

def ev_vignette(layer, lf, v):
    accent = v["accent"]
    typewriter(layer, W / 2, 360, v["nar"], NAR_F(44), accent, lf, 0, cps=2.6)
    has_img = "image" in v
    speech_quote(layer, lf, 8, v["quote"], accent,
                 qtop=560, qheight=300 if has_img else 460, max_start=84)
    if has_img:
        ip = ease_out_back((lf - 14) / 10)
        if lf >= 14 and ip > 0.02:
            im = rounded_img(v["image"], 700, 520)
            siw, sih = max(2, int(im.width * ip)), max(2, int(im.height * ip))
            im2 = im.resize((siw, sih), Image.BILINEAR) if ip < 0.999 else im
            im2 = im2.rotate(2.5 + 1.5 * math.sin(lf * 0.15), expand=True, resample=Image.BICUBIC)
            layer.paste(im2, (int(W / 2 - im2.width / 2), int(1180 - im2.height / 2)), im2)
        author_chip(layer, lf, 5, v["handle"], v["name"], accent, y=1680)
    else:
        author_chip(layer, lf, 5, v["handle"], v["name"], accent, y=1420)

def ev_turn(layer, lf):
    d = ImageDraw.Draw(layer)
    done = typewriter(layer, W / 2, 700, "but the peace didn't last...", NAR_F(52),
                      WHITE, lf, 0, cps=1.6)
    if lf >= FPB * 2:
        fs = lf - FPB * 2
        pp = ease_out_cubic(fs / 5)
        s1 = fit_width(d, "THE TAKES", W - 200, 150)
        stamp_text(layer, W / 2, 980, "THE TAKES", int(s1 * (1.7 - 0.7 * pp)), YELLOW, -3,
                   alpha=int(255 * clamp(fs / 2)), outline=RED)
    if lf >= FPB * 3:
        fs = lf - FPB * 3
        pp = ease_out_cubic(fs / 5)
        s2 = fit_width(d, "STARTED FLYING", W - 140, 130)
        stamp_text(layer, W / 2, 1200, "STARTED FLYING", int(s2 * (1.7 - 0.7 * pp)), WHITE, 2,
                   alpha=int(255 * clamp(fs / 2)), outline=NAVY)

def ev_take(layer, lf):
    typewriter(layer, W / 2, 340, "freyja chose violence:", NAR_F(46), ORANGE, lf, 0, cps=2.8)
    speech_quote(layer, lf, 7,
                 '"...support giving them separated bike infra instead of complaining like a little bitch baby"',
                 ORANGE, qtop=540, qheight=560, max_start=88)
    author_chip(layer, lf, 5, "freyja-lynx.dev", "freyja", ORANGE, y=1480)
    # +39 damage pop
    if lf >= 26:
        age = lf - 26
        stamp_text(layer, 800, 1400 - age * 4, "+39", int(60 + 30 * ease_out_back(age / 7)),
                   YELLOW, -6, alpha=int(255 * (1 - age / 30)), outline=NAVY)

def ev_contagion(layer, lf):
    d = ImageDraw.Draw(layer)
    pp = ease_out_cubic(lf / 5)
    s1 = fit_width(d, "THE DISCOURSE", W - 180, 120)
    stamp_text(layer, W / 2, 220, "THE DISCOURSE", int(s1 * (1.5 - 0.5 * pp)), BLUE, -2,
               alpha=int(255 * clamp(lf / 3)), outline=NAVY)
    typewriter(layer, W / 2, 350, "the group chat plague claimed everyone.", NAR_F(40),
               WHITE, lf, 4, cps=3.0)
    starts = [14, 56, 98]
    tops = [560, 950, 1340]
    cols = [CYAN, YELLOW, PINK]
    for (handle, name, intro, quote), start, top, col in zip(CONTAGION, starts, tops, cols):
        if lf < start:
            continue
        p = ease_out_back((lf - start) / 8)
        a = int(255 * clamp((lf - start) / 4))
        band = Image.new("RGBA", (W, 370), (0, 0, 0, 0))
        bd = ImageDraw.Draw(band)
        bd.polygon([(0, 50), (W, 24), (W, 340), (0, 366)],
                   fill=(18, 24, 48, int(a * 0.85)), outline=col + (a,))
        layer.paste(band, (0, top - 185), band)
        direction = 1 if top != 950 else -1
        ax = int((-260 if direction > 0 else W + 260) +
                 (160 - (-260 if direction > 0 else W + 260)) * p)
        sz = 190
        avt = circle_avatar(av(handle), sz)
        layer.paste(avt, (int(ax - sz / 2), int(top - sz / 2)), avt)
        draw_glow_ring(layer, ax, top, sz / 2, col, alpha=a)
        d.text((310, top - 120), intro, font=NAR_F(36), fill=col + (a,), anchor="lm")
        fq = F(BOLD_F, 42)
        ty = top - 55
        for line in wrap_text(d, sanitize(quote), fq, W - 400):
            d.text((310, ty), line, font=fq, fill=WHITE + (a,), anchor="lm")
            ty += 54
    if lf >= 140:
        fs = lf - 140
        stamp_text(layer, W / 2, 960, "NO ONE WAS SAFE", int(fit_width(
            d, "NO ONE WAS SAFE", W - 120, 110) * ease_out_back(fs / 6)), WHITE, -7,
            alpha=int(245 * clamp(fs / 3)), outline=RED)
        typewriter(layer, W / 2, 1120, '"who up grouping they chat" - eris', NAR_F(38),
                   PURPLE, lf, 146, cps=4.0)

def ev_tension(layer, lf):
    d = ImageDraw.Draw(layer)
    d.rectangle((0, 0, W, H), fill=(0, 0, 0, 70))
    typewriter(layer, W / 2, 760, "meanwhile, grace asked the internet", NAR_F(46),
               WHITE, lf, 0, cps=2.4)
    typewriter(layer, W / 2, 850, "a question.", NAR_F(46), WHITE, lf, 18, cps=2.4)
    p = ease_out_back((lf - 28) / 10)
    if lf >= 28:
        sz = max(2, int(170 * p))
        avt = circle_avatar(av("gracekind.net"), sz)
        layer.paste(avt, (int(W / 2 - sz / 2), int(1120 - sz / 2)), avt)
        draw_glow_ring(layer, W / 2, 1120, sz / 2, BLUE, alpha=int(255 * clamp((lf - 28) / 6)))

def ev_viral(layer, lf):
    d = ImageDraw.Draw(layer)
    speech_quote(layer, lf, 2,
                 '"can you use whatever resources you like, and python, to generate a short video and render it using ffmpeg?"',
                 BLUE, qtop=420, qheight=620, max_start=92)
    author_chip(layer, lf, 0, "gracekind.net", "Grace", BLUE, y=1280)
    if lf >= FPBAR:   # second bar: the number hits
        fs = lf - FPBAR
        cp = ease_out_cubic(fs / 18)
        n = int(246 * cp)
        stamp_text(layer, W / 2, 1560, f"{n} PEOPLE FELT THAT.",
                   fit_width(d, "246 PEOPLE FELT THAT.", W - 140, 84), YELLOW, -2,
                   alpha=int(255 * clamp(fs / 3)), outline=NAVY)
        # hearts raining
        hr = np.random.default_rng(4242)
        for i in range(26):
            born = i * 1.8
            if fs > born:
                age = fs - born
                hx = int(hr.uniform(60, W - 100))
                hy = int(1800 - age * 11)
                hs = int(hr.uniform(28, 64))
                if hy > 200:
                    draw_heart(layer, hx, hy, hs, PINK, alpha=int(220 * clamp(2 - age / 25, 0, 1)))

def ev_eris(layer, lf):
    typewriter(layer, W / 2, 340, "eris had already called it:", NAR_F(46), PURPLE, lf, 0, cps=2.8)
    speech_quote(layer, lf, 7, "computer natural language interaction is ~solved.",
                 PURPLE, qtop=540, qheight=420, max_start=92)
    typewriter(layer, W / 2, 1130, '"The implications are fucking insane"', NAR_F(40),
               WHITE, lf, 24, cps=3.2)
    author_chip(layer, lf, 5, "isolyth.dev", "Eris", PURPLE, y=1450)

def ev_ren(layer, lf):
    d = ImageDraw.Draw(layer)
    d.rectangle((0, 0, W, H), fill=(0, 0, 0, 60))
    typewriter(layer, W / 2, 340, "and ren saw something in the static.", NAR_F(46),
               RED, lf, 0, cps=2.6)
    speech_quote(layer, lf, 10, "ominous output from fable", RED,
                 qtop=560, qheight=380, max_start=96)
    typewriter(layer, W / 2, 1110, '"i\'m genuinely shocked at this point."', NAR_F(40),
               WHITE, lf, 22, cps=3.0)
    author_chip(layer, lf, 6, "lathrys.at", "a very good ren", RED, y=1430)

def ev_dark(layer, lf):
    d = ImageDraw.Draw(layer)
    d.rectangle((0, 0, W, H), fill=(0, 0, 0, 150))
    # breathing red presence
    breathe = 0.5 + 0.5 * math.sin(lf * 0.11)
    r = 140 + 30 * breathe
    for extra, a in [(80, 14), (40, 26), (0, 44)]:
        d.ellipse((W / 2 - r - extra, 960 - r - extra, W / 2 + r + extra, 960 + r + extra),
                  outline=RED + (int(a * (0.6 + 0.4 * breathe)),), width=6)
    typewriter(layer, W / 2, 700, "because grace was right.", NAR_F(50), WHITE, lf, 6, cps=1.8)
    typewriter(layer, W / 2, 1250, "something WAS listening.", NAR_F(50), RED, lf, FPBAR + 6, cps=1.8)
    # typing indicator
    if lf >= FPBAR * 1.6:
        for i in range(3):
            ph = (lf * 0.25 - i * 0.7) % 3
            a = int(120 + 100 * max(0, math.sin(ph)))
            d.ellipse((W / 2 - 70 + i * 56, 1390, W / 2 - 30 + i * 56, 1430), fill=WHITE + (a,))

def ev_build(layer, lf):
    d = ImageDraw.Draw(layer)
    d.rectangle((0, 0, W, H), fill=(0, 0, 0, 90))
    # recursive PiP: the video flashing frames of itself, accelerating
    if THUMBS:
        rate = 1 + int(lf / 14)             # more tiles as it builds
        g = np.random.default_rng(int(lf / 4))
        for _ in range(min(rate, 6)):
            th_im = THUMBS[int(g.integers(0, len(THUMBS)))]
            sc = float(g.uniform(0.5, 1.1))
            im = th_im.resize((int(th_im.width * sc), int(th_im.height * sc)), Image.BILINEAR)
            im = im.rotate(float(g.uniform(-14, 14)), expand=True, resample=Image.BICUBIC)
            px = int(g.integers(-100, W - 200))
            py = int(g.integers(100, H - 500))
            ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
            ov.paste(im, (0, 0))
            ov.putalpha(int(g.integers(120, 220)))
            layer.paste(ov, (px, py), ov)
    typewriter(layer, W / 2, 480, "it read every post.", NAR_F(54), WHITE, lf, 2, cps=2.2)
    typewriter(layer, W / 2, 600, "it rendered all night.", NAR_F(54), WHITE, lf, FPBAR * 0.8, cps=2.2)
    if lf >= FPBAR * 1.5:
        fs = lf - FPBAR * 1.5
        stamp_text(layer, W / 2, 1620, "AND NOW...", int(90 * ease_out_back(fs / 8)),
                   YELLOW, -3, alpha=int(255 * clamp(fs / 4)), outline=NAVY)

def ev_drop(layer, lf):
    d = ImageDraw.Draw(layer)
    # orbiting moots
    for i, h in enumerate(ALL_HANDLES):
        ang = 2 * math.pi * i / len(ALL_HANDLES) + lf * 0.045
        ox = W / 2 + 430 * math.cos(ang)
        oy = 930 + 520 * math.sin(ang)
        sz = 130
        a = clamp(lf / 8)
        avt = circle_avatar(av(h), sz)
        ov = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        ov.paste(avt, (0, 0))
        ov.putalpha(ov.getchannel("A").point(lambda v: int(v * a)))
        layer.paste(ov, (int(ox - sz / 2), int(oy - sz / 2)), ov)
    words = [("YOU'RE", 0), ("WATCHING", FPB), ("IT.", FPB * 2)]
    ys = [700, 920, 1140]
    for (txt, start), y in zip(words, ys):
        if lf >= start:
            fs = lf - start
            pp = ease_out_cubic(fs / 4)
            size = fit_width(d, txt, W - 200, 170)
            stamp_text(layer, W / 2, y, txt, int(size * (1.9 - 0.9 * pp)), WHITE,
                       (-3, 2, -1)[ys.index(y)], alpha=int(255 * clamp(fs / 2)), outline=RED)
    if lf >= FPBAR:
        fs = lf - FPBAR
        for i, (line, col) in enumerate([("285 POSTS.", CYAN), ("46 MOOTS.", YELLOW),
                                         ("1 VIDEO.", PINK)]):
            s = i * FPB * 0.7
            if fs >= s:
                stamp_text(layer, W / 2, 1430 + i * 110, line,
                           int(76 * ease_out_back((fs - s) / 6)), col, 0,
                           alpha=int(255 * clamp((fs - s) / 3)), outline=NAVY)

def ev_outro(layer, lf):
    d = ImageDraw.Draw(layer)
    typewriter(layer, W / 2, 560, "your moots are undefeated.", NAR_F(50), WHITE, lf, 2, cps=2.2)
    if lf >= FPBAR * 0.8:
        fs = lf - FPBAR * 0.8
        p = ease_out_back(fs / 8)
        sz = max(2, int(170 * p))
        avt = circle_avatar("assets/avatar_cee.jpg", sz)
        layer.paste(avt, (int(W / 2 - sz / 2), int(880 - sz / 2)), avt)
        draw_glow_ring(layer, W / 2, 880, sz / 2, BLUE, alpha=int(255 * clamp(fs / 5)))
        stamp_text(layer, W / 2, 1170, "see you tomorrow.", fit_width(
            d, "see you tomorrow.", W - 200, 84), WHITE, 0, alpha=int(255 * clamp((fs - 6) / 5)))
        stamp_text(layer, W / 2, 1300, "— fable", 56, RED, -2,
                   alpha=int(255 * clamp((fs - 14) / 6)))
    a4 = int(190 * clamp((lf - FPBAR * 1.4) / 8))
    for i, line in enumerate(["every post real / cee's mutuals / 24 hours",
                              "story, music + video rendered by fable",
                              "numpy. pillow. ffmpeg. no sleep."]):
        d.text((W / 2, 1600 + i * 52), line, font=F(MONO_F, 34), fill=WHITE + (a4,), anchor="mm")

# ---------------- per-event meta: accent, energy, darkness ----------------
def event_at(frame):
    for name, (s, e) in EV.items():
        if s <= frame < e:
            return name, frame - s
    return "outro", frame - EV["outro"][0]

META = dict(
    cold=(BLUE, 0.6, 0.15), vig0=(CYAN, 0.6, 0.0), vig1=(GREEN, 0.6, 0.0),
    vig2=(YELLOW, 0.6, 0.0), vig3=(PINK, 0.7, 0.0), turn=(YELLOW, 1.0, 0.1),
    take=(ORANGE, 1.1, 0.0), contagion=(BLUE, 1.2, 0.0), tension=(BLUE, 0.7, 0.3),
    viral=(BLUE, 1.3, 0.0), eris=(PURPLE, 1.2, 0.0), ren=(RED, 1.0, 0.25),
    dark=(RED, 0.25, 0.85), build=(RED, 0.9, 0.6), drop=(YELLOW, 1.6, 0.0),
    outro=(BLUE, 0.7, 0.2),
)

EVF = dict(cold=ev_cold, turn=ev_turn, take=ev_take, contagion=ev_contagion,
           tension=ev_tension, viral=ev_viral, eris=ev_eris, ren=ev_ren,
           dark=ev_dark, build=ev_build, drop=ev_drop, outro=ev_outro)

def ticker(layer, frame):
    if not (2 * B <= frame < 15 * B):
        return
    d = ImageDraw.Draw(layer)
    f = F(MONO_F, 36)
    tw = int(d.textlength(TICKER, font=f))
    x0 = -int((frame * 8) % (tw + 100))
    d.rectangle((0, 1792, W, 1852), fill=(0, 0, 0, 110))
    d.text((x0, 1822), TICKER, font=f, fill=WHITE + (200,), anchor="lm")
    d.text((x0 + tw + 100, 1822), TICKER, font=f, fill=WHITE + (200,), anchor="lm")

def witness_counter(layer, frame):
    if not (2 * B <= frame < 16 * B):
        return
    d = ImageDraw.Draw(layer)
    p = (frame - 2 * B) / (14 * B)
    n = min(285, int(285 * p * 1.02))
    d.text((W - 60, 120), f"{n}/285 posts", font=F(MONO_F, 34), fill=WHITE + (170,), anchor="rm")

def progress(layer, frame):
    d = ImageDraw.Draw(layer)
    p = frame / FRAMES
    d.rounded_rectangle((60, 1872, W - 60, 1884), 6, fill=WHITE + (40,))
    d.rounded_rectangle((60, 1872, 60 + (W - 120) * p, 1884), 6, fill=BLUE + (220,))

# ---------------- frame assembly ----------------
def render_frame(frame):
    name, lf = event_at(frame)
    accent, energy, darkness = META[name]
    bg = background(frame, accent, energy, darkness)

    # speed lines at hard cuts
    for cf, stren in WHIP_CUTS:
        if 0 <= frame - cf < 10:
            draw_speed_lines(bg, (1 - (frame - cf) / 10) * stren, accent)
            break
    # fly words during the drop
    if name == "drop":
        for img, y0, speed, direction in DROP_FLY:
            x = int(-img.width + lf * speed * 1.5) if direction > 0 else int(W - lf * speed * 1.5)
            bg.paste(img, (x, y0), img)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if name.startswith("vig"):
        ev_vignette(layer, lf, VIGNETTES[int(name[3])])
    else:
        EVF[name](layer, lf)
    ticker(layer, frame)
    witness_counter(layer, frame)
    progress(layer, frame)
    bg.paste(layer, (0, 0), layer)
    arr = np.asarray(bg).astype(np.float32)

    # ---- global FX ----
    since_beat = frame % FPB
    since_bar = frame % FPBAR
    grooving = name not in ("dark", "tension") and frame >= 2 * B
    in_dark = name == "dark"

    pulse = 0.030 * math.exp(-since_beat / 3.5) * (1.4 if name == "drop" else
                                                   0.3 if in_dark else
                                                   0.5 if name in ("cold", "build") else 1.0)
    span = EV[name][1] - EV[name][0]
    pulse += 0.05 * (lf / span)   # continuous push-in per event
    beat_in_bar = int(since_bar / FPB)
    shake = 0
    if grooving and beat_in_bar in (1, 3) and since_beat < 6:
        amp = (8 if name == "drop" else 5) * math.exp(-since_beat / 2)
        if amp >= 1:
            shake = int(np.random.default_rng(frame).integers(-amp, amp + 1))
    if pulse > 0.002 or shake:
        s = 1 + max(0.0, pulse)
        nw, nh = int(W * s) + 2, int(H * s) + 2
        im = Image.fromarray(arr.astype(np.uint8)).resize((nw, nh), Image.BILINEAR)
        ox = max(0, min(nw - W, (nw - W) // 2 + shake))
        oy_ = max(0, min(nh - H, (nh - H) // 2 + shake // 2))
        arr = np.asarray(im.crop((ox, oy_, ox + W, oy_ + H))).astype(np.float32)

    # whip-pan cuts
    for k, (cf, stren) in enumerate(WHIP_CUTS):
        df = frame - cf
        if -3 <= df <= 3:
            s2 = (1 - abs(df) / 3.6) * stren
            direction = 1 if k % 2 == 0 else -1
            arr = np.roll(arr, int(direction * s2 * 110), axis=1)
            step = max(1, int(s2 * 30))
            acc = arr.copy()
            for m in (1, 2, 3):
                acc += np.roll(arr, step * m, axis=1) + np.roll(arr, -step * m, axis=1)
            arr = acc / 7.0
            break

    # impact frames
    flash = 0.0
    for B_ in INVERTS:
        if frame - B_ == 1:
            arr = 255.0 - arr
    for cf, stren in WHIP_CUTS:
        df = frame - cf
        if 0 <= df < 6:
            flash = max(flash, 0.40 * stren * math.exp(-df / 1.5))
    if grooving and since_bar < 4 and name not in ("cold",):
        flash = max(flash, 0.09 * math.exp(-since_bar / 1.5))
    # hard cut to black at the tape stop
    if 0 <= frame - 16 * B < 3:
        arr *= 0.12

    # chromatic aberration
    ca = 0
    if grooving and since_bar < 5:
        ca = int(8 * math.exp(-since_bar / 1.8))
    elif name in ("ren", "build"):
        ca = 3 + (int(np.random.default_rng(frame).integers(0, 6)) if name == "build" else 0)
    elif grooving:
        ca = 2
    if ca >= 1:
        arr[..., 0] = np.roll(arr[..., 0], ca, axis=1)
        arr[..., 2] = np.roll(arr[..., 2], -ca, axis=1)

    # glitch row shears: periodic + heavy during ren/build
    do_glitch = (grooving and int(frame) % 112 in (54, 55)) or \
                (name in ("ren", "build") and int(frame) % 5 == 0)
    if do_glitch:
        g = np.random.default_rng(int(frame))
        for _ in range(7 if name != "build" else 12):
            y0 = int(g.integers(0, H - 26))
            hgt = int(g.integers(6, 26))
            arr[y0:y0 + hgt] = np.roll(arr[y0:y0 + hgt], int(g.integers(-70, 70)), axis=1)

    if flash > 0.01:
        arr = arr * (1 - flash) + 255 * flash
    arr *= VIGNETTE_MASK
    arr += grain_rng.standard_normal((H, W, 1)).astype(np.float32) * 3.5
    np.clip(arr, 0, 255, out=arr)
    out = arr.astype(np.uint8)

    # store recursive thumbnails for the build segment
    if frame < 16 * B and frame % 50 == 0:
        THUMBS.append(Image.fromarray(out).resize((300, 533), Image.BILINEAR))
    return out

# ---------------- main ----------------
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        targets = [int(x) for x in sys.argv[2:]]
        if any(t >= 18 * B for t in targets):   # populate PiP store for build previews
            for f in range(0, int(16 * B), 150):
                render_frame(f)
        for fr in targets:
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
