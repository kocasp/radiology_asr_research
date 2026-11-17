"""Przelicza metryki wszystkich ukończonych przebiegów z zapisanych transkrypcji (results/<id>/hyp.jsonl),
bez ponownej transkrypcji. Uruchamiać po zmianie normalizacji lub metryk, gdy nie działa żaden runner.

Użycie (z katalogu eval/):  uv run python rescore.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import run
from asr_eval import data
from asr_eval.plan import PLAN

items = {i["id"]: i for i in data.test_set()}
prog = json.load(open(run.PROG)) if os.path.exists(run.PROG) else {"results": {}, "plan": []}
for spec in PLAN:
    d = os.path.join(run.RES, spec["id"]); h = os.path.join(d, "hyp.jsonl")
    if not os.path.exists(h):
        continue
    recs = {}
    for line in open(h, encoding="utf-8"):
        r = json.loads(line); recs[r["id"]] = r
    if len(recs) < len(items):
        print(f"{spec['id']}: niekompletny ({len(recs)}/{len(items)}), pomijam"); continue
    old = json.load(open(os.path.join(d, "metrics.json"))) if os.path.exists(os.path.join(d, "metrics.json")) else {}
    agg = run.score(spec, [recs[i] for i in items], sum(r["sec"] for r in recs.values()), d)
    agg["finished"] = old.get("finished", agg["finished"])
    json.dump(agg, open(os.path.join(d, "metrics.json"), "w"), ensure_ascii=False, indent=1)
    prog["results"][spec["id"]] = agg
    for e in prog.get("plan", []):
        if e["id"] == spec["id"]:
            e["status"] = "done"; e["reason"] = None; e["note"] = spec.get("note"); e["leak_risk"] = spec.get("leak_risk")
    print(f"{spec['id']}: WER {old.get('wer')} -> {agg['wer']} | WER-N {agg['wer_num']}")
prog["updated"] = run.now()
json.dump(prog, open(run.PROG, "w"), ensure_ascii=False, indent=1)
import build_results_db; build_results_db.main()
