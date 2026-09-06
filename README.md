# PLaND

Path to Least Non-Determinism (PLaND) is a methodology for moving suitable
model-mediated SOP decisions into executable code, subject to measured quality
requirements.

## Paper

The manuscript is available in four matching formats:

- [PDF](paper/PLaND.pdf)
- [Word](paper/PLaND.docx)
- [HTML](paper/PLaND.html)
- [Markdown](paper/PLaND.md)

The three figures used by the paper are in [`paper/figures/`](paper/figures/).

## Repository structure

```text
PLaND/
├── paper/          paper formats and figures
├── experiments/    experiment SOPs, reproduction scripts, and results
├── datasets/       dataset preparation, source locks, and audit scripts
├── skills/         the two PLaND methodology skills
└── reproduce/      locked Python environment and repository verification
```

## Experiment collection

The historical local-model result trees have been removed before the new
collection. Shared experiment code is under:

```text
experiments/
├── collection/                      shared runner, scorer, and tests
└── <model-name>/
    └── YYYY-MM-DD-HH-MM-am|pm/      frozen plan and collected evidence
```

## Verify the repository

Requirements: Git, Python 3.11–3.14, and
[`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/mnvsk97/PLaND.git
cd PLaND
uv sync --project reproduce --frozen
reproduce/.venv/bin/python reproduce/verify.py
```

`reproduce/pyproject.toml` lists the Python dependencies and
`reproduce/uv.lock` freezes their exact resolved versions. They are grouped
under `reproduce/` because they exist only to run and verify the experiments.

Until the new collection is complete, repository verification covers source,
tests, and the existing manuscript artifacts; it does not claim that deleted
historical model outputs remain reproducible from this checkout.

## Prepare datasets

Dataset URLs, revisions, file sizes, SHA-256 hashes, and redistribution limits
are recorded in [`datasets/sources.lock.json`](datasets/sources.lock.json).
Preparation and audit commands are in [`datasets/README.md`](datasets/README.md).

Raw benchmark records are not committed. LEDGAR and SpamAssassin can be rebuilt
from the locked public files. Exact CFPB reconstruction requires the
frozen local snapshot recorded by the source lock; using current upstream data
is a new experimental condition.

## New collection

The new LEDGAR → CFPB → SpamAssassin collection uses exactly 500 development,
1,000 selection, and 500 final-test cases per dataset. Its reviewed `plan.json`
and `protocol.md` live inside the timestamped model directory. The repo-local
collection skill records execution and enforces selection/final-test gates.
