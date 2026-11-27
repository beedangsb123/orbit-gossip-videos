"""Orbit Gossip 002 — Planet Reviews: Venus's dating profile (day longer than year, spins backwards, 900 °F, 90x pressure).
Copied from render_001.py (helpers lines kept as-is) + Venus scenes below. Real images: Mariner 10 (PIA23791) and
Magellan radar global view (PIA00104), Magellan 3D Maat Mons (PIA00254) — NASA/JPL(-Caltech), public domain.
Facts (NASA Science "Venus: Facts"): day = 243 Earth days, year = 225 Earth days, retrograde spin (Sun rises in the west),
surface ~900 °F (475 °C, hot enough to melt lead), pressure >90x Earth, sulfuric-acid clouds, Earth-size "twin".
Neutron-star teaser: NASA Goddard (sugar cube of neutron star ~ weight of a mountain).
usage (work dir with meta.json): python render_002.py stills <prefix> t1 t2 ... | python render_002.py full [a b out.mp4]"""
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




# ================= 002: Venus =================
GREEN = hexc("2FBF71"); RED = hexc("E0303A"); ACID = hexc("C8E83A")
_IMG = {}
VR = {"clouds": 671.3, "radar": 695.0}


def _img(name):
    if name not in _IMG: _IMG[name] = cairo.ImageSurface.create_from_png(name)
    return _IMG[name]


def venus(c, cx, cy, r, t, kind="clouds", heat=0.0, spin=0.015, glow=1.0):
    """REAL images: Mariner 10 cloud tops (PIA23791) or Magellan radar surface (PIA00104), NASA/JPL, public domain."""
    r = max(8, r)
    if glow > 0:
        g = cairo.RadialGradient(cx, cy, r * 0.95, cx, cy, r * 1.3)
        col = hexc("FFD9A0") if kind == "clouds" else hexc("FF9A3D")
        g.add_color_stop_rgba(0, *col, 0.35 * glow); g.add_color_stop_rgba(1, *col, 0)
        c.set_source(g); c.arc(cx, cy, r * 1.32, 0, 2 * math.pi); c.fill()
    S = _img("venus_%s.png" % kind); k = r / VR[kind]
    c.save(); c.arc(cx, cy, r, 0, 2 * math.pi); c.clip()
    c.save(); c.translate(cx, cy); c.rotate(spin * t); c.scale(k, k); c.translate(-700, -700)
    c.set_source_surface(S, 0, 0); c.get_source().set_filter(cairo.FILTER_GOOD); c.paint(); c.restore()
    if heat > 0: c.set_source_rgba(1.0, 0.35, 0.05, 0.5 * heat); c.paint()
    c.restore()


def heart(c, x, y, r, col, a=1.0):
    c.save(); c.translate(x, y); c.set_source_rgba(*col, a)
    c.move_to(0, r * 0.9); c.curve_to(-r * 1.6, -r * 0.2, -r * 0.7, -r * 1.3, 0, -r * 0.45)
    c.curve_to(r * 0.7, -r * 1.3, r * 1.6, -r * 0.2, 0, r * 0.9); c.close_path(); c.fill(); c.restore()


def red_flag(c, x, y, s, t):
    if t <= 0: return
    k = back(t / 0.3); wave = math.sin(t * 9) * 0.12
    c.save(); c.translate(x, y); c.scale(s * k, s * k)
    c.set_source_rgb(0.85, 0.85, 0.9); c.set_line_width(14); c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.move_to(0, 120); c.line_to(0, -130); c.stroke()
    c.set_source_rgb(*RED); c.move_to(6, -130)
    c.curve_to(60, -150 + 30 * wave, 110, -110 - 30 * wave, 170, -125 + 20 * wave)
    c.line_to(170, -35 + 20 * wave); c.curve_to(110, -20 - 30 * wave, 60, -60 + 30 * wave, 6, -40); c.close_path(); c.fill()
    c.restore()


def profile_card(c, t, x=W / 2, y=800, sc=1.0, swipe=0.0, kind="clouds", stamp_t=-1):
    """dating-app profile card with the real Venus photo; swipe>0 flies it off to the left"""
    if t <= 0: return
    k = eout(t / 0.3); w, h = 760, 900
    dx = -1400 * eout(swipe) if swipe > 0 else 0; rot = -0.35 * eout(swipe) if swipe > 0 else 0
    c.save(); c.translate(x + dx, y + (1 - k) * 300); c.rotate(rot); c.scale(sc * lerp(0.8, 1, k), sc * lerp(0.8, 1, k))
    c.set_source_rgba(0, 0, 0, 0.45); rrect(c, -w / 2 + 14, -h / 2 + 18, w, h, 40); c.fill()
    c.set_source_rgb(1, 1, 1); rrect(c, -w / 2, -h / 2, w, h, 40); c.fill()
    c.save(); rrect(c, -w / 2 + 20, -h / 2 + 20, w - 40, 620, 30); c.clip()
    c.set_source_rgb(*hexc("0E0820")); c.paint()
    venus(c, 0, -h / 2 + 330, 270, t, kind=kind, glow=0.6)
    g = cairo.LinearGradient(0, -h / 2 + 460, 0, -h / 2 + 640); g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.75)
    c.set_source(g); c.paint()
    text(c, "Venus", -w / 2 + 50, -h / 2 + 600, 64, col=WHITE, align="left")
    c.restore()
    text(c, "2nd planet from the Sun", -w / 2 + 50, -h / 2 + 720, 36, col=(0.35, 0.3, 0.45), align="left")
    text(c, "“Brightest planet in your sky”", -w / 2 + 50, -h / 2 + 780, 34, col=PURPLE, align="left")
    for j, (col, sym) in enumerate(((RED, "✕"), (PINK, "♥"))):
        bx = -110 + j * 220; by = h / 2 - 30
        c.set_source_rgb(1, 1, 1); c.arc(bx, by, 62, 0, 2 * math.pi); c.fill()
        c.set_source_rgb(*col); c.set_line_width(6); c.arc(bx, by, 62, 0, 2 * math.pi); c.stroke()
        if j == 0:
            c.set_source_rgb(*col); c.set_line_width(12); c.set_line_cap(cairo.LINE_CAP_ROUND)
            c.move_to(bx - 22, by - 22); c.line_to(bx + 22, by + 22); c.move_to(bx + 22, by - 22); c.line_to(bx - 22, by + 22); c.stroke()
        else: heart(c, bx, by, 26, col)
    if stamp_t > 0: stamp(c, "NOPE", 0, -h / 2 + 260, stamp_t, col=RED, size=150, ang=0.25)
    c.restore()


def series_banner(c, t, y=300):
    if t <= 0: return
    sticker(c, "PLANET REVIEWS", W / 2, y, 64, t, bg=YELLOW, fg=INK, outline=PINK, ang=-0.03)


def popcorn(c, x, y, s, t):
    if t <= 0: return
    k = back(t / 0.35)
    c.save(); c.translate(x, y); c.scale(s * k, s * k)
    for j in range(9):
        px = -90 + (j % 5) * 45 + (10 if j >= 5 else 0); py = -120 - (30 if j >= 5 else 0) + 8 * math.sin(t * 6 + j)
        c.set_source_rgb(1, 0.97, 0.85); c.arc(px, py, 38, 0, 2 * math.pi); c.fill()
        c.set_source_rgb(1, 0.85, 0.45); c.arc(px + 8, py + 8, 14, 0, 2 * math.pi); c.fill()
    c.move_to(-130, -110); c.line_to(130, -110); c.line_to(100, 160); c.line_to(-100, 160); c.close_path()
    c.set_source_rgb(1, 1, 1); c.fill_preserve(); c.save(); c.clip()
    c.set_source_rgb(*RED)
    for j in range(-3, 3): c.rectangle(j * 52 + 12, -120, 26, 290); c.fill()
    c.restore(); c.restore()


def chat(c, t, d):
    """Monday text -> typing... -> reply in AUGUST"""
    panel(c, 120, 330, 840, 960, t + 0.3, col=hexc("F4F1FA"), a=0.98, edge=PINK)
    if t <= 0: return
    text(c, "Venus", W / 2 - 20, 420, 48, col=INK); heart(c, W / 2 + 95, 405, 18, PINK)
    TM = wt(5, "monday", 1.2); TA = wt(5, "august", 2.6)
    if t > TM - 0.4:
        text(c, "MON 9:00 AM", W / 2, 520, 30, col=(0.5, 0.5, 0.6))
        k = back((t - TM + 0.4) / 0.3)
        c.save(); c.translate(760, 610); c.scale(k, k)
        c.set_source_rgb(*hexc("2F7BE8")); rrect(c, -210, -50, 380, 100, 50); c.fill()
        text(c, "good morning! :)", -20, 14, 38, col=WHITE); c.restore()
    if TM < t < TA:
        for j in range(3):
            a = 0.4 + 0.6 * abs(math.sin(t * 5 - j * 0.6))
            c.set_source_rgba(0.55, 0.55, 0.65, a); c.arc(250 + j * 50, 760, 16, 0, 2 * math.pi); c.fill()
        text(c, "Venus is typing...", 360, 840, 30, col=(0.5, 0.5, 0.6), align="left")
        # calendar pages flying
        mon = ["FEB", "MAR", "APR", "MAY", "JUN", "JUL"]; q = (t - TM) / max(0.3, TA - TM)
        sticker(c, mon[min(5, int(q * 6))], 780, 1000, 80, 1, bg=WHITE, fg=RED, outline=INK, ang=0.05 * math.sin(t * 9), maxw=300)
    if t > TA:
        text(c, "AUG 9:00 AM", W / 2, 750, 30, col=(0.5, 0.5, 0.6))
        k = back((t - TA) / 0.3)
        c.save(); c.translate(330, 840); c.scale(k, k)
        c.set_source_rgb(*hexc("E4E0EE")); rrect(c, -170, -50, 340, 100, 50); c.fill()
        text(c, "morning!", -20, 14, 40, col=INK); heart(c, 120, 0, 16, PINK); c.restore()
        stamp(c, "8 MONTHS LATER", W / 2, 1080, t - TA, col=PINK, size=80, ang=-0.06)


def bars(c, t, ty):
    """DAY 243 vs YEAR 225 bars"""
    panel(c, 90, 430, 900, 560, t + 0.3, col=INK, a=0.88, edge=CYAN)
    if t <= 0: return
    text(c, "ONE DAY", 140, 560, 50, col=WHITE, align="left"); text(c, "ONE YEAR", 140, 780, 50, col=WHITE, align="left")
    k1 = eout(t / 0.8); c.set_source_rgb(*PINK); rrect(c, 140, 590, 780 * k1, 80, 20); c.fill()
    text(c, counter(t, 0, 243, 0.8) + " days", 160 + 780 * k1 - 30, 648, 44, col=WHITE, align="right")
    if t > ty:
        k2 = eout((t - ty) / 0.8); c.set_source_rgb(*CYAN); rrect(c, 140, 810, 780 * 225 / 243 * k2, 80, 20); c.fill()
        text(c, counter(t - ty, 0, 225, 0.8) + " days", 160 + 780 * 225 / 243 * k2 - 30, 868, 44, col=INK, align="right")
    text(c, "(Earth days)", W / 2, 960, 34, col=(0.8, 0.8, 0.9))


def spin_arrow(c, cx, cy, r, t, direction=-1, col=YELLOW):
    a0 = t * 1.5 * direction
    c.set_source_rgba(*col, 1); c.set_line_width(18); c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.save(); c.translate(cx, cy); c.scale(1, 0.32)
    c.arc(0, 0, r, math.pi * 0.15, math.pi * 0.85); c.restore(); c.stroke()
    # head at left end pointing left (backwards)
    hx, hy = cx + direction * r * math.cos(math.pi * 0.15) * (-1 if direction < 0 else 1), cy + r * 0.32 * math.sin(math.pi * 0.15)
    hx = cx - r * math.cos(math.pi * 0.15) if direction < 0 else cx + r * math.cos(math.pi * 0.15)
    c.move_to(hx - 40 * (1 if direction < 0 else -1), hy - 5); c.line_to(hx + 30 * (1 if direction < 0 else -1), hy - 40); c.line_to(hx + 30 * (1 if direction < 0 else -1), hy + 30); c.close_path(); c.fill()


def sunrise_west(c, t, k):
    """horizon with W on the left, E on the right; the Sun rises on the WEST side"""
    c.save()
    g = cairo.LinearGradient(0, 700, 0, 1250); g.add_color_stop_rgb(0, *hexc("3B1C7A")); g.add_color_stop_rgb(1, *hexc("FF8A3D"))
    rrect(c, 90, 700, 900, 560, 30); c.set_source(g); c.fill()
    sy = lerp(1230, 900, eout(k)); 
    c.save(); rrect(c, 90, 700, 900, 560, 30); c.clip()
    star(c, 270, sy, 90, t)
    c.set_source_rgb(*hexc("5A2A12")); c.rectangle(90, 1120, 900, 140); c.fill()
    c.restore()
    c.set_source_rgba(*PINK, 1); c.set_line_width(6); rrect(c, 90, 700, 900, 560, 30); c.stroke()
    text(c, "W", 170, 1215, 70, col=YELLOW, stroke=8); text(c, "E", 910, 1215, 70, col=WHITE, stroke=8)
    c.restore()


def lead_bar(c, x, y, t, melt):
    """grey lead ingot that slumps and drips as it melts"""
    m = ease(melt); c.save(); c.translate(x, y)
    c.set_source_rgb(*hexc("8D93A3"))
    c.move_to(-170, 0); c.line_to(-130 - 40 * m, -110 + 90 * m); c.curve_to(-40, -120 + 100 * m, 40, -120 + 100 * m, 130 + 40 * m, -110 + 90 * m)
    c.line_to(170 + 60 * m, 0); c.close_path(); c.fill()
    text(c, "Pb", 0, -40 + 50 * m, 64 * (1 - 0.4 * m), col=hexc("D8DCE6"))
    if m > 0.2:
        for j in range(4):
            dy = ((t * 120 + j * 37) % 120)
            c.set_source_rgb(*hexc("A6ACBA")); c.arc(-120 + j * 80, 10 + dy, 12, 0, 2 * math.pi); c.fill()
    c.restore()


def oven(c, cx, cy, t, k):
    if k <= 0: return
    s = back(k / 0.35)
    c.save(); c.translate(cx, cy); c.scale(s, s)
    c.set_source_rgb(*hexc("D8D8DE")); rrect(c, -330, -300, 660, 600, 30); c.fill()
    c.set_source_rgb(*hexc("2A2A33")); rrect(c, -330, -300, 660, 110, 30); c.fill()
    for j in range(4):
        c.set_source_rgb(0.85, 0.85, 0.9); c.arc(-210 + j * 140, -245, 28, 0, 2 * math.pi); c.fill()
    c.set_source_rgb(*hexc("1A1012")); rrect(c, -270, -150, 540, 380, 24); c.fill()
    c.save(); rrect(c, -270, -150, 540, 380, 24); c.clip()
    c.set_source_rgba(1, 0.4, 0.05, 0.5 + 0.2 * math.sin(t * 8)); c.paint()
    venus(c, 0, 40, 150, t, kind="radar", heat=0.6, glow=0)
    c.restore()
    c.set_source_rgb(*hexc("B0B0B8")); c.set_line_width(18); c.move_to(-200, -175); c.line_to(200, -175); c.stroke()
    c.restore()


def acid_clouds(c, t, k):
    r = np.random.default_rng(13)
    for j in range(9):
        x = (r.random() * (W + 600) + t * (40 + 40 * r.random())) % (W + 600) - 300; y = 380 + r.random() * 500
        cloud(c, x, y, 0.9 + 0.6 * r.random(), col=ACID, a=0.55 * k)


def press_arrows(c, t, k):
    for j in range(5):
        x = 160 + j * 190; y = 440 + 40 * math.sin(t * 6 + j) * k
        arrow(c, x, y - 140, x, y + 60, col=WHITE, w=22, k=k)


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


def balance(c, t, k):
    """seesaw: sugar cube on the left balances a whole mountain on the right"""
    cx, cy = W / 2, 1120
    c.set_source_rgb(*hexc("C9C2DA")); c.move_to(cx, cy); c.line_to(cx - 60, cy + 120); c.line_to(cx + 60, cy + 120); c.close_path(); c.fill()
    ang = 0.25 * (1 - eout(k))
    c.save(); c.translate(cx, cy); c.rotate(ang)
    c.set_source_rgb(*hexc("EDE7FF")); rrect(c, -420, -18, 840, 36, 18); c.fill()
    c.set_source_rgb(1, 1, 1); rrect(c, -360, -110, 92, 92, 10); c.fill()
    c.set_source_rgb(0.85, 0.85, 0.9); c.set_line_width(4); rrect(c, -360, -110, 92, 92, 10); c.stroke()
    c.set_source_rgba(*CYAN, 0.5 + 0.5 * math.sin(t * 6)); c.arc(-314, -64, 70, 0, 2 * math.pi); c.set_line_width(5); c.stroke()
    if k > 0:
        c.set_source_rgb(*hexc("6F6A86")); c.move_to(140, -18); c.line_to(300, -330 * eout(k)); c.line_to(420, -18); c.close_path(); c.fill()
        c.set_source_rgb(1, 1, 1); c.move_to(300 - 45, -330 * eout(k) + 80 * eout(k)); c.line_to(300, -330 * eout(k)); c.line_to(300 + 40, -330 * eout(k) + 70 * eout(k)); c.close_path(); c.fill()
    c.restore()


def hook_frame(c, t, k=1.0):
    background(c, t)
    venus(c, W / 2, 860, 430, t)


# ---------------- scenes (one per ORIGINAL line index) ----------------
def s0(c, t, d):   # F Venus has a day that's longer than her whole year.
    hook_frame(c, t)
    sticker(c, "VENUS", W / 2, 380, 110, t + 0.4, ang=-0.05)
    TL = wt(0, "longer", 1.0)
    if t > TL: sticker(c, "HER DAY > HER YEAR", W / 2, 1230, 84, t - TL, bg=YELLOW, fg=INK, outline=PINK, ang=0.04)
    tag(c, "Image: NASA/JPL-Caltech (Mariner 10)", t - 0.6, y=1320)


def s1(c, t, d):   # M not a schedule. cry for help
    background(c, t, dim=0.85)
    panel(c, 190, 420, 700, 640, t + 0.3, col=WHITE, a=0.97, edge=INK)
    c.set_source_rgb(*RED); rrect(c, 190, 420, 700, 130, 26); c.fill()
    text(c, "MY SCHEDULE", W / 2, 505, 56, col=WHITE)
    for r_ in range(4):
        for q in range(5):
            c.set_source_rgb(0.88, 0.88, 0.92); rrect(c, 230 + q * 128, 590 + r_ * 112, 110, 96, 10); c.fill()
    text(c, "DAY 1", 230 + 55, 650, 30, col=INK)
    c.set_source_rgba(*PINK, 0.85); rrect(c, 230, 700, 620, 330, 14); c.fill()
    text(c, "...STILL DAY 1", W / 2, 880, 60, col=WHITE)
    TC = wt(1, "cry", 1.5)
    if t > TC: stamp(c, "CRY FOR HELP", W / 2, 1200, t - TC, col=YELLOW, size=84, ang=-0.07)


def s2(c, t, d):   # F Grab your popcorn! It's Planet Reviews... swiping through Venus's dating profile
    background(c, t)
    TP = wt(2, "popcorn", 0.5); TR = wt(2, "planet", 1.4); TS = wt(2, "swiping", 3.0)
    if t < TS:
        c.set_source_rgba(*PINK, 1); c.set_line_width(26); c.rectangle(60, 290, W - 120, 1000); c.stroke()
        text(c, "ORBIT GOSSIP", W / 2, 400, 120, col=WHITE, stroke=14)
        popcorn(c, W / 2, 830, 1.5, t - TP + 0.1)
        if t > TR: series_banner(c, t - TR, y=1150)
    else:
        tt = t - TS
        series_banner(c, 1, y=300)
        profile_card(c, tt + 0.1, y=830, sc=0.95)
        burst(c, "NEW\nMATCH?", 880, 470, 120, tt - 0.4, size=34)


def s3(c, t, d):   # M Ooh. Earth's twin? same size, next door?
    background(c, t)
    venus(c, 330, 820, 230, t); mini_globe(c, 760, 820, 230, t)
    text(c, "VENUS", 330, 1110, 50, col=WHITE, stroke=8); text(c, "EARTH", 760, 1110, 50, col=WHITE, stroke=8)
    TT = wt(3, "twin", 0.8); TN = wt(3, "next", 2.6)
    if t > TT: sticker(c, "EARTH'S TWIN?", W / 2, 420, 100, t - TT, bg=hexc("2F7BE8"), outline=YELLOW)
    if t > TN: sticker(c, "NEIGHBORS!", W / 2, 1220, 80, t - TN, bg=YELLOW, fg=INK, outline=PINK, ang=0.04)


def s4(c, t, d):   # F Same size yes. RED FLAG #1. spins slowly, 243 Earth days
    background(c, t)
    TF = wt(4, "red", 1.2); TD = wt(4, "two", 4.6)
    if t < TF:
        venus(c, 330, 820, 230, t); mini_globe(c, 760, 820, 230, t)
        stamp(c, "SAME SIZE!", W / 2, 420, t + 0.05, col=GREEN, size=96, ang=-0.05)
    else:
        tt = t - TF
        venus(c, W / 2, 900, 330, t, spin=0.004)
        red_flag(c, 180, 560, 1.3, tt)
        sticker(c, "RED FLAG #1", 620, 420, 92, tt, bg=RED, outline=YELLOW, ang=-0.04, maxw=760)
        if t > wt(4, "slowly", 2.8): sticker(c, "SLOOOW SPIN", W / 2, 640, 64, t - wt(4, "slowly", 2.8), bg=PURPLE, outline=CYAN, ang=0.03)
        if t > TD:
            sticker(c, counter(t - TD, 0, 243, 0.9) + " EARTH DAYS", W / 2, 1230, 96, t - TD, bg=YELLOW, fg=INK, outline=PINK, ang=0.03)
            tag(c, "Source: NASA Science, Venus facts", t - TD - 0.3, y=1320)


def s5(c, t, d):   # M 243 days? text Monday, reply in August
    background(c, t, dim=0.8)
    chat(c, t, d)


def s6(c, t, d):   # F year only 225 days. birthday before bedtime
    background(c, t)
    TB = wt(6, "birthday", 2.6)
    if t < TB:
        bars(c, t + 0.3, wt(6, "two", 1.2))
        if t > wt(6, "two", 1.2) + 0.4: tag(c, "Source: NASA Science (243 vs 225 Earth days)", t - wt(6, "two", 1.2) - 0.4, y=1320)
    else:
        tt = t - TB; confetti(c, t)
        cake(c, W / 2, 900, 1.2, t)
        sticker(c, "BIRTHDAY", W / 2, 420, 110, tt, bg=PINK, ang=-0.05)
        if t > wt(6, "bedtime", TB + 0.8): sticker(c, "BEFORE BEDTIME", W / 2, 1230, 86, t - wt(6, "bedtime", TB + 0.8), bg=PURPLE, outline=CYAN, ang=0.04)


def s7(c, t, d):   # F RED FLAG #2. spins backwards. Sun rises in the west
    background(c, t)
    TB = wt(7, "backwards", 1.8); TW_ = wt(7, "sun", 3.2)
    red_flag(c, 170, 480, 1.1, t + 0.1)
    sticker(c, "RED FLAG #2", 600, 400, 92, t + 0.1, bg=RED, outline=YELLOW, ang=-0.04, maxw=760)
    if t < TW_:
        venus(c, W / 2, 880, 300, t, spin=-0.5 if t > TB else 0.0)
        if t > TB:
            spin_arrow(c, W / 2, 880, 400, t, direction=-1)
            sticker(c, "BACKWARDS", W / 2, 1250, 96, t - TB, bg=YELLOW, fg=INK, outline=PINK, ang=0.04)
    else:
        tt = t - TW_
        sunrise_west(c, t, tt / 1.2)
        if t > wt(7, "west", TW_ + 0.8): stamp(c, "WEST?!", 680, 840, t - wt(7, "west", TW_ + 0.8), col=YELLOW, size=110, ang=-0.1)


def s9(c, t, d):   # F RED FLAG #3. 900 F. melt lead
    background(c, t)
    TN = wt(9, "nine", 1.5); TL = wt(9, "lead", 4.4)
    h = eout((t - TN + 0.2) / 0.8) if t > TN - 0.2 else 0
    red_flag(c, 170, 480, 1.1, t + 0.1)
    sticker(c, "RED FLAG #3", 600, 400, 92, t + 0.1, bg=RED, outline=YELLOW, ang=-0.04, maxw=760)
    if t < TL - 0.5:
        venus(c, 400, 900, 280, t, kind="radar", heat=0.8 * h)
        thermo(c, 880, 1080, 560, 1000 * h, t + 0.2)
        if t > TN: sticker(c, counter(t - TN, 0, 900, 0.7) + "°F", W / 2, 640, 110, t - TN, bg=hexc("FF5A1F"), outline=YELLOW)
        if t > TN + 0.3: tag(c, "Image: NASA/JPL (Magellan radar) · 900°F (475°C): NASA", t - TN - 0.3, y=1320)
    else:
        tt = t - TL + 0.5
        c.set_source_rgba(1, 0.35, 0.05, 0.35); c.paint()
        lead_bar(c, W / 2, 980, t, tt / 1.2)
        sticker(c, "MELTS LEAD", W / 2, 680, 110, tt, bg=hexc("FF5A1F"), outline=YELLOW)
        text(c, "475°C", W / 2, 1200, 64, col=YELLOW, stroke=8)


def s10(c, t, d):  # M I thought HOT meant CUTE! Not SELF-CLEANING OVEN!
    background(c, t)
    TO = wt(10, "self", 1.6)
    if t < TO:
        profile_card(c, 1, y=840, sc=0.8)
        for j in range(6):
            x = 200 + j * 140; y = 1180 - ((t * 300 + j * 90) % 700)
            heart(c, x, y, 34, PINK)
        sticker(c, "HOT = CUTE?", W / 2, 360, 104, t - wt(10, "hot", 0.4), bg=PINK, ang=-0.05)
    else:
        tt = t - TO
        oven(c, W / 2, 830, t, tt)
        sticker(c, "SELF-CLEANING OVEN", W / 2, 400, 80, tt, bg=hexc("FF5A1F"), outline=YELLOW, ang=-0.04)
        stamp(c, "~900°F", W / 2, 1230, tt - 0.4, col=YELLOW, size=90, ang=0.06)


def s11(c, t, d):  # F (whisper) air pushes down 90x harder. sulfuric acid clouds
    background(c, t, dim=0.9)
    S = _img("maat.png"); k = max(960 / S.get_width(), 1000 / S.get_height())
    c.save(); rrect(c, 60, 330, 960, 1000, 34); c.clip()
    c.translate(W / 2, 830); c.scale(k * (1 + 0.02 * t), k * (1 + 0.02 * t)); c.translate(-S.get_width() / 2, -S.get_height() / 2)
    c.set_source_surface(S, 0, 0); c.paint(); c.restore()
    c.set_source_rgba(*PINK, 1); c.set_line_width(6); rrect(c, 60, 330, 960, 1000, 34); c.stroke()
    background_overlay = cairo.LinearGradient(0, 0, 0, H); background_overlay.add_color_stop_rgba(0, *SPACE, 0.0)
    T9 = wt(11, "ninety", 1.6); TA = wt(11, "sulfuric", 3.8)
    press_arrows(c, t, ease((t - 0.3) / 0.4))
    if t > T9: sticker(c, counter(t - T9, 0, 90, 0.6) + "× EARTH'S PRESSURE", W / 2, 1180, 72, t - T9, bg=PURPLE, outline=CYAN)
    if t > TA:
        acid_clouds(c, t, ease((t - TA) / 0.5))
        sticker(c, "SULFURIC ACID CLOUDS", W / 2, 700, 74, t - TA - 0.2, bg=hexc("8BAE1E"), fg=INK, outline=YELLOW, ang=0.03)
    tag(c, "Image: NASA/JPL (Magellan, Maat Mons) · Facts: NASA", t - 0.5, y=1320)


def s12(c, t, d):  # M Crushing, toxic, eight months to turn around. Swipe left.
    background(c, t)
    TS = wt(12, "swipe", 3.4)
    profile_card(c, 1, y=840, sc=0.85, swipe=(t - TS) / 0.6 if t > TS else 0, stamp_t=(t - TS + 0.6) if t > TS - 0.6 else -1)
    for key, lab, y, col in (("crushing", "CRUSHING", 380, PURPLE), ("toxic", "TOXIC", 520, hexc("8BAE1E")), ("eight", "8-MONTH SPIN", 1260, RED)):
        if t > wt(12, key, 0.5) and t < TS + 0.3: sticker(c, lab, W / 2 + (-120 if key == "crushing" else 120 if key == "toxic" else 0), y, 76, t - wt(12, key, 0.5), bg=col, outline=YELLOW, ang=0.05 if key == "toxic" else -0.04, maxw=700)
    if t > TS: sticker(c, "<< SWIPE LEFT", W / 2, 1240, 100, t - TS, bg=RED, outline=YELLOW)


def s14(c, t, d):  # F Tomorrow on Planet Reviews: star so dense, sugar cube ~ mountain. Follow!
    background(c, t)
    TD = wt(14, "dense", 2.2); TC = wt(14, "sugar", 2.8); TM = wt(14, "mountain", 4.6); TF = wt(14, "follow", 5.4)
    sticker(c, "TOMORROW", W / 2, 330, 104, t + 0.1, bg=PINK, ang=-0.05)
    series_banner(c, t - wt(14, "planet", 0.6), y=470)
    neutron_star(c, W / 2, 760, 80, t, k=ease((t - 0.3) / 0.5))
    if t > TD: sticker(c, "SUPER DENSE STAR", W / 2, 620, 60, t - TD, bg=PURPLE, outline=CYAN, ang=0.04)
    if t > TC: balance(c, t, (t - TM) / 0.6 if t > TM else 0)
    if t > TF: sticker(c, "FOLLOW SO YOU DON'T MISS IT", W / 2, 1300, 62, t - TF, bg=YELLOW, fg=INK, outline=PINK)
    if t > TC + 0.3 and t < TF: tag(c, "Source: NASA Goddard (neutron stars)", t - TC - 0.3, y=1320)


def s15(c, t, d):  # M loop: If Venus ever finishes her day.
    hook_frame(c, t)
    sticker(c, "...IF SHE EVER", W / 2, 380, 96, t - 0.1, bg=PURPLE, outline=CYAN, ang=-0.04)
    if t > wt(15, "finishes", 0.9): sticker(c, "FINISHES HER DAY", W / 2, 1230, 92, t - wt(15, "finishes", 0.9), bg=YELLOW, fg=INK, outline=PINK, ang=0.04)


def s_end(c, t, d):
    background(c, t)
    end_card_logo(c, t, W / 2, 700, 250, LOGO)
    sticker(c, "FOLLOW", W / 2, 1060, 110, t - 0.4, ang=-0.04)
    if t > 0.7: text(c, "Tomorrow: the star so dense...", W / 2, 1200, 50, col=YELLOW, stroke=8, alpha=ease((t - 0.7) / 0.4))
    if t > 0.9: text(c, "@orbit.gossip · Planet Reviews", W / 2, 1290, 40, col=WHITE, stroke=8, alpha=ease((t - 0.9) / 0.4))


SCENES = {0: s0, 1: s1, 2: s2, 3: s3, 4: s4, 5: s5, 6: s6, 7: s7, 9: s9, 10: s10, 11: s11, 12: s12, 14: s14, 15: s15, NSC: s_end}
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
    s = ST; ev = [("boom", 0.0), ("pop", 0.05), ("ding", s[0] + wt(0, "longer", 1.0))]
    ev += [("pop", ST[o]) for o in ORDER[1:]]
    ev += [("trombone", s[1] + wt(1, "cry", 1.5))]
    ev += [("bubble", s[2] + wt(2, "popcorn", 0.5)), ("ding", s[2] + wt(2, "planet", 1.4)), ("whoosh", s[2] + wt(2, "swiping", 3.0))]
    ev += [("ding", s[3] + wt(3, "twin", 0.8)), ("pop", s[3] + wt(3, "next", 2.6))]
    ev += [("ding", s[4] + 0.1), ("scratch", s[4] + wt(4, "red", 1.2))] + [("tick", s[4] + wt(4, "two", 4.6) + k * 0.1) for k in range(8)]
    ev += [("pop", s[5] + wt(5, "monday", 1.2))] + [("tick", s[5] + wt(5, "monday", 1.2) + 0.3 + k * 0.25) for k in range(5)] + [("ding", s[5] + wt(5, "august", 2.6)), ("trombone", s[5] + wt(5, "august", 2.6) + 0.3)]
    ev += [("whoosh", s[6] + 0.2), ("pop", s[6] + wt(6, "birthday", 2.6)), ("thunk", s[6] + wt(6, "bedtime", 3.4))]
    ev += [("scratch", s[7] + 0.1), ("whoosh", s[7] + wt(7, "backwards", 1.8)), ("ding", s[7] + wt(7, "west", 4.0))]
    ev += [("scratch", s[9] + 0.1)] + [("tick", s[9] + wt(9, "nine", 1.5) + k * 0.08) for k in range(8)] + [("hiss", s[9] + wt(9, "lead", 4.4) - 0.5)]
    ev += [("bubble", s[10] + 0.1), ("clank", s[10] + wt(10, "self", 1.6)), ("ding", s[10] + wt(10, "self", 1.6) + 0.4)]
    ev += [("thunk", s[11] + 0.3), ("thunk", s[11] + wt(11, "ninety", 1.6)), ("bubble", s[11] + wt(11, "sulfuric", 3.8))]
    ev += [("thunk", s[12] + wt(12, "crushing", 0.3)), ("thunk", s[12] + wt(12, "toxic", 0.9)), ("whoosh", s[12] + wt(12, "swipe", 3.4)), ("trombone", s[12] + wt(12, "swipe", 3.4) + 0.4)]
    ev += [("ding", s[14] + 0.1), ("boom", s[14] + wt(14, "mountain", 4.6)), ("pop", s[14] + wt(14, "follow", 5.4))]
    ev += [("boom", s[15] + 0.05), ("pop", s[NSC] + 0.4)]
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
