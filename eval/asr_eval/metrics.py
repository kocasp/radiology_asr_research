"""Metryki: WER, CER (z 95% CI z bootstrapu po wypowiedziach) i kategorie błędów istotnych klinicznie.

Kategorie liczone na tokenach referencji (po normalizacji): token jest „trafiony”, gdy w wyrównaniu
jiwer należy do fragmentu `equal`; podmiana lub pominięcie = błąd.
- num:  tokeny z cyfrą (wymiary, objętości, numery kręgów)
- neg:  zaprzeczenia: nie, bez, brak
- side: strona ciała: prawy/lewy (wszystkie formy) oraz prawo-/lewostronny
Wstawienia: liczba słów wstawionych przez model oraz „długie wstawki” (>=3 kolejne wstawione słowa
w jednym miejscu) — przybliżenie halucynacji.
"""
import re
import numpy as np
import jiwer

SIDE = re.compile(r"^(praw|lew)(y|a|e|ego|ej|ym|ą|ych|ymi|emu|o)$|^(prawo|lewo)stronn\w*$")
NEG = {"nie", "bez", "brak"}


def cat_of(tok):
    if any(c.isdigit() for c in tok):
        return "num"
    if tok in NEG:
        return "neg"
    if SIDE.match(tok):
        return "side"
    return None


def utterance_stats(ref, hyp):
    """Statystyki jednej wypowiedzi (ref/hyp już znormalizowane)."""
    if not ref:
        return None
    out = jiwer.process_words(ref, hyp if hyp else "")
    r_tok, h_tok = out.references[0], out.hypotheses[0]
    cats = {k: [0, 0] for k in ("num", "neg", "side")}   # [błędy, wszystkie]
    long_ins = 0
    ops = []
    for ch in out.alignments[0]:
        if ch.type == "insert":
            n = ch.hyp_end_idx - ch.hyp_start_idx
            long_ins += n >= 3
            ops.append(("I", None, " ".join(h_tok[ch.hyp_start_idx:ch.hyp_end_idx])))
            continue
        for i in range(ch.ref_start_idx, ch.ref_end_idx):
            c = cat_of(r_tok[i])
            if c:
                cats[c][1] += 1
                cats[c][0] += ch.type != "equal"
        if ch.type != "equal":
            ops.append(({"substitute": "S", "delete": "D"}[ch.type],
                        " ".join(r_tok[ch.ref_start_idx:ch.ref_end_idx]),
                        " ".join(h_tok[ch.hyp_start_idx:ch.hyp_end_idx])))
    cer = jiwer.process_characters(ref, hyp if hyp else "")
    return dict(n_ref=len(r_tok), S=out.substitutions, D=out.deletions, I=out.insertions,
                char_err=cer.substitutions + cer.deletions + cer.insertions, n_char=len(ref),
                cats=cats, long_ins=long_ins, ops=ops)


def _ci(err, tot, iters=1000, seed=0):
    rng = np.random.default_rng(seed)
    n = len(err)
    idx = rng.integers(0, n, size=(iters, n))
    vals = err[idx].sum(1) / np.maximum(tot[idx].sum(1), 1) * 100
    return [round(float(np.percentile(vals, 2.5)), 2), round(float(np.percentile(vals, 97.5)), 2)]


def aggregate(stats, audio_s, proc_s):
    stats = [s for s in stats if s]
    werr = np.array([s["S"] + s["D"] + s["I"] for s in stats], float)
    wtot = np.array([s["n_ref"] for s in stats], float)
    cerr = np.array([s["char_err"] for s in stats], float)
    ctot = np.array([s["n_char"] for s in stats], float)
    res = dict(
        n_utt=len(stats), n_words=int(wtot.sum()),
        wer=round(float(werr.sum() / wtot.sum() * 100), 2), wer_ci=_ci(werr, wtot),
        cer=round(float(cerr.sum() / ctot.sum() * 100), 2), cer_ci=_ci(cerr, ctot),
        S=int(sum(s["S"] for s in stats)), D=int(sum(s["D"] for s in stats)), I=int(sum(s["I"] for s in stats)),
        long_ins=int(sum(s["long_ins"] for s in stats)),
        utt_perfect=round(100 * sum((s["S"] + s["D"] + s["I"]) == 0 for s in stats) / len(stats), 1),
        audio_s=round(audio_s, 1), proc_s=round(proc_s, 1), rtf=round(proc_s / audio_s, 3) if audio_s else None,
    )
    for k in ("num", "neg", "side"):
        e = sum(s["cats"][k][0] for s in stats); t = sum(s["cats"][k][1] for s in stats)
        res[f"{k}_err"] = round(100 * e / t, 1) if t else None
        res[f"{k}_n"] = t
    return res


def alignment_ops(ref, hyp):
    """Szczegółowa lista błędów jednej wypowiedzi (do bazy wyników).
    Zwraca listę dict(op, ref_pos, hyp_pos, ref_text, hyp_text, n_ref, n_hyp, category, long_ins)."""
    out = jiwer.process_words(ref, hyp if hyp else "")
    r_tok, h_tok = out.references[0], out.hypotheses[0]
    ops = []
    for ch in out.alignments[0]:
        if ch.type == "equal":
            continue
        rt = r_tok[ch.ref_start_idx:ch.ref_end_idx]
        ht = h_tok[ch.hyp_start_idx:ch.hyp_end_idx]
        if ch.type == "insert":
            cat = "insertion"
        else:
            cats = {cat_of(t) for t in rt} - {None}
            cat = ",".join(sorted(cats)) if cats else "other"
        ops.append(dict(op={"substitute": "S", "delete": "D", "insert": "I"}[ch.type],
                        ref_pos=ch.ref_start_idx, hyp_pos=ch.hyp_start_idx,
                        ref_text=" ".join(rt) or None, hyp_text=" ".join(ht) or None,
                        n_ref=len(rt), n_hyp=len(ht), category=cat,
                        long_ins=int(ch.type == "insert" and len(ht) >= 3)))
    return ops
