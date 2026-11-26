"""Real video footage in renders (added 2026-11-21 for video 003).
Extract a segment of a free-licence clip (e.g. a Wikimedia Commons .webm) into 1080x1920 JPEG frames at 30 fps,
cropped (to keep people / phones / logos out of frame) and colour-graded, then read frames by time in a render.
  from clips import extract, Clip
  extract("media/x.webm", start=34, dur=3, out="clipA", crop=(x, y, w, h))   # crop in source pixels, ~9:16
  A = Clip("clipA"); rgb = A.at(t, speed=1.0)  -> HxWx3 uint8 (holds last frame past the end)
Commons serves big originals with 429s: download the transcoded 1080p tier instead:
  https://upload.wikimedia.org/wikipedia/commons/transcoded/<a>/<ab>/<File>.webm/<File>.webm.1080p.vp9.webm
"""
import os, glob, subprocess, numpy as np
from PIL import Image

W, H, FPS = 1080, 1920, 30


def extract(src, start, dur, out, crop=None, grade="eq=contrast=1.08:saturation=1.25:gamma=0.97"):
    if os.path.isdir(out) and len(glob.glob(f"{out}/*.jpg")) >= int(dur * FPS) - 1: return out
    os.makedirs(out, exist_ok=True)
    vf = []
    if crop: vf.append("crop=%d:%d:%d:%d" % (crop[2], crop[3], crop[0], crop[1]))
    vf += [f"scale={W}:{H}:flags=lanczos", "unsharp=5:5:0.6", grade, f"fps={FPS}"]
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(dur), "-i", src, "-vf", ",".join(vf),
                           "-q:v", "2", f"{out}/f%04d.jpg"])
    return out


class Clip:
    def __init__(self, d):
        self.files = sorted(glob.glob(f"{d}/*.jpg")); self.cache = {}

    def at(self, t, speed=1.0):
        i = min(len(self.files) - 1, max(0, int(t * speed * FPS)))
        if i not in self.cache:
            if len(self.cache) > 8: self.cache.clear()
            self.cache[i] = np.asarray(Image.open(self.files[i]).convert("RGB"))
        return self.cache[i]
