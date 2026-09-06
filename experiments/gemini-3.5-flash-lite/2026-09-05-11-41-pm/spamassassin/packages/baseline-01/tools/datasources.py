import json
from pathlib import Path

from langchain.tools import tool


MANIFEST = Path(__file__).resolve().parents[1] / "data" / "manifest.json"
MAX_DATASOURCE_CHARS = 200_000


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@tool
def list_datasources() -> str:
    """List approved datasource files and their recorded metadata."""
    value = load_manifest()
    return json.dumps(value["sources"], separators=(",", ":"))


@tool
def read_datasource(relative_path: str) -> str:
    """Read one approved datasource by its exact relative manifest path."""
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
