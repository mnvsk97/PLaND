import os
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from tools.datasources import compact_datasource, list_datasources


PROJECT_ROOT = Path(__file__).resolve().parent
from deepagents import GeneralPurposeSubagentProfile, HarnessProfile, register_harness_profile
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
)
INSTRUCTIONS = (PROJECT_ROOT / "instructions.md").read_text(encoding="utf-8")

agent = create_deep_agent(
    model=MODEL,
    tools=[list_datasources, compact_datasource],
    system_prompt=INSTRUCTIONS,
    skills=["/skills/"],
    backend=FilesystemBackend(root_dir=str(PROJECT_ROOT), virtual_mode=True),
)


def invoke_workflow(request: str):
    """Invoke from isolated state after explicitly loading the workflow SOP."""
    prompt = (
        "First call read_file with file_path "
        f"/skills/document-classification/SKILL.md. Follow that SOP, then handle this request: "
        f"{request}"
    )
    return agent.invoke({"messages": [{"role": "user", "content": prompt}]})
