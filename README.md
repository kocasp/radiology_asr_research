# Halucynacje modeli ASR w dyktowaniu polskich opisów diagnostyki obrazowej

> Wersja robocza publikacji. Plik jest aktualizowany po każdym kroku badania (zasady w `CLAUDE.md`).
> Sekcje oznaczone *TODO* nie mają jeszcze wyników.

## Streszczenie

*TODO — uzupełnić po pierwszych eksperymentach z modelami ASR.*

Stan na 2026-11-16: przygotowany zbiór danych (sekcja 3). Eksperymentów z modelami jeszcze nie było.

## 1. Wprowadzenie i pytanie badawcze

Radiolodzy coraz częściej dyktują opisy badań do systemów rozpoznawania mowy (ASR). Modele
sekwencyjne, takie jak Whisper, mogą **halucynować**: zwracają płynny, wiarygodnie brzmiący tekst,
którego nie było w nagraniu. W opisie badania obrazowego taki błąd jest groźniejszy niż zwykła
literówka. Wstawiony wymiar, strona ciała czy zaprzeczenie („nie stwierdza się") zmienia znaczenie
kliniczne, a lekarz może go nie zauważyć.

**Pytanie badawcze:** jak często i w jakich warunkach modele ASR halucynują przy polskich frazach
z opisów radiologicznych? Które cechy nagrania zwiększają ryzyko: szum tła, cisza, długość,
mikrofon, głos przetworzony lub syntetyczny?

*TODO: operacyjna definicja halucynacji i metoda jej wykrywania.*

## 2. Powiązane prace

*TODO.* Punkty wyjścia:
- korpus ADMEDVOICE ([Scientific Data 2025](https://www.nature.com/articles/s41597-025-05776-1)),
- model `whisper-medium-medical-pl`, dla którego deklarowany WER spada z 24,03 do 13,91 (deklaracja
  autorów, nie sprawdzaliśmy jej).

## 3. Dane

### 3.1 Źródło

Polskie nagrania medyczne z korpusu **ADMEDVOICE**:
- Kaggle `karmarci/polish-medical-multi-source-corpus`,
- DOI 10.34740/kaggle/ds/6698205,
- licencja CC BY 4.0.

Korpus zawiera 52 990 nagrań (88:19 h, dane autorów) w trzech wariantach:
- **naturalny** głos ludzki,
- **zanonimizowany**, czyli głos ludzki po konwersji metodą SALT,
- **syntetyczny**, wygenerowany przez TTS.

Nagrania to czytane krótkie frazy, a nie spontaniczne dyktowanie całych opisów.

### 3.2 Wybór podzbioru radiologicznego

Z ośmiu kategorii tematycznych korpusu zostawiliśmy dwie radiologiczne:
- `02-001`: radiologia tarczycy, czyli frazy z opisów USG,
- `02-003`: radiologia głowy i szyi, w tym frazy z opisów TK i MR.

Pozostałe kategorie (onkologia, kardiologia, resuscytacja, zalecenia, skierowania) usunęliśmy, bo
nie są diagnostyką obrazową.

| Wariant | Nagrania | Mówcy | Teksty | Godziny |
|---|---:|---:|---:|---:|
| naturalny | 939 | 14 | 246 | 2,69 |
| zanonimizowany | 4 964 | 30 | 755 | 12,57 |
| syntetyczny | 1 740 | 6 | 290 | 2,89 |
| **Razem** | **7 643** | | **857** | **18,2** |

Długość nagrań wyliczyliśmy z nagłówków WAV. Frazy mają od 2 do 46 słów, średnio 15,8.

**Zbiór oceniający to wyłącznie nagrania naturalne.** Warianty zanonimizowany i syntetyczny służą
jako warunki porównawcze, bo pozwalają sprawdzić, czy przetworzony lub sztuczny głos zmienia
skłonność modelu do halucynacji.

### 3.3 Budowa bazy

Skrypt `scripts/build_radiology_db.py` zbudował bazę SQLite (`recordings/radiology.sqlite`) oraz
pliki CSV (`metadata.csv`, `phrases.csv`). Dla każdego nagrania baza zawiera:
- transkrypcję referencyjną,
- mówcę i jego płeć,
- miejsce nagrania i mikrofon,
- parametry audio,
- oceny jakości z korpusu.

Schemat bazy opisuje `recordings/README.md`.

**Problemy z danymi znalezione i poprawione przy budowie bazy:**
- 61 nagrań mówcy AMV102 ma w nazwie pliku kod kategorii `02-001` (tarczyca), choć teksty dotyczą
  głowy i szyi (np. MR twarzoczaszki, `text_id` 13289–13739). W bazie przypisaliśmy im `02-003`.
  Bez tej poprawki część naturalna głowy i szyi liczyłaby 39 nagrań zamiast 100.
- 60 nagrań ma niestandardowy separator (`_`) w nazwie pliku, a 23 nagrania zanonimizowane mają
  zastępczy znacznik czasu zamiast daty. Skrypt obsługuje oba przypadki.
- Ten sam tekst bywa wgrany pod różnymi `text_id`, bo autorzy poprawiali spacje i fleksję. Kolumna
  `phrase_group` łączy teksty identyczne po zmianie na małe litery i obcięciu końcowej kropki:
  857 `text_id` daje 773 grupy.

### 3.4 Powtórzenia i ryzyko przecieku między zbiorami

- **Identycznych plików nie ma.** Sprawdziliśmy to hashem MD5 próbek audio, z pominięciem nagłówka
  WAV.
- **449 nagrań zanonimizowanych to przekonwertowane nagrania naturalne.** Dopasowaliśmy je po
  `text_id` i identycznym znaczniku czasu w nazwie pliku. Potwierdza to korelacja obwiedni głośności:
  - liczona jako korelacja Pearsona log-RMS w ramkach 10 ms,
  - dla kandydatów o tej samej długości (±50 ms) wynosi zwykle ponad 0,9,
  - dla 200 losowych par z tym samym tekstem mediana wynosi 0,21.

  Takie pary są tą samą wypowiedzią, więc **przy podziale train/test muszą trafiać do tego samego
  zbioru**.
- **Ten sam mówca czyta ten sam tekst kilka razy:** 258 takich nagrań w części naturalnej i 365
  w zanonimizowanej. Jeden tekst ma średnio 3,8 nagrania naturalnego.

### 3.5 Ograniczenia danych

- Część naturalna jest mała (2,69 h) i zdominowana przez USG tarczycy: 839 nagrań wobec 100 z głowy
  i szyi.
- Nagrania to czytane frazy, a nie spontaniczne dyktowanie, więc brakuje typowych dla dyktowania
  pauz, poprawek i komend.
- Transkrypcje są w formie pisanej („14x12x45 mm", „3,7 ml"), więc przed liczeniem metryk trzeba
  je znormalizować.
- Audio nie jest ujednolicone: próbkowanie od 16 do 48 kHz, głębia 16 lub 24 bit.

## 4. Metoda

*TODO: wybrane modele ASR, normalizacja tekstu, definicja i detekcja halucynacji, metryki.*

## 5. Eksperymenty i wyniki

*TODO.*

## 6. Dyskusja i ograniczenia

*TODO.*

## 7. Odtwarzalność

| Element | Wersja / źródło | Użycie |
|---|---|---|
| ADMEDVOICE | Kaggle, DOI 10.34740/kaggle/ds/6698205, CC BY 4.0 | dane |
| Python | 3.15.2 (biblioteka standardowa: `csv`, `sqlite3`, `struct`, `hashlib`) | budowa bazy, odczyt nagłówków WAV |
| SQLite | 3.43.2 | baza metadanych |
| NumPy | 2.5.5 (Python 3.12.16) | korelacja obwiedni głośności (analiza par, sekcja 3.4) |

Odtworzenie danych:
1. pobierz ADMEDVOICE z Kaggle i rozpakuj go do `recordings/`,
2. uruchom `python3 scripts/build_radiology_db.py recordings --move`.

Analiza par z sekcji 3.4 była jednorazowym skryptem uruchomionym w sesji. *TODO: przenieść ją do
`scripts/`.*

## Licencja i cytowanie danych

Dane: ADMEDVOICE, CC BY 4.0. Przy wykorzystaniu należy cytować korpus (DOI powyżej) i artykuł
w Scientific Data.
