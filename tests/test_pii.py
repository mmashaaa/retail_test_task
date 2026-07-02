"""PII masking — the safety guarantee that customer emails/phones never reach
the user, even if a query retrieves them. Pure functions, no LLM/network."""
from src import pii


def test_mask_text_redacts_email():
    assert pii.mask_text("write to john@example.com now") == \
        "write to [EMAIL REDACTED] now"


def test_mask_text_redacts_phone():
    out = pii.mask_text("call +1-202-555-0142 today")
    assert "[PHONE REDACTED]" in out
    assert "0142" not in out


def test_mask_text_keeps_plain_text():
    assert pii.mask_text("Revenue grew 20% in Q3") == "Revenue grew 20% in Q3"


def test_mask_text_handles_empty_and_none():
    assert pii.mask_text("") == ""
    assert pii.mask_text(None) is None


def test_mask_text_keeps_short_numbers():
    # The phone heuristic needs 7+ digits; short numbers/years must survive.
    assert pii.mask_text("order 4321 in 2026") == "order 4321 in 2026"


def test_mask_rows_redacts_pii_columns_wholesale():
    rows = [{"email": "a@b.com", "phone": "555-123-4567", "revenue": 1200}]
    out = pii.mask_rows(rows)
    assert out[0]["email"] == "[EMAIL REDACTED]"
    assert out[0]["phone"] == "[PHONE REDACTED]"
    assert out[0]["revenue"] == 1200          # non-PII numeric untouched


def test_mask_rows_scrubs_stray_email_in_free_text():
    rows = [{"notes": "reach me at a@b.com"}]
    assert pii.mask_rows(rows)[0]["notes"] == "reach me at [EMAIL REDACTED]"


def test_mask_rows_keeps_names():
    # The task forbids phone/email specifically; names are not PII to mask.
    rows = [{"first_name": "John", "last_name": "Smith"}]
    assert pii.mask_rows(rows)[0] == {"first_name": "John", "last_name": "Smith"}
