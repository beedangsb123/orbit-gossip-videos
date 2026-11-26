"""EXTRAS BEYOND THE VIDEO (PLAYBOOK, Bidhan 2026-11-25) — cheap posts with NO ElevenLabs voice:
  story   : 15 s meme/"did you know" Story (1080x1920 mp4) over a real free-licence photo + original synth bed + pops
  card    : 1080x1350 meme / fact card (Facebook photo post, Instagram carousel slide)
  slides  : carousel slide set, 1080x1350 (Instagram) and 1080x1920 (TikTok photo mode)
All text comes from the spec JSON (facts already verified for the main videos). Own meme FORMATS only
("NOBODY: / X:", "POV:", "EXPECTATION / REALITY", "REAL OR FAKE?", "RATE THIS") — never templates, faces or logos.
usage:
  python extras.py story spec.json out.mp4        spec: {"photo", "focus":[x,y], "top", "line1", "line2", "fact", "fact_sub", "credit", "seed"}
  python extras.py card  spec.json out.jpg        spec: {"photo", "focus", "kicker", "headline", "answer", "credit"}
  python extras.py slides spec.json outprefix     spec: {"photo", "slides":[{"photo"?, "kicker","headline","body"}], "credit"}"""
import sys, os, json, math, subprocess, cairo, numpy as np
from PIL import Image, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import (text, text_w, rrect, hexc, ease, eout, back, lerp, to_surface, mini_globe, fbm)

Image.MAX_IMAGE_PIXELS = None
FPS = 30
INK = hexc("14161C"); CREAM = hexc("F6E9CF"); RED = hexc("FF5233"); GOLDC = hexc("FFC857"); TEAL = hexc("2EE6D6")


def load(photo, w, h, focus=(0.5, 0.5), z=1.0):
    im = Image.open(photo).convert("RGB")
    r = max(w * 1.25 * z / im.width, h * 1.25 * z / im.height)
    return im.resize((int(im.width * r) + 2, int(im.height * r) + 2), Image.LANCZOS), focus


def crop(im, focus, w, h, z):
    cw, ch = w * 1.25 / z, h * 1.25 / z
    cx = min(max(focus[0] * im.width, cw / 2), im.width - cw / 2); cy = min(max(focus[1] * im.height, ch / 2), im.height - ch / 2)
    a = np.asarray(im.resize((w, h), Image.BILINEAR, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)), np.float32)
    yy = np.linspace(-1, 1, h)[:, None]; xx = np.linspace(-1, 1, w)[None, :]
    a *= (1 - 0.18 * (xx ** 2 + 0.6 * yy ** 2))[..., None]          # soft vignette, edges keep detail (no flat border)
    return a


def paint(c, a):
    s = to_surface(np.clip(a, 0, 255) / 255); c.set_source_surface(s, 0, 0); c.paint()


def box(c, s, x, y, size, k, bg=CREAM, fg=INK, maxw=900, ang=0.0):
    if k <= 0: return
    w = text_w(c, s, size)
    if w > maxw - 60: size *= (maxw - 60) / w; w = maxw - 60
    sc = 0.85 + 0.15 * back(min(1, k))
    c.save(); c.translate(x, y); c.rotate(ang); c.scale(sc, sc)
    c.set_source_rgba(0, 0, 0, 0.35 * min(1, k)); rrect(c, -w / 2 - 30 + 8, -size * 0.75 + 10, w + 60, size * 1.5, 16); c.fill()
    c.set_source_rgba(*bg, min(1, k)); rrect(c, -w / 2 - 30, -size * 0.75, w + 60, size * 1.5, 16); c.fill()
    text(c, s, 0, size * 0.35, size, col=fg, alpha=min(1, k)); c.restore()


def wrap(c, s, size, maxw):
    lines, cur = [], ""
    for wd in s.split():
        t = (cur + " " + wd).strip()
        if text_w(c, t, size) > maxw and cur: lines.append(cur); cur = wd
        else: cur = t
    if cur: lines.append(cur)
    return lines


def para(c, s, x, y, size, maxw, col=(1, 1, 1), alpha=1.0, stroke=10, gap=1.18):
    for i, ln in enumerate(wrap(c, s, size, maxw)):
        text(c, ln, x, y + i * size * gap, size, col=col, alpha=alpha, stroke=stroke)
    return y + len(wrap(c, s, size, maxw)) * size * gap


def handle(c, x, y, size=34, alpha=1.0, W=1080):
    mini_globe(c, x - text_w(c, "@thehowonearth", size) / 2 - 34, y - size * 0.35, size * 0.55, 0.0)
    text(c, "@thehowonearth", x + 10, y, size, col=(1, 1, 1), stroke=8, alpha=alpha)


# ---------------- story video ----------------
def story(spec, out):
    W, H = 1080, 1920; dur = float(spec.get("dur", 15.0))
    im, f = load(spec["photo"], W, H, tuple(spec.get("focus", (0.5, 0.5))))
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H); c = cairo.Context(surf)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", out + ".wav", "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                          "-shortest", out], stdin=subprocess.PIPE)
    sfx = []
    synth_bed(out + ".wav", dur, spec.get("seed", 1), [0.4, 0.9, 5.2, 5.6, 6.4, 11.0])
    for fr in range(int(dur * FPS)):
        t = fr / FPS
        z = lerp(1.0, 1.12, t / dur); fx = f[0] + 0.03 * math.sin(t / dur * math.pi); fy = f[1]
        paint(c, crop(im, (fx, fy), W, H, z))
        c.set_source_rgba(0, 0, 0, 0.18); c.paint()
        if t < 5.2:          # beat 1: the meme format
            box(c, spec["top"], W / 2, 470, 66, (t - 0.4) / 0.25, bg=INK, fg=GOLDC, ang=-0.02)
            if spec.get("line1"): para(c, spec["line1"], W / 2, 660, 64, 900, alpha=ease((t - 0.9) / 0.3), stroke=12)
            if spec.get("line2") and t > 2.4: box(c, spec["line2"], W / 2, 1060, 80, (t - 2.4) / 0.25, bg=RED, fg=CREAM, ang=0.02)
        elif t < 11.0:       # beat 2: the real fact
            box(c, "REAL FACT", W / 2, 470, 56, (t - 5.2) / 0.25, bg=TEAL, fg=INK)
            box(c, spec["fact"], W / 2, 760, 104, (t - 5.6) / 0.25, bg=CREAM, fg=INK)
            if spec.get("fact_sub"): para(c, spec["fact_sub"], W / 2, 960, 56, 880, alpha=ease((t - 6.4) / 0.3), stroke=12)
        else:                # beat 3: teaser to the main video
            box(c, spec.get("cta", "FULL VIDEO ON OUR PAGE"), W / 2, 760, 70, (t - 11.0) / 0.25, bg=GOLDC, fg=INK)
            mini_globe(c, W / 2, 1060, max(2, 90 * ease((t - 11.3) / 0.4)), t)
            handle(c, W / 2, 1250, 46, alpha=ease((t - 11.6) / 0.3))
        if spec.get("credit"): text(c, spec["credit"], W / 2, 1530, 26, col=(1, 1, 1), stroke=6, alpha=0.85)
        p.stdin.write(surf.get_data())
    p.stdin.close(); p.wait(); os.remove(out + ".wav"); print(out)


def synth_bed(path, dur, seed, pops):
    """original synth: warm plucked arpeggio + soft kick + pops on the card hits (no samples)"""
    import soundfile as sf
    SR = 44100; N = int(dur * SR); t = np.arange(N) / SR; x = np.zeros(N); r = np.random.default_rng(seed)
    root = 220 * 2 ** (int(r.integers(-3, 4)) / 12); bpm = 100 + int(r.integers(-8, 12)); beat = 60 / bpm
    prog = [[0, 4, 7, 12], [5, 9, 12, 17], [7, 11, 14, 19], [0, 4, 7, 12]]
    for k in range(int(dur / (beat / 2))):
        ch = prog[(k // 8) % 4]; n = ch[[0, 1, 2, 3, 2, 1][k % 6]]; s0 = int(k * beat / 2 * SR); L = min(N - s0, int(0.5 * SR))
        if L <= 0: break
        tt = np.arange(L) / SR; f = root * 2 ** (n / 12)
        x[s0:s0 + L] += 0.12 * np.exp(-tt * 5) * (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(4 * np.pi * f * tt))
        if k % 2 == 0:
            Lb = min(N - s0, int(0.2 * SR)); tb = np.arange(Lb) / SR
            x[s0:s0 + Lb] += 0.3 * np.exp(-tb * 22) * np.sin(2 * np.pi * (50 + 80 * np.exp(-tb * 40)) * tb)
    for at in pops:
        s0 = int(at * SR); L = min(N - s0, int(0.12 * SR)); tt = np.arange(L) / SR
        x[s0:s0 + L] += 0.25 * np.exp(-tt * 40) * np.sin(2 * np.pi * (600 + 900 * tt) * tt)
    x *= np.clip(t / 0.05, 0, 1) * np.clip((dur - t) / 0.8, 0, 1); x /= np.max(np.abs(x)) + 1e-9; x *= 0.8
    sf.write(path, np.stack([x, x], 1), SR)


# ---------------- still cards ----------------
def card_img(spec, W, H, photo=None, focus=None):
    im, f = load(photo or spec["photo"], W, H, tuple(focus or spec.get("focus", (0.5, 0.5))))
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H); c = cairo.Context(surf)
    paint(c, crop(im, f, W, H, 1.0))
    g = cairo.LinearGradient(0, 0, 0, H); g.add_color_stop_rgba(0, 0, 0, 0, 0.45); g.add_color_stop_rgba(0.45, 0, 0, 0, 0.05)
    g.add_color_stop_rgba(0.7, 0, 0, 0, 0.15); g.add_color_stop_rgba(1, 0, 0, 0, 0.6); c.set_source(g); c.paint()
    return surf, c


def card(spec, out, W=1080, H=1350):
    surf, c = card_img(spec, W, H)
    top = 120 if H < 1500 else 300
    box(c, spec["kicker"], W / 2, top + 40, 54, 1, bg=GOLDC, fg=INK, ang=-0.015)
    y = para(c, spec["headline"], W / 2, top + 190, 78, W - 140, stroke=14)
    if spec.get("answer"): box(c, spec["answer"], W / 2, H - (300 if H < 1500 else 560), 72, 1, bg=RED, fg=CREAM, ang=0.02)
    handle(c, W / 2, H - (90 if H < 1500 else 420), 34)
    if spec.get("credit"): text(c, spec["credit"], W / 2, H - (36 if H < 1500 else 370), 22, col=(1, 1, 1), stroke=5, alpha=0.85)
    save(surf, out)


def save(surf, out):
    surf.write_to_png(out + ".png"); Image.open(out + ".png").convert("RGB").save(out, quality=92); os.remove(out + ".png"); print(out)


def slides(spec, prefix):
    outs = []
    for W, H, tag in ((1080, 1350, "ig"), (1080, 1920, "tt")):
        n = len(spec["slides"])
        for i, s in enumerate(spec["slides"]):
            surf, c = card_img(spec, W, H, s.get("photo"), s.get("focus"))
            top = 140 if tag == "ig" else 330
            box(c, s["kicker"], W / 2, top, 50, 1, bg=GOLDC, fg=INK)
            y = para(c, s["headline"], W / 2, top + 170, 84 if i == 0 else 92, W - 140, stroke=14, col=CREAM if i else (1, 1, 1))
            if s.get("body"): para(c, s["body"], W / 2, y + 40, 50, W - 160, stroke=10)
            text(c, f"{i + 1}/{n}", W - 90, H - (70 if tag == "ig" else 420), 34, col=(1, 1, 1), stroke=8)
            handle(c, W / 2, H - (70 if tag == "ig" else 420), 32)
            if spec.get("credit") and i == n - 1: text(c, spec["credit"], W / 2, H - (26 if tag == "ig" else 375), 20, col=(1, 1, 1), stroke=5, alpha=0.85)
            o = f"{prefix}-{tag}-{i + 1}.jpg"; save(surf, o); outs.append(o)
    return outs


if __name__ == "__main__":
    cmd, sp, out = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3]
    {"story": story, "card": card, "slides": slides}[cmd](sp, out)
