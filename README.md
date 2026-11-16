<p align="center"><img src="assets/banner.svg" alt="Halucynacje modeli ASR w dyktowaniu polskich opisów diagnostyki obrazowej — model dopisuje tekst w ciszy nagrania" width="100%"></p>

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

### 2.1 ADMEDVOICE i model `whisper-medium-medical-pl`

Korpus opisano w artykule Czyżewski i in., *A Comprehensive Polish Medical Speech Dataset for
Enhancing Automatic Medical Dictation*, Scientific Data 12:1436 (2025),
[doi:10.1038/s41597-025-05776-1](https://doi.org/10.1038/s41597-025-05776-1),
[PMC12357909](https://europepmc.org/articles/PMC12357909). Zespół pochodzi z Politechniki Gdańskiej
i Gdańskiego Uniwersytetu Medycznego, a projekt finansowało NCBR (INFOSTRATEG4/0003/2022).

**Jak powstał model.** Opis pochodzi z artykułu, karty modelu na Kaggle i notebooka autora
(sprawdzone 2026-11-16).

- **Model bazowy:** `openai/whisper-medium` (769M parametrów, licencja Apache 2.0). Notebook odczytuje
  go z konfiguracji adaptera (`PeftConfig.base_model_name_or_path`).
- **Metoda:** artykuł jej nie nazywa. Karta na Kaggle podaje „trained with LoRA” i 4,7M trenowanych
  parametrów, czyli około 0,6% modelu. Notebook ładuje adapter przez `PeftModel` i scala go
  (`merge_and_unload`). Rank, alpha i docelowe moduły LoRA nie są nigdzie podane.
- **Parametry treningu:** wszystkie dane pochodzą z artykułu, nie sprawdzaliśmy ich.

  | Parametr | Wartość |
  |---|---|
  | Liczba kroków | maks. 10 000 |
  | Batch | 64 |
  | Learning rate | 1e-5 |
  | Wybór checkpointu | najniższy WER na walidacji |
  | Sprzęt | 1× NVIDIA A100 (PLGrid), do 48 h na przebieg |
  | Biblioteki | PyTorch 2.5, transformers 4.48, HF datasets |
  | Audio | próbkowanie 16 kHz; nagrania dłuższe niż 30 s usunięte |

- **Dane:** wszystkie kategorie ADMEDVOICE, nie tylko radiologia. Podział jest rozłączny po mówcach
  (deklaracja autorów):

  | Zbiór | Train | Val | Test |
  |---|---|---|---|
  | N+A+S (łącznie) | 34 900 próbek (58 h) | 2 492 (4 h) | 12 468 (21 h) |
  | Natural | 7 404 (9,6 h) | 529 | 2 645 (3,4 h) |

  W zbiorze testowym każda unikalna fraza pojawia się średnio 4,6 razy.
- **Warianty:** na Kaggle są checkpointy trenowane na danych natural, anonym, synth oraz na wszystkich
  trzech razem. Najlepszy to `natural_anonym_synth`.
- **Wyniki:** WER na teście natural, deklaracja autorów, w nawiasach 95% CI z bootstrapu.

  | Model | WER (natural test) |
  |---|---|
  | Whisper bazowy | 24,0 [22,3; 26,0] |
  | trening na natural | 15,5 [12,5; 19,8] |
  | trening na anonymized | 13,6 [12,1; 15,2] |
  | trening na N+A+S | 13,9 [12,4; 15,6] |
  | N+A+S + Common Voice + FLEURS | 9,5 [8,1; 11,1] |

  Wariantu z Common Voice i FLEURS (WER 9,5) nie ma wśród checkpointów wymienionych w opisie modelu
  na Kaggle. Opis podaje tylko natural, anonym, synth i `natural_anonym_synth`. Najlepszy model,
  który da się pobrać, ma więc deklarowany WER 13,9, a nie 9,5. Listy plików modelu nie
  sprawdzaliśmy, bo wymaga logowania do Kaggle.
- **Publikacja:** model na Kaggle `msxksm/whisper-medium-medical-pl` (Apache 2.0) i notebook
  `msxksm/transcribe-medical-pl-whisper-medium`. Wersja dla whisper.cpp to HF
  `fwasil162/whisper-medium-medical-pl-ggml`: adapter scalony z modelem bazowym, przekonwertowany
  do formatu ggml i skwantyzowany do q5_0 (514 MB). To repozytorium nie jest od autorów korpusu.

**Luki i niespójności istotne dla naszego badania:**
- **Artykuł nie analizuje halucynacji.** Cytuje literaturę o halucynacjach, ale ich nie mierzy. To jest
  luka, którą wypełnia nasze badanie.
- **Nie wiadomo, jak normalizowano tekst przed liczeniem WER.** Artykuł o tym nie pisze.
- **Niespójności w artykule:**
  - w tekście wyników WER 9,5% przypisano treningowi na nagraniach naturalnych, a tabela podaje 9,5
    dla wariantu z Common Voice i FLEURS;
  - przedziały ufności wariantów natural i anonymized nakładają się, więc teza, że trening na danych
    zanonimizowanych jest lepszy, nie jest dowiedziona.
- **Ryzyko przecieku danych (najważniejsze dla nas):** model trenowano na mówcach z ADMEDVOICE, a lista
  mówców testowych nie jest opublikowana w artykule ani w notebooku. Ocena tego modelu na naszym
  wycinku radiologicznym może więc obejmować nagrania, które widział w treningu, nawet jeśli tylko
  w wersji zanonimizowanej. Notebook demonstracyjny transkrybuje nagranie mówcy AMV010
  z `cat_02-001`, który jest w naszym zbiorze. *TODO: ustalić podział mówców autorów, np. z kodu na
  Kaggle albo przez kontakt z autorami, zanim porównamy ten model z bazowym Whisperem.*

### 2.2 Inne prace

- Kurowski, Zaporowski, Kostek, Czyżewski (ISD 2025/2026): porównują metody PEFT (LoRA, DoRA, MoRA)
  na Whisper small, oceniając je na teście ADMEDVOICE.
  *TODO: przeczytać i opisać.*

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

**Schemat bazy** (`recordings/radiology.sqlite`; pliki CSV mają te same kolumny):

#### Tabela `recordings` (7 643 wiersze, to samo co `metadata.csv`)

| Kolumna | Opis |
|---|---|
| `recording_id` | Nazwa pliku bez `.wav` (klucz główny). |
| `path` | Ścieżka do `.wav` względem `recordings/`, np. `audio/natural/AMV010/….wav`. |
| `source` | `natural` / `anonymized` / `synthetic`. |
| `category_code`, `category` | `02-001` radiologia tarczycy (USG) / `02-003` radiologia głowa–szyja. |
| `speaker_id` | `AMV…` człowiek, `ANI…` głos zanonimizowany, `SYN…` głos syntetyczny. |
| `speaker_sex`, `speaker_age` | `F`/`M` i wiek; puste dla anonymized. |
| `rec_place` | `GU…` pomieszczenia GUMed, `PG…` studio, `UNKNV` nagranie online, `SPGEN` syntezator. |
| `mic_code`, `mic` | Mikrofon, np. `NTG2` = RODE NTG-2, `ONLN` = online, `MODE` = synteza. |
| `text_id` | ID tekstu; klucz obcy do `phrases`. |
| `phrase_group` | Grupa identycznych tekstów (patrz „Problemy z danymi” niżej). |
| `phrase` | **Transkrypcja referencyjna** (spacje znormalizowane, Unicode NFC). |
| `duration_s`, `sample_rate`, `bit_depth`, `channels` | Odczytane z nagłówka WAV. |
| `mos_pred`, `grade`, `comments` | Jakość nagrania i uwagi z metadanych korpusu. |
| `recorded_at` | Data z nazwy pliku. W 23 nagraniach anonymized jest to zastępczy ciąg w rodzaju `03753T000000`, a nie data. |

#### Tabela `phrases` (857 wierszy, to samo co `phrases.csv`)

Kolumny `text_id`, `phrase_group`, `category_code`, `phrase` i `n_words`, a do tego liczba nagrań
każdego tekstu w każdym źródle: `n_natural`, `n_anonymized`, `n_synthetic`.

#### Widoki

- `summary` zawiera liczby z tabeli w sekcji 3.2, w podziale na kategorie.
- `speakers` zawiera, dla każdego mówcy: źródło, płeć, wiek, użyte mikrofony, liczbę nagrań i minuty.

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
