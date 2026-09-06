"""Conservative, standard-library SpamAssassin classifier."""
from __future__ import annotations

import re


RULES = (
    ("spam", r"\bremoved from\b"),
    ("spam", r"\bviagra\b"),
    ("ham", r"(?im)^in-reply-to\s*:"),
    ("ham", r"(?im)^references\s*:"),
)


def classify(text, labels):
    """Return a guarded label match or abstain for the frozen model fallback."""
    if not isinstance(text, str) or len(text) > 500_000:
        return None
    allowed = set(labels)
    for label, pattern in RULES:
        if label in allowed and re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            return {"label": label, "matched_rule": pattern}
    return None
