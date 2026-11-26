"""Voice generator v3: reads script.json {voice, speed, lines:[[spoken, caption, speaker, emotion?], ...]}.
Two-voice conversational mode (Bidhan 2026-11-21): "voices": {"M": {"voice": "am_michael", "speed": 1.08},
"F": {"voice": "af_heart", "speed": 1.1}} and each line's 3rd element "M" or "F" (the speaker).
EMOTION (Bidhan 2026-11-21: "not a neutral tone — show some emotions"): optional 4th element, a preset name or a dict
{"speed": x, "pitch": semitones, "gain": x}. Presets below shift tempo and pitch per line (ffmpeg asetrate+atempo),
so reactions sound excited/surprised and big reveals sound awed instead of a flat read.
Writes l{i}.wav + meta.json with per-line duration, caption text (CAPS words = gold highlight), speaker, emotion."""
import json, sys, os, subprocess, tempfile, soundfile as sf, numpy as np
from kokoro_onnx import Kokoro
PRESETS = {
    "neutral":   {"speed": 1.00, "pitch": 0.0, "gain": 1.00},
    "excited":   {"speed": 1.10, "pitch": 1.0, "gain": 1.10},
    "surprised": {"speed": 1.08, "pitch": 1.8, "gain": 1.12},   # "Wait — WHAT?!"
    "awe":       {"speed": 0.92, "pitch": -0.6, "gain": 1.00},  # slow, low: the big reveal
    "curious":   {"speed": 1.02, "pitch": 0.8, "gain": 1.00},   # questions
    "playful":   {"speed": 1.06, "pitch": 0.6, "gain": 1.05},
    "urgent":    {"speed": 1.14, "pitch": 0.5, "gain": 1.12},   # the hook
    "serious":   {"speed": 0.96, "pitch": -0.4, "gain": 1.00},
}
k = Kokoro("/home/claude/models/kokoro.onnx", "/home/claude/models/voices.bin")
S = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "script.json"))
meta = []
V = S.get("voices", {})


def shape(a, sr, e):
    """pitch-shift by e['pitch'] semitones keeping duration (asetrate+atempo), then gain"""
    p = e.get("pitch", 0.0)
    if abs(p) > 0.05:
        r = 2 ** (p / 12)
        with tempfile.TemporaryDirectory() as d:
            sf.write(f"{d}/i.wav", a, sr)
            subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", f"{d}/i.wav", "-af",
                                   f"asetrate={int(sr * r)},aresample={sr},atempo={1 / r:.5f}", f"{d}/o.wav"])
            a, _ = sf.read(f"{d}/o.wav")
    return np.clip(a * e.get("gain", 1.0), -1, 1)


for i, line in enumerate(S["lines"]):
    spoken, cap = line[0], line[1]; spk = line[2] if len(line) > 2 else None
    emo = line[3] if len(line) > 3 else "neutral"
    e = PRESETS.get(emo, PRESETS["neutral"]) if isinstance(emo, str) else {**PRESETS["neutral"], **emo}
    v = V.get(spk, {}) if spk else {}
    sp = v.get("speed", S.get("speed", 1.0)) * e.get("speed", 1.0)
    a, sr = k.create(spoken, voice=v.get("voice", S.get("voice")), speed=sp, lang="en-us")
    a = shape(a, sr, e)
    # trim leading/trailing silence so the hook starts at 0.0 s
    nz = np.where(np.abs(a) > 0.01)[0]
    if len(nz): a = a[max(0, nz[0] - 200): nz[-1] + 2000]
    sf.write(f"l{i}.wav", a, sr)
    meta.append({"text": spoken, "cap": cap, "dur": len(a) / sr, "sr": sr, "speaker": spk, "emotion": emo if isinstance(emo, str) else "custom"})
json.dump(meta, open("meta.json", "w"), indent=1)
print(round(sum(m["dur"] for m in meta), 2), [round(m["dur"], 2) for m in meta])
