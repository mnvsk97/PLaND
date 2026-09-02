#!/usr/bin/env python3
"""Select a fixed 20-case paper subset from a frozen 100-case dataset."""
import argparse, csv, hashlib, json, shutil
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("--seed", type=int, default=20260902)
args = parser.parse_args()
if args.output.exists(): raise SystemExit(f"output exists: {args.output}")
with (args.source / "evals.csv").open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))
rank = lambda row: hashlib.sha256(f"{args.seed}:{row['id']}".encode()).hexdigest()
labels = sorted({json.loads(row["output"])["label"] for row in rows})
if len(labels) != 10: raise SystemExit("paper subset requires exactly 10 labels")
by_label = {label: sorted((row for row in rows if json.loads(row["output"])["label"] == label), key=rank)[:2]
            for label in labels}
development = [by_label[label][0] for label in labels] + [by_label[label][1] for label in labels[:2]]
validation = [by_label[label][1] for label in labels[2:6]]
test = [by_label[label][1] for label in labels[6:]]
chosen = development + validation + test
for row, split in zip(chosen, ["development"]*12+["validation"]*4+["test"]*4, strict=True): row["split"] = split
args.output.mkdir(parents=True)
(args.output / "data/cases").mkdir(parents=True)
with (args.output / "evals.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(chosen)
for row in chosen:
    source = args.source / row["input"]
    destination = args.output / row["input"]
    destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, destination)
selection = {"schema_version": 1, "parent_selection_sha256": hashlib.sha256((args.source/"selection.json").read_bytes()).hexdigest(),
             "seed": args.seed, "rule": "lowest two SHA-256(seed:id) ranks per label; assigned 12/4/4",
             "selected": [{"id": r["id"], "split": r["split"]} for r in chosen]}
(args.output/"selection.json").write_text(json.dumps(selection, indent=2)+"\n")
(args.output/"dataset-summary.json").write_text(json.dumps({"cases":20,"by_split":{"development":12,"validation":4,"test":4}},indent=2)+"\n")
