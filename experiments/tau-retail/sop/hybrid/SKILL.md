---
name: tau-retail-sop
description: Resolve retail support requests under the supplied policy.
---

1. Read the full request; list every requested outcome.
2. `python scripts/compile_policy.py --policy "$TAU_POLICY" --output "$PLAND_COMPILED_RULES"`
3. Follow [compiled-rules.md](references/compiled-rules.md).
4. Ask rather than guess missing facts. Execute each write once, verify its result, report the outcome, and stop.
