# backend/app/ai/validators.py

from __future__ import annotations

import re
from typing import Iterable


class AdvisoryLanguageError(ValueError):
    """Raised when AI output contains non-advisory or impermissible language."""


# Phrases that suggest autonomous clinical decision-making or commands.
# This is intentionally conservative. Tune as you see false positives/negatives in practice.
_DISALLOWED_PATTERNS = [
    r"\bmust\b",
    r"\bshould\b(?!\s+be\s+considered)",  # allow "should be considered" but block generic "should"
    r"\brequired\b",
    r"\bguarantee\b",
    r"\bensure\b",
    r"\bimmediately\b\s+(start|give|administer|refer|transfer|treat|deliver)",
    r"\bstart\b\s+(treatment|therapy|magnesium|antihypertensives|antibiotics)",
    r"\badminister\b",
    r"\bgive\b\s+(magnesium|antibiotics|oxytocin|antihypertensives)",
    r"\bdiagnose\b",
    r"\bconfirm\b\s+diagnosis",
    r"\bdo\s+not\b\s+delay\b",
    r"\border\b\s+",
    r"\bprescribe\b",
    r"\bperform\b\s+(cs|c-section|caesarean|surgery)",
    r"\bdecide\b\s+to\b",
    r"\bpatient\s+has\b\s+(preeclampsia|eclampsia|sepsis|hemorrhage)\b",
]

# Allowed advisory hedges; used in guidance for developers, not enforced.
_ALLOWED_HINTS = [
    "consider",
    "may",
    "might",
    "suggest",
    "could",
    "evaluate",
    "assess",
    "discuss with",
    "per local protocol",
    "if clinically indicated",
]


def validate_advisory_language(text: str) -> None:
    """
    Raises AdvisoryLanguageError if the text contains impermissible autonomous/imperative language.

    This is NOT a medical safety net by itself; it is a policy guardrail.
    """
    if not isinstance(text, str):
        raise AdvisoryLanguageError("AI output must be a string")

    normalized = " ".join(text.strip().split())
    if not normalized:
        raise AdvisoryLanguageError("AI output cannot be empty")

    lower = normalized.lower()

    for pat in _DISALLOWED_PATTERNS:
        if re.search(pat, lower):
            raise AdvisoryLanguageError(
                f"Non-advisory language detected. Please rephrase in advisory form (e.g., 'consider', 'may', 'suggest'). "
                f"Matched pattern: {pat}"
            )


def validate_advisory_language_many(texts: Iterable[str]) -> None:
    for t in texts:
        validate_advisory_language(t)
