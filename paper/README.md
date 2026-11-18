# paper/ — LaTeX (IEEEtran) preprint

`main.pdf` is the compiled paper (6 pages, US Letter), ready to upload to Zenodo.

## Build

Everything is self-contained except the TeX engine. The project uses **tectonic**
(Homebrew: `brew install tectonic`), which fetches the required LaTeX packages on demand.

```bash
cd paper
tectonic main.tex        # -> main.pdf
```

Files:
- `main.tex` — the paper (IEEE conference template, `\documentclass[conference]{IEEEtran}`),
- `fig_terms_vs_freq.pdf` — Figure 1 (generated from `results/terms/by_zipf.csv`),
- `main.pdf` — compiled output.

To regenerate the figure from the current results (from the repo root):

```python
# reads results/terms/by_zipf.csv and writes paper/fig_terms_vs_freq.pdf
# (see the plotting snippet used to produce it)
```

## Zenodo upload (suggested metadata)

- **Resource type:** Publication → Preprint
- **Title:** Benchmarking Off-the-Shelf ASR Systems on Polish Radiology Dictation: Terminology, Numbers, and Clinically Critical Errors
- **Creator:** Strojny, Konrad (add ORCID/affiliation)
- **Description:** copy the paper abstract
- **Keywords:** automatic speech recognition; Polish; radiology; medical dictation; terminology; benchmark; speech-to-text
- **License:** CC BY 4.0 (adjust as desired)
- **Related identifiers:** *is supplemented by* the code repository `https://github.com/kocasp/radiology_asr_research`; the dataset ADMEDVOICE, DOI `10.34740/kaggle/ds/6698205`
- **Files:** `main.pdf` (and optionally the LaTeX sources + figure)
