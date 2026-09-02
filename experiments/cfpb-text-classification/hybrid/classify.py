"""Conservative, dependency-free classifier for explicit CFPB product narratives."""
import re

RULES = {
    "Mortgage": (r"\bmortgage\b", r"home loan"),
    "Student loan": (r"student loan", r"\bnavient\b"),
    "Vehicle loan or lease": (r"(?:auto|car|vehicle) (?:loan|lease|financ)",),
    "Prepaid card": (r"prepaid (?:debit )?card",),
    "Debt collection": (r"debt collect(?:or|ion)|collection agency",),
    "Checking or savings account": (r"checking account|savings account",),
    "Credit card": (r"credit card",),
    "Credit reporting or other personal consumer reports": (r"credit report(?:ing)?|credit bureau|\bequifax\b|\bexperian\b|\btransunion\b",),
    "Money transfer, virtual currency, or money service": (r"money transfer|wire transfer|virtual currency|cryptocurrency",),
    "Payday loan, title loan, personal loan, or advance loan": (r"payday loan|title loan|personal loan|cash advance",),
}

def classify(text, labels):
    lowered = " ".join(text.lower().split())
    hits = [label for label, patterns in RULES.items()
            if label in labels and any(re.search(p, lowered) for p in patterns)]
    return {"label": hits[0], "confidence": .99} if len(hits) == 1 else None
