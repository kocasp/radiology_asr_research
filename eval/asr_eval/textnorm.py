"""Normalizacja tekstu przed liczeniem WER/CER (wersja v1).

Zasady (identyczne dla referencji i hipotezy):
1. Unicode NFC, małe litery.
2. Wymiary: „14x12x45”, „14 x 12 × 45” -> „14 x 12 x 45” (znak „x” między liczbami jako osobny token).
   Jednostka sklejona z liczbą jest odklejana: „50mm” -> „50 mm”, „1,5cm” -> „1,5 cm” (tylko przejście
   cyfra -> litera; „L4”, „Th12”, „C5” zostają bez zmian).
3. Przecinek dziesiętny zostaje częścią liczby („3,7”); pozostała interpunkcja jest usuwana.
4. Myślniki/ukośniki między słowami -> spacja; wielokrotne spacje -> jedna.
5. Znaczniki techniczne modeli (</s>, <unk>, [unintelligible], <|...|>) są usuwane.
Liczby NIE są zamieniane na słowa: „45” vs „czterdzieści pięć” liczy się jako błąd — w opisie
badania forma zapisu ma znaczenie, a model dyktowania powinien zwrócić cyfry.
"""
import re
import unicodedata

_DIM = re.compile(r"(?<=\d)\s*[x×]\s*(?=\d)")
_UNIT = re.compile(r"(?<=\d)(?=[^\W\d_])", re.UNICODE)
_DEC = re.compile(r"(?<=\d)[,.](?=\d)")
_PUNCT = re.compile(r"[^\w\s\u0001]", re.UNICODE)


_SPECIAL = re.compile(r"</?s>|<unk>|<pad>|\[unintelligible\]|<\|[^|>]*\|>", re.I)


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFC", _SPECIAL.sub(" ", text or "")).lower()
    t = _DIM.sub(" x ", t)
    t = _UNIT.sub(" ", t)
    t = _DEC.sub("\u0001", t)            # chroń przecinek/kropkę dziesiętną
    t = re.sub(r"[-–—/]", " ", t)
    t = _PUNCT.sub(" ", t)
    t = t.replace("_", " ").replace("\u0001", ",")
    return re.sub(r"\s+", " ", t).strip()


# --- wariant „mówiony” (metryka WER-N) -------------------------------------------------------------
# Oddziela błędy rozpoznania od formy zapisu liczb: po zwykłej normalizacji liczby zamieniane są na
# słowa (num2words, mianownik), „x” między liczbami -> „na”, a słownie zapisane jednostki -> skróty.
# Przykład: „20x14 mm” i „dwadzieścia na czternaście milimetrów” dają ten sam tekst.
_UNITS = [(re.compile(r"^milimetr\w*$"), "mm"), (re.compile(r"^centymetr\w*$"), "cm"),
          (re.compile(r"^mililitr\w*$"), "ml"), (re.compile(r"^procent\w*$"), "%")]
_NUM = re.compile(r"^\d+(,\d+)?$")


def _num_words(tok):
    from num2words import num2words
    try:
        return num2words(float(tok.replace(",", ".")) if "," in tok else int(tok), lang="pl")
    except Exception:
        return tok


def normalize_spoken(text: str) -> str:
    toks = normalize(text).split()
    out = []
    for i, t in enumerate(toks):
        if t == "x" and 0 < i < len(toks) - 1 and _NUM.match(toks[i - 1]) and _NUM.match(toks[i + 1]):
            out.append("na"); continue
        for rx, u in _UNITS:
            if rx.match(t):
                t = u; break
        out.append(_num_words(t) if _NUM.match(t) else t)
    return re.sub(r"\s+", " ", " ".join(out)).strip()
