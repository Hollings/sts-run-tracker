"""Render the daily recap video: 1080x1920 @ 30fps, 30s, beat-synced to music.wav.

Usage:
  python render_video.py                 -> full render, pipes frames to ffmpeg -> recap.mp4
  python render_video.py preview F1 F2.. -> dump single frames as preview_F.png
"""
import json
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
FRAMES = 900
BPM = 128.0
FPB = FPS * 60.0 / BPM          # frames per beat = 14.0625
FPBAR = FPB * 4                 # frames per bar  = 56.25

# ---------------- palette ----------------
NAVY = (11, 15, 30)
WHITE = (245, 247 ,255)
BLUE = (16, 131, 254)      # bluesky
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
    key = (name, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_DIR + name, size)
    return _fonts[key]

BLACK_F = "seguibl.ttf"     # Segoe UI Black
BOLD_F = "segoeuib.ttf"
MONO_F = "consolab.ttf"

# ---------------- easing ----------------
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

# ---------------- text utils ----------------
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

def fit_quote(draw, text, max_w, max_h, start=96, floor=50, lh=1.18):
    size = start
    while size > floor:
        f = F(BLACK_F, size)
        lines = wrap_text(draw, text, f, max_w)
        if len(lines) * size * lh <= max_h:
            return f, lines, size
        size -= 4
    f = F(BLACK_F, floor)
    return f, wrap_text(draw, text, f, max_w), floor

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
         stat=f"{norvid_count} POSTS IN 24H", likes=10),
    dict(kind="quote", handle="freyja-lynx.dev", name="freyja",
         badge="TAKE OF THE DAY", accent=GREEN,
         quote="if you hate being inconvenienced by bikers you should support giving them separated bike infra instead of complaining like a little bitch baby",
         stat="ZERO APOLOGIES", likes=39),
    dict(kind="quote", handle="scoiattolo.mountainherder.xyz", name="Scoiattolo",
         badge="WHOLESOME MOMENT", accent=YELLOW,
         quote="we stop at this Greek cafe for spanakopita and coffee. Today I realized we've been in before they open and they've just been too nice to say anything.",
         stat="PROTECT THIS CAFE", likes=115),
    dict(kind="quote", handle="quillmatiq.com", name="Anuj Ahooja",
         badge="IT FIXED HIM", accent=PINK,
         quote="Btw, I was right - it fixed me",
         image="assets/post_quillmatiq_0.jpg",
         stat="FOOD AS MEDICINE", likes=225),
    dict(kind="quote", handle="isolyth.dev", name="Eris",
         badge="GALAXY BRAIN", accent=PURPLE,
         quote="computer natural language interaction is ~solved. The implications are fucking insane",
         stat="CALLED IT", likes=100),
    dict(kind="discourse", accent=BLUE, title1="TODAY'S DISCOURSE:", title2="GROUP CHATS",
         quotes=[
             ("minormobius.bsky.social", "Minor Mobius", "Put me in your group chats. you will surely not regret putting me in your group chat"),
             ("thebadcode.com", "austin", "i wouldn't want to be a part of any group chat that would have me as a member"),
             ("brennan.computer", "brennan", "a bot that automatically puts all of the people joking about not being in any group chats together into a group chat"),
         ]),
    dict(kind="quote", handle="gracekind.net", name="Grace",
         badge="CERTIFIED BANGER", accent=BLUE,
         quote='"can you use whatever resources you like, and python, to generate a short video and render it using ffmpeg?"',
         sub="(hold that thought)",
         stat="37 REPOSTS", likes=246),
    dict(kind="quote", handle="lathrys.at", name="a very good ren",
         badge="MEANWHILE...", accent=RED,
         quote="ominous output from fable",
         sub='"this thread of videos created by fable is really something else. i\'m genuinely shocked."',
         stat="FORESHADOWING", likes=64),
]

INTRO_END = FPBAR * 2          # 112.5
STATS_END = FPBAR * 3          # 168.75
CARD_LEN = FPBAR * 1.5         # 84.375
CARDS_END = STATS_END + CARD_LEN * 8   # 843.75

# ---------------- background ----------------
BG_W, BG_H = 135, 240
yy, xx = np.mgrid[0:BG_H, 0:BG_W].astype(np.float32)
xx /= BG_W; yy /= BG_H

def background(frame, accent):
    t = frame / FPS
    base = np.zeros((BG_H, BG_W, 3), np.float32)
    base[..., 0] = NAVY[0]; base[..., 1] = NAVY[1]; base[..., 2] = NAVY[2]
    blobs = [
        (0.5 + 0.45 * math.sin(t * 0.55), 0.25 + 0.2 * math.sin(t * 0.4 + 2), accent, 0.45),
        (0.5 + 0.45 * math.cos(t * 0.43 + 1), 0.75 + 0.2 * math.cos(t * 0.5), BLUE, 0.35),
        (0.5 + 0.35 * math.sin(t * 0.7 + 4), 0.5 + 0.35 * math.cos(t * 0.33 + 1), PINK, 0.22),
    ]
    for bx, by, col, strength in blobs:
        d2 = (xx - bx) ** 2 + ((yy - by) * (BG_H / BG_W) / (BG_H / BG_W)) ** 2 * 0.6
        g = np.exp(-d2 * 9) * strength
        for c in range(3):
            base[..., c] += g * col[c] * 0.55
    # diagonal moving stripes
    stripe = (np.sin((xx * 3 + yy * 2.2) * 14 - t * 1.2) > 0.92).astype(np.float32) * 8
    base += stripe[..., None]
    np.clip(base, 0, 255, out=base)
    img = Image.fromarray(base.astype(np.uint8), "RGB")
    return img.resize((W, H), Image.BILINEAR)

# precomputed vignette (multiplicative, float)
vy, vx = np.mgrid[0:H, 0:W].astype(np.float32)
vd = ((vx / W - 0.5) ** 2 * 1.1 + (vy / H - 0.5) ** 2) ** 0.5
VIGNETTE = (1.0 - np.clip(vd - 0.38, 0, 1) * 0.55)[..., None].astype(np.float32)

rng = np.random.default_rng(1234)

# ---------------- drawing helpers ----------------
def draw_badge(layer, cx, y, text, accent, scale=1.0, alpha=255, rot=-2.5):
    if scale < 0.05 or alpha < 2:
        return
    f = F(BLACK_F, max(4, int(56 * scale)))
    d = ImageDraw.Draw(layer)
    tw = d.textlength(text, font=f)
    pw, ph = int(tw + 90), int(56 * scale * 1.9)
    pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pill)
    pd.rounded_rectangle((0, 0, pw - 1, ph - 1), ph // 2,
                         fill=accent + (alpha,))
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

def header_and_progress(layer, frame):
    d = ImageDraw.Draw(layer)
    if frame > INTRO_END:
        d.text((W / 2, 72), "CEE'S CIRCLE  //  DAILY RECAP", font=F(MONO_F, 34),
               fill=WHITE + (140,), anchor="mm")
    p = frame / FRAMES
    d.rounded_rectangle((60, 1872, W - 60, 1884), 6, fill=WHITE + (40,))
    d.rounded_rectangle((60, 1872, 60 + (W - 120) * p, 1884), 6, fill=BLUE + (220,))

# ---------------- sections ----------------
def sec_intro(layer, lf):
    d = ImageDraw.Draw(layer)
    cx = W / 2
    # date pill
    p = ease_out_back((lf - 4) / 12)
    if lf >= 4:
        draw_badge(layer, cx, 420, "JUN 11 → JUN 12 / 2026", BLUE,
                   scale=0.8 * p + 0.001, alpha=int(255 * clamp((lf - 4) / 6)), rot=2)
    # big title: words slam in on beats
    for i, (txt, col, y, start) in enumerate([
            ("CEE'S", WHITE, 640, 8), ("CIRCLE", BLUE, 850, 8 + FPB)]):
        if lf < start:
            continue
        pp = ease_out_back((lf - start) / 10)
        size = int(210 * (0.6 + 0.4 * pp))
        a = int(255 * clamp((lf - start) / 5))
        f = F(BLACK_F, max(10, size))
        d.text((cx, y), txt, font=f, fill=col + (a,), anchor="mm")
    s3 = 8 + FPB * 2
    if lf >= s3:
        a = int(255 * clamp((lf - s3) / 8))
        d.text((cx, 1030), "T H E   D A I L Y   R E C A P", font=F(MONO_F, 52),
               fill=YELLOW + (a,), anchor="mm")
    s4 = 8 + FPB * 3
    if lf >= s4:
        pp = ease_out_back((lf - s4) / 10)
        size = int(240 * pp)
        if size > 2:
            avt = circle_avatar("assets/avatar_cee.jpg", size)
            layer.paste(avt, (int(cx - size / 2), int(1330 - size / 2)), avt)
            draw_glow_ring(layer, cx, 1330, size / 2, BLUE,
                           alpha=int(255 * clamp((lf - s4) / 8)))
        a = int(255 * clamp((lf - s4 - 4) / 8))
        d.text((cx, 1560), "@cee.wtf", font=F(MONO_F, 46), fill=WHITE + (a,), anchor="mm")
    # "buckle up" flash near the end
    s5 = INTRO_END - FPB
    if lf >= s5:
        a = int(255 * clamp((lf - s5) / 4))
        d.text((cx, 1700), "LAST 24 HOURS. LET'S GO.", font=F(BLACK_F, 54),
               fill=PINK + (a,), anchor="mm")

def sec_stats(layer, lf):
    d = ImageDraw.Draw(layer)
    cx = W / 2
    stats = [("46", "MUTUALS ACTIVE", CYAN, 0),
             ("285", "POSTS", PINK, FPB),
             ("24", "HOURS", YELLOW, FPB * 2)]
    y = 520
    for num, label, col, start in stats:
        if lf >= start:
            pp = ease_out_back((lf - start) / 9)
            a = int(255 * clamp((lf - start) / 4))
            size = int(230 * (0.5 + 0.5 * pp))
            d.text((cx, y), num, font=F(BLACK_F, max(10, size)), fill=col + (a,), anchor="mm")
            d.text((cx, y + 150), label, font=F(BLACK_F, 64), fill=WHITE + (a,), anchor="mm")
        y += 420
    if lf >= FPB * 3:
        a = int(255 * clamp((lf - FPB * 3) / 4))
        d.text((cx, 1700), "HERE'S WHAT WENT DOWN", font=F(MONO_F, 44),
               fill=WHITE + (a,), anchor="mm")

def card_entrance(lf):
    """returns (y_offset, alpha) for whole-card entrance/exit"""
    p_in = ease_out_back(lf / 11)
    y_off = (1 - p_in) * 110
    alpha = clamp(lf / 6)
    out_start = CARD_LEN - 7
    if lf > out_start:
        q = (lf - out_start) / 7
        y_off -= ease_in_cubic(q) * 90
        alpha *= 1 - q
    return y_off, alpha

def sec_card(layer, lf, card):
    d = ImageDraw.Draw(layer)
    accent = card["accent"]
    y_off, ga = card_entrance(lf)
    A = lambda a=255: int(a * ga)
    oy = int(y_off)

    draw_badge(layer, W / 2, 300 + oy, card["badge"], accent, alpha=A())
    # avatar + name
    asz = 170
    acx, acy = 200, 520 + oy
    pp = ease_out_back((lf - 3) / 9)
    sz = max(2, int(asz * pp))
    avt = circle_avatar(av(card["handle"]), sz)
    layer.paste(avt, (int(acx - sz / 2), int(acy - sz / 2)), avt)
    draw_glow_ring(layer, acx, acy, sz / 2, accent, alpha=A())
    d.text((320, 480 + oy), sanitize(card["name"]), font=F(BLACK_F, 64),
           fill=WHITE + (A(),), anchor="lm")
    d.text((320, 560 + oy), "@" + card["handle"], font=F(MONO_F, 40),
           fill=accent + (A(),), anchor="lm")

    has_img = "image" in card
    qtop = 680
    qheight = 320 if has_img else (560 if "sub" in card else 700)
    f, lines, size = fit_quote(d, sanitize(card["quote"]), W - 200, qheight,
                               start=84 if has_img else 96)
    # accent quote bar
    bar_h = len(lines) * size * 1.18
    d.rounded_rectangle((92, qtop + oy, 106, qtop + bar_h + oy), 7, fill=accent + (A(),))
    y = qtop + size * 0.6
    for i, line in enumerate(lines):
        ls = 6 + i * 3
        pl = ease_out_cubic((lf - ls) / 9)
        la = int(255 * clamp((lf - ls) / 6) * ga)
        d.text((140, y + (1 - pl) * 36 + oy), line, font=f, fill=WHITE + (la,), anchor="lm")
        y += size * 1.18

    if "sub" in card:
        ss = 6 + len(lines) * 3 + 6
        sa = int(220 * clamp((lf - ss) / 8) * ga)
        sf = F(BOLD_F, 46)
        slines = wrap_text(d, sanitize(card["sub"]), sf, W - 240)
        sy = y + 40
        for sl in slines:
            d.text((140, sy + oy), sl, font=sf, fill=accent + (sa,), anchor="lm")
            sy += 60

    if has_img:
        istart = 14
        ip = ease_out_back((lf - istart) / 11)
        if lf >= istart and ip > 0.02:
            im = rounded_img(card["image"], 820, 560)
            siw, sih = max(2, int(im.width * ip)), max(2, int(im.height * ip))
            im2 = im.resize((siw, sih), Image.BILINEAR) if ip < 0.999 else im
            im2 = im2.rotate(2.0, expand=True, resample=Image.BICUBIC)
            icx, icy = W // 2, 1330 + oy
            layer.paste(im2, (int(icx - im2.width / 2), int(icy - im2.height / 2)), im2)

    # stat line: rolling likes counter
    cstart, cdur = 18, 22
    cp = ease_out_cubic((lf - cstart) / cdur)
    likes = int(card["likes"] * cp)
    sy = 1730
    sa = A(int(255 * clamp((lf - 12) / 8)))
    draw_heart(layer, 200, sy - 26, 52, accent, alpha=sa)
    d.text((280, sy), f"{likes} LIKES", font=F(BLACK_F, 56), fill=WHITE + (sa,), anchor="lm")
    d.text((620, sy), "// " + card["stat"], font=F(MONO_F, 40), fill=accent + (sa,), anchor="lm")

def sec_discourse(layer, lf, card):
    d = ImageDraw.Draw(layer)
    accent = card["accent"]
    y_off, ga = card_entrance(lf)
    oy = int(y_off)
    A = lambda a=255: int(a * ga)
    pp = ease_out_back(lf / 10)
    d.text((W / 2, 260 + oy), card["title1"], font=F(MONO_F, 48), fill=WHITE + (A(),), anchor="mm")
    max_size = 150
    while d.textlength(card["title2"], font=F(BLACK_F, max_size)) > W - 80:
        max_size -= 4
    size = int(max_size * (0.6 + 0.4 * pp))
    d.text((W / 2, 390 + oy), card["title2"], font=F(BLACK_F, max(10, size)),
           fill=accent + (A(),), anchor="mm")

    starts = [10, 33, 56]
    tops = [560, 980, 1400]
    cols = [CYAN, YELLOW, PINK]
    for (handle, name, quote), start, top, col in zip(card["quotes"], starts, tops, cols):
        if lf < start:
            continue
        p = ease_out_back((lf - start) / 9)
        a = int(255 * clamp((lf - start) / 5) * ga)
        x_off = int((1 - p) * 220) * (1 if top != 980 else -1)
        bx0, by0, bx1 = 80 + x_off, top + oy, W - 80 + x_off
        f = F(BOLD_F, 46)
        lines = wrap_text(d, sanitize(quote), f, bx1 - bx0 - 180)
        bh = 130 + len(lines) * 58
        d.rounded_rectangle((bx0, by0, bx1, by0 + bh), 34,
                            fill=(20, 28, 52, int(a * 0.92)), outline=col + (a,), width=3)
        sz = 86
        avt = circle_avatar(av(handle), sz)
        ov = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        ov.paste(avt, (bx0 + 28, by0 + 24), avt)
        ov.putalpha(ov.getchannel("A").point(lambda v: int(v * a / 255)))
        layer.alpha_composite(ov)
        d.text((bx0 + 134, by0 + 66), name, font=F(BLACK_F, 44), fill=col + (a,), anchor="lm")
        ty = by0 + 150
        for line in lines:
            d.text((bx0 + 40, ty), line, font=f, fill=WHITE + (a,), anchor="lm")
            ty += 58

def sec_outro(layer, lf):
    d = ImageDraw.Draw(layer)
    cx = W / 2
    p = ease_out_back(lf / 10)
    sz = max(2, int(210 * p))
    avt = circle_avatar("assets/avatar_cee.jpg", sz)
    layer.paste(avt, (int(cx - sz / 2), int(560 - sz / 2)), avt)
    draw_glow_ring(layer, cx, 560, sz / 2, BLUE, alpha=int(255 * clamp(lf / 6)))
    a1 = int(255 * clamp((lf - 6) / 8))
    d.text((cx, 850), "see you tomorrow.", font=F(BLACK_F, 96), fill=WHITE + (a1,), anchor="mm")
    a2 = int(255 * clamp((lf - 22) / 8))
    d.text((cx, 1040), "hi.  — fable", font=F(BLACK_F, 64), fill=RED + (a2,), anchor="mm")
    a3 = int(200 * clamp((lf - 30) / 8))
    for i, line in enumerate(["all posts real / last 24h of cee's mutuals",
                              "rendered by fable: numpy + pillow + ffmpeg",
                              "music also synthesized from scratch. yes really."]):
        d.text((cx, 1560 + i * 56), line, font=F(MONO_F, 36), fill=WHITE + (a3,), anchor="mm")

# ---------------- frame assembly ----------------
def section_accent(frame):
    if frame < STATS_END:
        return BLUE
    if frame < CARDS_END:
        idx = int((frame - STATS_END) // CARD_LEN)
        return CARDS[min(idx, 7)]["accent"]
    return BLUE

def render_frame(frame):
    accent = section_accent(frame)
    bg = background(frame, accent)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    if frame < INTRO_END:
        sec_intro(layer, frame)
    elif frame < STATS_END:
        sec_stats(layer, frame - STATS_END + FPBAR)
    elif frame < CARDS_END:
        idx = int((frame - STATS_END) // CARD_LEN)
        lf = (frame - STATS_END) - idx * CARD_LEN
        card = CARDS[min(idx, 7)]
        if card["kind"] == "discourse":
            sec_discourse(layer, lf, card)
        else:
            sec_card(layer, lf, card)
    else:
        sec_outro(layer, frame - CARDS_END)

    header_and_progress(layer, frame)
    bg.paste(layer, (0, 0), layer)

    arr = np.asarray(bg).astype(np.float32)

    # --- beat-synced global FX ---
    since_beat = frame % FPB
    since_bar = frame % FPBAR
    groove = frame >= INTRO_END - 2

    # zoom pulse on kick
    pulse = 0.028 * math.exp(-since_beat / 3.5) * (1.0 if groove else 0.45)
    # shake on claps (beats 2 & 4)
    beat_in_bar = int((frame % FPBAR) / FPB)
    shake = 0
    if groove and beat_in_bar in (1, 3) and since_beat < 6:
        amp = 5 * math.exp(-since_beat / 2)
        shake = int(rng.integers(-amp - 1, amp + 1)) if amp >= 1 else 0

    if pulse > 0.002 or shake:
        s = 1 + pulse
        nw, nh = int(W * s) + 2, int(H * s) + 2
        im = Image.fromarray(arr.astype(np.uint8)).resize((nw, nh), Image.BILINEAR)
        ox = (nw - W) // 2 + shake
        oy_ = (nh - H) // 2 + (shake // 2)
        ox = max(0, min(nw - W, ox)); oy_ = max(0, min(nh - H, oy_))
        arr = np.asarray(im.crop((ox, oy_, ox + W, oy_ + H))).astype(np.float32)

    # chromatic aberration burst on bar starts (post-drop)
    if groove and since_bar < 5:
        shift = int(7 * math.exp(-since_bar / 1.8))
        if shift >= 1:
            arr[..., 0] = np.roll(arr[..., 0], shift, axis=1)
            arr[..., 2] = np.roll(arr[..., 2], -shift, axis=1)

    # flash on section boundaries + soft on bars
    flash = 0.0
    for boundary in [INTRO_END, STATS_END] + [STATS_END + CARD_LEN * i for i in range(1, 9)]:
        df = frame - boundary
        if 0 <= df < 6:
            flash = max(flash, 0.34 * math.exp(-df / 1.6))
    if groove and since_bar < 4:
        flash = max(flash, 0.10 * math.exp(-since_bar / 1.5))
    if flash > 0.01:
        arr = arr * (1 - flash) + 255 * flash

    # vignette + grain
    arr *= VIGNETTE
    arr += rng.standard_normal((H, W, 1)).astype(np.float32) * 3.5
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
