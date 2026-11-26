"""How On Earth render engine v2 (video 002+).
Shared helpers: procedural textures (numpy fBm -> cairo), camera, particles, kinetic captions
with gold keywords, colour-wipe transitions (never black), labels, counters, badge, end card.
Rules baked in (PLAYBOOK "Making it NOT boring" + "Platform flags to avoid"):
 - every frame is filled edge to edge with texture (no flat bands, no fades to black)
 - captions 1-3 words, pop-in, CAPS/number words gold
"""
import cairo, math, random, numpy as np
from PIL import Image

W, H, FPS = 1080, 1920, 30


def ease(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)
def eout(t): t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3
def back(t):  # overshoot pop
    t = max(0.0, min(1.0, t)); s = 1.70158; t -= 1; return t * t * ((s + 1) * t + s) + 1
def lerp(a, b, t): return a + (b - a) * t
def lerpc(c1, c2, t): return tuple(lerp(a, b, t) for a, b in zip(c1, c2))
def hexc(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

NAVY, MID, BLUE, ORANGE, GOLD = map(hexc, ["0B1026", "1B2B5C", "3E5C9A", "F28C38", "FFC857"])
WHITE = (1, 1, 1)


# ---------------- textures ----------------
def fbm(h, w, octaves=6, seed=0, base=4):
    rng = np.random.default_rng(seed); out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        n = base * 2 ** o
        g = rng.random((max(2, n * h // w), n)).astype(np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += amp * np.asarray(im, np.float32) / 255; tot += amp; amp *= 0.55
    out /= tot; out = (out - out.min()) / (out.max() - out.min() + 1e-6); return out


def to_surface(rgb):
    """rgb float array HxWx3 in 0..1 -> cairo ImageSurface"""
    h, w, _ = rgb.shape
    a = np.empty((h, w, 4), np.uint8)
    a[..., 0] = np.clip(rgb[..., 2] * 255, 0, 255); a[..., 1] = np.clip(rgb[..., 1] * 255, 0, 255)
    a[..., 2] = np.clip(rgb[..., 0] * 255, 0, 255); a[..., 3] = 255
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    stride = s.get_stride(); buf = s.get_data()
    np.ndarray((h, stride // 4, 4), np.uint8, buf)[:, :w, :] = a
    s.mark_dirty(); return s


def ramp(n, stops):
    """n: 0..1 array; stops list of (pos, (r,g,b))"""
    out = np.zeros(n.shape + (3,), np.float32)
    for i in range(3):
        out[..., i] = np.interp(n, [p for p, _ in stops], [c[i] for _, c in stops])
    return out


def make_textures(seed=1):
    T = {}
    hh, ww = H, W
    y = np.linspace(0, 1, hh)[:, None] * np.ones((1, ww))
    # sky: blue top -> warm horizon, with clouds
    n = fbm(hh, ww, 6, seed, 3)
    sky = ramp(y, [(0, hexc("3C6FB4")), (0.25, hexc("6E9BD0")), (0.4, hexc("F2B27A")), (1, hexc("F7C98E"))])
    cl = np.clip((n - 0.45) * 2.2, 0, 1)[..., None]
    T["sky"] = to_surface(sky * (1 - 0.55 * cl) + 0.55 * cl * np.array([1, 0.97, 0.93]))
    # rock: banded warm brown volcanic rock
    n1 = fbm(hh, ww, 7, seed + 1, 6); n2 = fbm(hh, ww, 5, seed + 2, 2)
    strata = 0.5 + 0.5 * np.sin(y * 140 + n2 * 9)
    v = np.clip(0.55 * n1 + 0.25 * strata + 0.2 * n2, 0, 1)
    T["rock"] = to_surface(ramp(v, [(0, hexc("4A2E22")), (0.35, hexc("7A4A32")), (0.6, hexc("A8693F")), (0.8, hexc("C98E58")), (1, hexc("E2B07A"))]))
    # concrete: pale grey-beige with speckle
    sp = np.random.default_rng(seed + 3).random((hh, ww)).astype(np.float32)
    v = 0.7 * fbm(hh, ww, 6, seed + 4, 5) + 0.3 * sp
    T["concrete"] = to_surface(ramp(v, [(0, hexc("9C968C")), (0.5, hexc("CFC8BB")), (1, hexc("ECE6DA"))]))
    # water: teal/blue ripples
    v = fbm(hh, ww, 6, seed + 5, 8)
    rip = 0.5 + 0.5 * np.sin(y * 260 + v * 12)
    T["water"] = to_surface(ramp(0.6 * v + 0.4 * rip, [(0, hexc("1C5F7A")), (0.5, hexc("2F8FA8")), (0.85, hexc("6CC4CF")), (1, hexc("D8F4F2"))]))
    # terrain for maps
    v = fbm(hh, ww, 7, seed + 6, 4)
    T["terrain"] = to_surface(ramp(v, [(0, hexc("5E7B3E")), (0.4, hexc("8D9A55")), (0.6, hexc("C2A36A")), (0.8, hexc("A9744A")), (1, hexc("EAD7A8"))]))
    # sand (dry riverbed)
    v = fbm(hh, ww, 6, seed + 7, 10)
    T["sand"] = to_surface(ramp(v, [(0, hexc("B98B57")), (1, hexc("E8C88E"))]))
    # blueprint / x-ray background
    v = fbm(hh, ww, 6, seed + 8, 3)
    T["xray"] = to_surface(ramp(v, [(0, hexc("123A6B")), (0.5, hexc("1D5A9A")), (1, hexc("3D86C6"))]))
    return T


def tex(c, surf, dx=0, dy=0, alpha=1.0):
    p = cairo.SurfacePattern(surf); p.set_extend(cairo.EXTEND_REFLECT)
    m = cairo.Matrix(); m.translate(-dx, -dy); p.set_matrix(m)
    c.set_source(p)
    return p


def fill_tex(c, surf, dx=0, dy=0, alpha=1.0):
    """fill current path with texture"""
    tex(c, surf, dx, dy)
    if alpha >= 1: c.fill()
    else:
        c.save(); c.clip(); c.paint_with_alpha(alpha); c.restore()


def paint_tex(c, surf, dx=0, dy=0, alpha=1.0, pad=400):
    c.rectangle(-pad, -pad, W + 2 * pad, H + 2 * pad); fill_tex(c, surf, dx, dy, alpha)


def rrect(c, x, y, w, h, r):
    c.new_sub_path(); c.arc(x + w - r, y + r, r, -math.pi / 2, 0); c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi); c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi); c.close_path()


# ---------------- text ----------------
def fam(s): return "Montserrat" if set(s) & set("ṉṟṯ") else "Poppins"


def text(c, s, x, y, size, col=WHITE, align="center", alpha=1, stroke=0, weight=cairo.FONT_WEIGHT_BOLD):
    c.select_font_face(fam(s), cairo.FONT_SLANT_NORMAL, weight); c.set_font_size(size)
    ext = c.text_extents(s)
    xx = x - ext.x_advance / 2 if align == "center" else (x - ext.x_advance if align == "right" else x)
    c.move_to(xx, y); c.text_path(s)
    if stroke:
        c.set_source_rgba(0, 0, 0, 0.85 * alpha); c.set_line_width(stroke); c.set_line_join(cairo.LINE_JOIN_ROUND); c.stroke_preserve()
    c.set_source_rgba(*col, alpha); c.fill(); return ext.x_advance


def text_w(c, s, size):
    c.select_font_face(fam(s), cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(size)
    return c.text_extents(s).x_advance


def pop_text(c, s, x, y, size, t, col=GOLD, stroke=12, maxw=900):
    """big text that pops in with overshoot at t>=0"""
    if t <= 0: return
    w = text_w(c, s, size)
    if w > maxw: size *= maxw / w
    k = back(t / 0.35)
    c.save(); c.translate(x, y); c.scale(k, k); text(c, s, 0, 0, size, col=col, stroke=stroke, alpha=min(1, t / 0.12)); c.restore()


def label(c, s, y, t, x=W / 2, size=46, bg=GOLD, fg=NAVY):
    if t <= 0: return
    a = min(1, t / 0.2); k = back(t / 0.35)
    w = text_w(c, s, size) + 64; h = size + 34
    c.save(); c.translate(x, y + h / 2); c.scale(k, k)
    c.set_source_rgba(0, 0, 0, 0.35 * a); rrect(c, -w / 2 + 6, -h / 2 + 8, w, h, h / 2); c.fill()
    c.set_source_rgba(*bg, a); rrect(c, -w / 2, -h / 2, w, h, h / 2); c.fill()
    text(c, s, 0, size * 0.36, size, col=fg, alpha=a); c.restore()


def mini_globe(c, cx, cy, r, t=0.0):
    """small drawn Earth icon: ocean gradient, stylised continents, grid lines, gold orbit"""
    c.save()
    g = cairo.RadialGradient(cx - r * 0.35, cy - r * 0.35, r * 0.1, cx, cy, r)
    g.add_color_stop_rgb(0, *hexc("7FD3FF")); g.add_color_stop_rgb(0.6, *hexc("2A7DD1")); g.add_color_stop_rgb(1, *hexc("103E85"))
    c.arc(cx, cy, r, 0, 2 * math.pi); c.set_source(g); c.fill_preserve(); c.clip()
    off = (t * 0.25 % 1.0) * 2 * r  # continents drift slowly = spinning globe
    c.set_source_rgb(*hexc("4CB963"))
    for dx in (-2 * r, 0, 2 * r):
        x0 = cx - r + off + dx
        for (px, py, rx, ry) in ((0.35, -0.35, 0.35, 0.28), (0.55, 0.25, 0.22, 0.38), (1.25, -0.15, 0.32, 0.25), (1.45, 0.4, 0.15, 0.14)):
            c.save(); c.translate(x0 + px * r, cy + py * r); c.scale(rx * r, ry * r); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore(); c.fill()
    c.set_source_rgba(1, 1, 1, 0.35); c.set_line_width(max(1, r * 0.06))
    for k in (-0.5, 0, 0.5):
        c.save(); c.translate(cx, cy + k * r); c.scale(1, 0.18); c.arc(0, 0, r * math.sqrt(1 - k * k), 0, 2 * math.pi); c.restore(); c.stroke()
    c.save(); c.translate(cx, cy); c.scale(0.45, 1); c.arc(0, 0, r, 0, 2 * math.pi); c.restore(); c.stroke()
    hl = cairo.RadialGradient(cx - r * 0.4, cy - r * 0.45, 0, cx - r * 0.4, cy - r * 0.45, r * 0.7)
    hl.add_color_stop_rgba(0, 1, 1, 1, 0.55); hl.add_color_stop_rgba(1, 1, 1, 1, 0)
    c.set_source(hl); c.paint()
    c.restore()
    c.save(); c.translate(cx, cy); c.rotate(-0.35); c.scale(1.45, 0.42)
    c.arc(0, 0, r, math.pi * 0.95, math.pi * 2.05); c.restore()
    c.set_source_rgba(*GOLD, 1); c.set_line_width(max(2, r * 0.13)); c.set_line_cap(cairo.LINE_CAP_ROUND); c.stroke()
    a = t * 2.2; c.set_source_rgba(1, 0.97, 0.8, 1)
    c.arc(cx + math.cos(a) * r * 1.45 * math.cos(-0.35) - math.sin(a) * r * 0.42 * math.sin(-0.35),
          cy + math.cos(a) * r * 1.45 * math.sin(-0.35) + math.sin(a) * r * 0.42 * math.cos(-0.35), r * 0.12, 0, 2 * math.pi); c.fill()


def badge(c, t=0.0, y=190):
    """channel badge v2 (Bidhan 2026-11-20: 'make the icon more attractive'): glossy navy pill, gold gradient rim,
    spinning mini-globe with orbit, HOW ON (white) EARTH? (gold), light sweep every 4 s"""
    c.save()
    size = 38; h = 70
    tw = text_w(c, "HOW ON ", size); tw2 = text_w(c, "EARTH?", size)
    w = 70 + tw + tw2 + 34; x = W / 2 - w / 2
    c.set_source_rgba(0, 0, 0, 0.35); rrect(c, x + 3, y + 6, w, h, h / 2); c.fill()
    g = cairo.LinearGradient(0, y, 0, y + h); g.add_color_stop_rgba(0, *hexc("26407F"), 0.92); g.add_color_stop_rgba(1, *NAVY, 0.92)
    rrect(c, x, y, w, h, h / 2); c.set_source(g); c.fill()
    rim = cairo.LinearGradient(x, 0, x + w, 0)
    rim.add_color_stop_rgb(0, *hexc("FFE29A")); rim.add_color_stop_rgb(0.5, *ORANGE); rim.add_color_stop_rgb(1, *hexc("FFE29A"))
    rrect(c, x + 2, y + 2, w - 4, h - 4, h / 2 - 2); c.set_source(rim); c.set_line_width(4); c.stroke()
    gl = cairo.LinearGradient(0, y, 0, y + h / 2); gl.add_color_stop_rgba(0, 1, 1, 1, 0.22); gl.add_color_stop_rgba(1, 1, 1, 1, 0)
    rrect(c, x + 6, y + 5, w - 12, h / 2 - 4, h / 4); c.set_source(gl); c.fill()
    ph = (t % 4.0) / 0.8
    if ph < 1:
        sx = x + ph * (w + 120) - 60
        c.save(); rrect(c, x, y, w, h, h / 2); c.clip()
        sg = cairo.LinearGradient(sx - 40, 0, sx + 40, 0)
        sg.add_color_stop_rgba(0, 1, 1, 1, 0); sg.add_color_stop_rgba(0.5, 1, 1, 1, 0.45); sg.add_color_stop_rgba(1, 1, 1, 1, 0)
        c.set_source(sg); c.paint(); c.restore()
    mini_globe(c, x + 40, y + h / 2, 22, t)
    tx = x + 76; ty = y + h / 2 + size * 0.36
    text(c, "HOW ON ", tx, ty, size, col=WHITE, align="left", stroke=4)
    text(c, "EARTH?", tx + tw, ty, size, col=GOLD, align="left", stroke=4)
    c.restore()


def end_card_logo(c, t, cx, cy, r, logo):
    """end-card logo v2: glowing pulsing halo, rotating gold arcs, logo pops in"""
    k = back(t / 0.45)
    for i in range(6, 0, -1):
        c.set_source_rgba(*GOLD, 0.05 * (1 + 0.3 * math.sin(t * 5))); c.arc(cx, cy, r * k + i * 14, 0, 2 * math.pi); c.fill()
    c.save(); c.translate(cx, cy); c.rotate(t * 1.4); c.set_line_cap(cairo.LINE_CAP_ROUND)
    for j in range(3):
        c.arc(0, 0, r * k + 26, j * 2.09, j * 2.09 + 1.2); c.set_source_rgba(*GOLD, 0.95); c.set_line_width(8); c.stroke()
    c.restore()
    c.save(); s = r * k / 540; c.translate(cx - 540 * s, cy - 540 * s); c.scale(s, s)
    c.arc(540, 540, 540, 0, 2 * math.pi); c.clip(); c.set_source_surface(logo, 0, 0); c.paint(); c.restore()
    c.set_source_rgba(1, 1, 1, 0.9); c.set_line_width(6); c.arc(cx, cy, r * k, 0, 2 * math.pi); c.stroke()


# ---------------- captions ----------------
def chunks(cap, dur):
    words = cap.split(); out = []; cur = []
    for w in words:
        cur.append(w)
        if len(cur) >= 3 or w[-1] in ".,?!" or (len(cur) >= 2 and len(" ".join(cur)) > 16):
            out.append(cur); cur = []
    if cur: out.append(cur)
    tot = sum(len(" ".join(x)) + 4 for x in out); t = 0; res = []
    for x in out:
        d = dur * (len(" ".join(x)) + 4) / tot; res.append((t, t + d, x)); t += d
    return res


CAP_ACCENT = GOLD   # keyword colour in captions; a render may set engine.CAP_ACCENT per video (look rotation)


def is_key(w):
    core = w.strip(".,?!'\"")
    return (core.isupper() and len(core) > 1) or any(ch.isdigit() for ch in core)


SPK_COL = {"M": hexc("6FB7FF"), "F": GOLD}          # speaker dot colours (man blue, woman gold)
SPK_TXT = {"M": (0.90, 0.95, 1.0), "F": (1.0, 0.95, 0.88), None: WHITE}  # subtle per-speaker tint of plain words


def word_chunks(cap, words):
    """caption chunks timed to the real spoken words (ElevenLabs timestamps). Caption words map 1:1 to spoken
    words when the counts match (write scripts so they do: "fifteen-storey" <-> "15-STOREY"), else by position."""
    cw = cap.split(); n, m = len(cw), len(words)
    tms = [words[i][1] if n == m else words[min(m - 1, int(i * m / n))][1] for i in range(n)]
    groups = []; cur = []
    for k, w in enumerate(cw):
        cur.append(k)
        if len(cur) >= 3 or w[-1] in ".,?!" or (len(cur) >= 2 and len(" ".join(cw[j] for j in cur)) > 16):
            groups.append(cur); cur = []
    if cur: groups.append(cur)
    res = []
    for gi, g in enumerate(groups):
        a = max(0.0, tms[g[0]] - 0.06)                        # appear a hair BEFORE the word is heard
        b = (tms[groups[gi + 1][0]] - 0.06) if gi + 1 < len(groups) else 1e9
        res.append((a, b, [cw[j] for j in g]))
    return res


def captions(c, cap, dur, t, y=1440, speaker=None, dot=False, words=None):
    """kinetic captions. With words=[[word, start, end], ...] (tts_el.py) every chunk is synced to the voice;
    otherwise chunks are spread over the line by length (old behaviour, can lag)."""
    ch = word_chunks(cap, words) if words else chunks(cap, dur)
    for i, (a, b, ws) in enumerate(ch):
        if a <= t < b or (t >= b and i == len(ch) - 1):
            k = back((t - a) / 0.1)
            size = 84
            words_ = list(ws)
            full = " ".join(words_)
            tw = text_w(c, full, size)
            if tw > 880: size *= 880 / tw; tw = 880
            c.save(); c.translate(W / 2, y); s_ = 0.9 + 0.1 * k; c.scale(s_, s_)
            x = -tw / 2
            if dot and speaker in SPK_COL:  # off by default (Bidhan: dots looked like bullets)
                dc = SPK_COL[speaker]; dx = x - 44; dy = -size * 0.33
                c.set_source_rgba(*dc, 0.3); c.arc(dx, dy, 24, 0, 2 * math.pi); c.fill()
                c.set_source_rgba(0, 0, 0, 0.8); c.arc(dx, dy, 15, 0, 2 * math.pi); c.fill()
                c.set_source_rgba(*dc, 1); c.arc(dx, dy, 12, 0, 2 * math.pi); c.fill()
            for w in words_:
                col = CAP_ACCENT if is_key(w) else SPK_TXT.get(speaker, WHITE)
                adv = text(c, w, x, 0, size, col=col, align="left", stroke=16)
                x += adv + text_w(c, " ", size)
            c.restore(); return


# ---------------- particles ----------------
class Particles:
    def __init__(self, n, seed=0):
        r = random.Random(seed); self.p = [(r.random(), r.random(), r.random(), r.random()) for _ in range(n)]

    def dust(self, c, t, col=(1, 0.95, 0.85), alpha=0.5, speed=40, size=3):
        for a, b, s, ph in self.p:
            x = (a * W + math.sin(t * 0.7 + ph * 6) * 30) % W
            y = (b * H - t * speed * (0.5 + s)) % H
            c.set_source_rgba(*col, alpha * (0.4 + 0.6 * abs(math.sin(t * 2 + ph * 9))))
            c.arc(x, y, size * (0.5 + s), 0, 2 * math.pi); c.fill()

    def steam(self, c, t, x0, x1, y0, rise=500, alpha=0.35, col=(1, 1, 1)):
        for a, b, s, ph in self.p:
            life = (t * (0.25 + 0.2 * s) + ph) % 1.0
            x = lerp(x0, x1, a) + math.sin(life * 6 + ph * 7) * 40 * life
            y = y0 - life * rise * (0.6 + s)
            r = 18 + 90 * life * (0.5 + s)
            c.set_source_rgba(*col, alpha * math.sin(math.pi * life) * (0.5 + 0.5 * b))
            c.arc(x, y, r, 0, 2 * math.pi); c.fill()

    def sparks(self, c, t, x, y, alpha=1):
        for a, b, s, ph in self.p[:40]:
            life = (t * 2.5 + ph) % 1.0
            ang = a * 2 * math.pi; d = life * 120 * (0.5 + s)
            c.set_source_rgba(1, lerp(0.95, 0.5, life), 0.3, alpha * (1 - life))
            c.arc(x + math.cos(ang) * d, y + math.sin(ang) * d - 40 * life, 4 * (1 - life) + 1, 0, 2 * math.pi); c.fill()


def glow_stroke(c, path_fn, col, width, alpha=1, layers=4):
    for i in range(layers, 0, -1):
        path_fn(); c.set_source_rgba(*col, alpha * 0.12); c.set_line_width(width + i * width * 0.9); c.stroke()
    path_fn(); c.set_source_rgba(*col, alpha); c.set_line_width(width); c.stroke()


def wipe(c, t, col=GOLD, dur=0.22):
    """diagonal colour band sweeping across at a scene start (replaces fades to black)"""
    if t >= dur: return
    k = t / dur; x = lerp(-700, W + 700, k)
    c.save(); c.move_to(x - 260, -100); c.line_to(x + 260, -100); c.line_to(x - 140, H + 100); c.line_to(x - 660, H + 100); c.close_path()
    c.set_source_rgba(*col, 0.85); c.fill(); c.restore()


def thermal_rgb(h):
    """h 0 (cool blue) .. 1 (hot yellow-white)"""
    stops = [(0, (0.18, 0.45, 0.85)), (0.35, (0.55, 0.2, 0.6)), (0.6, (0.9, 0.25, 0.15)), (0.8, (1.0, 0.55, 0.1)), (1, (1.0, 0.92, 0.5))]
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if h <= p1: return lerpc(c0, c1, (h - p0) / (p1 - p0))
    return stops[-1][1]


def source_tag(c, s, t, y=1262, x=70, size=24):
    """small on-screen source / credit line (anti-slop rule: show a checkable source), above the caption zone"""
    if t <= 0: return
    a = min(1, t / 0.3); c.save()
    c.select_font_face("Poppins", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(size)
    w = c.text_extents(s).x_advance + 36
    c.set_source_rgba(0.04, 0.06, 0.15, 0.55 * a); rrect(c, x, y - size - 10, w, size + 24, (size + 24) / 2); c.fill()
    c.set_source_rgba(*GOLD, 0.95 * a); c.arc(x + 16, y - size * 0.35 + 2, 5, 0, 2 * math.pi); c.fill()
    c.move_to(x + 28, y); c.set_source_rgba(1, 1, 1, 0.92 * a); c.show_text(s); c.restore()


def clock(c, cx, cy, r, t, strike=0.0, spin=1.0):
    """wall clock icon with spinning hands; strike 0..1 draws a red slash (\"never on the hour\")"""
    c.save()
    c.set_source_rgba(0, 0, 0, 0.35); c.arc(cx + 6, cy + 10, r, 0, 2 * math.pi); c.fill()
    g = cairo.RadialGradient(cx - r * 0.3, cy - r * 0.3, r * 0.1, cx, cy, r)
    g.add_color_stop_rgb(0, 1, 1, 1); g.add_color_stop_rgb(1, 0.85, 0.88, 0.95)
    c.arc(cx, cy, r, 0, 2 * math.pi); c.set_source(g); c.fill()
    c.set_source_rgb(*NAVY); c.set_line_width(r * 0.09); c.arc(cx, cy, r, 0, 2 * math.pi); c.stroke()
    for k in range(12):
        a = k * math.pi / 6; r0 = r * (0.78 if k % 3 else 0.7)
        c.move_to(cx + math.cos(a) * r0, cy + math.sin(a) * r0); c.line_to(cx + math.cos(a) * r * 0.88, cy + math.sin(a) * r * 0.88)
        c.set_line_width(r * (0.05 if k % 3 else 0.08)); c.stroke()
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for ln, wd, sp in ((0.5, 0.08, 1.0), (0.75, 0.05, 12.0)):
        a = -math.pi / 2 + t * spin * sp * 0.9
        c.move_to(cx, cy); c.line_to(cx + math.cos(a) * r * ln, cy + math.sin(a) * r * ln); c.set_line_width(r * wd); c.stroke()
    c.set_source_rgb(*ORANGE); c.arc(cx, cy, r * 0.07, 0, 2 * math.pi); c.fill()
    if strike > 0:
        k = eout(strike); x0, y0 = cx - r * 1.05, cy - r * 1.05
        c.move_to(x0, y0); c.line_to(x0 + 2.1 * r * k, y0 + 2.1 * r * k)
        c.set_source_rgba(0, 0, 0, 0.6); c.set_line_width(r * 0.26); c.stroke()
        c.move_to(x0, y0); c.line_to(x0 + 2.1 * r * k, y0 + 2.1 * r * k)
        c.set_source_rgb(0.92, 0.18, 0.2); c.set_line_width(r * 0.17); c.stroke()
    c.restore()


def stopwatch(c, cx, cy, r, t, run=True, col=None):
    """stopwatch icon; hand sweeps while run"""
    col = col or GOLD
    c.save()
    c.set_source_rgb(*col); rrect(c, cx - r * 0.18, cy - r * 1.32, r * 0.36, r * 0.22, r * 0.06); c.fill()
    c.rectangle(cx - r * 0.07, cy - r * 1.12, r * 0.14, r * 0.16); c.fill()
    clock(c, cx, cy, r, 0, spin=0)
    a = -math.pi / 2 + (t * 2 * math.pi / 3 if run else 0)
    c.set_line_cap(cairo.LINE_CAP_ROUND); c.set_source_rgb(0.9, 0.2, 0.2)
    c.move_to(cx, cy); c.line_to(cx + math.cos(a) * r * 0.8, cy + math.sin(a) * r * 0.8); c.set_line_width(r * 0.06); c.stroke()
    c.restore()


# ---------------- look v3 (added 2026-11-23, video 005 remake: "animations look the same") ----------------
def ribbon(c, s, x, y, size, t, bg=(0.25, 0.82, 1.0), fg=NAVY, angle=-0.035, maxw=940, sub=None):
    """headline in a tilted colour block that slides in from the left with a light sweep (replaces gold pop_text)"""
    if t <= 0: return
    w = text_w(c, s, size)
    if w > maxw - 80: size *= (maxw - 80) / w; w = maxw - 80
    k = eout(t / 0.32); bw, bh = w + 80, size * 1.35
    c.save(); c.translate(x + (1 - k) * -W, y); c.rotate(angle)
    c.set_source_rgba(0, 0, 0, 0.45); c.rectangle(-bw / 2 + 12, -bh / 2 + 14, bw, bh); c.fill()
    c.set_source_rgb(*bg); c.rectangle(-bw / 2, -bh / 2, bw, bh); c.fill()
    sw = (t * 0.9) % 2.5
    if sw < 1:  # light sweep
        g = cairo.LinearGradient(-bw / 2 + sw * bw * 1.4 - 200, 0, -bw / 2 + sw * bw * 1.4, 0)
        g.add_color_stop_rgba(0, 1, 1, 1, 0); g.add_color_stop_rgba(0.5, 1, 1, 1, 0.35); g.add_color_stop_rgba(1, 1, 1, 1, 0)
        c.rectangle(-bw / 2, -bh / 2, bw, bh); c.set_source(g); c.fill()
    text(c, s, 0, size * 0.36, size, col=fg)
    c.restore()
    if sub and t > 0.25:
        a = ease((t - 0.25) / 0.25)
        c.save(); c.translate(x, y + bh / 2 + 50); c.rotate(angle)
        sz = 46; sw2 = text_w(c, sub, sz) + 40
        c.set_source_rgba(0.04, 0.06, 0.15, 0.85 * a); c.rectangle(-sw2 / 2, -sz * 0.75, sw2, sz * 1.25); c.fill()
        text(c, sub, 0, sz * 0.25, sz, col=WHITE, alpha=a); c.restore()


def neon_path(c, pts, k, col=(0.25, 0.82, 1.0), width=10, t=0.0, dash=True):
    """glowing polyline drawn up to fraction k (0..1) of its length, with travelling light dashes"""
    if k <= 0 or len(pts) < 2: return
    segs = [math.dist(a, b) for a, b in zip(pts, pts[1:])]; L = sum(segs) * min(1, k)
    out = [pts[0]]; acc = 0
    for (a, b), sl in zip(zip(pts, pts[1:]), segs):
        if acc + sl >= L:
            u = (L - acc) / sl if sl else 0; out.append((lerp(a[0], b[0], u), lerp(a[1], b[1], u))); break
        out.append(b); acc += sl
    def path():
        c.move_to(*out[0]); [c.line_to(*p) for p in out[1:]]
    c.save(); c.set_line_cap(cairo.LINE_CAP_ROUND); c.set_line_join(cairo.LINE_JOIN_ROUND)
    for wmul, a in ((4.0, 0.12), (2.4, 0.22), (1.4, 0.5)):
        path(); c.set_source_rgba(*col, a); c.set_line_width(width * wmul); c.stroke()
    path(); c.set_source_rgba(1, 1, 1, 0.95); c.set_line_width(width * 0.55); c.stroke()
    if dash:
        path(); c.set_dash([18, 60], -t * 160); c.set_source_rgba(1, 1, 1, 0.9); c.set_line_width(width * 0.9); c.stroke(); c.set_dash([])
    c.restore()
    return out[-1]


def ring_marker(c, x, y, t, col=(0.25, 0.82, 1.0), r=26):
    """pulsing target ring (radar ping) marking a spot on a satellite image"""
    if t <= 0: return
    k = back(t / 0.35)
    for j in range(2):
        ph = (t * 0.9 + j * 0.5) % 1.0
        c.set_source_rgba(*col, 0.7 * (1 - ph)); c.set_line_width(5); c.arc(x, y, r + 70 * ph, 0, 2 * math.pi); c.stroke()
    c.set_source_rgba(0, 0, 0, 0.5); c.arc(x, y, r * k + 6, 0, 2 * math.pi); c.fill()
    c.set_source_rgba(*col, 1); c.arc(x, y, r * k, 0, 2 * math.pi); c.fill()
    c.set_source_rgba(1, 1, 1, 1); c.arc(x, y, r * k * 0.4, 0, 2 * math.pi); c.fill()


def whip(surf, t, dur=0.24, direction=1, maxpx=150):
    """whip-pan transition: horizontal motion smear on the finished frame for the first `dur` s of a scene
    (replaces the gold diagonal wipe). Works in place on an RGB24/ARGB32 cairo surface."""
    if t >= dur: return
    surf.flush()
    a = np.ndarray((H, surf.get_stride() // 4, 4), np.uint8, surf.get_data())[:, :W, :3]
    amt = int(maxpx * (1 - eout(t / dur)))
    if amt < 4: return
    src = a.astype(np.float32); acc = np.zeros_like(src); n = 7
    for i in range(n):
        acc += np.roll(src, direction * int(amt * (i / (n - 1) - 0.5)), axis=1)
    a[...] = (acc / n).astype(np.uint8); surf.mark_dirty()
