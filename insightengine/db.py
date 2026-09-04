from __future__ import annotations

import os


DEFAULT_DATABASE_URL = (
    "postgresql://insightengine:insightengine@localhost:5432/insightengine"
)


def connect(database_url: str):
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: install with `python -m pip install -r requirements.txt`."
        ) from exc

    return psycopg.connect(database_url, row_factory=dict_row)


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def check_database(url: str | None = None) -> dict[str, str]:
    active_url = url or database_url()
    with connect(active_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS ok")
            cur.fetchone()

    return {
        "status": "ok",
        "database_url": redact_url(active_url),
    }


def redact_url(database_url: str) -> str:
    if "@" not in database_url or "://" not in database_url:
        return database_url
    prefix, rest = database_url.split("://", 1)
    _, host = rest.rsplit("@", 1)
    return f"{prefix}://***:***@{host}"
