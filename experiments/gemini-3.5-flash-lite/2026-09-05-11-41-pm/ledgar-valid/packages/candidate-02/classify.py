"""Conservative, standard-library LEDGAR clause classifier."""
from __future__ import annotations

import re


RULES = (
    ("Counterparts", r"\bcounterparts?\b"),
    ("Governing Laws", r"(?:\bgoverned by\b|\bconstrued in accordance with\b).{0,140}\blaws?\b|\blaws?\b.{0,100}\bstate of\b"),
    ("Severability", r"\b(?:invalid|illegal|unenforceable|invalidity)\b.{0,180}\b(?:provision|remainder|remaining)\b|\bprovision\b.{0,180}\b(?:invalid|illegal|unenforceable)\b"),
    ("Entire Agreements", r"\bentire agreement\b|\bsupersed(?:e|es|ed|ing)\b.{0,100}\bprior\b|\ball prior\b.{0,100}\bagreements?\b|\bagreements and understandings\b"),
    ("Notices", r"\ball notices\b|\bnotice shall be\b|\bnotices shall be\b"),
    ("Expenses", r"\bexpenses incurred\b|\bcosts and expenses\b|\breimburse\b.{0,100}\bexpenses\b"),
    ("Assignments", r"\bassign\b|\bassignee\b|\ban assignment\b|\bbe assigned\b"),
    ("Amendments", r"\b(?:any|no|such|the) amendment\b"),
    ("Survival", r"\bshall survive (?:the )?(?:closing|termination|expiration|resignation)\b|\brepayment satisfaction or discharge\b"),
    ("Terms", r"\bshall commence\b|\bthe term shall\b|\bdate and shall continue\b"),
)


def classify(text, labels):
    """Return a guarded label match or abstain for the frozen model fallback."""
    if not isinstance(text, str) or len(text) > 200_000:
        return None
    allowed = set(labels)
    normalized = " ".join(text.casefold().split())
    for label, pattern in RULES:
        if label in allowed and re.search(pattern, normalized, flags=re.DOTALL):
            return {"label": label, "matched_rule": pattern}
    return None
