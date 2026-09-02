---
name: sroie-receipt-extraction
description: Extract company, date, address, and total from receipt text.
---

# Receipt extraction SOP

1. Read all receipt words in their supplied reading order. <!-- pland:english -->
2. Identify the merchant or company name, normally near the beginning. <!-- pland:english -->
3. Identify the transaction date and retain its printed representation. <!-- pland:english -->
4. Identify the merchant address, joining its consecutive lines. <!-- pland:english -->
5. Identify the final payable total rather than a subtotal, tax, cash, or change value. <!-- pland:english -->
6. Check every extracted value against the receipt evidence. <!-- pland:english -->
7. Return only the required JSON object. <!-- pland:english -->
