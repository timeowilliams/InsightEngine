from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from insightengine.db import check_database, database_url
from insightengine.repositories.search import search_conversations
from insightengine.repositories.stats import (
    get_monthly_trends,
    get_overview,
    get_question_types,
)


DATABASE_URL = database_url()
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(
    title="InsightEngine API",
    description="Backend API for local Cognitive Mirror conversation analysis.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))


@app.get("/health")
def health() -> dict[str, Any]:
    try:
        return check_database(DATABASE_URL)
    except Exception as exc:  # pragma: no cover - exercised by integration smoke checks
        raise HTTPException(status_code=503, detail="database unavailable") from exc


@app.get("/stats/overview")
def stats_overview() -> dict[str, Any]:
    return get_overview(DATABASE_URL)


@app.get("/stats/monthly-trends")
def monthly_trends() -> dict[str, Any]:
    return get_monthly_trends(DATABASE_URL)


@app.get("/stats/question-types")
def question_types() -> dict[str, Any]:
    return get_question_types(DATABASE_URL)


@app.get("/search")
def search(query: str = Query(min_length=1, max_length=200)) -> dict[str, Any]:
    return search_conversations(DATABASE_URL, query)
