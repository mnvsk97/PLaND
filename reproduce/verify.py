#!/usr/bin/env python3
"""Run offline repository checks without rebuilding artifacts or calling models."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_MANIFESTS = ()
PAPER_FILES = {
    "paper/PLaND.docx": ("76664f19c5e327131803e4aa24bf2be014cf29870f79d69ff60c25a9054d158e", 435751),
    "paper/PLaND.html": ("c49a1dfae6a15ca36062b97d044d3ef473471c1c2ff9b722b9f3b1f1b2f65d51", 609564),
    "paper/PLaND.md": ("d579b68872efec9b5efbfd8313ef5967f44065d614d0503108aaa3cf6ac175be", 47464),
    "paper/PLaND.pdf": ("cbf802a4651aa462ce5736e21d1e8a2c64cad5444bb0b9ee9c891ba3d2baaecd", 505242),
    "paper/build_artifacts.cjs": ("2670542a31e957e683e2064136014967c23844a84ea09335f15676de78b51806", 3863),
    "paper/build_manuscript.py": ("745acabfaacccd8276b0fc5e36c96f718267123432977a8e83c7ea6d7954d36c", 30038),
    "paper/figures/architecture.png": ("03ef8522429f5ab3577314464e7a2938662a8d9080bd0abd050a7b495a6f126e", 99078),
    "paper/figures/architecture.svg": ("ef074c760719982e9b0279adcbab0f8d65b050ca4a8998b4e92253c687be844c", 4005),
    "paper/figures/evolution-loop.png": ("1dd668c6ab572510e28e1233dbc612bff5f5691a5d0e4d749228f220b87ccad2", 118304),
    "paper/figures/evolution-loop.svg": ("84311cb74abd9a27dfb89880247e8a114fc443159263796b9266fa70f70897f6", 5506),
    "paper/figures/evolution-path.png": ("4aa5da539f5544a4b9f25d607afec9922d323894f7668b88b129a932d6b3b18a", 201220),
    "paper/figures/evolution-path.svg": ("1be052aa9d5fd73309a1914fb73b2259e839bc01d05a04ede88c8802d4827b88", 4462),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_file(path: Path, expected_hash: str, expected_bytes: int | None = None) -> None:
    if not path.is_file():
        raise RuntimeError(f"missing manifested file: {path.relative_to(ROOT)}")
    if expected_bytes is not None and path.stat().st_size != expected_bytes:
        raise RuntimeError(f"byte-size mismatch: {path.relative_to(ROOT)}")
    if sha256(path) != expected_hash:
        raise RuntimeError(f"SHA-256 mismatch: {path.relative_to(ROOT)}")


def check_file_list_manifest(relative: str) -> int:
    manifest = ROOT / relative
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    entries = payload.get("files")
    if not isinstance(entries, list):
        raise RuntimeError(f"unsupported evidence manifest: {relative}")
    for entry in entries:
        check_file(
            manifest.parent / entry["path"],
            entry["sha256"],
            entry.get("bytes"),
        )
    return len(entries)


def check_paper_files() -> int:
    for relative, (expected_hash, expected_bytes) in PAPER_FILES.items():
        check_file(ROOT / relative, expected_hash, expected_bytes)
    return len(PAPER_FILES)


def test_directories() -> list[Path]:
    roots = (ROOT / "datasets", ROOT / "experiments", ROOT / "skills", ROOT / ".codex/skills")
    return sorted({path.parent for root in roots for path in root.rglob("test_*.py")})


def run_tests() -> int:
    directories = test_directories()
    for directory in directories:
        relative = directory.relative_to(ROOT)
        print(f"TEST {relative}", flush=True)
        subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(directory), "-p", "test_*.py", "-v"],
            cwd=ROOT,
            check=True,
        )
    return len(directories)


def main() -> int:
    test_directories = run_tests()
    manifests = list(EVIDENCE_MANIFESTS) + [
        str(path.relative_to(ROOT))
        for path in sorted((ROOT / "experiments").glob("*/*/*/evidence-manifest.json"))
    ]
    evidence_files = sum(check_file_list_manifest(path) for path in manifests)
    paper_files = check_paper_files()
    print(
        f"PASS: {test_directories} test directories; "
        f"{len(manifests)} evidence manifests ({evidence_files} files); "
        f"{paper_files} paper files",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
