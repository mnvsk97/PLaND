---
name: document-classification
description: Execute the document classification workflow using the approved datasource collection. Use when a request requires this workflow.
---

# Document Classification SOP

1. Run `analyze_datasource` on the requested approved OCR document.
2. Use its deterministic signals and the document text to choose the single best label from `advertisement`, `email`, `form`, `letter`, `memo`, `news`, `note`, `report`, `resume`, or `scientific`; a fax cover sheet or other fillable template is a `form`, even when it carries a message.
3. Return only `{"label":"<label>","confidence":<number from 0 through 1>}`.
