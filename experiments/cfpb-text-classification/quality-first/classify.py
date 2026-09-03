"""Development-gated deterministic routes for explicit complaint products."""

import re


RULES = {
    "Student loan": (r"\bnavient\b",),
    "Prepaid card": (r"prepaid (?:debit )?card",),
}


def classify(text, labels):
    lowered = " ".join(text.lower().split())
    hits = [
        label for label, patterns in RULES.items()
        if label in labels and any(re.search(pattern, lowered) for pattern in patterns)
    ]
    return {"label": hits[0], "confidence": 0.99} if len(hits) == 1 else None
