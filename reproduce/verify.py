#!/usr/bin/env python3
"""Run offline repository checks without rebuilding artifacts or calling models."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_MANIFESTS = (
    "experiments/variance-study/study-manifest.json",
    "experiments/ledgar-text-classification/results/variance-study-20260903/manifest.json",
    "experiments/cfpb-text-classification/results/variance-study-20260903/manifest.json",
    "experiments/spamassassin-email-classification/results/variance-study-20260903/manifest.json",
    "experiments/quality-first-replications/study-manifest.json",
    "experiments/ledgar-text-classification/results/quality-first-validation-20260903/manifest.json",
    "experiments/cfpb-text-classification/results/quality-first-validation-20260903/manifest.json",
    "experiments/spamassassin-email-classification/results/quality-first-validation-20260903/manifest.json",
)
PAPER_FILES = {
    "paper/PLaND.docx": ("ede72b8323722ccd56ef4447c687bc27f63eed4a8cec655d1f690e7241f1a1c7", 309501),
    "paper/PLaND.html": ("ff37ec71dbed96cb90b47e8ed1f4ece4ab7755a8425bcc728165e132560f6403", 57516),
    "paper/PLaND.md": ("873a59429a33dd781d3d6b671e51442782b543498db05db3fda30cc0f966442b", 35168),
    "paper/PLaND.pdf": ("86d219d71357de6243d7b6db7e03676669273549c7f33124872468792e307494", 593969),
    "paper/REVISION_NOTES.md": ("298978efc935b26c592286e9d766cd7048f11edfdd96e599aac75e3af2ea049a", 18360),
    "paper/audit_paper.py": ("02d6514a6f8ce33fad05277d68de9b66037c8141ea628afaa829830ee13fdd24", 8949),
    "paper/build_artifacts.cjs": ("4bbfdcb0ec58dbb5715d2ca4849dcf7d73e4827c82316b207789672ab4b51d08", 3629),
    "paper/build_manuscript.py": ("ac9c3b02945d81d867f1a1dcf5249d801e6c1243cb430bf60b9f65324a79b322", 29548),
    "paper/figures/architecture.svg": ("ef074c760719982e9b0279adcbab0f8d65b050ca4a8998b4e92253c687be844c", 4005),
    "paper/figures/evolution-loop.svg": ("84311cb74abd9a27dfb89880247e8a114fc443159263796b9266fa70f70897f6", 5506),
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
    roots = (ROOT / "datasets", ROOT / "experiments", ROOT / "skills")
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
    evidence_files = sum(check_file_list_manifest(path) for path in EVIDENCE_MANIFESTS)
    paper_files = check_paper_files()

    print(
        f"PASS: {test_directories} test directories; "
        f"{len(EVIDENCE_MANIFESTS)} evidence manifests ({evidence_files} files); "
        f"{paper_files} paper files",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
