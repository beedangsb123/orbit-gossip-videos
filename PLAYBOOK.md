# Orbit Gossip — PLAYBOOK (read fully every run, follow exactly)

**Niche:** space, but make it gossip. Wild TRUE stories about planets, stars, moons, black holes, space missions and
astronauts' daily life, told as a celebrity-gossip show about space objects. ~70 s Shorts/Reels/TikToks, faceless.
**Owner:** Bidhan (Sydney time). Sister channel of How On Earth (natural wonders / mega-builds) — never cover Earth
landmarks, geography or mega-builds here.
**Goal:** grow to real income (platform payouts + sponsors/affiliates: telescopes, astronomy apps, learning apps, books).

## Accounts
| Platform | Handle | Link |
|---|---|---|
| YouTube | @orbitgossip | https://www.youtube.com/@orbitgossip (channel UCMAx70rfpCAMxxD13uToIYQ, Brand Account under Bidhan's Google login) |
| Facebook | Orbit Gossip (Page) | https://www.facebook.com/profile.php?id=61597052756928 |
| Instagram | @orbit.gossip | https://www.instagram.com/orbit.gossip |
| TikTok | @orbit.gossip | https://www.tiktok.com/@orbit.gossip |
- Metricool brand **Orbit Gossip, blogId 8377975** (How On Earth is blogId 8221611 — never post Orbit Gossip there).
- Email for IG/TikTok: orbitgossip@gmail.com. GitHub repo: beedangsb123/orbit-gossip-videos (public; NEVER commit keys).
- Every profile links to the other three (done 2026-11-26). Keep it that way.

## Bidhan's rules
- Never wait for approval to post; DO send him each finished video in the chat (SendUserFile). Push-notify only on problems.
- **ElevenLabs credits:** before generating, check credits. If they are too low for today's script (or the API fails),
  push-notify Bidhan ("ElevenLabs credits low/out — X left") AND tell him in the message; then render with the free
  kokoro voice (pipeline/tts_kok.py) so the day isn't missed. The key is shared with How On Earth (Starter plan,
  40,000 characters/month, resets monthly). Keep scripts ~1,000–1,200 characters.
- Don't spend money, change account settings or run ads without asking.
- **Cross-promotion (Bidhan 2026-11-26):** occasionally (1–2x/week, not daily) Orbit Gossip promotes How On Earth and
  vice versa — **same platform only**: Facebook→Facebook Page, Instagram→@howonearth2026, TikTok→@the.how.on.earth,
  YouTube→How On Earth channel. Do it as a pinned/first comment or one line in the caption ("Like Earth's wonders too?
  Follow @…"), never a whole video. Log the date in LOG.md so it stays occasional.

## FUN FIRST (Bidhan's strongest feedback on How On Earth: "there is no fun in this video")
- Format: a gossip show about a space object. F = gossip host who spills the facts; M = the big REACTOR who gets the
  punchlines (sarcasm, disbelief, laughs). ~1 laugh every 8–10 s, callback joke at the end, loop ending back to the hook.
- Never one host explaining for 4+ lines. Jokes about the object/physics/situation — never about people, cultures,
  religions or accents; no real public figures.
- Change the FORMAT every video, keep the brand: tabloid exposé, planet dating profile, "real or fake?", star ratings /
  reviews, red-carpet arrivals, breaking-news desk, "who wore it better", horoscope parody, "press the button" what-if.
- Recurring series (subscriber conversion — Shorts series convert far better): "Planet Reviews", "Space Scandals",
  "Real or Fake?". Put the series name on screen; at the end promise tomorrow's topic ("Tomorrow: the planet made of
  diamonds. Follow so you don't miss it.") — never ask to subscribe in the first 3 s.
- Banned lazy openers: "Wait", "Hang on", "Hold on", "No way", "Okay, tell me".

## Voices (ElevenLabs eleven_v3 Text-to-Dialogue, stability 0.0) — pipeline/tts_el.py
- Video 001 used Laura (F, FGY2WhTYpPnrIDTdsKH5) + Liam (M, TX3LPaxmHKxFdv7VOQHJ). Use a DIFFERENT lively pair each
  video (premade voices: Jessica cgSgspJ2msm6clMCkdW9, Sarah EXAVITQu4vr4xnSDxMaL, Alice Xb7hH8MSUJpSbSDYk0k2, Matilda
  XrExE9yKIg1WjnnlVkGX, Chris iP95p4xoKVk53GoZ742B, Charlie IKne3meq5aSn9XLyUdCD, George JBFqnCBsd6RMkjVDRZzb, Brian
  nPczCjzI2devNBz1zQrb, Will bIHbv24MWmeRgasZH58o, Eric cjVigY5qzO86Huf0OWal…). Avoid deadpan-only pairs.
- Set "voices": {"F": {"el": id}, "M": {"el": id}} in the script; only real v3 tags via emotions: excited, surprised,
  curious, playful, sarcastic, laughs, mischievous, whispers, sighs.
- Caption words must match spoken words 1:1 (write "Sixty-three light-years" ↔ "63 LIGHT-YEARS"). Numbers spoken as words.
- Fit 61–75 s total (incl. 2.4 s end card): use "tail": 0.12, "tempo" ≤ 1.08, and "drop" for lines to cut (no extra credits
  with --reuse). Render code must use original line numbers (see render_001.py ORIG/META/ST handling).

## Look v1 "tabloid cosmos" (pipeline/render_001.py is the reference render)
- Nebula + parallax stars background (never flat dark — Facebook border check), hot-pink tabloid stickers with yellow
  outline, EXCLUSIVE starbursts, stamps, review/score cards, paparazzi-flash cuts, ORBIT GOSSIP pill badge at top.
- Palette: space #120A2E, purple #3B1C7A, pink #FF3D9A, cyan #3DF5FF, yellow #FFE14D. Caption accent #FF5FB0.
- Real imagery first: NASA images API (images-api.nasa.gov, public domain), NASA/ESA/Hubble/Webb (ESA = CC BY 4.0 → credit
  in caption and on-screen tag), Wikimedia Commons PD/CC. Every fact gets a small on-screen source tag.
- Frame 1 = most striking real image + ≤6 words; voice at 0.0 s; first visual change by 1.5 s; change every 2–3 s;
  visual beats keyed to word times with wt(line, word); captions in safe zone y≈1440.
- Music: audio2.py style "default" transposed +3, 112 bpm (different from How On Earth). Soft SFX only.
- Encode: 1080x1920, 30 fps, -b:v 5200k, < 90 MB; run check_edges.py (must PASS) and listen-check line lengths.

## Posting (Metricool brand 8377975) — 4 single-network posts at the same time
- Daily main video at **19:00 Australia/Sydney** (never two main videos on one day, never in the past).
- TikTok: short caption + #fyp, tiktokData.title. Instagram: REEL, caption + #reels, firstCommentText = engagement question.
  Facebook: REEL + title + #facebookreels. YouTube: type short, title with #shorts, tags, category SCIENCE_TECHNOLOGY,
  madeForKids false. Captions open with a question, 1 emoji, the key number, 5–6 hashtags, image credit line.
- AI labels: off (nothing realistic is faked; voices narrate a comedy show). Never make realistic fake footage.
- Video hosted as public raw GitHub URL; confirm it returns 200 before scheduling.

## Facts
- Verify every number against NASA/ESA/JPL or peer-reviewed sources; prefer the exact source you tag on screen.
- No medical/financial advice, no tragedy-as-entertainment, no conspiracy "mysteries".
