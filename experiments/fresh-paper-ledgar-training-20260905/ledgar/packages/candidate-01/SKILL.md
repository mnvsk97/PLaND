---
name: ledgar-classification
description: Execute the ledgar classification workflow using the approved datasource collection. Use when a request requires this workflow.
---

# Ledgar Classification SOP

1. [S01] Identify the requested item and follow this requirement: Classify the supplied contract clause into exactly one allowed provision label by its main legal function. <!-- pland:english -->
2. [S02] Read the complete evidence text supplied in this request. <!-- pland:english -->
3. [S03] Execute `python classify.py` through its `classify(text, labels)` function on the supplied evidence. Use a valid single-label result only when a declared phrase matches without a conflicting label; otherwise execute the exact English fallback. <!-- pland:command fallback=S03 -->
   Fallback [S03]: Classify the evidence into exactly one known bucket: `Amendments`, `Assignments`, `Counterparts`, `Entire Agreements`, `Expenses`, `Governing Laws`, `Notices`, `Severability`, `Survival`, `Terms`. <!-- pland:fallback -->
4. [S04] Return exactly one JSON object shaped as `{"label":"<known bucket>"}`. <!-- pland:english -->
