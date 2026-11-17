# halucination_research — błędy ASR w dyktowaniu opisów diagnostyki obrazowej (PL)

Badamy, jak i dlaczego modele ASR (np. Whisper) mylą się przy dyktowaniu polskich opisów
radiologicznych. Mierzymy ogólny poziom błędu (WER, CER) i typy błędów: podmiany, pominięcia,
wstawienia. Główny temat: poprawny zapis słownictwa radiologicznego (terminy anatomiczne, opisu obrazu,
jednostek chorobowych, skróty) w porównaniu ze słowami ogólnymi; leksykon terminów:
`eval/lexicon/radiology_terms.tsv`, analiza: `eval/terms.py`. Halucynacje są tylko jedną z kategorii
błędów, a nie głównym tematem.
Dane opisuje `recordings/README.md`.

Nazwa repo (`halucination_research`) jest historyczna. Temat to błędy ASR w ogóle.

**To autonomiczny projekt.** Nie przeszukuj, nie czytaj i nie cytuj plików z nadrzędnego katalogu
`exrais/` (jego CLAUDE.md, README, briefs/, status/, data/, asr/…). Wiedza z zewnątrz pochodzi tylko
ze świeżego researchu ze źródłami, zapisanego w README tego repo.

## Cel: publikacja i landing page

Z projektu mają powstać:
1. **artykuł naukowy** do złożenia w czasopiśmie,
2. **landing page** z opisem eksperymentu, do CV.

Oba powstaną z pliku `halucination_research/README.md` (README w katalogu głównym tego repo, nie
`recordings/README.md` i nie README projektu exrais). Dlatego README musi być na bieżąco i tak
kompletne, żeby dało się z niego napisać artykuł bez zaglądania do historii rozmów.

## Zasada: sposób dojścia do wyniku zapisujemy w README.md

Po każdym nowym kroku, eksperymencie lub wyniku dopisz do `halucination_research/README.md`:

- **Jak doszliśmy do analizy błędów ASR:** pytania badawcze, przyjęte założenia, definicje metryk
  i kategorii błędów, sposób ich wykrywania.
- **Każde doświadczenie:**
  - co uruchomiono i na jakich danych (wycinek, liczba nagrań, filtry, zapytanie SQL),
  - jakie parametry,
  - jakie wyniki, z liczbami i informacją, jak je zmierzono,
  - wnioski i ograniczenia.
- **Algorytmy i metody:** normalizacja tekstu, metryki (WER, CER, wskaźniki typów błędów), dopasowania,
  progi, augmentacje.
- **Biblioteki, modele i narzędzia:** nazwa, dokładna wersja lub checkpoint, do czego użyte. Linki do
  źródeł i licencje.
- **Odtwarzalność:** skrypt, który daje dany wynik (ścieżka w repo), seed, sprzęt, czas obliczeń.

Przy pisaniu pilnuj, żeby:
- **README opisywał aktualną metodę.** Gdy zmieniamy podejście, nowy sposób zastępuje stary i opis
  poprzedniego można usunąć. Zostaw najwyżej jedno zdanie o tym, dlaczego zmieniliśmy podejście,
  jeśli to wnosi coś do publikacji (np. „podejście X zawyżało WER, bo…”).
- **Liczby pochodziły z pomiarów, a nie z przeczucia.** Oddzielaj to, co zweryfikowane, od tego, co
  deklarują autorzy modeli lub korpusów.
- **Każdy skrót był rozwinięty i wyjaśniony przy pierwszym użyciu**, np. „WER (ang. *word error rate*:
  odsetek błędnie rozpoznanych słów)”. Dotyczy też nazw technicznych (LoRA, CTC, KenLM, fp16).
- **README był pisany w formie bezosobowej:** „porównane zostały”, „zmierzono”, a nie „porównaliśmy”,
  „mierzymy”, i bez trybu rozkazującego („należy pobrać”, a nie „pobierz”).
- **README był pisany stylem artykułu:** wnioski na początku, potem metoda i wyniki, potem ograniczenia.
  Tabele i wykresy zapisuj w repo i linkuj z README.
- **Informacje o danych były w `recordings/README.md`.** Główny README tylko do niego odsyła
  i streszcza najważniejsze fakty.

## Zasady techniczne

- **Etap 1 (bieżący): modele bez pomocy.** Żadnych promptów ze słownictwem, list słów kluczowych,
  słowników niestandardowych ani korekty po rozpoznaniu; tylko `language=pl`. Google Gemini dostaje
  wyłącznie neutralne „przepisz dosłownie”. Wsparcie (prompty, słowniki, korekta) to etap 2, mierzony
  osobno i porównywany z etapem 1. Szczegóły: README, sekcja 4.0.
- **Testujemy tylko gotowe, dostępne rozwiązania.** Nie oceniamy modeli dotrenowanych na ADMEDVOICE
  (np. whisper-medium-medical-pl, VoxMedic), bo znają frazy testowe. Uzasadnienie: README, sekcja 4.2.
- Audio (`recordings/audio/`, 5,6 GB) nie jest w Git. Odtwarza się je skryptem
  `scripts/build_radiology_db.py`.
- Do oceny ASR używaj nagrań `source='natural'`. Przy podziale na train/test nagrania anonymized,
  które są przetworzonymi wersjami nagrań naturalnych, muszą być po tej samej stronie co oryginał
  (szczegóły w `recordings/README.md`, sekcja „Powtórzenia nagrań”).
- Dane są publiczne: ADMEDVOICE, CC BY 4.0. Przy publikacji podaj źródło (DOI
  10.34740/kaggle/ds/6698205).
