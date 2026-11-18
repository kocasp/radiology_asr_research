# gh-pages — interactive results browser

Static landing page with an interactive browser of the ASR benchmark. It runs fully in the
browser (no server): `sql.js` loads a slim SQLite database and computes word-level alignments
on the fly.

## What you can do

- **Models overview** — sortable table of all 19 systems (WER, WER-N, CER, TER, GWER, numbers,
  negations, body side, RTF).
- **By recording** — pick a dictated phrase (search by id or reference text) and see how **all
  models** transcribed it, ranked by WER; click a model to see the word-level diff (substitutions,
  deletions, insertions) with numbers / negations / body side underlined.
- **By model** — pick a model and browse all its 939 transcriptions (worst first), filter by text,
  inspect the diff, or jump to the cross-model comparison for that recording.

## Files

```
gh-pages/
├── index.html            landing page + app shell
├── style.css             styling (dark theme)
├── app.js                sql.js loading, views, word alignment/diff
├── data/benchmark.sqlite slim DB (runs + utterances; ~10 MB)
├── vendor/sql-wasm.{js,wasm}   sql.js runtime (vendored, works offline)
├── build_data.py         rebuilds data/benchmark.sqlite from results/results.sqlite
└── .nojekyll
```

The shipped database contains only `runs` and `utterances` (with normalised texts). The heavier
`errors` and `term_tokens` tables are excluded; the diff is recomputed in JavaScript from
`ref_norm`/`hyp_norm`.

## Rebuild the data

After re-running the evaluation (which regenerates `results/results.sqlite`):

```bash
cd eval && uv run python build_results_db.py && cd ..
python3 gh-pages/build_data.py
```

## Deploy on GitHub Pages

The repository ships `.github/workflows/pages.yml`, which publishes the contents of `gh-pages/`.
One-time setup: **Settings → Pages → Build and deployment → Source: GitHub Actions**. After that,
every push that touches `gh-pages/` redeploys the site.

Local preview:

```bash
cd gh-pages && python3 -m http.server 8000   # open http://localhost:8000
```

`sql.js` is loaded from `vendor/` and the WASM file is fetched with a relative path, so the page
also works when opened from a sub-path such as `/repo/gh-pages/` on a project Pages site.
