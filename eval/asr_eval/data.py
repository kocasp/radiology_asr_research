"""Zbiór testowy: wszystkie nagrania naturalne z recordings/radiology.sqlite (939)."""
import os
import sqlite3
import numpy as np
import soundfile as sf
import soxr

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REC = os.path.join(ROOT, "recordings")


def test_set(limit=None):
    con = sqlite3.connect(os.path.join(REC, "radiology.sqlite"))
    rows = con.execute("""SELECT recording_id, path, phrase, speaker_id, category_code, duration_s
                          FROM recordings WHERE source='natural' ORDER BY recording_id""").fetchall()
    items = [dict(id=r[0], path=os.path.join(REC, r[1]), ref=r[2], speaker=r[3], cat=r[4], dur=r[5]) for r in rows]
    return items[:limit] if limit else items


def load_16k(path):
    x, sr = sf.read(path, dtype="float32", always_2d=True)
    x = x.mean(1)
    if sr != 16000:
        x = soxr.resample(x, sr, 16000)
    return np.ascontiguousarray(x, dtype=np.float32)
