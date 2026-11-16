"""Generuje assets/banner.svg — baner repozytorium (deterministyczny, bez zależności).

Ilustracja: tekst podyktowany (REF) i rozpoznany przez ASR, wyrównane słowo do słowa, z czterema
typami błędów (podmiana strony ciała, zły wymiar, zgubione zaprzeczenie, wstawienie w ciszy).
"""
import math, random, os

W, H = 1280, 390
X0, X1 = 64, 1216
TX = 150                     # początek kolumn tekstu
CH = 12                      # szerokość znaku (wymuszona przez textLength)
GAP = 18
CY, AMP = 214, 18            # oś i amplituda fali
STEP, BW = 6, 3
Y_REF, Y_ASR, Y_TAG = 272, 306, 326

# (ref, asr, typ błędu); None = brak słowa
COLS = [("Płat", "Płat", None), ("prawy", "lewy", "S"), ("14x12x45", "14x12x4", "S"), ("mm,", "mm,", None),
        ("bez", None, "D"), ("zmian", "zmian", None), ("ogniskowych.", "ogniskowych.", None), (None, "Dziękuję.", "I")]
N_REF = sum(r is not None for r, _, _ in COLS)
LABEL = {"S": "podmiana", "D": "pominięcie", "I": "wstawienie"}

x = TX; cols = []
for r, a, t in COLS:
    w = max(len(r or "***"), len(a or "***")) * CH
    cols.append(dict(ref=r, asr=a, typ=t, x=x, w=w)); x += w + GAP
SPEECH_END = cols[6]["x"] + cols[6]["w"]

SWEEP_A, SWEEP_B = TX - 10, cols[-1]["x"] + cols[-1]["w"] + 30
DUR, SWEEP = 11.0, 6.5
def pct(xx):  # % czasu animacji, gdy głowica jest w xx
    return (xx - SWEEP_A) / (SWEEP_B - SWEEP_A) * SWEEP / DUR * 100
END = SWEEP / DUR * 100

rnd = random.Random(11)
def amp(xx):
    for c in cols[:7]:
        if c["ref"] and c["x"] <= xx <= c["x"] + c["w"]:
            t = (xx - c["x"]) / c["w"]
            env = math.sin(math.pi * t) ** 0.6
            syl = 0.55 + 0.45 * abs(math.sin(t * math.pi * len(c["ref"]) / 2.6))
            return max(2, AMP * env * syl * (0.7 + 0.3 * rnd.random()))
    return 1 + 1.1 * rnd.random()
bars = "\n      ".join(
    f'<rect x="{xx}" y="{CY - (h := amp(xx)):.1f}" width="{BW}" height="{2 * h:.1f}" rx="1.5"/>'
    for xx in range(X0, X1 + 1, STEP))

def word(txt, c, y, cls):
    if txt is None:
        return f'<text class="mono {cls}" x="{c["x"]}" y="{y}" font-size="20" opacity=".45">***</text>'
    return f'<text class="mono {cls}" x="{c["x"]}" y="{y}" font-size="20" textLength="{len(txt) * CH}" lengthAdjust="spacing">{txt}</text>'

ref_row = "\n    ".join(word(c["ref"], c, Y_REF, "muted") for c in cols)
asr_row = "\n      ".join(word(c["asr"], c, Y_ASR, "acc" if c["typ"] else "fg") for c in cols)

# znaczniki błędów i licznik WER — każdy element ma własne keyframes
kf, tags, counters = [], [], []
errs = [c for c in cols if c["typ"]]
for k, c in enumerate(errs, 1):
    on = pct(c["x"] + c["w"])
    kf.append(f"@keyframes e{k} {{ 0%,{on:.1f}% {{ opacity:0; }} {on + 2:.1f}%,92% {{ opacity:1; }} 97%,100% {{ opacity:0; }} }}")
    cx = c["x"] + c["w"] / 2
    tags.append(f'<g class="flag" style="animation-name:e{k}"><rect class="tagbox" x="{cx - 9}" y="{Y_TAG}" width="18" height="18" rx="4"/>'
                f'<text class="mono tagtxt" x="{cx}" y="{Y_TAG + 13.5}" font-size="12" text-anchor="middle" font-weight="700">{c["typ"]}</text></g>')
times = [0] + [pct(c["x"] + c["w"]) for c in errs] + [97]
for k in range(len(errs) + 1):
    a, b = times[k], times[k + 1]
    fade_in = "" if k == 0 else f"{a:.1f}% {{ opacity:0; }} {a + 0.1:.1f}% {{ opacity:1; }}"
    first = "0%" if k == 0 else f"0%,{a:.1f}%"
    body = (f"0%,{b:.1f}% {{ opacity:1; }} {b + 0.1:.1f}%,100% {{ opacity:0; }}" if k == 0 else
            f"0%,{a:.1f}% {{ opacity:0; }} {a + 0.1:.1f}%,{b:.1f}% {{ opacity:1; }} {b + 0.1:.1f}%,100% {{ opacity:0; }}")
    if k == len(errs):
        body = f"0%,{a:.1f}% {{ opacity:0; }} {a + 0.1:.1f}%,92% {{ opacity:1; }} 97%,100% {{ opacity:0; }}"
    kf.append(f"@keyframes w{k} {{ {body} }}")
    pctv = round(100 * k / N_REF)
    final = " final" if k == len(errs) else ""
    counters.append(f'<g class="wer{final}" style="animation-name:w{k}">'
                    f'<text class="sans {"acc" if k else "fg"}" x="{X1}" y="{Y_ASR + 4}" font-size="40" font-weight="650" text-anchor="end" letter-spacing="-1">{pctv}%</text>'
                    f'<text class="mono muted" x="{X1}" y="{Y_TAG + 14}" font-size="12" text-anchor="end">{k} {"błąd" if k == 1 else "błędy" if 2 <= k <= 4 else "błędów"} / {N_REF} słów</text></g>')

legend_x = TX
legend = []
for t in "SDI":
    legend.append(f'<rect class="tagbox" x="{legend_x}" y="352" width="18" height="18" rx="4"/>'
                  f'<text class="mono tagtxt" x="{legend_x + 9}" y="365.5" font-size="12" text-anchor="middle" font-weight="700">{t}</text>'
                  f'<text class="mono muted" x="{legend_x + 26}" y="366" font-size="12" letter-spacing=".5">{LABEL[t]}</text>')
    legend_x += 26 + len(LABEL[t]) * 7.3 + 30
legend = "\n  ".join(legend)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
  <title id="t">Błędy modeli ASR w dyktowaniu polskich opisów diagnostyki obrazowej</title>
  <desc id="d">Podyktowano: „Płat prawy 14x12x45 mm, bez zmian ogniskowych.” Model rozpoznał: „Płat lewy 14x12x4 mm, zmian ogniskowych. Dziękuję.” Cztery błędy na siedem słów (WER 57%): podmiana strony ciała, zły wymiar, pominięte zaprzeczenie i słowo wstawione w ciszy.</desc>
  <style>
    :root {{ --bg:#fbfbfa; --fg:#18181b; --muted:#6b6b73; --faint:#d9d9de; --line:#e7e7ea; --acc:#c2410c; --acc-bg:rgba(194,65,12,.12); }}
    @media (prefers-color-scheme: dark) {{
      :root {{ --bg:#0d1117; --fg:#e6edf3; --muted:#8b949e; --faint:#30363d; --line:#21262d; --acc:#f0883e; --acc-bg:rgba(240,136,62,.16); }}
    }}
    .bg {{ fill:var(--bg); stroke:var(--line); }}
    .sans {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Helvetica Neue",Arial,sans-serif; }}
    .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace; }}
    .fg {{ fill:var(--fg); }} .muted {{ fill:var(--muted); }} .acc {{ fill:var(--acc); }}
    .wave-dim {{ fill:var(--faint); }} .wave-on {{ fill:var(--fg); }}
    .rule {{ stroke:var(--line); stroke-width:1; }}
    .head {{ stroke:var(--acc); stroke-width:1.5; }}
    .tagbox {{ fill:var(--acc-bg); }} .tagtxt {{ fill:var(--acc); }}

    .reveal   {{ transform-origin:0 0; animation:reveal {DUR}s linear infinite; }}
    .playhead {{ animation:play {DUR}s linear infinite; }}
    .fadeout  {{ animation:fadeout {DUR}s linear infinite; }}
    .flag, .wer {{ animation-duration:{DUR}s; animation-iteration-count:infinite; animation-timing-function:ease-out; }}
    @keyframes reveal  {{ 0% {{ transform:scaleX({SWEEP_A / X1:.4f}); }} {END:.1f}%,100% {{ transform:scaleX({SWEEP_B / X1:.4f}); }} }}
    @keyframes play    {{ 0% {{ transform:translateX({SWEEP_A}px); opacity:1; }} {END:.1f}% {{ transform:translateX({SWEEP_B}px); opacity:1; }} {END + 4:.1f}%,100% {{ transform:translateX({SWEEP_B}px); opacity:0; }} }}
    @keyframes fadeout {{ 0%,92% {{ opacity:1; }} 97%,100% {{ opacity:0; }} }}
    {chr(10).join("    " + k for k in kf).strip()}
    @media (prefers-reduced-motion: reduce) {{
      .reveal {{ animation:none; transform:scaleX({SWEEP_B / X1:.4f}); }}
      .fadeout, .flag, .wer.final {{ animation:none; opacity:1; }}
      .wer {{ animation:none; opacity:0; }} .wer.final {{ opacity:1; }}
      .playhead {{ animation:none; opacity:0; }}
    }}
  </style>
  <defs>
    <clipPath id="played"><rect class="reveal" x="0" y="0" width="{X1}" height="{H}"/></clipPath>
  </defs>

  <rect class="bg" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14"/>

  <!-- nagłówek -->
  <text class="mono muted" x="{X0}" y="66" font-size="13" letter-spacing="2">BADANIE · ROZPOZNAWANIE MOWY · RADIOLOGIA</text>
  <text class="mono muted" x="{X1}" y="66" font-size="13" letter-spacing="1" text-anchor="end">ADMEDVOICE · 7 643 nagrania · PL</text>
  <text class="sans fg" x="{X0 - 2}" y="120" font-size="44" font-weight="650" letter-spacing="-0.8">Błędy modeli ASR</text>
  <text class="sans muted" x="{X0}" y="156" font-size="22">w dyktowaniu polskich opisów diagnostyki obrazowej</text>

  <!-- fala -->
  <g class="wave-dim">
      {bars}
  </g>
  <g class="wave-on" clip-path="url(#played)">
      {bars}
  </g>
  <text class="mono muted" x="{SPEECH_END + 14}" y="{CY - 26}" font-size="11" letter-spacing="1">CISZA</text>

  <!-- etykiety wierszy -->
  <text class="mono muted" x="{X0}" y="{Y_REF - 2}" font-size="12" letter-spacing="1.5">REF</text>
  <text class="mono muted" x="{X0}" y="{Y_ASR - 2}" font-size="12" letter-spacing="1.5">ASR</text>
  <line class="rule" x1="{X0}" y1="{(Y_REF + Y_ASR) / 2 - 6}" x2="{SWEEP_B}" y2="{(Y_REF + Y_ASR) / 2 - 6}"/>

  <!-- tekst podyktowany (zawsze widoczny) -->
  <g>
    {ref_row}
  </g>

  <!-- tekst rozpoznany + znaczniki błędów + WER -->
  <g class="fadeout">
    <g clip-path="url(#played)">
      {asr_row}
    </g>
    {chr(10).join("    " + t for t in tags).strip()}
  </g>
  <text class="mono muted" x="{X1}" y="{Y_REF - 2}" font-size="12" letter-spacing="1.5" text-anchor="end">WER</text>
  {chr(10).join("  " + c for c in counters).strip()}

  <!-- legenda -->
  {legend}

  <!-- głowica -->
  <g class="playhead">
    <line class="head" x1="0" y1="{CY - 26}" x2="0" y2="{Y_ASR + 10}"/>
    <circle class="acc" cx="0" cy="{CY - 26}" r="3.5"/>
  </g>
</svg>
'''
out = os.path.join(os.path.dirname(__file__), "..", "assets", "banner.svg")
open(out, "w", encoding="utf-8").write(svg)
print("zapisano", os.path.abspath(out), len(svg), "B; kolumny:", [(c["x"], c["w"]) for c in cols], "koniec:", SWEEP_B)
