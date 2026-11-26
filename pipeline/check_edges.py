"""Edge-band check (PLAYBOOK 'Platform flags to avoid'): samples frames every 2 s plus first/last,
measures mean/std of top 150 px, bottom 150 px, left/right 60 px strips. FAIL if std<6 or mean<25.
usage: python check_edges.py video.mp4"""
import subprocess, sys, json, numpy as np
f = sys.argv[1]
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]))
times = [0.0] + list(np.arange(2, dur - 0.1, 2.0)) + [dur - 0.15]
bad = 0
for t in times:
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", f, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"])
    a = np.frombuffer(raw, np.uint8).reshape(1920, 1080).astype(float)
    strips = {"top": a[:150], "bottom": a[-150:], "left": a[:, :60], "right": a[:, -60:]}
    res = {k: (round(v.mean(), 1), round(v.std(), 1)) for k, v in strips.items()}
    fail = [k for k, (m, s) in res.items() if s < 6 or m < 25]
    if fail: bad += 1
    print(f"{t:6.2f}s", res, "FAIL " + ",".join(fail) if fail else "ok")
print("RESULT:", "FAIL" if bad else "PASS", f"({bad} bad frames of {len(times)})")
