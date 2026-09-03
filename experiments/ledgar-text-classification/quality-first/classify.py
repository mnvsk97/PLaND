"""Development-gated deterministic routes for unambiguous contract clauses."""

import re


RULES = {
    "Governing Laws": (r"governed by.{0,40}laws?|construed (?:in accordance|under)",),
    "Counterparts": (r"executed in (?:one or more )?counterparts|counterparts.{0,60}(?:original|instrument)",),
    "Notices": (r"all notices.{0,80}(?:writing|address|delivered)|notice shall be (?:given|sent|delivered)",),
}


def classify(text, labels):
    lowered = " ".join(text.lower().split())
    hits = [
        label for label, patterns in RULES.items()
        if label in labels and any(re.search(pattern, lowered) for pattern in patterns)
    ]
    return {"label": hits[0], "confidence": 0.99} if len(hits) == 1 else None
