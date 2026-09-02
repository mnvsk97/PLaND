---
name: document-classification
description: Execute the document classification workflow using the approved datasource collection. Use when a request requires this workflow.
---

# Document Classification SOP

1. Read the requested approved OCR document with `read_datasource`.
2. Identify the document's purpose and structural cues from its OCR text.
3. Apply these precedence rules: electronic headers such as `From:`, `Sent:`, `To:`, and `Subject:` make an `email`; a cover sheet, questionnaire, application, or fillable template is a `form`; use `letter` only when neither of those stronger structures applies.
4. Otherwise choose the single best label from `advertisement`, `memo`, `news`, `note`, `report`, `resume`, or `scientific`.
5. Return only `{"label":"<label>","confidence":<number from 0 through 1>}`.
