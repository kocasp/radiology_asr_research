<p align="center"><img src="assets/banner.svg" alt="Błędy modeli ASR w dyktowaniu polskich opisów diagnostyki obrazowej — porównanie tekstu podyktowanego z rozpoznanym: podmiana strony ciała, zły wymiar, zgubione zaprzeczenie, wstawione słowo" width="100%"></p>

# Błędy modeli ASR w dyktowaniu polskich opisów diagnostyki obrazowej

> Wersja robocza publikacji. Plik jest aktualizowany po każdym kroku badania (zasady w `CLAUDE.md`).
> Sekcje oznaczone *TODO* nie mają jeszcze wyników.

## Streszczenie

> **Wersja wstępna (2026-11-17):** wyniki modeli otwartych są kompletne; usługi chmurowe
> i dwa najnowsze modele (Cohere Transcribe, NVIDIA Nemotron 3.5) są w toku.

Porównane zostały gotowe systemy automatycznego rozpoznawania mowy (ASR, ang. *automatic speech
recognition*) na polskich frazach z opisów diagnostyki
obrazowej. Zbiór testowy to 939 nagrań głosu naturalnego (2,69 h, 14 mówców, ultrasonografia (USG) tarczycy oraz
radiologia głowy i szyi) z publicznego korpusu ADMEDVOICE. Poza WER (ang. *word error rate*: odsetek słów rozpoznanych błędnie, czyli
podmienionych, pominiętych lub wstawionych, względem liczby słów w tekście wzorcowym) i CER (ang.
*character error rate*: to samo liczone na znakach) mierzone są błędy w trzech
kategoriach istotnych klinicznie (liczby i wymiary, zaprzeczenia, strona ciała) oraz wstawki słów,
których nie było w nagraniu.

Wśród 10 modeli otwartych uruchamianych lokalnie (12 konfiguracji, w tym warianty z modelem
językowym i kontrola negatywna) najlepszy jest **Whisper large-v3: WER 8,0%**
(95% przedział ufności, CI: 7,4–8,7), z błędami w 2,5–2,8% liczb, zaprzeczeń i określeń strony. Nowsze modele z lat
2025–2026 (NVIDIA Canary-1B-v2, Parakeet-TDT-0.6B-v3, Qwen3-ASR-1.7B) osiągają WER 18–22%. Ich
słabości są różne: modele NVIDIA tracą głównie na zapisie liczb, a Qwen3-ASR na zaprzeczeniach
i stronie ciała (10–14% błędów). Modele CTC (ang. *connectionist temporal classification*: wybierają literę
dla każdego fragmentu dźwięku osobno, bez wbudowanej wiedzy o języku) bez modelu językowego (wav2vec2,
Meta MMS, ang. *Massively Multilingual Speech*) mają WER 35–58%;
ogólny polski model językowy obniża go o 3–6 punktów procentowych (p.p.), czyli
względnie o ok. 9%.

Ustalenie metodologiczne: modele dotrenowane na ADMEDVOICE znają frazy testowe. Opublikowany adapter
LoRA (ang. *low-rank adaptation*: dotrenowanie niewielkich dodatkowych macierzy zamiast całego
modelu) osiąga na zbiorze testowym WER 1,46% wobec 13,9% deklarowanych przez autorów, a jeden z mówców
ma 60 nagrań bez żadnego błędu. Takie modele zostały wykluczone z porównania. Korpusu ADMEDVOICE nie
należy używać jako testu dla modeli trenowanych na jego tekstach.

## 1. Wprowadzenie i pytanie badawcze

Radiolodzy coraz częściej dyktują opisy badań do systemów rozpoznawania mowy (ASR). Ogólne modele,
takie jak Whisper, dobrze radzą sobie z mową potoczną. W dyktowaniu radiologicznym mylą się jednak
częściej: na terminologii, liczbach i jednostkach, skrótach i nazwach własnych. Błędy w opisie badania
obrazowego nie są sobie równe. Jedne są kosmetyczne, jak interpunkcja czy końcówka fleksyjna. Inne
zmieniają znaczenie kliniczne i lekarz może ich nie zauważyć:
- podmieniona strona ciała („prawy” → „lewy”),
- zły wymiar („45 mm” → „4 mm”),
- zgubione zaprzeczenie („bez zmian” → „zmian”),
- słowa wstawione, choć nikt ich nie powiedział (tzw. halucynacje).

**Pytania badawcze:**
1. Jak duży jest błąd rozpoznawania (WER, CER) polskich fraz z opisów radiologicznych dla gotowych,
   dostępnych rozwiązań ASR: otwartych modeli uruchamianych lokalnie i komercyjnych usług
   chmurowych?
2. Jakie typy błędów dominują (podmiany, pominięcia, wstawienia) i jaka ich część jest istotna
   klinicznie: terminy, liczby i jednostki, strona ciała, zaprzeczenia?
3. Które cechy nagrania zwiększają liczbę błędów: szum tła, cisza, długość, mikrofon, mówca, głos
   przetworzony lub syntetyczny?

*TODO: operacyjne definicje metryk i kategorii błędów, w tym błędu istotnego klinicznie.*

## 2. Powiązane prace

### 2.1 ADMEDVOICE i model `whisper-medium-medical-pl`

Korpus opisano w artykule Czyżewski i in., *A Comprehensive Polish Medical Speech Dataset for
Enhancing Automatic Medical Dictation*, Scientific Data 12:1436 (2025),
[doi:10.1038/s41597-025-05776-1](https://doi.org/10.1038/s41597-025-05776-1),
[PMC12357909](https://europepmc.org/articles/PMC12357909) (PubMed Central). Zespół pochodzi z Politechniki Gdańskiej
i Gdańskiego Uniwersytetu Medycznego, a projekt finansowało Narodowe Centrum Badań i Rozwoju (NCBR, grant INFOSTRATEG4/0003/2022).

**Jak powstał model.** Opis pochodzi z artykułu, karty modelu na Kaggle, notebooka autora oraz z
plików samego modelu (archiwum pobrane z Kaggle 2026-11-16: `adapter_config.json`,
`trainer_state.json`).

- **Model bazowy:** `openai/whisper-medium` (769M parametrów, licencja Apache 2.0). Notebook odczytuje
  go z konfiguracji adaptera (`PeftConfig.base_model_name_or_path`).
- **Metoda: LoRA** (artykuł tego nie mówi; wynika to z karty na Kaggle i z plików modelu).
  Konfiguracja adaptera, taka sama we wszystkich wariantach:

  | Parametr LoRA | Wartość |
  |---|---|
  | rank `r` | 16 |
  | `lora_alpha` | 32 |
  | `lora_dropout` | 0,05 |
  | moduły docelowe | `q_proj`, `v_proj` |
  | biblioteka | PEFT (ang. *parameter-efficient fine-tuning*, biblioteka Hugging Face) |

  Karta podaje 4,7M trenowanych parametrów, czyli około 0,6% modelu.
- **Parametry treningu według artykułu:**

  | Parametr | Wartość |
  |---|---|
  | Liczba kroków | maks. 10 000 |
  | Batch | 64 |
  | Learning rate | 1e-5 |
  | Wybór checkpointu | najniższy WER na walidacji |
  | Sprzęt | 1× NVIDIA A100 (karta graficzna, GPU) w PLGrid (polska infrastruktura obliczeniowa dla nauki), do 48 h na przebieg |
  | Biblioteki | PyTorch 2.5, transformers 4.48, Hugging Face (HF) datasets |
  | Audio | próbkowanie 16 kHz; nagrania dłuższe niż 30 s usunięte |

- **Parametry treningu według logów (`trainer_state.json`)** różnią się od artykułu:

  | Wariant | Batch | Learning rate (z nazwy katalogu) | Najlepszy krok | WER walidacji |
  |---|---:|---|---:|---:|
  | natural | 8 | — | 7 600 z 10 000 | 9,92 |
  | anonymized | 16 | — | 9 100 | 15,75 |
  | synthetic | 8 | — | 8 400 | 2,38 |
  | natural_anonym_synth | 64 | 1e-4 | 3 000 | 7,57 |
  | natural_anonym_synth_cv_fl | 32 | 1e-3 | 1 400 | 8,67 |

  Artykuł podaje jeden zestaw ustawień (batch 64, lr 1e-5, 10 000 kroków). Logi pokazują, że warianty
  trenowano z różnym batchem, a dla wariantów łączonych z wyższym learning rate. WER walidacji
  jest liczony na zbiorach walidacyjnych autorów, a nie na zbiorze testowym niniejszego badania.

- **Dane:** wszystkie kategorie ADMEDVOICE, nie tylko radiologia. Podział jest rozłączny po mówcach
  (deklaracja autorów):

  | Zbiór | Train | Val | Test |
  |---|---|---|---|
  | N+A+S (natural + anonymized + synthetic, łącznie) | 34 900 próbek (58 h) | 2 492 (4 h) | 12 468 (21 h) |
  | Natural | 7 404 (9,6 h) | 529 | 2 645 (3,4 h) |

  W zbiorze testowym każda unikalna fraza pojawia się średnio 4,6 razy.
- **Warianty:** archiwum na Kaggle zawiera pięć adapterów: `natural`, `anonymized`, `synthetic`,
  `natural_anonym_synth` i `natural_anonym_synth_cv_fl`. Notebook autora używa
  `natural_anonym_synth`.
- **Wyniki:** WER na teście natural, deklaracja autorów, w nawiasach 95% CI z bootstrapu.

  | Model | WER (natural test) |
  |---|---|
  | Whisper bazowy | 24,0 [22,3; 26,0] |
  | trening na natural | 15,5 [12,5; 19,8] |
  | trening na anonymized | 13,6 [12,1; 15,2] |
  | trening na N+A+S | 13,9 [12,4; 15,6] |
  | N+A+S + Common Voice + FLEURS | 9,5 [8,1; 11,1] |

  Wariant z Common Voice i FLEURS (WER 9,5) **jest** opublikowany. Opis modelu na Kaggle go nie
  wymienia, ale adapter `natural_anonym_synth_cv_fl` jest w archiwum.
- **Publikacja:** model na Kaggle `msxksm/whisper-medium-medical-pl` (Apache 2.0) i notebook
  `msxksm/transcribe-medical-pl-whisper-medium`. Wersja dla whisper.cpp to HF
  `fwasil162/whisper-medium-medical-pl-ggml`: adapter scalony z modelem bazowym, przekonwertowany
  do formatu ggml (format modeli biblioteki whisper.cpp) i skwantyzowany do q5_0 (wagi zapisane
  w ok. 5 bitach) — 514 MB. To repozytorium nie jest od autorów korpusu.

**Luki i niespójności istotne dla niniejszego badania:**
- **Artykuł raportuje zagregowany WER.** Nie zawiera on podziału błędów na typy ani oceny ich
  wagi klinicznej. Halucynacje są w nim cytowane z literatury, ale nie są mierzone. Tym właśnie
  zajmuje się niniejsze badanie.
- **Nie wiadomo, jak normalizowano tekst przed liczeniem WER.** Artykuł o tym nie pisze.
- **Niespójności w artykule:**
  - w tekście wyników WER 9,5% przypisano treningowi na nagraniach naturalnych, a tabela podaje 9,5
    dla wariantu z Common Voice i FLEURS;
  - przedziały ufności wariantów natural i anonymized nakładają się, więc teza, że trening na danych
    zanonimizowanych jest lepszy, nie jest dowiedziona.
- **Przeciek danych:** model trenowano na frazach ADMEDVOICE, więc na zbiorze testowym niniejszego badania
  zna frazy, które ma rozpoznać. Zostało to potwierdzone pomiarem, a model został wykluczony
  z porównania (sekcja 4.2).

### 2.2 Inne prace

- Kurowski, Zaporowski, Kostek, Czyżewski (ISD, International Conference on Information Systems
  Development 2025/2026): porównują metody PEFT (LoRA, DoRA, MoRA)
  na Whisper small, oceniając je na teście ADMEDVOICE.
  *TODO: przeczytać i opisać.*

## 3. Dane

### 3.1 Źródło

Polskie nagrania medyczne z korpusu **ADMEDVOICE**:
- Kaggle `karmarci/polish-medical-multi-source-corpus`,
- DOI (cyfrowy identyfikator obiektu) 10.34740/kaggle/ds/6698205,
- licencja CC BY 4.0 (Creative Commons, uznanie autorstwa).

Korpus zawiera 52 990 nagrań (88:19 h, dane autorów) w trzech wariantach:
- **naturalny** głos ludzki,
- **zanonimizowany**, czyli głos ludzki po konwersji metodą SALT (konwersja barwy głosu użyta
  przez autorów korpusu),
- **syntetyczny**, wygenerowany przez syntezator mowy (TTS, ang. *text-to-speech*).

Nagrania to czytane krótkie frazy, a nie spontaniczne dyktowanie całych opisów.

### 3.2 Wybór podzbioru radiologicznego

Z ośmiu kategorii tematycznych korpusu pozostawione zostały dwie radiologiczne:
- `02-001`: radiologia tarczycy, czyli frazy z opisów USG,
- `02-003`: radiologia głowy i szyi, w tym frazy z opisów tomografii komputerowej (TK)
  i rezonansu magnetycznego (MR).

Pozostałe kategorie (onkologia, kardiologia, resuscytacja, zalecenia, skierowania) zostały usunięte,
ponieważ nie są diagnostyką obrazową.

| Wariant | Nagrania | Mówcy | Teksty | Godziny |
|---|---:|---:|---:|---:|
| naturalny | 939 | 14 | 246 | 2,69 |
| zanonimizowany | 4 964 | 30 | 755 | 12,57 |
| syntetyczny | 1 740 | 6 | 290 | 2,89 |
| **Razem** | **7 643** | | **857** | **18,2** |

Długość nagrań została wyliczona z nagłówków plików WAV (nieskompresowany format audio). Frazy mają od 2 do 46 słów, średnio 15,8.

**Zbiór oceniający to wyłącznie nagrania naturalne.** Warianty zanonimizowany i syntetyczny służą
jako warunki porównawcze, bo pozwalają sprawdzić, czy przetworzony lub sztuczny głos zmienia
liczbę i rodzaj błędów modelu.

### 3.3 Budowa bazy

Skrypt `scripts/build_radiology_db.py` zbudował bazę SQLite (`recordings/radiology.sqlite`) oraz
pliki CSV (tabele tekstowe z wartościami rozdzielonymi przecinkami: `metadata.csv`, `phrases.csv`). Dla każdego nagrania baza zawiera:
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
| `rec_place` | `GU…` pomieszczenia Gdańskiego Uniwersytetu Medycznego (GUMed), `PG…` studio, `UNKNV` nagranie online, `SPGEN` syntezator. |
| `mic_code`, `mic` | Mikrofon, np. `NTG2` = RODE NTG-2, `ONLN` = online, `MODE` = synteza. |
| `text_id` | Identyfikator (ID) tekstu; klucz obcy do `phrases`. |
| `phrase_group` | Grupa identycznych tekstów (patrz „Problemy z danymi” niżej). |
| `phrase` | **Transkrypcja referencyjna** (spacje znormalizowane, Unicode NFC — kanoniczna postać złożona znaków). |
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
  głowy i szyi (np. MR twarzoczaszki, `text_id` 13289–13739). W bazie przypisano im kod `02-003`.
  Bez tej poprawki część naturalna głowy i szyi liczyłaby 39 nagrań zamiast 100.
- 60 nagrań ma niestandardowy separator (`_`) w nazwie pliku, a 23 nagrania zanonimizowane mają
  zastępczy znacznik czasu zamiast daty. Skrypt obsługuje oba przypadki.
- Ten sam tekst bywa wgrany pod różnymi `text_id`, bo autorzy poprawiali spacje i fleksję. Kolumna
  `phrase_group` łączy teksty identyczne po zmianie na małe litery i obcięciu końcowej kropki:
  857 `text_id` daje 773 grupy.

### 3.4 Powtórzenia i ryzyko przecieku między zbiorami

- **Identycznych plików nie ma.** Zostało to sprawdzone skrótem kryptograficznym MD5 próbek audio, z pominięciem
  nagłówka WAV.
- **449 nagrań zanonimizowanych to przekonwertowane nagrania naturalne.** Zostały dopasowane po
  `text_id` i identycznym znaczniku czasu w nazwie pliku. Potwierdza to korelacja obwiedni głośności:
  - liczona jako korelacja Pearsona logarytmu średniej kwadratowej amplitudy (log-RMS)
    w ramkach 10 ms,
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

### 4.1 Zakres: gotowe rozwiązania

Testowane są rozwiązania, które radiolog lub szpital może dziś wdrożyć bez własnego treningu:
- **Otwarte modele uruchamiane lokalnie (offline):**
  - Whisper medium (model bazowy z publikacji ADMEDVOICE), large-v3-turbo i large-v3,
  - modele z lat 2025–2026 z deklarowaną obsługą polskiego: NVIDIA Canary-1B-v2,
    NVIDIA Parakeet-TDT-0.6B-v3, Qwen3-ASR-1.7B, Cohere Transcribe 03-2026,
    NVIDIA Nemotron 3.5 Transcribe (wymaga wynajętej karty graficznej), Meta Omnilingual ASR,
  - NVIDIA FastConformer PL,
  - wav2vec2 XLSR-53 Polish (XLSR, ang. *cross-lingual speech representations*) i Meta MMS-1b-all,
    każdy bez modelu językowego (LM, ang. *language model*) i z ogólnym polskim KenLM
    (n-gramowy model językowy),
  - Google MedASR (model tylko angielski, jako kontrola negatywna).
- **Usługi chmurowe (online):**
  - ElevenLabs Scribe v2,
  - OpenAI whisper-1 i gpt-4o-transcribe,
  - Deepgram Nova-3,
  - Speechmatics, AssemblyAI, Soniox,
  - Google Chirp i Google Gemini (transkrypcja przez model multimodalny),
  - Azure AI Speech.

Obsługa polskiego przez nowe modele została sprawdzona w kartach modeli na Hugging Face (2026-11-17).

Aktualny plan z postępem i blokadami jest w `eval/asr_eval/plan.py` i na stronie `dashboard/`.

### 4.2 Wykluczone: modele dotrenowane na ADMEDVOICE

Z porównania wyłączone zostały modele dotrenowane na korpusie, z którego pochodzi zbiór testowy:
`whisper-medium-medical-pl` (wszystkie warianty LoRA) i VoxMedic (trenowany na `lion-ai/admed_voice`).

Pomiar wariantu N+A+S pokazał, że taki model zna frazy testowe:
- WER 1,46% wobec 13,9% deklarowanych przez autorów na ich teście;
- u każdego z 14 mówców WER mieści się w przedziale 0–10%, a jeden mówca ma 60 nagrań bez błędu;
- na frazach czytanych przez wielu mówców WER wynosi 0,9%, a na czytanych przez jednego 5,4%.

Podział autorów jest rozłączny po mówcach, ale nie po tekstach: te same frazy występują w korpusie
wielokrotnie, czytane przez różnych mówców oraz w wersjach zanonimizowanej i syntetycznej. Wynik
takiego modelu na ADMEDVOICE nie mierzy więc rozpoznawania nowej mowy.

### 4.3 Procedura

**Zbiór testowy:** 939 nagrań naturalnych (2,69 h, 14 mówców) z bazy `recordings/radiology.sqlite`.
Audio jest przepróbkowane do 16 kHz mono (soxr).

**Dekodowanie (identyczne w obrębie rodziny modeli, bez promptów i słowników):**
- Whisper: transformers, dekodowanie zachłanne (greedy), `language="pl"`, `task="transcribe"`, batch 8,
  połówkowa precyzja (fp16) na GPU Maca (MPS, ang. *Metal Performance Shaders*).
- Modele CTC (wav2vec2, MMS): greedy. Warianty „+ KenLM” używają beam search (pyctcdecode) z ogólnym
  polskim 5-gramowym modelem językowym z repozytorium `jonatasgrosman/wav2vec2-large-xlsr-53-polish`.
  Ten model językowy pochodzi z 2021 roku, czyli sprzed ADMEDVOICE, i nie zawiera np. słowa
  „hipoechogenny”.
- NVIDIA NeMo (FastConformer, Canary, Parakeet): domyślny dekoder modelu; Canary z
  `source_lang=target_lang="pl"`.
- Qwen3-ASR: pakiet `qwen-asr`, backend transformers, `language="Polish"`.
- Usługi chmurowe: każde nagranie wysyłane osobno, `language=pl`, bez promptu i bez słownika.

**Normalizacja tekstu** (`eval/asr_eval/textnorm.py`, taka sama dla referencji i hipotezy):
- małe litery, usunięta interpunkcja;
- wymiary rozdzielone („14x12x45” → „14 x 12 x 45”), jednostka odklejona od liczby („50mm” → „50 mm”);
- przecinek dziesiętny zachowany;
- usunięte znaczniki techniczne modeli (`</s>`, `<unk>`).

Liczby **nie** są zamieniane na słowa, bo w opisie badania oczekiwane są cyfry.

**Metryki** (`eval/asr_eval/metrics.py`, jiwer):
- **WER i CER** z 95% przedziałem ufności z bootstrapu po wypowiedziach (1000 losowań).
- **WER-N:** WER po zamianie liczb na słowa (num2words), „x” → „na” i jednostek zapisanych słownie
  na skróty. Oddziela błędy rozpoznania od formy zapisu liczb.
- **Kategorie istotne klinicznie:** odsetek błędnie rozpoznanych tokenów referencji (podmiana lub
  pominięcie) w trzech grupach:
  - liczby (tokeny z cyfrą),
  - zaprzeczenia („nie”, „bez”, „brak”),
  - strona ciała (prawy/lewy we wszystkich formach).
- **Wstawki ≥3:** miejsca, w których model wstawił co najmniej 3 słowa, których nie było (przybliżenie
  halucynacji).
- **RTF** (ang. *real-time factor*): czas przetwarzania podzielony przez długość audio (MacBook M1 Pro,
  16 GB pamięci operacyjnej).

**Dane wynikowe:**
- `results/<model>/hyp.jsonl`: surowe transkrypcje;
- `results/<model>/metrics.json`: metryki zbiorcze;
- `results/summary.csv`: zestawienie wszystkich modeli;
- baza `results/results.sqlite`, odtwarzana poleceniem `eval/build_results_db.py`:
  - tabele `runs`, `utterances` (wynik każdego nagrania) i `errors` (dziennik wszystkich błędów),
  - widoki według kategorii, mówcy i mikrofonu.

## 5. Eksperymenty i wyniki

### 5.1 Modele otwarte uruchamiane lokalnie (stan na 2026-11-17)

Liczby w procentach; WER z 95% CI. Kolumny „Liczby”, „Zaprzecz.” i „Strona” podają odsetek błędnie
rozpoznanych tokenów w danej kategorii (n = 1 990 / 399 / 599 tokenów w referencji).

| Model | WER [95% CI] | WER-N | CER | Liczby | Zaprzecz. | Strona | Wstawki ≥3 | RTF |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Whisper large-v3 | 8,03 [7,43–8,73] | 7,61 | 2,17 | 2,8 | 2,8 | 2,5 | 2 | 0,139 |
| Whisper large-v3-turbo | 9,75 [9,1–10,44] | 9,21 | 2,57 | 2,8 | 1,5 | 2,8 | 3 | 0,082 |
| Whisper medium | 13,77 [12,94–14,64] | 13,12 | 3,94 | 4,1 | 2,5 | 3,8 | 6 | 0,071 |
| NVIDIA Parakeet-TDT-0.6B-v3 | 18,21 [17,2–19,2] | 15,03 | 6,29 | 20,8 | 1,8 | 5,3 | 3 | 0,097 |
| NVIDIA Canary-1B-v2 | 20,05 [18,95–21,34] | 14,04 | 8,66 | 25,6 | 1,5 | 5,0 | 8 | 0,295 |
| Qwen3-ASR-1.7B | 21,8 [20,9–22,76] | 18,35 | 7,37 | 7,7 | 10,3 | 13,7 | 3 | 0,151 |
| Meta MMS-1b-all (pol) + KenLM | 32,07 [30,88–33,35] | 25,72 | 12,47 | 81,8 | 1,8 | 6,8 | 13 | 0,101 |
| Meta MMS-1b-all (adapter pol, bez LM) | 35,22 [33,87–36,48] | 27,46 | 13,17 | 57,3 | 6,3 | 11,0 | 36 | 0,088 |
| NVIDIA FastConformer PL (hybrid, P&C) | 50,7 [49,26–52,17] | 31,4 | 30,29 | 100,0 | 7,5 | 37,1 | 41 | 0,03 |
| wav2vec2 XLSR-53 Polish + KenLM | 52,8 [51,22–54,3] | 32,94 | 29,54 | 100,0 | 14,0 | 20,7 | 132 | 0,066 |
| wav2vec2 XLSR-53 Polish (bez LM) | 58,31 [56,67–59,69] | 41,08 | 30,68 | 100,0 | 23,8 | 25,5 | 121 | 0,07 |
| Google MedASR | 99,65 [99,21–100,08] | 99,01 | 80,48 | 98,2 | 100,0 | 100,0 | 41 | 0,011 |

**Wstępne obserwacje** (do potwierdzenia po dołożeniu usług chmurowych):
- **Whisper large-v3 jest najlepszy spośród modeli otwartych** (WER 8,0%), także wobec nowszych
  modeli z lat 2025–2026: NVIDIA Canary-1B-v2, Parakeet-TDT-0.6B-v3 i Qwen3-ASR-1.7B.
- **Nowe modele NVIDIA tracą głównie na zapisie liczb** (20–26% błędów w wymiarach). Po wyrównaniu
  formy zapisu (WER-N 14–15%) zbliżają się do Whisper medium.
- **Qwen3-ASR dobrze radzi sobie z liczbami, ale źle z zaprzeczeniami i stroną ciała** (10–14%
  błędów), czyli z kategoriami najgroźniejszymi klinicznie.
- **Ogólny polski model językowy poprawia modele CTC:** wav2vec2 z 58,3 do 52,8% WER, MMS z 35,2
  do 32,1%, a u MMS liczba długich wstawek spada z 36 do 13.
- **NVIDIA FastConformer PL myli stronę ciała w 37% przypadków** (np. „prawym” → „prawem”).
- **Google MedASR** (tylko angielski) daje WER ~100% zgodnie z oczekiwaniem dla kontroli
  negatywnej. Zamienia polską mowę na angielskie terminy medyczne („discharge”, „protein”),
  co ilustruje mechanizm halucynacji.

*TODO: usługi chmurowe, Cohere Transcribe, NVIDIA Nemotron 3.5 Transcribe.*

## 6. Dyskusja i ograniczenia

*TODO.*

## 7. Odtwarzalność

| Element | Wersja / źródło | Użycie |
|---|---|---|
| ADMEDVOICE | Kaggle, DOI 10.34740/kaggle/ds/6698205, CC BY 4.0 | dane |
| Python | 3.15.2 (biblioteka standardowa: `csv`, `sqlite3`, `struct`, `hashlib`) | budowa bazy, odczyt nagłówków WAV |
| SQLite | 3.43.2 | baza metadanych |
| NumPy | 2.5.5 (Python 3.12.16) | korelacja obwiedni głośności (analiza par, sekcja 3.4) |
| PyTorch | 2.15.0 (MPS) | inferencja modeli |
| transformers | 5.23.0 (Qwen3-ASR: 4.57.6 w osobnym środowisku) | Whisper, wav2vec2, MMS, MedASR |
| NVIDIA NeMo | 3.0.0 (osobne środowisko) | FastConformer, Canary, Parakeet |
| qwen-asr | z PyPI (osobne środowisko) | Qwen3-ASR |
| jiwer | z `eval/uv.lock` | WER, CER, wyrównanie |
| pyctcdecode + kenlm | 0.5.0 | dekodowanie CTC z modelem językowym |
| num2words | z `eval/uv.lock` | metryka WER-N |
| Sprzęt | MacBook Pro M1 Pro, 16 GB pamięci operacyjnej (RAM) | wszystkie przebiegi offline |

Odtworzenie danych:
1. pobranie ADMEDVOICE z Kaggle i rozpakowanie go do `recordings/`,
2. uruchomienie `python3 scripts/build_radiology_db.py recordings --move`.

Analiza par z sekcji 3.4 była jednorazowym skryptem uruchomionym w sesji. *TODO: przenieść ją do
`scripts/`.*

## Licencja i cytowanie danych

Dane: ADMEDVOICE, CC BY 4.0. Przy wykorzystaniu należy cytować korpus (DOI powyżej) i artykuł
w Scientific Data.
