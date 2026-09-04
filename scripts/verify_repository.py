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


def check_paper_manifest() -> int:
    manifest = ROOT / "output/paper/artifact-manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    for name, entry in payload["artifacts"].items():
        check_file(manifest.parent / name, entry["sha256"], entry.get("bytes"))
    return len(payload["artifacts"])


def check_arxiv_manifest() -> int:
    manifest = ROOT / "output/arxiv/artifact-manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    count = 0
    for key in ("source_archive", "compiled_preview"):
        entry = payload[key]
        check_file(manifest.parent / entry["path"], entry["sha256"], entry.get("bytes"))
        count += 1
    source_dir = manifest.parent / "PLAND_ARXIV_SOURCE"
    for name, expected_hash in payload["source_files"].items():
        check_file(source_dir / name, expected_hash)
        count += 1
    return count


def test_directories() -> list[Path]:
    roots = (ROOT / "datasets", ROOT / "experiments", ROOT / "paper", ROOT / "skills")
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
    artifact_files = check_paper_manifest() + check_arxiv_manifest()

    source = ROOT / "paper/PAPER.md"
    generated = ROOT / "output/paper/PLAND_PAPER.md"
    if source.read_bytes() != generated.read_bytes():
        raise RuntimeError("output/paper/PLAND_PAPER.md differs from paper/PAPER.md")

    subprocess.run(
        [sys.executable, str(ROOT / "paper/generate_tables.py"), "--check"],
        cwd=ROOT,
        check=True,
    )

    final_builder = ROOT / "paper/build_final_submission.py"
    if final_builder.is_file():
        subprocess.run([sys.executable, str(final_builder), "--check"], cwd=ROOT, check=True)

    print(
        f"PASS: {test_directories} test directories; "
        f"{len(EVIDENCE_MANIFESTS)} evidence manifests ({evidence_files} files); "
        f"paper/arXiv manifests ({artifact_files} files)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
