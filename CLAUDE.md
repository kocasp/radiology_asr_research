# halucination_research — błędy ASR w dyktowaniu opisów diagnostyki obrazowej (PL)

Badamy, jak i dlaczego modele ASR (np. Whisper) mylą się przy dyktowaniu polskich opisów
radiologicznych. Mierzymy ogólny poziom błędu (WER, CER) i typy błędów: podmiany, pominięcia,
wstawienia. Sprawdzamy też, które błędy są istotne klinicznie: terminy, liczby i jednostki, strona
ciała, zaprzeczenia. Halucynacje są tylko jedną z kategorii błędów, a nie głównym tematem.
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
- **README był pisany stylem artykułu:** wnioski na początku, potem metoda i wyniki, potem ograniczenia.
  Tabele i wykresy zapisuj w repo i linkuj z README.
- **Informacje o danych były w `recordings/README.md`.** Główny README tylko do niego odsyła
  i streszcza najważniejsze fakty.

## Zasady techniczne

- Audio (`recordings/audio/`, 5,6 GB) nie jest w Git. Odtwarza się je skryptem
  `scripts/build_radiology_db.py`.
- Do oceny ASR używaj nagrań `source='natural'`. Przy podziale na train/test nagrania anonymized,
  które są przetworzonymi wersjami nagrań naturalnych, muszą być po tej samej stronie co oryginał
  (szczegóły w `recordings/README.md`, sekcja „Powtórzenia nagrań”).
- Dane są publiczne: ADMEDVOICE, CC BY 4.0. Przy publikacji podaj źródło (DOI
  10.34740/kaggle/ds/6698205).
