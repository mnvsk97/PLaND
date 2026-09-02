# Compiled retail guardrails

- Authenticate with supplied facts; never invent identity data.
- Read records before writes and enforce the matching policy section.
- Obtain confirmation immediately before consequential writes when required.
- Treat a successful tool result as final: never repeat the same mutation.
- Verify all requested outcomes, communicate the result, then stop.

## Available policy sections
- Domain basic
- User
- Product
- Order
- Generic action rules
- Cancel pending order
- Modify pending order
- Modify payment
- Modify items
- Return delivered order
- Exchange delivered order

## Mutation vocabulary detected from the frozen policy
cancel, cancel or modify pending orders, cancel pending order, cancellation, cancellation reason, cancelled, cancelled if its status is , exchange, exchange delivered order, exchange or modify order tools can only be called onc, exchange requested, exchanged, exchanged if its status is , exchanged to an available new item of the same produc, modify, modify items, modify its shipping address, modify or cancel the order anymore, modify payment, modify pending order, modify shirt to shoe, modify the payment method to gift card, modify their default user address, return, return delivered order, return items, return or exchange delivered orders, return requested, returned, returned if its status is
