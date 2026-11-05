import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from analytics import get_analytics
from routing import classify_issue


class TestAnalytics(unittest.TestCase):
    def test_empty_analytics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_db = Path(temp_dir) / "test.db"
            with patch.object(database, "DB_PATH", test_db):
                database.init_db()
                stats = get_analytics()
                self.assertEqual(stats["total"], 0)
                self.assertEqual(stats["resolution_rate"], 0.0)
                self.assertTrue(stats["data"].empty)

    def test_populated_analytics_metrics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_db = Path(temp_dir) / "test.db"
            with patch.object(database, "DB_PATH", test_db):
                database.init_db()

                # Create 2 tickets: 1 Billing (Resolved), 1 Unclassified (Open)
                t1 = database.create_ticket(
                    "Shelf price 499 but POS shows 599",
                    classify_issue("Shelf price 499 but POS shows 599"),
                )
                database.update_ticket_status(t1, "Resolved")

                database.create_ticket(
                    "Need breakroom Wi-Fi password",
                    classify_issue("Need breakroom Wi-Fi password"),
                )

                stats = get_analytics()
                self.assertEqual(stats["total"], 2)
                self.assertEqual(stats["open"], 1)
                self.assertEqual(stats["resolved"], 1)
                self.assertEqual(stats["manual_review"], 1)
                self.assertEqual(stats["resolution_rate"], 50.0)


if __name__ == "__main__":
    unittest.main()