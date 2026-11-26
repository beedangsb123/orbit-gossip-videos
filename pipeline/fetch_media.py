"""Find + download free-licence real imagery/footage with licence + credit captured.
Sources: Wikimedia Commons API (PD / CC0 / CC BY / CC BY-SA only) and NASA images API (public domain).
usage:
  python fetch_media.py commons "Hoover Dam aerial" [n] [image|video]  -> lists candidates (title, licence, size, author)
  python fetch_media.py get "File:Some file.jpg" outdir                  -> downloads 1920px (images) or original (video) + writes credits.txt line
  python fetch_media.py nasa "Lake Mead" [n]                            -> NASA image candidates (nasa_id, title, url)
Rules: no people's faces, no logos/brands, no Indigenous sacred-site close-ups. Credit CC BY/BY-SA in the caption.
Network notes: thumb.wikimedia.org is blocked by the proxy; upload.wikimedia.org works (paths are rewritten).
Thumb widths must be standard steps (e.g. 1920, 3840); 7680 returns 400. Send the UA and wait ~1 s between calls."""
import json, sys, os, re, time, subprocess, urllib.parse, html
UA = "HowOnEarthBot/1.0 (https://github.com/beedangsb123/how-on-earth-videos)"
OK = re.compile(r"^(public domain|pd|cc0|cc by(-sa)? ?[0-9.]*)", re.I)


def get(url, tries=5):
    for i in range(tries):  # Wikimedia rate-limits (429): back off and retry
        time.sleep(1.0 + 4 * i)
        r = subprocess.run(["curl", "-s", "-m", "90", "-A", UA, "-w", "\n%{http_code}", url], capture_output=True)
        body, _, code = r.stdout.rpartition(b"\n")
        if code == b"200": return body
        print(f"  HTTP {code.decode()} for {url[:90]}… retry {i + 1}", file=sys.stderr)
    raise RuntimeError("download failed: " + url)


def commons_search(q, n=12, kind="image"):
    ft = "bitmap" if kind == "image" else "video"
    url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6&gsrlimit=%d&gsrsearch=%s"
           "&prop=imageinfo&iiprop=url|size|extmetadata|mime&iiurlwidth=1920") % (n, urllib.parse.quote(f"{q} filetype:{ft}"))
    d = json.loads(get(url)); out = []
    for p in (d.get("query", {}).get("pages", {}) or {}).values():
        ii = p["imageinfo"][0]; m = ii.get("extmetadata", {})
        lic = m.get("LicenseShortName", {}).get("value", "")
        if not OK.match(lic.strip()): continue
        art = re.sub("<[^>]+>", "", html.unescape(m.get("Artist", {}).get("value", "")))[:80].strip()
        out.append({"title": p["title"], "licence": lic, "author": art, "w": ii.get("width"), "h": ii.get("height"),
                    "mime": ii.get("mime"), "url": ii.get("url"), "thumb": (ii.get("thumburl") or "").split("?")[0].replace("thumb.wikimedia.org", "upload.wikimedia.org")})
    return out


def download(title, outdir):
    os.makedirs(outdir, exist_ok=True)
    # FM_WIDTH=3840 for landscape photos that get cropped to a 9:16 frame (1920 px wide is too soft once cropped; added 2026-11-25)
    url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&titles=%s&prop=imageinfo&iiprop=url|extmetadata|mime&iiurlwidth=%s"
           % (urllib.parse.quote(title), os.environ.get("FM_WIDTH", "1920")))
    p = list(json.loads(get(url))["query"]["pages"].values())[0]; ii = p["imageinfo"][0]; m = ii["extmetadata"]
    lic = m.get("LicenseShortName", {}).get("value", ""); assert OK.match(lic.strip()), "licence not allowed: " + lic
    src = ii["url"] if ii["mime"].startswith("video") else (ii.get("thumburl") or ii["url"]).split("?")[0].replace("thumb.wikimedia.org", "upload.wikimedia.org")
    fn = os.path.join(outdir, re.sub(r"[^A-Za-z0-9._-]", "_", title.split(":", 1)[1]))
    open(fn, "wb").write(get(src))
    art = re.sub("<[^>]+>", "", html.unescape(m.get("Artist", {}).get("value", "")))
    art = re.split(r"\s*Related names", " ".join(art.split()))[0][:80].strip()   # HAER/LoC pages add multi-line "Related names"
    credit = f"{title.split(':',1)[1]}: {art} / {lic} via Wikimedia Commons"
    open(os.path.join(outdir, "credits.txt"), "a").write(credit + "\n"); print(fn); print(credit)


def nasa_search(q, n=10):
    d = json.loads(get("https://images-api.nasa.gov/search?media_type=image&q=" + urllib.parse.quote(q)))
    for it in d["collection"]["items"][:n]:
        dd = it["data"][0]; print(dd["nasa_id"], "|", dd["title"][:70], "|", it["links"][0]["href"] if it.get("links") else "")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "commons":
        for r in commons_search(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 12, sys.argv[4] if len(sys.argv) > 4 else "image"):
            print(f'{r["title"]} | {r["licence"]} | {r["w"]}x{r["h"]} | {r["author"]}')
    elif cmd == "get": download(sys.argv[2], sys.argv[3])
    elif cmd == "nasa": nasa_search(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10)
