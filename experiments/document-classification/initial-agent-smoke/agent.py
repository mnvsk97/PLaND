import os
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_ollama import ChatOllama

from tools.datasources import list_datasources, read_datasource


PROJECT_ROOT = Path(__file__).resolve().parent
MODEL = ChatOllama(
    model=os.environ["PLAND_MODEL"],
    temperature=0,
    reasoning=False,
    seed=42,
)
INSTRUCTIONS = (PROJECT_ROOT / "instructions.md").read_text(encoding="utf-8")

agent = create_deep_agent(
    model=MODEL,
    tools=[list_datasources, read_datasource],
    system_prompt=INSTRUCTIONS,
    skills=["/skills/"],
    backend=FilesystemBackend(root_dir=str(PROJECT_ROOT), virtual_mode=True),
)
