"""Weekly YouTube long-form (PLAYBOOK "EXTRAS BEYOND THE VIDEO" 5, added 2026-11-25): compile the week's Shorts into
one 16:9 1920x1080 video. Each Short sits in the centre at full height; the side margins are a blurred, zoomed copy of
the same frames (no flat border), with a chapter label on the left and the channel name on the right. No new voice.
usage: python compile_longform.py out.mp4 "Title 1=videos/a.mp4" "Title 2=videos/b.mp4" ...
prints the YouTube chapter list (0:00 Title ...) for the description."""
import sys, subprocess, os

FONT = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"


def dur(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]))


def esc(s):
    return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace(",", "\\,")


def chapter(i, title, src, out):
    vf = (f"[0:v]split[a][b];[a]scale=1920:-2,crop=1920:1080,boxblur=28:2,eq=brightness=-0.08:saturation=1.2[bg];"
          f"[b]scale=-2:1080[fg];[bg][fg]overlay=(W-w)/2:0,"
          f"drawtext=fontfile={FONT}:text='{i}':x=(656-tw)/2:y=330:fontsize=150:fontcolor=0xFFC857:borderw=6:bordercolor=0x0B1026,"
          f"drawtext=fontfile={FONT}:text='{esc(title)}':x=max(20\\,(656-tw)/2):y=520:fontsize=44:fontcolor=white:borderw=5:bordercolor=0x0B1026,"
          f"drawtext=fontfile={FONT}:text='HOW ON EARTH?':x=1264+(656-tw)/2:y=500:fontsize=52:fontcolor=white:borderw=5:bordercolor=0x0B1026[v]")
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", vf, "-map", "[v]", "-map", "0:a",
                           "-c:v", "libx264", "-preset", "veryfast", "-b:v", "1100k", "-maxrate", "1500k", "-bufsize", "3000k",
                           "-r", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", out])


if __name__ == "__main__":
    out = sys.argv[1]; items = [a.split("=", 1) for a in sys.argv[2:]]
    parts, t, chap = [], 0.0, []
    for i, (title, src) in enumerate(items, 1):
        p = f"_ch{i:02d}.mp4"
        if not os.path.exists(p): chapter(i, title, src, p)
        parts.append(p); chap.append(f"{int(t // 60)}:{int(t % 60):02d} {title}"); t += dur(p)
    open("_list.txt", "w").write("".join(f"file {p}\n" for p in parts))
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-i", "_list.txt", "-c", "copy", "-movflags", "+faststart", out])
    print("\n".join(chap)); print("total", round(t, 1))
