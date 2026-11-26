"""Voice generator v4 — ElevenLabs Text-to-Dialogue (eleven_v3), chosen by Bidhan 2026-11-21 (pair A: Chris + Jessica).
Same script format as tts2.py: {"lines": [[spoken, caption, speaker "M"/"F", emotion?], ...]}.
 - emotion presets become v3 audio tags at the start of the line (unless the line already starts with "[").
 - one API call for the whole conversation -> natural turn-taking, real question intonation.
 - /with-timestamps gives each line's start/end, so the audio is cut into l{i}.wav (each segment keeps the
   natural pause that follows it) and meta.json is written exactly like tts2.py -> render with PAD = 0 and run
   audio2.py with pad 0.
API key: env ELEVENLABS_API_KEY or /home/claude/.elevenlabs_key (NEVER commit the key: this repo is public).
Falls back with exit code 2 if the API fails or credits are too low -> then use tts2.py (kokoro).
usage: python tts_el.py script.json [--reuse]   (--reuse re-cuts the saved dialogue.json without spending credits)
Script options (2026-11-25): "settings" (v3 dialogue settings, default stability 0.0), "beat_gap" (max pause kept inside
lines with "..."/"—"/[sighs], default 0.6), "tag_lead" (max s of a tag's laugh/exhale before the first word), "drop" (line
indices generated but cut from the edit)."""
import json, sys, os, base64, subprocess, numpy as np, soundfile as sf

VOICES = {"M": "LERny3t2s1OQcjLCatHn",   # "Bidhan" — Bidhan's own voice (replaced 2026-11-22; looked up by name at run time)
          "F": "cgSgspJ2msm6clMCkdW9"}   # Jessica — Playful, Bright, Warm (female, American)
TAGS = {"urgent": "[excited]", "excited": "[excited]", "surprised": "[surprised]", "curious": "[curious]",
        "awe": "[amazed]", "playful": "[playful]", "serious": "", "neutral": "",
        # 2026-11-25 (Bidhan: "some expressions sound so robotic"): only REAL v3 tags, and calm emotions get NO tag —
        # invented tags ([matter-of-fact], [warmly], [intrigued]) were read literally or flattened the delivery.
        "intrigued": "", "matter_of_fact": "", "warm": "", "thoughtful": "",
        "deadpan": "[deadpan]", "sarcastic": "[sarcastic]", "sighs": "[sighs]", "laughs": "[laughs]",
        "mischievous": "[mischievously]", "whispers": "[whispers]"}
API = "https://api.elevenlabs.io/v1"
LEAD = 0.10   # max silence kept before each line's first word (reactions feel snappier)


def key():
    k = os.environ.get("ELEVENLABS_API_KEY")
    if not k and os.path.exists("/home/claude/.elevenlabs_key"): k = open("/home/claude/.elevenlabs_key").read().strip()
    if not k: sys.exit("no ElevenLabs key")
    return k


def call(path, body=None, out=None):
    cmd = ["curl", "-s", "-m", "300", "-w", "\n%{http_code}", "-H", f"xi-api-key: {key()}"]
    if body is not None: cmd += ["-X", "POST", "-H", "Content-Type: application/json", "-d", json.dumps(body)]
    r = subprocess.run(cmd + [API + path], capture_output=True)
    data, _, code = r.stdout.rpartition(b"\n")
    if code != b"200": print("ElevenLabs HTTP", code.decode(), data[:300], file=sys.stderr); sys.exit(2)
    return json.loads(data)


def tighten(x, sr, max_gap=0.25, tail=0.08, thr=0.006, with_map=False, lead=0.1):
    """shorten silences inside a line to max_gap and the trailing pause to tail (v3 tends to leave long gaps).
    with_map=True also returns (orig_times, new_times) breakpoints so word timestamps can be moved with the audio."""
    win = int(0.02 * sr); n = len(x) // win
    if n < 3: return (x, ([0, len(x) / sr], [0, len(x) / sr])) if with_map else x
    e = np.sqrt((x[:n * win].reshape(n, win) ** 2).mean(1)); loud = e > thr
    out = []; i = 0; po, pn = [0.0], [0.0]; newlen = 0
    while i < n:
        j = i
        while j < n and loud[j] == loud[i]: j += 1
        chunk = x[i * win:j * win]
        if not loud[i]:
            keep = int((tail if j == n else max_gap) * sr)
            if i == 0: keep = min(keep, int(lead * sr))
            if len(chunk) > keep: chunk = np.concatenate([chunk[:keep // 2], chunk[-(keep - keep // 2):]]) if keep > 0 else chunk[:0]
        out.append(chunk); newlen += len(chunk); po.append(j * win / sr); pn.append(newlen / sr); i = j
    out.append(x[n * win:]); y = np.concatenate(out)
    po.append(len(x) / sr); pn.append(len(y) / sr)
    return (y, (po, pn)) if with_map else y


def words_from_alignment(al):
    """[(word, start, end, char_index)] from ElevenLabs character alignment, skipping [audio tags]"""
    ch, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    out, cur, t0, t1, tag, ci = [], "", None, None, False, 0
    for k, (c, a_, b_) in enumerate(zip(ch, st, en)):
        if c == "[": tag = True
        if tag:
            if c == "]": tag = False
            continue
        if c.isspace():
            if cur: out.append((cur, t0, t1, ci)); cur = ""
            continue
        # 2026-11-25: v3 dialogue alignment can join two lines with NO space ("snacks.No") -> the next line's first word
        # was glued to the previous line's last word (wrong caption timing). Split at [.?!…] + capital/digit.
        if cur and cur[-1] in ".?!…" and (c.isupper() or c.isdigit()):
            out.append((cur, t0, t1, ci)); cur = ""
        if not cur: t0 = a_; ci = k
        cur += c; t1 = b_
    if cur: out.append((cur, t0, t1, ci))
    return out


def refine_words(x, sr, ws, thr=0.012, look=0.45):
    """2026-11-25: v3 word timestamps are sometimes up to ~0.4 s EARLY (caption shows before the word is heard).
    If there is no voice energy at a word's start, move the start forward to the first voiced 10 ms window (within
    `look` s, never past the word's end / next word)."""
    w = int(0.01 * sr); n = len(x) // w
    if n == 0: return ws
    r = np.sqrt((x[:n * w].reshape(n, w) ** 2).mean(1))
    out = []
    for j, (wd, a_, b_) in enumerate(ws):
        q = int(a_ * 100)
        if q < n and r[q:q + 8].mean() < thr:
            lim = min(n, int((a_ + look) * 100), int(((ws[j + 1][1] if j + 1 < len(ws) else b_ + look)) * 100))
            for k in range(q, lim):
                if r[k] > thr: a_ = k / 100; break
        out.append([wd, a_, max(b_, a_ + 0.05)])
    return out


def resolve_bidhan(default):
    """Bidhan may retrain/replace his voice: use the newest personal voice whose name starts with 'Bidhan'.
    Falls back to the stored id, then to Chris (iP95p4xoKVk53GoZ742B) if neither exists."""
    try:
        vs = call("/../v2/voices?voice_type=personal&page_size=50").get("voices", [])
        mine = sorted([v for v in vs if v["name"].lower().startswith("bidhan")], key=lambda v: v.get("created_at_unix") or 0)
        if mine: return mine[-1]["voice_id"]
        return default if any(v["voice_id"] == default for v in vs) else "iP95p4xoKVk53GoZ742B"
    except SystemExit:
        return default


def per_line(S, V, gap=0.22):
    """Added 2026-11-23: eleven_v3 dialogue can drift a voice's accent (British voices came out American-sounding).
    Script option "model": "per_line" renders each line separately with eleven_multilingual_v2 (keeps the voice's own
    accent; audio tags are NOT supported, so emotions become voice settings), then joins them into the same
    dialogue.json structure (audio, voice_segments, alignment) the rest of this script expects."""
    STY = {"excited": 0.65, "surprised": 0.6, "playful": 0.55, "curious": 0.45, "warm": 0.35, "intrigued": 0.4,
           "serious": 0.15, "matter_of_fact": 0.1, "neutral": 0.2, "awe": 0.4, "thoughtful": 0.25}
    parts, segs, chars, st, en = [], [], [], [], []; t0 = 0.0; sr = 44100
    for i, line in enumerate(S["lines"]):
        txt = line[0]; emo = line[3] if len(line) > 3 and isinstance(line[3], str) else "neutral"
        r = call(f"/text-to-speech/{V[line[2]]}/with-timestamps?output_format=mp3_44100_128",
                 {"text": txt, "model_id": S.get("line_model", "eleven_multilingual_v2"),
                  "voice_settings": {"stability": 0.45, "similarity_boost": 0.85, "style": STY.get(emo, 0.3), "use_speaker_boost": True,
                                    "speed": S.get("speed", 1.0)}})   # Bidhan 2026-11-23: news bulletins at ~0.9
        open("_l.mp3", "wb").write(base64.b64decode(r["audio_base64"]))
        subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", "_l.mp3", "-ac", "1", "-ar", str(sr), "_l.wav"])
        x, _ = sf.read("_l.wav"); dur = len(x) / sr
        al = r["alignment"]
        if i: chars.append(" "); st.append(t0 - gap); en.append(t0 - gap)
        chars += al["characters"]; st += [t0 + v for v in al["character_start_times_seconds"]]; en += [t0 + v for v in al["character_end_times_seconds"]]
        segs.append({"dialogue_input_index": i, "start_time_seconds": t0, "end_time_seconds": t0 + dur})
        parts.append(np.concatenate([x, np.zeros(int(gap * sr))])); t0 += dur + gap
    sf.write("_all.wav", np.concatenate(parts), sr)
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", "_all.wav", "-b:a", "192k", "_all.mp3"])
    return {"audio_base64": base64.b64encode(open("_all.mp3", "rb").read()).decode(), "voice_segments": segs,
            "alignment": {"characters": chars, "character_start_times_seconds": st, "character_end_times_seconds": en}}


def credits_left():
    s = call("/user/subscription"); return s["character_limit"] - s["character_count"]


if __name__ == "__main__":
    S = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "script.json"))
    if "--reuse" not in sys.argv: VOICES["M"] = resolve_bidhan(VOICES["M"]); print("male voice", VOICES["M"])
    V = {**VOICES, **{k: v["el"] for k, v in S.get("voices", {}).items() if isinstance(v, dict) and "el" in v}}
    inputs = []
    for line in S["lines"]:
        spoken, spk = line[0], line[2]; emo = line[3] if len(line) > 3 else "neutral"
        tag = TAGS.get(emo, "") if isinstance(emo, str) else ""
        inputs.append({"text": spoken if spoken.lstrip().startswith("[") or not tag else f"{tag} {spoken}", "voice_id": V[spk]})
    # 2026-11-25: eleven_v3 dialogue twice cut the LAST line off mid-word (audio ends at full volume). A short throwaway
    # last input absorbs that truncation; it is never used in the edit. Disable with "pad_last": false.
    NL = len(S["lines"]); PAD_LAST = S.get("pad_last", True) and S.get("model") != "per_line"
    if PAD_LAST: inputs.append({"text": "[laughs] Mm-hm.", "voice_id": V[S["lines"][-1][2]]})
    need = sum(len(i["text"]) for i in inputs)
    if "--reuse" not in sys.argv:
        left = credits_left(); print("characters", need, "credits left", left)
        if left < need + 500: print("not enough ElevenLabs credits", file=sys.stderr); sys.exit(2)
    if os.path.exists("dialogue.json") and "--reuse" in sys.argv: d = json.load(open("dialogue.json"))
    else:
        if S.get("model") == "per_line":
            d = per_line(S, V)   # accent-faithful mode (one eleven_multilingual_v2 call per line, no audio tags)
        else:
            # v3 "Creative" (stability 0.0) = most expressive delivery (PLAYBOOK "LESS ROBOTIC", 2026-11-25)
            d = call("/text-to-dialogue/with-timestamps?output_format=mp3_44100_128",
                     {"model_id": "eleven_v3", "inputs": inputs, "settings": S.get("settings", {"stability": 0.0})})
        json.dump(d, open("dialogue.json", "w"))
    open("dialogue.mp3", "wb").write(base64.b64decode(d["audio_base64"]))
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", "dialogue.mp3", "-ac", "1", "-ar", "44100", "dialogue.wav"])
    a, sr = sf.read("dialogue.wav")
    # ---- cut the dialogue into lines (REWRITTEN 2026-11-25 after Bidhan: "missing words", "subtitles do not sync") ----
    # Old method shortened every pause inside a line (tighten(), RMS < 0.006 = "silence") -> quiet/deadpan words were
    # squashed or cut, and word times were remapped through that edit -> captions drifted. New method:
    #  * words are assigned to lines by CHARACTER index (voice_segments character ranges), never by time;
    #  * NO edits inside a line: only the silence before the first word (energy onset) and after the last word are trimmed,
    #    so word timestamps just shift by one constant and stay exactly on the voice.
    segs = {}
    for v in d.get("voice_segments", []):
        i = v["dialogue_input_index"]; r = segs.setdefault(i, [1e9, 0, 1e9, 0])
        r[0] = min(r[0], v["start_time_seconds"]); r[1] = max(r[1], v["end_time_seconds"])
        r[2] = min(r[2], v.get("character_start_index", 1e9)); r[3] = max(r[3], v.get("character_end_index", 0))
    n = len(segs); assert n >= NL, f"timestamps for {n}/{NL} lines"
    al = d.get("alignment") or d.get("normalized_alignment")
    WORDS = words_from_alignment(al) if al else []
    TAIL = S.get("tail", 0.28)        # pause kept after each line's last word (turn-taking gap)
    meta = []; dur_a = len(a) / sr
    # v3's segment boundaries / last-character times end ~0.1-0.3 s BEFORE the voice really stops -> cutting there clipped
    # the end of the last word of many lines ("missing words"). Move each boundary forward to the first real silence
    # (>= 80 ms below -40 dB-ish) within 0.8 s, else to the quietest point in that range.
    W10 = int(0.01 * sr); NW = len(a) // W10
    R = np.sqrt((a[:NW * W10].reshape(NW, W10) ** 2).mean(1))
    def split_at(b):
        q0 = int(b * 100); q1 = min(NW - 8, q0 + 80)
        for q in range(q0, q1):
            if (R[q:q + 8] < 0.008).all(): return (q + 4) / 100
        return (q0 + int(np.argmin(R[q0:q1 + 1]))) / 100 if q1 > q0 else b
    BOUND = [0.0] + [split_at(segs[k][0]) for k in range(1, NL)] + [split_at(segs[NL][0]) if n > NL else dur_a]
    for i, line in enumerate(S["lines"]):
        cs, ce = segs[i][2], segs[i][3]
        ws = [[w, t0, t1] for w, t0, t1, ci in WORDS if cs <= ci < ce]
        if not ws: ws = [[w, t0, t1] for w, t0, t1, ci in WORDS if segs[i][0] <= t0 < segs[i][1]]
        w0, w1 = BOUND[i], BOUND[i + 1]
        x = a[int(w0 * sr):int(w1 * sr)].copy()
        win = int(0.01 * sr); nw = len(x) // win
        rms = np.sqrt((x[:nw * win].reshape(nw, win) ** 2).mean(1)) if nw else np.zeros(1)
        thr = max(0.006, 0.05 * rms.max())
        # onset: first sustained voice after a 60 ms guard, but never after the first word's END
        on = 0.0
        for q in range(6, max(7, nw - 6)):
            if rms[q] > thr and rms[q:q + 6].mean() > thr: on = q * win / sr; break
        if ws: on = min(on, ws[0][2] - w0 - 0.08)
        lead = 0.03 if i == 0 else LEAD
        if S.get("tag_lead") is not None and ws and (ws[0][1] - w0) - on > S["tag_lead"]: on = ws[0][1] - w0 - S["tag_lead"]
        cut = max(0.0, on - lead)
        # end: last sustained voice, never before the last word's end
        last = len(x) / sr
        for q in range(nw - 1, 0, -1):
            if rms[q] > thr: last = (q + 1) * win / sr; break
        if ws: last = max(last, ws[-1][1] - w0 + 0.25)      # v3 stretches the last word's END over the pause: trust energy
        if ws: ws[0][1] = max(ws[0][1], w0 + on - 0.02)      # ...and the first word's START over the lead-in silence
        if ws: ws[-1][2] = min(ws[-1][2], w0 + last)
        x = x[int(cut * sr):int(min(len(x) / sr, last + TAIL) * sr)]
        fade = int(0.012 * sr); x[:fade] *= np.linspace(0, 1, fade); x[-fade:] *= np.linspace(1, 0, fade)
        ws = [[w, max(0.0, t0 - w0 - cut), max(0.0, t1 - w0 - cut)] for w, t0, t1 in ws]
        if i == NL - 1 and len(x) > sr // 10 and np.sqrt((x[-int(0.05 * sr):] ** 2).mean()) > 0.02:
            print(f"WARNING: line {i} ends while the voice is still loud (dialogue audio may be truncated)", file=sys.stderr)
        sf.write(f"l{i}.wav", x, sr)
        meta.append({"text": line[0], "cap": line[1], "dur": len(x) / sr, "sr": sr, "speaker": line[2],
                     "emotion": line[3] if len(line) > 3 else "neutral", "words": ws})
    if S.get("drop"):   # line indices generated but cut from the final edit; renumber l*.wav to stay contiguous
        keep = [j for j in range(len(meta)) if j not in S["drop"]]
        wavs = [sf.read(f"l{j}.wav")[0] for j in keep]
        for k in range(len(meta)):
            if os.path.exists(f"l{k}.wav"): os.remove(f"l{k}.wav")
        for k, wv in enumerate(wavs): sf.write(f"l{k}.wav", wv, sr)
        meta = [meta[j] for j in keep]
    if S.get("tempo", 1.0) != 1.0:   # optional pitch-preserving speed-up (atempo), e.g. 1.05 to land under 75 s; word times scaled
        k = float(S["tempo"])
        for i, z in enumerate(meta):
            subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", f"l{i}.wav", "-filter:a", f"atempo={k:.4f}", "-ar", str(sr), "_t.wav"])
            y, _ = sf.read("_t.wav"); sf.write(f"l{i}.wav", y, sr)
            z["dur"] = len(y) / sr; z["words"] = [[w, a_ / k, b_ / k] for w, a_, b_ in z["words"]]
    for i, z in enumerate(meta):   # snap early word starts onto the voice
        z["words"] = refine_words(sf.read(f"l{i}.wav")[0], sr, z["words"])
    json.dump(meta, open("meta.json", "w"), indent=1)
    print("total", round(sum(m["dur"] for m in meta), 2), [round(m["dur"], 2) for m in meta])
