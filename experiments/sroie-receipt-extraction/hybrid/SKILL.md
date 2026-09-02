---
name: sroie-receipt-extraction
description: Extract company, date, address, and total from receipt text.
---

# Receipt extraction SOP

1. Run `python scripts/extract_candidates.py --input <case-json-or-ocr-json>` to deterministically find and compact likely fields. <!-- pland:command -->
2. Resolve ambiguous company and address candidates from the supplied evidence. <!-- pland:english -->
3. Return only the required JSON object, retaining printed date and total representations. <!-- pland:english -->
