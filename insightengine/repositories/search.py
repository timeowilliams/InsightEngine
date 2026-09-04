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
