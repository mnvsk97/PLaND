---
name: spamassassin-classification
description: Execute the spamassassin classification workflow using the approved datasource collection. Use when a request requires this workflow.
---

# Spamassassin Classification SOP

1. [S01] Identify the requested item and follow this requirement: Classify one email as 'spam' when it is unsolicited bulk, fraudulent, or promotional abuse, otherwise as 'ham'. Use the complete sanitized email content and ordinary email intent cues. Return only a JSON object with the selected label; do… <!-- pland:english -->
2. [S02] Use the approved datasource tools to read only the relevant evidence; the source collection contains .json files. <!-- pland:english -->
3. [S03] Classify the evidence into exactly one known bucket: `ham`, `spam`. <!-- pland:english -->
4. [S04] Return exactly one JSON object shaped as `{"label":"<known bucket>"}`. <!-- pland:english -->
