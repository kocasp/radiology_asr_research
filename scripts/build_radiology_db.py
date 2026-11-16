"""Buduje bazę nagrań radiologicznych z ADMEDVOICE (kategorie 02-001, 02-003).

Użycie: python3 build_radiology_db.py <recordings_dir> [--move]
Bez --move tylko raportuje (dry run). Z --move przenosi .wav do audio/<source>/<speaker>/.
"""
import csv, os, re, sqlite3, struct, sys, shutil, unicodedata
from collections import Counter, defaultdict

ROOT = os.path.abspath(sys.argv[1]); MOVE = "--move" in sys.argv
CATS = {"02-001": "radiologia tarczycy (USG)", "02-003": "radiologia głowa–szyja"}
SRC_DIRS = {"natural": "human_voices/human/human", "anonymized": "anoni/anoni", "synthetic": "synth/synth"}
SUMMARY_SRC = {"natural": "natural", "anonymization": "anonymized", "synthesis": "synthetic"}
MICS = {"NTG2": "RODE NTG-2", "TLM3": "Neumann TLM 103", "TLM2": "Neumann TLM 102", "S416": "Sennheiser MKH 416",
        "BEB5": "Behringer B-5", "SK24": "Sennheiser ME 4-N", "SU58": "Shure SM58", "ZOF2": "Zoom F2",
        "ONLN": "nagranie online (nieznany mikrofon)", "MODE": "synteza mowy"}
NAME_RE = re.compile(r"^(?P<place>[A-Z0-9]+)-(?P<spk>[A-Z]+\d+)-FOR-(?P<mic>[A-Z0-9]+)-(?P<cat>\d\d-\d{3})-(?P<tid>\d+)[-_](?P<date>[0-9T]+)\.wav$")

def wav_info(p):
    with open(p, "rb") as f:
        h = f.read(12)
        if h[:4] != b"RIFF" or h[8:12] != b"WAVE": raise ValueError(p)
        fmt = None
        while True:
            ch = f.read(8)
            if len(ch) < 8: break
            cid, size = ch[:4], struct.unpack("<I", ch[4:])[0]
            if cid == b"fmt ":
                d = f.read(size); _, nch, sr, br, _, bits = struct.unpack("<HHIIHH", d[:16]); fmt = (nch, sr, br, bits)
            elif cid == b"data":
                return dict(channels=fmt[0], sample_rate=fmt[1], bit_depth=fmt[3], duration_s=round(size / fmt[2], 3))
            else:
                f.seek(size + (size & 1), 1)
    raise ValueError("no data chunk " + p)

def norm(t):
    t = unicodedata.normalize("NFC", t or "").strip()
    return re.sub(r"\s+", " ", t)

# 1. metadane z corpus_summary_all.csv (deduplikacja po filename)
summary = {}
for r in csv.DictReader(open(os.path.join(ROOT, "corpus_summary_all.csv"), encoding="utf-8"), delimiter=";"):
    if r["cat_code"] in CATS: summary.setdefault(r["filename"], r)
# 2. CSV per katalog mówcy (zapasowe źródło transkrypcji)
local = {}
for src, d in SRC_DIRS.items():
    for c in CATS:
        for dp, _, fs in os.walk(os.path.join(ROOT, d, "cat_" + c)):
            for fn in fs:
                if fn.endswith(".csv"):
                    with open(os.path.join(dp, fn), encoding="utf-8") as fh:
                        for r in csv.DictReader(fh, delimiter=";"): local.setdefault(r["filename"], r)
# 3. pliki audio
rows, notes, problems = [], [], Counter()
for src, d in SRC_DIRS.items():
    for folder_cat in CATS:
        for dp, _, fs in os.walk(os.path.join(ROOT, d, "cat_" + folder_cat)):
            for fn in sorted(fs):
                full = os.path.join(dp, fn)
                if fn == "info.txt": notes.append(full); continue
                if not fn.endswith(".wav"): continue
                m = NAME_RE.match(fn)
                if not m: problems["bad_name"] += 1; print("BAD NAME", full); continue
                s = summary.get(fn); l = local.get(fn)
                if not s: problems[f"no_summary_{src}"] += 1
                phrase = norm((s or {}).get("phrase") or (l or {}).get("phrase"))
                if not phrase: problems[f"no_phrase_{src}"] += 1
                na = lambda v: None if v in (None, "", "NA", "unknown") else v
                g = lambda k: na((s or {}).get(k) or (l or {}).get(k))
                info = wav_info(full)
                # Błąd w korpusie: AMV102 ma teksty głowa–szyja (13289–13739) z kodem 02-001 w nazwie pliku.
                c = "02-003" if m["spk"] == "AMV102" and 13289 <= int(m["tid"]) <= 13739 else folder_cat
                rows.append(dict(
                    recording_id=fn[:-4], source=src, category_code=c, category=CATS[c],
                    speaker_id=m["spk"], speaker_sex=g("speaker_sex"), speaker_age=g("speaker_age"),
                    rec_place=m["place"], mic_code=m["mic"], mic=MICS.get(m["mic"]),
                    text_id=int(m["tid"]), phrase=phrase,
                    mos_pred=float(g("mos_pred")) if g("mos_pred") else None,
                    grade=float(g("grade")) if g("grade") else None, comments=g("comments"),
                    recorded_at=m["date"], **info,
                    path=f"audio/{src}/{m['spk']}/{fn}", _orig=full))
print("files:", Counter((r["source"], r["category_code"]) for r in rows)); print("problems:", dict(problems))
ids = Counter(r["recording_id"] for r in rows); dup = [k for k, v in ids.items() if v > 1]
print("duplicate recording ids:", len(dup))
# phrases: ten sam znormalizowany tekst -> ta sama phrase_group
groups = {}
for r in sorted(rows, key=lambda r: r["text_id"]):
    key = r["phrase"].lower().rstrip(".")
    r["phrase_group"] = groups.setdefault(key, len(groups) + 1)
print("unique text_id:", len({r['text_id'] for r in rows}), "unique phrase groups:", len(groups))
if not MOVE: sys.exit(0)

# 4. przenieś audio
for r in rows:
    dst = os.path.join(ROOT, r["path"]); os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(r.pop("_orig"), dst)
os.makedirs(os.path.join(ROOT, "docs/speaker_notes"), exist_ok=True)
for n in notes:
    spk = os.path.basename(os.path.dirname(n)); shutil.move(n, os.path.join(ROOT, "docs/speaker_notes", spk + ".txt"))

# 5. metadata.csv + phrases.csv + sqlite
cols = ["recording_id", "path", "source", "category_code", "category", "speaker_id", "speaker_sex", "speaker_age",
        "rec_place", "mic_code", "mic", "text_id", "phrase_group", "phrase", "duration_s", "sample_rate", "bit_depth",
        "channels", "mos_pred", "grade", "comments", "recorded_at"]
rows.sort(key=lambda r: (r["source"], r["category_code"], r["speaker_id"], r["text_id"], r["recording_id"]))
with open(os.path.join(ROOT, "metadata.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(rows)
ph = {}
for r in rows:
    p = ph.setdefault(r["text_id"], dict(text_id=r["text_id"], phrase_group=r["phrase_group"], category_code=r["category_code"],
                                          phrase=r["phrase"], n_words=len(r["phrase"].split()), n_natural=0, n_anonymized=0, n_synthetic=0))
    p["n_" + r["source"]] += 1
with open(os.path.join(ROOT, "phrases.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(next(iter(ph.values())).keys())); w.writeheader(); w.writerows(sorted(ph.values(), key=lambda p: p["text_id"]))

db = os.path.join(ROOT, "radiology.sqlite")
if os.path.exists(db): os.remove(db)
con = sqlite3.connect(db)
con.execute("""CREATE TABLE phrases(text_id INTEGER PRIMARY KEY, phrase_group INTEGER, category_code TEXT, phrase TEXT,
               n_words INTEGER, n_natural INTEGER, n_anonymized INTEGER, n_synthetic INTEGER)""")
con.execute("""CREATE TABLE recordings(recording_id TEXT PRIMARY KEY, path TEXT NOT NULL, source TEXT NOT NULL,
               category_code TEXT, category TEXT, speaker_id TEXT, speaker_sex TEXT, speaker_age INTEGER, rec_place TEXT,
               mic_code TEXT, mic TEXT, text_id INTEGER REFERENCES phrases(text_id), phrase_group INTEGER, phrase TEXT,
               duration_s REAL, sample_rate INTEGER, bit_depth INTEGER, channels INTEGER, mos_pred REAL, grade REAL,
               comments TEXT, recorded_at TEXT)""")
con.executemany("INSERT INTO phrases VALUES(:text_id,:phrase_group,:category_code,:phrase,:n_words,:n_natural,:n_anonymized,:n_synthetic)", ph.values())
con.executemany(f"INSERT INTO recordings VALUES({','.join(':'+c for c in cols)})", rows)
for c in ["source", "category_code", "speaker_id", "text_id"]:
    con.execute(f"CREATE INDEX ix_rec_{c} ON recordings({c})")
con.execute("""CREATE VIEW speakers AS SELECT source, speaker_id, speaker_sex, speaker_age, group_concat(DISTINCT mic_code) mics,
               count(*) n_recordings, round(sum(duration_s)/60,1) minutes FROM recordings GROUP BY source, speaker_id""")
con.execute("""CREATE VIEW summary AS SELECT source, category_code, count(*) n_recordings, count(DISTINCT speaker_id) n_speakers,
               count(DISTINCT text_id) n_texts, round(sum(duration_s)/3600,2) hours FROM recordings GROUP BY source, category_code""")
con.commit()
for r in con.execute("SELECT * FROM summary"): print(r)
