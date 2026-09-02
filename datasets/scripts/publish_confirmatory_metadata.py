#!/usr/bin/env python3
"""Publish compact confirmatory-design metadata from a passing audit proof."""
import argparse, json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--proof", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
proof = json.loads(args.proof.read_text())
if not proof.get("passed"): raise SystemExit("refusing to publish a failing audit")
eligible = proof["eligible_unique_by_label"]
per_label_required = sum(proof["requested_split_counts"].values()) // len(eligible)
source_mapping = proof.get("source_split_mapping")
eligible_by_source = proof.get("eligible_unique_by_label_and_source_split")
if source_mapping and eligible_by_source:
    capacities = [
        (eligible_by_source[source_mapping[split]][label] / (count // len(eligible)),
         split, label, eligible_by_source[source_mapping[split]][label])
        for split, count in proof["requested_split_counts"].items() for label in eligible
    ]
    limiting_ratio, limiting_split, limiting_label, limiting_unique = min(capacities)
    scale = int(limiting_ratio)
else:
    scale = min(eligible.values()) // per_label_required
    limiting_split = None
    limiting_label = min(eligible, key=eligible.get)
    limiting_unique = min(eligible.values())
payload = {
    "schema_version": 1, "status": "data_prepared_experiment_not_run",
    "design": {"development": 100, "validation": 100, "test": 1000,
               "test_policy": "untouched until candidate selection is complete"},
    "selection_seed": 20260902, "audit_proof": args.proof.as_posix(),
    "hashes": proof["hashes"], "sources": proof["sources"],
    "verified_checks": proof["checks"],
    "repeatability": proof.get("repeatability"),
    "exclusion_manifest": proof.get("exclusion_manifest", []),
    "source_split_mapping": source_mapping,
    "eligible_unique_by_label": eligible,
    "balanced_capacity_at_this_snapshot": {
        "limiting_label": limiting_label,
        "limiting_source_split": limiting_split,
        "limiting_unique_cases": limiting_unique,
        "requested_cases_per_label": per_label_required,
        "maximum_whole_design_multiples": scale,
        "maximum_same_ratio_balanced_splits": {
            split: count * scale for split, count in proof["requested_split_counts"].items()
        },
    },
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(payload, indent=2) + "\n")
