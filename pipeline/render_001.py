"""Orbit Gossip 001 — HD 189733b, the planet where it rains glass sideways (sample / quality-bar draft).
Format: celebrity-gossip show about a planet. F (Stella, af_bella) = gossip host, spills the facts; M (Max, am_puck) =
the big reactor who gets the punchlines. Look v1 "tabloid cosmos": nebula + parallax stars, procedural gas giant,
hot-pink tabloid stickers, EXCLUSIVE bursts, paparazzi-flash transitions, review/score cards.
Facts (NASA "Blue and bizarre", NASA Exoplanet Exploration "Rains of terror", Sci. American): deep blue from silicate
(glass) droplets, possibly rains glass sideways, winds up to 5,400 mph (8,700 km/h) ~7x speed of sound, >1,000 °C,
63 light-years away, orbit 2.2 days, day/night sides differ (thought tidally locked).
usage (work dir with meta.json): python render_001.py stills <prefix> t1 t2 ... | python render_001.py full [a b out.mp4]"""
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
    panel(c, 120, 520, 840, 560, t, col=hexc("F7F3FF"), a=0.97, edge=PINK)
    if t <= 0.15: return
    a = ease((t - 0.15) / 0.2)
    c.save(); c.translate(W / 2, 640)
    for j, rr in enumerate((90, 62, 34)):
        c.set_source_rgba(*PURPLE, a); c.set_line_width(14); c.arc(0, 40, rr, math.pi * 1.25, math.pi * 1.75); c.stroke()
    c.arc(0, 40, 10, 0, 2 * math.pi); c.fill(); c.restore()
    text(c, "Join network?", W / 2, 760, 54, col=INK, alpha=a)
    c.set_source_rgba(0.9, 0.88, 0.96, a); rrect(c, 180, 800, 720, 100, 18); c.fill()
    text(c, "HD 189733b", W / 2, 868, 64, col=PURPLE, alpha=a)
    c.set_source_rgba(0.9, 0.88, 0.96, a); rrect(c, 180, 930, 720, 100, 18); c.fill()
    pw = "•" * 10 if reveal <= 0 else "pl4net_GL4SS!"
    text(c, "Password: " + pw, W / 2, 998, 46, col=INK, alpha=a)


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


def hook_frame(c, t, k=1.0):
    background(c, t)
    star(c, W + 40, 260, 150, t)
    planet(c, W / 2 + 40, 860, 400, t, light=(-0.9, -0.5))
    glass_rain(c, t, n=80, alpha=0.95 * k, region=(0, 420, W, 900), seed=1)


# ---------------- scenes (one per line) ----------------
def s0(c, t, d):   # F hook: rains glass. Sideways.
    hook_frame(c, t)
    sticker(c, "IT RAINS GLASS.", W / 2, 400, 104, t + 0.4, ang=-0.05)
    TS = wt(0, "SIDEWAYS", 1.4)
    if t > TS:
        sticker(c, "SIDEWAYS", W / 2 - 80, 1180, 112, t - TS, bg=YELLOW, fg=INK, outline=PINK, ang=0.06)
        arrow(c, 760, 1180, 980, 1150, col=YELLOW, w=22, k=eout((t - TS) / 0.3))


def s1(c, t, d):   # M Sideways? Rain has one job. Down!
    background(c, t, dim=0.85)
    for x0, lab, side in ((60, "EARTH", False), (560, "HD 189733b", True)):
        panel(c, x0, 380, 460, 760, t + 0.3, col=hexc("1B1240"), a=0.85, edge=CYAN if side else WHITE)
        text(c, lab, x0 + 230, 470, 52, col=YELLOW if side else WHITE, stroke=6)
        cloud(c, x0 + 230, 600, 1.1, col=(0.75, 0.78, 0.88) if not side else (0.45, 0.75, 1.0))
        if side: rain_side(c, x0 + 20, 680, 420, 360, t)
        else: rain_down(c, x0 + 90, 680, 280, 380, t)
    TO = wt(1, "ONE", 0.9); TD = wt(1, "DOWN", 1.7)
    if t > TO: stamp(c, "ONE JOB", W / 2, 1230 - 70, t - TO, col=YELLOW, size=96, ang=-0.08)
    if t > TD: arrow(c, 290, 1000, 290, 1110, col=WHITE, w=14, k=eout((t - TD) / 0.25))


def s2(c, t, d):   # F Welcome to Orbit Gossip! Today's scandal: HD 189733b
    background(c, t)
    c.set_source_rgba(*PINK, 1); c.set_line_width(26); c.rectangle(60, 290, W - 120, 1000); c.stroke()
    text(c, "ORBIT GOSSIP", W / 2, 400, 120, col=WHITE, stroke=14)
    c.set_source_rgba(*YELLOW, 1); c.rectangle(110, 425, W - 220, 10); c.fill()
    planet(c, W / 2, 820, 300 + 10 * math.sin(t * 1.5), t, light=(-0.8, -0.6))
    burst(c, "EXCLUSIVE", 840, 560, 130, t - 0.25, size=38)
    TP = wt(2, "HD", 2.6)
    if t > TP: sticker(c, "HD 189733b", W / 2, 1180, 96, t - TP, bg=PURPLE, outline=CYAN)
    if t > wt(2, "scandal", 2.0): sticker(c, "TODAY'S SCANDAL", W / 2, 1060, 54, t - wt(2, "scandal", 2.0), bg=YELLOW, fg=INK, outline=PINK, ang=0.03)
    tag(c, "Image: NASA, ESA, M. Kornmesser (CC BY 4.0)", t - 0.3, y=1262)


def s3(c, t, d):   # M not a name, a wifi password
    background(c, t, dim=0.8)
    wifi_card(c, t + 0.1, t - wt(3, "WIFI", 1.2))
    if t > wt(3, "WIFI", 1.2): stamp(c, "WIFI PASSWORD?", W / 2, 1200, t - wt(3, "WIFI", 1.2), col=YELLOW, size=80, ang=-0.06)


def s4(c, t, d):   # F Rude! It's a celebrity.
    background(c, t)
    planet(c, W / 2, 820, 360, t, light=(-0.8, -0.6))
    sunglasses(c, W / 2, 820, 360, t - wt(4, "CELEBRITY", 0.5) + 0.1)
    camera_flashes(c, t)
    sticker(c, "RUDE!", W / 2, 400, 120, t, ang=-0.07)


def s5(c, t, d):   # F Gorgeous, blue like Earth, 63 light-years
    background(c, t)
    TL = wt(5, "sixty", 2.2)
    if t < TL:
        planet(c, 380, 820, 280, t, light=(-0.8, -0.6))
        mini_globe(c, 840, 820, 120, t)
        text(c, "THIS PLANET", 380, 1170, 46, col=WHITE, stroke=8); text(c, "EARTH", 840, 1010, 46, col=WHITE, stroke=8)
        if t > wt(5, "BLUE", 1.0): sticker(c, "TWINS?", W / 2, 420, 110, t - wt(5, "BLUE", 1.0), bg=hexc("2F7BE8"), outline=YELLOW)
    else:
        tt = t - TL
        mini_globe(c, 180, 1060, 60, t); planet(c, 900, 520, 110, t, light=(-0.8, -0.2), glints=0)
        c.set_source_rgba(1, 1, 1, 0.6); c.set_line_width(6); c.set_dash([18, 14]); c.move_to(230, 1020); c.line_to(lerp(230, 850, eout(tt / 0.8)), lerp(1020, 580, eout(tt / 0.8))); c.stroke(); c.set_dash([])
        sticker(c, counter(tt, 0, 63, 0.9) + " LIGHT-YEARS", W / 2, 800, 96, tt, bg=PURPLE, outline=CYAN)
        tag(c, "Source: NASA (63 light-years)", tt - 0.3)


def s6(c, t, d):   # M Blue? oceans, beaches, umbrellas
    background(c, t, dim=0.85)
    planet(c, W / 2, 1000, 330, t, light=(-0.8, -0.6))
    beach_bubble(c, W / 2, 560, t)
    sticker(c, "HIS THEORY", W / 2, 300, 60, t - 0.2, bg=YELLOW, fg=INK, outline=PINK, ang=0.04)


def s7(c, t, d):   # F Nope. The blue is glass. Droplets.
    background(c, t, dim=0.9)
    TN = wt(7, "blue", 0.6)
    if t < TN:
        planet(c, W / 2, 1000, 330, t, light=(-0.8, -0.6)); beach_bubble(c, W / 2, 560, 1.0, pop=t + 0.01)
        stamp(c, "NOPE.", W / 2, 520, t, col=PINK, size=150)
    else:
        tt = t - TN; z = 330 * (1 + 4 * eout(tt / 0.6))
        planet(c, W / 2, 1000 + 400 * eout(tt / 0.6), z, t, light=(-0.8, -0.6))
        c.set_source_rgba(*hexc("8FD3FF"), 0.35 * eout(tt / 0.5)); c.paint()
        droplets(c, t, W / 2, 760, k=tt / 0.8)
        if t > wt(7, "MELTED", 2.0): sticker(c, "MELTED GLASS", W / 2, 400, 104, t - wt(7, "MELTED", 2.0), bg=hexc("1C8FD8"), outline=WHITE)
        if t > wt(7, "MELTED", 2.0) + 0.4: tag(c, "Source: NASA/Hubble (silicate droplets)", t - wt(7, "MELTED", 2.0) - 0.4)


def s8(c, t, d):   # M the sky is basically... a chandelier
    background(c, t)
    planet(c, W / 2, 1120, 380, t, light=(-0.8, -0.6))
    TC = wt(8, "CHANDELIER", 1.4)
    if t > TC - 0.4:
        k = eout((t - TC + 0.4) / 0.5); chandelier(c, W / 2, lerp(-300, 620, k), 1.1, t, swing=0.08 * math.sin(t * 3))
    if t > TC: stamp(c, "ACCURATE", W / 2, 360, t - TC, col=YELLOW, size=96, ang=0.08)


def s9(c, t, d):   # F chandelier in a hurricane, 8,700 km/h, 7x speed of sound
    background(c, t, drift=4)
    planet(c, W / 2, 1150, 420, t, light=(-0.8, -0.6), spin=0.12)
    glass_rain(c, t, n=120, speed=1.8, alpha=1.0, region=(0, 200, W, 1300), seed=9, length=170)
    TW = wt(9, "seven", 1.8); TS = wt(9, "nearly", 3.6)
    sticker(c, "HURRICANE!", W / 2, 330, 104, t - wt(9, "HURRICANE", 0.6), bg=hexc("E0303A"), outline=YELLOW)
    if t > TW - 0.2: gauge(c, W / 2, 900, 330, lerp(0, 7000, eout((t - TW + 0.2) / 1.3)), 9000, t - TW + 0.2)
    if t > TS: sticker(c, "~6× SPEED OF SOUND", W / 2, 1060, 72, t - TS, bg=YELLOW, fg=INK, outline=PINK, ang=0.03)
    if t > TW: tag(c, "Source: NASA Goddard (7,000 km/h winds)", t - TW)


def s10(c, t, d):  # M sandblasted. By a window.
    background(c, t, drift=4)
    planet(c, W / 2, 1200, 420, t, light=(-0.8, -0.6), spin=0.12)
    glass_rain(c, t, n=90, speed=1.8, region=(0, 200, W, 1300), seed=10, length=170)
    TS = wt(10, "SANDBLASTED", 1.4); TW_ = wt(10, "WINDOW", 2.4)
    if t > TS: stamp(c, "SANDBLASTED", W / 2, 420, t - TS, col=YELLOW, size=100, ang=-0.08)
    window_fly(c, t - TW_ + 0.3)


def s11(c, t, d):  # F over 1,000 degrees
    background(c, t)
    TD = wt(11, "thousand", 0.9); h = eout((t - TD + 0.2) / 0.8) if t > TD - 0.2 else 0
    planet(c, 420, 880, 330, t, light=(-0.8, -0.6), heat=0.85 * h)
    thermo(c, 880, 1080, 620, 1000 * h, t + 0.2)
    if t > TD: sticker(c, counter(t - TD, 0, 1000, 0.7) + "°C+", W / 2, 360, 120, t - TD, bg=hexc("FF5A1F"), outline=YELLOW)
    if t > TD + 0.3: tag(c, "Source: NASA (over 1,000 °C)", t - TD - 0.3)


def s12(c, t, d):  # M one star, would not visit
    background(c, t, dim=0.8)
    review_card(c, t + 0.1, t - wt(12, "ONE", 1.4) + 0.2)


def s13(c, t, d):  # F one year = 2.2 days
    background(c, t)
    orbit_scene(c, t)
    TD = wt(13, "two", 1.4)
    sticker(c, "1 YEAR =", W / 2, 360, 90, t - wt(13, "YEAR", 0.5), bg=PURPLE, outline=CYAN)
    if t > TD: sticker(c, "2.2 DAYS", W / 2, 1110, 130, t - TD, bg=YELLOW, fg=INK, outline=PINK, ang=0.04)
    if t > TD + 0.3: tag(c, "Source: Scientific American / NASA", t - TD - 0.3)


def s14(c, t, d):  # M birthday every weekend
    background(c, t)
    confetti(c, t)
    cake(c, W / 2, 900, 1.25, t)
    TB = wt(14, "BIRTHDAY", 0.9)
    sticker(c, "2 DAYS?!", W / 2, 360, 120, t, bg=PINK, ang=-0.06)
    if t > TB: sticker(c, "BIRTHDAY EVERY WEEKEND", W / 2, 1160, 64, t - TB, bg=YELLOW, fg=INK, outline=PINK, ang=0.03)


def daynight(c, t, k):
    planet(c, W / 2, 860, 400, t, light=(-1.0, 0.0), terminator=k, spin=0.0, glints=0)
    star(c, W + 80, 860, 150, t)


def s15(c, t, d):  # F one side always faces its star
    background(c, t)
    daynight(c, t, eout(t / 1.2))
    if t > wt(15, "DAY", 4.0): sticker(c, "ALWAYS DAY", 780, 400, 64, t - wt(15, "DAY", 4.0), bg=YELLOW, fg=INK, outline=PINK, ang=-0.04, maxw=520)
    if t > wt(15, "NIGHT", 5.0): sticker(c, "ALWAYS NIGHT", 300, 1200, 64, t - wt(15, "NIGHT", 5.0), bg=PURPLE, outline=CYAN, ang=0.04, maxw=520)
    if t > 0.8: tag(c, "Day/night: NASA Spitzer heat map", t - 0.8)


def s16(c, t, d):  # M never sleeps / never breakfast
    background(c, t)
    daynight(c, t, 1.0)
    sticker(c, "ALWAYS DAY", 780, 400, 64, 1, bg=YELLOW, fg=INK, outline=PINK, ang=-0.04, maxw=520)
    sticker(c, "ALWAYS NIGHT", 300, 1200, 64, 1, bg=PURPLE, outline=CYAN, ang=0.04, maxw=520)
    if t > wt(16, "SLEEPS", 1.2): stamp(c, "NO SLEEP", 760, 700, t - wt(16, "SLEEPS", 1.2), col=PINK, size=78, ang=-0.12)
    if t > wt(16, "BREAKFAST", 3.0): stamp(c, "NO BREAKFAST", 330, 960, t - wt(16, "BREAKFAST", 3.0), col=YELLOW, size=70, ang=0.1)


def s17(c, t, d):  # F Final ratings! Looks 10/10
    background(c, t); planet(c, W / 2, 1180, 260, t, light=(-0.8, -0.6))
    scorecard(c, t + 0.1, 0)


def s18(c, t, d):  # M Personality: hurricane full of windows
    background(c, t); planet(c, W / 2, 1180, 260, t, light=(-0.8, -0.6))
    scorecard(c, 2.0, t + 0.05)


STORM = None


def s19(c, t, d):  # M loop: next time it rains on you, say thank you. falling DOWN.
    TL = wt(19, "falling", 2.6) - 0.15
    if t < TL:
        global STORM
        if STORM is None:
            n = fbm(H, W, octaves=6, seed=31, base=3)
            STORM = to_surface(ramp(n, [(0, hexc("2B3550")), (0.5, hexc("4E5C7C")), (1, hexc("8A97B4"))]))
        c.set_source_surface(STORM, 0, 0); c.paint()
        cloud(c, W / 2, 420, 2.0, col=(0.72, 0.75, 0.82))
        rain_down(c, 120, 560, 840, 720, t, n=60, seed=8)
        c.set_source_rgba(*PINK, 1); c.move_to(W / 2 - 230, 1060); c.curve_to(W / 2 - 150, 860, W / 2 + 150, 860, W / 2 + 230, 1060); c.close_path(); c.fill()
        c.set_source_rgba(0.2, 0.15, 0.1, 1); c.set_line_width(12); c.move_to(W / 2, 1000); c.line_to(W / 2, 1200); c.stroke()
        c.arc(W / 2 + 30, 1200, 30, 0, math.pi); c.stroke()
        if t > wt(19, "THANK", 1.6): sticker(c, "THANK YOU, RAIN", W / 2, 1180 - 600 + 60, 80, t - wt(19, "THANK", 1.6), bg=YELLOW, fg=INK, outline=PINK, ang=-0.04)
    else:
        tt = t - TL; hook_frame(c, t, k=ease(tt / 0.4))
        sticker(c, "AT LEAST IT FALLS DOWN", W / 2, 400, 70, tt, ang=-0.04)


def s_end(c, t, d):
    background(c, t)
    end_card_logo(c, t, W / 2, 760, 270, LOGO)
    sticker(c, "FOLLOW", W / 2, 1150, 110, t - 0.5, ang=-0.04)
    if t > 0.9: text(c, "@orbitgossip · space, but make it gossip", W / 2, 1300, 40, col=WHITE, stroke=8, alpha=ease((t - 0.9) / 0.4))


SCENES = [s0, s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, s13, s14, s15, s16, s17, s18, s19, s_end]
assert len(SCENES) == NSC + 1, len(SCENES)
NO_FLASH = (10, 16, 18)   # continuous scenes


def frame(c, gt, surf):
    k = max(j for j in range(len(STARTS)) if STARTS[j] <= gt + 1e-9)
    t = gt - STARTS[k]; d = DURS[k]; i = ORDER[k]
    c.set_source_rgb(*SPACE); c.paint()
    c.save()
    if i > 0 and t < 0.25 and i not in NO_FLASH:
        z = 1 + 0.05 * (1 - eout(t / 0.25)); c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-W / 2, -H / 2)
    SCENES[i](c, t, d)
    c.restore()
    if i > 0 and i not in NO_FLASH: flash(c, t)
    badge_og(c, gt)
    if i in META:
        m = META[i]; captions(c, m["cap"], m["dur"], t, speaker=m.get("speaker"), words=m.get("words"))


def events():
    s = ST; ev = [("boom", 0.0), ("crack", 0.05), ("pop", s[0] + wt(0, "SIDEWAYS", 1.4))]
    ev += [("pop", ST[o]) for o in ORDER[1:] if o not in NO_FLASH]
    ev += [("ding", s[1] + wt(1, "ONE", 0.9)), ("thunk", s[1] + wt(1, "DOWN", 1.7))]
    ev += [("ding", s[2] + 0.3), ("pop", s[2] + wt(2, "HD", 2.6))]
    ev += [("ding", s[3] + 0.2), ("scratch", s[3] + wt(3, "WIFI", 1.2))]
    ev += [("tick", s[4] + k * 0.13) for k in range(10)]
    ev += [("tick", s[5] + wt(5, "sixty", 2.2) + k * 0.08) for k in range(8)] + [("ding", s[5] + wt(5, "sixty", 2.2) + 0.9)]
    ev += [("bubble", s[6] + 0.1), ("pop", s[7] + 0.02), ("crack", s[7] + wt(7, "blue", 0.6)), ("bubble", s[7] + wt(7, "MELTED", 2.0))]
    ev += [("clank", s[8] + wt(8, "CHANDELIER", 1.4) - 0.1), ("ding", s[8] + wt(8, "CHANDELIER", 1.4) + 0.1)]
    ev += [("whoosh", s[9] + 0.2), ("whoosh", s[9] + 2.8), ("ding", s[9] + wt(9, "nearly", 3.6))]
    ev += [("crack", s[10] + wt(10, "SANDBLASTED", 1.4)), ("whoosh", s[10] + wt(10, "WINDOW", 2.4) - 0.3), ("crack", s[10] + wt(10, "WINDOW", 2.4) + 0.2)]
    ev += [("tick", s[11] + wt(11, "thousand", 0.9) + k * 0.08) for k in range(8)] + [("ding", s[11] + wt(11, "thousand", 0.9) + 0.75)]
    ev += [("pop", s[12] + wt(12, "ONE", 1.4)), ("trombone", s[12] + wt(12, "Would", 2.2))]
    ev += [("whoosh", s[13] + 0.4), ("ding", s[13] + wt(13, "two", 1.4))]
    ev += [("bubble", s[14] + 0.1), ("pop", s[14] + wt(14, "BIRTHDAY", 0.9))]
    ev += [("thunk", s[16] + wt(16, "SLEEPS", 1.2)), ("thunk", s[16] + wt(16, "BREAKFAST", 3.0))]
    ev += [("ding", s[17] + 0.5), ("thunk", s[18] + wt(18, "hurricane", 1.0)), ("scratch", s[18] + wt(18, "windows", 2.0))]
    ev += [("ding", s[19] + wt(19, "THANK", 1.6)), ("boom", s[19] + wt(19, "falling", 2.6) - 0.15), ("pop", s[NSC] + 0.5)]
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
