"""Audio v2: voice lines placed on the timeline + original synth music (driving pulse, ducked
under the voice) + synthesised SFX (whoosh, boom, tick, thunk, crack, pop, drill).
usage (in work dir with meta.json, l*.wav, events.json): python audio2.py [pad] [transpose] [bpm]  -> mix.wav
Rotate transpose (semitones from A minor) and bpm every video (anti-slop rule). 003: +5 (D minor), 92 bpm.
SFX kinds: scratch trombone (meme beats, 2026-11-25) clank ding whoosh boom tick thunk crack pop drill hiss (steam roar) bubble (rising blips) splash roar (deep waterfall rumble)."""
import json, sys, numpy as np, soundfile as sf
SR = 44100
PAD = float(sys.argv[1]) if len(sys.argv) > 1 else 0.25
TR = int(sys.argv[2]) if len(sys.argv) > 2 else 0
BPM = float(sys.argv[3]) if len(sys.argv) > 3 else 100
meta = json.load(open("meta.json")); ev = json.load(open("events.json"))
T = ev["total"]; N = int(T * SR) + SR
t = np.arange(N) / SR
rng = np.random.default_rng(4)

# ---- voice ----
voice = np.zeros(N); pos = float(ev.get("voice_offset", 0.0))   # e.g. a news ident before the first line
for i, m in enumerate(meta):
    a, sr = sf.read(f"l{i}.wav")
    if a.ndim > 1: a = a.mean(1)
    if sr != SR: a = np.interp(np.arange(int(len(a) * SR / sr)) * sr / SR, np.arange(len(a)), a)
    s = int(pos * SR); voice[s:s + len(a)] += a[:N - s]; pos += m["dur"] + PAD
voice = voice / (np.max(np.abs(voice)) + 1e-9) * 0.92

# ---- music: A minor driving pulse, 100 bpm ----
def hz(n): return 440 * 2 ** ((n + TR - 69) / 12)
beat = 60.0 / BPM; music = np.zeros(N)
prog = [[45, 52, 57, 60, 64], [41, 48, 53, 57, 60], [48, 55, 60, 64, 67], [43, 50, 55, 59, 62]]
bar = beat * 4
for b in range(int(T / bar) + 1):
    ch = prog[b % 4]; s = int(b * bar * SR); e = min(N, int((b + 1) * bar * SR + 0.5 * SR))
    tt = t[s:e] - b * bar; env = np.clip(tt / 0.4, 0, 1) * np.clip((bar + 0.5 - tt) / 0.6, 0, 1)
    for n in ch[1:]:
        f = hz(n); music[s:e] += 0.10 * env * (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * f * 1.004 * tt))
    for k in range(8):  # eighth-note bass pulse
        s2 = int((b * bar + k * beat / 2) * SR); e2 = min(N, s2 + int(0.28 * SR)); t2 = t[s2:e2] - (b * bar + k * beat / 2)
        music[s2:e2] += 0.32 * np.exp(-t2 * 9) * np.sin(2 * np.pi * hz(ch[0] - 12) * t2)
    for k in range(16):  # sixteenth arpeggio
        s2 = int((b * bar + k * beat / 4) * SR); e2 = min(N, s2 + int(0.14 * SR)); t2 = t[s2:e2] - (b * bar + k * beat / 4)
        n = ch[[1, 2, 3, 4, 3, 2][k % 6]] + 12
        music[s2:e2] += 0.05 * np.exp(-t2 * 22) * np.sin(2 * np.pi * hz(n) * t2)  # sine, not square (less harsh)
    for k in range(4):  # kick on beats
        s2 = int((b * bar + k * beat) * SR); e2 = min(N, s2 + int(0.2 * SR)); t2 = t[s2:e2] - (b * bar + k * beat)
        music[s2:e2] += 0.45 * np.exp(-t2 * 25) * np.sin(2 * np.pi * (50 + 90 * np.exp(-t2 * 40)) * t2)
# ---- regional / occasion music styles (added 2026-11-23, Bidhan: "if it's India give Indian music, the Taj Mahal can
# evoke Central Asian Sufi music, Egypt can give Arabic music"). All ORIGINAL numpy synthesis, inspired by the scale/
# rhythm conventions only (no melodies copied). Choose with events.json "music_style": default | news | sufi | arabic |
# festive | latin | eastasia | swing | americana. TR (transpose) and BPM still apply.
STYLE = ev.get("music_style", "default")
_rng2 = np.random.default_rng(11)
def _pluck(f, d, a, decay=4.0, harm=(1, 0.5, 0.33, 0.2)):
    tt = L(d); return a * np.exp(-tt * decay) * sum(h * np.sin(2 * np.pi * f * (i + 1) * tt) for i, h in enumerate(harm))
def _drum(f, d, a, bend=1.6, decay=18):
    tt = L(d); return a * np.exp(-tt * decay) * np.sin(2 * np.pi * f * (1 + bend * np.exp(-tt * 30)) * tt)
def _put(buf, at, x):
    s0 = int(at * SR); e = min(N, s0 + len(x))
    if 0 <= s0 < N: buf[s0:e] += x[:e - s0]
def L(d): return np.arange(int(d * SR)) / SR
if STYLE != "default":
    music = np.zeros(N); root = hz(50)   # D3 + TR
    if STYLE == "sufi":       # tanpura-like drone (Sa-Pa-Sa), harmonium-ish raga phrases (Bhairav-type scale), tabla-like dha/tin
        dr = sum(a_ * np.sin(2 * np.pi * root * m * t * (1 + 0.0007 * np.sin(t * 0.7 * m))) for m, a_ in ((1, .25), (1.5, .15), (2, .18), (3, .06), (4, .04)))
        music += dr * (0.75 + 0.25 * np.sin(2 * np.pi * t / (beat * 4)) ** 2)
        scale = [0, 1, 4, 5, 7, 8, 11, 12]; note = 4
        for k in range(int(T / beat)):
            if _rng2.random() < 0.55:
                note = int(np.clip(note + _rng2.choice([-2, -1, 1, 2]), 0, 7))
                _put(music, k * beat, _pluck(root * 2 * 2 ** (scale[note] / 12), beat * 1.6, 0.10, decay=1.6, harm=(1, .6, .4, .25, .15)))
            for j, (f, a_) in enumerate(((root * 0.75, .35), (root * 2.4, .12), (root * 2.4, .1), (root * 0.75, .3))):
                if (k + j) % 2 == 0: _put(music, k * beat + j * beat / 4, _drum(f, 0.25, a_, bend=0.4 if f < root else 0.05, decay=12 if f < root else 30))
    elif STYLE == "arabic":   # maqam Hijaz phrases on an oud-like pluck, drone, darbuka maqsum (D-T-.-T-D-.-T-.)
        music += 0.18 * (np.sin(2 * np.pi * root / 2 * t) + 0.5 * np.sin(2 * np.pi * root * 0.75 * t))
        hij = [0, 1, 4, 5, 7, 8, 10, 12]; note = 3
        for k in range(int(T / (beat / 2))):
            if _rng2.random() < 0.6:
                note = int(np.clip(note + _rng2.choice([-1, 1, 1, -2, 2]), 0, 7))
                _put(music, k * beat / 2, _pluck(root * 2 * 2 ** (hij[note] / 12), 0.6, 0.12, decay=5, harm=(1, .7, .45, .3, .2, .1)))
        pat = "DT.TD.T."
        for k in range(int(T / (beat / 2))):
            c_ = pat[k % 8]
            if c_ == "D": _put(music, k * beat / 2, _drum(70, 0.35, 0.45, bend=0.8, decay=10))
            elif c_ == "T": _put(music, k * beat / 2, _drum(520, 0.08, 0.12, bend=0.1, decay=60))
    elif STYLE == "news":     # steady news-bed: 16th pulse, held string pad, soft timpani each bar
        for b in range(int(T / bar) + 1):
            ch = prog[b % 4]; s0 = int(b * bar * SR); e = min(N, int((b + 1) * bar * SR + 0.3 * SR)); tt = t[s0:e] - b * bar
            env = np.clip(tt / 0.3, 0, 1) * np.clip((bar + 0.3 - tt) / 0.4, 0, 1)
            for n in ch[1:]: music[s0:e] += 0.07 * env * np.sin(2 * np.pi * hz(n) * tt)
            _put(music, b * bar, _drum(hz(ch[0] - 24), 1.0, 0.4, bend=0.3, decay=4))
            for k in range(16): _put(music, b * bar + k * beat / 4, 0.05 * np.exp(-L(0.05) * 70) * np.sin(2 * np.pi * 1100 * L(0.05)))
    elif STYLE == "festive":  # major key, pizzicato bass + soft celesta-like bells (sines, no sleigh-bell noise)
        maj = [[48, 55, 60, 64], [53, 57, 60, 65], [55, 59, 62, 67], [48, 55, 60, 64]]
        for b in range(int(T / bar) + 1):
            ch = maj[b % 4]
            for k in range(4): _put(music, b * bar + k * beat, _pluck(hz(ch[0] - 12), 0.4, 0.3, decay=8))
            for k in range(8): _put(music, b * bar + k * beat / 2, _pluck(hz(ch[1 + (k % 3)] + 12), 0.8, 0.07, decay=4, harm=(1, .1, .05)))
    elif STYLE == "latin":    # tresillo bass + nylon-guitar-ish plucks
        for b in range(int(T / bar) + 1):
            ch = prog[b % 4]
            for k in (0, 1.5, 3): _put(music, b * bar + k * beat, _pluck(hz(ch[0] - 12), 0.5, 0.3, decay=6))
            for k in range(8): _put(music, b * bar + k * beat / 2, _pluck(hz(ch[1 + k % 4]), 0.5, 0.06, decay=6))
    elif STYLE == "swing":    # added 2026-11-24 (video 006, 1930s New York): original swing feel -- walking upright-bass
        # plucks on every beat, soft brushed ride with a swung 8th (2/3 split), muted-piano 6th/9th chord stabs on 2 & 4.
        # No samples, no melody copied; hat is a short high sine burst (not noise) to keep the >4 kHz share low.
        chords = [[45, 52, 57, 60, 66], [50, 57, 62, 65, 71], [43, 50, 55, 59, 64], [48, 55, 60, 64, 69]]
        walk = [0, 3, 5, 7]; sw = beat * 2 / 3
        for b in range(int(T / bar) + 1):
            ch = chords[b % 4]
            for k in range(4):
                _put(music, b * bar + k * beat, _pluck(hz(ch[0] - 12 + walk[k]), beat * 0.95, 0.34, decay=5, harm=(1, .35, .12)))
                for d_, a_ in ((0, 0.05), (sw, 0.03)):
                    _put(music, b * bar + k * beat + d_, a_ * np.exp(-L(0.08) * 45) * np.sin(2 * np.pi * 3100 * L(0.08)) * np.sin(2 * np.pi * 37 * L(0.08)))
                if k in (1, 3):
                    for n in ch[1:]: _put(music, b * bar + k * beat + 0.02, _pluck(hz(n), 0.35, 0.05, decay=11, harm=(1, .3, .1)))
            _put(music, b * bar, _drum(52, 0.25, 0.22, bend=0.6, decay=16))
    elif STYLE == "americana":  # added 2026-11-25 (video 010, South Dakota / Black Hills): original "open road" feel --
        # fingerpicked acoustic-guitar-like travis pattern (alternating bass + treble plucks), soft held fiddle-ish fifths,
        # light brushed kick on 1 & 3. Major key, all numpy synthesis, no melody copied.
        chords = [[43, 55, 59, 62], [48, 55, 60, 64], [50, 57, 62, 66], [43, 55, 59, 62]]
        for b in range(int(T / bar) + 1):
            ch = chords[b % 4]
            for k in range(8):
                bass = ch[0] - 12 + (7 if k % 4 == 2 else 0)
                if k % 2 == 0: _put(music, b * bar + k * beat / 2, _pluck(hz(bass), 0.6, 0.26, decay=6, harm=(1, .45, .2)))
                else: _put(music, b * bar + k * beat / 2, _pluck(hz(ch[1 + (k // 2) % 3]), 0.5, 0.07, decay=7, harm=(1, .5, .3, .15)))
            s0 = int(b * bar * SR); e = min(N, int((b + 1) * bar * SR + 0.3 * SR)); tt = t[s0:e] - b * bar
            env = np.clip(tt / 0.6, 0, 1) * np.clip((bar + 0.3 - tt) / 0.8, 0, 1)
            vib = 1 + 0.003 * np.sin(2 * np.pi * 5.2 * tt)
            for n in (ch[1], ch[1] + 7): music[s0:e] += 0.035 * env * (np.sin(2 * np.pi * hz(n) * vib * tt) + 0.3 * np.sin(4 * np.pi * hz(n) * vib * tt))
            for k in (0, 2): _put(music, b * bar + k * beat, _drum(58, 0.22, 0.2, bend=0.5, decay=18))
    elif STYLE == "eastasia": # pentatonic plucked-zither phrases over a soft pad
        pen = [0, 2, 4, 7, 9, 12, 14]; note = 3
        music += 0.08 * np.sin(2 * np.pi * root * t) * (0.7 + 0.3 * np.sin(t))
        for k in range(int(T / (beat / 2))):
            if _rng2.random() < 0.5:
                note = int(np.clip(note + _rng2.choice([-1, 1, 2, -2]), 0, 6))
                _put(music, k * beat / 2, _pluck(root * 2 * 2 ** (pen[note] / 12), 1.2, 0.1, decay=3))
music /= np.max(np.abs(music)) + 1e-9
# duck under voice
env = np.convolve(np.abs(voice), np.ones(2205) / 2205, mode="same")
duck = 1 - 0.6 * np.clip(env / 0.05, 0, 1)
duck = np.convolve(duck, np.ones(4410) / 4410, mode="same")
music *= 0.32 * duck
music *= np.clip((T - t) / 1.0, 0, 1)

# ---- sfx ----
sfx = np.zeros(N)
def add(at, a):
    s = int(at * SR)
    if s < 0: a = a[-s:]; s = 0
    e = min(N, s + len(a)); sfx[s:e] += a[:e - s]
def lp(x, k):  # crude low-pass
    return np.convolve(x, np.ones(k) / k, mode="same")
L = lambda d: np.arange(int(d * SR)) / SR
# Bidhan 2026-11-21: the "cshhhh cshhhh" noise SFX were irritating -> noise-based SFX are now rare, quiet and dark:
# whooshes at most one per 2.5 s, low-passed and ~1/3 the old level; "hiss" is a soft low rumble, max one per 8 s.
_last = {"whoosh": -9.0, "hiss": -99.0}; _gap = {"whoosh": 2.5, "hiss": 8.0}
for kind, at in sorted(ev["events"], key=lambda e: e[1]):
    if kind in _last:
        if at - _last[kind] < _gap[kind]: continue
        _last[kind] = at
    if kind == "whoosh":
        tt = L(0.5); n = rng.standard_normal(len(tt))
        x = lp(n, 18) - lp(n, 90); add(at - 0.1, 0.12 * x * np.sin(np.pi * tt / 0.5) ** 2)
    elif kind == "boom":
        tt = L(1.4); add(at, 0.9 * np.exp(-tt * 3.5) * np.sin(2 * np.pi * (38 + 60 * np.exp(-tt * 12)) * tt) + 0.1 * lp(rng.standard_normal(len(tt)), 60) * np.exp(-tt * 6))
    elif kind == "tick":
        tt = L(0.03); add(at, 0.18 * np.exp(-tt * 300) * np.sin(2 * np.pi * 2400 * tt))
    elif kind == "thunk":
        tt = L(0.18); add(at, 0.35 * np.exp(-tt * 30) * np.sin(2 * np.pi * (120 + 80 * np.exp(-tt * 50)) * tt) + 0.08 * lp(rng.standard_normal(len(tt)), 8) * np.exp(-tt * 60))
    elif kind == "crack":
        tt = L(0.6); n = rng.standard_normal(len(tt)) * (rng.random(len(tt)) > 0.97)
        add(at, 0.35 * lp(n, 8) * np.exp(-tt * 8))
    elif kind == "pop":
        tt = L(0.12); add(at, 0.25 * np.exp(-tt * 40) * np.sin(2 * np.pi * (600 + 900 * tt) * tt))
    elif kind == "drill":
        tt = L(2.6); add(at, 0.07 * np.sign(np.sin(2 * np.pi * 55 * tt)) * lp(rng.standard_normal(len(tt)), 4) * np.clip(tt / 0.2, 0, 1) * np.clip((2.6 - tt) / 0.3, 0, 1))
    elif kind == "hiss":  # steam roar: band-passed noise swelling over 2.5 s
        tt = L(2.0); n = rng.standard_normal(len(tt)); x = lp(n, 40) - lp(n, 200)
        add(at, 0.07 * x * np.clip(tt / 0.4, 0, 1) * np.clip((2.0 - tt) / 1.0, 0, 1))
    elif kind == "bubble":
        for j in range(7):
            tt = L(0.07); f = 500 + 120 * j + rng.random() * 80
            add(at + j * 0.09, 0.12 * np.exp(-tt * 50) * np.sin(2 * np.pi * (f + 2500 * tt) * tt))
    elif kind == "roar":  # waterfall bed (video 005): deep brown-noise rumble, low-passed twice -> no hiss, 3 s swell
        tt = L(3.0); n = np.cumsum(rng.standard_normal(len(tt))); n -= lp(n, 4000); x = lp(lp(n, 30), 30)
        x /= np.max(np.abs(x)) + 1e-9; add(at, 0.10 * x * np.clip(tt / 0.5, 0, 1) * np.clip((3.0 - tt) / 1.0, 0, 1))
    elif kind == "clank":  # added 2026-11-24 (video 006): steel beam / rivet hit -- inharmonic metal partials, no noise
        tt = L(0.7); add(at, 0.16 * sum(np.exp(-tt * d) * np.sin(2 * np.pi * f * tt) for f, d in ((310, 6), (837, 9), (1490, 14), (2210, 20))))
    elif kind == "ding":   # small bell (counter end / "three minutes")
        tt = L(1.2); add(at, 0.14 * np.exp(-tt * 3.5) * (np.sin(2 * np.pi * 1568 * tt) + 0.4 * np.sin(2 * np.pi * 3920 * tt) * np.exp(-tt * 6)))
    elif kind == "scratch":  # added 2026-11-25: record-scratch meme beat (synth fallback, no samples): pitch zig-zag, low-passed
        tt = L(0.45); f = 300 + 900 * np.abs(np.sin(2 * np.pi * 3.2 * tt)); ph = 2 * np.pi * np.cumsum(f) / SR
        x = np.sign(np.sin(ph)) * 0.5 + np.sin(ph); add(at, 0.09 * lp(x, 6) * np.clip((0.45 - tt) / 0.1, 0, 1))
    elif kind == "trombone":  # "sad trombone" (wah-wah-wah-waaah): four falling brassy notes with a wobble on the last
        for j, (n_, d_) in enumerate(((58, 0.32), (57, 0.32), (56, 0.32), (55, 1.0))):
            tt = L(d_); f = 440 * 2 ** ((n_ - 69) / 12) * (1 + (0.02 * np.sin(2 * np.pi * 6 * tt) if j == 3 else 0))
            ph = 2 * np.pi * np.cumsum(f * np.ones_like(tt)) / SR
            x = sum(np.sin(ph * h) / h ** 1.2 for h in range(1, 6)) * np.clip(tt / 0.04, 0, 1) * np.clip((d_ - tt) / 0.12, 0, 1)
            add(at + j * 0.34, 0.07 * x)
    elif kind == "splash":
        tt = L(0.5); n = rng.standard_normal(len(tt)); add(at, 0.1 * (lp(n, 10) - lp(n, 60)) * np.exp(-tt * 8))
# ---- news ident (added 2026-11-23 for the "How On Earth News" format): original synth sting, NOT a real broadcaster's
# theme. "news_open" = timpani roll + brass-like stabs + rising 16th pulse (~3.2 s); "news_close" = shorter button (~2.4 s).
def brass(f, d, a=0.25):
    tt = L(d); x = sum(np.sin(2 * np.pi * f * h * tt) / h ** 1.3 for h in range(1, 7))     # bright but band-limited
    return a * x * np.clip(tt / 0.02, 0, 1) * np.exp(-tt * 2.2)
def timp(f, d=0.9, a=0.6):
    tt = L(d); return a * np.exp(-tt * 4) * np.sin(2 * np.pi * (f + 30 * np.exp(-tt * 20)) * tt)
news = np.zeros(N)
def addn(at, x):
    s0 = int(at * SR); e = min(N, s0 + len(x))
    if 0 <= s0 < N: news[s0:e] += x[:e - s0]
for kind, at in ev["events"]:
    if kind == "news_open":
        for k in range(10): addn(at + k * 0.06, timp(55, 0.5, 0.18 + 0.03 * k))           # timpani roll
        for k in range(16): addn(at + 0.6 + k * 0.125, 0.09 * np.exp(-L(0.06) * 60) * np.sin(2 * np.pi * 1320 * L(0.06)))  # pulse
        for j, (tt_, ch) in enumerate(((0.6, (196, 247, 294)), (1.35, (220, 277, 330)), (2.1, (262, 330, 392)), (2.6, (294, 370, 440)))):
            for f in ch: addn(at + tt_, brass(f, 0.9 if j < 3 else 1.6, 0.11))
            addn(at + tt_, timp(49 if j < 3 else 41, 1.0, 0.5))
    elif kind == "news_close":
        for k in range(8): addn(at + k * 0.11, 0.08 * np.exp(-L(0.06) * 60) * np.sin(2 * np.pi * 1320 * L(0.06)))
        for tt_, ch in ((0.0, (262, 330, 392)), (0.45, (294, 370, 440)), (0.9, (196, 247, 294, 392))):
            for f in ch: addn(at + tt_, brass(f, 1.5 if tt_ > 0.8 else 0.6, 0.11))
            addn(at + tt_, timp(45, 1.2, 0.55))
if np.any(news): news = news / (np.max(np.abs(news)) + 1e-9) * 0.75
mix = voice + music + 0.6 * sfx + news
mix = mix[:int(T * SR)]
mix = mix / np.max(np.abs(mix)) * 0.95
sf.write("mix.wav", np.stack([mix, mix], 1), SR)
print("audio", len(mix) / SR)
