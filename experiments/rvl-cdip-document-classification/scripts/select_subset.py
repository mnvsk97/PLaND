#!/usr/bin/env python3
"""Select and OCR a small, balanced RVL-CDIP subset from a public mirror."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import subprocess
import time
import urllib.parse
import urllib.request
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


def select_rows(rows: list[dict], seed: int, split: str) -> list[dict]:
    by_label = {index: [] for index in range(len(LABELS))}
    for item in rows:
        by_label[item["row"]["label"]].append(item)
    rng = random.Random(f"{seed}:{split}")
    selected = []
    for label_id, label in enumerate(LABELS):
        candidates = sorted(by_label[label_id], key=lambda item: item["row_idx"])
        if not candidates:
            raise RuntimeError(f"no source rows for {label} in {split}")
        selected.append(rng.choice(candidates))
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20260902)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output already exists: {args.output}")
    tesseract_version = subprocess.run(
        ["tesseract", "--version"], check=True, capture_output=True, text=True
    ).stdout.splitlines()[0]
    args.output.mkdir(parents=True)

    records = []
    eval_rows = []
    for source_split, experiment_split in (("validation", "development"), ("test", "validation")):
        for item in select_rows(fetch_rows(source_split), args.seed, source_split):
            label_id = item["row"]["label"]
            label = LABELS[label_id]
            row_idx = item["row_idx"]
            stem = f"{source_split}-{row_idx}"
            image_path = args.output / "images" / label.replace(" ", "-") / f"{stem}.jpg"
            text_path = args.output / "documents" / label.replace(" ", "-") / f"{stem}.txt"
            image_path.parent.mkdir(parents=True, exist_ok=True)
            text_path.parent.mkdir(parents=True, exist_ok=True)
            image_url = item["row"]["image"]["src"]
            urllib.request.urlretrieve(image_url, image_path)
            completed = subprocess.run(
                ["tesseract", str(image_path), "stdout", "-l", "eng"],
                check=True, capture_output=True, text=True,
            )
            text_path.write_text(completed.stdout, encoding="utf-8")
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
                "image_url": image_url,
                "image_sha256": sha256(image_path),
                "ocr_path": relative_text,
                "ocr_sha256": sha256(text_path),
                "ocr_bytes": text_path.stat().st_size,
            })

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
        "selection_rule": "one seeded row per class from validation and test",
        "records": records,
    }
    (args.output / "selection.json").write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(records), "classes": len(LABELS), "tesseract": tesseract_version}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
