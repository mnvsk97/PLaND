---
name: cfpb-complaint-routing
description: Route a consumer complaint narrative to one approved financial product.
---

# Complaint routing SOP

1. Read the complete consumer complaint narrative. <!-- pland:english -->
2. Run `python classify.py` on the narrative and allowed labels; accept only a high-confidence result. <!-- pland:command -->
3. If the command abstains, identify the financial product that is the primary subject of the problem. <!-- pland:english -->
4. Distinguish the product from related institutions, payment methods, and incidental products mentioned in the narrative. <!-- pland:english -->
5. Compare the primary product with every allowed label and select exactly one. <!-- pland:english -->
6. Return exactly `{"label":"<allowed label>","confidence":<0 to 1>}`. <!-- pland:english -->
