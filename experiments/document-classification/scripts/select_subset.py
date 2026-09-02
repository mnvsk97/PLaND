#!/usr/bin/env python3
"""Create a reproducible balanced QS-OCR-Small dry-run subset."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import random
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path


LABELS = {
    "ADVE": "advertisement",
    "Email": "email",
    "Form": "form",
    "Letter": "letter",
    "Memo": "memo",
    "News": "news",
    "Note": "note",
    "Report": "report",
    "Resume": "resume",
    "Scientific": "scientific",
}

REASONS = {
    "advertisement": "Promotional document directed at a general audience.",
    "email": "Electronic message identifiable from email-specific content or fields.",
    "form": "Structured document with fields or spaces intended to be completed.",
    "letter": "Physical correspondence identifiable from letter structure or addressing.",
    "memo": "Organizational correspondence presenting information or requested action.",
    "news": "Journalistic article or newspaper-style content.",
    "note": "Brief handwritten or typed message with minimal document structure.",
    "report": "Organized account of findings, activity, or status.",
    "resume": "Summary of a person's experience, education, or qualifications.",
    "scientific": "Scientific or technical publication presenting research content.",
}


def normalized_id(name: str) -> str:
    digits = re.sub(r"\D", "", Path(name).stem).lstrip("0")
    return digits or "0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20260902)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise SystemExit(f"output already exists: {args.output}")

    audit_by_id = {}
    with args.audit.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            audit_by_id[normalized_id(row["Filename"])] = row

    counts = Counter()
    eligible = defaultdict(list)
    for path in sorted(args.corpus.glob("*/*.txt")):
        counts["ocr_documents"] += 1
        if path.stat().st_size == 0 or not path.read_text(encoding="utf-8", errors="replace").strip():
            counts["excluded_empty"] += 1
            continue
        row = audit_by_id.get(normalized_id(path.name))
        if row is None:
            counts["excluded_unmatched"] += 1
            continue
        corrected = ast.literal_eval(row["New Labels"])
        if len(corrected) != 1:
            counts["excluded_ambiguous"] += 1
            continue
        label = LABELS[corrected[0]]
        eligible[label].append(path)
        counts["eligible"] += 1

    missing = sorted(set(LABELS.values()) - set(eligible))
    if missing:
        raise SystemExit(f"classes have no eligible documents: {missing}")

    rng = random.Random(args.seed)
    ordered = {}
    selected = []
    for label in sorted(eligible):
        candidates = sorted(eligible[label], key=lambda path: normalized_id(path.name))
        rng.shuffle(candidates)
        ordered[label] = [normalized_id(path.name) for path in candidates]
        for index, source in enumerate(candidates[:2]):
            split = "development" if index == 0 else "validation"
            destination = Path("documents") / label / f"{normalized_id(source.name)}.txt"
            selected.append(
                {
                    "id": normalized_id(source.name),
                    "input": destination.as_posix(),
                    "output": label,
                    "reasoning": REASONS[label],
                    "split": split,
                    "source_sha256": sha256(source),
                    "source": str(source.resolve()),
                }
            )

    args.output.mkdir(parents=True)
    for item in selected:
        destination = args.output / item["input"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item["source"], destination)

    fieldnames = ["id", "input", "output", "reasoning", "split"]
    with (args.output / "evals.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({key: item[key] for key in fieldnames} for item in selected)

    selection = {
        "schema_version": 1,
        "seed": args.seed,
        "corpus": str(args.corpus.resolve()),
        "audit": str(args.audit.resolve()),
        "audit_sha256": sha256(args.audit),
        "ordered_candidate_ids": ordered,
        "selected": selected,
        "review_rejections": [],
    }
    (args.output / "selection.json").write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    summary = {"counts": dict(sorted(counts.items())), "eligible_by_class": {key: len(value) for key, value in sorted(eligible.items())}, "selected": len(selected)}
    (args.output / "dataset-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
