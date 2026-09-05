# PLaND

Path to Least Non-Determinism (PLaND) is a methodology for replacing stable
model-mediated SOP steps with deterministic references or scripts while
preserving measured quality.

This repository contains the two PLaND skills, the experiment code and result
artifacts used in the paper, dataset preparation and audit scripts, and the
paper in multiple file formats.

## Start here

| If you want to... | Read or run |
|---|---|
| Understand the reported findings | [`RESULTS.md`](RESULTS.md) |
| Reproduce the datasets and experiments | [`REPRODUCE.md`](REPRODUCE.md) |
| Verify the repository without rerunning models | `make setup && make verify` |
| Read the paper | [`paper/PAPER.md`](paper/PAPER.md) |
| Download another paper format | [`output/paper/`](output/paper/) |
| Inspect the methodology | [`skills/`](skills/) |

## Repository map

- `skills/` — the initial-version generator and evaluation-gated evolver.
- `datasets/` — public-source locks, preparation scripts, proofs, and audits.
- `experiments/` — experiment SOPs, runners, committed summaries, and safe
  traces.
- `paper/` — manuscript source and submission build inputs.
- `output/paper/` — generated Markdown, PDF, DOCX, HTML, and submission files.
- `scripts/` — repository-level verification utilities.
- component-local `tests/` directories — dataset, experiment, skill, and paper
  tests collected by the repository verifier.

## Quick verification

Requirements: Git, Python 3.11–3.14, and
[`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/mnvsk97/PLaND.git
cd PLaND
make setup
make verify
```

`make verify` is offline and does not rerun a model or rewrite committed
results. It runs the tests and validates the evidence and paper manifests.

## Reproducibility boundary

The code needed to regenerate the reported results is included. Public datasets
can be prepared by the scripts in `datasets/scripts/`. Exact reproduction also
requires the same frozen input bytes and Ollama model digest recorded by each
study.

The frozen CFPB API response and SROIE rows snapshot are not redistributed in
this repository. Without those local snapshots, the corresponding runners can
still be used on newly fetched data, but that is a new experimental condition—not
an exact reproduction of the reported numbers. See [`REPRODUCE.md`](REPRODUCE.md)
for the complete matrix and commands.
