# PLaND paper build

`PAPER.md` is the editable repository manuscript source. From the repository
root, install the locked Python environment and build all formats:

```bash
make setup
make reproduce-paper
```

The root `.python-version` and `uv.lock` select the exact Python and package
versions. LibreOffice (`soffice` on `PATH`) is required for the
HTML conversion; on macOS it can be installed with `brew install --cask
libreoffice`.

Outputs use one basename under `output/paper/`:

- `PLAND_PAPER.md`: source snapshot
- `PLAND_PAPER.pdf`: print/review copy
- `PLAND_PAPER.docx`: editable submission copy
- `PLAND_PAPER.html`: browser copy

The approved submission artifact is
`output/paper/PLAND_SUBMISSION_READY_FINAL.pdf`. It preserves Asit's reviewed
nine-page typesetting and replaces Figure 1 on page 2 with representative
numbered excerpts from the actual LEDGAR natural-language and hybrid SOPs.
Rebuild that exact page composition from the frozen reviewed base and approved
replacement page with:

```bash
python paper/build_final_submission.py
```

Use `python paper/build_final_submission.py --check` for a non-mutating,
page-by-page content verification against the committed final PDF. The builder
checks the SHA-256 hashes of both frozen inputs before assembling any output.
The `PLAND_PAPER.*` files remain the repository-generated editable/source
bundle. Run the checks recorded in `FINAL_ALIGNMENT.md` before replacing the
approved PDF.

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

The public repository is https://github.com/mnvsk97/PLaND. Preserve the approved
submission PDF at nine A4 pages and visually inspect every page.
