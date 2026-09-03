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

Rebuild and commit these files after changing the source, figures, or builders.
Use `--source` or `--output-dir` to override paths. The draft-only
`--allow-pending-results` flag must not be used for submission.

The public repository is https://github.com/mnvsk97/PLaND. Keep the PDF at five
A4 pages including references and visually inspect every page.
