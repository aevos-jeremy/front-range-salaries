"""Pull the useful parts out of a job description's text: a short summary, the duties,
required qualifications, and desired traits. Works on text pasted into the app and on
text the CASFM scraper saved from an employer's page. Rule-based, so it needs no API key;
a reviewer can correct anything it gets wrong."""
import re

# Checked in this order, so "Preferred Qualifications" counts as desired, not required.
SECTIONS = [
    ("desired_traits", r"prefer|desir|nice to have|bonus|ideal candidate|would be great"),
    ("qualifications", r"qualif|requirement|what you bring|must have|minimum|education|who you are|^(skills|knowledge|qualifications)\b"),
    ("responsibilities", r"responsib|duties|what you.ll do|day in the life|essential functions|the role|job description|what you will do|key tasks"),
]
OTHER_HEADING = r"benefit|compensation|salary|pay range|about (us|the company)|how to apply|equal opportunity|perks|why (join|work)"
BULLET = re.compile(r"^\s*(?:[-•*·▪◦●–]|\d+[.)])\s*")
MAX_ITEMS = 12


def _heading(line):
    """The section a heading line starts, 'other' for headings we skip, or None."""
    text = line.strip().rstrip(":").strip()
    words = text.split()
    if (not text or len(words) > 9 or BULLET.match(line) or text.endswith(".")
            or re.search(r"\d", text)):
        return None
    # The keyword has to lead the line, so "HEC-RAS experience a plus" stays a bullet.
    low = " ".join(words[:5]).lower()
    for name, pattern in SECTIONS:
        if re.search(pattern, low):
            return name
    if re.search(OTHER_HEADING, low) or line.strip().endswith(":"):
        return "other"
    return None


def _clean(line):
    line = BULLET.sub("", line).strip()
    return line[:220] + ("…" if len(line) > 220 else "")


def _summary(lines):
    """The first real paragraph before any section, cut to two sentences."""
    for line in lines:
        if _heading(line):
            break
        text = line.strip()
        if len(text) >= 100 and not BULLET.match(line):
            sentences = re.split(r"(?<=[.!?])\s+", text)
            return " ".join(sentences[:2])[:400]
    return None


def extract(text):
    """Returns {summary, responsibilities, qualifications, desired_traits}; list fields
    are newline-joined bullet strings, and anything not found is None."""
    out = {"summary": None, "responsibilities": None, "qualifications": None, "desired_traits": None}
    if not text or not text.strip():
        return out
    lines = [l for l in text.replace("\r", "").split("\n") if l.strip()]
    out["summary"] = _summary(lines)
    found, current = {}, None
    for line in lines:
        head = _heading(line)
        if head:
            current = head if head != "other" else None
            continue
        if current:
            items = found.setdefault(current, [])
            if len(items) < MAX_ITEMS and len(line.strip()) > 3:
                items.append(_clean(line))
    for name, items in found.items():
        if items and name in out:
            out[name] = "\n".join(items)
    return out
