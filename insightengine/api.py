from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query

from scripts.postgres_store import DEFAULT_DATABASE_URL, analyze_db, connect, redact_url


DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

app = FastAPI(
    title="InsightEngine API",
    description="Backend API for local Cognitive Mirror conversation analysis.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, Any]:
    try:
        with connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 AS ok")
                cur.fetchone()
    except Exception as exc:  # pragma: no cover - exercised by integration smoke checks
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    return {
        "status": "ok",
        "database_url": redact_url(DATABASE_URL),
    }


@app.get("/stats/overview")
def stats_overview() -> dict[str, Any]:
    with connect(DATABASE_URL) as conn:
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


@app.get("/stats/monthly-trends")
def monthly_trends() -> dict[str, Any]:
    analysis = analyze_db(DATABASE_URL, top_terms=0)
    return {"monthly_user_trends": analysis["monthly_user_trends"]}


@app.get("/stats/question-types")
def question_types() -> dict[str, Any]:
    analysis = analyze_db(DATABASE_URL, top_terms=0)
    return {"question_type_counts": analysis["question_type_counts"]}


@app.get("/search")
def search(query: str = Query(min_length=1, max_length=200)) -> dict[str, Any]:
    analysis = analyze_db(DATABASE_URL, search=query, top_terms=0)
    return analysis["search"]
