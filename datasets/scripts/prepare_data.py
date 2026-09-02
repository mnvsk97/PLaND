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
import urllib.parse
import urllib.error
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 2
DEFAULT_SEED = 20260902
SPLIT_COUNTS = {"development": 60, "validation": 20, "test": 20}
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
CFPB_API_SAMPLE_SIZE = 10_000
TAU_REVISION = "a2c024725189473d2d7cea3a5cfdbcc67478e41f"
TAU_TASKS_URL = (
    "https://raw.githubusercontent.com/sierra-research/tau2-bench/"
    + TAU_REVISION + "/data/tau2/domains/retail/tasks.json"
)
TAU_POLICY_URL = (
    "https://raw.githubusercontent.com/sierra-research/tau2-bench/"
    + TAU_REVISION + "/data/tau2/domains/retail/policy.md"
)
SROIE_DATASET = "mp-02/sroie"
SROIE_REVISION = "f845db1c2ccaf883550320fe450d1e723374be32"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_rank(seed: int, identifier: str) -> str:
    return hashlib.sha256(f"{seed}:{identifier}".encode()).hexdigest()


def sroie_source_id(item: dict[str, Any]) -> str:
    """Return an ID unique across SROIE's independently indexed splits."""
    return f"{item.get('upstream_split', 'source')}:{item['row_idx']}"


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
    cases: int, classes: int, seed: int,
) -> tuple[list[tuple[str, dict[str, Any]]], list[str]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record[label_key])].append(record)
    labels = sorted(grouped, key=lambda label: (-len(grouped[label]), label))[:classes]
    per_split = balanced_allocation(cases, classes)
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
    selected, labels = choose_balanced(records, "label", "id", args.cases, args.classes, args.seed)
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
        "seed": args.seed, "selection_rule": "top labels by eligible count, then lowest seeded hashes",
        "labels": labels, "selected": [{"id": row["id"], "split": row["split"]} for row in rows],
    }, source_paths)


def iter_cfpb(source: Path) -> Iterable[dict[str, str]]:
    if source.suffix == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
        for hit in payload.get("hits", {}).get("hits", []):
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
        query = urllib.parse.urlencode({
            "size": CFPB_API_SAMPLE_SIZE,
            "from": 0,
            "no_aggs": "true",
            "has_narrative": "true",
        })
        fetch_json(f"{CFPB_API_URL}?{query}", source)
    records = []
    for row in iter_cfpb(source):
        narrative = (row.get("Consumer complaint narrative") or "").strip()
        product = (row.get("Product") or "").strip()
        identifier = (row.get("Complaint ID") or "").strip()
        if narrative and product and identifier:
            records.append({"id": identifier, "text": narrative, "label": product, "issue": row.get("Issue", "")})
    selected, labels = choose_balanced(records, "label", "id", args.cases, args.classes, args.seed)
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
        "snapshot_rule": f"latest {CFPB_API_SAMPLE_SIZE} public complaints with narratives",
        "seed": args.seed, "selection_rule": "top products by narrative count, then lowest seeded hashes",
        "labels": labels, "selected": [{"id": row["id"], "split": row["split"]} for row in rows],
    }, [source])


def prepare_tau(args: argparse.Namespace, root: Path) -> None:
    source_dir = root / "sources"
    tasks_path = args.source if args.source else source_dir / "tasks.json"
    policy_path = args.policy_source if args.policy_source else source_dir / "policy.md"
    if not tasks_path.exists():
        fetch(TAU_TASKS_URL, tasks_path)
    if not policy_path.exists():
        fetch(TAU_POLICY_URL, policy_path)
    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    counts = allocate(min(args.cases, len(tasks)))
    ranked = sorted(tasks, key=lambda task: stable_rank(args.seed, str(task["id"])))[:sum(counts.values())]
    rows, cursor = [], 0
    for split, count in counts.items():
        for task in ranked[cursor:cursor + count]:
            identifier = f"retail-{task['id']}"
            input_path = write_case(root, "tau3-retail", identifier, {
                "domain": "retail", "task_id": str(task["id"]),
                "policy_path": "../sources/policy.md", "user_scenario": task["user_scenario"],
                "initial_state": task.get("initial_state"),
            })
            rows.append({
                "schema_version": str(SCHEMA_VERSION), "id": identifier,
                "benchmark": "tau3-retail", "task_type": "tool_workflow", "split": split,
                "input": input_path, "output": compact(task["evaluation_criteria"]),
                "reasoning": "Official outcome-based evaluation criteria; hidden from the agent.",
                "metadata": compact({"upstream_task_id": str(task["id"])}),
            })
        cursor += count
    write_artifacts(root, rows, {
        "dataset": "sierra-research/tau2-bench retail", "revision": TAU_REVISION,
        "seed": args.seed, "selection_rule": "lowest seeded task-id hashes",
        "selected": [{"id": row["id"], "split": row["split"]} for row in rows],
    }, [tasks_path, policy_path])


def hf_rows(split: str) -> list[dict[str, Any]]:
    rows, offset = [], 0
    while True:
        query = urllib.parse.urlencode({
            "dataset": SROIE_DATASET, "config": "default", "split": split,
            "offset": offset, "length": 100,
        })
        request = urllib.request.Request(
            f"https://datasets-server.huggingface.co/rows?{query}",
            headers={"User-Agent": "PLaND-data-preparer/1.0"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.load(response)
        rows.extend({**item, "upstream_split": split} for item in payload["rows"])
        if len(rows) >= payload["num_rows_total"]:
            return rows
        offset += len(payload["rows"])


def prepare_sroie(args: argparse.Namespace, root: Path) -> None:
    if args.source:
        payload = json.loads(args.source.read_text(encoding="utf-8"))
        upstream = payload["rows"] if isinstance(payload, dict) else payload
        source_paths = [args.source]
    else:
        upstream = hf_rows("train") + hf_rows("test")
        snapshot = root / "sources" / "rows.json"
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        # Signed image URLs are transient, but source IDs, annotations, and the snapshot hash are retained.
        snapshot.write_text(json.dumps({"rows": upstream}) + "\n", encoding="utf-8")
        source_paths = [snapshot]
    count = min(args.cases, len(upstream))
    counts = allocate(count)
    # Hugging Face row indexes restart at zero for every split. Including the
    # split prevents train/test collisions and overwritten images/case files.
    ranked = sorted(upstream, key=lambda item: stable_rank(args.seed, sroie_source_id(item)))[:count]
    tag_names = ["company", "date", "address", "total", "other"]
    rows, cursor = [], 0
    for split, split_count in counts.items():
        for item in ranked[cursor:cursor + split_count]:
            upstream_split = str(item.get("upstream_split", "source"))
            identifier = f"receipt-{upstream_split}-{item['row_idx']}"
            record = item["row"]
            image_path = root / "data" / "images" / f"{identifier}.jpg"
            fetch(record["image"]["src"], image_path)
            fields: dict[str, list[str]] = defaultdict(list)
            for word, tag in zip(record["words"], record["ner_tags"], strict=True):
                if tag < 4:
                    fields[tag_names[tag]].append(word)
            expected = {key: " ".join(fields.get(key, [])) for key in tag_names[:4]}
            input_path = write_case(root, "sroie", identifier, {
                "image": image_path.relative_to(root).as_posix(),
                "frozen_ocr": {"words": record["words"], "bboxes": record["bboxes"]},
            })
            rows.append({
                "schema_version": str(SCHEMA_VERSION), "id": identifier, "benchmark": "sroie",
                "task_type": "multimodal_extraction", "split": split, "input": input_path,
                "output": compact(expected),
                "reasoning": "Structured key fields derived from the dataset token annotations.",
                "metadata": compact({
                    "source_split": upstream_split,
                    "source_row": item["row_idx"],
                    "image_sha256": sha256(image_path),
                }),
            })
        cursor += split_count
    write_artifacts(root, rows, {
        "dataset": SROIE_DATASET, "revision": SROIE_REVISION, "seed": args.seed,
        "selection_rule": "lowest seeded source-row hashes",
        "selected": [{"id": row["id"], "split": row["split"]} for row in rows],
    }, source_paths)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=("ledgar", "cfpb", "tau-retail", "sroie"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source", type=Path, help="Local source file or LEDGAR split directory")
    parser.add_argument("--policy-source", type=Path, help="Local tau retail policy.md")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--cases", type=int, default=100)
    parser.add_argument("--classes", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise SystemExit(f"output already exists: {args.output}")
    args.output.mkdir(parents=True)
    try:
        {"ledgar": prepare_ledgar, "cfpb": prepare_cfpb,
         "tau-retail": prepare_tau, "sroie": prepare_sroie}[args.dataset](args, args.output)
    except Exception:
        shutil.rmtree(args.output)
        raise
    print(compact({"dataset": args.dataset, "output": str(args.output), "cases": args.cases}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
