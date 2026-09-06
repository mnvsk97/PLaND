---
name: ledgar-classification
description: Execute the ledgar classification workflow using the approved datasource collection. Use when a request requires this workflow.
---

# Ledgar Classification SOP

1. [S01] Identify the requested item and follow this requirement: Classify one contract clause by its primary legal function into exactly one supplied LEDGAR provision label. Base the decision only on the clause text and label meanings. Return only a JSON object with the selected label; do not expose… <!-- pland:english -->
2. [S02] Use the approved datasource tools to read only the relevant evidence; the source collection contains .json files. <!-- pland:english -->
3. [S03] Run the bounded local `classify.py` rules; accept only a supplied label with a named matching rule. Abstain on every unrecognized clause so the exact English fallback handles it. <!-- pland:command fallback=S03 -->
   Fallback [S03]: Classify the evidence into exactly one known bucket: `Amendments`, `Assignments`, `Counterparts`, `Entire Agreements`, `Expenses`, `Governing Laws`, `Notices`, `Severability`, `Survival`, `Terms`. <!-- pland:fallback -->
4. [S04] Return exactly one JSON object shaped as `{"label":"<known bucket>"}`. <!-- pland:english -->
