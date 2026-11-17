# recordings/ — baza nagrań radiologicznych (ADMEDVOICE)

Wycinek korpusu **ADMEDVOICE** (Kaggle `karmarci/polish-medical-multi-source-corpus`,
DOI 10.34740/kaggle/ds/6698205, licencja CC BY 4.0). Zawiera wyłącznie nagrania z naturalnym
głosem ludzkim, w kategoriach radiologicznych:

- `02-001` to radiologia tarczycy (opisy USG),
- `02-003` to radiologia głowy i szyi.

Pozostałe kategorie korpusu (onkologia, kardiologia, resuscytacja, zalecenia, skierowania) oraz
warianty zanonimizowany i syntetyczny nie są wykorzystywane w tym badaniu i nie wchodzą do bazy.

Nagrania to czytane, krótkie frazy z opisów (od 2 do 46 słów, średnio 16), a nie dyktowanie całych opisów.

> **Audio (`recordings/audio/`, ok. 1,0 GB) nie jest w repozytorium Git.** Repo zawiera tylko
> metadane, bazę i skrypt. Żeby odtworzyć audio:
> 1. pobierz korpus ADMEDVOICE z Kaggle i rozpakuj go do `recordings/`; potrzebny jest katalog
>    `human_voices/` i plik `corpus_summary_all.csv`,
> 2. uruchom `python3 scripts/build_radiology_db.py recordings --move`.
>
> Skrypt przetwarza wyłącznie nagrania naturalne i nadpisuje `metadata.csv`, `phrases.csv`
> oraz `radiology.sqlite`. Pozostałych katalogów korpusu nie usuwa.

## Szybki start

```bash
sqlite3 -header -column radiology.sqlite "SELECT * FROM summary"
```

```python
import sqlite3, pandas as pd
con = sqlite3.connect("recordings/radiology.sqlite")
df = pd.read_sql("SELECT path, phrase, speaker_id, duration_s FROM recordings", con)
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
│   └── natural/<speaker_id>/*.wav     prawdziwy głos ludzki (AMV…)
└── docs/
    ├── info-pl.txt, info-en.txt       oryginalny opis korpusu od autorów (schemat nazw, kody)
    └── speaker_notes/GUSOR-AMV016.txt notatka nagrywającego o warunkach akustycznych
```

Skrypt, który zbudował bazę, to `../scripts/build_radiology_db.py`. Bez flagi `--move` wykonuje
tylko dry run.

## Liczby

Policzone z bazy (`SELECT * FROM summary`). Czasy wyliczono z nagłówków WAV.

| Kategoria | Nagrania | Mówcy | Teksty | Godziny |
|---|---:|---:|---:|---:|
| 02-001 tarczyca | 839 | 12 | 185 | 2,50 |
| 02-003 głowa–szyja | 100 | 3 | 61 | 0,18 |
| **Razem** | **939** | **14** | **246** | **2,69** |

**Mówcy:** 9 kobiet i 4 mężczyzn; jeden mówca (61 nagrań) nie ma podanej płci.

## Ważne przy eksperymentach

- **Radiologia głowy i szyi to tylko 100 plików od 3 mówców.** Większość zbioru dotyczy USG tarczycy.
- **Poprawka kategorii:** 61 nagrań mówcy AMV102 ma w nazwie pliku kod `02-001`, ale teksty
  pochodzą z głowy i szyi (`text_id` 13289–13739, np. MR twarzoczaszki). W bazie mają
  `category_code='02-003'`. Nazwy plików zostawiono bez zmian.
- **Audio nie jest ujednolicone.** Częstotliwości próbkowania to 16, 24, 44,1 i 48 kHz, głębia
  16 lub 24 bit, wszystko mono. Przed podaniem do Whispera przepróbkuj do 16 kHz.
- **Prawie identyczne teksty z różnymi `text_id`.** Autorzy uprzedzają, że teksty wgrywano
  ponownie po poprawkach spacji czy fleksji. Kolumna `phrase_group` grupuje teksty identyczne po
  zmianie na małe litery i obcięciu końcowej kropki: 246 `text_id` daje 215 grup. Teksty różniące
  się jednym słowem (np. „opcji CD” i „opcji color doppler”) pozostają w osobnych grupach.
- **Transkrypcje są zapisem pisanym** (np. „14x12x45 mm”, „3,7 ml”, skróty), a nie zapisem tego,
  co zostało powiedziane. Przed liczeniem WER trzeba znormalizować i referencję, i hipotezę.
- **Ocena jakości `grade`** to ręczna ocena 0–5.
- **Notatka do mówcy AMV016** (`docs/speaker_notes/GUSOR-AMV016.txt`): od tekstu 4502 w tle
  słychać „beep” aparatury, a od 4522 dodatkowe szumy.

## Powtórzenia nagrań

Sprawdzone hashem MD5 próbek audio (z pominięciem nagłówka WAV):

- **Nie ma identycznych plików.**
- **Ten sam mówca czyta ten sam tekst kilka razy:** 129 przypadków, razem 258 nagrań.
- **Teksty powtarzają się między mówcami.** Średnio jeden tekst ma 3,8 nagrania (najwięcej 13).
  Kolumna `phrase_group` grupuje dodatkowo teksty identyczne mimo różnych `text_id` (246 → 215).

## Schemat bazy

Opis tabel, kolumn i widoków jest w głównym README repo: `../README.md`, sekcja 3.3.

## Przykładowe zapytania

```sql
-- zaszumione nagrania AMV016 (aparatura w tle)
SELECT path, phrase FROM recordings WHERE speaker_id = 'AMV016' AND text_id >= 4502;

-- najdłuższe nagrania (długie audio to większe ryzyko błędów)
SELECT path, duration_s, phrase FROM recordings ORDER BY duration_s DESC LIMIT 20;

-- dobre jakościowo nagrania
SELECT * FROM recordings WHERE grade >= 4;
```
