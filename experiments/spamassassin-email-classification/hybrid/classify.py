"""Conservative deterministic routing for unambiguous historical spam."""

from email import policy
from email.parser import Parser
import re


HIGH_PRECISION_SPAM = (
    r"\b(?:herbal\s+)?viagra\b",
    r"\beliminate (?:your )?(?:credit card )?debt\b",
    r"\bwithout filing bankruptcy\b",
    r"\brelief for all skin disorders\b",
    r"\bseptic (?:tank|system).{0,120}\b(?:pump outs?|backups?|odor)\b",
    r"\bgrow your business\b.{0,600}\b(?:marketing|sales|customer)\b",
)


def classify(raw_email: str, labels: list[str]):
    """Return a label only for one clear rule; otherwise defer to the model."""
    if set(labels) != {"ham", "spam"}:
        return None
    message = Parser(policy=policy.default).parsestr(raw_email)
    subject = str(message.get("subject", ""))
    bodies = []
    for part in message.walk():
        if part.get_content_type() in {"text/plain", "text/html"}:
            try:
                bodies.append(str(part.get_content()))
            except (LookupError, UnicodeError):
                continue
    evidence = " ".join((subject, *bodies)).lower()
    hits = sum(bool(re.search(pattern, evidence, flags=re.DOTALL)) for pattern in HIGH_PRECISION_SPAM)
    return {"label": "spam", "confidence": 0.99} if hits == 1 else None
