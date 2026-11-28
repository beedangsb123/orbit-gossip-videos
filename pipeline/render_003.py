"""Orbit Gossip 003 — Planet Reviews x "Real or Fake?": the neutron star (sugar cube = 1 billion tons).
Copied from render_002.py (helpers kept as-is) + neutron-star game-show scenes below.
Real images (NASA/JPL-Caltech, public domain): pulsar concept PIA21085, magnetar concept PIA26274, Uranus Voyager 2 PIA18182;
Crab Nebula PIA03606 = NASA, ESA, J. Hester & A. Loll (ASU), CC BY 4.0 -> credited on screen + in captions.
Facts: NASA Science "Neutron Stars Are Weird" + NASA Imagine the Universe "Neutron Stars and Pulsars": sugar cube ~1 billion
tons (~a mountain); heavier than the Sun, city-sized (~20 km / 12.5 mi, like Manhattan); fastest pulsar PSR J1748-2446ad spins
43,000 times a minute (twice a household blender); magnetic fields trillions x Earth's, magnetars another 1,000x stronger;
first pulsar 1967 nicknamed "little green men" (LGM-1). Teaser: NASA JPL — Uranus cloud tops contain hydrogen sulfide (rotten eggs).
usage (work dir with meta.json): python render_003.py stills <prefix> t1 t2 ... | python render_003.py full [a b out.mp4]"""
import cairo, json, math, os, sys, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine
from engine import *

SPACE = hexc("120A2E"); PURPLE = hexc("3B1C7A"); PINK = hexc("FF3D9A"); CYAN = hexc("3DF5FF"); CREAM = hexc("FFF4E0")
YELLOW = hexc("FFE14D"); INK = hexc("140B24"); STARC = hexc("FFB15A")
engine.CAP_ACCENT = hexc("FF5FB0")
engine.SPK_TXT = {"M": (0.92, 0.97, 1.0), "F": (1.0, 0.95, 0.97), None: WHITE}

_meta = json.load(open("meta.json"))
_S = json.load(open("script_el.json")) if os.path.exists("script_el.json") else {"lines": _meta}
DROP = set(_S.get("drop", []))
ORIG = [j for j in range(len(_S["lines"])) if j not in DROP]     # scene numbers (original line indices) that are kept
assert len(ORIG) == len(_meta), (len(ORIG), len(_meta))
META = dict(zip(ORIG, _meta))
meta = _meta
NSC = len(_S["lines"])                                             # end card = scene NSC
END = 2.4
ORDER = ORIG + [NSC]
STARTS = []; DURS = []; _t = 0
for j in ORIG: STARTS.append(_t); DURS.append(META[j]["dur"]); _t += META[j]["dur"]
STARTS.append(_t); DURS.append(END)
TOTAL = _t + END
from collections import defaultdict
ST = defaultdict(lambda: -1000.0, {o: STARTS[k] for k, o in enumerate(ORDER)})   # start time by scene number


def wt(i, key, default):
    if i not in META: return default
    for w in META[i]["words"]:
        if w[0].lower().strip(".,!?'\"").startswith(key.lower()): return w[1]
    return default


# ---------------- background: nebula + stars ----------------
_rng = np.random.default_rng(3)
def _nebula():
    n1 = fbm(H + 300, W + 300, octaves=6, seed=21, base=3); n2 = fbm(H + 300, W + 300, octaves=5, seed=5, base=2)
    base = ramp(n1, [(0, hexc("1C1046")), (0.45, hexc("2E1868")), (0.7, hexc("6A2A8C")), (1, hexc("C2448F"))])
    cy = ramp(n2, [(0, (0, 0, 0)), (0.6, (0, 0, 0)), (1, hexc("2A8FB0"))])
    a = np.clip(base + 0.55 * cy, 0, 1)
    return (a * 255).astype(np.float32)
NEB = _nebula()
STARS = [(_rng.random() * W, _rng.random() * H, _rng.random(), _rng.random()) for _ in range(260)]


def background(c, t, drift=1.0, dim=1.0):
    ox = int(150 + 120 * math.sin(t * 0.05 * drift)); oy = int(150 + 120 * math.cos(t * 0.04 * drift))
    a = NEB[oy:oy + H, ox:ox + W] * dim + (1 - dim) * 30
    s = to_surface(a / 255); c.set_source_surface(s, 0, 0); c.paint()
    for x, y, s_, ph in STARS:
        px = (x - t * (6 + 26 * s_) * drift) % W
        tw = 0.45 + 0.55 * abs(math.sin(t * (1.5 + 2 * ph) + ph * 9))
        r = 0.8 + 2.4 * s_ ** 2
        c.set_source_rgba(1, 0.97, 0.92, 0.85 * tw); c.arc(px, y, r, 0, 2 * math.pi); c.fill()
        if s_ > 0.93:
            c.set_source_rgba(1, 1, 1, 0.35 * tw); c.set_line_width(1.5)
            c.move_to(px - 9, y); c.line_to(px + 9, y); c.move_to(px, y - 9); c.line_to(px, y + 9); c.stroke()


# ---------------- the planet (procedural blue hot Jupiter) ----------------
def _bands():
    h, w = 512, 1024
    lat = np.linspace(-1, 1, h)[:, None]
    n = fbm(h, w, octaves=6, seed=8, base=4); n2 = fbm(h, w, octaves=4, seed=2, base=8)
    v = 0.5 + 0.28 * np.sin(lat * 13 + n * 5.0) + 0.22 * (n2 - 0.5)
    col = ramp(np.clip(v, 0, 1), [(0, hexc("0A1E6E")), (0.35, hexc("1846B8")), (0.6, hexc("2F7BE8")), (0.85, hexc("7CC8FF")), (1, hexc("D7F1FF"))])
    wx = np.sin(np.pi * np.arange(w) / w)[None, :, None] ** 2      # seamless in longitude (no vertical seam)
    return col * wx + np.roll(col, w // 2, axis=1) * (1 - wx)
BANDS = _bands()


_DISC = None
DISC_R = 1063 / 1080 * 700   # planet radius inside hd_disc.png (1400 px square)


def planet(c, cx, cy, r, t, light=(-0.7, -0.35), heat=0.0, terminator=0.0, spin=0.02, glints=1.0):
    """REAL image: NASA/ESA/M. Kornmesser illustration of HD 189733b (CC BY 4.0), lit from the right.
    heat tints it orange; terminator darkens the left half hard (day/night scene); glints = glass sparkles."""
    global _DISC
    if _DISC is None: _DISC = cairo.ImageSurface.create_from_png("hd_disc.png")
    r = max(8, r)
    g = cairo.RadialGradient(cx, cy, r * 0.95, cx, cy, r * 1.3)
    g.add_color_stop_rgba(0, *CYAN, 0.30); g.add_color_stop_rgba(1, *CYAN, 0)
    c.set_source(g); c.arc(cx, cy, r * 1.32, 0, 2 * math.pi); c.fill()
    k = r / DISC_R
    c.save(); c.arc(cx, cy, r, 0, 2 * math.pi); c.clip()
    c.save(); c.translate(cx, cy); c.rotate(0.03 * math.sin(t * 0.4) + spin * t * 0.5); c.scale(k, k); c.translate(-700, -700)
    c.set_source_surface(_DISC, 0, 0); c.get_source().set_filter(cairo.FILTER_GOOD); c.paint(); c.restore()
    if heat > 0:
        c.set_source_rgba(1.0, 0.42, 0.1, 0.55 * heat); c.paint()
    if terminator > 0:
        lg = cairo.LinearGradient(cx - r, 0, cx + r, 0)
        lg.add_color_stop_rgba(0, 0, 0, 0.02, 0.92 * terminator); lg.add_color_stop_rgba(0.46, 0, 0, 0.02, 0.85 * terminator)
        lg.add_color_stop_rgba(0.56, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
        c.set_source(lg); c.paint()
    if glints > 0:
        rr = np.random.default_rng(11)
        for j in range(26):
            a_, d_ = rr.random() * 2 * math.pi, math.sqrt(rr.random()) * 0.9
            x = cx + math.cos(a_) * d_ * r; y = cy + math.sin(a_) * d_ * r
            if x < cx - 0.1 * r: continue
            tw = max(0.0, math.sin(t * (3 + 4 * rr.random()) + j)) ** 6
            if tw < 0.05: continue
            s_ = r * 0.035 * (0.5 + tw)
            c.set_source_rgba(1, 1, 1, 0.9 * tw * glints); c.set_line_width(max(1, r * 0.006))
            c.move_to(x - s_, y); c.line_to(x + s_, y); c.move_to(x, y - s_); c.line_to(x, y + s_); c.stroke()
    c.restore()


def star(c, x, y, r, t):
    for i in range(7, 0, -1):
        c.set_source_rgba(*STARC, 0.07 * (1 + 0.15 * math.sin(t * 3 + i))); c.arc(x, y, r * (1 + i * 0.35), 0, 2 * math.pi); c.fill()
    g = cairo.RadialGradient(x - r * 0.2, y - r * 0.2, 0, x, y, r)
    g.add_color_stop_rgb(0, 1, 0.97, 0.85); g.add_color_stop_rgb(0.6, *hexc("FFC46B")); g.add_color_stop_rgb(1, *hexc("F2772E"))
    c.set_source(g); c.arc(x, y, r, 0, 2 * math.pi); c.fill()


def glass_rain(c, t, n=70, ang=-0.12, speed=1.0, alpha=1.0, region=(0, 0, W, H), seed=1, length=110):
    """sideways streaks of glass: thin cyan-white lines with a bright glint head, moving right->left"""
    r = np.random.default_rng(seed); x0, y0, w, h = region
    for j in range(n):
        a, b, s = r.random(), r.random(), r.random()
        sp = (900 + 1400 * s) * speed
        x = x0 + w + 200 - ((a * (w + 400) + t * sp) % (w + 400)); y = y0 + b * h + (x - x0) * math.tan(ang)
        L = length * (0.6 + s)
        g = cairo.LinearGradient(x, y, x + L, y + L * math.tan(-ang) * 0.0 + L * math.sin(ang))
        g.add_color_stop_rgba(0, 1, 1, 1, 0.95 * alpha); g.add_color_stop_rgba(0.15, *CYAN, 0.7 * alpha); g.add_color_stop_rgba(1, *CYAN, 0)
        c.set_source(g); c.set_line_width(2 + 3 * s); c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.move_to(x, y); c.line_to(x + L, y + L * math.sin(ang)); c.stroke()
        c.set_source_rgba(1, 1, 1, 0.9 * alpha); c.arc(x, y, 2 + 2.5 * s, 0, 2 * math.pi); c.fill()


# ---------------- tabloid graphics (look v1) ----------------
def sticker(c, s, x, y, size, t, bg=PINK, fg=WHITE, ang=-0.05, maxw=940, outline=YELLOW):
    """tabloid headline sticker: slams in (scale 1.6 -> 1), tilted, thick outline + drop shadow"""
    if t <= 0: return
    w = text_w(c, s, size)
    if w > maxw - 70: size *= (maxw - 70) / w; w = maxw - 70
    k = min(1, t / 0.18); sc = lerp(1.6, 1.0, eout(k)) + 0.04 * math.sin(min(1, max(0, t - 0.18) / 0.2) * math.pi)
    bw, bh = w + 70, size * 1.45
    c.save(); c.translate(x, y); c.rotate(ang); c.scale(sc, sc)
    c.set_source_rgba(0, 0, 0, 0.5 * k); rrect(c, -bw / 2 + 12, -bh / 2 + 14, bw, bh, 14); c.fill()
    c.set_source_rgba(*bg, k); rrect(c, -bw / 2, -bh / 2, bw, bh, 14); c.fill()
    c.set_source_rgba(*outline, k); c.set_line_width(7); rrect(c, -bw / 2, -bh / 2, bw, bh, 14); c.stroke()
    text(c, s, 0, size * 0.36, size, col=fg, alpha=k)
    c.restore()


def burst(c, s, x, y, r, t, bg=YELLOW, fg=INK, spikes=14, ang=0.18, size=None):
    """starburst 'EXCLUSIVE' badge that pops and slowly spins"""
    if t <= 0: return
    k = back(t / 0.3); a = min(1, t / 0.1)
    c.save(); c.translate(x, y); c.rotate(ang + 0.15 * math.sin(t * 2)); c.scale(k, k)
    c.move_to(r, 0)
    for j in range(1, spikes * 2 + 1):
        rr = r if j % 2 == 0 else r * 0.78; aa = j * math.pi / spikes; c.line_to(rr * math.cos(aa), rr * math.sin(aa))
    c.close_path(); c.set_source_rgba(0, 0, 0, 0.4 * a); c.fill_preserve(); c.set_source_rgba(*bg, a); c.fill_preserve()
    c.set_source_rgba(*PINK, a); c.set_line_width(5); c.stroke()
    sz = size or r * 0.34; lines = s.split("\n")
    for j, ln in enumerate(lines):
        text(c, ln, 0, sz * 0.36 + (j - (len(lines) - 1) / 2) * sz * 1.05, sz, col=fg, alpha=a)
    c.restore()


def stamp(c, s, x, y, t, col=PINK, size=120, ang=-0.14):
    if t <= 0: return
    k = min(1, t / 0.14); sc = lerp(2.2, 1, eout(k)); w = text_w(c, s, size) + 60
    c.save(); c.translate(x, y); c.rotate(ang); c.scale(sc, sc)
    c.set_source_rgba(*col, 0.92 * k); c.set_line_width(12); rrect(c, -w / 2, -size * 0.8, w, size * 1.25, 16); c.stroke()
    text(c, s, 0, size * 0.36, size, col=col, alpha=0.95 * k)
    c.restore()


def flash(c, t, dur=0.22):
    """paparazzi flash transition (partial, never a full white or black frame)"""
    if t < 0 or t > dur: return
    k = 1 - t / dur
    g = cairo.RadialGradient(W * 0.7, H * 0.3, 0, W * 0.7, H * 0.3, H * 0.9)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.75 * k); g.add_color_stop_rgba(1, 1, 0.85, 0.95, 0.2 * k)
    c.set_source(g); c.paint()


def panel(c, x, y, w, h, t, col=INK, a=0.82, edge=PINK):
    if t <= 0: return
    k = eout(t / 0.25)
    c.save(); c.translate(x + w / 2, y + h / 2); c.scale(lerp(0.85, 1, k), lerp(0.85, 1, k)); c.translate(-w / 2, -h / 2)
    c.set_source_rgba(0, 0, 0, 0.35 * k); rrect(c, 10, 14, w, h, 26); c.fill()
    c.set_source_rgba(*col, a * k); rrect(c, 0, 0, w, h, 26); c.fill()
    c.set_source_rgba(*edge, k); c.set_line_width(6); rrect(c, 0, 0, w, h, 26); c.stroke()
    c.restore()


def counter(t, v0, v1, dur, fmt="{:,}"):
    return fmt.format(int(round(lerp(v0, v1, eout(t / dur))))) if t > 0 else fmt.format(v0)


def tag(c, s, t, y=1262, x=70):
    source_tag(c, s, t, y=y, x=x, size=22)


def mini_planet(c, cx, cy, r, t):
    """badge/logo icon: blue planet with a pink ring and a speech-bubble tail"""
    c.save()
    c.translate(cx, cy); c.rotate(-0.4); c.scale(1.6, 0.42); c.arc(0, 0, r, math.pi, 2 * math.pi); c.restore()
    c.set_source_rgba(*PINK, 1); c.set_line_width(max(2, r * 0.18)); c.stroke()
    g = cairo.RadialGradient(cx - r * 0.35, cy - r * 0.35, r * 0.1, cx, cy, r)
    g.add_color_stop_rgb(0, *hexc("9DE6FF")); g.add_color_stop_rgb(0.6, *hexc("2F7BE8")); g.add_color_stop_rgb(1, *hexc("12308A"))
    c.set_source(g); c.arc(cx, cy, r, 0, 2 * math.pi); c.fill()
    c.save(); c.arc(cx, cy, r, 0, 2 * math.pi); c.clip()
    c.set_source_rgba(1, 1, 1, 0.25); c.set_line_width(max(1, r * 0.12))
    for k in (-0.35, 0.15, 0.55):
        c.move_to(cx - r, cy + k * r); c.curve_to(cx - r * 0.3, cy + k * r - r * 0.12, cx + r * 0.3, cy + k * r + r * 0.12, cx + r, cy + k * r); c.stroke()
    c.restore()
    c.save()
    c.translate(cx, cy); c.rotate(-0.4); c.scale(1.6, 0.42); c.arc(0, 0, r, 0, math.pi); c.restore()
    c.set_source_rgba(*PINK, 1); c.set_line_width(max(2, r * 0.18)); c.stroke()
    a = t * 2.5; mx = cx + math.cos(a) * r * 1.6 * math.cos(-0.4) - math.sin(a) * r * 0.42 * math.sin(-0.4)
    my = cy + math.cos(a) * r * 1.6 * math.sin(-0.4) + math.sin(a) * r * 0.42 * math.cos(-0.4)
    c.set_source_rgba(*YELLOW, 1); c.arc(mx, my, r * 0.14, 0, 2 * math.pi); c.fill()


def badge_og(c, t, y=190):
    size = 38; h = 70
    tw = text_w(c, "ORBIT ", size); tw2 = text_w(c, "GOSSIP", size)
    w = 92 + tw + tw2 + 34; x = W / 2 - w / 2
    c.save()
    c.set_source_rgba(0, 0, 0, 0.35); rrect(c, x + 3, y + 6, w, h, h / 2); c.fill()
    g = cairo.LinearGradient(x, 0, x + w, 0); g.add_color_stop_rgba(0, *hexc("2A1459"), 0.94); g.add_color_stop_rgba(1, *hexc("150A30"), 0.94)
    rrect(c, x, y, w, h, h / 2); c.set_source(g); c.fill()
    rim = cairo.LinearGradient(x, 0, x + w, 0); rim.add_color_stop_rgb(0, *PINK); rim.add_color_stop_rgb(0.5, *YELLOW); rim.add_color_stop_rgb(1, *PINK)
    rrect(c, x + 2, y + 2, w - 4, h - 4, h / 2 - 2); c.set_source(rim); c.set_line_width(4); c.stroke()
    ph = (t % 4.0) / 0.8
    if ph < 1:
        sx = x + ph * (w + 120) - 60
        c.save(); rrect(c, x, y, w, h, h / 2); c.clip()
        sg = cairo.LinearGradient(sx - 40, 0, sx + 40, 0)
        sg.add_color_stop_rgba(0, 1, 1, 1, 0); sg.add_color_stop_rgba(0.5, 1, 1, 1, 0.4); sg.add_color_stop_rgba(1, 1, 1, 1, 0)
        c.set_source(sg); c.paint(); c.restore()
    mini_planet(c, x + 50, y + h / 2, 17, t)
    tx = x + 92; ty = y + h / 2 + size * 0.36
    text(c, "ORBIT ", tx, ty, size, col=WHITE, align="left", stroke=4)
    text(c, "GOSSIP", tx + tw, ty, size, col=hexc("FF6FB8"), align="left", stroke=4)
    c.restore()


def logo_png(path):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1080, 1080); c = cairo.Context(s)
    g = cairo.RadialGradient(420, 380, 60, 540, 540, 620)
    g.add_color_stop_rgb(0, *hexc("4A2391")); g.add_color_stop_rgb(1, *hexc("140A30"))
    c.set_source(g); c.paint()
    r_ = np.random.default_rng(9)
    for _ in range(90):
        c.set_source_rgba(1, 1, 1, 0.3 + 0.6 * r_.random()); c.arc(r_.random() * 1080, r_.random() * 1080, 1 + 3 * r_.random() ** 3, 0, 2 * math.pi); c.fill()
    # speech bubble behind the planet
    c.save(); c.translate(720, 330)
    rrect(c, -170, -110, 340, 200, 90); c.move_to(-60, 85); c.line_to(-150, 170); c.line_to(10, 88); c.close_path()
    c.set_source_rgb(*PINK); c.fill()
    for j in range(3):
        c.set_source_rgb(1, 1, 1); c.arc(-80 + j * 80, -10, 24, 0, 2 * math.pi); c.fill()
    c.restore()
    mini_planet(c, 480, 600, 250, 0.9)
    text(c, "ORBIT", 540, 960, 120, col=WHITE, stroke=14)
    s.write_to_png(path)


LOGO_PATH = "logo_og.png"
if not os.path.exists(LOGO_PATH): logo_png(LOGO_PATH)
LOGO = cairo.ImageSurface.create_from_png(LOGO_PATH)


# ---------------- little drawn props ----------------
def cloud(c, x, y, s, col=(0.75, 0.78, 0.85), a=1.0):
    c.set_source_rgba(*col, a)
    for dx, dy, r in ((-60, 10, 50), (-10, -20, 65), (55, 0, 55), (100, 20, 40), (-100, 25, 38)):
        c.arc(x + dx * s, y + dy * s, r * s, 0, 2 * math.pi); c.fill()
    rrect(c, x - 138 * s, y + 10 * s, 276 * s, 60 * s, 30 * s); c.fill()


def rain_down(c, x, y, w, h, t, col=(0.6, 0.8, 1.0), n=26, seed=3):
    r = np.random.default_rng(seed); c.set_source_rgba(*col, 0.9); c.set_line_width(5); c.set_line_cap(cairo.LINE_CAP_ROUND)
    for j in range(n):
        px = x + r.random() * w; py = y + ((r.random() * h + t * 700) % h)
        c.move_to(px, py); c.line_to(px, py + 36); c.stroke()


def rain_side(c, x, y, w, h, t, n=26, seed=4):
    r = np.random.default_rng(seed); c.set_line_width(5); c.set_line_cap(cairo.LINE_CAP_ROUND)
    for j in range(n):
        py = y + r.random() * h; px = x + w - ((r.random() * w + t * 900) % w)
        c.set_source_rgba(*CYAN, 0.95); c.move_to(px, py); c.line_to(px + 48, py - 6); c.stroke()
        c.set_source_rgba(1, 1, 1, 1); c.arc(px, py, 4, 0, 2 * math.pi); c.fill()


def arrow(c, x0, y0, x1, y1, col=YELLOW, w=16, k=1.0):
    x1 = lerp(x0, x1, k); y1 = lerp(y0, y1, k); ang = math.atan2(y1 - y0, x1 - x0)
    c.set_source_rgba(*col, 1); c.set_line_width(w); c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.move_to(x0, y0); c.line_to(x1 - math.cos(ang) * w, y1 - math.sin(ang) * w); c.stroke()
    c.move_to(x1, y1)
    for s_ in (2.6, -2.6): c.line_to(x1 - math.cos(ang + s_ * 0.2) * w * 3, y1 - math.sin(ang + s_ * 0.2) * w * 3)
    c.close_path(); c.fill()


def sunglasses(c, cx, cy, r, t):
    if t <= 0: return
    k = eout(t / 0.35); yy = cy - r * 0.15 - (1 - k) * 300
    c.save(); c.set_source_rgba(0.05, 0.05, 0.08, 0.97)
    for sx in (-1, 1):
        c.save(); c.translate(cx + sx * r * 0.33, yy); c.scale(r * 0.3, r * 0.2); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore(); c.fill()
    c.set_line_width(r * 0.06); c.move_to(cx - r * 0.1, yy - r * 0.04); c.line_to(cx + r * 0.1, yy - r * 0.04); c.stroke()
    c.move_to(cx - r * 0.62, yy - r * 0.05); c.line_to(cx - r * 0.95, yy - r * 0.15); c.stroke()
    c.move_to(cx + r * 0.62, yy - r * 0.05); c.line_to(cx + r * 0.95, yy - r * 0.15); c.stroke()
    c.set_source_rgba(1, 1, 1, 0.45)
    for sx in (-1, 1):
        c.save(); c.translate(cx + sx * r * 0.33 - r * 0.1, yy - r * 0.07); c.scale(r * 0.08, r * 0.04); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore(); c.fill()
    c.restore()


def camera_flashes(c, t, seed=2):
    r = np.random.default_rng(seed)
    for j in range(9):
        x = 60 + r.random() * (W - 120); y = 300 + r.random() * 900; ph = r.random() * 1.2
        k = ((t + ph) % 1.2) / 1.2
        if k < 0.12:
            a = 1 - k / 0.12
            for i in range(4, 0, -1):
                c.set_source_rgba(1, 1, 1, 0.18 * a); c.arc(x, y, 30 * i, 0, 2 * math.pi); c.fill()
            c.set_source_rgba(1, 1, 1, a); c.set_line_width(4)
            c.move_to(x - 70, y); c.line_to(x + 70, y); c.move_to(x, y - 70); c.line_to(x, y + 70); c.stroke()


def wifi_card(c, t, reveal):
    """the joke: the planet's 'name' looks like a wifi PASSWORD -> it appears in the password field"""
    panel(c, 120, 520, 840, 560, t, col=hexc("F7F3FF"), a=0.97, edge=PINK)
    if t <= 0.15: return
    a = ease((t - 0.15) / 0.2)
    c.save(); c.translate(W / 2, 640)
    for j, rr in enumerate((90, 62, 34)):
        c.set_source_rgba(*PURPLE, a); c.set_line_width(14); c.arc(0, 40, rr, math.pi * 1.25, math.pi * 1.75); c.stroke()
    c.arc(0, 40, 10, 0, 2 * math.pi); c.fill(); c.restore()
    text(c, "Join \u201cSpace_Cafe_5G\u201d", W / 2, 760, 54, col=INK, alpha=a)
    text(c, "Password", 200, 830, 34, col=(0.45, 0.42, 0.55), align="left", alpha=a)
    c.set_source_rgba(0.9, 0.88, 0.96, a); rrect(c, 180, 845, 720, 110, 18); c.fill()
    pw = "\u2022" * 10 if reveal <= 0 else "HD189733b"
    text(c, pw, W / 2, 920, 70 if reveal > 0 else 60, col=PURPLE, alpha=a)
    if reveal > 0:
        c.set_source_rgba(0.18, 0.75, 0.44, ease(reveal / 0.3) * a); rrect(c, 330, 985, 420, 70, 35); c.fill()
        text(c, "CONNECTED!", W / 2, 1032, 40, col=WHITE, alpha=ease(reveal / 0.3) * a)


def beach_bubble(c, x, y, t, pop=-1.0):
    if t <= 0: return
    k = back(t / 0.35)
    if pop > 0:
        if pop > 0.25: return
        k *= 1 + pop * 3; a_ = 1 - pop / 0.25
    else: a_ = 1
    c.save(); c.translate(x, y); c.scale(k, k)
    c.set_source_rgba(1, 1, 1, 0.95 * a_)
    for dx, dy, r in ((-260, 20, 140), (-120, -90, 170), (60, -100, 170), (230, -10, 150), (130, 110, 150), (-110, 120, 150)):
        c.arc(dx, dy, r, 0, 2 * math.pi); c.fill()
    for dx, dy, r in ((-160, 290, 36), (-210, 360, 22)):
        c.arc(dx, dy, r, 0, 2 * math.pi); c.fill()
    c.save(); c.arc(0, 0, 270, 0, 2 * math.pi); c.clip()
    g = cairo.LinearGradient(0, -270, 0, 270); g.add_color_stop_rgb(0, *hexc("8FD8FF")); g.add_color_stop_rgb(0.55, *hexc("27A9E1")); g.add_color_stop_rgb(0.56, *hexc("F2D58B")); g.add_color_stop_rgb(1, *hexc("E8C06A"))
    c.set_source_rgba(1, 1, 1, 0); c.rectangle(-270, -270, 540, 540); c.set_source(g); c.paint_with_alpha(a_)
    c.set_source_rgba(1, 0.9, 0.4, a_); c.arc(150, -150, 50, 0, 2 * math.pi); c.fill()
    # umbrella
    c.set_source_rgba(*PINK, a_); c.move_to(-180, 40); c.curve_to(-120, -110, 40, -110, 90, 40); c.close_path(); c.fill()
    c.set_source_rgba(0.3, 0.2, 0.1, a_); c.set_line_width(8); c.move_to(-45, 0); c.line_to(-30, 190); c.stroke()
    # drink with tiny umbrella
    c.set_source_rgba(1, 0.6, 0.2, a_); c.move_to(110, 120); c.line_to(190, 120); c.line_to(170, 220); c.line_to(130, 220); c.close_path(); c.fill()
    c.set_source_rgba(*YELLOW, a_); c.move_to(120, 105); c.curve_to(140, 60, 180, 60, 200, 105); c.close_path(); c.fill()
    c.restore(); c.restore()


def droplets(c, t, cx, cy, k=1.0, seed=6):
    r = np.random.default_rng(seed)
    for j in range(22):
        x = cx + (r.random() - 0.5) * 860 + math.sin(t * 1.5 + j) * 20; y = cy + (r.random() - 0.5) * 760 + math.cos(t * 1.2 + j) * 16
        rr = (22 + 60 * r.random() ** 2) * eout(k * 1.5 - j * 0.03)
        if rr <= 1: continue
        g = cairo.RadialGradient(x - rr * 0.35, y - rr * 0.4, rr * 0.05, x, y, rr)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.95); g.add_color_stop_rgba(0.35, 0.7, 0.95, 1, 0.55); g.add_color_stop_rgba(1, 0.2, 0.6, 1, 0.25)
        c.set_source(g); c.arc(x, y, rr, 0, 2 * math.pi); c.fill()
        c.set_source_rgba(1, 1, 1, 0.8); c.set_line_width(2.5); c.arc(x, y, rr, 0, 2 * math.pi); c.stroke()


def chandelier(c, x, y, s, t, swing=0.0):
    c.save(); c.translate(x, y); c.rotate(swing); c.scale(s, s)
    c.set_source_rgb(*hexc("E8C15A")); c.set_line_width(8); c.move_to(0, -400); c.line_to(0, 0); c.stroke()
    c.set_line_width(14)
    c.move_to(-260, 40); c.curve_to(-200, 140, 200, 140, 260, 40); c.stroke()
    c.move_to(-160, 120); c.curve_to(-100, 200, 100, 200, 160, 120); c.stroke()
    c.arc(0, 10, 34, 0, 2 * math.pi); c.fill()
    for j, xx in enumerate((-260, -130, 0, 130, 260)):
        yy = 40 if abs(xx) == 260 else (110 if abs(xx) == 130 else 150)
        c.set_source_rgb(*hexc("E8C15A")); c.rectangle(xx - 8, yy - 50, 16, 50); c.fill()
        fl = 1 + 0.15 * math.sin(t * 18 + j)
        c.set_source_rgba(1, 0.8, 0.3, 0.95); c.save(); c.translate(xx, yy - 62); c.scale(10 * fl, 20 * fl); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore(); c.fill()
        for d in range(3):
            gy = yy + 30 + d * 38; g = cairo.RadialGradient(xx - 4, gy - 6, 1, xx, gy, 16)
            g.add_color_stop_rgba(0, 1, 1, 1, 1); g.add_color_stop_rgba(1, 0.5, 0.9, 1, 0.6)
            c.set_source(g); c.move_to(xx, gy - 20); c.line_to(xx + 12, gy); c.line_to(xx, gy + 20); c.line_to(xx - 12, gy); c.close_path(); c.fill()
    c.restore()


def gauge(c, cx, cy, r, v, vmax, t, label_="KM/H"):
    if t <= 0: return
    a = ease(t / 0.25)
    c.save(); c.set_source_rgba(*INK, 0.85 * a); c.arc(cx, cy, r + 30, math.pi, 2 * math.pi); c.close_path(); c.fill()
    for j in range(21):
        an = math.pi + math.pi * j / 20; rr = r - (34 if j % 5 == 0 else 18)
        c.set_source_rgba(1, 1, 1, 0.8 * a); c.set_line_width(6 if j % 5 == 0 else 3)
        c.move_to(cx + math.cos(an) * rr, cy + math.sin(an) * rr); c.line_to(cx + math.cos(an) * r, cy + math.sin(an) * r); c.stroke()
    g = cairo.LinearGradient(cx - r, 0, cx + r, 0); g.add_color_stop_rgb(0, *CYAN); g.add_color_stop_rgb(0.6, *YELLOW); g.add_color_stop_rgb(1, *PINK)
    k = min(1, v / vmax); c.set_source(g); c.set_line_width(22); c.arc(cx, cy, r - 60, math.pi, math.pi + math.pi * k); c.stroke()
    an = math.pi + math.pi * k + 0.03 * math.sin(t * 40)
    c.set_source_rgba(*PINK, a); c.set_line_width(12); c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.move_to(cx, cy); c.line_to(cx + math.cos(an) * (r - 40), cy + math.sin(an) * (r - 40)); c.stroke()
    c.set_source_rgba(1, 1, 1, a); c.arc(cx, cy, 20, 0, 2 * math.pi); c.fill()
    text(c, "{:,}".format(int(round(v / 10) * 10)), cx, cy - 80, 110, col=WHITE, alpha=a, stroke=10)
    text(c, label_, cx, cy + 60, 48, col=YELLOW, alpha=a, stroke=8)
    c.restore()


def window_fly(c, t):
    """a window frame flies past the camera (the 'sandblasted by a window' gag)"""
    if t <= 0: return
    k = min(1, t / 0.9); x = lerp(W + 400, -500, eout(k)); y = 720 + 60 * math.sin(k * 6); s = lerp(0.6, 1.4, k); rot = k * 2.2
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(s, s)
    c.set_source_rgba(0.95, 0.95, 1, 0.95); c.set_line_width(22); c.rectangle(-150, -170, 300, 340); c.stroke()
    c.set_line_width(14); c.move_to(0, -170); c.line_to(0, 170); c.move_to(-150, 0); c.line_to(150, 0); c.stroke()
    c.set_source_rgba(0.6, 0.9, 1, 0.35); c.rectangle(-140, -160, 280, 320); c.fill()
    c.set_source_rgba(1, 1, 1, 0.7); c.set_line_width(6); c.move_to(-110, -120); c.line_to(-40, -50); c.stroke()
    c.restore()
    c.set_source_rgba(1, 1, 1, 0.6); c.set_line_width(5)
    for j in range(6):
        yy = y - 160 + j * 64; c.move_to(x + 220, yy); c.line_to(x + 220 + 220 * (1 - k * 0.5), yy); c.stroke()


def thermo(c, x, y, h, v, t):
    if t <= 0: return
    a = ease(t / 0.2)
    c.set_source_rgba(1, 1, 1, 0.95 * a); rrect(c, x - 45, y - h, 90, h + 40, 45); c.fill(); c.arc(x, y + 40, 80, 0, 2 * math.pi); c.fill()
    g = cairo.LinearGradient(0, y, 0, y - h); g.add_color_stop_rgb(0, *hexc("FF3B2F")); g.add_color_stop_rgb(1, *YELLOW)
    c.set_source(g); c.arc(x, y + 40, 60, 0, 2 * math.pi); c.fill()
    hh = (h - 40) * min(1, v / 1000); rrect(c, x - 25, y - hh, 50, hh + 40, 25); c.fill()
    for j in range(6):
        yy = y - (h - 40) * j / 5; c.set_source_rgba(*INK, a); c.set_line_width(5); c.move_to(x + 45, yy); c.line_to(x + 75, yy); c.stroke()


def review_card(c, t, stars_k):
    panel(c, 110, 470, 860, 620, t, col=hexc("FFFFFF"), a=0.97, edge=YELLOW)
    if t <= 0.1: return
    a = ease((t - 0.1) / 0.2)
    text(c, "VISITOR REVIEWS", W / 2, 570, 50, col=PURPLE, alpha=a)
    for j in range(5):
        x = W / 2 - 320 + j * 160; y = 700; on = j == 0; k = back((stars_k - j * 0.08) / 0.3) if on else ease((stars_k - j * 0.08) / 0.3)
        if k <= 0: continue
        c.save(); c.translate(x, y); c.scale(k, k); c.move_to(0, -62)
        for i in range(1, 10):
            rr = 62 if i % 2 == 0 else 26; an = -math.pi / 2 + i * math.pi / 5; c.line_to(rr * math.cos(an), rr * math.sin(an))
        c.close_path()
        if on: c.set_source_rgb(*YELLOW); c.fill_preserve(); c.set_source_rgb(*hexc("E0A800"))
        else: c.set_source_rgb(0.85, 0.85, 0.88)
        c.set_line_width(5); c.stroke(); c.restore()
    text(c, "“Hot. Windy. Raining glass.”", W / 2, 850, 50, col=INK, alpha=a)
    text(c, "Would not visit.", W / 2, 940, 64, col=PINK, alpha=ease((stars_k - 0.6) / 0.3))
    text(c, "- Max, 1 star", W / 2, 1020, 38, col=(0.4, 0.4, 0.5), alpha=ease((stars_k - 0.8) / 0.3))


def orbit_scene(c, t, spinv=2.8):
    sx, sy = W / 2, 760
    star(c, sx, sy, 90, t)
    c.set_source_rgba(1, 1, 1, 0.35); c.set_line_width(3); c.set_dash([14, 12])
    c.save(); c.translate(sx, sy); c.scale(1, 0.42); c.arc(0, 0, 360, 0, 2 * math.pi); c.restore(); c.stroke(); c.set_dash([])
    an = t * spinv; px = sx + math.cos(an) * 360; py = sy + math.sin(an) * 360 * 0.42
    planet(c, px, py, 60, t, light=(sx - px, sy - py), glints=0)
    for j in range(14):   # motion trail
        a2 = an - j * 0.06; c.set_source_rgba(*CYAN, 0.25 * (1 - j / 14))
        c.arc(sx + math.cos(a2) * 360, sy + math.sin(a2) * 360 * 0.42, 50 * (1 - j / 18), 0, 2 * math.pi); c.fill()


def cake(c, x, y, s, t):
    c.save(); c.translate(x, y); c.scale(s, s)
    c.set_source_rgb(*hexc("FF9EC9")); rrect(c, -220, -60, 440, 180, 30); c.fill()
    c.set_source_rgb(*hexc("FFF0F6")); rrect(c, -170, -190, 340, 140, 26); c.fill()
    c.set_source_rgb(1, 1, 1)
    for j in range(9): c.arc(-200 + j * 50, -60, 26, 0, math.pi); c.fill()
    for j, xx in enumerate((-110, -40, 40, 110)):
        c.set_source_rgb(*CYAN); c.rectangle(xx - 10, -290, 20, 100); c.fill()
        fl = 1 + 0.2 * math.sin(t * 20 + j * 2)
        c.set_source_rgba(1, 0.75, 0.2, 1); c.save(); c.translate(xx, -315); c.scale(13 * fl, 24 * fl); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore(); c.fill()
    c.restore()


def confetti(c, t, seed=5, n=60):
    r = np.random.default_rng(seed)
    for j in range(n):
        x = r.random() * W + math.sin(t * 3 + j) * 30; y = ((r.random() * H) + t * (200 + 200 * r.random())) % H
        c.save(); c.translate(x, y); c.rotate(t * 4 + j); c.set_source_rgba(*[PINK, YELLOW, CYAN, WHITE][j % 4], 0.9)
        c.rectangle(-10, -5, 20, 10); c.fill(); c.restore()


def scorecard(c, t, pers_t):
    panel(c, 100, 430, 880, 700, t, col=INK, a=0.88, edge=PINK)
    if t <= 0.1: return
    a = ease((t - 0.1) / 0.2)
    text(c, "FINAL RATINGS", W / 2, 540, 60, col=YELLOW, alpha=a)
    text(c, "LOOKS", 170, 680, 56, col=WHITE, align="left", alpha=a)
    sticker(c, "10/10", 790, 662, 72, t - 0.4, bg=hexc("2FBF71"), outline=WHITE, ang=0.04, maxw=400)
    if pers_t > 0:
        text(c, "PERSONALITY", 170, 870, 56, col=WHITE, align="left", alpha=ease(pers_t / 0.2))
        sticker(c, "0/10", 820, 852, 72, pers_t - wt(18, "hurricane", 1.0), bg=hexc("E0303A"), outline=WHITE, ang=-0.05, maxw=300)
        if pers_t > wt(18, "windows", 2.0): text(c, "(hurricane + windows)", W / 2, 1020, 44, col=hexc("FFB3D6"), alpha=ease((pers_t - wt(18, "windows", 2.0)) / 0.3))



GREEN = hexc("2FBF71"); RED = hexc("E0303A"); ACID = hexc("C8E83A")
_IMG = {}
VR = {"clouds": 671.3, "radar": 695.0}


def _img(name):
    if name not in _IMG: _IMG[name] = cairo.ImageSurface.create_from_png(name)
    return _IMG[name]
def heart(c, x, y, r, col, a=1.0):
    c.save(); c.translate(x, y); c.set_source_rgba(*col, a)
    c.move_to(0, r * 0.9); c.curve_to(-r * 1.6, -r * 0.2, -r * 0.7, -r * 1.3, 0, -r * 0.45)
    c.curve_to(r * 0.7, -r * 1.3, r * 1.6, -r * 0.2, 0, r * 0.9); c.close_path(); c.fill(); c.restore()

def series_banner(c, t, y=300):
    if t <= 0: return
    sticker(c, "PLANET REVIEWS", W / 2, y, 64, t, bg=YELLOW, fg=INK, outline=PINK, ang=-0.03)

def neutron_star(c, cx, cy, r, t, k=1.0):
    a = t * 2.2
    for s_ in (1, -1):
        c.save(); c.translate(cx, cy); c.rotate(a + (0 if s_ > 0 else math.pi))
        g = cairo.LinearGradient(0, 0, 0, -700); g.add_color_stop_rgba(0, *CYAN, 0.8 * k); g.add_color_stop_rgba(1, *CYAN, 0)
        c.move_to(-12, 0); c.line_to(-90, -700); c.line_to(90, -700); c.line_to(12, 0); c.close_path(); c.set_source(g); c.fill(); c.restore()
    for i in range(6, 0, -1):
        c.set_source_rgba(0.7, 0.9, 1, 0.08 * k); c.arc(cx, cy, r * (1 + i * 0.4), 0, 2 * math.pi); c.fill()
    g = cairo.RadialGradient(cx - r * 0.3, cy - r * 0.3, 0, cx, cy, r)
    g.add_color_stop_rgba(0, 1, 1, 1, k); g.add_color_stop_rgba(1, 0.55, 0.8, 1, k)
    c.set_source(g); c.arc(cx, cy, r, 0, 2 * math.pi); c.fill()



# ================= 003: Planet Reviews x Real or Fake? — the neutron star =================
GREENB = hexc("22C55E"); ORANGE = hexc("FF5A1F")


def photo_panel(c, name, t, x=60, y=300, w=960, h=1040, zoom=0.02, fx=0.5, fy=0.5, edge=PINK, a=1.0, k0=1.0):
    """real image inside a rounded panel (never full-bleed: keeps edges lit for the Facebook border check)"""
    S = _img(name); k = max(w / S.get_width(), h / S.get_height()) * k0 * (1 + zoom * t)
    c.save(); rrect(c, x, y, w, h, 34); c.clip()
    c.translate(x + w / 2, y + h / 2); c.scale(k, k); c.translate(-S.get_width() * fx, -S.get_height() * fy)
    c.set_source_surface(S, 0, 0); c.get_source().set_filter(cairo.FILTER_GOOD); c.paint_with_alpha(a); c.restore()
    c.set_source_rgba(*edge, a); c.set_line_width(6); rrect(c, x, y, w, h, 34); c.stroke()


def mag_star_xy(x=60, y=300, w=960, h=1040, t=0, zoom=0.02, fx=0.5, fy=0.5, k0=1.0):
    """screen position + radius of the neutron star inside ns_magnetar.png (star at 380,749 r~89 in 760x1080)"""
    S = _img("ns_magnetar.png"); k = max(w / S.get_width(), h / S.get_height()) * k0 * (1 + zoom * t)
    return x + w / 2 + (380 - S.get_width() * fx) * k, y + h / 2 + (749 - S.get_height() * fy) * k, 89 * k


def buzzer(c, x, y, r, label_, col, t, pressed=0.0, glow=0.0):
    if t <= 0: return
    k = back(t / 0.3); p = ease(pressed / 0.12) if pressed > 0 else 0
    c.save(); c.translate(x, y); c.scale(k, k)
    if glow > 0:
        for i in range(5, 0, -1):
            c.set_source_rgba(*col, 0.12 * glow); c.arc(0, 0, r * (1 + i * 0.12), 0, 2 * math.pi); c.fill()
    c.set_source_rgb(0.2, 0.2, 0.25); c.save(); c.scale(1, 0.45); c.arc(0, r * 0.9, r * 1.15, 0, 2 * math.pi); c.restore(); c.fill()
    dy = r * 0.18 * p
    c.set_source_rgb(*[v * 0.7 for v in col]); c.save(); c.scale(1, 0.45); c.arc(0, r * 0.55 + dy * 2, r, 0, 2 * math.pi); c.restore(); c.fill()
    c.rectangle(-r, -r * 0.25 + dy, 2 * r, r * 0.5); c.fill()
    g = cairo.RadialGradient(-r * 0.3, -r * 0.45 + dy, r * 0.1, 0, -r * 0.25 + dy, r)
    g.add_color_stop_rgb(0, *[min(1, v * 1.4 + 0.2) for v in col]); g.add_color_stop_rgb(1, *col)
    c.set_source(g); c.save(); c.translate(0, -r * 0.25 + dy); c.scale(1, 0.45); c.arc(0, 0, r, 0, 2 * math.pi); c.restore(); c.fill()
    c.restore()
    text(c, label_, x, y + r * 0.95 + 40, 60 * k, col=WHITE, stroke=8)


def verdict(c, word, t, y=820):
    """big REAL (green check) / FAKE (red X) result card"""
    if t <= 0: return
    col = GREENB if word == "REAL" else RED
    k = back(t / 0.3)
    c.save(); c.translate(W / 2, y); c.rotate(-0.05); c.scale(k, k)
    c.set_source_rgba(0, 0, 0, 0.5); rrect(c, -330, -150, 680, 320, 40); c.fill()
    c.set_source_rgb(*col); rrect(c, -340, -165, 680, 320, 40); c.fill()
    c.set_source_rgb(*YELLOW); c.set_line_width(10); rrect(c, -340, -165, 680, 320, 40); c.stroke()
    c.set_source_rgb(1, 1, 1); c.set_line_width(30); c.set_line_cap(cairo.LINE_CAP_ROUND)
    if word == "REAL": c.move_to(-260, -10); c.line_to(-205, 50); c.line_to(-110, -70); c.stroke()
    else: c.move_to(-250, -60); c.line_to(-140, 50); c.move_to(-140, -60); c.line_to(-250, 50); c.stroke()
    text(c, word, 90, 45, 150, col=WHITE, stroke=10)
    c.restore()


def sugar_cube(c, x, y, s, t=0, sparkle=True):
    c.save(); c.translate(x, y); c.scale(s, s)
    c.set_source_rgba(0, 0, 0, 0.35); c.move_to(-60, 70); c.line_to(80, 70); c.line_to(110, 50); c.line_to(-30, 50); c.close_path(); c.fill()
    c.set_source_rgb(1, 1, 1); c.move_to(-70, -40); c.line_to(50, -40); c.line_to(50, 70); c.line_to(-70, 70); c.close_path(); c.fill()
    c.set_source_rgb(0.86, 0.88, 0.95); c.move_to(50, -40); c.line_to(90, -70); c.line_to(90, 40); c.line_to(50, 70); c.close_path(); c.fill()
    c.set_source_rgb(0.95, 0.96, 1); c.move_to(-70, -40); c.line_to(-30, -70); c.line_to(90, -70); c.line_to(50, -40); c.close_path(); c.fill()
    r = np.random.default_rng(4); c.set_source_rgba(0.75, 0.78, 0.88, 1)
    for _ in range(30): c.arc(-65 + r.random() * 110, -35 + r.random() * 100, 2.5, 0, 2 * math.pi); c.fill()
    if sparkle:
        for j in range(3):
            a = max(0, math.sin(t * 4 + j * 2)) ** 4; px, py = (-90, 100, 20)[j], (-90, -20, 95)[j]
            c.set_source_rgba(*CYAN, a); c.set_line_width(5); c.move_to(px - 22, py); c.line_to(px + 22, py); c.move_to(px, py - 22); c.line_to(px, py + 22); c.stroke()
    c.restore()


def scale_dial(c, x, y, t, val, crack=0.0):
    """bathroom scale under the sugar cube; display counts up"""
    c.save(); c.translate(x, y)
    c.set_source_rgba(0, 0, 0, 0.4); rrect(c, -300, 20, 610, 150, 40); c.fill()
    c.set_source_rgb(*hexc("EDEAF6")); rrect(c, -310, 0, 620, 150, 40); c.fill()
    c.set_source_rgb(*INK); rrect(c, -270, 30, 540, 90, 16); c.fill()
    text(c, val, 0, 92, 44, col=hexc("FF5FB0"))
    if crack > 0:
        c.set_source_rgba(*INK, min(1, crack * 3)); c.set_line_width(6)
        c.move_to(-300, 0); c.line_to(-280, 60); c.line_to(-295, 100); c.line_to(-275, 150); c.stroke()
        c.move_to(295, 0); c.line_to(280, 70); c.line_to(298, 150); c.stroke()
    c.restore()


def donut(c, x, y, r, t):
    c.save(); c.translate(x, y); c.rotate(t * 0.8)
    c.set_source_rgb(*hexc("E0A060")); c.arc(0, 0, r, 0, 2 * math.pi); c.arc_negative(0, 0, r * 0.38, 2 * math.pi, 0); c.fill()
    c.set_source_rgb(*PINK); c.arc(0, 0, r * 0.88, 0, 2 * math.pi); c.arc_negative(0, 0, r * 0.45, 2 * math.pi, 0); c.fill()
    r_ = np.random.default_rng(8)
    for j in range(18):
        a = r_.random() * 2 * math.pi; d = r * (0.52 + 0.3 * r_.random())
        c.set_source_rgb(*[YELLOW, CYAN, WHITE][j % 3]); c.save(); c.translate(math.cos(a) * d, math.sin(a) * d); c.rotate(r_.random() * 3)
        rrect(c, -12, -4, 24, 8, 4); c.fill(); c.restore()
    c.restore()


def skyline(c, x0, y0, w, t, k=1.0, col=hexc("2A1C55"), lit=True):
    r = np.random.default_rng(12); x = x0
    while x < x0 + w:
        bw = 40 + r.random() * 60; bh = (80 + r.random() * 260) * k
        c.set_source_rgb(*col); c.rectangle(x, y0 - bh, bw - 6, bh); c.fill()
        if lit:
            for wy in range(int(bh // 30)):
                for wx in range(int((bw - 16) // 18)):
                    if r.random() < 0.45:
                        c.set_source_rgba(1, 0.9, 0.5, 0.8); c.rectangle(x + 6 + wx * 18, y0 - bh + 10 + wy * 30, 8, 12); c.fill()
        x += bw


def couch(c, x, y, s, t, k):
    """couch wedged in a doorway (wiggles)"""
    c.save(); c.translate(x, y); c.scale(s, s)
    c.set_source_rgb(*hexc("8A6A4A")); c.rectangle(-170, -330, 40, 520); c.fill(); c.rectangle(130, -330, 40, 520); c.fill(); c.rectangle(-170, -330, 340, 40); c.fill()
    c.rotate(-0.5 + 0.06 * math.sin(t * 10) * k)
    c.set_source_rgb(*PINK); rrect(c, -300, -60, 600, 130, 30); c.fill()
    c.set_source_rgb(*hexc("D02C7E")); rrect(c, -300, -140, 600, 100, 30); c.fill()
    rrect(c, -330, -110, 70, 190, 26); c.fill(); rrect(c, 260, -110, 70, 190, 26); c.fill()
    c.restore()


def blender(c, x, y, s, t, spin=1.0):
    c.save(); c.translate(x, y); c.scale(s, s)
    c.set_source_rgb(*hexc("3A3A48")); rrect(c, -150, 120, 300, 160, 30); c.fill()
    c.set_source_rgb(*RED); c.arc(0, 200, 34, 0, 2 * math.pi); c.fill()
    c.set_source_rgba(0.75, 0.95, 1, 0.35); c.move_to(-130, -260); c.line_to(130, -260); c.line_to(100, 120); c.line_to(-100, 120); c.close_path(); c.fill()
    c.set_source_rgba(1, 1, 1, 0.8); c.set_line_width(6); c.move_to(-130, -260); c.line_to(130, -260); c.line_to(100, 120); c.line_to(-100, 120); c.close_path(); c.stroke()
    c.set_source_rgba(*PINK, 0.85); c.move_to(-108, 0); c.line_to(108, 0); c.line_to(100, 115); c.line_to(-100, 115); c.close_path(); c.fill()
    a = t * 30 * spin
    c.set_source_rgb(0.9, 0.9, 0.95)
    for j in range(2):
        c.save(); c.translate(0, 95); c.scale(1, 0.3); c.rotate(a + j * math.pi / 2); rrect(c, -80, -10, 160, 20, 10); c.restore(); c.fill()
    for j in range(4):
        c.set_source_rgba(1, 1, 1, 0.6); c.set_line_width(5); c.arc(0, 40, 140 + j * 18, a + j, a + j + 0.6); c.stroke()
    c.restore()


def smoothie(c, x, y, s, t):
    c.save(); c.translate(x, y); c.scale(s, s)
    c.set_source_rgb(*PINK); c.move_to(-110, -150); c.line_to(110, -150); c.line_to(80, 170); c.line_to(-80, 170); c.close_path(); c.fill()
    c.set_source_rgb(1, 1, 1); c.set_line_width(8); c.move_to(-110, -150); c.line_to(110, -150); c.line_to(80, 170); c.line_to(-80, 170); c.close_path(); c.stroke()
    c.set_source_rgb(*CYAN); c.set_line_width(16); c.move_to(30, -150); c.line_to(80, -300); c.stroke()
    # heartbeat line across the cup
    ph = (t * 1.2) % 1.0
    c.set_source_rgb(1, 1, 1); c.set_line_width(9); c.set_line_join(cairo.LINE_JOIN_ROUND)
    pts = [(-95, 10), (-45, 10), (-25, -50), (0, 70), (20, -10), (40, 10), (95, 10)]
    n = max(2, int(len(pts) * min(1, ph * 2) + 1)); c.move_to(*pts[0])
    for p in pts[1:n]: c.line_to(*p)
    c.stroke()
    c.restore()


def credit_card(c, x, y, s, ang, a=1.0):
    c.save(); c.translate(x, y); c.rotate(ang); c.scale(s, s)
    c.set_source_rgba(*hexc("2F7BE8"), a); rrect(c, -170, -105, 340, 210, 22); c.fill()
    c.set_source_rgba(*YELLOW, a); rrect(c, -130, -50, 60, 46, 8); c.fill()
    c.set_source_rgba(0.1, 0.1, 0.15, a); c.rectangle(-170, -80, 340, 0); c.fill()
    for j in range(4): text(c, "••••", -105 + j * 75, 50, 34, col=WHITE, alpha=a)
    c.restore()


def angry_brows(c, x, y, r, t, k):
    if k <= 0: return
    c.save(); c.set_source_rgba(0.1, 0.0, 0.05, k); c.set_line_width(r * 0.22); c.set_line_cap(cairo.LINE_CAP_ROUND)
    wob = 0.04 * math.sin(t * 14)
    c.move_to(x - r * 0.75, y - r * 0.55 - r * wob); c.line_to(x - r * 0.12, y - r * 0.2); c.stroke()
    c.move_to(x + r * 0.75, y - r * 0.55 + r * wob); c.line_to(x + r * 0.12, y - r * 0.2); c.stroke()
    c.restore()


def radio_chart(c, t, k):
    """1967-style chart recorder: paper scrolls, regular blips"""
    panel(c, 90, 520, 900, 520, k + 0.3, col=hexc("F3EBD2"), a=0.98, edge=YELLOW)
    if k <= 0: return
    c.save(); rrect(c, 110, 540, 860, 480, 20); c.clip()
    c.set_source_rgba(0.6, 0.75, 0.6, 0.5); c.set_line_width(2)
    off = (t * 220) % 60
    for j in range(17): c.move_to(110 + j * 60 - off, 540); c.line_to(110 + j * 60 - off, 1020); c.stroke()
    c.set_source_rgb(*INK); c.set_line_width(5); c.move_to(110, 800)
    for xx in range(110, 971, 4):
        u = xx + t * 220; ph = (u % 300) / 300
        yy = 800 + 6 * math.sin(u * 0.37) + (-200 * math.exp(-((ph - 0.5) * 40) ** 2))
        c.line_to(xx, yy)
    c.stroke(); c.restore()


def alien(c, x, y, s, t, k):
    """original cartoon 'little green man' (generic, waving)"""
    if k <= 0: return
    sc = back(k / 0.35) * s
    c.save(); c.translate(x, y + 8 * math.sin(t * 5)); c.scale(sc, sc)
    G = hexc("5EE06A")
    c.set_source_rgb(*G); rrect(c, -55, 40, 110, 150, 40); c.fill()
    c.set_line_width(22); c.set_line_cap(cairo.LINE_CAP_ROUND); c.set_source_rgb(*G)
    c.move_to(-50, 80); c.line_to(-110, 30 + 25 * math.sin(t * 9)); c.stroke()
    c.move_to(50, 80); c.line_to(100, 140); c.stroke()
    c.save(); c.scale(1, 0.85); c.arc(0, -40, 110, 0, 2 * math.pi); c.restore(); c.fill()
    c.set_line_width(8); c.move_to(-40, -120); c.line_to(-70, -190); c.move_to(40, -120); c.line_to(70, -190); c.stroke()
    c.arc(-70, -195, 14, 0, 2 * math.pi); c.fill(); c.arc(70, -195, 14, 0, 2 * math.pi); c.fill()
    c.set_source_rgb(0.05, 0.05, 0.1)
    for sx in (-1, 1):
        c.save(); c.translate(sx * 42, -45); c.rotate(sx * 0.4); c.scale(30, 20); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore(); c.fill()
    c.set_source_rgb(1, 1, 1); c.arc(-48, -52, 6, 0, 2 * math.pi); c.fill(); c.arc(36, -52, 6, 0, 2 * math.pi); c.fill()
    c.set_source_rgb(0.05, 0.05, 0.1); c.set_line_width(6); c.arc(0, 0, 26, 0.3, math.pi - 0.3); c.stroke()
    c.restore()


def uranus(c, cx, cy, r, t):
    S = _img("uranus.png"); k = r / 515.0
    g = cairo.RadialGradient(cx, cy, r * 0.95, cx, cy, r * 1.3); g.add_color_stop_rgba(0, *CYAN, 0.3); g.add_color_stop_rgba(1, *CYAN, 0)
    c.set_source(g); c.arc(cx, cy, r * 1.32, 0, 2 * math.pi); c.fill()
    c.save(); c.arc(cx, cy, r, 0, 2 * math.pi); c.clip(); c.translate(cx, cy); c.scale(k, k); c.translate(-640, -640)
    c.set_source_surface(S, 0, 0); c.get_source().set_filter(cairo.FILTER_GOOD); c.paint(); c.restore()


def egg(c, x, y, s, t):
    c.save(); c.translate(x, y); c.scale(s, s)
    c.set_source_rgb(*hexc("F4EBD6")); c.save(); c.scale(1, 1.3); c.arc(0, 0, 70, 0, 2 * math.pi); c.restore(); c.fill()
    c.set_source_rgb(*hexc("9AAE2A")); c.set_line_width(8); c.set_line_cap(cairo.LINE_CAP_ROUND)
    for j in range(3):
        xx = -50 + j * 50; c.move_to(xx, -110)
        for q in range(1, 8): c.line_to(xx + 14 * math.sin(t * 6 + q + j), -110 - q * 16)
        c.stroke()
    c.restore()


def hook_frame(c, t):
    background(c, t)
    photo_panel(c, "ns_magnetar.png", t, zoom=0.025, fy=0.6)


# ---------------- scenes (one per ORIGINAL line index) ----------------
def s0(c, t, d):   # F A sugar cube of this star weighs one billion tons.
    hook_frame(c, t)
    sx, sy, sr = mag_star_xy(t=t, zoom=0.025, fy=0.6)
    sticker(c, "1 SUGAR CUBE", W / 2, 400, 110, t + 0.4, ang=-0.05)
    TB = wt(0, "billion", 1.8)
    if t > wt(0, "star", 1.0) - 0.1: arrow(c, 300, 560, sx - sr - 30, sy - sr - 10, col=YELLOW, w=14, k=eout((t - wt(0, "star", 1.0) + 0.1) / 0.3))
    if t > TB: sticker(c, "= 1 BILLION TONS", W / 2, 1230, 96, t - TB, bg=YELLOW, fg=INK, outline=PINK, ang=0.04)
    tag(c, "Image: NASA/JPL-Caltech (neutron star, artist's concept)", t - 0.6, y=1320)


def s1(c, t, d):   # M One billion tons? not a sugar cube, that's a cheat day!
    background(c, t)
    TC = wt(1, "cheat", 2.6)
    v = counter(t, 0, 1_000_000_000, 1.4) + " TONS"
    scale_dial(c, W / 2, 980, t, v, crack=(t - 1.2) if t > 1.2 else 0)
    sugar_cube(c, W / 2, 900, 1.1 + 0.04 * math.sin(t * 20) * (t > 1.2), t)
    sticker(c, "1 BILLION TONS?", W / 2, 430, 100, t + 0.2, bg=PINK)
    if t > TC:
        tt = t - TC
        for j, (dx, dy) in enumerate(((-300, 650), (300, 640))): donut(c, W / 2 + dx, dy + 30 * math.sin(t * 3 + j), 95 * back(tt / 0.3), t)
        stamp(c, "CHEAT DAY", W / 2, 1230, tt, col=YELLOW, size=110, ang=-0.06)


def s2(c, t, d):   # F Buzzers ready! It's Planet Reviews, today's guest a neutron star. Real or fake?
    background(c, t)
    TP = wt(2, "planet", 1.6); TN = wt(2, "neutron", 3.4); TR = wt(2, "real", 4.8)
    if t < TN:
        c.set_source_rgba(*PINK, 1); c.set_line_width(26); c.rectangle(60, 290, W - 120, 1000); c.stroke()
        text(c, "ORBIT GOSSIP", W / 2, 420, 120, col=WHITE, stroke=14)
        buzzer(c, 300, 820, 150, "REAL", GREENB, t + 0.1, glow=0.6 + 0.4 * math.sin(t * 8))
        buzzer(c, 780, 820, 150, "FAKE", RED, t, glow=0.6 + 0.4 * math.cos(t * 8))
        if t > TP: series_banner(c, t - TP, y=1180)
    else:
        tt = t - TN
        photo_panel(c, "ns_pulsar.png", tt, x=110, y=420, w=860, h=760, zoom=0.03, edge=CYAN)
        series_banner(c, 1, y=330)
        sticker(c, "TODAY'S GUEST: NEUTRON STAR", W / 2, 1110, 64, tt, bg=PURPLE, outline=CYAN, ang=0.03)
        if t > TR:
            sticker(c, "REAL or FAKE?", W / 2, 1270, 100, t - TR, bg=YELLOW, fg=INK, outline=PINK, ang=-0.04)
        tag(c, "Image: NASA/JPL-Caltech (pulsar, artist's concept)", tt - 0.4, y=1340)


def s3(c, t, d):   # F Claim one. heavier than our Sun, ~12 miles across. size of a city.
    background(c, t)
    TH = wt(3, "heavier", 0.9); TT = wt(3, "twelve", 2.9); TC = wt(3, "city", 4.6)
    sticker(c, "CLAIM #1", W / 2, 360, 100, t + 0.2, bg=PINK)
    if t < TC - 0.2:
        photo_panel(c, "crab.png", t, x=90, y=470, w=900, h=760, zoom=0.03, edge=YELLOW)
        tag(c, "Crab Nebula (a neutron star lives inside) · NASA, ESA, J. Hester & A. Loll (CC BY 4.0)", t - 0.3, y=1262, x=100)
        if t > TH: sticker(c, "HEAVIER THAN THE SUN", W / 2, 620, 74, t - TH, bg=ORANGE, outline=YELLOW, ang=0.03)
        if t > TT: sticker(c, "~12 MILES (20 KM) WIDE", W / 2, 1120, 78, t - TT, bg=PURPLE, outline=CYAN, ang=-0.03)
    else:
        tt = t - TC + 0.2
        skyline(c, 80, 1200, 920, t, k=1.0)
        r = lerp(260, 120, eout(tt / 0.6)); neutron_star(c, W / 2, lerp(760, 900, eout(tt / 0.6)), r, t, k=1)
        sticker(c, "SIZE OF A CITY", W / 2, 520, 96, tt, bg=YELLOW, fg=INK, outline=PINK, ang=-0.03)
        tag(c, "Source: NASA (heavier than the Sun, as small as a city)", tt - 0.2, y=1262)


def s4(c, t, d):   # M Fake. Nobody fits a whole Sun into a city. can't fit my couch in my apartment.
    background(c, t, dim=0.9)
    TC = wt(4, "couch", 3.0)
    if t < TC - 0.1:
        buzzer(c, W / 2, 780, 190, "FAKE", RED, t + 0.3, pressed=t, glow=1.0)
        sticker(c, "FAKE!", W / 2, 420, 120, t, bg=RED, outline=YELLOW)
        if t > wt(4, "sun", 1.2): text(c, "a whole SUN in a CITY?", W / 2, 1230, 64, col=YELLOW, stroke=10, alpha=ease((t - wt(4, "sun", 1.2)) / 0.3))
    else:
        tt = t - TC + 0.1
        couch(c, W / 2, 860, 1.25, t, 1)
        sticker(c, "MY COUCH", W / 2, 400, 104, tt, bg=PINK)
        if t > wt(4, "apartment", 4.0): stamp(c, "WON'T FIT", W / 2, 1230, t - wt(4, "apartment", 4.0), col=YELLOW, size=100, ang=-0.06)


def s5(c, t, d):   # F Real! Squished down to about the size of Manhattan.
    background(c, t)
    TM = wt(5, "manhattan", 1.8)
    if t < TM - 0.15:
        verdict(c, "REAL", t + 0.05, y=800); confetti(c, t)
    else:
        tt = t - TM + 0.15
        skyline(c, 80, 1150, 920, t, k=1.25)
        c.set_source_rgba(*CYAN, 0.25 + 0.1 * math.sin(t * 6)); c.arc(W / 2, 880, 440 * eout(tt / 0.4), 0, 2 * math.pi); c.fill()
        c.set_source_rgba(*CYAN, 1); c.set_line_width(8); c.arc(W / 2, 880, 440 * eout(tt / 0.4), 0, 2 * math.pi); c.stroke()
        sticker(c, "REAL!", W / 2, 360, 110, 1, bg=GREENB, outline=YELLOW)
        sticker(c, "~MANHATTAN-SIZED", W / 2, 1250, 84, tt, bg=YELLOW, fg=INK, outline=PINK, ang=0.03)
        tag(c, "Source: NASA Goddard (about 20 km / 12.5 mi across)", tt - 0.3, y=1330)


def s6(c, t, d):   # F Claim two. fastest one spins 43,000 times a minute.
    background(c, t)
    TF = wt(6, "fastest", 0.9); TN = wt(6, "forty", 1.8)
    photo_panel(c, "ns_pulsar.png", t, x=90, y=470, w=900, h=780, zoom=0.03, edge=CYAN)
    cx, cy = 90 + 450 + (540 - 540) * 1, 470 + 390 + (516 - 500) * (780 / 1000)
    sp = 1 + 9 * ease((t - TN) / 1.0) if t > TN else 1
    c.save(); rrect(c, 90, 470, 900, 780, 34); c.clip()
    for s_ in (1, -1):
        c.save(); c.translate(cx, cy); c.rotate(t * 2.2 * sp + (0 if s_ > 0 else math.pi))
        g = cairo.LinearGradient(0, 0, 0, -700); g.add_color_stop_rgba(0, 1, 0.75, 1, 0.55); g.add_color_stop_rgba(1, 1, 0.75, 1, 0)
        c.move_to(-14, 0); c.line_to(-110, -700); c.line_to(110, -700); c.line_to(14, 0); c.close_path(); c.set_source(g); c.fill(); c.restore()
    c.restore()
    sticker(c, "CLAIM #2", W / 2, 360, 100, t + 0.2, bg=PINK)
    if t > TF: sticker(c, "FASTEST PULSAR", W / 2, 600, 70, t - TF, bg=PURPLE, outline=CYAN, ang=0.03)
    if t > TN:
        sticker(c, counter(t - TN, 0, 43000, 0.9) + " SPINS / MIN", W / 2, 1180, 88, t - TN, bg=YELLOW, fg=INK, outline=PINK, ang=-0.03)
        tag(c, "PSR J1748-2446ad · Source: NASA · Image: NASA/JPL-Caltech", t - TN - 0.3, y=1300)


def s7(c, t, d):   # M Okay, that's fake. faster than my blender.
    background(c, t, dim=0.9)
    TB = wt(7, "blender", 1.6)
    buzzer(c, 280, 1080, 110, "FAKE", RED, t + 0.3, pressed=t - wt(7, "fake", 0.5), glow=1.0)
    blender(c, 700, 820, 1.1, t, spin=1.0)
    sticker(c, "FAKE?", W / 2, 400, 110, t - wt(7, "fake", 0.5), bg=RED, outline=YELLOW)
    if t > TB: stamp(c, "MY BLENDER", 700, 1230, t - TB, col=YELLOW, size=80, ang=-0.05)


def s8(c, t, d):   # F Real! Twice as fast as your blender. smoothie with a pulse.
    background(c, t)
    TT = wt(8, "twice", 0.6); TS = wt(8, "smoothie", 2.9)
    if t < TS - 0.1:
        sticker(c, "REAL!", W / 2, 380, 120, t + 0.1, bg=GREENB, outline=YELLOW)
        blender(c, 330, 860, 0.85, t, spin=1.0); neutron_star(c, 760, 830, 70, t * 2, k=1)
        if t > TT: sticker(c, "2× YOUR BLENDER", W / 2, 1220, 92, t - TT, bg=YELLOW, fg=INK, outline=PINK, ang=0.03)
        if t > TT: tag(c, "Source: NASA (twice a household blender)", t - TT - 0.3, y=1320)
    else:
        tt = t - TS + 0.1
        smoothie(c, W / 2, 860, 1.5 * back(tt / 0.35), t)
        sticker(c, "SMOOTHIE", W / 2, 400, 110, tt, bg=PINK)
        if t > wt(8, "pulse", TS + 0.6): sticker(c, "...WITH A PULSE", W / 2, 1230, 90, t - wt(8, "pulse", TS + 0.6), bg=PURPLE, outline=CYAN, ang=0.04)


def s9(c, t, d):   # F Claim three. magnetic field trillions of times stronger than Earth's.
    background(c, t)
    TM = wt(9, "magnetic", 1.0); TT = wt(9, "trillions", 2.2)
    photo_panel(c, "ns_magnetar.png", t, x=90, y=470, w=900, h=820, zoom=0.03, fy=0.6, edge=GREENB)
    sticker(c, "CLAIM #3", W / 2, 360, 100, t + 0.2, bg=PINK)
    if t > TM: sticker(c, "MAGNETIC FIELD", W / 2, 600, 76, t - TM, bg=hexc("1E8F4E"), outline=YELLOW, ang=0.03)
    if t > TT:
        sticker(c, "TRILLIONS × EARTH'S", W / 2, 1180, 88, t - TT, bg=YELLOW, fg=INK, outline=PINK, ang=-0.03)
        mini_globe(c, 900, 1000, 60, t)
        tag(c, "Source: NASA · Image: NASA/JPL-Caltech (magnetar concept)", t - TT - 0.3, y=1320)


def s10(c, t, d):  # M Fine. Real. Keep her away from my credit cards.
    background(c, t, dim=0.9)
    TR = wt(10, "real", 0.6); TC = wt(10, "credit", 1.8)
    if t < TC - 0.1:
        buzzer(c, W / 2, 780, 190, "REAL", GREENB, t + 0.3, pressed=t - TR, glow=1.0)
        if t > TR: sticker(c, "FINE. REAL.", W / 2, 420, 110, t - TR, bg=GREENB, outline=YELLOW)
    else:
        tt = t - TC + 0.1
        neutron_star(c, 820, 560, 70, t, k=1)
        c.set_source_rgba(*GREENB, 0.8); c.set_line_width(4)
        for j in range(5):
            c.save(); c.translate(820, 560); c.scale(1, 0.5 + j * 0.1); c.arc(0, 0, 160 + j * 70, 0, 2 * math.pi); c.restore(); c.stroke()
        k = eout(tt / 1.2); jitter = 10 * math.sin(t * 40)
        credit_card(c, lerp(260, 520, k) + jitter, lerp(1000, 820, k), 1.0, -0.3 + 0.6 * k)
        sticker(c, "KEEP AWAY!", W / 2, 1230, 100, tt, bg=RED, outline=YELLOW, ang=-0.04)
        sticker(c, "MY CREDIT CARDS", W / 2, 380, 84, tt + 0.1, bg=PINK)


def s11(c, t, d):  # F (whisper) a magnetar, her angry cousin, is another 1,000 times stronger.
    background(c, t, dim=0.85)
    TA = wt(11, "angry", 1.4); TT = wt(11, "thousand", 3.3)
    photo_panel(c, "ns_magnetar.png", t, x=60, y=330, w=960, h=1000, zoom=0.05, fy=0.62, k0=1.15, edge=RED)
    sx, sy, sr = mag_star_xy(x=60, y=330, w=960, h=1000, t=t, zoom=0.05, fy=0.62, k0=1.15)
    sticker(c, "MAGNETAR", W / 2, 430, 100, t + 0.1, bg=PURPLE, outline=CYAN)
    if t > TA:
        angry_brows(c, sx, sy, sr, t, ease((t - TA) / 0.2))
        sticker(c, "ANGRY COUSIN", W / 2, 620, 80, t - TA, bg=RED, outline=YELLOW, ang=0.04)
    if t > TT:
        sticker(c, "1,000× STRONGER", W / 2, 1200, 96, t - TT, bg=YELLOW, fg=INK, outline=PINK, ang=-0.03)
        tag(c, "Source: NASA Goddard (magnetars)", t - TT - 0.3, y=1300, x=90)


def s13(c, t, d):  # F Final claim. 1967 caught her blinking, nicknamed the signal little green men.
    background(c, t)
    TY = wt(13, "nineteen", 2.6); TB = wt(13, "blinking", 2.2); TL = wt(13, "little", 5.6)
    sticker(c, "FINAL CLAIM", W / 2, 360, 100, t + 0.2, bg=PINK)
    if t < TL - 0.15:
        radio_chart(c, t, t)
        if t > TB: text(c, "BEEP · BEEP · BEEP", W / 2, 1110, 64, col=YELLOW, stroke=10, alpha=ease((t - TB) / 0.3))
        if t > TY: stamp(c, "1967", 840, 560, t - TY, col=RED, size=110, ang=0.12)
        if t > TY: tag(c, "Source: NASA (first pulsar signal, nicknamed LGM-1)", t - TY - 0.3, y=1262, x=100)
    else:
        tt = t - TL + 0.15
        radio_chart(c, t, 1); c.set_source_rgba(*SPACE, 0.55); rrect(c, 90, 520, 900, 520, 26); c.fill()
        alien(c, W / 2, 820, 1.4, t, tt)
        sticker(c, "LITTLE GREEN MEN", W / 2, 1210, 80, tt, bg=GREENB, outline=YELLOW, ang=0.03, maxw=880)


def s15(c, t, d):  # F Real. Final rating: 10/10 drama. 0/10 as a sweetener.
    background(c, t)
    TF = wt(15, "final", 0.6); TD = wt(15, "drama", 2.2); TS = wt(15, "zero", 2.8)
    sticker(c, "REAL!", W / 2, 360, 110, t + 0.1, bg=GREENB, outline=YELLOW)
    if t > TF:
        tt = t - TF
        panel(c, 100, 470, 880, 640, tt, col=INK, a=0.9, edge=PINK)
        if tt > 0.1:
            a = ease((tt - 0.1) / 0.2)
            text(c, "FINAL RATING", W / 2, 580, 60, col=YELLOW, alpha=a)
            text(c, "DRAMA", 170, 730, 58, col=WHITE, align="left", alpha=a)
            if t > TD - 0.3: sticker(c, "10/10", 790, 712, 76, t - TD + 0.3, bg=GREENB, outline=WHITE, ang=0.04, maxw=400)
            if t > TS - 0.2:
                text(c, "SWEETENER", 170, 920, 58, col=WHITE, align="left", alpha=ease((t - TS + 0.2) / 0.2))
                sticker(c, "0/10", 810, 902, 76, t - wt(15, "sweetener", TS + 0.8), bg=RED, outline=WHITE, ang=-0.05, maxw=300)
                sugar_cube(c, W / 2, 1040, 0.5, t)


def s16(c, t, d):  # F Tomorrow on Planet Reviews: clouds smell like rotten eggs. Follow!
    background(c, t)
    TC = wt(16, "clouds", 2.6); TE = wt(16, "rotten", 3.4); TF = wt(16, "follow", 4.6)
    sticker(c, "TOMORROW", W / 2, 330, 104, t + 0.1, bg=PINK, ang=-0.05)
    series_banner(c, t - wt(16, "planet", 0.6), y=470)
    uranus(c, W / 2, 830, 250 * eout((t + 0.2) / 0.5), t)
    if t > TC: sticker(c, "SMELLY CLOUDS", W / 2, 640, 70, t - TC, bg=PURPLE, outline=CYAN, ang=0.04)
    if t > TE:
        egg(c, 830, 1040, 1.0 * back((t - TE) / 0.3), t)
        stamp(c, "ROTTEN EGGS?!", 400, 1130, t - TE, col=YELLOW, size=76, ang=-0.06)
    if t > TF: sticker(c, "FOLLOW SO YOU DON'T MISS IT", W / 2, 1290, 62, t - TF, bg=YELLOW, fg=INK, outline=PINK)
    if t > 0.5 and t < TF: tag(c, "Image: NASA/JPL-Caltech (Voyager 2) · Source: NASA JPL", t - 0.5, y=1330)


def s17(c, t, d):  # M loop: Still lighter than one sugar cube of her.
    hook_frame(c, t)
    sticker(c, "STILL LIGHTER THAN...", W / 2, 400, 90, t - 0.05, bg=PURPLE, outline=CYAN, ang=-0.04)
    TS = wt(17, "sugar", 0.9)
    if t > TS:
        sticker(c, "1 SUGAR CUBE", W / 2, 1230, 100, t - TS, bg=YELLOW, fg=INK, outline=PINK, ang=0.04)


def s_end(c, t, d):
    background(c, t)
    end_card_logo(c, t, W / 2, 700, 250, LOGO)
    sticker(c, "FOLLOW", W / 2, 1060, 110, t - 0.4, ang=-0.04)
    if t > 0.7: text(c, "Tomorrow: the planet that smells...", W / 2, 1200, 50, col=YELLOW, stroke=8, alpha=ease((t - 0.7) / 0.4))
    if t > 0.9: text(c, "@orbit.gossip · Planet Reviews", W / 2, 1290, 40, col=WHITE, stroke=8, alpha=ease((t - 0.9) / 0.4))


SCENES = {0: s0, 1: s1, 2: s2, 3: s3, 4: s4, 5: s5, 6: s6, 7: s7, 8: s8, 9: s9, 10: s10, 11: s11, 13: s13, 15: s15, 16: s16, 17: s17, NSC: s_end}
assert all(o in SCENES for o in ORDER), [o for o in ORDER if o not in SCENES]
NO_FLASH = ()


def frame(c, gt, surf):
    k = max(j for j in range(len(STARTS)) if STARTS[j] <= gt + 1e-9)
    t = gt - STARTS[k]; d = DURS[k]; i = ORDER[k]
    c.set_source_rgb(*SPACE); c.paint()
    c.save()
    if k > 0 and t < 0.25 and i not in NO_FLASH:
        z = 1 + 0.05 * (1 - eout(t / 0.25)); c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-W / 2, -H / 2)
    SCENES[i](c, t, d)
    c.restore()
    if k > 0 and i not in NO_FLASH: flash(c, t)
    badge_og(c, gt)
    if i in META:
        m = META[i]; captions(c, m["cap"], m["dur"], t, speaker=m.get("speaker"), words=m.get("words"))


def events():
    s = ST; ev = [("boom", 0.0), ("pop", 0.05), ("thunk", s[0] + wt(0, "billion", 1.8))]
    ev += [("pop", ST[o]) for o in ORDER[1:]]
    ev += [("tick", s[1] + k * 0.12) for k in range(10)] + [("trombone", s[1] + wt(1, "cheat", 2.6))]
    ev += [("ding", s[2] + 0.1), ("ding", s[2] + wt(2, "planet", 1.6)), ("whoosh", s[2] + wt(2, "neutron", 3.4)), ("boom", s[2] + wt(2, "real", 4.8))]
    ev += [("whoosh", s[3] + wt(3, "heavier", 0.9)), ("pop", s[3] + wt(3, "twelve", 2.9)), ("thunk", s[3] + wt(3, "city", 4.6))]
    ev += [("scratch", s[4] + 0.05), ("clank", s[4] + wt(4, "couch", 3.0)), ("trombone", s[4] + wt(4, "apartment", 4.0))]
    ev += [("ding", s[5] + 0.05), ("whoosh", s[5] + wt(5, "manhattan", 1.8))]
    ev += [("whoosh", s[6] + wt(6, "fastest", 0.9))] + [("tick", s[6] + wt(6, "forty", 1.8) + k * 0.1) for k in range(9)]
    ev += [("scratch", s[7] + wt(7, "fake", 0.5)), ("drill", s[7] + wt(7, "blender", 1.6))]
    ev += [("ding", s[8] + 0.05), ("bubble", s[8] + wt(8, "smoothie", 2.9))]
    ev += [("thunk", s[9] + wt(9, "magnetic", 1.0)), ("boom", s[9] + wt(9, "trillions", 2.2))]
    ev += [("ding", s[10] + wt(10, "real", 0.6)), ("whoosh", s[10] + wt(10, "credit", 1.8))]
    ev += [("thunk", s[11] + wt(11, "angry", 1.4)), ("boom", s[11] + wt(11, "thousand", 3.3))]
    ev += [("tick", s[13] + wt(13, "blinking", 2.2) + k * 0.45) for k in range(6)] + [("bubble", s[13] + wt(13, "little", 5.6))]
    ev += [("ding", s[15] + 0.05), ("ding", s[15] + wt(15, "drama", 2.2)), ("trombone", s[15] + wt(15, "sweetener", 3.6))]
    ev += [("ding", s[16] + 0.1), ("pop", s[16] + wt(16, "rotten", 3.4)), ("pop", s[16] + wt(16, "follow", 4.6))]
    ev += [("boom", s[17] + 0.05), ("pop", s[NSC] + 0.4)]
    return [e for e in ev if e[1] >= 0]


if __name__ == "__main__":
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H); c = cairo.Context(surf)
    if sys.argv[1] == "stills":
        for x in sys.argv[3:]:
            frame(c, float(x), surf); surf.write_to_png(f"{sys.argv[2]}_{x}.png")
    else:
        json.dump({"total": TOTAL, "events": events(), "music_style": "default"}, open("events.json", "w"))
        a, b = (int(v) for v in sys.argv[2:4]) if len(sys.argv) > 3 else (0, int(math.ceil(TOTAL * FPS)))
        out = sys.argv[4] if len(sys.argv) > 4 else "video.mp4"
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        for f in range(a, b):
            frame(c, f / FPS, surf); p.stdin.write(surf.get_data())
        p.stdin.close(); p.wait(); print("frames", a, b, "total", TOTAL)
