# PLaND paper build

`PAPER.md` is the single source of truth for the paper. One command builds the
formats that are useful for editing, reviewing, printing, and sharing:

```bash
python paper/build_all.py
```

Run the command with the bundled workspace Python so the existing dependencies
from `paper/pyproject.toml` are available. The generated files are written to
`output/paper/` with one stable basename:

- `PLAND_PAPER.md` - portable source snapshot;
- `PLAND_PAPER.pdf` - print and review copy;
- `PLAND_PAPER.docx` - editable Word/submission copy; and
- `PLAND_PAPER.html` - browser-readable copy.

The four stable artifacts are checked into Git so the GitHub repository remains
the central paper reference. Rebuild and commit them whenever `PAPER.md`, a
builder, or a figure changes. Local render/QA intermediates remain ignored.

The public repository is https://github.com/mnvsk97/PLaND.

Use a different source or destination when needed:

```bash
python paper/build_all.py --source paper/PAPER.md --output-dir output/paper
```

The draft-only `--allow-pending-results` option is forwarded to the DOCX
builder. Do not use it for a submission artifact.

The target manuscript length is five A4 pages including references. Verify the
page count and inspect every rendered page after meaningful content or layout
changes.
