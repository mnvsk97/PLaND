#!/usr/bin/env python3
"""Compile stable retail-policy guardrails into a compact agent reference."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def compile_rules(policy: str) -> str:
    headings = [line.strip("# ") for line in policy.splitlines() if line.startswith("##")]
    mutation_terms = sorted(set(re.findall(
        r"(?:cancel|return|exchange|modify)[a-z -]{0,45}", policy.lower()
    )))
    return "\n".join([
        "# Compiled retail guardrails",
        "",
        "- Authenticate with supplied facts; never invent identity data.",
        "- Read records before writes and enforce the matching policy section.",
        "- Obtain confirmation immediately before consequential writes when required.",
        "- Treat a successful tool result as final: never repeat the same mutation.",
        "- Verify all requested outcomes, communicate the result, then stop.",
        "",
        "## Available policy sections",
        *[f"- {heading}" for heading in headings],
        "",
        "## Mutation vocabulary detected from the frozen policy",
        ", ".join(mutation_terms[:40]),
        "",
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(compile_rules(args.policy.read_text()), encoding="utf-8")


if __name__ == "__main__":
    main()
