# PLaND

Path to Least Non Determinism (PLaND) is an evaluation-driven methodology for moving stable SOP work from natural language into references, Python, or Bash while retaining model judgment where it preserves task quality.

The central rule is: freeze the comparison, change only the workflow skill package, and accept a candidate only when it passes both the task-quality contract and the selected expense objective.

## Headline finding

On the 1,000-case LEDGAR confirmatory test, the accepted hybrid stayed inside the prespecified two-point quality margin and reduced tokens by 40.02%. It replaced 411 of 1,000 model calls with deterministic command calls. Those bypasses produced 97.24% of the token saving; prompt shortening produced the remaining 2.76%. An optimized post-change replication reproduced the -0.8-point accuracy difference, 40.02% token reduction, and 411-call bypass.

The negative results are equally important: CFPB and SpamAssassin saved tokens but failed quality gates, while QS-OCR, SROIE, and RVL-CDIP stopped after nonviable baselines.

## Repository map

- [`skills/generate-initial-version`](skills/generate-initial-version/) - creates an initial open-ended agent and natural-language SOP from task inputs.
- [`skills/pland-evolver`](skills/pland-evolver/) - evaluates bounded SOP changes against frozen contracts.
- [`datasets`](datasets/) - preparation scripts, source proofs, hashes, and audit tests.
- [`experiments`](experiments/) - benchmark definitions, SOPs, runners, decisions, and aggregate findings.
- [`paper/PAPER.md`](paper/PAPER.md) - manuscript source of truth.
- [`output/paper`](output/paper/) - generated Markdown, PDF, DOCX, and HTML paper artifacts.

## Optimized local Ollama setup

The refreshed text collection used Ollama 0.33.0, `qwen3:14b`, a 4,096-token context, no thinking, temperature 0, an exact JSON schema, and two parallel requests. Keep the model tag and digest fixed throughout a comparison.

### macOS with Homebrew service

```bash
ollama pull qwen3:14b

launchctl setenv OLLAMA_FLASH_ATTENTION 1
launchctl setenv OLLAMA_KV_CACHE_TYPE q8_0
launchctl setenv OLLAMA_NUM_PARALLEL 2
launchctl setenv OLLAMA_MAX_LOADED_MODELS 1
launchctl setenv OLLAMA_KEEP_ALIVE -1

brew services restart ollama
```

### Linux service

Add these values under `[Service]` in `systemctl edit ollama.service`:

```ini
[Service]
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_KEEP_ALIVE=-1"
```

Then restart Ollama:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### Preload and verify

```bash
curl -fsS http://127.0.0.1:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3:14b","keep_alive":-1,"options":{"num_ctx":4096}}' \
  >/dev/null

ollama ps
ollama show qwen3:14b
```

`ollama ps` should report the model fully loaded on the GPU, a 4,096-token request context, and unlimited keep-alive. Two parallel 4K requests allocate an 8K server context internally. Start with one worker on lower-memory machines; parallelism increases KV-cache memory.

These settings persist beyond one experiment. On macOS, remove them with `launchctl unsetenv VARIABLE` and restart the service. On Linux, remove the service overrides and restart Ollama.

## Run a paired validation

This example assumes LEDGAR has been prepared at `tmp/confirmatory-datasets/ledgar`:

```bash
export OLLAMA_FLASH_ATTENTION=1
export OLLAMA_KV_CACHE_TYPE=q8_0
export OLLAMA_NUM_PARALLEL=2
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_KEEP_ALIVE=-1

python experiments/text-classification/scripts/run_experiment.py \
  --dataset tmp/confirmatory-datasets/ledgar \
  --split validation \
  --system-prompt experiments/ledgar-text-classification/system-prompt.md \
  --sop experiments/ledgar-text-classification/nl/SKILL.md \
  --workers 2 \
  --output tmp/ledgar-validation-nl.json

python experiments/text-classification/scripts/run_experiment.py \
  --dataset tmp/confirmatory-datasets/ledgar \
  --split validation \
  --system-prompt experiments/ledgar-text-classification/system-prompt.md \
  --sop experiments/ledgar-text-classification/hybrid/SKILL.md \
  --classifier experiments/ledgar-text-classification/hybrid/classify.py \
  --workers 2 \
  --output tmp/ledgar-validation-hybrid.json

python experiments/text-classification/scripts/compare.py \
  --nl tmp/ledgar-validation-nl.json \
  --hybrid tmp/ledgar-validation-hybrid.json \
  --minimum-accuracy 0.80 \
  --output tmp/ledgar-validation-comparison.json
```

Do not open a test split unless validation passes. The runner stores runtime
settings, SOP and invoked-classifier hashes, shared frozen-artifact hashes,
outputs, tokens, timings, and resumable checkpoints. The comparison preserves
the variant SOP hashes and rejects mismatched runtime configurations.

## Tests and paper build

```bash
python -m unittest discover -s skills/generate-initial-version/tests -v
python -m unittest discover -s skills/pland-evolver/tests -v
python -m unittest discover -s experiments/text-classification/tests -v
python paper/build_all.py
```

See [`paper/README.md`](paper/README.md) for paper outputs. The optimized collection is summarized in [`experiments/RECOLLECTION_2026-09-02.md`](experiments/RECOLLECTION_2026-09-02.md).

## Reproducibility boundary

Large, copyrighted, licensed, or sensitive source data is not checked in. The repository retains source references, selection rules, hashes, proof manifests, aggregate results, and reproduction code. Post-change LEDGAR test runs are replications because the same cases had already been evaluated; they are not represented as newly untouched tests.
