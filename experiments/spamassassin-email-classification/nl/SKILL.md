---
name: spamassassin-email-classification
description: Classify a complete historical email as spam or ham.
---

# Email classification SOP

1. Read the complete message, including headers, subject, plain text, and HTML content. <!-- pland:english -->
2. Assess sender and routing context without assuming that one unusual header proves spam. <!-- pland:english -->
3. Determine whether the message is unsolicited or deceptive, or instead legitimate correspondence or an expected newsletter. <!-- pland:english -->
4. Select exactly one allowed label: `spam` or `ham`. <!-- pland:english -->
5. Return exactly `{"label":"<spam|ham>","confidence":<0 to 1>}`. <!-- pland:english -->
