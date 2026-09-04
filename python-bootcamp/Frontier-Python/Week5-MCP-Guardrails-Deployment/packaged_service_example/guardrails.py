"""
guardrails.py
Week 5 — Reliability & Safety Code

A small, real module (not a notebook demo) containing the guardrail functions that
`test_guardrails.py` exercises with pytest. Kept deliberately dependency-free (stdlib only)
so it runs with zero installs; a production version would typically swap the hand-rolled
PII regex for a library such as Microsoft Presidio (see requirements.txt).
"""

import re

INJECTION_PATTERNS = [
    re.compile(r"ignore (all )?previous instructions", re.IGNORECASE),
    re.compile(r"you are now", re.IGNORECASE),
    re.compile(r"system prompt", re.IGNORECASE),
]

EMAIL_PATTERN = re.compile(r"[\w.\-]+@[\w\-]+\.[\w.\-]+")
PHONE_PATTERN = re.compile(r"\b\d{10}\b")


def scan_for_injection(user_text: str) -> list[str]:
    """Return the list of injection-signature patterns matched, if any."""
    return [p.pattern for p in INJECTION_PATTERNS if p.search(user_text)]


def is_safe_input(user_text: str) -> bool:
    """True if no injection signature was detected."""
    return len(scan_for_injection(user_text)) == 0


def redact_pii(user_text: str) -> str:
    """Replace emails and 10-digit phone numbers with redaction placeholders."""
    text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", user_text)
    text = PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
    return text


def sanitize_for_log(user_text: str) -> str:
    """The function every log call should pass user-supplied text through first."""
    return redact_pii(user_text)
