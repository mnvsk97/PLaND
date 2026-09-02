import os
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.middleware.filesystem import FilesystemMiddleware

from tools.datasources import list_datasources, read_datasource


PROJECT_ROOT = Path(__file__).resolve().parent
from langchain_ollama import ChatOllama

MODEL = ChatOllama(
    model=os.environ["PLAND_MODEL"],
    temperature=0,
    reasoning=False,
    seed=int(os.environ.get("PLAND_SEED", "42")),
)
INSTRUCTIONS = (PROJECT_ROOT / "instructions.md").read_text(encoding="utf-8")
BACKEND = FilesystemBackend(root_dir=str(PROJECT_ROOT), virtual_mode=True)

agent = create_deep_agent(
    model=MODEL,
    tools=[list_datasources, read_datasource],
    system_prompt=INSTRUCTIONS,
    skills=["/skills/"],
    backend=BACKEND,
    middleware=[FilesystemMiddleware(backend=BACKEND, tools=["read_file"])],
)


def invoke_workflow(request: str):
    """Invoke from isolated state after explicitly loading the workflow SOP."""
    prompt = (
        "First call read_file with file_path "
        f"/skills/document-classification/SKILL.md. Follow that SOP, then handle this request: "
        f"{request}"
    )
    return agent.invoke({"messages": [{"role": "user", "content": prompt}]})
