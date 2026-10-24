"""Hinglish order parser (rule-based, original code, no LLM)."""
import re
from dataclasses import dataclass, asdict

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

NUM_WORDS = {
    "aadha": 0.5, "adha": 0.5, "aadhi": 0.5, "half": 0.5, "आधा": 0.5,
    "dedh": 1.5, "dhai": 2.5, "derh": 1.5, "sava": 1.25, "paav": 0.25, "pav": 0.25,
    "ek": 1, "one": 1, "एक": 1, "do": 2, "two": 2, "दो": 2, "teen": 3, "tin": 3, "three": 3, "तीन": 3,
    "chaar": 4, "char": 4, "four": 4, "चार": 4, "paanch": 5, "panch": 5, "five": 5, "पांच": 5, "पाँच": 5,
    "chhe": 6, "che": 6, "chah": 6, "six": 6, "छह": 6, "saat": 7, "seven": 7, "सात": 7,
    "aath": 8, "eight": 8, "आठ": 8, "nau": 9, "nine": 9, "नौ": 9, "das": 10, "ten": 10, "दस": 10,
    "gyarah": 11, "barah": 12, "baarah": 12, "twelve": 12, "बारह": 12, "छे": 6, "छः": 6, "डेढ़": 1.5, "ढाई": 2.5, "आधा": 0.5, "darjan": 12, "dozen": 12,
    "pandrah": 15, "bees": 20, "pachas": 50,
}
UNITS = {
    "kilo": "kg", "kg": "kg", "किलो": "kg", "gram": "g", "g": "g", "grams": "g", "ग्राम": "g",
    "litre": "L", "liter": "L", "ltr": "L", "l": "L", "लीटर": "L", "लिटर": "L", "लिट्रेट": "L", "लीटरर": "L",
    "packet": "packet", "packets": "packet", "paket": "packet", "पैकेट": "packet", "पैकेट्स": "packet",
    "dabba": "box", "dibba": "box", "box": "box", "bottle": "bottle", "botal": "bottle",
    "piece": "pcs", "pcs": "pcs", "darjan": "dozen", "dozen": "dozen",
}
# synthetic demo catalog: canonical name -> (aliases, default unit, needs_unit)
CATALOG = {
    "atta": (["atta", "aata", "आटा", "आता"], "kg", True),
    "chawal": (["chawal", "rice", "चावल", "राइस"], "kg", True),
    "cheeni": (["cheeni", "chini", "sugar", "चीनी", "चिनी", "शुगर"], "kg", True),
    "dal": (["dal", "daal", "दाल"], "kg", True),
    "Fortune oil": (["fortune oil", "fortune", "oil", "tel", "तेल", "फॉर्च्यून ऑयल", "फॉर्च्यून", "फार्च्यून", "ऑयल"], "L", True),
    "ande": (["ande", "anda", "egg", "eggs", "अंडे", "अंडा", "अंडें", "अण्डे", "आंडे", "आंद"], "pcs", False),
    "doodh": (["doodh", "milk", "दूध", "मिल्क"], "packet", False),
    "Maggi": (["maggi", "मैगी", "मैग्गी"], "packet", False),
    "bread": (["bread", "pav bread"], "packet", False),
    "namak": (["namak", "salt", "नमक"], "packet", False),
    "Parle-G": (["parle-g", "parle g", "parle", "biscuit"], "packet", False),
}
ALIASES = sorted(((a, k) for k, (al, _, _) in CATALOG.items() for a in al), key=lambda x: -len(x[0]))
NEGATION = re.compile(r"\b(nahi|nahin|no|galat|not)\b|नहीं|नही|गलत")
YES = re.compile(r"\b(haan|ha|haa|ji|yes|sahi|theek|thik|ok|okay|bas|done|correct)\b|हाँ|हां|बस|ठीक|सही|जी")
REMOVE = re.compile(r"\b(hata|hatao|cancel|remove|mat)\b|हटा|कैंसल")
FILLER = {"aur", "and", "bhi", "bhaiya", "bhai", "bhej", "do_", "dena", "chahiye", "de", "please", "ji", ","}

@dataclass
class Item:
    name: str
    qty: float | None
    unit: str

def normalize(text: str) -> str:
    t = text.translate(DEVANAGARI_DIGITS).lower()
    t = re.sub(r"(\d)\s*(kg|g|l|ltr)\b", r"\1 \2", t)
    t = re.sub(r"[!?.;।]", " ", t)
    return re.sub(r"\s+", " ", t.replace(",", " , ")).strip()

def _num(tok: str):
    try:
        return float(tok)
    except ValueError:
        return NUM_WORDS.get(tok)

def find_items(text: str):
    """Return (items, unknown_words). An item's qty is None if not stated."""
    t = " " + normalize(text) + " "
    # trailing 'bhej do' / 'de do' — 'do' here is a verb, not the number 2
    t = re.sub(r"\b(bhej|de|dedo|dena|likh|kar)\s+do\b", " ", t)
    t = re.sub(r"(भेज|दे|लिख|कर)\s+दो", " ", t)
    spans = []
    for alias, canon in ALIASES:
        for m in re.finditer(r"(?<![\w-])" + re.escape(alias) + r"(?![\w-])", t):
            if not any(s <= m.start() < e for s, e, _ in spans):
                spans.append((m.start(), m.end(), canon))
    spans.sort()
    items, prev_end = [], 0
    for s, e, canon in spans:
        seg = t[prev_end:s].split()
        qty = unit = None
        for tok in reversed(seg[-4:]):
            if unit is None and tok in UNITS:
                unit = UNITS[tok]
                if tok in ("darjan", "dozen") and qty is None:
                    qty = 12
                continue
            n = _num(tok)
            if n is not None and qty is None:
                qty = n
            elif qty is not None and n is not None and tok in ("dedh", "dhai", "aadha"):
                pass
            if qty is not None and tok not in UNITS:
                break
        if qty == 12 and unit == "dozen":
            unit = None
        default_unit = CATALOG[canon][1]
        if unit == "g" and qty:
            qty, unit = qty / 1000, "kg"
        if unit in (None, "dozen"):
            unit = default_unit
        items.append(Item(canon, qty, unit))
        prev_end = e
    # unknown nouns: words with a qty but no catalog match, e.g. "2 kilo kaju"
    unknown = []
    for m in re.finditer(r"\b(\d+(?:\.\d+)?|" + "|".join(map(re.escape, [k for k in NUM_WORDS if k.isascii()])) + r")\s+(?:(" + "|".join(map(re.escape, [k for k in UNITS if k.isascii()])) + r")\s+)?([a-z]+)", t):
        word = m.group(3)
        if word in UNITS or word in NUM_WORDS or word in FILLER or any(word == a.split()[0] for a, _ in ALIASES):
            continue
        if word in {"aur", "bhej", "de", "dena", "chahiye", "bhi", "ka", "ki", "ke", "wala", "wali"}:
            continue
        unknown.append(word)
    return items, unknown

def is_yes(text: str) -> bool:
    n = normalize(text)
    return bool(YES.search(n)) and not NEGATION.search(n)

def is_negation(text: str) -> bool:
    return bool(NEGATION.search(normalize(text)))

def is_removal(text: str) -> bool:
    return bool(REMOVE.search(normalize(text)))

def extract_phone(text: str):
    digits = re.sub(r"\D", "", normalize(text))
    return digits[-10:] if len(digits) >= 10 else None

def extract_name(text: str):
    n = normalize(text)
    m = re.search(r"(?:naam|name|main|mai|mera naam|this is)\s+(?:hai\s+|is\s+)?([a-z]+)", n)
    if m and m.group(1) not in {"hai", "is", "ka", "ki", "bol"}:
        return m.group(1).title()
    m = re.search(r"(?:नाम|मैं)\s+(?:है\s+)?([^\s,]+)", n)
    if m and m.group(1) not in {"है", "क्या"}:
        return m.group(1)
    m = re.search(r"\b([a-z]+)\s+(?:bol raha|bol rahi|here|hoon|hu)\b", n)
    return m.group(1).title() if m else None

def fmt_qty(q):
    if q is None:
        return "?"
    return str(int(q)) if float(q).is_integer() else str(q)

def item_dict(i: Item):
    return asdict(i)
