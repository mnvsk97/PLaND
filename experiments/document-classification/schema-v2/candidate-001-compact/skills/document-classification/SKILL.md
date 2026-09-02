---
name: document-classification
description: Execute the document classification workflow using the approved datasource collection. Use when a request requires this workflow.
---

# Document Classification SOP

1. Execute the approved compact-document command through `compact_datasource`: `python3 scripts/compact_document.py --file <relative-path>`. <!-- pland:command -->
2. Identify the document's purpose and structural cues from the returned OCR excerpt and metadata. <!-- pland:english -->
3. Apply these precedence rules: electronic headers such as `From:`, `Sent:`, `To:`, and `Subject:` make an `email`; a cover sheet, questionnaire, application, or fillable template is a `form`; use `letter` only when neither of those stronger structures applies. <!-- pland:english -->
4. Otherwise choose the single best label from `advertisement`, `memo`, `news`, `note`, `report`, `resume`, or `scientific`. <!-- pland:english -->
5. Return only `{"label":"<label>","confidence":<number from 0 through 1>}`. <!-- pland:english -->
