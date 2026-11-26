"""Globe -> location zoom (Bidhan 2026-11-20: show WHERE it is, zooming in from Earth).
Orthographic globe rendered with numpy from a public-domain NASA Blue Marble texture
(Wikimedia Commons "Whole world - land and oceans 12000.jpg", NASA/GSFC, public domain).
Get the texture once per run:  python globe.py fetch   (saves /home/claude/media/earth.jpg)
In a render:  from globe import Globe; g = Globe(); rgb = g.frame(t_norm, lat, lon)  -> HxWx3 uint8
"""
import os, sys, math, subprocess, numpy as np
from PIL import Image, ImageFilter

W, H = 1080, 1920
EARTH = "/home/claude/media/earth.jpg"
UA = "HowOnEarthBot/1.0 (https://github.com/beedangsb123/how-on-earth-videos)"
URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Whole_world_-_land_and_oceans_12000.jpg/3840px-Whole_world_-_land_and_oceans_12000.jpg"


def fetch():
    os.makedirs(os.path.dirname(EARTH), exist_ok=True)
    if not os.path.exists(EARTH):
        subprocess.check_call(["curl", "-sf", "-A", UA, "-o", EARTH, URL])
    return EARTH


def _space(seed=3):
    """deep-blue nebula + stars (NOT flat black: passes the edge-band check)"""
    rng = np.random.default_rng(seed)
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
    neb = np.zeros((H, W), np.float32); amp = 1.0
    for n in (3, 6, 12, 24):
        small = rng.random((n * 2, n)).astype(np.float32)
        neb += amp * np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(H / n / 3)), np.float32) / 255
        amp *= 0.5
    neb = (neb - neb.min()) / (neb.max() - neb.min())
    base = np.stack([0.05 + 0.10 * neb + 0.05 * y, 0.08 + 0.12 * neb, 0.22 + 0.25 * neb + 0.1 * (1 - y)], -1) * np.ones((H, W, 1))
    base += 0.08 * np.stack([neb * x, 0 * neb, neb * (1 - x)], -1)
    stars = rng.random((H, W)) > 0.9975
    base[stars] = rng.uniform(0.6, 1, (stars.sum(), 1))
    return (np.clip(base, 0, 1) * 255).astype(np.uint8)


class Globe:
    def __init__(self, path=EARTH, tex_w=3840):
        im = Image.open(path).convert("RGB")
        if im.width != tex_w: im = im.resize((tex_w, tex_w // 2), Image.BICUBIC)
        t = np.asarray(im).astype(np.float32); self.th, self.tw = t.shape[:2]
        # lift the very dark Blue Marble ocean (smooth noise, done once) so zoomed views have no flat dark bands
        rng = np.random.default_rng(1); n = np.zeros((self.th, self.tw), np.float32)
        for c, a in ((16, 1.0), (64, 0.5), (256, 0.25)):
            sm = Image.fromarray((rng.random((c // 2, c)) * 255).astype(np.uint8)).resize((self.tw, self.th), Image.BICUBIC)
            n += a * np.asarray(sm, np.float32) / 255
        n /= 1.75
        ocean = np.clip((70 - t.mean(2, keepdims=True)) / 70, 0, 1)
        t = t + ocean * np.array([20, 62, 112]) * (0.75 + 0.5 * n[..., None])
        self.tex = np.clip(t, 0, 255).astype(np.uint8)
        self.space = _space()
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xx = xx - W / 2; self.yy = yy - H * 0.47

    def render(self, lat0, lon0, R, glow=True):
        """orthographic view centred on (lat0, lon0) with globe radius R px"""
        x = self.xx / R; y = -self.yy / R
        rho2 = x * x + y * y; inside = rho2 <= 1.0
        out = self.space.copy()
        if inside.any():
            xi, yi = x[inside], y[inside]; z = np.sqrt(np.clip(1 - xi * xi - yi * yi, 0, 1))
            p0, l0 = math.radians(lat0), math.radians(lon0)
            lat = np.arcsin(np.clip(z * math.sin(p0) + yi * math.cos(p0), -1, 1))
            lon = l0 + np.arctan2(xi, z * math.cos(p0) - yi * math.sin(p0))
            u = ((lon / (2 * math.pi) + 0.5) % 1.0) * (self.tw - 1)
            v = (0.5 - lat / math.pi) * (self.th - 1)
            # bilinear sampling (no blocky pixels when zoomed)
            u0 = np.floor(u).astype(np.int32); v0 = np.floor(v).astype(np.int32).clip(0, self.th - 2)
            fu = (u - u0)[:, None]; fv = (v - v0)[:, None]; u1 = (u0 + 1) % self.tw
            T = self.tex
            col = ((T[v0, u0] * (1 - fu) + T[v0, u1] * fu) * (1 - fv) + (T[v0 + 1, u0] * (1 - fu) + T[v0 + 1, u1] * fu) * fv).astype(np.float32)
            shade = (0.55 + 0.45 * z)[:, None]           # limb darkening
            col = col * shade * 1.15 + np.array([20, 35, 60]) * (1 - z[:, None]) ** 3  # bluish limb haze
            out[inside] = np.clip(col, 0, 255).astype(np.uint8)
        if glow and R < 3000:
            rho = np.sqrt(rho2); ring = np.exp(-((rho - 1.0) * R / 28.0) ** 2) * (rho > 0.98)
            out = np.clip(out + ring[..., None] * np.array([90, 160, 255]) * 0.8, 0, 255).astype(np.uint8)
        return out

    def frame(self, k, lat, lon, lon_start=None, R0=430, R1=2400):
        """k in 0..1: spin from lon_start to target while zooming R0 -> R1 (exponential)"""
        if lon_start is None: lon_start = lon + 70
        s = k * k * (3 - 2 * k)
        spin = min(1.0, s / 0.55)
        lo = lon_start + (lon - lon_start) * (spin * spin * (3 - 2 * spin))
        la = lat * spin + 10 * (1 - spin)
        zk = max(0.0, (s - 0.25) / 0.75)
        R = R0 * (R1 / R0) ** (zk ** 1.6)
        return self.render(la, lo, R), R


def handoff(globe_rgb, photo_rgb, k, cy=None):
    """k 0..1: circular 'zoom-through' reveal of a real photo from the location point (centre of the globe view),
    photo eases from 1.25x to 1.0x so the motion continues the zoom. Soft edge + gold ring."""
    k = max(0.0, min(1.0, k)); e = k * k * (3 - 2 * k)
    cy = H * 0.47 if cy is None else cy
    sc = 1.25 - 0.25 * e
    ph = Image.fromarray(photo_rgb).resize((int(W * sc), int(H * sc)), Image.BICUBIC)
    ph = np.asarray(ph)[(ph.height - H) // 2:(ph.height - H) // 2 + H, (ph.width - W) // 2:(ph.width - W) // 2 + W]
    r = 20 + e * math.hypot(W, H)
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt((xx - W / 2) ** 2 + (yy - cy) ** 2)
    m = np.clip((r - d) / 40.0, 0, 1)[..., None]
    out = globe_rgb * (1 - m) + ph * m
    ring = np.exp(-((d - r) / 6.0) ** 2)[..., None] * (1 - e)
    out = out + ring * np.array([255, 200, 87]) * 0.9
    return np.clip(out, 0, 255).astype(np.uint8)


def cover(img, w=W, h=H):
    """resize+crop a PIL image to fully cover w x h (no borders)"""
    r = max(w / img.width, h / img.height)
    im = img.resize((int(img.width * r + 1), int(img.height * r + 1)), Image.LANCZOS)
    x = (im.width - w) // 2; y = (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


if __name__ == "__main__":
    if sys.argv[1] == "fetch":
        print(fetch())
    elif sys.argv[1] == "test":  # python globe.py test lat lon out_prefix
        g = Globe(); lat, lon = float(sys.argv[2]), float(sys.argv[3])
        for k in (0.0, 0.3, 0.55, 0.75, 0.9, 1.0):
            a, R = g.frame(k, lat, lon); Image.fromarray(a).save(f"{sys.argv[4]}_{k}.png"); print(k, int(R))
