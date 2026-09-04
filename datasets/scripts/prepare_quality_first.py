#!/usr/bin/env python3
"""Rebuild the frozen quality-first datasets from hash-verified raw inputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = ROOT / "datasets/sources.lock.json"
PREPARE_DATA = ROOT / "datasets/scripts/prepare_data.py"
PREPARATION = "quality_first_validation_20260903"
DATASETS = ("ledgar", "cfpb", "spamassassin")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_lock(path: Path = LOCK_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError(f"unsupported dataset source lock schema: {payload.get('schema_version')}")
    return payload


def require_file(path: Path, expected_hash: str, expected_bytes: int | None = None) -> None:
    if not path.is_file():
        raise ValueError(f"missing required file: {path}")
    if expected_bytes is not None and path.stat().st_size != expected_bytes:
        raise ValueError(
            f"source size mismatch for {path}: {path.stat().st_size} != {expected_bytes}"
        )
    actual_hash = sha256(path)
    if actual_hash != expected_hash:
        raise ValueError(f"SHA-256 mismatch for {path}: {actual_hash} != {expected_hash}")


def count_evals(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def verify_inputs(
    lock: dict[str, Any], source_root: Path, confirmatory_root: Path
) -> dict[str, dict[str, Path]]:
    preparation = lock["preparations"][PREPARATION]
    resolved: dict[str, dict[str, Path]] = {}
    for dataset in DATASETS:
        source_spec = lock["sources"][dataset]
        for file_spec in source_spec["files"]:
            require_file(
                source_root / file_spec["path"],
                file_spec["sha256"],
                file_spec.get("bytes"),
            )
        prior = confirmatory_root / dataset
        evals = prior / "evals.csv"
        selection = prior / "selection.json"
        require_file(evals, preparation["datasets"][dataset]["prior_evals_sha256"])
        if count_evals(evals) != preparation["exclude_prior_cases"]:
            raise ValueError(
                f"{dataset} prior selection must contain exactly "
                f"{preparation['exclude_prior_cases']} cases"
            )
        if not selection.is_file():
            raise ValueError(f"missing prior selection manifest: {selection}")
        labels = json.loads(selection.read_text(encoding="utf-8")).get("labels")
        if not isinstance(labels, list) or not labels:
            raise ValueError(f"prior selection has no frozen labels: {selection}")
        resolved[dataset] = {"prior": prior, "labels": selection}
    return resolved


def source_argument(dataset: str, source_root: Path) -> Path:
    if dataset == "ledgar":
        return source_root / "ledgar"
    if dataset == "cfpb":
        return source_root / "cfpb/complaints-api.json"
    return source_root / "spamassassin"


def command_for(
    dataset: str,
    destination: Path,
    source_root: Path,
    inputs: dict[str, Path],
    spec: dict[str, Any],
    seed: int,
) -> list[str]:
    splits = spec["splits"]
    return [
        sys.executable,
        str(PREPARE_DATA),
        dataset,
        "--output",
        str(destination),
        "--source",
        str(source_argument(dataset, source_root)),
        "--exclude-dataset",
        str(inputs["prior"]),
        "--labels-from",
        str(inputs["labels"]),
        "--seed",
        str(seed),
        "--development-cases",
        str(splits["development"]),
        "--validation-cases",
        str(splits["validation"]),
        "--test-cases",
        str(splits["test"]),
    ]


def verify_outputs(output_root: Path, spec: dict[str, Any]) -> None:
    for dataset in DATASETS:
        dataset_spec = spec["datasets"][dataset]
        require_file(output_root / dataset / "evals.csv", dataset_spec["expected_evals_sha256"])
        require_file(
            output_root / dataset / "selection.json",
            dataset_spec["expected_selection_sha256"],
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        required=True,
        type=Path,
        help="Root containing the raw files at paths declared in datasets/sources.lock.json",
    )
    parser.add_argument(
        "--confirmatory-root",
        required=True,
        type=Path,
        help="Root containing the three original 1,200-case prepared selections",
    )
    parser.add_argument(
        "--output",
        default=ROOT / "tmp/quality-first-datasets",
        type=Path,
        help="New output directory; it must not exist",
    )
    parser.add_argument(
        "--check-inputs-only",
        action="store_true",
        help="Verify source bytes and prior selections without preparing outputs",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.source_root = args.source_root.resolve()
    args.confirmatory_root = args.confirmatory_root.resolve()
    args.output = args.output.resolve()
    lock = load_lock()
    inputs = verify_inputs(lock, args.source_root, args.confirmatory_root)
    if args.check_inputs_only:
        print(json.dumps({"status": "inputs_verified", "datasets": list(DATASETS)}))
        return 0
    if args.output.exists():
        raise SystemExit(f"output already exists: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{args.output.name}-", dir=args.output.parent))
    preparation = lock["preparations"][PREPARATION]
    try:
        for dataset in DATASETS:
            command = command_for(
                dataset,
                staging / dataset,
                args.source_root,
                inputs[dataset],
                preparation["datasets"][dataset],
                preparation["seed"],
            )
            subprocess.run(command, cwd=ROOT, check=True)
        verify_outputs(staging, preparation)
        staging.replace(args.output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(json.dumps({"status": "prepared", "output": str(args.output), "datasets": list(DATASETS)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
