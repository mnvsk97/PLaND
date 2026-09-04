#!/usr/bin/env python3
"""Rebuild the approved nine-page manuscript from frozen page sources."""

from __future__ import annotations

import argparse
import hashlib
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / "paper" / "final_submission" / "reviewed-base.pdf"
DEFAULT_PAGE_TWO = ROOT / "paper" / "final_submission" / "replacement-page-2.pdf"
DEFAULT_OUTPUT = ROOT / "output" / "paper" / "PLAND_SUBMISSION_READY_FINAL.pdf"
TABLE_SNAPSHOT = ROOT / "paper" / "FINAL_TABLES.md"

EXPECTED_BASE_SHA256 = "959ab2405aa60cdb991c259b52ac668b366efbd8182e649acb29d3e817e04a87"
EXPECTED_PAGE_TWO_SHA256 = "4a034904ba21ac5c963fabd5ff25edaefdcaa221e4753b141fc0c257f35a35f6"
EXPECTED_TABLE_SNAPSHOT_SHA256 = "b80922e70485fd10ef604a5fa7244c9250382bbea11080353b14756b1e7c3c67"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_hash(path: Path, expected: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"hash mismatch for {path}: expected {expected}, got {actual}")


def page_fingerprint(page: object) -> str:
    contents = page.get_contents()
    data = contents.get_data() if contents is not None else b""
    box = tuple(float(value) for value in page.mediabox)
    return hashlib.sha256(repr(box).encode("ascii") + b"\0" + data).hexdigest()


def build(base_path: Path, page_two_path: Path, output_path: Path) -> None:
    require_hash(base_path, EXPECTED_BASE_SHA256)
    require_hash(page_two_path, EXPECTED_PAGE_TWO_SHA256)
    require_hash(TABLE_SNAPSHOT, EXPECTED_TABLE_SNAPSHOT_SHA256)

    base = PdfReader(base_path)
    replacement = PdfReader(page_two_path)
    if len(base.pages) != 9 or len(replacement.pages) != 1:
        raise ValueError("expected a nine-page base and one replacement page")

    writer = PdfWriter()
    for index, page in enumerate(base.pages):
        writer.add_page(replacement.pages[0] if index == 1 else page)
    writer.metadata = None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as stream:
        writer.write(stream)


def verify_rebuild(candidate_path: Path, approved_path: Path) -> None:
    candidate = PdfReader(candidate_path)
    approved = PdfReader(approved_path)
    if len(candidate.pages) != 9 or len(approved.pages) != 9:
        raise ValueError("approved and rebuilt manuscripts must both contain nine pages")
    for number, (left, right) in enumerate(zip(candidate.pages, approved.pages), start=1):
        if page_fingerprint(left) != page_fingerprint(right):
            raise ValueError(f"page {number} content differs from the approved manuscript")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--page-two", type=Path, default=DEFAULT_PAGE_TWO)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild to a temporary file and compare every page with --output",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.check:
        if not args.output.is_file():
            raise FileNotFoundError(f"approved manuscript not found: {args.output}")
        with tempfile.TemporaryDirectory(prefix="pland-final-") as directory:
            candidate = Path(directory) / "rebuilt.pdf"
            build(args.base, args.page_two, candidate)
            verify_rebuild(candidate, args.output)
        print(f"verified reproducible nine-page manuscript: {args.output}")
        return 0

    build(args.base, args.page_two, args.output)
    print(f"wrote {args.output} ({sha256(args.output)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
