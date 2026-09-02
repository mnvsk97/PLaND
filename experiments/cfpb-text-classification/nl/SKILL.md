---
name: cfpb-complaint-routing
description: Route a consumer complaint narrative to one approved financial product.
---

# Complaint routing SOP

1. Read the complete consumer complaint narrative. <!-- pland:english -->
2. Identify the financial product that is the primary subject of the problem. <!-- pland:english -->
3. Distinguish the product from related institutions, payment methods, and incidental products mentioned in the narrative. <!-- pland:english -->
4. Compare the primary product with every allowed label and select exactly one. <!-- pland:english -->
5. Return exactly `{"label":"<allowed label>","confidence":<0 to 1>}`. <!-- pland:english -->
