<p align="center"><img src="assets/banner.svg" alt="Błędy modeli ASR w dyktowaniu polskich opisów diagnostyki obrazowej — porównanie tekstu podyktowanego z rozpoznanym: podmiana strony ciała, zły wymiar, zgubione zaprzeczenie, wstawione słowo" width="100%"></p>

# Błędy modeli ASR w dyktowaniu polskich opisów diagnostyki obrazowej

> Wersja robocza publikacji. Plik jest aktualizowany po każdym kroku badania (zasady w `CLAUDE.md`).
> Sekcje oznaczone *TODO* nie mają jeszcze wyników.

## Streszczenie

> **Wersja wstępna (2026-11-17):** wyniki modeli otwartych i siedmiu usług chmurowych są kompletne;
> w toku pozostają dwa najnowsze modele (Cohere Transcribe, NVIDIA Nemotron 3.5). Soniox, Google
> Chirp i Azure są zablokowane (brak środków/kluczy).

Porównane zostały gotowe systemy automatycznego rozpoznawania mowy (ASR, ang. *automatic speech
recognition*) na polskich frazach z opisów diagnostyki
obrazowej. Zbiór testowy to 939 nagrań głosu naturalnego (2,69 h, 14 mówców, ultrasonografia (USG) tarczycy oraz
radiologia głowy i szyi) z publicznego korpusu ADMEDVOICE. Poza WER (ang. *word error rate*: odsetek słów rozpoznanych błędnie, czyli
podmienionych, pominiętych lub wstawionych, względem liczby słów w tekście wzorcowym) i CER (ang.
*character error rate*: to samo liczone na znakach) mierzona jest przede wszystkim poprawność zapisu
**słownictwa radiologicznego**: TER (ang. *term error rate*: odsetek błędnie zapisanych wystąpień
terminów z ręcznie oznaczonego leksykonu 309 form) w porównaniu z tym samym wskaźnikiem dla słów ogólnych.

**Główny wynik: terminy radiologiczne są rozpoznawane 3–6 razy gorzej niż słowa ogólne w tych samych
nagraniach** (dotyczy modeli, które dobrze radzą sobie z ogólną polszczyzną). Najlepszy model otwarty, Whisper large-v3, zapisuje błędnie 15,8% wystąpień terminów (95% CI
14,8–17,1) i tylko 3,1% słów ogólnych. Ponad połowa błędów terminologicznych tego modelu to
*bliskie zapisy* („TIRADS” → „TIRAC”, „miąższ” → „miosz”, „color” → „kolor”, „dopplerowskim” →
„doplerowskim”): model słyszy termin, ale nie zna jego pisowni. Najtrudniejsze są skróty i nazwy
obce (TIRADS, PACS, color Doppler: błędy w 44–68% wystąpień) oraz złożenia pisane łącznie
(„okołotarczycowo”, „gładkokonturowany”), które modele rozbijają na dwa słowa. Wyższy odsetek błędów
dla terminów utrzymuje się także przy tej samej częstości słowa w ogólnej polszczyźnie, więc nie
wynika tylko z rzadkości słów.

Wśród 10 modeli otwartych uruchamianych lokalnie (12 konfiguracji, w tym warianty z modelem
językowym i kontrola negatywna) najlepszy jest **Whisper large-v3: WER 8,0%**
(95% przedział ufności, CI: 7,4–8,7) i TER 15,8%. Nowsze modele z lat
2025–2026 (NVIDIA Canary-1B-v2, Parakeet-TDT-0.6B-v3, Qwen3-ASR-1.7B) osiągają WER 18–22% i TER
29–39%; Qwen3-ASR myli ponad połowę wystąpień nazw jednostek chorobowych i zabiegów. Modele CTC (ang. *connectionist temporal classification*: wybierają literę
dla każdego fragmentu dźwięku osobno, bez wbudowanej wiedzy o języku) bez modelu językowego (wav2vec2,
Meta MMS, ang. *Massively Multilingual Speech*) mają WER 35–58%;
ogólny polski model językowy obniża go o 3–6 punktów procentowych (p.p.), czyli
względnie o ok. 9%.

Najlepszą usługą chmurową jest **OpenAI gpt-4o-transcribe** — WER 5,96% (CI 5,4–6,5), najlepszy
wynik w całym zestawieniu, wyprzedzający Whisper large-v3 (8,0%). OpenAI whisper-1 (9,9%),
AssemblyAI Universal-2 (10,3%) i Google Gemini 3.5 Flash (10,4%) plasują się tuż za nim, a Deepgram
Nova-3 i Speechmatics mają WER 15–19%. Najlepiej terminy zapisuje **Google Gemini 3.5 Flash**
(TER 6,6%, WER-N 4,2%) — to ogólny LLM, który „wygładza" treść, stąd jego surowy WER jest wyższy
niż po normalizacji. Osobnym przypadkiem jest **ElevenLabs Scribe v2**, który zapisuje liczby
słownie zamiast cyframi („2 mm" → „dwóch milimetrów"), przez co jego surowy WER (28,3%) jest
mylący; po wyrównaniu formy zapisu liczb (WER-N 5,2%) to trzeci najdokładniejszy system, a jego
TER (7,2%) drugi najniższy.

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
2. Jak poprawnie zapisywane jest słownictwo radiologiczne (anatomia, opis obrazu, jednostki
   chorobowe i zabiegi, skróty i nazwy obce) w porównaniu ze słowami ogólnymi w tych samych
   nagraniach? Jakiego rodzaju są te błędy: fleksja, podział na słowa, błędna pisownia słyszanego
   terminu, podmiana na inne słowo, pominięcie?
3. Które cechy nagrania zwiększają liczbę błędów: szum tła, cisza, długość, mikrofon, mówca, głos
   przetworzony lub syntetyczny?

Definicje operacyjne terminu, wskaźnika TER i kategorii błędów są w sekcji 4.4.

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

### 4.0 Etapy badania

Badanie jest podzielone na dwa etapy:
1. **Etap 1 (bieżący): modele bez pomocy.** Każdy system dostaje tylko nagranie i informację, że
   język to polski. Nie są używane prompty ze słownictwem, listy słów kluczowych (ang. *keyword
   boosting*), słowniki niestandardowe, kontekst medyczny ani korekta tekstu po rozpoznaniu.
   Etap mierzy, jak gotowe rozwiązanie radzi sobie „z pudełka”, i stanowi punkt odniesienia.
    Jedyny wyjątek to Google Gemini (ogólny LLM), który wymaga polecenia tekstowego: dostaje
    neutralną instrukcję „przepisz dosłownie”, bez słownictwa i bez wzmianki o medycynie.
2. **Etap 2 (planowany): modele z pomocą.** Te same systemy z dostępnymi w nich mechanizmami
   wsparcia (prompt lub lista terminów z leksykonu, słowniki niestandardowe usług chmurowych)
   oraz z korektą pisowni terminów po rozpoznaniu. Wynik etapu 2 jest porównywany z etapem 1.

Wszystkie wyniki w sekcji 5 pochodzą z etapu 1.

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
  - Google Chirp i Google Gemini 3.5 Flash (transkrypcja przez ogólny LLM),
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
- Usługi chmurowe (`eval/asr_eval/cloud.py`): każde nagranie wysyłane osobnym żądaniem jako WAV
  16 kHz mono, `language=pl`, bez promptu i bez słownika (etap 1); do 8 żądań równolegle. Wyjątek
  to Google Gemini (ogólny multimodalny LLM `gemini-3.5-flash`), który przez API `generateContent`
  dostaje neutralne „przepisz dosłownie" — bez słownictwa i bez kontekstu medycznego. Usługi
  asynchroniczne (Speechmatics, Soniox, AssemblyAI) są odpytywane o wynik, a pliki i zadania
  usuwane z ich serwerów po odczytaniu transkrypcji. RTF usług chmurowych obejmuje czas sieci
  i kolejki, więc nie jest porównywalny z modelami lokalnymi.

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

### 4.4 Rozpoznawanie słownictwa radiologicznego

**Leksykon terminów** (`eval/lexicon/radiology_terms.tsv`). Słownik referencji zbioru testowego po
normalizacji liczy 736 typów słów bez cyfr, więc został oznaczony w całości, ręcznie, a nie filtrem
częstości. Adnotację wykonał model językowy Claude Opus 5.5 (Anthropic) z regułami zapisanymi w nagłówku pliku; nie była
jeszcze weryfikowana przez radiologa. Każda forma terminu ma lemat i jedną z czterech klas:

| Klasa | Zawartość | Formy | Lematy | Wystąpienia w referencjach |
|---|---|---:|---:|---:|
| anatomia (`anatomy`) | narządy i okolice oraz przymiotniki od nich: tarczyca, płat, cieśń, miąższ, przygardłowy | 112 | 68 | 2 326 |
| opis obrazu (`descriptor`) | echogeniczność, echostruktura, unaczynienie, morfologia zmiany, sekwencje i techniki | 114 | 59 | 2 142 |
| patologia i zabiegi (`pathology`) | zapalenie, guzek, limfadenopatia, biopsja, parotidektomia | 54 | 35 | 410 |
| skróty i nazwy obce (`acronym`) | TIRADS, USG, DWI, PACS, color Doppler, Hashimoto, Gadovist | 29 | 29 | 551 |
| **terminy razem** | | **309** | **191** | **5 429** |
| słowa ogólne (grupa porównawcza) | pozostałe słowa bez cyfr: prawidłowy, wielkość, zmiana, położona, prawy | 424 | 319 | 9 405 |

Liczby, jednostki i znak wymiaru „x” nie należą do żadnej grupy. Dwie formy z błędem pisowni
w referencji („wiekości” zamiast „wielkości”, 13 wystąpień; „hiperechegennicznym”) zostały pominięte
w obu grupach.

**Los każdego słowa referencji** (`eval/terms.py`). Na wyrównaniu jiwer (po normalizacji z sekcji 4.3)
każde wystąpienie słowa referencji dostaje jeden status, sprawdzany w tej kolejności:
1. *poprawne*: forma identyczna;
2. *podział na słowa*: te same litery, inny podział (rozbicie „okołotarczycowo” → „około
   tarczycowo” albo sklejenie „płynowo lita” → „płynowolita”, „ti rads” → „tirads”);
3. *pominięcie*: słowo nie ma odpowiednika w hipotezie;
4. *inna forma*: ten sam lemat, inna forma fleksyjna („przepływu” → „przepływów”). Lematy form
   z referencji pochodzą z leksykonu, a słów hipotezy z lematyzatora simplemma;
5. *bliski zapis*: odległość edycyjna na znakach (Levenshteina) ≤ max(1, round(0,3 · długość słowa));
   wyjątkiem jest zmiana przedrostka niosącego znaczenie (nie-, hipo-, hiper-, izo-, normo-),
   np. „niejednorodny” → „jednorodne”, która zawsze liczy się jako podmiana;
6. *podmiana*: każde inne słowo.

**Wskaźniki:**
- **TER** (ang. *term error rate*): odsetek wystąpień terminów o statusie innym niż *poprawne*;
- **TER-L** (wersja łagodna): liczone są tylko *bliski zapis*, *podmiana* i *pominięcie*. Inna
  forma fleksyjna i podział na słowa nie są błędem, bo lekarz zwykle nie musi ich poprawiać
  w znaczeniu, a jedynie w zapisie;
- **GWER** (ang. *general word error rate*): odsetek błędów liczony tak samo jak TER, dla słów
  ogólnych. Iloraz TER/GWER mówi, ile razy trudniejsze dla modelu są terminy;
- 95% CI z bootstrapu po wypowiedziach (1000 losowań, seed 0), jak dla WER.

**Rzadkość a terminologia.** Żeby oddzielić efekt dziedziny od efektu rzadkości słowa, odsetek
błędów policzono osobno w przedziałach częstości słowa w ogólnej polszczyźnie (skala Zipfa:
log10 liczby wystąpień na miliard słów, biblioteka wordfreq 3.1.1).

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

**Obserwacje:**
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

*TODO: Cohere Transcribe, NVIDIA Nemotron 3.5 Transcribe.*

### 5.2 Usługi chmurowe (online, stan na 2026-11-17)

Kolumny jak w sekcji 5.1. RTF obejmuje czas sieci i kolejki, więc nie jest porównywalny z modelami
lokalnymi (sekcja 4.3).

| Model | WER [95% CI] | WER-N | CER | Liczby | Zaprzecz. | Strona | Wstawki ≥3 | RTF |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| OpenAI gpt-4o-transcribe | 5,96 [5,4–6,52] | 4,47 | 2,03 | 1,9 | 2,0 | 2,7 | 1 | 0,021 |
| OpenAI whisper-1 | 9,93 [9,26–10,62] | 9,45 | 2,58 | 3,5 | 3,3 | 3,5 | 1 | 0,032 |
| AssemblyAI Universal-2 | 10,25 [9,54–10,96] | 9,71 | 2,77 | 3,5 | 2,8 | 3,8 | 1 | 0,265 |
| Google Gemini 3.5 Flash | 10,4 [9,75–11,09] | 4,18 | 4,03 | 3,0 | 1,0 | 3,0 | 8 | 0,076 |
| Deepgram Nova-3 | 15,06 [14,3–15,84] | 8,48 | 7,88 | 8,0 | 3,5 | 2,5 | 6 | 0,018 |
| Speechmatics (pl) | 19,41 [18,68–20,18] | 16,37 | 6,18 | 16,1 | 0,3 | 7,0 | 1 | 0,03 |
| ElevenLabs Scribe v2 | 28,27 [26,22–30,33] | 5,22 | 23,53 | 97,7 | 1,3 | 1,7 | 65 | 0,037 |

**Obserwacje:**
- **OpenAI gpt-4o-transcribe jest najlepszym systemem w całym zestawieniu** (WER 5,96%, CER 2,03%,
  WER-N 4,47%, najniższy odsetek błędów w liczbach: 1,9%). Wyprzedza najlepszy model otwarty
  Whisper large-v3 (8,03%) i wszystkich konkurentów chmurowych. Aż 54% wypowiedzi transkrybuje
  bezbłędnie (Whisper large-v3: 39,6%).
- **Google Gemini 3.5 Flash jest najlepszy w zapisie terminów** (TER 6,6% — najniżej ze wszystkich,
  wobec 15,8% u Whisper large-v3) i w WER-N (4,18%) oraz najrzadziej myli zaprzeczenia (1,0%).
  Jego surowy WER (10,4%) jest wyższy, bo ogólny LLM „wygładza" treść (interpunkcja, podział
  wyrazów, 8 dłuższych wstawek), co metryka WER liczy jako błąd.
- **OpenAI whisper-1 (9,93%)** i AssemblyAI Universal-2 (10,25%) plasują się tuż za Whisper
  large-v3, ale przed Whisper medium (13,77%). AssemblyAI prawie nie wstawia dłuższych fraz
  (1 wstawka).
- **ElevenLabs Scribe v2 zapisuje liczby słownie**, co sztucznie zawyża WER: „2 mm" →
  „dwóch milimetrów", „14x12x45 mm" → „czternaście na dwanaście na czterdzieści pięć
  milimetrów", „10,9 ml" → „dziesięć i dziewięć dziesiątych mililitra". Dotyczy to 97,7% tokenów
  z cyfrą i podnosi CER do 23,53%. Po wyrównaniu formy zapisu liczb (WER-N) ElevenLabs osiąga
  5,22% — drugi najlepszy wynik po gpt-4o-transcribe. Równocześnie ma najwięcej długich wstawek
  (65 wobec 1–6 u pozostałych), co sugeruje „wygładzanie" treści zamiast dosłownej transkrypcji.
- **Speechmatics**, mimo deklarowanego modelu medycznego, nie wyróżnia się: WER 19,41%, najgorzej
  ze stroną ciała (7,0%) i z liczbami (16,1%).
- **Deepgram Nova-3** jest najszybszy (RTF 0,018) i bliski AssemblyAI w WER-N (8,48%).

**Usługi niedostępne w tym przebiegu:** Soniox (brak środków, `organization_balance_exhausted`),
Google Chirp (wymaga projektu i poświadczeń Google Cloud), Azure AI Speech (brak klucza).
Dedykowany model transkrypcyjny Google `gemini-3.5-transcribe` ma limit 100 żądań/dzień na
tierze 1 (AI Studio), więc na pełnym zbiorze (939 nagrań) nie da się go zmierzyć w jednym dniu;
zamiast niego zmierzony został ogólny model `gemini-3.5-flash` (transkrypcja przez LLM).

### 5.3 Słownictwo radiologiczne (stan na 2026-11-17)

Te same transkrypcje co w sekcjach 5.1 i 5.2, ocenione metodą z sekcji 4.4. Wartości w procentach.
Kolumny „Inna forma” … „Pominięcie” podają odsetek wszystkich wystąpień terminów (n = 5 429);
ich suma to TER.

| Model | TER [95% CI] | TER-L | GWER | TER/GWER | Inna forma | Podział | Bliski zapis | Podmiana | Pominięcie |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Whisper large-v3 | 15,8 [14,8–17,1] | 13,0 | 3,1 | 5,1 | 0,9 | 2,0 | 8,7 | 3,4 | 0,8 |
| Whisper large-v3-turbo | 19,5 [18,4–20,8] | 16,5 | 3,4 | 5,7 | 1,1 | 1,9 | 11,4 | 4,1 | 1,0 |
| Whisper medium | 27,0 [25,6–28,4] | 23,6 | 5,6 | 4,8 | 1,3 | 2,1 | 15,1 | 7,2 | 1,3 |
| NVIDIA Parakeet-TDT-0.6B-v3 | 28,9 [27,6–30,3] | 25,3 | 5,9 | 4,9 | 1,0 | 2,7 | 14,9 | 7,4 | 3,0 |
| NVIDIA Canary-1B-v2 | 30,1 [28,8–31,4] | 26,3 | 5,7 | 5,3 | 1,5 | 2,3 | 14,5 | 10,0 | 1,8 |
| Meta MMS-1b-all (pol) + KenLM | 30,3 [28,9–31,5] | 24,1 | 9,0 | 3,4 | 1,5 | 4,8 | 14,8 | 7,0 | 2,2 |
| Meta MMS-1b-all (bez LM) | 39,3 [37,8–40,7] | 35,3 | 14,1 | 2,8 | 1,2 | 2,8 | 24,2 | 8,0 | 3,0 |
| Qwen3-ASR-1.7B | 39,3 [37,7–40,7] | 33,9 | 10,2 | 3,8 | 3,0 | 2,3 | 20,1 | 10,8 | 3,0 |
| wav2vec2 XLSR-53 Polish + KenLM | 46,0 [44,5–47,4] | 40,0 | 26,0 | 1,8 | 1,6 | 4,4 | 18,4 | 18,7 | 2,9 |
| NVIDIA FastConformer PL | 53,9 [52,3–55,3] | 49,2 | 23,2 | 2,3 | 1,7 | 3,0 | 22,4 | 20,7 | 6,1 |
| wav2vec2 XLSR-53 Polish (bez LM) | 54,9 [53,3–56,3] | 49,7 | 31,9 | 1,7 | 1,6 | 3,7 | 22,9 | 22,4 | 4,4 |
| Google MedASR (kontrola negatywna) | 97,6 [97,2–98,1] | 97,6 | 98,1 | 1,0 | 0,0 | 0,0 | 0,5 | 50,1 | 47,1 |

Usługi chmurowe (te same kolumny):

| Model | TER [95% CI] | TER-L | GWER | TER/GWER | Inna forma | Podział | Bliski zapis | Podmiana | Pominięcie |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Google Gemini 3.5 Flash | 6,6 [5,8–7,4] | 4,8 | 4,0 | 1,6 | 1,3 | 0,4 | 2,8 | 1,6 | 0,5 |
| ElevenLabs Scribe v2 | 7,2 [6,4–8,1] | 5,7 | 10,1 | 0,7 | 0,6 | 0,9 | 3,7 | 1,6 | 0,4 |
| OpenAI gpt-4o-transcribe | 7,6 [6,8–8,5] | 4,5 | 2,9 | 2,6 | 1,4 | 1,7 | 1,8 | 2,2 | 0,5 |
| Deepgram Nova-3 | 16,6 [15,3–17,9] | 13,9 | 11,1 | 1,5 | 1,2 | 1,5 | 7,6 | 4,4 | 1,9 |
| OpenAI whisper-1 | 19,1 [17,9–20,3] | 15,5 | 3,7 | 5,2 | 1,3 | 2,3 | 9,8 | 4,7 | 0,9 |
| AssemblyAI Universal-2 | 19,3 [18,0–20,6] | 15,8 | 4,3 | 4,5 | 1,1 | 2,4 | 9,8 | 4,9 | 1,1 |
| Speechmatics (pl) | 29,2 [27,9–30,4] | 23,0 | 6,7 | 4,4 | 2,4 | 3,8 | 11,4 | 10,1 | 1,6 |

TER według klasy terminu (wybrane modele; pełna tabela: `results/terms/by_class.csv`):

| Model | Anatomia | Opis obrazu | Patologia i zabiegi | Skróty i nazwy obce |
|---|---:|---:|---:|---:|
| Whisper large-v3 | 12,2 | 12,6 | 15,9 | 43,9 |
| Whisper large-v3-turbo | 13,5 | 17,4 | 15,1 | 56,8 |
| NVIDIA Parakeet-TDT-0.6B-v3 | 23,3 | 24,0 | 33,4 | 68,2 |
| NVIDIA Canary-1B-v2 | 27,7 | 23,7 | 33,4 | 62,4 |
| Qwen3-ASR-1.7B | 30,0 | 40,6 | 58,1 | 59,4 |

![Odsetek błędów a częstość słowa w ogólnej polszczyźnie](assets/terms_vs_frequency.svg)

**Obserwacje:**
- **Terminy są 3,4–5,7 razy trudniejsze niż słowa ogólne** dla siedmiu modeli z GWER ≤ 10,2%
  (Whisper, NVIDIA Canary i Parakeet, Qwen3-ASR, MMS + KenLM). Iloraz TER/GWER spada do 1,7–2,8
  u modeli, które źle rozpoznają także zwykłą polszczyznę (MMS bez LM, wav2vec2, FastConformer),
  i do 1,0 w kontroli negatywnej.
- **Wyjątkiem jest ElevenLabs Scribe v2: terminy są dla niego łatwiejsze niż słowa ogólne**
  (TER/GWER 0,7; TER 7,2% — najlepszy wynik w całym zestawieniu, wobec 15,8% u Whisper large-v3).
  Wysoki GWER (10,1%) przy niskim TER sugeruje, że ElevenLabs lepiej utrwala rzadkie terminy
  (być może dzięki zapisowi liczbowemu/słownemu i „wygładzaniu”), a myli się raczej na słowach
  pospolitych i spójnikach.
- **Dominuje bliski zapis, nie podmiana na inne słowo.** U Whisper large-v3 8,7 z 15,8 p.p. TER
  to zapisy bliskie poprawnemu: model rozpoznaje brzmienie terminu, ale go nie zna. Najczęstsze:
  „TIRADS” → „TIRAC”/„TIRATS”/„TIRAS” (104 ze 176 wystąpień), „color” → „kolor” (34),
  „miąższ” → „miosz”/„miąż” (19), „guzki” → „głuski”/„guski” (15), „cieśń” → „cieść” (8).
  To wskazuje, że słownik podpowiedzi lub korekta pisowni po rozpoznaniu mogłyby usunąć dużą część
  błędów bez zmiany modelu akustycznego; zostanie to sprawdzone w etapie 2 (sekcja 4.0).
- **Złożenia pisane łącznie są rozbijane** („okołotarczycowo” → „około tarczycowo”,
  „gładkokonturowany” → „gładko konturowany”): 2–5% wystąpień terminów.
- **Najtrudniejsza klasa to skróty i nazwy obce** (44–68% błędów). Sam TIRADS odpowiada za 18%
  błędów terminologicznych Whisper large-v3; po wyłączeniu skrótów TIRADS, EU, CD i color TER
  tego modelu spada z 15,8 do 12,8%.
- **Qwen3-ASR wyróżnia się słabością w nazwach chorób i zabiegów** (58% błędów: „limfadenopatii”,
  „autoimmunologicznym”, „parotidektomii”) i w przymiotnikach echogeniczności („hipoechogenny”:
  87% błędów wobec 20% u Whisper large-v3).
- **Efekt dziedziny nie sprowadza się do rzadkości słów.** Słowa nieobecne w ogólnym korpusie
  (Zipf < 1, np. „hipoechogenna”) są najtrudniejsze dla wszystkich modeli (30% błędów u Whisper
  large-v3). Jednak także przy tej samej częstości ogólnej (Zipf 3–5) terminy mają 10–13% błędów,
  a słowa ogólne 2–3% (Whisper large-v3; wykres powyżej, dane `results/terms/by_zipf.csv`). Słowa
  takie jak „płat”, „miąższ” czy „cieśń” są znane z polszczyzny ogólnej, ale w kontekście
  radiologicznym modele zapisują je gorzej.
- Terminy najczęściej mylone przez trzy najlepsze modele (średnio, lematy z ≥ 10 wystąpieniami):
  gładkokonturowany (97%), PACS (95%), TIRADS (94%), torbielowaty (92%), dopplerowski (82%),
  okołotarczycowy (79%), normoechogeniczny (75%). Pełna lista: `results/terms/by_lemma.csv`.

**Ograniczenia tej analizy:**
- leksykon oznaczył model językowy, bez weryfikacji przez radiologa; granica między terminem
  a słowem ogólnym jest umowna (np. „zmiana”, „prawidłowy” zostały uznane za ogólne);
- korpus obejmuje tylko dwie kategorie (USG tarczycy, głowa i szyja), więc słownictwo jest wąskie,
  a pojedyncze terminy (TIRADS: 176 wystąpień) mają duży wpływ na wynik;
- próg bliskiego zapisu (30% długości słowa) jest arbitralny; dla krótkich słów może zaliczyć
  do tej kategorii rzeczywiście inne słowo („płat” → „płot”);
- „color” → „kolor” to raczej spolszczenie pisowni niż błąd rozpoznania, a mimo to liczy się
  jako błąd.

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
| wordfreq | 3.1.1 | częstość słów w ogólnej polszczyźnie (skala Zipfa) |
| simplemma | 2.0.0 | lematy słów hipotezy (analiza terminów) |
| matplotlib | 3.11.2 | wykres `assets/terms_vs_frequency.svg` |
| google-auth, requests | z `eval/uv.lock` | opcjonalna ścieżka Vertex AI (nieużywana w bieżących wynikach) |
| Sprzęt | MacBook Pro M1 Pro, 16 GB pamięci operacyjnej (RAM) | wszystkie przebiegi offline |

Analizę terminów (sekcja 5.3) odtwarza `cd eval && uv run python terms.py` (ok. 30 s na M1 Pro);
zapisuje `results/terms/*.csv`, wykres i tabelę `term_tokens` w `results/results.sqlite`.
Polecenie trzeba uruchomić ponownie po `build_results_db.py`, bo ten odbudowuje bazę od zera.

Odtworzenie danych:
1. pobranie ADMEDVOICE z Kaggle i rozpakowanie go do `recordings/`,
2. uruchomienie `python3 scripts/build_radiology_db.py recordings --move`.

Analiza par z sekcji 3.4 była jednorazowym skryptem uruchomionym w sesji. *TODO: przenieść ją do
`scripts/`.*

## Licencja i cytowanie danych

Dane: ADMEDVOICE, CC BY 4.0. Przy wykorzystaniu należy cytować korpus (DOI powyżej) i artykuł
w Scientific Data.
