---
name: ledgar-contract-routing
description: Classify a contract clause into one approved provision category.
---

# Contract routing SOP

1. Read the complete contract clause. <!-- pland:english -->
2. Run `python classify.py` on the clause and allowed labels; accept only a high-confidence result. <!-- pland:command -->
3. If the command abstains, identify the clause's main legal function and compare it with every allowed label. <!-- pland:english -->
4. Return exactly `{"label":"<allowed label>","confidence":<0 to 1>}`. <!-- pland:english -->
