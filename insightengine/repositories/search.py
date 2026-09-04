from __future__ import annotations

from typing import Any

from insightengine.db import connect


def search_conversations(database_url: str, query: str, limit: int = 10) -> dict[str, Any]:
    pattern = f"%{query}%"
    with connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT conversation_id, count(*) AS hit_count
                FROM messages
                WHERE role = 'user' AND text ILIKE %s
                GROUP BY conversation_id
                ORDER BY hit_count DESC, conversation_id
                LIMIT %s
                """,
                (pattern, limit),
            )
            top_matches = cur.fetchall()
            cur.execute(
                """
                SELECT count(DISTINCT conversation_id) AS conversations,
                       count(*) AS messages
                FROM messages
                WHERE role = 'user' AND text ILIKE %s
                """,
                (pattern,),
            )
            counts = cur.fetchone()

    return {
        "query": query,
        "matching_conversations": counts["conversations"],
        "total_user_message_hits": counts["messages"],
        "top_matching_conversations": [
            {
                "conversation_id": row["conversation_id"],
                "hit_count": row["hit_count"],
            }
            for row in top_matches
        ],
    }


def summarize_topic(database_url: str, query: str, limit: int = 10) -> dict[str, Any]:
    pattern = f"%{query}%"
    with connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    mf.month,
                    count(*) AS user_message_hits,
                    count(DISTINCT mf.conversation_id) AS conversations
                FROM message_features AS mf
                JOIN messages AS m
                    ON m.conversation_id = mf.conversation_id
                   AND m.message_id = mf.message_id
                WHERE mf.role = 'user'
                  AND mf.month IS NOT NULL
                  AND m.text ILIKE %s
                GROUP BY mf.month
                ORDER BY mf.month
                """,
                (pattern,),
            )
            monthly = cur.fetchall()
            cur.execute(
                """
                SELECT mf.question_type, count(*) AS count
                FROM message_features AS mf
                JOIN messages AS m
                    ON m.conversation_id = mf.conversation_id
                   AND m.message_id = mf.message_id
                WHERE mf.role = 'user'
                  AND m.text ILIKE %s
                GROUP BY mf.question_type
                ORDER BY count DESC, mf.question_type
                """,
                (pattern,),
            )
            question_types = cur.fetchall()

    search = search_conversations(database_url, query, limit=limit)
    return {
        **search,
        "monthly_hits": [
            {
                "month": row["month"],
                "user_message_hits": row["user_message_hits"],
                "conversations": row["conversations"],
            }
            for row in monthly
        ],
        "question_type_counts": {
            row["question_type"]: row["count"]
            for row in question_types
        },
    }
