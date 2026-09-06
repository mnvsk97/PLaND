---
name: ledgar-classification
description: Execute the ledgar classification workflow using the approved datasource collection. Use when a request requires this workflow.
---

# Ledgar Classification SOP

1. [S01] Identify the requested item and follow this requirement: Classify the supplied contract clause into exactly one allowed provision label by its main legal function. <!-- pland:english -->
2. [S02] Use the approved datasource tools to read only the relevant evidence; the source collection contains .json files. <!-- pland:english -->
3. [S03] Classify the evidence into exactly one known bucket: `Amendments`, `Assignments`, `Counterparts`, `Entire Agreements`, `Expenses`, `Governing Laws`, `Notices`, `Severability`, `Survival`, `Terms`. <!-- pland:english -->
4. [S04] Return exactly one JSON object shaped as `{"label":"<known bucket>"}`. <!-- pland:english -->
