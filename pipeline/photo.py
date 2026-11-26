"""Real-photo helpers shared by renders (moved out of render_002b.py on 2026-11-21):
Photo(path, archival=False, maxz=1.35).kb(k, z0, z1, f0, f1) -> Ken Burns HxWx3 float;
finish(a, t, archival, heat, xray, vign) -> graded uint8; to_ctx(c, a) paints it; blur(a, r) soft background."""
import numpy as np, cairo
from PIL import Image, ImageFilter
from engine import *


# ---------------- photos ----------------
LUT_THERM = (np.array([thermal_rgb(i / 255) for i in range(256)]) * 255).astype(np.float32)
_rng = np.random.default_rng(7)
GRAIN = [(_rng.standard_normal((H // 2, W // 2)) * 6).astype(np.float32) for _ in range(3)]


class Photo:
    def __init__(self, path, archival=False, maxz=1.35):
        im = Image.open(path).convert("RGB")
        r = max(W * maxz / im.width, H * maxz / im.height)
        self.im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
        self.maxz = maxz; self.archival = archival

    def kb(self, k, z0=1.0, z1=1.15, f0=(0.5, 0.5), f1=(0.5, 0.5)):
        """Ken Burns: k 0..1 -> numpy HxWx3 float"""
        e = ease(k); z = lerp(z0, z1, e); fx = lerp(f0[0], f1[0], e); fy = lerp(f0[1], f1[1], e)
        cw = W * self.maxz / z; ch = H * self.maxz / z
        cx = min(max(fx * self.im.width, cw / 2), self.im.width - cw / 2)
        cy = min(max(fy * self.im.height, ch / 2), self.im.height - ch / 2)
        a = np.asarray(self.im.resize((W, H), Image.BILINEAR, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)), np.float32)
        if self.archival:  # warm sepia + film grain + vignette ("1930s photo" look)
            l = a.mean(2, keepdims=True)
            a = l * np.array([1.08, 0.96, 0.78]) + 8
        return a


def finish(a, t, archival=False, heat=0.0, xray=0.0, vign=0.35, night=0.0):
    if night > 0:  # day -> moonlit night grade (added 2026-11-23, video 005): darker, blue, highlights kept
        l = a.mean(2, keepdims=True)
        nt = 0.55 * l * np.array([0.55, 0.72, 1.15]) + 0.35 * (l / 255) ** 2 * 255 * np.array([0.8, 0.9, 1.0]) + np.array([6, 10, 28])
        a = a * (1 - night) + nt * night
    if heat > 0:
        l = a.mean(2).clip(0, 255).astype(np.uint8)
        th = LUT_THERM[np.clip(l.astype(np.int32) + 40, 0, 255)]
        a = a * (1 - heat * 0.8) + th * heat * 0.8
    if xray > 0:
        l = a.mean(2, keepdims=True)
        a = a * (1 - xray) + xray * (np.array([0.25, 0.55, 0.95]) * l + np.array([10, 30, 70]))
    if archival:
        g = GRAIN[int(t * 12) % 3]; a = a + np.kron(g, np.ones((2, 2)))[..., None]
    if vign:
        yy = np.linspace(-1, 1, H)[:, None]; xx = np.linspace(-1, 1, W)[None, :]
        a = a * (1 - vign * 0.5 * (xx ** 2 + 0.6 * yy ** 2))[..., None]
    return np.clip(a, 0, 255).astype(np.uint8)


def to_ctx(c, a):
    s = to_surface(a.astype(np.float32) / 255); c.set_source_surface(s, 0, 0); c.paint()



def blur(a, r=12, dim=0.7):
    return (np.asarray(Image.fromarray(a).filter(ImageFilter.GaussianBlur(r)), np.float32) * dim).astype(np.uint8)


# ---------------- edge haze (added 2026-11-22, video 004) ----------------
# Flat skies, grey water and blurred backgrounds failed the Facebook edge-band check (std < 6 in the outer strips).
# haze() adds soft drifting cloud/mist (low-frequency fbm) that is strongest near the frame edges and fades to zero in
# the centre, so the subject is untouched and the edges get natural texture (looks like atmosphere, not a border).
_HZ = {}


def haze(a, t, amt=24.0, drift=(14, -6)):
    if "n" not in _HZ:
        n = fbm(H + 400, W + 400, octaves=5, seed=11, base=3)
        _HZ["n"] = (n - n.mean()) / (n.std() + 1e-6)
        yy = np.linspace(-1, 1, H)[:, None]; xx = np.linspace(-1, 1, W)[None, :]
        d = np.minimum(np.minimum(1 - abs(xx), 1 - abs(yy)) * np.array([[1.0]]), 1)
        e = np.minimum((1 - abs(xx)) * W, (1 - abs(yy)) * H) / 2          # px distance to nearest edge
        _HZ["m"] = np.clip(1 - e / 420, 0, 1) ** 1.3
    ox = int(200 + 180 * math.sin(t * drift[0] / 180)); oy = int(200 + 180 * math.sin(t * drift[1] / 180 + 1))
    n = _HZ["n"][oy:oy + H, ox:ox + W]
    lift = (n * amt + abs(n) * amt * 0.6) * _HZ["m"]
    return np.clip(a.astype(np.float32) + lift[..., None] * np.array([0.95, 1.0, 1.05]), 0, 255)
