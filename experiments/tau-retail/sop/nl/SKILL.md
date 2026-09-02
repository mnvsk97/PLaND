---
name: tau-retail-sop
description: Resolve retail support requests under the supplied policy.
---

1. Read the entire customer request and identify every requested outcome before acting.
2. Authenticate the customer using only information they supplied and the authentication methods allowed by policy.
3. Retrieve the relevant customer, order, item, and product records before deciding what can be changed.
4. Check order status, timing, payment method, item constraints, and all other applicable policy conditions.
5. If information is missing, ask the customer instead of guessing. Never substitute placeholder names, emails, addresses, or identifiers.
6. Explain any choices or required price differences and obtain confirmation immediately before a consequential write when policy requires it.
7. Perform each permitted write exactly once. Do not repeat a successful mutation.
8. Verify the returned state against every requested outcome.
9. Tell the customer what was completed or why it could not be completed, then stop the conversation.
