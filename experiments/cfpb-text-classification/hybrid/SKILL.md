---
name: cfpb-complaint-routing
description: Route a consumer complaint narrative to one approved financial product.
---

# Complaint routing SOP

1. Read the complete consumer complaint narrative. <!-- pland:english -->
2. Run `python classify.py` on the narrative and allowed labels; accept only a high-confidence result. <!-- pland:command -->
3. If the command abstains, identify the primary financial product and distinguish it from incidental products. <!-- pland:english -->
4. Return exactly `{"label":"<allowed label>","confidence":<0 to 1>}`. <!-- pland:english -->
