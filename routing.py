import re


def classify_issue(description: str) -> dict:
    """Classifies operational store incidents into categories, responsible roles, and SOP actions."""
    text = " ".join(description.casefold().split())

    if not text:
        raise ValueError("Issue description cannot be empty.")

    matches = []

    def add(rule_id: str, category: str, issue_type: str, assigned_to: str, action: str, source: str):
        matches.append({
            "rule_id": rule_id,
            "category": category,
            "issue_type": issue_type,
            "assigned_to": assigned_to,
            "action": action,
            "source": source,
        })

    # 1. Detect return-related incidents
    is_return = any(word in text for word in ("return", "refund", "exchange"))
    no_receipt = bool(
        re.search(
            r"\b(?:without|no|missing|lost)\s+"
            r"(?:(?:a|the|my|valid)\s+)?"
            r"(?:receipt|invoice|bill)\b",
            text,
        )
    )

    if is_return and no_receipt:
        add(
            "RETURN_NO_RECEIPT",
            "Returns",
            "Missing Receipt",
            "Store Manager",
            "Escalate the request. Cashier cannot process it.",
            "returns.md Section 1",
        )

    damaged = any(word in text for word in ("damaged", "defective"))
    online = any(word in text for word in ("online", "delivery", "delivered"))

    if is_return and damaged and not online:
        add(
            "DAMAGED_IN_STORE_RETURN",
            "Returns",
            "Damaged In-Store Return",
            "Store Manager",
            "Inspect the item and obtain manager approval.",
            "returns.md Section 3",
        )

    # 2. Detect shelf/POS pricing discrepancies
    if any(x in text for x in ("shelf", "price tag")) and any(
        x in text for x in ("pos", "scan", "checkout", "billing")
    ):
        add(
            "BILLING_PRICE_MISMATCH",
            "Billing",
            "Price Mismatch",
            "Floor Supervisor",
            "Verify the shelf tag. A cashier cannot independently override the POS price.",
            "billing.md Section 3",
        )

    # 3. Detect receiving shipment discrepancies
    shipment = any(x in text for x in ("shipment", "carton", "asn"))
    discrepancy = any(
        x in text for x in ("missing", "mismatch", "short", "discrepancy", "different", "differs", "differ")
    )

    if shipment and discrepancy:
        add(
            "SHIPMENT_DISCREPANCY",
            "Inventory",
            "Shipment Discrepancy",
            "Receiving Associate; Store Manager approval",
            "Log an ERP discrepancy and obtain the Store Manager's signature before acceptance.",
            "inventory.md Section 1",
        )

    # 4. Never invent an assignment for unknown problems
    if not matches:
        return {
            "category": "Unclassified",
            "issue_type": "Manual Review Required",
            "assigned_to": "Unassigned",
            "actions": ["Review the problem manually."],
            "sources": [],
            "matched_rules": [],
            "requires_review": True,
        }

    # 5. Handle incidents spanning multiple distinct departments/categories
    categories = {m["category"] for m in matches}
    if len(categories) > 1:
        return {
            "category": "Multiple",
            "issue_type": "Multiple Incident Categories",
            "assigned_to": "Unassigned",
            "actions": ["Separate the incidents for review."],
            "sources": list(dict.fromkeys(m["source"] for m in matches)),
            "matched_rules": [m["rule_id"] for m in matches],
            "requires_review": True,
        }

    # 6. Single-category match (supports 1 or more rules within the same category)
    return {
        "category": matches[0]["category"],
        "issue_type": " / ".join(m["issue_type"] for m in matches),
        "assigned_to": "; ".join(dict.fromkeys(m["assigned_to"] for m in matches)),
        "actions": [m["action"] for m in matches],
        "sources": list(dict.fromkeys(m["source"] for m in matches)),
        "matched_rules": [m["rule_id"] for m in matches],
        "requires_review": False,
    }