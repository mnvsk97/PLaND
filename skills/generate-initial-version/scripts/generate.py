#!/usr/bin/env python3
"""Generate a minimal DeepAgent project with one SOP skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_manifest(root: Path) -> list[dict[str, object]]:
    entries = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    if not entries:
        raise ValueError("datasource directory contains no files")
    return entries


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def sop(workflow: str) -> str:
    title = workflow.replace("-", " ").title()
    return f"""---
name: {workflow}
description: Execute the {workflow.replace('-', ' ')} workflow using the approved datasource collection. Use when a request requires this workflow.
---

# {title} SOP

1. Identify the requested outcome and required output shape. <!-- pland:english -->
2. Inspect the datasource manifest and retrieve only the evidence relevant to the request. <!-- pland:english -->
3. Apply the requirements to the available evidence and produce the requested result. <!-- pland:english -->
4. Check that the result satisfies the required output shape and constraints. <!-- pland:english -->
"""


def model_source(provider: str) -> tuple[str, list[str]]:
    if provider == "ollama":
        return (
            '''from deepagents import GeneralPurposeSubagentProfile, HarnessProfile, register_harness_profile
from langchain_ollama import ChatOllama

MODEL = ChatOllama(
    model=os.environ["PLAND_MODEL"],
    temperature=0,
    reasoning=False,
    seed=int(os.environ.get("PLAND_SEED", "42")),
)
register_harness_profile(
    "ollama",
    HarnessProfile(
        excluded_tools=frozenset({"delete", "edit_file", "execute", "glob", "grep", "ls", "write_file"}),
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    ),
)''',
            ["deepagents", "langchain-ollama"],
        )
    return ('MODEL = os.environ["PLAND_MODEL"]', ["deepagents"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--requirements", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--guidance", type=Path)
    parser.add_argument("--model-provider", choices=("generic", "ollama"), default="generic")
    args = parser.parse_args()

    if not NAME_PATTERN.fullmatch(args.workflow):
        raise SystemExit("--workflow must contain lowercase letters, numbers, and single hyphens")
    requirements = args.requirements.resolve()
    sources = args.sources.resolve()
    output = args.output.resolve()
    guidance = args.guidance.resolve() if args.guidance else None
    if not requirements.is_file():
        raise SystemExit(f"requirements file not found: {requirements}")
    if not sources.is_dir():
        raise SystemExit(f"datasource directory not found: {sources}")
    if guidance and not guidance.is_file():
        raise SystemExit(f"guidance file not found: {guidance}")
    if output.exists():
        raise SystemExit(f"output already exists: {output}")

    try:
        sources_data = source_manifest(sources)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error

    model, dependencies = model_source(args.model_provider)
    output.mkdir(parents=True)
    write(
        output / "agent.py",
        f'''import os
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from tools.datasources import list_datasources, read_datasource


PROJECT_ROOT = Path(__file__).resolve().parent
{model}
INSTRUCTIONS = (PROJECT_ROOT / "instructions.md").read_text(encoding="utf-8")

agent = create_deep_agent(
    model=MODEL,
    tools=[list_datasources, read_datasource],
    system_prompt=INSTRUCTIONS,
    skills=["/skills/"],
    backend=FilesystemBackend(root_dir=str(PROJECT_ROOT), virtual_mode=True),
)


def invoke_workflow(request: str):
    """Invoke from isolated state after explicitly loading the workflow SOP."""
    prompt = (
        "First call read_file with file_path "
        f"/skills/{args.workflow}/SKILL.md. Follow that SOP, then handle this request: "
        f"{{request}}"
    )
    return agent.invoke({{"messages": [{{"role": "user", "content": prompt}}]}})
''',
    )
    write(
        output / "instructions.md",
        f"""# {args.workflow.replace('-', ' ').title()} agent

Use only the approved datasource collection and tools. The application invokes this agent through `invoke_workflow`, which explicitly loads the `{args.workflow}` SOP before the request. Return the required result without exposing internal reference answers or credentials.
""",
    )
    write(output / f"skills/{args.workflow}/SKILL.md", sop(args.workflow))
    write(
        output / "tools/datasources.py",
        '''import json
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
''',
    )
    write(output / "tools/__init__.py", "")
    manifest = {
        "schema_version": 1,
        "workflow": args.workflow,
        "requirements": {"path": str(requirements), "sha256": sha256(requirements)},
        "guidance": ({"path": str(guidance), "sha256": sha256(guidance)} if guidance else None),
        "model_provider": args.model_provider,
        "datasource_root": str(sources),
        "sources": sources_data,
    }
    write(output / "data/manifest.json", json.dumps(manifest, indent=2) + "\n")
    write(
        output / "pyproject.toml",
        f'''[project]
name = "{args.workflow}-agent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = {json.dumps(dependencies)}
''',
    )
    print(json.dumps({"output": str(output), "workflow": args.workflow, "sources": len(sources_data)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
