#!/usr/bin/env python3
"""Download and prepare deterministic enterprise-like PLaND eval subsets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import io
import json
import shutil
import subprocess
import tarfile
import urllib.parse
import urllib.error
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 2
DEFAULT_SEED = 20260902
EVAL_FIELDS = [
    "schema_version", "id", "benchmark", "task_type", "split",
    "input", "output", "reasoning", "metadata",
]
LEDGAR_REVISION = "0fb195adf1b8903c9a69fe707353ff03b54ee8a7"
LEDGAR_URL = (
    "https://huggingface.co/datasets/lighteval/lexglue/resolve/"
    + LEDGAR_REVISION + "/ledgar/{split}.jsonl"
)
CFPB_URL = "https://files.consumerfinance.gov/ccdb/complaints.csv.zip"
CFPB_API_URL = (
    "https://www.consumerfinance.gov/data-research/consumer-complaints/"
    "search/api/v1/"
)
CFPB_PER_PRODUCT_SAMPLE_SIZE = 1_000
CFPB_PRODUCTS = (
    "Checking or savings account",
    "Credit card",
    "Credit reporting or other personal consumer reports",
    "Debt collection",
    "Money transfer, virtual currency, or money service",
    "Mortgage",
    "Payday loan, title loan, personal loan, or advance loan",
    "Prepaid card",
    "Student loan",
    "Vehicle loan or lease",
)
SPAMASSASSIN_BASE_URL = "https://spamassassin.apache.org/old/publiccorpus"
SPAMASSASSIN_ARCHIVES = (
    "20030228_easy_ham.tar.bz2",
    "20030228_hard_ham.tar.bz2",
    "20030228_spam.tar.bz2",
    "20030228_spam_2.tar.bz2",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_rank(seed: int, identifier: str) -> str:
    return hashlib.sha256(f"{seed}:{identifier}".encode()).hexdigest()


def fetch(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "PLaND-data-preparer/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def fetch_json(url: str, destination: Path) -> None:
    """Fetch JSON, falling back to curl for hosts that reject urllib clients."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "curl/8.7.1"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.load(response)
        destination.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    except urllib.error.HTTPError as error:
        if error.code != 403 or shutil.which("curl") is None:
            raise
        subprocess.run(
            ["curl", "--fail", "--location", "--silent", "--show-error", url,
             "--output", str(destination)],
            check=True,
        )
        json.loads(destination.read_text(encoding="utf-8"))


def compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def allocate(total: int) -> dict[str, int]:
    if total < 3:
        raise ValueError("cases must be at least 3")
    development = round(total * 0.6)
    validation = round(total * 0.2)
    return {
        "development": development,
        "validation": validation,
        "test": total - development - validation,
    }


def balanced_allocation(total: int, classes: int) -> dict[str, int]:
    if total % classes:
        raise ValueError("cases must be divisible by classes for balanced selection")
    per_class = total // classes
    allocation = allocate(per_class)
    if min(allocation.values()) < 1:
        raise ValueError("each class needs at least three cases")
    return allocation


def requested_splits(args: argparse.Namespace) -> dict[str, int]:
    values = {
        "development": getattr(args, "development_cases", None),
        "validation": getattr(args, "validation_cases", None),
        "test": getattr(args, "test_cases", None),
    }
    supplied = [value is not None for value in values.values()]
    if any(supplied) and not all(supplied):
        raise ValueError("development, validation, and test case counts must be supplied together")
    if all(supplied):
        if any(value < 1 for value in values.values()):
            raise ValueError("every split must contain at least one case")
        return values
    return allocate(args.cases)


def balanced_splits(split_counts: dict[str, int], classes: int) -> dict[str, int]:
    if any(count % classes for count in split_counts.values()):
        raise ValueError("each split count must be divisible by classes for balanced selection")
    per_label = {split: count // classes for split, count in split_counts.items()}
    if min(per_label.values()) < 1:
        raise ValueError("each class needs at least one case in every split")
    return per_label


def deduplicate_text(records: Iterable[dict[str, Any]], text_key: str, id_key: str) -> list[dict[str, Any]]:
    """Keep one stable source record for each normalized exact text."""
    unique: dict[str, dict[str, Any]] = {}
    for record in records:
        normalized = " ".join(str(record[text_key]).split()).casefold()
        content_hash = hashlib.sha256(normalized.encode()).hexdigest()
        current = unique.get(content_hash)
        if current is None or str(record[id_key]) < str(current[id_key]):
            unique[content_hash] = record
    return list(unique.values())


def exclusion_manifest(paths: Iterable[Path]) -> tuple[set[str], set[str], list[dict[str, Any]]]:
    """Load IDs and normalized contents that may not enter a new experiment."""
    excluded_ids: set[str] = set()
    excluded_contents: set[str] = set()
    manifest = []
    for specification in paths:
        raw = str(specification)
        if "::" in raw:
            root_value, split_value = raw.rsplit("::", 1)
            included_splits = {item for item in split_value.split(",") if item}
            if not included_splits <= {"development", "validation", "test"}:
                raise ValueError(f"invalid exclusion split filter: {split_value}")
            root = Path(root_value)
        else:
            root = specification
            included_splits = None
        evals = root / "evals.csv"
        if not evals.is_file():
            raise ValueError(f"excluded dataset has no evals.csv: {root}")
        case_hashes = []
        with evals.open(newline="", encoding="utf-8") as handle:
            rows = [row for row in csv.DictReader(handle)
                    if included_splits is None or row.get("split") in included_splits]
        for row in rows:
            path = root / row["input"]
            payload = json.loads(path.read_text(encoding="utf-8"))
            content_hash = hashlib.sha256(normalized_case_content(payload).encode()).hexdigest()
            excluded_ids.add(row["id"])
            excluded_contents.add(content_hash)
            case_hashes.append((row["input"], sha256(path)))
        manifest.append({
            "path": str(root), "evals_sha256": sha256(evals), "cases": len(rows),
            "included_splits": sorted(included_splits) if included_splits else ["all"],
            "case_manifest_sha256": hashlib.sha256(compact(sorted(case_hashes)).encode()).hexdigest(),
        })
    return excluded_ids, excluded_contents, manifest


def normalized_case_content(payload: dict[str, Any]) -> str:
    for key in ("text", "narrative", "raw_email"):
        if key in payload:
            return " ".join(str(payload[key]).split()).casefold()
    return compact(payload)


def exclude_records(
    records: Iterable[dict[str, Any]], text_key: str, id_key: str, paths: Iterable[Path]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ids, contents, manifest = exclusion_manifest(paths)
    selected = []
    for record in records:
        content_hash = hashlib.sha256(
            " ".join(str(record[text_key]).split()).casefold().encode()
        ).hexdigest()
        if str(record[id_key]) not in ids and content_hash not in contents:
            selected.append(record)
    return selected, manifest


def write_case(root: Path, benchmark: str, identifier: str, payload: dict[str, Any]) -> str:
    safe_id = identifier.replace("/", "-").replace(" ", "-")
    relative = Path("data") / "cases" / f"{safe_id}.json"
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return relative.as_posix()


def write_artifacts(
    root: Path, rows: list[dict[str, str]], selection: dict[str, Any], source_paths: Iterable[Path]
) -> None:
    with (root / "evals.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EVAL_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    selection["schema_version"] = SCHEMA_VERSION
    selection["sources"] = [
        {"path": path.name, "sha256": sha256(path), "bytes": path.stat().st_size}
        for path in source_paths
    ]
    (root / "selection.json").write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    summary = {
        "cases": len(rows),
        "by_split": dict(Counter(row["split"] for row in rows)),
        "by_output": dict(Counter(row["output"] for row in rows)),
    }
    (root / "dataset-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def choose_balanced(
    records: Iterable[dict[str, Any]], label_key: str, id_key: str,
    cases: int, classes: int, seed: int, split_counts: dict[str, int] | None = None,
    frozen_labels: list[str] | None = None,
) -> tuple[list[tuple[str, dict[str, Any]]], list[str]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record[label_key])].append(record)
    labels = list(frozen_labels) if frozen_labels is not None else sorted(
        grouped, key=lambda label: (-len(grouped[label]), label)
    )[:classes]
    if len(labels) != classes or len(labels) != len(set(labels)):
        raise ValueError("frozen labels must contain exactly the configured number of unique classes")
    if split_counts is None:
        per_split = balanced_allocation(cases, classes)
    else:
        if sum(split_counts.values()) != cases:
            raise ValueError("split counts must sum to cases")
        per_split = balanced_splits(split_counts, classes)
    required = sum(per_split.values())
    if len(labels) != classes or any(len(grouped[label]) < required for label in labels):
        raise ValueError("not enough eligible examples to create the balanced subset")
    selected: list[tuple[str, dict[str, Any]]] = []
    for label in labels:
        ranked = sorted(grouped[label], key=lambda row: stable_rank(seed, str(row[id_key])))[:required]
        cursor = 0
        for split, count in per_split.items():
            selected.extend((split, row) for row in ranked[cursor:cursor + count])
            cursor += count
    selected.sort(key=lambda item: (item[0], str(item[1][label_key]), str(item[1][id_key])))
    return selected, labels


def choose_balanced_official_splits(
    records: Iterable[dict[str, Any]], label_key: str, id_key: str,
    source_split_key: str, split_counts: dict[str, int], classes: int, seed: int,
    source_mapping: dict[str, str], frozen_labels: list[str] | None = None,
) -> tuple[list[tuple[str, dict[str, Any]]], list[str]]:
    """Select balanced cases while preserving official upstream boundaries."""
    records = list(records)
    grouped = Counter(str(record[label_key]) for record in records)
    labels = list(frozen_labels) if frozen_labels is not None else sorted(
        grouped, key=lambda label: (-grouped[label], label)
    )[:classes]
    if len(labels) != classes or len(labels) != len(set(labels)):
        raise ValueError("frozen labels must contain exactly the configured number of unique classes")
    per_label = balanced_splits(split_counts, classes)
    selected = []
    for split, source_split in source_mapping.items():
        for label in labels:
            eligible = [row for row in records
                        if str(row[label_key]) == label and str(row[source_split_key]) == source_split]
            ranked = sorted(eligible, key=lambda row: stable_rank(seed, str(row[id_key])))
            if len(ranked) < per_label[split]:
                raise ValueError(f"not enough {source_split} examples for {label}: {len(ranked)}")
            selected.extend((split, row) for row in ranked[:per_label[split]])
    selected.sort(key=lambda item: (item[0], str(item[1][label_key]), str(item[1][id_key])))
    return selected, labels


def prepare_ledgar(args: argparse.Namespace, root: Path) -> None:
    source_dir = root / "sources"
    source_paths: list[Path] = []
    records = []
    for upstream_split in ("train", "validation", "test"):
        source = args.source / f"{upstream_split}.jsonl" if args.source else source_dir / f"{upstream_split}.jsonl"
        if not source.exists():
            fetch(LEDGAR_URL.format(split=upstream_split), source)
        source_paths.append(source)
        with source.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                item = json.loads(line)
                gold = item.get("gold", [])
                if len(gold) == 1 and item.get("input", "").strip():
                    records.append({
                        "id": f"{upstream_split}-{line_number}", "text": item["input"],
                        "label": gold[0], "upstream_split": upstream_split,
                    })
    records = deduplicate_text(records, "text", "id")
    records, exclusions = exclude_records(records, "text", "id", args.exclude_dataset)
    split_counts = requested_splits(args)
    cases = sum(split_counts.values())
    selected, labels = choose_balanced_official_splits(
        records, "label", "id", "upstream_split", split_counts, args.classes, args.seed,
        {"development": "train", "validation": "validation", "test": "test"},
        frozen_labels(args),
    )
    rows = []
    for split, item in selected:
        input_path = write_case(root, "ledgar", item["id"], {"text": item["text"]})
        rows.append({
            "schema_version": str(SCHEMA_VERSION), "id": item["id"], "benchmark": "ledgar",
            "task_type": "text_classification", "split": split, "input": input_path,
            "output": compact({"label": item["label"]}),
            "reasoning": "Gold contract-provision label supplied by LexGLUE LEDGAR.",
            "metadata": compact({"upstream_split": item["upstream_split"]}),
        })
    write_artifacts(root, rows, {
        "dataset": "lighteval/lexglue:ledgar", "revision": LEDGAR_REVISION,
        "seed": args.seed,
        "selection_rule": "top labels by eligible count; lowest seeded hashes within preserved official splits",
        "source_split_mapping": {"development": "train", "validation": "validation", "test": "test"},
        "requested_split_counts": split_counts,
        "eligible_unique_by_label": dict(Counter(item["label"] for item in records)),
        "eligible_unique_by_label_and_source_split": {
            source_split: dict(Counter(item["label"] for item in records
                                       if item["upstream_split"] == source_split))
            for source_split in ("train", "validation", "test")
        },
        "excluded_datasets": exclusions,
        "labels": labels, "selected": [{"id": row["id"], "split": row["split"]} for row in rows],
    }, source_paths)


def iter_cfpb(source: Path) -> Iterable[dict[str, str]]:
    if source.suffix == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
        hits = payload.get("hits", {}).get("hits", [])
        if "by_product" in payload:
            hits = [hit for product in payload["by_product"].values()
                    for hit in product.get("hits", {}).get("hits", [])]
        for hit in hits:
            item = hit.get("_source", {})
            yield {
                "Consumer complaint narrative": item.get("complaint_what_happened", ""),
                "Product": item.get("product", ""),
                "Complaint ID": str(item.get("complaint_id", "")),
                "Issue": item.get("issue", ""),
            }
        return
    if source.suffix == ".zip":
        archive = zipfile.ZipFile(source)
        names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(names) != 1:
            raise ValueError("CFPB archive must contain exactly one CSV")
        binary = archive.open(names[0])
        handle: Any = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
    else:
        handle = source.open(encoding="utf-8-sig", newline="")
    try:
        yield from csv.DictReader(handle)
    finally:
        handle.close()


def prepare_cfpb(args: argparse.Namespace, root: Path) -> None:
    source = args.source if args.source else root / "sources" / "complaints-api.json"
    if not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        by_product = {}
        for product in CFPB_PRODUCTS:
            query = urllib.parse.urlencode({
                "size": CFPB_PER_PRODUCT_SAMPLE_SIZE, "from": 0,
                "no_aggs": "true", "has_narrative": "true", "product": product,
            })
            part = source.parent / f"cfpb-{hashlib.sha256(product.encode()).hexdigest()[:12]}.json"
            fetch_json(f"{CFPB_API_URL}?{query}", part)
            by_product[product] = json.loads(part.read_text(encoding="utf-8"))
            part.unlink()
        source.write_text(json.dumps({"by_product": by_product}, sort_keys=True) + "\n", encoding="utf-8")
    records = []
    for row in iter_cfpb(source):
        narrative = (row.get("Consumer complaint narrative") or "").strip()
        product = (row.get("Product") or "").strip()
        identifier = (row.get("Complaint ID") or "").strip()
        if narrative and product and identifier:
            records.append({"id": identifier, "text": narrative, "label": product, "issue": row.get("Issue", "")})
    records = deduplicate_text(records, "text", "id")
    records, exclusions = exclude_records(records, "text", "id", args.exclude_dataset)
    split_counts = requested_splits(args)
    cases = sum(split_counts.values())
    selected, labels = choose_balanced(
        records, "label", "id", cases, args.classes, args.seed, split_counts,
        frozen_labels(args),
    )
    rows = []
    for split, item in selected:
        input_path = write_case(root, "cfpb", item["id"], {"narrative": item["text"]})
        rows.append({
            "schema_version": str(SCHEMA_VERSION), "id": item["id"], "benchmark": "cfpb",
            "task_type": "text_classification", "split": split, "input": input_path,
            "output": compact({"label": item["label"]}),
            "reasoning": "Product selected by the complainant in the public CFPB record.",
            "metadata": compact({"issue": item["issue"]}),
        })
    write_artifacts(root, rows, {
        "dataset": "CFPB Consumer Complaint Database", "download_url": CFPB_URL,
        "snapshot_api_url": CFPB_API_URL,
        "snapshot_rule": f"latest {CFPB_PER_PRODUCT_SAMPLE_SIZE} public narrative complaints per frozen product",
        "frozen_products": list(CFPB_PRODUCTS),
        "seed": args.seed, "selection_rule": "top products by narrative count, then lowest seeded hashes",
        "requested_split_counts": split_counts,
        "eligible_unique_by_label": dict(Counter(item["label"] for item in records)),
        "excluded_datasets": exclusions,
        "labels": labels, "selected": [{"id": row["id"], "split": row["split"]} for row in rows],
    }, [source])


def sanitize_email(raw: bytes) -> str:
    """Remove corpus or filter annotations that directly reveal the label."""
    text = raw.decode("utf-8", errors="replace").replace("\r\n", "\n")
    lines = text.splitlines()
    cleaned: list[str] = []
    skipping = False
    in_headers = True
    for line in lines:
        if in_headers and not line:
            in_headers = False
            skipping = False
            cleaned.append("")
            continue
        if in_headers:
            if line[:1].isspace() and skipping:
                continue
            name = line.partition(":")[0].strip().lower()
            skipping = name.startswith("x-spam-") or name in {
                "x-bogosity", "x-filtered-by", "x-mail-scanner",
            }
            if skipping:
                continue
            if name == "subject":
                value = line.partition(":")[2]
                value = value.replace("*****SPAM*****", "").replace("[SPAM]", "").strip()
                line = f"Subject: {value}"
        cleaned.append(line)
    return "\n".join(cleaned).strip() + "\n"


def iter_spamassassin(archives: Iterable[Path]) -> Iterable[dict[str, str]]:
    seen: set[str] = set()
    for archive_path in archives:
        label = "ham" if "ham" in archive_path.name else "spam"
        with tarfile.open(archive_path, "r:bz2") as archive:
            for member in sorted(archive.getmembers(), key=lambda item: item.name):
                if not member.isfile() or member.size == 0:
                    continue
                handle = archive.extractfile(member)
                if handle is None:
                    continue
                raw = handle.read()
                sanitized = sanitize_email(raw)
                content_hash = hashlib.sha256(sanitized.encode()).hexdigest()
                if content_hash in seen or not sanitized.strip():
                    continue
                seen.add(content_hash)
                yield {
                    "id": f"mail-{content_hash[:20]}",
                    "label": label,
                    "raw_email": sanitized,
                    "archive": archive_path.name,
                    "member": member.name,
                    "content_sha256": content_hash,
                }


def prepare_spamassassin(args: argparse.Namespace, root: Path) -> None:
    source_dir = args.source if args.source else root / "sources"
    if args.source and not source_dir.is_dir():
        raise ValueError("SpamAssassin --source must be a directory of corpus archives")
    archives = []
    for name in SPAMASSASSIN_ARCHIVES:
        path = source_dir / name
        if not path.exists():
            fetch(f"{SPAMASSASSIN_BASE_URL}/{name}", path)
        archives.append(path)
    records = list(iter_spamassassin(archives))
    records, exclusions = exclude_records(records, "raw_email", "id", args.exclude_dataset)
    split_counts = requested_splits(args)
    cases = sum(split_counts.values())
    selected, labels = choose_balanced(
        records, "label", "id", cases, 2, args.seed, split_counts, frozen_labels(args)
    )
    rows = []
    for split, item in selected:
        input_path = write_case(root, "spamassassin", item["id"], {"raw_email": item["raw_email"]})
        rows.append({
            "schema_version": str(SCHEMA_VERSION), "id": item["id"],
            "benchmark": "spamassassin", "task_type": "text_classification",
            "split": split, "input": input_path,
            "output": compact({"label": item["label"]}),
            "reasoning": "Hand-verified SpamAssassin public-corpus label.",
            "metadata": compact({
                "archive": item["archive"], "member": item["member"],
                "sanitized_content_sha256": item["content_sha256"],
            }),
        })
    write_artifacts(root, rows, {
        "dataset": "Apache SpamAssassin public mail corpus",
        "source_url": SPAMASSASSIN_BASE_URL,
        "archives": list(SPAMASSASSIN_ARCHIVES), "seed": args.seed,
        "sanitization": "remove X-Spam and equivalent filter headers and explicit subject markers",
        "selection_rule": "deduplicate sanitized messages, then lowest seeded hashes per label",
        "requested_split_counts": split_counts,
        "eligible_unique_by_label": dict(Counter(item["label"] for item in records)),
        "excluded_datasets": exclusions,
        "labels": labels,
        "selected": [{"id": row["id"], "split": row["split"]} for row in rows],
    }, archives)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=("ledgar", "cfpb", "spamassassin"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source", type=Path, help="Local source file or LEDGAR split directory")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--cases", type=int, default=100)
    parser.add_argument("--development-cases", type=int)
    parser.add_argument("--validation-cases", type=int)
    parser.add_argument("--test-cases", type=int)
    parser.add_argument("--exclude-selection", action="append", default=[], type=Path)
    parser.add_argument("--classes", type=int, default=10)
    parser.add_argument(
        "--labels-from", type=Path,
        help="Selection JSON whose ordered labels define the frozen task label set",
    )
    parser.add_argument("--exclude-dataset", action="append", default=[], type=Path,
                        help="Prepared dataset to exclude; append ::development,validation to filter splits")
    return parser.parse_args()


def frozen_labels(args: argparse.Namespace) -> list[str] | None:
    path = getattr(args, "labels_from", None)
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    labels = payload.get("labels")
    if not isinstance(labels, list) or not all(isinstance(label, str) and label for label in labels):
        raise ValueError("--labels-from must contain a non-empty string labels array")
    return labels


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise SystemExit(f"output already exists: {args.output}")
    args.output.mkdir(parents=True)
    try:
        {"ledgar": prepare_ledgar, "cfpb": prepare_cfpb,
         "spamassassin": prepare_spamassassin}[args.dataset](args, args.output)
    except Exception:
        shutil.rmtree(args.output)
        raise
    summary = json.loads((args.output / "dataset-summary.json").read_text(encoding="utf-8"))
    print(compact({"dataset": args.dataset, "output": str(args.output),
                   "cases": summary["cases"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
