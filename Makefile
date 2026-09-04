PYTHON ?= .venv/bin/python
UV ?= uv
CONFIRMATORY_DATASET_ROOT ?= tmp/confirmatory-datasets
QUALITY_FIRST_DATASET_ROOT ?= tmp/quality-first-datasets
REPRODUCTION_ROOT ?= tmp/reproduction-runs

.PHONY: setup verify reproduce-paper reproduce-experiments

setup:
	$(UV) sync --frozen

# Offline and read-only with respect to committed artifacts. This target runs
# tests and checksum checks; it never invokes Ollama or an experiment runner.
verify:
	$(PYTHON) scripts/verify_repository.py

reproduce-paper:
	$(PYTHON) paper/build_all.py
	$(PYTHON) paper/build_final_submission.py

# This is intentionally explicit and expensive. Both runners perform their
# own dataset, model-digest, and frozen-runtime preflight checks.
reproduce-experiments:
	test -d "$(CONFIRMATORY_DATASET_ROOT)"
	test -d "$(QUALITY_FIRST_DATASET_ROOT)"
	OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 \
	OLLAMA_NUM_PARALLEL=2 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=-1 \
	$(PYTHON) experiments/variance-study/run_variance_study.py \
		--dataset-root "$(CONFIRMATORY_DATASET_ROOT)" \
		--output-root "$(REPRODUCTION_ROOT)/variance"
	$(PYTHON) experiments/variance-study/aggregate.py \
		--study-dir "$(REPRODUCTION_ROOT)/variance/ledgar-text-classification/results/variance-study-20260903" \
		--study-dir "$(REPRODUCTION_ROOT)/variance/cfpb-text-classification/results/variance-study-20260903" \
		--study-dir "$(REPRODUCTION_ROOT)/variance/spamassassin-email-classification/results/variance-study-20260903" \
		--output "$(REPRODUCTION_ROOT)/variance/summary.json"
	OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 \
	OLLAMA_NUM_PARALLEL=2 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=-1 \
	$(PYTHON) experiments/quality-first-replications/run_study.py \
		--dataset-root "$(QUALITY_FIRST_DATASET_ROOT)" \
		--output-root "$(REPRODUCTION_ROOT)/quality-first"
	$(PYTHON) experiments/variance-study/aggregate.py \
		--study-dir "$(REPRODUCTION_ROOT)/quality-first/ledgar-text-classification/results/quality-first-validation-20260903" \
		--study-dir "$(REPRODUCTION_ROOT)/quality-first/cfpb-text-classification/results/quality-first-validation-20260903" \
		--study-dir "$(REPRODUCTION_ROOT)/quality-first/spamassassin-email-classification/results/quality-first-validation-20260903" \
		--seeds 20260906 20260907 20260908 \
		--candidate-variant quality-first \
		--runner-path experiments/quality-first-replications/run_study.py \
		--output "$(REPRODUCTION_ROOT)/quality-first/summary.json"
