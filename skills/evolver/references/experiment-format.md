# Experiment record format

Store each run under `runs/<run-id>/` with:

- `manifest.json`: runner, model, agent version, SOP hash, eval-set hash, production-data policy, timestamps, and environment notes;
- `cases.jsonl`: case identifier, output, expected result or rubric score, cost, latency, and error;
- `summary.json`: aggregate accuracy, cost, latency, failure counts, and comparison to the baseline;
- `decision.md`: hypothesis, observed tradeoff, and accept or reject rationale.

Use an `INVENTORY.json` entry for each accepted artifact:

```json
{
  "artifacts": {
    "parse-page-one": {
      "path": ".rule/parse_page_one.py",
      "kind": "script",
      "introduced_by": "run-id"
    }
  },
  "patterns": {
    "layout-signal": {
      "description": "Document layout contributes to bucket selection",
      "count": 12,
      "notes": "Observed across the development set"
    }
  }
}
```

Counts must come from recorded cases. Keep observations and conclusions distinct in `notes`.
