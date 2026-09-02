---
name: document-classification
description: Execute the document classification workflow using the approved datasource collection. Use when a request requires this workflow.
---

# Document Classification SOP

1. Read the requested approved OCR document with `read_datasource`. <!-- pland:english -->
2. Identify the document's purpose and structural cues from its OCR text. <!-- pland:english -->
3. Choose the single best label from `advertisement`, `email`, `form`, `letter`, `memo`, `news`, `note`, `report`, `resume`, or `scientific`. <!-- pland:english -->
4. Return only `{"label":"<label>","confidence":<number from 0 through 1>}`. <!-- pland:english -->
