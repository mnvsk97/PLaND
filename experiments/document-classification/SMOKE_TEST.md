# Initial agent smoke test

Date: 2026-09-01
Model: Ollama `qwen3:14b`
DeepAgents: `0.7.12`
LangChain Ollama: `1.1.0`

## Case

- Datasource: `email/2085319449.txt`
- Audited expected label: `email`
- Model settings: temperature `0`, seed `42`, reasoning disabled

## Results

### Automatic activation attempt

The request asked the agent to classify the document using the
`document-classification` SOP. The agent called `read_datasource`, but it did
not first call `read_file` for the SOP. It returned:

```json
{"label":"UK Ingredient Disclosure","confidence":0.95}
```

This fails the output-label contract and shows that mentioning the skill by
name did not reliably activate progressive loading with this local model.

### Explicit skill-load attempt

The request explicitly instructed the agent to call `read_file` for
`/skills/document-classification/SKILL.md` before classification. The trace
confirmed this sequence:

1. `read_file("/skills/document-classification/SKILL.md")`
2. `read_datasource("email/2085319449.txt")`
3. final JSON output

The output was:

```json
{"label":"memo","confidence":0.95}
```

The output is schema-valid but incorrect against the audited `email` label.

## Conclusion

The generated agent, local Ollama model, DeepAgents skill middleware, and
approved datasource tool all execute. The initial agent is not yet acceptable:
automatic skill activation is unreliable and the first explicitly skill-backed
classification is incorrect. These are separate failure modes and must remain
separate in later traces and scoring.

Do not modify the SOP from this single case. First add a deterministic runner
that always loads the workflow skill, then run the frozen development split to
measure the initial baseline before PLaND evolution.
