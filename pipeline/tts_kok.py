"""Free kokoro voice with caption-word timings (Orbit Gossip sample, no ElevenLabs credits).
Each line is synthesised sentence by sentence, so every sentence's start/end on the timeline is exact; caption words
inside a sentence get times proportional to their spoken length. Writes l{i}.wav + meta.json (with "words").
usage (in work dir): python tts_kok.py script.json"""
import json, re, sys, os, subprocess, tempfile
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
PRESETS = {"neutral": (1.0, 0.0), "excited": (1.08, 0.8), "surprised": (1.06, 1.6), "curious": (1.02, 0.7),
           "playful": (1.05, 0.5), "urgent": (1.06, 0.4), "serious": (0.95, -0.6)}
k = Kokoro("/home/claude/models/kokoro.onnx", "/home/claude/models/voices.bin")
S = json.load(open(sys.argv[1])); V = S["voices"]; GAP = 0.09; TAIL = 0.14


def split(s):
    return [p for p in re.split(r"(?<=[.!?])\s+", s.strip()) if p]


def pitch(a, sr, p):
    if abs(p) < 0.05: return a
    r = 2 ** (p / 12)
    with tempfile.TemporaryDirectory() as d:
        sf.write(f"{d}/i.wav", a, sr)
        subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", f"{d}/i.wav", "-af",
                               f"asetrate={int(sr * r)},aresample={sr},atempo={1 / r:.5f}", f"{d}/o.wav"])
        return sf.read(f"{d}/o.wav")[0]


def trim(a):
    nz = np.where(np.abs(a) > 0.012)[0]
    return a[max(0, nz[0] - 150): nz[-1] + 900] if len(nz) else a


meta = []
for i, (spoken, cap, spk, emo) in enumerate(S["lines"]):
    sp, pt = PRESETS[emo]; v = V[spk]
    ss, cs = split(spoken), split(cap)
    assert len(ss) == len(cs), (i, ss, cs)
    parts, words, t = [], [], 0.0
    for s_sp, s_cap in zip(ss, cs):
        a, sr = k.create(s_sp, voice=v["voice"], speed=v["speed"] * sp, lang="en-us")
        a = trim(pitch(a, sr, pt)); d = len(a) / sr
        cw = s_cap.split(); wl = [len(re.sub(r"[^A-Za-z0-9]", "", w)) + 2 for w in cw]; tot = sum(wl); x = t
        for w, l in zip(cw, wl):
            words.append([w, round(x, 3), round(x + d * l / tot, 3)]); x += d * l / tot
        parts += [a, np.zeros(int(GAP * sr))]; t += d + GAP
    a = np.concatenate(parts[:-1] + [np.zeros(int(TAIL * sr))])
    sf.write(f"l{i}.wav", a, sr)
    meta.append({"text": spoken, "cap": cap, "dur": len(a) / sr, "speaker": spk, "emotion": emo, "words": words})
json.dump(meta, open("meta.json", "w"), indent=1)
print(round(sum(m["dur"] for m in meta), 2), [round(m["dur"], 2) for m in meta])
