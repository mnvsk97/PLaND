import json
import subprocess
import sys
from pathlib import Path

from langchain.tools import tool


MANIFEST = Path(__file__).resolve().parents[1] / "data" / "manifest.json"
MAX_DATASOURCE_CHARS = 200_000
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compact_document.py"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@tool
def list_datasources() -> str:
    """List approved datasource files and their recorded metadata."""
    value = load_manifest()
    return json.dumps(value["sources"], separators=(",", ":"))


def normalize_approved_path(relative_path: str) -> str:
    value = load_manifest()
    approved = {item["path"] for item in value["sources"]}
    normalized = Path(relative_path).as_posix().lstrip("/")
    if normalized not in approved:
        raise ValueError(f"datasource is not approved: {relative_path}")
    return normalized


@tool
def compact_datasource(relative_path: str) -> str:
    """Run the approved deterministic compact-document script for one datasource."""
    normalized = normalize_approved_path(relative_path)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--file", normalized],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "compact-document command failed")
    return result.stdout
