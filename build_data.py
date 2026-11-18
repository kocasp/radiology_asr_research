"""Buduje odchudzoną bazę SQLite do interaktywnej przeglądarki (gh-pages/data/benchmark.sqlite).

Źródło: results/results.sqlite (zbudowana przez eval/build_results_db.py). Do przeglądarki trafiają
tylko tabele `runs` i `utterances` (bez `term_tokens` i `errors`, które odpowiadają za większość
rozmiaru). Z utterances zachowane są znormalizowane teksty (`ref_norm`, `hyp_norm`); wyrównanie
i błędy na poziomie słów są liczone w przeglądarce (JS) na żądanie.

Użycie (z katalogu głównego repo):
  cd eval && uv run python build_results_db.py && cd ..
  python3 gh-pages/build_data.py
"""
import csv, json, os, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "results", "results.sqlite")
TERMS = os.path.join(ROOT, "results", "terms", "summary.csv")
DST = os.path.join(ROOT, "gh-pages", "data", "benchmark.sqlite")
DROP = {"ref", "hyp"}  # surowe teksty; wystarczą znormalizowane do diffu


def enrich_runs(con):
    """Dodaje do runs: WER-N (z metrics.json) oraz TER/TER-L/GWER (z results/terms/summary.csv)."""
    for col, typ in [("wer_num", "REAL"), ("ter", "REAL"), ("ter_ci_lo", "REAL"), ("ter_ci_hi", "REAL"),
                     ("ter_lenient", "REAL"), ("gwer", "REAL"), ("ter_to_gwer", "REAL")]:
        con.execute(f"ALTER TABLE runs ADD COLUMN {col} {typ}")
    terms = {}
    if os.path.exists(TERMS):
        for r in csv.DictReader(open(TERMS, encoding="utf-8")):
            terms[r["run_id"]] = r
    for (rid,) in con.execute("SELECT run_id FROM runs"):
        mpath = os.path.join(ROOT, "results", rid, "metrics.json")
        wer_num = None
        if os.path.exists(mpath):
            wer_num = json.load(open(mpath)).get("wer_num")
        t = terms.get(rid, {})
        def f(key):
            v = t.get(key)
            return float(v) if v not in (None, "") else None
        con.execute("UPDATE runs SET wer_num=?, ter=?, ter_ci_lo=?, ter_ci_hi=?, ter_lenient=?, gwer=?, ter_to_gwer=? WHERE run_id=?",
                    (wer_num, f("ter"), f("ter_ci_lo"), f("ter_ci_hi"), f("ter_lenient"), f("gwer"), f("ter_to_gwer"), rid))


def main():
    if not os.path.exists(SRC):
        sys.exit(f"Brak {SRC}. Uruchom najpierw: cd eval && uv run python build_results_db.py")
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    if os.path.exists(DST):
        os.remove(DST)
    con = sqlite3.connect(DST)
    con.execute(f"ATTACH DATABASE '{SRC}' AS src")
    runs_cols = [r[1] for r in con.execute("PRAGMA src.table_info(runs)")]
    utt_cols = [r[1] for r in con.execute("PRAGMA src.table_info(utterances)") if r[1] not in DROP]
    con.execute(f"CREATE TABLE runs AS SELECT {','.join(runs_cols)} FROM src.runs")
    con.execute(f"CREATE TABLE utterances AS SELECT {','.join(utt_cols)} FROM src.utterances")
    con.execute("CREATE INDEX ix_utt_run ON utterances(run_id)")
    con.execute("CREATE INDEX ix_utt_rec ON utterances(recording_id)")
    con.commit()
    con.execute("DETACH DATABASE src")
    enrich_runs(con)
    con.commit()
    con.execute("VACUUM")
    con.close()
    print(f"zapisano {DST} ({os.path.getsize(DST)/1e6:.1f} MB)")

if __name__ == "__main__":
    main()
