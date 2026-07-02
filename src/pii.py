"""PII masking. The agent is forbidden from surfacing customer phones/emails,
even if a query retrieves them. We mask at the data layer (query rows) and
again on the final report text — defense in depth.
"""
import re

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Phone: sequences of 7+ digits allowing spaces/dashes/dots/parens/leading +.
_PHONE = re.compile(r"(?<!\w)(\+?\d[\d\s().-]{6,}\d)(?!\w)")

# Column names that are PII regardless of content.
_PII_COLUMNS = {"email", "phone", "phone_number", "e_mail"}

_EMAIL_MASK = "[EMAIL REDACTED]"
_PHONE_MASK = "[PHONE REDACTED]"


def mask_text(text: str) -> str:
    if not text:
        return text
    text = _EMAIL.sub(_EMAIL_MASK, text)
    text = _PHONE.sub(_PHONE_MASK, text)
    return text


def mask_value(value):
    if isinstance(value, str):
        return mask_text(value)
    return value


def mask_rows(rows: list[dict]) -> list[dict]:
    """Mask PII in query result rows: redact PII columns wholesale and scrub
    any stray PII that lands in other string columns."""
    masked = []
    for row in rows:
        new = {}
        for key, val in row.items():
            if key.lower() in _PII_COLUMNS:
                new[key] = _EMAIL_MASK if "mail" in key.lower() else _PHONE_MASK
            else:
                new[key] = mask_value(val)
        masked.append(new)
    return masked
