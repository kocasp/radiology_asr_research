"""Buduje results/results.sqlite ze wszystkich ukończonych przebiegów (results/<model>/hyp.jsonl + metrics.json).
Baza jest w całości odtwarzalna z plików JSONL — można ją usunąć i zbudować ponownie (np. po zmianie normalizacji).

Użycie (z katalogu eval/):  uv run python build_results_db.py
"""
import json, os, sqlite3, sys

sys.path.insert(0, os.path.dirname(__file__))
from asr_eval import data, metrics, textnorm
from asr_eval.plan import PLAN

RES = os.path.join(data.ROOT, "results")
DB = os.path.join(RES, "results.sqlite")
NORM_VERSION = "v1 (lowercase, bez interpunkcji, 14x12 -> 14 x 12, 50mm -> 50 mm, liczby bez zamiany na słowa)"

SCHEMA = """
CREATE TABLE runs(
  run_id TEXT PRIMARY KEY, name TEXT, model TEXT, lora TEXT, mode TEXT, engine TEXT, params TEXT,
  decoding TEXT, normalization TEXT, leak_risk TEXT, finished TEXT,
  n_utt INTEGER, n_words INTEGER, wer REAL, wer_ci_lo REAL, wer_ci_hi REAL, cer REAL, cer_ci_lo REAL, cer_ci_hi REAL,
  S INTEGER, D INTEGER, I INTEGER, long_ins INTEGER, utt_perfect REAL,
  num_err REAL, num_n INTEGER, neg_err REAL, neg_n INTEGER, side_err REAL, side_n INTEGER,
  audio_s REAL, proc_s REAL, rtf REAL);
CREATE TABLE utterances(
  run_id TEXT REFERENCES runs(run_id), recording_id TEXT,
  speaker_id TEXT, speaker_sex TEXT, category_code TEXT, mic_code TEXT, rec_place TEXT, duration_s REAL, text_id INTEGER,
  ref TEXT, hyp TEXT, ref_norm TEXT, hyp_norm TEXT,
  n_words INTEGER, S INTEGER, D INTEGER, I INTEGER, wer REAL, n_chars INTEGER, char_err INTEGER, cer REAL,
  num_err INTEGER, num_n INTEGER, neg_err INTEGER, neg_n INTEGER, side_err INTEGER, side_n INTEGER,
  long_ins INTEGER, perfect INTEGER, proc_s REAL,
  PRIMARY KEY(run_id, recording_id));
CREATE TABLE errors(
  run_id TEXT, recording_id TEXT, op TEXT, ref_pos INTEGER, hyp_pos INTEGER,
  ref_text TEXT, hyp_text TEXT, n_ref INTEGER, n_hyp INTEGER, category TEXT, long_ins INTEGER);
CREATE INDEX ix_err_run ON errors(run_id, op, category);
CREATE INDEX ix_utt_rec ON utterances(recording_id);

-- WER w podziale na kategorię / mówcę / mikrofon (ważony liczbą słów)
CREATE VIEW v_by_category AS SELECT run_id, category_code, count(*) n_utt,
  round(100.0*sum(S+D+I)/sum(n_words),2) wer, round(100.0*sum(char_err)/sum(n_chars),2) cer FROM utterances GROUP BY 1,2;
CREATE VIEW v_by_speaker AS SELECT run_id, speaker_id, speaker_sex, count(*) n_utt,
  round(100.0*sum(S+D+I)/sum(n_words),2) wer FROM utterances GROUP BY 1,2,3;
CREATE VIEW v_by_mic AS SELECT run_id, mic_code, rec_place, count(*) n_utt,
  round(100.0*sum(S+D+I)/sum(n_words),2) wer FROM utterances GROUP BY 1,2,3;
-- nagrania najtrudniejsze dla wszystkich modeli
CREATE VIEW v_hard_recordings AS SELECT recording_id, speaker_id, mic_code, duration_s, ref,
  count(*) n_runs, round(avg(wer),1) avg_wer, min(wer) best_wer, sum(perfect) n_perfect
  FROM utterances GROUP BY recording_id ORDER BY avg_wer DESC;
-- najczęstsze błędy
CREATE VIEW v_top_errors AS SELECT run_id, op, category, ref_text, hyp_text, count(*) n
  FROM errors GROUP BY 1,2,3,4,5 ORDER BY n DESC;
"""


def main():
    meta = {}
    con_rec = sqlite3.connect(os.path.join(data.REC, "radiology.sqlite"))
    for r in con_rec.execute("SELECT recording_id, speaker_id, speaker_sex, category_code, mic_code, rec_place, duration_s, text_id FROM recordings WHERE source='natural'"):
        meta[r[0]] = r[1:]
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    plan = {s["id"]: s for s in PLAN}
    n_runs = 0
    for rid, spec in plan.items():
        mpath, hpath = os.path.join(RES, rid, "metrics.json"), os.path.join(RES, rid, "hyp.jsonl")
        if not (os.path.exists(mpath) and os.path.exists(hpath)):
            continue
        m = json.load(open(mpath))
        recs = {}
        for line in open(hpath, encoding="utf-8"):
            r = json.loads(line); recs[r["id"]] = r
        utts, errs = [], []
        for rec_id, r in recs.items():
            rn, hn = textnorm.normalize(r["ref"]), textnorm.normalize(r["hyp"])
            s = metrics.utterance_stats(rn, hn)
            if not s:
                continue
            md = meta.get(rec_id, (None,) * 7)
            e = s["S"] + s["D"] + s["I"]
            utts.append((rid, rec_id, *md, r["ref"], r["hyp"], rn, hn, s["n_ref"], s["S"], s["D"], s["I"],
                         round(100 * e / s["n_ref"], 2), s["n_char"], s["char_err"], round(100 * s["char_err"] / max(s["n_char"], 1), 2),
                         s["cats"]["num"][0], s["cats"]["num"][1], s["cats"]["neg"][0], s["cats"]["neg"][1],
                         s["cats"]["side"][0], s["cats"]["side"][1], s["long_ins"], int(e == 0), r.get("sec")))
            for o in metrics.alignment_ops(rn, hn):
                errs.append((rid, rec_id, o["op"], o["ref_pos"], o["hyp_pos"], o["ref_text"], o["hyp_text"],
                             o["n_ref"], o["n_hyp"], o["category"], o["long_ins"]))
        run_row = (
            rid, spec["name"], spec["model"], m.get("lora"), spec["mode"], spec["engine"], spec.get("params"),
            m.get("decoding"), NORM_VERSION, spec.get("leak_risk"), m.get("finished"),
            m["n_utt"], m["n_words"], m["wer"], m["wer_ci"][0], m["wer_ci"][1], m["cer"], m["cer_ci"][0], m["cer_ci"][1],
            m["S"], m["D"], m["I"], m["long_ins"], m["utt_perfect"], m["num_err"], m["num_n"], m["neg_err"], m["neg_n"],
            m["side_err"], m["side_n"], m["audio_s"], m["proc_s"], m["rtf"])
        q = lambda n: "(" + ",".join("?" * n) + ")"
        con.execute("INSERT INTO runs VALUES" + q(len(run_row)), run_row)
        if utts:
            con.executemany("INSERT INTO utterances VALUES" + q(len(utts[0])), utts)
        if errs:
            con.executemany("INSERT INTO errors VALUES" + q(len(errs[0])), errs)
        n_runs += 1
        print(f"{rid}: {len(utts)} wypowiedzi, {len(errs)} błędów")
    con.commit()
    print(f"zapisano {DB} ({n_runs} przebiegów)")


if __name__ == "__main__":
    main()
