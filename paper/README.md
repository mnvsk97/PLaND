# PLaND paper build

`PAPER.md` is the source. From the repository root, install Python dependencies
and build all formats:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install ./paper
python paper/build_all.py
```

Python 3.11+ is required. LibreOffice (`soffice` on `PATH`) is required for the
HTML conversion; on macOS it can be installed with `brew install --cask
libreoffice`.

Outputs use one basename under `output/paper/`:

- `PLAND_PAPER.md`: source snapshot
- `PLAND_PAPER.pdf`: print/review copy
- `PLAND_PAPER.docx`: editable submission copy
- `PLAND_PAPER.html`: browser copy

The paper builders follow the published SJET visual authority at
https://saspublishers.com/article/21609/: A4 pages, full-width first-page front
matter, a two-column journal body, blue headings, spanning figures/tables,
running headers, and bordered footers. Publication-only DOI, issue, dates, and
page metadata are intentionally omitted until assigned.

Build the prepared-only cover letter from the same repository state as the
manuscript and experiment evidence:

```bash
python paper/build_cover_letter.py
```

Build the local arXiv source bundle without uploading it:

```bash
python paper/build_arxiv.py
```

The arXiv metadata uses primary category `cs.CL` with cross-lists `cs.AI` and
`cs.LG`. Its identifier and license choice remain pending until an actual
submission. The cover letter omits a date, editor name, phone, ORCID, and any
other unconfirmed submission metadata.

Rebuild and commit these files after changing the source, figures, or builders.
Use `--source` or `--output-dir` to override paths. The draft-only
`--allow-pending-results` flag must not be used for submission.

The public repository is https://github.com/mnvsk97/PLaND. Keep the PDF at five
A4 pages including references and visually inspect every page.
