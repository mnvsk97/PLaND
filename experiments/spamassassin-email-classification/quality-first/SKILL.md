---
name: spamassassin-email-classification
description: Classify a complete historical email as spam or ham.
---

# Email classification SOP

1. Run `python classify.py` to resolve only cases that satisfy the task-local high-precision command guard. <!-- pland:command -->
2. If the command abstains, read the complete message, including headers, subject, plain text, and HTML content. <!-- pland:english -->
3. Assess sender and routing context without assuming that one unusual header proves spam. <!-- pland:english -->
4. Determine whether the message is unsolicited or deceptive, or instead legitimate correspondence or an expected newsletter. <!-- pland:english -->
5. Select exactly one allowed label: `spam` or `ham`. <!-- pland:english -->
6. Return exactly `{"label":"<spam|ham>","confidence":<0 to 1>}`. <!-- pland:english -->
