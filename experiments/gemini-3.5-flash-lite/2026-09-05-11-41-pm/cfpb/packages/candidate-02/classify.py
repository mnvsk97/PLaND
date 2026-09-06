"""Conservative, standard-library CFPB product classifier."""
from __future__ import annotations

import re


RULES = (
    ("Prepaid card", r"\bprepaid (?:debit |gift )?card\b|\b(?:vanilla|incomm)\b.{0,80}\b(?:visa|card)\b|\bvisa gift card\b"),
    ("Student loan", r"\bstudent loans?\b|\b(?:mohela|navient|nelnet)\b|\bdepartment of education\b.{0,100}\bloans?\b"),
    ("Mortgage", r"\bmortgage\b|\bforeclosure\b|\bhome equity line of credit\b|\bheloc\b|\bescrow account\b"),
    ("Payday loan, title loan, personal loan, or advance loan", r"\b(?:payday|title|personal|advance) loans?\b|\baffirm\b"),
)


def classify(text, labels):
    if not isinstance(text, str) or len(text) > 200_000:
        return None
    allowed = set(labels)
    normalized = " ".join(text.casefold().split())
    for label, pattern in RULES:
        if label in allowed and re.search(pattern, normalized, flags=re.DOTALL):
            return {"label": label, "matched_rule": pattern}
    return None
