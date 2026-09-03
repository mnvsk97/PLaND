---
name: ledgar-contract-routing
description: Classify a contract clause into one approved provision category.
---

# Contract routing SOP

1. Read the complete contract clause. <!-- pland:english -->
2. Run `python classify.py` on the clause and allowed labels; accept only a high-confidence result. <!-- pland:command -->
3. If the command abstains, identify the clause's main legal function rather than matching one isolated word. <!-- pland:english -->
4. Compare that function with every allowed provision label. <!-- pland:english -->
5. Select the single best label, using the most specific applicable function when several concepts appear. <!-- pland:english -->
6. Return exactly `{"label":"<allowed label>","confidence":<0 to 1>}`. <!-- pland:english -->
