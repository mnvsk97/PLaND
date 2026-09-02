# SAS Publishers research-article submission format

Verified on 2026-09-02 from the publisher's [author
instructions](https://saspublishers.com/author-instructions) and the supplied
[example article](https://saspublishers.com/article/21609/).

The repository manuscript follows the submission instructions, not the
publisher's post-acceptance typesetting:

- Microsoft Word document;
- A4 page, one-inch margins, single column;
- Times New Roman, 10 point, single spacing, including tables and references;
- concise title, authors, affiliations, corresponding-author details, abstract,
  keywords, Introduction, Material and Methods or Experimental Section,
  Results, Discussion, Conclusion, optional Acknowledgements, and References;
- abstract no longer than 300 words, one paragraph, no subheadings;
- five to ten comma-separated keywords;
- APA 7 references in first-citation order, with one consistent in-text style;
- table number and title above each table, without color shading; and
- high-quality JPEG figures placed in the text, with number and title below.

The linked published PDF uses a two-column journal layout, running heads, and a
publisher masthead. Those elements are not copied into this submission draft
because they are applied after acceptance. The manuscript does not invent a
DOI, publication dates, journal page numbers, institutional affiliations, or
corresponding-author contact details.

## Reproducible build

`PAPER.md` is the source of truth. Build the submission DOCX with the bundled
workspace Python after marking the document operation as required by the
document-artifact workflow:

```bash
python paper/build_manuscript.py \
  paper/PAPER.md \
  output/docx/PLAND_SAS_SUBMISSION.docx
```

The builder validates the required section order, the 300-word abstract limit,
the 5-10 keyword requirement, and unresolved result markers. It prepares the
three existing SVG diagrams as 300-DPI JPEG files using the free `cairosvg`
dependency or the macOS `qlmanage` fallback. It then embeds the JPEGs and puts
their captions below them. Tables are fixed-width, single-spaced, unshaded, and
use Times New Roman 10 point.

During drafting only, `--allow-pending-results` permits a private DOCX while
result insertion markers remain. Never use that flag for the submission file.
After building, render and inspect every page with the document skill's
`render_docx.py`; the emitted PDF is the paper preview, not a recreation of the
publisher's post-acceptance layout.
