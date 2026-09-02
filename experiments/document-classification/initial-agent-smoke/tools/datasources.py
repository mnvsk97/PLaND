import json
from pathlib import Path

from langchain.tools import tool


MANIFEST = Path(__file__).resolve().parents[1] / "data" / "manifest.json"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@tool
def list_datasources() -> str:
    """List approved datasource files and their recorded metadata."""
    value = load_manifest()
    return json.dumps(value["sources"], separators=(",", ":"))


@tool
def read_datasource(relative_path: str) -> str:
    """Read one approved datasource by its relative path from the manifest."""
    value = load_manifest()
    approved = {item["path"] for item in value["sources"]}
    normalized = Path(relative_path).as_posix().lstrip("/")
    if normalized not in approved:
        raise ValueError(f"datasource is not approved: {relative_path}")
    root = Path(value["datasource_root"])
    return (root / normalized).read_text(encoding="utf-8", errors="replace")
