# recordings/ — baza nagrań radiologicznych (ADMEDVOICE)

Wycinek korpusu **ADMEDVOICE** (Kaggle `karmarci/polish-medical-multi-source-corpus`,
DOI 10.34740/kaggle/ds/6698205, licencja CC BY 4.0). Zawiera tylko kategorie radiologiczne:

- `02-001` to radiologia tarczycy (opisy USG),
- `02-003` to radiologia głowy i szyi.

Pozostałe kategorie (onkologia, kardiologia, resuscytacja, zalecenia, skierowania) usunięto
2026-11-16. Do ich odzyskania trzeba ponownie pobrać korpus z Kaggle.

Nagrania to czytane, krótkie frazy z opisów (od 2 do 46 słów, średnio 16), a nie dyktowanie całych opisów.

> **Audio (`recordings/audio/`, 5,6 GB) nie jest w repozytorium Git.** Repo zawiera tylko metadane,
> bazę i skrypt. Żeby odtworzyć audio:
> 1. pobierz korpus ADMEDVOICE z Kaggle i rozpakuj go do `recordings/`; powstaną katalogi
>    `human_voices/`, `anoni/`, `synth/` i plik `corpus_summary_all.csv`,
> 2. uruchom `python3 scripts/build_radiology_db.py recordings --move`.
>
> Skrypt nadpisze `metadata.csv`, `phrases.csv` i `radiology.sqlite`. Pozostałe kategorie korpusu
> zostaną w starych katalogach; skrypt ich nie usuwa.

## Szybki start

```bash
sqlite3 -header -column radiology.sqlite "SELECT * FROM summary"
```

```python
import sqlite3, pandas as pd
con = sqlite3.connect("recordings/radiology.sqlite")
# zbiór testowy: tylko głos naturalny
df = pd.read_sql("SELECT path, phrase, speaker_id, duration_s FROM recordings WHERE source='natural'", con)
# lub bez SQL:
df = pd.read_csv("recordings/metadata.csv")
```

Ścieżki w kolumnie `path` są względne wobec katalogu `recordings/`.

## Zawartość

```
recordings/
├── README.md            ten plik
├── radiology.sqlite     baza SQLite: tabele recordings, phrases; widoki speakers, summary
├── metadata.csv         to samo co tabela recordings, płaski CSV (1 wiersz = 1 plik .wav)
├── phrases.csv          to samo co tabela phrases (1 wiersz = 1 tekst referencyjny)
├── audio/
│   ├── natural/<speaker_id>/*.wav     prawdziwy głos ludzki (AMV…)
│   ├── anonymized/<speaker_id>/*.wav  głos ludzki po anonimizacji SALT (ANI…)
│   └── synthetic/<speaker_id>/*.wav   synteza mowy speechgen (SYN…)
└── docs/
    ├── info-pl.txt, info-en.txt       oryginalny opis korpusu od autorów (schemat nazw, kody)
    └── speaker_notes/GUSOR-AMV016.txt notatka nagrywającego o warunkach akustycznych
```

Skrypt, który zbudował bazę, to `../scripts/build_radiology_db.py`. Bez flagi `--move` wykonuje
tylko dry run.

## Liczby

Policzone z bazy (`SELECT * FROM summary`). Czasy wyliczono z nagłówków WAV.

| Źródło | Kategoria | Nagrania | Mówcy | Teksty | Godziny |
|---|---|---:|---:|---:|---:|
| natural | 02-001 tarczyca | 839 | 12 | 185 | 2,50 |
| natural | 02-003 głowa–szyja | 100 | 3 | 61 | 0,18 |
| anonymized | 02-001 | 1 467 | 21 | 307 | 4,51 |
| anonymized | 02-003 | 3 497 | 19 | 448 | 8,06 |
| synthetic | 02-001 | 144 | 6 | 24 | 0,31 |
| synthetic | 02-003 | 1 596 | 6 | 266 | 2,58 |
| **Razem** | | **7 643** | | **857** | **18,2** |

Łącznie zajmuje to 5,6 GB: natural 1,0 GB, anonymized 3,7 GB, synthetic 954 MB.

**Mówcy naturalni:** 9 kobiet i 4 mężczyzn. Jeden mówca (61 nagrań) nie ma podanej płci.
**Mówcy syntetyczni:** 3 głosy kobiece i 3 męskie.

## Ważne przy eksperymentach

- **Do oceny ASR używaj `source='natural'`.** Ta część ma 939 nagrań i niecałe 2,7 h. Mowa z części
  anonymized i synthetic jest przetworzona albo sztuczna, więc nadaje się do augmentacji
  i do porównań, a nie jako zbiór testowy.
- **Radiologia głowy i szyi w nagraniach naturalnych to tylko 100 plików od 3 mówców.** Większość
  części naturalnej dotyczy USG tarczycy.
- **Poprawka kategorii:** 61 nagrań mówcy AMV102 ma w nazwie pliku kod `02-001`, ale teksty
  pochodzą z głowy i szyi (`text_id` 13289–13739, np. MR twarzoczaszki). W bazie mają
  `category_code='02-003'`. Nazwy plików zostawiono bez zmian.
- **Audio nie jest ujednolicone.** Częstotliwości próbkowania to 16, 24, 44,1 i 48 kHz, głębia
  16 lub 24 bit, wszystko mono. Przed podaniem do Whispera przepróbkuj do 16 kHz.
- **Ten sam tekst czytany przez różne źródła:**
  - 144 teksty mają nagranie naturalne i zanonimizowane,
  - 63 teksty występują we wszystkich trzech źródłach,
  - odpowiednie zapytanie jest w sekcji „Przykładowe zapytania" niżej.
- **Prawie identyczne teksty z różnymi `text_id`.** Autorzy uprzedzają, że teksty wgrywano
  ponownie po poprawkach spacji czy fleksji. Kolumna `phrase_group` grupuje teksty identyczne po
  zmianie na małe litery i obcięciu końcowej kropki: 857 `text_id` daje 773 grupy. Teksty różniące
  się jednym słowem (np. „opcji CD" i „opcji color doppler") pozostają w osobnych grupach.
- **Transkrypcje są zapisem pisanym** (np. „14x12x45 mm", „3,7 ml", skróty), a nie zapisem tego,
  co zostało powiedziane. Przed liczeniem WER trzeba znormalizować i referencję, i hipotezę.
- **Ocena jakości:**
  - `grade` to ręczna ocena 0–5, dostępna tylko dla nagrań naturalnych,
  - `mos_pred` to automatyczna predykcja MOS, dostępna dla natural i anonymized,
  - synthetic nie ma żadnej z nich.
- **Notatka do mówcy AMV016** (`docs/speaker_notes/GUSOR-AMV016.txt`): od tekstu 4502 w tle
  słychać „beep" aparatury, a od 4522 dodatkowe szumy. Te nagrania przydadzą się do testów
  halucynacji na zaszumionym audio.

## Powtórzenia nagrań

Sprawdzone 2026-11-16 na wszystkich 7 643 plikach.

- **Nie ma identycznych plików.** Sprawdzone hashem MD5 próbek audio, z pominięciem nagłówka WAV.
- **Część nagrań zanonimizowanych to te same nagrania co naturalne, tylko po zmianie głosu.**
  - 449 z 4 964 nagrań `anonymized` ma odpowiednik w `natural`: ten sam `text_id` i ten sam znacznik
    czasu w nazwie pliku.
  - W 16 nagraniach z `GU001` czasu nie ma, więc dopasowano je po miejscu i mikrofonie.
  - Pary pochodzą od 10 par mówców, np. ANI573↔AMV102, ANI506↔AMV021, ANI542↔AMV157, ANI505↔AMV030,
    ANI535↔AMV049, ANI551↔AMV046.
  - Że to ta sama wypowiedź, potwierdza korelacja obwiedni głośności: dla takich par zwykle przekracza
    0,9, a dla losowych par z tym samym tekstem mediana wynosi 0,21.
  - **Wniosek: przy podziale train/test pary trzeba trzymać po tej samej stronie.** Inaczej ta sama
    wypowiedź trafi do obu zbiorów.
  - Pozostałe 4 515 nagrań `anonymized` nie ma odpowiednika w tym wycinku. Najpewniej pochodzą
    z nagrań naturalnych, których korpus nie udostępnia.
- **Ten sam mówca czyta ten sam tekst kilka razy:**
  - natural: 129 takich przypadków, razem 258 nagrań,
  - anonymized: 179 przypadków, razem 365 nagrań,
  - synthetic: każdy głos czyta dany tekst raz.
- **Teksty powtarzają się między mówcami.** Średnio jeden tekst ma 3,8 nagrania w części natural
  (najwięcej 13), 6,6 w anonymized i 6,0 w synthetic. Kolumna `phrase_group` grupuje dodatkowo
  teksty identyczne mimo różnych `text_id` (857 → 773).
- **Teksty wspólne dla źródeł:** 144 teksty mają nagrania natural i anonymized, 63 występują we
  wszystkich trzech źródłach.

```sql
-- pary anonymized ↔ natural (ta sama wypowiedź po zmianie głosu)
SELECT a.recording_id AS anon, n.recording_id AS nat
FROM recordings a JOIN recordings n
  ON a.source = 'anonymized' AND n.source = 'natural' AND a.text_id = n.text_id
 AND ((a.recorded_at = n.recorded_at AND a.recorded_at NOT LIKE '%T000000')
   OR (a.recorded_at LIKE '%T000000' AND a.rec_place = n.rec_place AND a.mic_code = n.mic_code));
```

## Schemat bazy

Opis tabel, kolumn i widoków jest w głównym README repo: `../README.md`, sekcja 3.3.

## Przykładowe zapytania

```sql
-- teksty nagrane we wszystkich trzech źródłach (porównanie natural vs anonymized vs synthetic)
SELECT r.* FROM recordings r JOIN phrases p USING(text_id)
WHERE p.n_natural > 0 AND p.n_anonymized > 0 AND p.n_synthetic > 0;

-- zaszumione nagrania AMV016 (aparatura w tle)
SELECT path, phrase FROM recordings WHERE speaker_id = 'AMV016' AND text_id >= 4502;

-- najdłuższe nagrania naturalne (ryzyko halucynacji na długim audio)
SELECT path, duration_s, phrase FROM recordings WHERE source = 'natural' ORDER BY duration_s DESC LIMIT 20;

-- dobre jakościowo nagrania naturalne
SELECT * FROM recordings WHERE source = 'natural' AND grade >= 4;
```
