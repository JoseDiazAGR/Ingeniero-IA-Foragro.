"""
Normalización de texto para síntesis de voz (TTS) en español hondureño.

El TTS de OpenAI detecta el idioma a partir del texto; los dígitos, siglas
("WP", "SC"), símbolos ("%", "/", "L.") y nombres de archivo lo hacen leer en
inglés o pronunciar cosas que no deben oírse. Aquí convertimos todo a palabras
en español ANTES de sintetizar. El texto mostrado en pantalla no se modifica.
"""

import re

# ---------------------------------------------------------------------------
# Números a palabras
# ---------------------------------------------------------------------------
_UNITS = [
    "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
    "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
    "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho", "veintinueve",
]
_TENS = ["", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
_HUNDREDS = [
    "", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos",
    "seiscientos", "setecientos", "ochocientos", "novecientos",
]


def _below_thousand(n: int) -> str:
    if n == 100:
        return "cien"
    parts = []
    if n >= 100:
        parts.append(_HUNDREDS[n // 100])
        n %= 100
    if n:
        if n < 30:
            parts.append(_UNITS[n])
        else:
            tens, unit = divmod(n, 10)
            parts.append(_TENS[tens] + (f" y {_UNITS[unit]}" if unit else ""))
    return " ".join(parts)


def _apocope(words: str) -> str:
    """'uno' -> 'un' delante de sustantivos (veintiún mil, un millón, un lempira)."""
    if words.endswith("veintiuno"):
        return words[:-len("veintiuno")] + "veintiún"
    if words.endswith("uno"):
        return words[:-3] + "un"
    return words


def number_to_words(n: int, apocope: bool = False) -> str:
    if n < 0:
        return "menos " + number_to_words(-n, apocope)
    if n == 0:
        return "cero"

    parts = []
    millions, rest = divmod(n, 1_000_000)
    thousands, units = divmod(rest, 1000)

    if millions:
        parts.append("un millón" if millions == 1 else _apocope(number_to_words(millions)) + " millones")
    if thousands:
        parts.append("mil" if thousands == 1 else _apocope(_below_thousand(thousands)) + " mil")
    if units:
        parts.append(_below_thousand(units))

    words = " ".join(parts)
    return _apocope(words) if apocope else words


def _decimal_to_words(raw: str, apocope: bool = False) -> str:
    """'2.5' -> 'dos punto cinco'; '0.05' -> 'cero punto cero cinco'."""
    if "." not in raw:
        return number_to_words(int(raw), apocope)
    integer, frac = raw.split(".", 1)
    frac = frac.rstrip("0")
    words = number_to_words(int(integer or "0"), apocope=False if frac else apocope)
    if not frac:
        return words
    leading = len(frac) - len(frac.lstrip("0"))
    frac_words = " ".join(["cero"] * leading)
    if frac.lstrip("0"):
        frac_words = (frac_words + " " if frac_words else "") + number_to_words(int(frac.lstrip("0")))
    return f"{words} punto {frac_words}"


def _is_one(raw: str) -> bool:
    try:
        return float(raw) == 1
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Tablas de siglas y unidades
# ---------------------------------------------------------------------------
_LETTERS = {
    "A": "a", "B": "be", "C": "ce", "D": "de", "E": "e", "F": "efe", "G": "ge", "H": "hache",
    "I": "i", "J": "jota", "K": "ka", "L": "ele", "M": "eme", "N": "ene", "Ñ": "eñe", "O": "o",
    "P": "pe", "Q": "cu", "R": "erre", "S": "ese", "T": "te", "U": "u", "V": "uve",
    "W": "doble u", "X": "equis", "Y": "ye", "Z": "zeta",
}

# Siglas que deben deletrearse en español (formulaciones agroquímicas y otras).
_ACRONYMS = {
    "WP", "WG", "WDG", "SC", "EC", "SL", "SP", "GR", "OD", "CS", "EW",
    "SG", "FS", "ULV", "NPK", "PH", "IA", "CRM", "PDV", "QR", "SMS",
}

# unidad -> (singular, plural)
_UNIT_NAMES = {
    "kg": ("kilo", "kilos"), "kgs": ("kilo", "kilos"),
    "g": ("gramo", "gramos"), "gr": ("gramo", "gramos"), "grs": ("gramo", "gramos"),
    "mg": ("miligramo", "miligramos"),
    "ml": ("mililitro", "mililitros"),
    "cc": ("centímetro cúbico", "centímetros cúbicos"),
    "l": ("litro", "litros"), "lt": ("litro", "litros"), "lts": ("litro", "litros"),
    "gal": ("galón", "galones"),
    "lb": ("libra", "libras"), "lbs": ("libra", "libras"),
    "oz": ("onza", "onzas"),
    "qq": ("quintal", "quintales"),
    "mz": ("manzana", "manzanas"), "mza": ("manzana", "manzanas"),
    "ha": ("hectárea", "hectáreas"),
    "m": ("metro", "metros"), "cm": ("centímetro", "centímetros"),
    "mm": ("milímetro", "milímetros"), "km": ("kilómetro", "kilómetros"),
    "°c": ("grado", "grados"), "ºc": ("grado", "grados"),
}
# Ordenadas de más larga a más corta para que "kg" gane a "g", "lts" a "l", etc.
_UNIT_RE = "|".join(sorted((re.escape(u) for u in _UNIT_NAMES), key=len, reverse=True))

_ORDINALS = {
    1: "primer", 2: "segundo", 3: "tercer", 4: "cuarto", 5: "quinto",
    6: "sexto", 7: "séptimo", 8: "octavo", 9: "noveno", 10: "décimo",
}

_ABBREVIATIONS = [
    (r"\by/o\b", "y o"),
    (r"\bc/u\b", "cada uno"),
    (r"\baprox\.", "aproximadamente"),
    (r"\betc\.", "etcétera"),
    (r"\bSr\.", "señor"),
    (r"\bSra\.", "señora"),
    (r"\bIng\.", "ingeniero"),
    (r"\bInge\.", "Inge"),
    (r"\bN[°º]\s?", "número "),
]

_NUM = r"\d+(?:\.\d+)?"


def _spell(acronym: str) -> str:
    return " ".join(_LETTERS.get(ch, ch) for ch in acronym.upper())


def _money(match: re.Match) -> str:
    raw = match.group("amount")
    integer, _, cents = raw.partition(".")
    cents = (cents + "00")[:2] if cents else ""
    value = int(integer)
    words = number_to_words(value, apocope=True) + (" lempira" if value == 1 else " lempiras")
    if cents and int(cents):
        words += " con " + number_to_words(int(cents), apocope=True) + " centavos"
    return words


def _feminine(words: str) -> str:
    """'un'/'veintiún' -> 'una'/'veintiuna' delante de sustantivos femeninos."""
    if words.endswith("veintiún"):
        return words[:-len("veintiún")] + "veintiuna"
    if words.endswith("un"):
        return words + "a"
    return words


def _looks_feminine(noun: str) -> bool:
    noun = noun.lower()
    if noun in {"vez", "veces", "mano", "manos", "foto", "fotos"}:
        return True
    return noun.endswith(("a", "as", "ción", "ciones", "sión", "siones")) and noun not in {"día", "días", "mapa", "problema", "problemas", "sistema", "clima"}


# Palabras tras un número que NO son sustantivos (no aplicar "un/una").
_NOT_NOUNS = {
    "y", "o", "u", "e", "a", "al", "de", "del", "en", "por", "para", "con", "sin", "que",
    "es", "son", "el", "la", "los", "las", "lo", "se", "le", "les", "más", "mas", "menos",
    "hasta", "entre", "cada", "punto", "como", "pero", "si", "ni",
}


def _unit(match: re.Match) -> str:
    raw = match.group("num")
    unit = match.group("unit").lower()
    singular, plural = _UNIT_NAMES[unit]
    feminine = _looks_feminine(singular)
    if raw in ("0.5", ".5"):
        text = f"{'media' if feminine else 'medio'} {singular}"
    else:
        words = _decimal_to_words(raw, apocope=True)
        if feminine:
            words = _feminine(words)
        text = f"{words} {singular if _is_one(raw) else plural}"
    per = match.group("per")
    if per:
        text += " por " + _UNIT_NAMES.get(per.lower(), (per, per))[0]
    return text


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def prepare_for_speech(text: str) -> str:
    """Convierte el texto de la IA en algo que el TTS lea correctamente en español."""
    if not text:
        return ""
    t = text

    # 1. Quitar lo que nunca debe pronunciarse: imágenes, enlaces, archivos, markdown, emojis.
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)                     # ![alt](img.png)
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)                  # [texto](url) -> texto
    t = re.sub(r"https?://\S+|www\.\S+", " ", t)
    t = re.sub(
        r"[\w\-./\\]*\.(?:png|jpe?g|gif|webp|svg|bmp|pdf|mp3|mp4|wav)\b",
        " ", t, flags=re.IGNORECASE,
    )
    t = re.sub(r"\(\s*\)", " ", t)                                   # paréntesis que quedaron vacíos
    t = re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200d]", "", t)
    t = re.sub(r"^\s*[-•*]\s+", "", t, flags=re.MULTILINE)          # viñetas
    t = re.sub(r"^\s*\d+[.)]\s+", "", t, flags=re.MULTILINE)         # listas numeradas
    t = re.sub(r"[*_#`>~|]", " ", t)
    t = re.sub(r"\s*\n+\s*", ". ", t)

    # 2. Abreviaturas comunes.
    for pattern, repl in _ABBREVIATIONS:
        t = re.sub(pattern, repl, t, flags=re.IGNORECASE)

    # 3. Separadores de miles: 1,500 -> 1500.
    t = re.sub(r"\b\d{1,3}(?:,\d{3})+\b", lambda m: m.group(0).replace(",", ""), t)

    # 4. Dinero: L. 350.00 / Lps 350 / HNL 350 / 350 HNL.
    t = re.sub(rf"\b(?:L(?:ps)?|HNL)\.?\s*(?P<amount>{_NUM})", _money, t)
    t = re.sub(rf"(?P<amount>{_NUM})\s*(?:HNL|Lps\.?|lempiras?)(?![\wáéíóú])", _money, t, flags=re.IGNORECASE)

    # 5. Porcentajes.
    t = re.sub(rf"({_NUM})\s*%", lambda m: _decimal_to_words(m.group(1)) + " por ciento", t)

    # 6. Fórmulas de fertilizante (20-20-20) y rangos (2-3).
    t = re.sub(
        r"\b(\d{1,2})-(\d{1,2})-(\d{1,2})\b",
        lambda m: ", ".join(number_to_words(int(g)) for g in m.groups()), t,
    )
    t = re.sub(
        rf"\b({_NUM})\s?(?:-|–|a)\s?({_NUM})\b(?=\s?(?:{_UNIT_RE}|%|días|dias|semanas|meses|horas|años))",
        lambda m: f"{m.group(1)} a {m.group(2)}", t, flags=re.IGNORECASE,
    )
    # El primer número de un rango no lleva unidad: "2 a 3 kg" -> "dos a tres kilos".
    t = re.sub(rf"\b({_NUM})(?= a \d)", lambda m: _decimal_to_words(m.group(1)), t)

    # 7. Horas: 8:30 -> ocho y treinta.
    t = re.sub(
        r"\b(\d{1,2}):(\d{2})\b",
        lambda m: number_to_words(int(m.group(1)))
        + (" en punto" if m.group(2) == "00" else " y " + number_to_words(int(m.group(2)))),
        t,
    )

    # 8. Cantidades con unidad (2.5 kg/mz, 200 ml, 1 L).
    t = re.sub(
        rf"(?P<num>{_NUM})\s?(?P<unit>{_UNIT_RE})(?![\wáéíóú])(?:\s?/\s?(?P<per>{_UNIT_RE}|bomba|barril|planta|mata))?",
        _unit, t, flags=re.IGNORECASE,
    )
    t = re.sub(r"\s?/\s?(bomba|barril|planta|mata|manzana|hectárea|litro|día|semana)\b", r" por \1", t)
    t = re.sub(rf"\s?/\s?({_UNIT_RE})\b", lambda m: " por " + _UNIT_NAMES[m.group(1).lower()][0], t, flags=re.IGNORECASE)

    # 9. Ordinales: 1er, 2do, 1ra, 3°.
    def _ordinal(m: re.Match) -> str:
        word = _ORDINALS.get(int(m.group(1)))
        if not word:
            return m.group(1)
        if m.group(2).lower() in ("ra", "da", "ta", "va", "na", "ma", "ª"):
            word = {"primer": "primera", "tercer": "tercera"}.get(word, word[:-1] + "a")
        return word

    t = re.sub(r"\b(\d{1,2})\s?(er|ro|ra|do|da|to|ta|vo|va|no|na|mo|ma|[°ºª])(?!\w)", _ordinal, t)

    # 10. Siglas y códigos de producto: "80 WP", "H-27", "NPK".
    t = re.sub(r"\b([A-Z])-?(\d+)\b", lambda m: f"{_LETTERS[m.group(1)]} {m.group(2)}", t)
    t = re.sub(r"\b[A-Za-z]{2,3}\b", lambda m: _spell(m.group(0)) if m.group(0).upper() in _ACRONYMS and (m.group(0).isupper() or m.group(0) == "pH") else m.group(0), t)

    # 11. Cualquier número que quede ("1 manzana" -> "una manzana", "21 días" -> "veintiún días").
    def _plain_number(m: re.Match) -> str:
        raw, noun = m.group(1), (m.group(2) or "").lower()
        if "." in raw or not noun or noun in _NOT_NOUNS:
            return _decimal_to_words(raw)
        words = number_to_words(int(raw), apocope=True)
        if _looks_feminine(noun):
            words = _feminine(words)
        return words

    t = re.sub(rf"\b({_NUM})\b(?=(?:\s+([a-záéíóúñ]+))?)", _plain_number, t)

    # 12. Limpieza final de espacios y puntuación duplicada.
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    t = re.sub(r"([.!?])\s*\.+", r"\1", t)
    t = re.sub(r",\s*\.", ".", t)
    t = re.sub(r"([,;:])(?:\s*[,;:])+", r"\1", t)
    t = re.sub(r"[,;:]\s*([.!?])", r"\1", t)
    t = re.sub(r"[,;:]\s*$", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" ,")
    t = re.sub(r"^[.\s]+", "", t)
    if t and t[-1] not in ".!?":
        t += "."
    return t
