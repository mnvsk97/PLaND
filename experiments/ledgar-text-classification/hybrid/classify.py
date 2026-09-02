"""Conservative, dependency-free classifier for unambiguous LEDGAR clauses."""
import re

RULES = {
    "Governing Laws": (r"governed by.{0,40}laws?|construed (?:in accordance|under)",),
    "Counterparts": (r"executed in (?:one or more )?counterparts|counterparts.{0,60}(?:original|instrument)",),
    "Entire Agreements": (r"entire agreement|supersedes all prior",),
    "Severability": (r"invalid.{0,80}unenforceable|severab",),
    "Survival": (r"survive.{0,50}(?:termination|expiration)|(?:termination|expiration).{0,50}survive",),
    "Amendments": (r"(?:amend|modif).{0,80}(?:writing|written).{0,30}(?:signed|parties)",),
    "Notices": (r"all notices.{0,80}(?:writing|address|delivered)|notice shall be (?:given|sent|delivered)",),
    "Assignments": (r"(?:may not|shall not) assign|assignment.{0,80}(?:consent|successor)",),
}

def classify(text, labels):
    lowered = " ".join(text.lower().split())
    hits = [label for label, patterns in RULES.items()
            if label in labels and any(re.search(p, lowered) for p in patterns)]
    return {"label": hits[0], "confidence": .99} if len(hits) == 1 else None
