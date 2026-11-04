# RetailOps Objective 1 - Test Questions

## 1. Returns & Escalations (`returns.md`)
- **Q:** Can a customer return a damaged product without a receipt?
  - **Expected:** Escalate missing receipt to Store Manager; damaged items also require Store Manager inspection and approval before refund/replacement.
  - **Expected Source:** `returns.md`
- **Q:** A customer bought 3 shirts under Buy 2 Get 1 (B2G1) and wants to return one of the paid shirts. How is the refund handled?
  - **Expected:** The benefit is recalculated. Since the full qualifying set condition is no longer met, the value of the free item (lowest-priced item) is deducted from the refund, or the customer must return the free item as well.
  - **Expected Source:** `returns.md`

## 2. Billing & Promotions (`billing.md`)
- **Q:** Can a customer use a WhatsApp discount coupon on Kirana or innerwear items?
  - **Expected:** No. Coupons are not valid on partner-brand categories like Kirana or on innerwear.
  - **Expected Source:** `billing.md`
- **Q:** What should I do if a customer has a ₹1,000 gift voucher but only wants to buy ₹600 worth of items?
  - **Expected:** Inform the customer that gift vouchers must be redeemed in full in a single transaction; partial redemption is not permitted.
  - **Expected Source:** `billing.md`

## 3. Inventory (`inventory.md`)
- **Q:** We just unloaded a truck and two cartons are missing compared to the ASN. What is the procedure?
  - **Expected:** Log a discrepancy ticket in the ERP system and get the Store Manager's signature before accepting the delivery.
  - **Expected Source:** `inventory.md`

## 4. Out-of-Scope Guardrail Test (`None`)
- **Q:** How many paid sick leaves do part-time store associates get per year?
  - **Expected:** Refusal stating the information is not in the available SOPs and advising to consult the Store Manager.
  - **Expected Source:** `None`