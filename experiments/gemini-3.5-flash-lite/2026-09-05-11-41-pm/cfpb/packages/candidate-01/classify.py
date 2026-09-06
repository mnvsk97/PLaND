"""Conservative, standard-library CFPB product classifier."""
from __future__ import annotations

import re


RULES = (
    ("Prepaid card", r"\bprepaid (?:debit |gift )?card\b|\b(?:vanilla|incomm)\b.{0,80}\b(?:visa|card)\b|\bvisa gift card\b"),
    ("Student loan", r"\bstudent loans?\b|\b(?:mohela|navient|nelnet)\b|\bdepartment of education\b.{0,100}\bloans?\b"),
    ("Mortgage", r"\bmortgage\b|\bforeclosure\b|\bhome equity line of credit\b|\bheloc\b|\bescrow account\b"),
    ("Money transfer, virtual currency, or money service", r"\b(?:zelle|venmo|coinbase|cryptocurrency|western union)\b|\bcash app\b|\bwire transfer\b"),
    ("Payday loan, title loan, personal loan, or advance loan", r"\b(?:payday|title|personal|advance) loans?\b|\baffirm\b"),
    ("Vehicle loan or lease", r"\b(?:auto|vehicle|car) loans?\b|\bauto lease\b|\bvehicle lease\b|\bbridgecrest\b"),
    ("Checking or savings account", r"\bchecking account\b|\bsavings account\b|\bdeposit account\b"),
    ("Debt collection", r"\bdebt collector\b|\bcollection agency\b|\bcollect(?:ing|ion of) (?:a |the )?debt\b"),
    ("Credit reporting or other personal consumer reports", r"\b(?:equifax|experian|transunion)\b|\bconsumer reports?\b|\bcredit report(?:ing)?\b"),
    ("Credit card", r"\bcredit card account\b|\bmy credit card\b|\bcard issuer\b"),
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
