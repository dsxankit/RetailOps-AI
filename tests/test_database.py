import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from routing import classify_issue


class TestTicketDatabase(unittest.TestCase):
    def test_create_and_update_ticket(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_db = Path(temp_dir) / "test.db"
            with patch.object(database, "DB_PATH", test_db):
                database.init_db()

                description = "Shelf price differs from POS price"
                result = classify_issue(description)

                ticket_id = database.create_ticket(description, result)
                ticket = database.get_ticket(ticket_id)

                self.assertIsNotNone(ticket)
                self.assertEqual(ticket["status"], "Open")
                self.assertEqual(ticket["category"], "Billing")
                self.assertEqual(ticket["assigned_to"], "Floor Supervisor")

                # Verify list_tickets returns the created record
                tickets = database.list_tickets()
                self.assertEqual(len(tickets), 1)
                self.assertEqual(tickets[0]["id"], ticket_id)

                # Update Open -> In Progress -> Resolved
                self.assertTrue(database.update_ticket_status(ticket_id, "In Progress"))
                self.assertEqual(database.get_ticket(ticket_id)["status"], "In Progress")

                self.assertTrue(database.update_ticket_status(ticket_id, "Resolved"))
                self.assertEqual(database.get_ticket(ticket_id)["status"], "Resolved")

    def test_unclassified_issue_saved_for_manual_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_db = Path(temp_dir) / "test.db"
            with patch.object(database, "DB_PATH", test_db):
                database.init_db()
                description = "Employee wants the Wi-Fi password."
                result = classify_issue(description)

                ticket_id = database.create_ticket(description, result)
                ticket = database.get_ticket(ticket_id)

                self.assertEqual(ticket["category"], "Unclassified")
                self.assertEqual(ticket["assigned_to"], "Unassigned")
                self.assertEqual(ticket["requires_review"], 1)

    def test_invalid_status_raises_value_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_db = Path(temp_dir) / "test.db"
            with patch.object(database, "DB_PATH", test_db):
                database.init_db()
                with self.assertRaises(ValueError):
                    database.update_ticket_status(1, "Closed")

    def test_empty_description_raises_value_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_db = Path(temp_dir) / "test.db"
            with patch.object(database, "DB_PATH", test_db):
                database.init_db()
                result = classify_issue("Shelf price 499 but POS shows 599.")
                with self.assertRaises(ValueError):
                    database.create_ticket("   ", result)


if __name__ == "__main__":
    unittest.main()