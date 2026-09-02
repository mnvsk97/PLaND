---
name: document-classification
description: Execute the document classification workflow using the approved datasource collection. Use when a request requires this workflow.
---

# Document Classification SOP

1. Run `python scripts/trim_document.py --file <requested relative path>` through `compact_datasource` and use its text. <!-- pland:command -->
2. Identify the document's purpose, audience, structure, headings, fields, and writing style while allowing for OCR errors. <!-- pland:english -->
3. Choose the strongest structural class: `email` has electronic message headers; `form` has fields to complete; `questionnaire` is organized as questions; `invoice` requests itemized payment; `budget` presents planned financial amounts; `presentation` contains slide-like titles or fragments; `file folder` is a sparse cover, tab, or routing sheet; and `handwritten` is predominantly informal handwritten text. <!-- pland:english -->
4. If no structural class dominates, choose the best content class: `advertisement` promotes something; `letter` is addressed correspondence; `memo` is internal organizational correspondence; `news article` is journalistic; `resume` summarizes a person's qualifications; `specification` states technical requirements; `scientific publication` presents scholarly research; and `scientific report` records technical findings or status without publication structure. <!-- pland:english -->
5. If the apparent type is not an allowed label, map it to the closest allowed class by purpose and structure; for example, a press release or press statement is usually a `news article` or `presentation`, never a new label. Return only `{"label":"<label>","confidence":<number from 0 through 1>}` using one of the 16 labels named above. <!-- pland:english -->
