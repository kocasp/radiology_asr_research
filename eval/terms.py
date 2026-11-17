"""Analiza rozpoznawania słownictwa radiologicznego (terminów) przez modele ASR.

Dla każdego przebiegu (results/<id>/hyp.jsonl) i każdego słowa referencji wyznaczany jest jego los
w wyrównaniu jiwer (po textnorm.normalize). Każde wystąpienie słowa dostaje jeden status:
  correct       – forma identyczna jak w referencji,
  form          – ten sam lemat, inna forma fleksyjna („tarczycy” -> „tarczyca”, „przepływu” -> „przepływów”),
  segmentation  – te same litery, inny podział na słowa („okołotarczycowo” -> „około tarczycowo”,
                  „ti rads” -> „tirads”),
  near_miss     – słowo bliskie zapisem, ale nie forma tego samego lematu: odległość edycyjna na znakach
                  <= max(1, round(0.3 * długość słowa referencji)) („tirads” -> „tirats”, „miąższ” -> „miosz”,
                  „dopplerowskim” -> „doplerowskim”); zwykle model usłyszał termin, ale nie zna jego pisowni;
                  zmiana przedrostka znaczeniowego (nie-, hipo-, hiper-, izo-, normo-) jest zawsze podmianą,
  substitution  – inne słowo,
  deletion      – słowo pominięte.
Terminy to formy z leksykonu eval/lexicon/radiology_terms.tsv (adnotacja ręczna); pozostałe słowa
bez cyfr to słownictwo ogólne (grupa porównawcza).

Metryki:
  TER (ang. term error rate)   = (form + segmentation + substitution + deletion) / wystąpienia terminów
  TER-L (wersja łagodna)       = (near_miss + substitution + deletion) / wystąpienia terminów
                                 (forma fleksyjna i podział na słowa nie są liczone jako błąd)
  GWER (słowa ogólne)          = to samo co TER, ale dla słów spoza leksykonu (bez liczb)
95% CI z bootstrapu po wypowiedziach (1000 losowań, seed 0).

Wyjście: results/terms/*.csv, wykres assets/terms_vs_frequency.svg i tabela term_tokens
w results/results.sqlite.

Użycie (z katalogu eval/):  uv run python terms.py
"""
import collections, csv, json, os, sqlite3, sys
import numpy as np
import jiwer
import simplemma
from wordfreq import zipf_frequency

sys.path.insert(0, os.path.dirname(__file__))
from asr_eval import data, textnorm
from asr_eval.metrics import _ci
from asr_eval.plan import PLAN

RES = os.path.join(data.ROOT, "results")
OUT = os.path.join(RES, "terms")
LEX = os.path.join(os.path.dirname(__file__), "lexicon", "radiology_terms.tsv")
STATUSES = ("correct", "form", "segmentation", "near_miss", "substitution", "deletion")
CLASSES = ("anatomy", "descriptor", "pathology", "acronym")
REF_TYPOS = {"wiekości", "hiperechegennicznym"}   # błędy pisowni w referencji: wykluczone z obu grup


def load_lexicon():
    lex = {}
    for line in open(LEX, encoding="utf-8"):
        if line.startswith("#") or line.startswith("form\t") or not line.strip():
            continue
        form, lemma, cls = line.rstrip("\n").split("\t")
        lex[form] = (lemma, cls)
    return lex


LEXICON = load_lexicon()


def lemma(tok):
    if tok in LEXICON:
        return LEXICON[tok][0]
    return simplemma.lemmatize(tok, lang="pl").lower()


def same_lemma(ref, hyp):
    """Ten sam lemat (leksykon dla form z referencji, simplemma dla pozostałych)."""
    if not hyp or any(c.isdigit() for c in hyp):
        return False
    return lemma(ref) == lemma(hyp)


def edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


MEANING_PREFIXES = ("hiper", "hipo", "normo", "izo", "nie")


def _prefix(w):
    return next((p for p in MEANING_PREFIXES if w.startswith(p)), "")


def near_miss(ref, hyp):
    """Bliski zapis, o ile nie zmienia się przedrostek niosący znaczenie (nie-, hipo-, hiper-, izo-, normo-):
    „niejednorodny” -> „jednorodne” to zmiana sensu, więc liczy się jako podmiana."""
    if not hyp or _prefix(ref) != _prefix(hyp):
        return False
    return edit_distance(ref, hyp) <= max(1, round(0.3 * len(ref)))


def token_fates(ref, hyp):
    """Lista (ref_tok, status, hyp_text) dla każdego słowa referencji."""
    out = jiwer.process_words(ref, hyp if hyp else "")
    r, h = out.references[0], out.hypotheses[0]
    m = [None] * len(r)            # ref_idx -> ("equal"|"S"|"D", hyp_idx)
    inserted = set()
    for ch in out.alignments[0]:
        if ch.type == "insert":
            inserted.update(range(ch.hyp_start_idx, ch.hyp_end_idx))
            continue
        for k, i in enumerate(range(ch.ref_start_idx, ch.ref_end_idx)):
            j = ch.hyp_start_idx + k if ch.type in ("equal", "substitute") else None
            m[i] = ({"equal": "equal", "substitute": "S", "delete": "D"}[ch.type], j)
    fates = []
    for i, tok in enumerate(r):
        kind, j = m[i]
        if kind == "equal":
            fates.append((tok, "correct", tok)); continue
        hj = h[j] if j is not None else None
        # segmentacja: rozbicie słowa referencji na dwa słowa hipotezy (drugie jako wstawka)
        if j is not None:
            if j + 1 < len(h) and (j + 1) in inserted and h[j] + h[j + 1] == tok:
                fates.append((tok, "segmentation", h[j] + " " + h[j + 1])); continue
            if j - 1 >= 0 and (j - 1) in inserted and h[j - 1] + h[j] == tok:
                fates.append((tok, "segmentation", h[j - 1] + " " + h[j])); continue
        # segmentacja: sklejenie dwóch słów referencji w jedno słowo hipotezy
        joined = False
        for a, b in ((i - 1, i), (i, i + 1)):
            if a < 0 or b >= len(r):
                continue
            for x in (a, b):
                jx = m[x][1]
                if jx is not None and h[jx] == r[a] + r[b]:
                    fates.append((tok, "segmentation", h[jx])); joined = True; break
            if joined:
                break
        if joined:
            continue
        if kind == "D":
            fates.append((tok, "deletion", None))
        elif same_lemma(tok, hj):
            fates.append((tok, "form", hj))
        elif near_miss(tok, hj):
            fates.append((tok, "near_miss", hj))
        else:
            fates.append((tok, "substitution", hj))
    return fates


def group_of(tok):
    if tok in REF_TYPOS or any(c.isdigit() for c in tok) or tok == "x":
        return None
    return LEXICON[tok][1] if tok in LEXICON else "general"


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []                                           # wszystkie wystąpienia
    runs = []
    for spec in PLAN:
        path = os.path.join(RES, spec["id"], "hyp.jsonl")
        if not os.path.exists(path):
            continue
        recs = [json.loads(l) for l in open(path, encoding="utf-8")]
        runs.append((spec["id"], spec["name"]))
        for u, rec in enumerate(recs):
            ref, hyp = textnorm.normalize(rec["ref"]), textnorm.normalize(rec["hyp"])
            for pos, (tok, st, hy) in enumerate(token_fates(ref, hyp)):
                g = group_of(tok)
                if g:
                    rows.append(dict(run_id=spec["id"], recording_id=rec["id"], utt=u, ref_pos=pos, ref_tok=tok,
                                     lemma=lemma(tok), cls=g, is_term=int(g != "general"), status=st, hyp_text=hy))
    print(f"{len(runs)} przebiegów, {len(rows)} wystąpień słów")

    # --- zestawienie per model -------------------------------------------------------------------
    def rates(sub, n_utt):
        err_strict = np.zeros(n_utt); err_len = np.zeros(n_utt); tot = np.zeros(n_utt)
        cnt = collections.Counter()
        for r in sub:
            tot[r["utt"]] += 1; cnt[r["status"]] += 1
            err_strict[r["utt"]] += r["status"] != "correct"
            err_len[r["utt"]] += r["status"] in ("near_miss", "substitution", "deletion")
        n = tot.sum()
        return n, cnt, 100 * err_strict.sum() / n, _ci(err_strict, tot), 100 * err_len.sum() / n

    by_run = collections.defaultdict(list)
    for r in rows:
        by_run[r["run_id"]].append(r)
    runs = [(rid, name) for rid, name in runs if by_run[rid]]   # pomiń puste przebiegi (np. usługa bez środków)
    summary, by_class = [], []
    for rid, name in runs:
        sub = by_run[rid]
        n_utt = max(r["utt"] for r in sub) + 1
        terms = [r for r in sub if r["is_term"]]
        gen = [r for r in sub if not r["is_term"]]
        n, cnt, ter, ci, ter_l = rates(terms, n_utt)
        ng, _, gwer, gci, gwer_l = rates(gen, n_utt)
        summary.append(dict(run_id=rid, name=name, n_terms=int(n), ter=round(ter, 2), ter_ci_lo=ci[0], ter_ci_hi=ci[1],
                            ter_lenient=round(ter_l, 2),
                            **{f"share_{s}": round(100 * cnt[s] / n, 2) for s in STATUSES[1:]},
                            n_general=int(ng), gwer=round(gwer, 2), gwer_ci_lo=gci[0], gwer_ci_hi=gci[1],
                            gwer_lenient=round(gwer_l, 2), ter_to_gwer=round(ter / gwer, 2) if gwer else None))
        for c in CLASSES:
            cs = [r for r in terms if r["cls"] == c]
            nc, cc, tc, cic, tlc = rates(cs, n_utt)
            by_class.append(dict(run_id=rid, name=name, cls=c, n=int(nc), ter=round(tc, 2), ter_ci_lo=cic[0],
                                 ter_ci_hi=cic[1], ter_lenient=round(tlc, 2)))

    def write(fname, recs):
        with open(os.path.join(OUT, fname), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(recs[0].keys())); w.writeheader(); w.writerows(recs)

    summary.sort(key=lambda d: d["ter"])
    write("summary.csv", summary)
    write("by_class.csv", by_class)

    # --- per lemat: odsetek błędów w każdym modelu + najczęstsza pomyłka ---------------------------
    lem = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    conf = collections.Counter()
    meta = {}
    for r in rows:
        if not r["is_term"]:
            continue
        meta[r["lemma"]] = r["cls"]
        e = lem[r["lemma"]][r["run_id"]]
        e[1] += 1; e[0] += r["status"] != "correct"
        if r["status"] != "correct":
            conf[(r["run_id"], r["ref_tok"], r["status"], r["hyp_text"] or "")] += 1
    best = [s["run_id"] for s in summary[:3]]
    lemma_rows = []
    for l, per in lem.items():
        n = next(iter(per.values()))[1]
        d = dict(lemma=l, cls=meta[l], n=n, zipf=zipf_frequency(l, "pl"))
        for rid, _ in runs:
            d[rid] = round(100 * per[rid][0] / per[rid][1], 1)
        d["err_best3"] = round(np.mean([d[b] for b in best]), 1)   # średnia z 3 modeli o najniższym TER
        d["err_all"] = round(  # średnia ze wszystkich modeli poza kontrolą negatywną
            np.mean([d[rid] for rid, _ in runs if rid != "google-medasr"]), 1)
        lemma_rows.append(d)
    lemma_rows.sort(key=lambda d: (-d["err_best3"], -d["n"]))
    write("by_lemma.csv", lemma_rows)
    write("confusions.csv", [dict(run_id=a, ref=b, status=c, hyp=d, n=n) for (a, b, c, d), n in conf.most_common()])

    # --- błąd vs częstość słowa w ogólnej polszczyźnie (wordfreq, skala Zipfa) ----------------------
    bins = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 8)]
    zrows = []
    for rid, name in runs:
        if rid == "google-medasr":
            continue
        for lo, hi in bins:
            for grp in ("term", "general"):
                s = [r for r in by_run[rid] if (r["is_term"] == (grp == "term"))
                     and lo <= zipf_frequency(r["ref_tok"], "pl") < hi]
                if s:
                    zrows.append(dict(run_id=rid, group=grp, zipf_lo=lo, zipf_hi=hi, n=len(s),
                                      err=round(100 * sum(r["status"] != "correct" for r in s) / len(s), 2)))
    write("by_zipf.csv", zrows)
    # po jednym najlepszym modelu z trzech rodzin: Whisper, NVIDIA, Qwen
    plot_zipf(zrows, ["whisper-large-v3", "nvidia-parakeet-tdt-v3", "qwen3-asr-1.7b"], dict(runs))

    # --- tabela w bazie wyników ------------------------------------------------------------------
    con = sqlite3.connect(os.path.join(RES, "results.sqlite"))
    con.executescript("""DROP TABLE IF EXISTS term_tokens;
      CREATE TABLE term_tokens(run_id TEXT, recording_id TEXT, ref_pos INTEGER, ref_tok TEXT, lemma TEXT,
        cls TEXT, is_term INTEGER, status TEXT, hyp_text TEXT);
      CREATE INDEX ix_tt ON term_tokens(run_id, is_term, status);""")
    con.executemany("INSERT INTO term_tokens VALUES (?,?,?,?,?,?,?,?,?)",
                    [(r["run_id"], r["recording_id"], r["ref_pos"], r["ref_tok"], r["lemma"], r["cls"],
                      r["is_term"], r["status"], r["hyp_text"]) for r in rows])
    con.commit(); con.close()

    for s in summary:
        print(f'{s["name"]:42s} TER {s["ter"]:6.2f} [{s["ter_ci_lo"]}-{s["ter_ci_hi"]}]  TER-L {s["ter_lenient"]:6.2f}'
              f'  GWER {s["gwer"]:6.2f}  ratio {s["ter_to_gwer"]}')


def plot_zipf(zrows, ids, names):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = ["#2a6fdb", "#e07a1f", "#3a9d5d"]
    for c, rid in zip(colors, ids):
        for grp, ls, mk in (("term", "-", "o"), ("general", "--", "s")):
            s = [r for r in zrows if r["run_id"] == rid and r["group"] == grp and r["n"] >= 50]
            ax.plot([(r["zipf_lo"] + min(r["zipf_hi"], 6)) / 2 for r in s], [r["err"] for r in s], ls=ls, marker=mk,
                    color=c, label=f'{names[rid]} – {"terminy" if grp == "term" else "słowa ogólne"}')
    ax.set_xlabel("Częstość słowa w ogólnej polszczyźnie (skala Zipfa, wordfreq)")
    ax.set_ylabel("Odsetek błędnie rozpoznanych wystąpień [%]")
    ax.grid(alpha=.3); ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(data.ROOT, "assets", "terms_vs_frequency.svg"))


if __name__ == "__main__":
    main()
