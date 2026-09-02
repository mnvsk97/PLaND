import json
import re
from pathlib import Path

from langchain.tools import tool


MANIFEST = Path(__file__).resolve().parents[1] / "data" / "manifest.json"
MAX_DATASOURCE_CHARS = 200_000


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def read_approved(relative_path: str) -> str:
    value = load_manifest()
    approved = {item["path"] for item in value["sources"]}
    normalized = Path(relative_path).as_posix().lstrip("/")
    if normalized not in approved:
        raise ValueError(f"datasource is not approved: {relative_path}")
    text = (Path(value["datasource_root"]) / normalized).read_text(
        encoding="utf-8", errors="replace"
    )
    if len(text) > MAX_DATASOURCE_CHARS:
        raise ValueError(
            f"datasource exceeds {MAX_DATASOURCE_CHARS} character limit: {relative_path}"
        )
    return text


def extract_signals(text: str) -> dict[str, int]:
    """Count conservative document-type cues in one pass over normalized text."""
    lowered = text.lower()
    return {
        "advertisement_terms": sum(lowered.count(term) for term in ("offer", "sale", "advertisement", "call now")),
        "email_headers": len(re.findall(r"(?mi)^(from|sent|to|subject|cc)\s*:", text)),
        "form_terms": sum(lowered.count(term) for term in ("form", "cover sheet", "questionnaire", "application")),
        "fillable_markers": len(re.findall(r"(?m)(_{2,}|\[[ x]?\]|:\s*(?:;|$))", lowered)),
        "letter_terms": sum(lowered.count(term) for term in ("dear ", "sincerely", "yours truly")),
        "memo_headers": len(re.findall(r"(?mi)^(memorandum|memo|to|from|date|subject)\s*:", text)),
        "news_terms": sum(lowered.count(term) for term in ("reported by", "newspaper", "press release")),
        "report_terms": sum(lowered.count(term) for term in ("report", "findings", "executive summary")),
        "resume_terms": sum(lowered.count(term) for term in ("curriculum vitae", "work experience", "education", "objective")),
        "scientific_terms": sum(lowered.count(term) for term in ("abstract", "methodology", "references", "doi")),
    }


@tool
def analyze_datasource(relative_path: str) -> str:
    """Read one approved OCR document and return its text with deterministic cue counts."""
    text = read_approved(relative_path)
    return json.dumps({"signals": extract_signals(text), "text": text}, separators=(",", ":"))
