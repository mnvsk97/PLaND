#!/usr/bin/env python3
"""Select and OCR a reproducible RVL-CDIP subset from a public mirror."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path


DATASET = "jordyvl/rvl_cdip_100_examples_per_class"
REVISION = "23c07577ae7d98d696806b794289926673929de6"
LABELS = [
    "letter", "form", "email", "handwritten", "advertisement",
    "scientific report", "scientific publication", "specification",
    "file folder", "news article", "budget", "invoice", "presentation",
    "questionnaire", "resume", "memo",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_rows(split: str) -> list[dict]:
    query = urllib.parse.urlencode({
        "dataset": DATASET, "config": "default", "split": split,
        "offset": 0, "length": 100,
    })
    rows: list[dict] = []
    offset = 0
    while True:
        page_query = query.replace("offset=0", f"offset={offset}")
        url = f"https://datasets-server.huggingface.co/rows?{page_query}"
        for attempt in range(4):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "PLaND-RVL-CDIP/1.0"})
                with urllib.request.urlopen(request, timeout=60) as response:
                    payload = json.load(response)
                break
            except OSError:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        rows.extend(payload["rows"])
        if len(rows) >= payload["num_rows_total"]:
            return rows
        offset += len(payload["rows"])


def allocate_balanced(total: int) -> dict[int, int]:
    base, remainder = divmod(total, len(LABELS))
    return {label_id: base + (label_id < remainder) for label_id in range(len(LABELS))}


def select_rows(rows: list[dict], seed: int, split: str, count: int) -> list[dict]:
    by_label = {index: [] for index in range(len(LABELS))}
    for item in rows:
        by_label[item["row"]["label"]].append(item)
    allocation = allocate_balanced(count)
    selected = []
    for label_id, label in enumerate(LABELS):
        candidates = sorted(
            by_label[label_id],
            key=lambda item: hashlib.sha256(f"{seed}:{split}:{item['row_idx']}".encode()).hexdigest(),
        )
        if len(candidates) < allocation[label_id]:
            raise RuntimeError(f"insufficient source rows for {label} in {split}")
        selected.extend(candidates[:allocation[label_id]])
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--development-cases", type=int, default=100)
    parser.add_argument("--validation-cases", type=int, default=100)
    parser.add_argument("--test-cases", type=int, default=1000)
    parser.add_argument("--exclude-selection", action="append", default=[], type=Path)
    parser.add_argument("--reuse-media-from", type=Path,
                        help="Reuse an existing preparation's immutable image/OCR bytes for repeatability checks")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output already exists: {args.output}")
    tesseract_version = subprocess.run(
        ["tesseract", "--version"], check=True, capture_output=True, text=True
    ).stdout.splitlines()[0]
    args.output.mkdir(parents=True)

    reusable_exclusions: dict[str, dict] = {}
    if args.reuse_media_from and (args.reuse_media_from / "selection.json").exists():
        reusable = json.loads((args.reuse_media_from / "selection.json").read_text(encoding="utf-8"))
        reusable_exclusions = {item["id"]: item for item in reusable.get("exclusions", [])}

    prior_pilot_ids: set[str] = set()
    for path in args.exclude_selection:
        prior = json.loads(path.read_text(encoding="utf-8"))
        prior_pilot_ids.update(str(item["id"]) for item in prior.get("records", prior.get("selected", [])))
    source_rows = {
        split: [item for item in fetch_rows(split) if f"{split}-{item['row_idx']}" not in prior_pilot_ids]
        for split in ("train", "validation", "test")
    }
    requested = {
        "development": args.development_cases,
        "validation": args.validation_cases,
        "test": args.test_cases,
    }
    available = {split: len(rows) for split, rows in source_rows.items()}
    actual = {
        "development": min(args.development_cases, available["train"]),
        "validation": min(args.validation_cases, available["validation"]),
        "test": min(args.test_cases, available["test"]),
    }
    records = []
    exclusions = []
    eval_rows = []
    for source_split, experiment_split in (("train", "development"), ("validation", "validation"), ("test", "test")):
        target_by_label = allocate_balanced(actual[experiment_split])
        accepted_by_label = {label_id: 0 for label_id in range(len(LABELS))}
        for item in select_rows(source_rows[source_split], args.seed, source_split, len(source_rows[source_split])):
            label_id = item["row"]["label"]
            if accepted_by_label[label_id] >= target_by_label[label_id]:
                continue
            label = LABELS[label_id]
            row_idx = item["row_idx"]
            stem = f"{source_split}-{row_idx}"
            if stem in reusable_exclusions:
                exclusions.append(reusable_exclusions[stem])
                continue
            image_path = args.output / "images" / f"{stem}.jpg"
            text_path = args.output / "documents" / f"{stem}.txt"
            image_path.parent.mkdir(parents=True, exist_ok=True)
            text_path.parent.mkdir(parents=True, exist_ok=True)
            image_url = item["row"]["image"]["src"]
            reused_image = args.reuse_media_from / "images" / f"{stem}.jpg" if args.reuse_media_from else None
            reused_text = args.reuse_media_from / "documents" / f"{stem}.txt" if args.reuse_media_from else None
            if reused_image and reused_text and reused_image.exists() and reused_text.exists():
                shutil.copyfile(reused_image, image_path)
                shutil.copyfile(reused_text, text_path)
            else:
                urllib.request.urlretrieve(image_url, image_path)
                completed = subprocess.run(
                    ["tesseract", str(image_path), "stdout", "-l", "eng"],
                    check=True, capture_output=True, text=True, errors="replace",
                )
                text_path.write_text(completed.stdout, encoding="utf-8")
            if not text_path.read_text(encoding="utf-8", errors="replace").strip():
                image_path.unlink(missing_ok=True)
                text_path.unlink(missing_ok=True)
                exclusions.append({"id": stem, "source_split": source_split, "reason": "empty_ocr"})
                continue
            relative_text = text_path.relative_to(args.output).as_posix()
            identifier = f"{source_split}-{row_idx}"
            eval_rows.append({
                "id": identifier,
                "input": relative_text,
                "output": label,
                "reasoning": f"RVL-CDIP source label {label}; hidden from the runtime agent.",
                "split": experiment_split,
            })
            records.append({
                "id": identifier,
                "label": label,
                "label_id": label_id,
                "source_split": source_split,
                "source_row": row_idx,
                "experiment_split": experiment_split,
                "image_sha256": sha256(image_path),
                "ocr_path": relative_text,
                "ocr_sha256": sha256(text_path),
                "ocr_bytes": text_path.stat().st_size,
            })
            accepted_by_label[label_id] += 1

    actual = dict(Counter(row["split"] for row in eval_rows))

    with (args.output / "evals.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "input", "output", "reasoning", "split"])
        writer.writeheader()
        writer.writerows(eval_rows)
    selection = {
        "schema_version": 1,
        "dataset": DATASET,
        "revision": REVISION,
        "seed": args.seed,
        "tesseract": tesseract_version,
        "selection_rule": "seeded near-balanced selection within each official source split",
        "requested_counts": requested,
        "available_source_counts": available,
        "actual_counts": actual,
        "capacity_shortfall": {key: requested[key] - actual.get(key, 0) for key in requested},
        "prior_pilot_ids": sorted(prior_pilot_ids),
        "exclusions": exclusions,
        "records": records,
    }
    (args.output / "selection.json").write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(records), "classes": len(LABELS), "counts": actual,
                      "capacity_shortfall": selection["capacity_shortfall"], "tesseract": tesseract_version}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
