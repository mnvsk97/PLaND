# Evidence contract

The reviewed plan is the authority for datasets, split roles and sizes, model
identity, runtime, seeds, quality metric, readiness threshold, candidate
limit, comparison gates, and final-test release. The collection operator may
resolve paths but may not change those choices.

The plan must be machine-readable JSON with these fields:

```json
{
  "schema_version": 1,
  "study_id": "user-chosen-id",
  "protocol": "path/to/human-readable-protocol.md",
  "datasets": ["dataset-a"],
  "splits": {"development": 500, "selection": 1000, "final_test": 500},
  "model": {"name": "model-name", "digest": "full-local-weight-digest"},
  "limits": {"baseline_attempts": 1, "candidate_attempts": 1},
  "acceptance": {"quality_metric": "accuracy"},
  "paper": {"source": "paper/PLaND.md"}
}
```

The split values above are fixed for the fresh paper collection. Additional
task-specific fields are allowed and are frozen by the plan hash.

Hosted models do not expose a locally verifiable weight digest. For a hosted
run, replace `digest` with an `identity` object containing `kind: hosted`, the
provider, exact endpoint, matching model name, and a 64-character
configuration SHA-256. This configuration hash identifies frozen request and
routing settings; it must never be described as a model-weight digest.

Every executed command must record:

- exact argv and working directory;
- start/end timestamps and exit status;
- Git commit and initial working-tree state;
- plan and protocol hashes;
- declared input hashes before execution;
- declared output hashes after execution;
- complete stdout and stderr logs;
- failures and retries without overwriting earlier records.

Every model result must additionally identify the dataset and split, case IDs,
expected and actual outputs, scorer, model identity, decoding/runtime
settings, SOP and executable package hashes, token counts, latency, model versus
command work, fallback/escape traces, and case-level correctness.

Baseline and candidate comparisons are valid only when their frozen dataset,
cases, model identity, prompt, runner, scorer, seed/runtime, permissions, and
baseline fallback contract match. Never pool runs from different runtime
conditions.

The final evidence manifest must cover the plan, protocol, state, ledger,
decision artifacts, run outputs, comparisons, summaries, logs, and any scripts
or SOP packages created for the study. Raw licensed inputs remain outside Git;
record their hashes and provenance instead.
