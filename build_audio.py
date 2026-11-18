"""Konwertuje nagrania naturalne (recordings/audio) do Opus/OGG do gh-pages/audio/.

Dla każdego nagrania z recordings/radiology.sqlite tworzy gh-pages/audio/<recording_id>.ogg
(mono, 16 kHz, 24 kb/s — wystarczające do odsłuchu dyktowanych fraz). Pliki istniejące są
pomijane. Wymaga ffmpeg w PATH.

Użycie (z katalogu głównego repo):  python3 gh-pages/build_audio.py
"""
import os, sqlite3, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(ROOT, "recordings", "radiology.sqlite")
OUT = os.path.join(ROOT, "gh-pages", "audio")


def convert(row):
    rid, path = row
    src = os.path.join(ROOT, "recordings", path)
    dst = os.path.join(OUT, rid + ".ogg")
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return 0
    if not os.path.exists(src):
        return -1
    r = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src,
                        "-ac", "1", "-ar", "16000", "-c:a", "libopus", "-b:a", "24k",
                        "-application", "voip", dst], capture_output=True)
    return 0 if r.returncode == 0 else -2


def main():
    if not os.path.exists(REC):
        sys.exit(f"Brak {REC}")
    os.makedirs(OUT, exist_ok=True)
    rows = sqlite3.connect(REC).execute("SELECT recording_id, path FROM recordings WHERE source='natural'").fetchall()
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(convert, rows))
    ok = sum(1 for x in res if x == 0)
    total = sum(os.path.getsize(os.path.join(OUT, r + ".ogg")) for r, _ in rows if os.path.exists(os.path.join(OUT, r + ".ogg")))
    print(f"przekonwertowano/istnieją: {ok}/{len(rows)}; brakujących źródeł: {sum(1 for x in res if x == -1)}; "
          f"błędy ffmpeg: {sum(1 for x in res if x == -2)}; łącznie {total/1e6:.1f} MB")


if __name__ == "__main__":
    main()
