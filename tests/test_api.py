from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from insightengine.api import app


class APITests(unittest.TestCase):
    def test_health_reports_ok_when_database_responds(self) -> None:
        with patch("insightengine.api.check_database") as check_database:
            check_database.return_value = {
                "status": "ok",
                "database_url": "postgresql://***:***@postgres:5432/insightengine",
            }

            response = TestClient(app).get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_stats_overview_returns_counts(self) -> None:
        with patch("insightengine.api.get_overview") as get_overview:
            get_overview.return_value = {
                "conversation_count": 2,
                "message_count": 5,
                "role_counts": {"assistant": 3, "user": 2},
                "average_user_message_words": 12.5,
            }

            response = TestClient(app).get("/stats/overview")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["conversation_count"], 2)
        self.assertEqual(response.json()["message_count"], 5)
        self.assertEqual(response.json()["role_counts"]["user"], 2)
        self.assertEqual(response.json()["average_user_message_words"], 12.5)

    def test_search_delegates_to_database_analysis(self) -> None:
        with patch("insightengine.api.search_conversations") as search_conversations:
            search_conversations.return_value = {
                "query": "robotics",
                "matching_conversations": 1,
                "total_user_message_hits": 2,
                "top_matching_conversations": [
                    {"conversation_id": "conv-1", "hit_count": 2}
                ],
            }

            response = TestClient(app).get("/search", params={"query": "robotics"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["matching_conversations"], 1)
        search_conversations.assert_called_once()

    def test_dashboard_serves_html(self) -> None:
        response = TestClient(app).get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Cognitive Mirror Dashboard", response.text)


if __name__ == "__main__":
    unittest.main()
