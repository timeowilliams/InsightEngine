from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from insightengine.db import connect
from scripts.profile_export import STOPWORDS, tokenize


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


def get_top_terms_by_month(
    database_url: str,
    months: int = 12,
    limit: int = 8,
) -> dict[str, Any]:
    with connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT month
                FROM message_features
                WHERE role = 'user' AND month IS NOT NULL
                GROUP BY month
                ORDER BY month DESC
                LIMIT %s
                """,
                (months,),
            )
            selected_months = [row["month"] for row in cur.fetchall()]
            if not selected_months:
                return {"months": []}

            cur.execute(
                """
                SELECT mf.month, m.text
                FROM message_features AS mf
                JOIN messages AS m
                    ON m.conversation_id = mf.conversation_id
                   AND m.message_id = mf.message_id
                WHERE mf.role = 'user' AND mf.month = ANY(%s)
                ORDER BY mf.month
                """,
                (selected_months,),
            )
            rows = cur.fetchall()

    terms_by_month: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        terms_by_month[row["month"]].update(
            token for token in tokenize(row["text"]) if token not in STOPWORDS
        )

    return {
        "months": [
            {
                "month": month,
                "top_terms": [
                    {"term": term, "count": count}
                    for term, count in terms_by_month[month].most_common(limit)
                ],
            }
            for month in sorted(selected_months)
        ]
    }


def get_workflow_trends(database_url: str) -> dict[str, Any]:
    with connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    month,
                    count(*) AS user_messages,
                    sum(CASE WHEN question_type = 'debugging' THEN 1 ELSE 0 END)
                        AS debugging_messages,
                    sum(CASE WHEN question_type = 'planning' THEN 1 ELSE 0 END)
                        AS planning_messages,
                    sum(CASE WHEN question_type = 'reflective' THEN 1 ELSE 0 END)
                        AS reflective_messages,
                    sum(CASE WHEN code_block_count > 0 THEN 1 ELSE 0 END)
                        AS code_block_messages,
                    sum(CASE WHEN url_count > 0 THEN 1 ELSE 0 END)
                        AS url_messages
                FROM message_features
                WHERE role = 'user' AND month IS NOT NULL
                GROUP BY month
                ORDER BY month
                """
            )
            rows = cur.fetchall()

    return {
        "workflow_trends": [
            {
                "month": row["month"],
                "user_messages": row["user_messages"],
                "debugging_messages": row["debugging_messages"],
                "planning_messages": row["planning_messages"],
                "reflective_messages": row["reflective_messages"],
                "code_block_messages": row["code_block_messages"],
                "url_messages": row["url_messages"],
            }
            for row in rows
        ]
    }


def get_code_signals(database_url: str, limit: int = 10) -> dict[str, Any]:
    with connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    count(*) FILTER (WHERE mf.code_block_count > 0) AS code_block_messages,
                    count(*) FILTER (WHERE mf.question_type = 'debugging')
                        AS debugging_messages,
                    count(*) FILTER (WHERE lower(m.text) LIKE %s)
                        AS error_mentions,
                    count(DISTINCT mf.conversation_id) FILTER (
                        WHERE mf.code_block_count > 0 OR mf.question_type = 'debugging'
                    ) AS technical_conversations
                FROM message_features AS mf
                JOIN messages AS m USING (conversation_id, message_id)
                WHERE mf.role = 'user'
                """,
                ("%error%",),
            )
            totals = cur.fetchone()
            cur.execute(
                """
                SELECT
                    mf.conversation_id,
                    count(*) FILTER (WHERE mf.code_block_count > 0) AS code_block_messages,
                    count(*) FILTER (WHERE mf.question_type = 'debugging')
                        AS debugging_messages,
                    count(*) FILTER (WHERE lower(m.text) LIKE %s)
                        AS error_mentions,
                    count(*) AS user_messages
                FROM message_features AS mf
                JOIN messages AS m USING (conversation_id, message_id)
                WHERE mf.role = 'user'
                GROUP BY mf.conversation_id
                HAVING count(*) FILTER (
                    WHERE mf.code_block_count > 0
                       OR mf.question_type = 'debugging'
                       OR lower(m.text) LIKE %s
                ) > 0
                ORDER BY
                    (
                        count(*) FILTER (WHERE mf.code_block_count > 0)
                        + count(*) FILTER (WHERE mf.question_type = 'debugging')
                        + count(*) FILTER (WHERE lower(m.text) LIKE %s)
                    ) DESC,
                    mf.conversation_id
                LIMIT %s
                """,
                ("%error%", "%error%", "%error%", limit),
            )
            rows = cur.fetchall()

    return {
        "totals": {
            "code_block_messages": totals["code_block_messages"],
            "debugging_messages": totals["debugging_messages"],
            "error_mentions": totals["error_mentions"],
            "technical_conversations": totals["technical_conversations"],
        },
        "top_conversations": [
            {
                "conversation_id": row["conversation_id"],
                "user_messages": row["user_messages"],
                "code_block_messages": row["code_block_messages"],
                "debugging_messages": row["debugging_messages"],
                "error_mentions": row["error_mentions"],
            }
            for row in rows
        ],
    }


def get_yearly_length(database_url: str) -> dict[str, Any]:
    with connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    left(month, 4) AS year,
                    count(*) AS user_messages,
                    round(avg(word_count)::numeric, 2) AS average_words,
                    percentile_cont(0.5) WITHIN GROUP (ORDER BY word_count)
                        AS median_words,
                    max(word_count) AS max_words
                FROM message_features
                WHERE role = 'user' AND month IS NOT NULL
                GROUP BY year
                ORDER BY year
                """
            )
            rows = cur.fetchall()

    return {
        "yearly_length": [
            {
                "year": row["year"],
                "user_messages": row["user_messages"],
                "average_words": float(row["average_words"]),
                "median_words": float(row["median_words"] or 0),
                "max_words": row["max_words"],
            }
            for row in rows
        ]
    }
