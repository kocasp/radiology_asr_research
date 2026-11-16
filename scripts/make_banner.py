"""Generuje assets/banner.svg — baner repozytorium (deterministyczny, bez zależności)."""
import math, random, os

W, H = 1280, 360
X0, X1 = 64, 1216            # zakres osi czasu
CY, AMP = 262, 26            # oś fali i maks. amplituda
STEP, BW = 6, 3              # rozstaw i szerokość słupków
CH = 12                      # szerokość znaku transkrypcji (wymuszona przez textLength)

speech_txt = "Tarczyca prawidłowej wielkości,"
hall_txt = "bez zmian ogniskowych."
words = [(0, 8), (9, 20), (21, 31)]           # zakresy znaków słów mowy
SIL_X = X0 + 31 * CH + 20                     # początek ciszy
HX = 600                                      # początek halucynacji
HW = len(hall_txt) * CH

rnd = random.Random(7)
def amp(x):
    for a, b in words:
        xa, xb = X0 + a * CH, X0 + b * CH
        if xa <= x <= xb:
            t = (x - xa) / (xb - xa)
            env = math.sin(math.pi * t) ** 0.6
            syl = 0.55 + 0.45 * abs(math.sin(t * math.pi * (b - a) / 2.6))
            return max(2, AMP * env * syl * (0.7 + 0.3 * rnd.random()))
    return 1 + 1.2 * rnd.random()             # cisza / szum tła

bars = []
for x in range(X0, X1 + 1, STEP):
    h = amp(x)
    bars.append(f'<rect x="{x}" y="{CY - h:.1f}" width="{BW}" height="{2 * h:.1f}" rx="1.5"/>')
bars = "\n      ".join(bars)

sweep = 7.0; dur = 10.0
p = lambda x: (x - X0) / (X1 - X0) * sweep / dur * 100     # % czasu, w którym głowica jest w x
hall_on = p(HX + HW)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
  <title id="t">Halucynacje modeli ASR w dyktowaniu polskich opisów diagnostyki obrazowej</title>
  <desc id="d">Fala dźwiękowa dyktowanego zdania „{speech_txt}”, po której następuje cisza. Model rozpoznawania mowy mimo ciszy dopisuje frazę „{hall_txt}”, której nikt nie wypowiedział.</desc>
  <style>
    :root {{ --bg:#fbfbfa; --fg:#18181b; --muted:#6b6b73; --faint:#d9d9de; --line:#e7e7ea; --acc:#c2410c; --acc-bg:rgba(194,65,12,.10); }}
    @media (prefers-color-scheme: dark) {{
      :root {{ --bg:#0d1117; --fg:#e6edf3; --muted:#8b949e; --faint:#30363d; --line:#21262d; --acc:#f0883e; --acc-bg:rgba(240,136,62,.14); }}
    }}
    .bg {{ fill:var(--bg); stroke:var(--line); }}
    .sans {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Helvetica Neue",Arial,sans-serif; }}
    .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace; }}
    .fg {{ fill:var(--fg); }} .muted {{ fill:var(--muted); }} .acc {{ fill:var(--acc); }}
    .wave-dim {{ fill:var(--faint); }} .wave-on {{ fill:var(--fg); }}
    .rule {{ stroke:var(--faint); stroke-width:1; fill:none; }}
    .head {{ stroke:var(--acc); stroke-width:1.5; }}
    .hl {{ fill:var(--acc-bg); }}

    .reveal  {{ transform-origin:0 0; animation:reveal {dur}s linear infinite; }}
    .playhead{{ animation:play {dur}s linear infinite; }}
    .fadeout {{ animation:fadeout {dur}s linear infinite; }}
    .flag    {{ animation:flag {dur}s ease-out infinite; }}
    @keyframes reveal  {{ 0% {{ transform:scaleX({X0 / X1:.4f}); }} {sweep / dur * 100:.1f}%,100% {{ transform:scaleX(1); }} }}
    @keyframes play    {{ 0% {{ transform:translateX({X0}px); opacity:1; }} {sweep / dur * 100:.1f}% {{ transform:translateX({X1}px); opacity:1; }} {sweep / dur * 100 + 4:.1f}%,100% {{ transform:translateX({X1}px); opacity:0; }} }}
    @keyframes fadeout {{ 0%,92% {{ opacity:1; }} 98%,100% {{ opacity:0; }} }}
    @keyframes flag    {{ 0%,{hall_on:.1f}% {{ opacity:0; }} {hall_on + 4:.1f}%,92% {{ opacity:1; }} 98%,100% {{ opacity:0; }} }}
    @media (prefers-reduced-motion: reduce) {{
      .reveal,.fadeout,.flag {{ animation:none; transform:none; opacity:1; }}
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
  <text class="sans fg" x="{X0 - 2}" y="120" font-size="44" font-weight="650" letter-spacing="-0.8">Halucynacje modeli ASR</text>
  <text class="sans muted" x="{X0}" y="156" font-size="22">w dyktowaniu polskich opisów diagnostyki obrazowej</text>

  <!-- adnotacja ciszy -->
  <path class="rule" d="M{SIL_X} 222 v-6 H{X1} v6"/>
  <text class="mono muted" x="{SIL_X}" y="206" font-size="12" letter-spacing="1">CISZA W NAGRANIU</text>

  <!-- fala: wyszarzona całość + odsłaniana część „odtworzona” -->
  <g class="wave-dim">
      {bars}
  </g>
  <g class="wave-on" clip-path="url(#played)">
      {bars}
  </g>

  <!-- transkrypcja -->
  <g class="fadeout">
    <rect class="hl flag" x="{HX - 8}" y="300" width="{HW + 16}" height="30" rx="5"/>
    <g clip-path="url(#played)">
      <text class="mono fg" x="{X0}" y="321" font-size="20" textLength="{len(speech_txt) * CH}" lengthAdjust="spacing">{speech_txt}</text>
      <text class="mono acc" x="{HX}" y="321" font-size="20" textLength="{HW}" lengthAdjust="spacing">{hall_txt}</text>
    </g>
    <text class="mono acc flag" x="{HX + HW + 22}" y="320" font-size="12" letter-spacing="1">← HALUCYNACJA: TEKSTU NIE MA W AUDIO</text>
  </g>

  <!-- głowica odtwarzania -->
  <g class="playhead">
    <line class="head" x1="0" y1="226" x2="0" y2="336"/>
    <circle class="acc" cx="0" cy="226" r="3.5"/>
  </g>
</svg>
'''
out = os.path.join(os.path.dirname(__file__), "..", "assets", "banner.svg")
open(out, "w", encoding="utf-8").write(svg)
print("zapisano", os.path.abspath(out), len(svg), "B")
