import re
_PHONE_RE = re.compile(r"^(?:\+?7|8)[\s\-()]*(\d[\s\-()]*){10}$")
def normalize_russian_phone(raw: str) -> str | None:
    if not raw: return None
    s = raw.strip()
    if not _PHONE_RE.match(s): return None
    digits = re.sub(r"\D", "", s)
    if len(digits) == 11 and digits[0] in ("7", "8"):
        return "+7" + digits[1:]
    return None
