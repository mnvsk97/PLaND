#!/usr/bin/env python3
"""Generate and validate the final manuscript tables from committed evidence.

The generated Markdown is the reviewable bridge between experiment JSON and the
typeset submission.  ``--check`` intentionally fails when either the evidence or
the committed table snapshot changes without regenerating the other.
"""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "paper" / "FINAL_TABLES.md"


def _json(relative: str) -> dict[str, Any]:
    with (ROOT / relative).open(encoding="utf-8") as handle:
        return json.load(handle)


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def _pct_compact(value: float, digits: int = 2) -> str:
    percentage = value * 100
    if percentage.is_integer():
        return f"{percentage:.0f}%"
    return f"{percentage:.{digits}f}%"


def _integer(value: float | int) -> str:
    return f"{value:,.0f}"


def _tokens(value: float) -> str:
    return f"{value:,.2f}" if value % 1 else f"{value:,.0f}"


def _reduction(value: float) -> str:
    return f"{value * 100:.2f}%"


def _table(title: str, headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = [f"## {title}", "", "| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines + [""]


def _comparison_row(label: str, path: str, decision: str) -> list[str]:
    data = _json(path)
    nl = data["natural_language"]
    hybrid = data["hybrid"]
    reduction = data["delta_hybrid_minus_nl"]["token_reduction_fraction"]
    return [
        label,
        f"{_pct(nl['accuracy'])} -> {_pct(hybrid['accuracy'])} accuracy",
        f"{_integer(nl['total_tokens'])} -> {_integer(hybrid['total_tokens'])} (-{_reduction(reduction)})",
        decision,
    ]


def table_1() -> list[str]:
    rows = [
        _comparison_row(
            "LEDGAR validation (100)",
            "experiments/ledgar-text-classification/results/confirmatory-validation-comparison.json",
            "Pass; test released",
        ),
        _comparison_row(
            "LEDGAR test (1,000)",
            "experiments/ledgar-text-classification/results/confirmatory-test-comparison.json",
            "Pass",
        ),
        _comparison_row(
            "CFPB validation (100)",
            "experiments/cfpb-text-classification/results/confirmatory-validation-comparison.json",
            "Reject; test closed",
        ),
        _comparison_row(
            "SpamAssassin validation (100)",
            "experiments/spamassassin-email-classification/results/confirmatory-validation-comparison.json",
            "Reject; test closed",
        ),
    ]
    for label, path, metric in [
        (
            "QS-OCR/Tobacco validation (100)",
            "experiments/document-classification/results/confirmatory-validation-nl.json",
            "accuracy",
        ),
        (
            "SROIE LiteParse validation (100)",
            "experiments/sroie-receipt-extraction/results/confirmatory-liteparse-validation/end-to-end-nl-baseline.json",
            "field_f1",
        ),
        (
            "RVL mirror validation (100)",
            "experiments/rvl-cdip-document-classification/results/confirmatory-validation-nl.json",
            "accuracy",
        ),
    ]:
        data = _json(path)
        metrics = data.get("summary", data.get("metrics"))
        quality = (
            f"{_pct(metrics[metric])} -> not run"
            if metric == "accuracy"
            else f"{metrics[metric]:.3f} field F1 -> not run"
        )
        rows.append(
            [
                label,
                quality,
                f"{_integer(metrics['total_tokens'])} -> not run",
                "Baseline nonviable",
            ]
        )
    return _table(
        "Table 1. Original confirmatory results",
        ["Workflow and split", "Quality (NL -> hybrid)", "Tokens (NL -> hybrid)", "Decision"],
        rows,
    )


def table_2() -> list[str]:
    summary = _json("experiments/variance-study/summary.json")
    specs = [
        ("ledgar-text-classification", "LEDGAR test (1,000)", "pass"),
        ("cfpb-text-classification", "CFPB validation (100)", "reject"),
        ("spamassassin-email-classification", "SpamAssassin validation (100)", "reject"),
    ]
    rows: list[list[str]] = []
    for key, label, decision in specs:
        data = summary["datasets"][key]
        nl, hybrid = data["variants"]["nl"], data["variants"]["hybrid"]
        routes = data["hybrid_route_stability"]["signature_counts"]
        command = routes.get("command/command/command", 0)
        model = routes.get("model/model/model", 0)
        gates = data["per_run_gates"]
        passed = sum(bool(run["gate"]["test_release_pass"]) for run in gates)
        reduction = 1 - hybrid["total_tokens"]["mean"] / nl["total_tokens"]["mean"]
        rows.append(
            [
                label,
                f"{_pct(nl['accuracy']['mean'])} (SD {_tokens(nl['accuracy']['sample_sd'])}) -> "
                f"{_pct(hybrid['accuracy']['mean'])} (SD {_tokens(hybrid['accuracy']['sample_sd'])})",
                f"{_tokens(nl['total_tokens']['mean'])} -> {_tokens(hybrid['total_tokens']['mean'])} "
                f"(-{_reduction(reduction)})",
                f"{command} command / {model} model; {decision} in {passed}/3"
                if decision == "pass"
                else f"{command} command / {model} model; reject in 3/3",
            ]
        )
    return _table(
        "Table 2. Three-run optimized replication results",
        ["Workflow and split", "Accuracy mean (NL -> hybrid)", "Mean tokens (NL -> hybrid)", "Routing / decision"],
        rows,
    )


def table_3() -> list[str]:
    summary = _json("experiments/quality-first-replications/summary.json")
    specs = [
        ("ledgar-text-classification", "LEDGAR", "ledgar"),
        ("cfpb-text-classification", "CFPB", "cfpb"),
        ("spamassassin-email-classification", "SpamAssassin", "spamassassin"),
    ]
    rows: list[list[str]] = []
    for key, label, folder in specs:
        data = summary["datasets"][key]
        nl, candidate = data["variants"]["nl"], data["variants"]["quality-first"]
        gate = data["per_run_gates"][0]
        low, high = gate["accuracy_difference_bootstrap_95"]
        routes = data["quality-first_route_stability"]["signature_counts"]
        command = routes.get("command/command/command", 0)
        if folder == "spamassassin":
            experiment = "spamassassin-email-classification"
        else:
            experiment = f"{folder}-text-classification"
        comparison = _json(
            f"experiments/{experiment}/results/quality-first-validation-20260903/"
            "seed-20260906-comparison.json"
        )
        precision = comparison["mechanism_decomposition"]["command_routed_hybrid_precision"]
        rows.append(
            [
                label,
                f"{_pct(nl['accuracy']['mean'])} -> {_pct(candidate['accuracy']['mean'])}",
                f"{(candidate['accuracy']['mean'] - nl['accuracy']['mean']) * 100:+.1f} pp "
                f"[{low * 100:+.1f}, {high * 100:+.1f}]",
                f"{gate['token_reduction_fraction'] * 100:.2f}% token reduction; "
                f"{command}/500 at {_pct_compact(precision)} precision; reject",
            ]
        )
    return _table(
        "Table 3. Fresh quality-first validation results",
        ["Dataset", "Accuracy (NL -> quality-first)", "Difference (95% interval)", "Efficiency / route / outcome"],
        rows,
    )


def table_4() -> list[str]:
    # Two older pilots only published aggregate result records; assert their
    # manuscript values before carrying them into the generated table.
    original_qs = _text("experiments/document-classification/RESULTS.md")
    for required in ("100% validation accuracy", "46.40% on validation", "no command step"):
        if required not in original_qs:
            raise ValueError(f"QS-OCR original result record lost required claim: {required}")
    spam = _text("experiments/spamassassin-email-classification/RESULTS.md")
    for required in ("tokens fell by 15.27%", "model calls fell from 20 to 16", "100%", "75%"):
        if required not in spam:
            raise ValueError(f"SpamAssassin pilot result record lost required claim: {required}")

    qs_v2 = _json("experiments/document-classification/schema-v2/comparisons/validation.json")
    rvl = _json("experiments/rvl-cdip-document-classification/schema-v2/comparisons/validation.json")
    sroie = _json("experiments/sroie-receipt-extraction/results/comparison.json")["modes"]["frozen-ocr"]
    qs_reduction = 1 - qs_v2["delta_hybrid_minus_natural_language"]["total_token_ratio"]
    qs_latency = 1 - qs_v2["delta_hybrid_minus_natural_language"]["mean_latency_ratio"]
    rvl_reduction = 1 - rvl["delta_hybrid_minus_natural_language"]["total_token_ratio"]
    rvl_latency = 1 - rvl["delta_hybrid_minus_natural_language"]["mean_latency_ratio"]
    sroie_reduction = 1 - sroie["candidate"]["total_tokens"] / sroie["baseline"]["total_tokens"]
    rows = [
        [
            "QS-OCR/Tobacco original pilot",
            "Preserved 100% validation accuracy and reduced validation tokens 46.40%, but the accepted SOP had no command step.",
            "Pre-protocol agent-boundary optimization; not English-to-command SOP compilation.",
        ],
        [
            "QS-OCR/Tobacco schema-v2",
            f"Preserved {_pct(qs_v2['hybrid']['metrics']['accuracy'], 0)} validation accuracy on 10 cases, "
            f"reduced tokens {_reduction(qs_reduction)}, and reduced mean latency {_reduction(qs_latency)}.",
            "Genuine hybrid operation-level proof-of-concept; one case per class, one seed, no third held-out split.",
        ],
        [
            "SpamAssassin pilot",
            "Across 20 cases, accuracy was 90% NL vs 85% hybrid; tokens fell 15.27% and calls 20 -> 16. Four-case held-out test was 100% vs 75%.",
            "Accepted under an earlier 75% absolute threshold; threshold-level pilot evidence only.",
        ],
        [
            "RVL-CDIP schema-v2",
            f"Validation accuracy improved {_pct(rvl['natural_language']['metrics']['accuracy'], 2)} -> "
            f"{_pct(rvl['hybrid']['metrics']['accuracy'], 2)}, tokens fell {_reduction(rvl_reduction)}, "
            f"and mean latency fell {_reduction(rvl_latency)}.",
            "Rejected because performance remained below the frozen 90% quality floor.",
        ],
        [
            "SROIE pilot / OCR replications",
            f"Frozen-OCR hybrid reduced tokens {_reduction(sroie_reduction)} overall but validation field F1 fell "
            f"{sroie['validation_baseline']['field_f1']:.3f} -> {sroie['validation_candidate']['field_f1']:.3f}; "
            "end-to-end OCR baselines were below viability.",
            "Negative evidence; OCR quality dominated and no accepted hybrid was established.",
        ],
    ]
    return _table(
        "Table 4. Earlier pilot and robustness studies",
        ["Study", "Key result", "Evidence boundary"],
        rows,
    )


def table_5() -> list[str]:
    evolver = _text("skills/pland-evolver/SKILL.md")
    ledgar = _text("experiments/ledgar-text-classification/quality-first/SKILL.md")
    harness = _text("experiments/text-classification/scripts/run_experiment.py")
    required = {
        "evolver development traces": ("development", evolver.lower()),
        "evolver bounded change": ("bounded", evolver.lower()),
        "quality-first command": ("pland:command", ledgar.lower()),
        "quality-first fallback": ("command abstains", ledgar.lower()),
        "benchmark routing": ('source = "command"', harness.lower()),
    }
    missing = [label for label, (needle, haystack) in required.items() if needle not in haystack]
    if missing:
        raise ValueError("Table 5 implementation evidence missing: " + ", ".join(missing))
    rows = [
        ["A workflow SOP can combine model-mediated and deterministic representations", "Implemented and exercised"],
        ["A command can resolve a bounded region and abstain to model fallback", "Implemented and exercised in text routing"],
        ["Deterministic routing can bypass model calls and materially reduce tokens", "Demonstrated in the original LEDGAR confirmatory test"],
        ["Token savings alone are insufficient for acceptance", "Demonstrated repeatedly by rejected studies"],
        ["Current-policy candidates preserve the complete accepted NL fallback", "Implemented in evolver policy and quality-first SOPs"],
        ["The evolver can instruct a host agent to propose bounded code changes from development traces", "Implemented as Agent Skill policy"],
        ["General autonomous pattern discovery or researcher-independent trace-to-rule synthesis", "Not established"],
        ["Autonomous DeepAgent command execution produced the main text results", "Not tested; routing used the benchmark harness"],
        ["Continuous production self-modification, monitoring, or demotion", "Not implemented; prospective"],
        ["Global least-nondeterministic optimum", "Not established; search is bounded"],
        ["Dollar, energy, or carbon savings", "Not measured; tokens and calls are proxies"],
    ]
    return _table("Table 5. What the current repository establishes", ["Claim", "Evidence status"], rows)


def render() -> str:
    lines = [
        "# Final manuscript tables",
        "",
        "<!-- Generated by paper/generate_tables.py from committed evidence. Do not edit manually. -->",
        "",
    ]
    for make_table in (table_1, table_2, table_3, table_4, table_5):
        lines.extend(make_table())
    return "\n".join(lines).rstrip() + "\n"


def check(snapshot: Path = SNAPSHOT) -> bool:
    generated = render()
    try:
        display_path = snapshot.relative_to(ROOT)
    except ValueError:
        display_path = snapshot
    if not snapshot.exists():
        print(f"missing generated table snapshot: {snapshot}")
        return False
    committed = snapshot.read_text(encoding="utf-8")
    if committed == generated:
        print(f"table evidence check passed: {display_path}")
        return True
    print("".join(difflib.unified_diff(
        committed.splitlines(keepends=True),
        generated.splitlines(keepends=True),
        fromfile=str(display_path),
        tofile="generated from current evidence",
    )))
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if FINAL_TABLES.md differs from evidence")
    args = parser.parse_args()
    if args.check:
        return 0 if check() else 1
    print(render(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
