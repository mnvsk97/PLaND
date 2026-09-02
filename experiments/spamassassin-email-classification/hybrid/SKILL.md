---
name: spamassassin-email-classification
description: Classify a complete historical email as spam or ham.
---

# Email classification SOP

1. Run `python hybrid/classify.py` to parse the RFC-822 message and resolve only high-precision spam patterns. <!-- pland:command -->
2. If the command does not return a label, assess the complete headers and content for unsolicited or deceptive intent versus legitimate correspondence or an expected newsletter. <!-- pland:english -->
3. Return exactly `{"label":"<spam|ham>","confidence":<0 to 1>}`. <!-- pland:english -->
