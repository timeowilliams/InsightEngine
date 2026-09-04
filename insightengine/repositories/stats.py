from __future__ import annotations

from typing import Any

from insightengine.db import connect


def get_overview(database_url: str) -> dict[str, Any]:
    with connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) AS count FROM conversations")
            conversation_count = cur.fetchone()["count"]
            cur.execute("SELECT count(*) AS count FROM messages")
            message_count = cur.fetchone()["count"]
            cur.execute(
                """
                SELECT role, count(*) AS count
                FROM messages
                GROUP BY role
                ORDER BY count DESC, role
                """
            )
            role_counts = {
                row["role"] or "unknown": row["count"]
                for row in cur.fetchall()
            }
            cur.execute(
                """
                SELECT round(avg(word_count)::numeric, 2) AS average_words
                FROM message_features
                WHERE role = 'user'
                """
            )
            average_words = cur.fetchone()["average_words"]

    return {
        "conversation_count": conversation_count,
        "message_count": message_count,
        "role_counts": role_counts,
        "average_user_message_words": float(average_words or 0),
    }


def get_monthly_trends(database_url: str) -> dict[str, Any]:
    with connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    month,
                    count(*) AS user_messages,
                    round(avg(word_count)::numeric, 2) AS average_words,
                    round(
                        (sum(uncertainty_marker_count)::numeric
                        / nullif(sum(word_count), 0)) * 1000,
                        2
                    ) AS uncertainty_markers_per_1000_words
                FROM message_features
                WHERE role = 'user' AND month IS NOT NULL
                GROUP BY month
                ORDER BY month
                """
            )
            rows = cur.fetchall()

    return {
        "monthly_user_trends": [
            {
                "month": row["month"],
                "user_messages": row["user_messages"],
                "average_words": float(row["average_words"]),
                "uncertainty_markers_per_1000_words": float(
                    row["uncertainty_markers_per_1000_words"] or 0
                ),
            }
            for row in rows
        ]
    }


def get_question_types(database_url: str) -> dict[str, Any]:
    with connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT question_type, count(*) AS count
                FROM message_features
                WHERE role = 'user'
                GROUP BY question_type
                ORDER BY count DESC, question_type
                """
            )
            rows = cur.fetchall()

    return {
        "question_type_counts": {
            row["question_type"]: row["count"]
            for row in rows
        }
    }
