from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from insightengine.api import app


class APITests(unittest.TestCase):
    def test_health_reports_ok_when_database_responds(self) -> None:
        with patch("insightengine.api.connect") as connect:
            cursor = MagicMock()
            cursor.fetchone.return_value = {"ok": 1}
            connection = MagicMock()
            connection.cursor.return_value.__enter__.return_value = cursor
            connect.return_value.__enter__.return_value = connection

            response = TestClient(app).get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_stats_overview_returns_counts(self) -> None:
        with patch("insightengine.api.connect") as connect:
            cursor = MagicMock()
            cursor.fetchone.side_effect = [
                {"count": 2},
                {"count": 5},
                {"average_words": 12.5},
            ]
            cursor.fetchall.return_value = [
                {"role": "assistant", "count": 3},
                {"role": "user", "count": 2},
            ]
            connection = MagicMock()
            connection.cursor.return_value.__enter__.return_value = cursor
            connect.return_value.__enter__.return_value = connection

            response = TestClient(app).get("/stats/overview")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["conversation_count"], 2)
        self.assertEqual(response.json()["message_count"], 5)
        self.assertEqual(response.json()["role_counts"]["user"], 2)
        self.assertEqual(response.json()["average_user_message_words"], 12.5)

    def test_search_delegates_to_database_analysis(self) -> None:
        with patch("insightengine.api.analyze_db") as analyze_db:
            analyze_db.return_value = {
                "search": {
                    "query": "robotics",
                    "matching_conversations": 1,
                    "total_user_message_hits": 2,
                    "top_matching_conversations": [
                        {"conversation_id": "conv-1", "hit_count": 2}
                    ],
                }
            }

            response = TestClient(app).get("/search", params={"query": "robotics"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["matching_conversations"], 1)
        analyze_db.assert_called_once()


if __name__ == "__main__":
    unittest.main()
