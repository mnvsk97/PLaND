---
name: cfpb-classification
description: Execute the cfpb classification workflow using the approved datasource collection. Use when a request requires this workflow.
---

# Cfpb Classification SOP

1. [S01] Identify the requested item and follow this requirement: Classify one consumer complaint narrative into exactly one supplied CFPB product category according to the financial product that is the main subject of the complaint. Base the decision only on the narrative and label meanings. Return… <!-- pland:english -->
2. [S02] Use the approved datasource tools to read only the relevant evidence; the source collection contains .json files. <!-- pland:english -->
3. [S03] Classify the evidence into exactly one known bucket: `Checking or savings account`, `Credit card`, `Credit reporting or other personal consumer reports`, `Debt collection`, `Money transfer, virtual currency, or money service`, `Mortgage`, `Payday loan, title loan, personal loan, or advance loan`, `Prepaid card`, `Student loan`, `Vehicle loan or lease`. <!-- pland:english -->
4. [S04] Return exactly one JSON object shaped as `{"label":"<known bucket>"}`. <!-- pland:english -->
