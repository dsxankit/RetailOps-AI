import unittest

from routing import classify_issue


class TestIssueClassification(unittest.TestCase):
    def test_return_without_receipt(self):
        result = classify_issue("Customer wants to return an item without a receipt.")
        self.assertEqual(result["category"], "Returns")
        self.assertEqual(result["issue_type"], "Missing Receipt")
        self.assertEqual(result["assigned_to"], "Store Manager")
        self.assertEqual(result["matched_rules"], ["RETURN_NO_RECEIPT"])
        self.assertFalse(result["requires_review"])

    def test_damaged_in_store_return(self):
        result = classify_issue("Customer wants to return a damaged product.")
        self.assertEqual(result["category"], "Returns")
        self.assertEqual(result["issue_type"], "Damaged In-Store Return")
        self.assertEqual(result["assigned_to"], "Store Manager")
        self.assertEqual(result["matched_rules"], ["DAMAGED_IN_STORE_RETURN"])
        self.assertFalse(result["requires_review"])

    def test_damaged_return_without_receipt_triggers_both_rules(self):
        result = classify_issue("Damaged return without receipt.")
        self.assertEqual(result["category"], "Returns")
        self.assertEqual(result["issue_type"], "Missing Receipt / Damaged In-Store Return")
        self.assertEqual(result["assigned_to"], "Store Manager")
        self.assertEqual(
            result["matched_rules"],
            ["RETURN_NO_RECEIPT", "DAMAGED_IN_STORE_RETURN"],
        )
        self.assertEqual(len(result["actions"]), 2)
        self.assertFalse(result["requires_review"])

    def test_billing_price_mismatch(self):
        result = classify_issue("Shelf price 499 but POS shows 599.")
        self.assertEqual(result["category"], "Billing")
        self.assertEqual(result["issue_type"], "Price Mismatch")
        self.assertEqual(result["assigned_to"], "Floor Supervisor")
        self.assertEqual(result["matched_rules"], ["BILLING_PRICE_MISMATCH"])
        self.assertFalse(result["requires_review"])

    def test_inventory_shipment_discrepancy(self):
        result = classify_issue("ASN carton count differs from received shipment.")
        self.assertEqual(result["category"], "Inventory")
        self.assertEqual(result["issue_type"], "Shipment Discrepancy")
        self.assertEqual(result["assigned_to"], "Receiving Associate; Store Manager approval")
        self.assertEqual(result["matched_rules"], ["SHIPMENT_DISCREPancy".upper()])
        self.assertFalse(result["requires_review"])

    def test_standard_return_with_receipt_not_escalated(self):
        result = classify_issue("Customer has a receipt and wants a standard return.")
        self.assertEqual(result["category"], "Unclassified")
        self.assertTrue(result["requires_review"])
        self.assertEqual(result["matched_rules"], [])

    def test_unclassified_wifi_password(self):
        result = classify_issue("Employee wants the Wi-Fi password.")
        self.assertEqual(result["category"], "Unclassified")
        self.assertEqual(result["issue_type"], "Manual Review Required")
        self.assertEqual(result["assigned_to"], "Unassigned")
        self.assertTrue(result["requires_review"])

    def test_empty_description_raises_value_error(self):
        with self.assertRaises(ValueError):
            classify_issue("   ")


if __name__ == "__main__":
    unittest.main()