# PLaND paper build

`PAPER.md` is the source. Build all checked-in formats with the bundled
workspace Python:

```bash
python paper/build_all.py
```

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
