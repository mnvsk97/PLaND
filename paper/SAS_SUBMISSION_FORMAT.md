# SAS Publishers research-article format

Verified 2026-09-02 against the publisher's [instructions](https://saspublishers.com/author-instructions)
and [example article](https://saspublishers.com/article/21609/).

The submission draft uses:

- Word, A4, one-inch margins, one column
- Times New Roman 10 point, single-spaced
- concise title; authors; affiliations/contact; abstract; 5-10 keywords;
  Introduction; Methods; Results; Discussion; Conclusion; optional
  Acknowledgements; References
- one-paragraph abstract of at most 300 words
- APA 7 references in citation order
- unshaded tables with titles above
- high-quality JPEG figures with captions below

The published two-column masthead layout is publisher-applied and is not copied.
Do not invent affiliations, contact details, DOI, dates, or page numbers.

## Build and check

```bash
python paper/build_all.py
```

`PAPER.md` is the source; outputs are under `output/paper/`. The builder
checks section order, abstract length, keyword count, and pending-result markers,
then creates Markdown, PDF, DOCX, and HTML. DOCX figures are 300-DPI JPEGs
generated from SVG with `cairosvg` or macOS `qlmanage`.

Use `--allow-pending-results` only for private drafts. Render the DOCX with the
document skill's `render_docx.py` and inspect every page. The preview is not
publisher typesetting.
