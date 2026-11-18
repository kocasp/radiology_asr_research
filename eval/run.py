"""Runner ewaluacji ASR. Uruchamia modele z planu po kolei i na bieżąco zapisuje results/progress.json,
który czyta strona dashboard/index.html.

Użycie (z katalogu eval/):
  uv run python run.py                      # wszystkie modele z planu, które da się uruchomić
  uv run python run.py --only whisper-medium medical-pl-nas
  uv run python run.py --limit 20           # test dymny na 20 nagraniach (osobny katalog wyników)
Wyniki: results/<id>/hyp.jsonl (wznawialne), results/<id>/metrics.json, results/summary.csv
"""
import argparse, collections, csv, datetime as dt, json, os, platform, sys, time, traceback

sys.path.insert(0, os.path.dirname(__file__))
from asr_eval import data, metrics, textnorm
from asr_eval.plan import PLAN

RES = os.path.join(data.ROOT, "results")

# klucze API / token HF z eval/.env (plik poza repo); nie nadpisuje zmiennych już ustawionych
_ENV = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_ENV):
    for _l in open(_ENV):
        if "=" in _l and not _l.lstrip().startswith("#"):
            _k, _v = _l.strip().split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"'))
PROG = os.path.join(RES, "progress.json")


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


class Progress:
    def __init__(self, items, smoke):
        os.makedirs(RES, exist_ok=True)
        old = json.load(open(PROG)) if os.path.exists(PROG) else {}
        self.p = dict(
            title="Błędy modeli ASR w dyktowaniu polskich opisów diagnostyki obrazowej",
            updated=now(), state="running", smoke=smoke,
            test_set=dict(n=len(items), hours=round(sum(i["dur"] for i in items) / 3600, 2),
                          speakers=len({i["speaker"] for i in items}),
                          desc="ADMEDVOICE, radiologia (02-001 tarczyca, 02-003 głowa–szyja), tylko głos naturalny"),
            env=dict(machine=f"{platform.machine()} · {platform.platform()}", python=platform.python_version()),
            plan=[], current=None, results=old.get("results", {}) if not smoke else {}, log=old.get("log", [])[-40:])
        old_plan = {e["id"]: e for e in old.get("plan", [])}
        for s in PLAN:
            o = old_plan.get(s["id"], {})
            self.p["plan"].append(dict(
                id=s["id"], name=s["name"], group=s["group"], mode=s["mode"], params=s.get("params"),
                model=s["model"] + (f" + LoRA {os.path.basename(s['lora'])}" if s.get("lora") else ""),
                note=s.get("note"), leak_risk=s.get("leak_risk"),
                status="done" if s["id"] in self.p["results"] else o.get("status", "pending") if o.get("status") != "running" else "pending",
                reason=o.get("reason")))

    def entry(self, mid):
        return next(e for e in self.p["plan"] if e["id"] == mid)

    def log(self, msg):
        self.p["log"].append(dict(t=now(), msg=msg)); self.p["log"] = self.p["log"][-60:]
        print(msg, flush=True); self.save()

    def save(self):
        self.p["updated"] = now()
        tmp = PROG + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.p, f, ensure_ascii=False, indent=1)
        os.replace(tmp, PROG)


CLOUD_OK = False   # ustawiane flagą --cloud (płatne wywołania tylko po akceptacji kosztu)


IMPLEMENTED = {"hf_whisper", "hf_ctc", "hf_mms", "nemo", "cloud", "qwen_asr"}
CLOUD_IMPLEMENTED = {"openai-whisper-1", "openai-gpt-4o-transcribe", "elevenlabs-scribe", "deepgram-nova-3",
                     "azure-speech", "speechmatics", "soniox", "assemblyai", "gemini-transcribe"}


def blocked_reason(spec):
    if spec["engine"] not in IMPLEMENTED:
        return spec.get("gated") or f"Adapter {spec['engine']} w przygotowaniu."
    if spec["engine"] == "cloud":
        if not os.environ.get(spec.get("key", "")):
            return f"Brak klucza {spec.get('key')} w eval/.env."
        if spec["id"] not in CLOUD_IMPLEMENTED:
            return "Adapter w przygotowaniu."
        if not CLOUD_OK:
            return "Klucz jest. Usługa płatna: uruchamiana dopiero po akceptacji kosztu (run.py --cloud)."
        return None
    if spec.get("gated"):
        try:
            from huggingface_hub import get_token, model_info
            if not get_token():
                return spec["gated"]
            model_info(spec["model"], files_metadata=False)
            from huggingface_hub import hf_hub_download
            hf_hub_download(spec["model"], "config.json")          # sprawdza faktyczny dostęp do plików
        except Exception as ex:
            return f"{spec['gated']} ({type(ex).__name__})"
    if spec["engine"] == "nemo" and "nemo" not in sys.prefix:
        return "Uruchamiany w osobnym środowisku NeMo (eval/.venv-nemo)."
    if spec["engine"] == "qwen_asr" and "qwen" not in sys.prefix:
        return "Uruchamiany w osobnym środowisku (eval/.venv-qwen)."
    if spec.get("lora") and not os.path.exists(spec["lora"]):
        return f"Brak adaptera LoRA w {spec['lora']}"
    return None


def decoding_label(spec):
    if spec["engine"] == "hf_whisper":
        return "greedy, language=pl, task=transcribe"
    if spec["engine"] == "cloud":
        if spec["id"] == "gemini-transcribe":
            return "API generateContent, neutralna instrukcja „przepisz dosłownie”, bez słownictwa"
        return "API, language=pl, bez promptu/słownika"
    if spec["engine"] == "nemo":
        return "greedy (domyślny dekoder NeMo), bez LM"
    return "beam search CTC + KenLM (ogólny polski)" if spec.get("lm") else "greedy CTC, bez LM"


def score(spec, recs, proc_s, outdir):
    """Liczy wszystkie metryki z surowych transkrypcji i zapisuje metrics.json + hyp_scored.jsonl."""
    stats, stats_n = [], []
    for r in recs:
        r["ref_norm"], r["hyp_norm"] = textnorm.normalize(r["ref"]), textnorm.normalize(r["hyp"])
        stats.append(metrics.utterance_stats(r["ref_norm"], r["hyp_norm"]))
        stats_n.append(metrics.utterance_stats(textnorm.normalize_spoken(r["ref"]), textnorm.normalize_spoken(r["hyp"])))
    agg = metrics.aggregate(stats, sum(r["dur"] for r in recs), proc_s)
    agg_n = metrics.aggregate(stats_n, 1, 0)
    agg["wer_num"], agg["wer_num_ci"] = agg_n["wer"], agg_n["wer_ci"]
    subs = collections.Counter((o[1], o[2]) for s in stats if s for o in s["ops"] if o[0] == "S")
    ins = collections.Counter(o[2] for s in stats if s for o in s["ops"] if o[0] == "I")
    dels = collections.Counter(o[1] for s in stats if s for o in s["ops"] if o[0] == "D")
    worst = sorted(((s["S"] + s["D"] + s["I"]) / s["n_ref"], r["ref"], r["hyp"]) for r, s in zip(recs, stats) if s)[::-1][:12]
    agg.update(top_subs=[[a, b, n] for (a, b), n in subs.most_common(15)],
               top_ins=[[a, n] for a, n in ins.most_common(10)], top_dels=[[a, n] for a, n in dels.most_common(10)],
               worst=[dict(err=round(w * 100), ref=r, hyp=h) for w, r, h in worst],
               model=spec["model"], lm=spec.get("lm"), finished=now(), decoding=decoding_label(spec))
    json.dump(agg, open(os.path.join(outdir, "metrics.json"), "w"), ensure_ascii=False, indent=1)
    with open(os.path.join(outdir, "hyp_scored.jsonl"), "w", encoding="utf-8") as f:
        for r, s, sn in zip(recs, stats, stats_n):
            f.write(json.dumps(dict(r, S=s["S"], D=s["D"], I=s["I"], n_ref=s["n_ref"],
                                    wer_num=round(100 * (sn["S"] + sn["D"] + sn["I"]) / sn["n_ref"], 2)), ensure_ascii=False) + "\n")
    return agg



def run_model(spec, items, prog, outdir):
    from asr_eval import engines
    mid = spec["id"]
    os.makedirs(outdir, exist_ok=True)
    hyp_path = os.path.join(outdir, "hyp.jsonl")
    done = {}
    if os.path.exists(hyp_path):
        for line in open(hyp_path, encoding="utf-8"):
            r = json.loads(line); done[r["id"]] = r
    e = prog.entry(mid); e["status"] = "running"; e["reason"] = None
    prog.log(f"▶ {spec['name']}: ładowanie modelu ({spec['model']})")
    t_load = time.time()
    if spec["engine"] == "nemo":
        eng = __import__("asr_eval.nemo_engine", fromlist=["x"]).NeMo(spec)
    elif spec["engine"] == "qwen_asr":
        from asr_eval.qwen_engine import QwenASR; eng = QwenASR(spec)
    elif spec["engine"] == "cloud":
        from asr_eval.cloud import Cloud; eng = Cloud(spec)
    else:
        eng = engines.make(spec)
    prog.log(f"  model załadowany w {time.time() - t_load:.0f} s; transkrypcja {len(items)} nagrań")
    todo = [i for i in items if i["id"] not in done]
    proc_s = sum(r["sec"] for r in done.values())
    started = time.time()
    last = collections.deque([dict(ref=r["ref"], hyp=r["hyp"]) for r in list(done.values())[-4:]], maxlen=4)
    with open(hyp_path, "a", encoding="utf-8") as fh:
        for b in range(0, len(todo), eng.batch):
            batch = todo[b:b + eng.batch]
            audios = [data.load_16k(i["path"]) for i in batch]
            t0 = time.time()
            hyps = eng.transcribe(audios)
            sec = time.time() - t0
            proc_s += sec
            for i, h in zip(batch, hyps):
                rec = dict(id=i["id"], speaker=i["speaker"], cat=i["cat"], dur=i["dur"], ref=i["ref"], hyp=h,
                           sec=round(sec * i["dur"] / max(sum(x["dur"] for x in batch), 1e-6), 3))
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); done[i["id"]] = rec
                last.append(dict(ref=i["ref"], hyp=h))
            fh.flush()
            n = len(done); el = time.time() - started; rate = (n - (len(items) - len(todo))) / max(el, 1e-6)
            prog.p["current"] = dict(id=mid, name=spec["name"], done=n, total=len(items), elapsed_s=round(el),
                                     eta_s=round((len(items) - n) / rate) if rate else None,
                                     audio_done_h=round(sum(r["dur"] for r in done.values()) / 3600, 2),
                                     last=list(last))
            prog.save()
    # metryki
    recs = [done[i["id"]] for i in items]
    agg = score(spec, recs, proc_s, outdir)
    prog.p["results"][mid] = agg
    e["status"] = "done"; prog.p["current"] = None
    prog.log(f"✔ {spec['name']}: WER {agg['wer']}% [{agg['wer_ci'][0]}–{agg['wer_ci'][1]}], CER {agg['cer']}%, RTF {agg['rtf']}")
    del eng
    try:
        import gc, torch; gc.collect(); torch.mps.empty_cache()
    except Exception:
        pass


def write_summary(prog):
    rows = []
    for e in prog.p["plan"]:
        r = prog.p["results"].get(e["id"])
        if r:
            rows.append(dict(id=e["id"], name=e["name"], mode=e["mode"], wer=r["wer"], wer_ci_lo=r["wer_ci"][0],
                             wer_ci_hi=r["wer_ci"][1], cer=r["cer"], num_err=r["num_err"], neg_err=r["neg_err"],
                             side_err=r["side_err"], ccer=r.get("ccer"), ccer_n=r.get("ccer_n"),
                             S=r["S"], D=r["D"], I=r["I"], long_ins=r["long_ins"],
                             utt_perfect=r["utt_perfect"], rtf=r["rtf"], leak_risk=bool(e.get("leak_risk"))))
    if rows:
        with open(os.path.join(RES, "summary.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--cloud", action="store_true", help="pozwól na płatne wywołania usług chmurowych")
    a = ap.parse_args()
    global RES, PROG, CLOUD_OK
    CLOUD_OK = a.cloud
    if a.limit:
        RES = os.path.join(data.ROOT, "results", f"_smoke{a.limit}"); PROG = os.path.join(RES, "progress.json")
    items = data.test_set(a.limit)
    prog = Progress(items, smoke=bool(a.limit))
    prog.log(f"Start: {len(items)} nagrań, {prog.p['test_set']['hours']} h audio")
    for spec in PLAN:
        if a.only and spec["id"] not in a.only:
            continue
        e = prog.entry(spec["id"])
        if e["status"] == "done":
            continue
        why = blocked_reason(spec)
        if why:
            e["status"] = "blocked"; e["reason"] = why; prog.save(); continue
        try:
            run_model(spec, items, prog, os.path.join(RES, spec["id"]))
        except Exception as ex:
            e["status"] = "failed"; e["reason"] = f"{type(ex).__name__}: {ex}"[:300]; prog.p["current"] = None
            prog.log(f"✖ {spec['name']}: {e['reason']}"); traceback.print_exc()
        write_summary(prog)
        if not a.limit:
            try:
                import build_results_db; build_results_db.main()
            except Exception as ex:
                prog.log(f"⚠ baza wyników: {ex}")
    prog.p["state"] = "idle"; prog.log("Koniec przebiegu.")


if __name__ == "__main__":
    main()
