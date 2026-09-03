from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from collections.abc import Iterator
from typing import Any

from profile_export import STOPWORDS, tokenize


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run deterministic local analyses over normalized messages."
    )
    parser.add_argument(
        "--messages",
        type=Path,
        default=Path("data/processed/messages.jsonl"),
        help="Path to messages.jsonl from import_chatgpt_export.py.",
    )
    parser.add_argument(
        "--search",
        help="Optional case-insensitive keyword or phrase to search in user messages.",
    )
    parser.add_argument(
        "--top-terms",
        type=int,
        default=25,
        help="Number of top user-message terms to include.",
    )
    args = parser.parse_args()

    result = analyze_messages(args.messages, search=args.search, top_terms=args.top_terms)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def analyze_messages(
    messages_path: Path,
    search: str | None = None,
    top_terms: int = 25,
) -> dict[str, Any]:
    message_count = 0
    user_message_count = 0
    assistant_message_count = 0
    user_words_total = 0
    terms: Counter[str] = Counter()
    messages_by_month: Counter[str] = Counter()
    user_words_by_month: defaultdict[str, int] = defaultdict(int)
    user_messages_by_month: Counter[str] = Counter()
    search_hits: Counter[str] = Counter()
    search_pattern = re.compile(re.escape(search), re.IGNORECASE) if search else None

    for message in read_jsonl(messages_path):
        message_count += 1
        role = message.get("role")
        month = month_from_timestamp(message.get("create_time"))
        if month:
            messages_by_month[month] += 1

        if role == "assistant":
            assistant_message_count += 1
            continue

        if role != "user":
            continue

        user_message_count += 1
        text = str(message.get("text") or "")
        word_count = int(message.get("word_count") or 0)
        user_words_total += word_count
        if month:
            user_words_by_month[month] += word_count
            user_messages_by_month[month] += 1
        terms.update(token for token in tokenize(text) if token not in STOPWORDS)

        if search_pattern and search_pattern.search(text):
            search_hits[str(message.get("conversation_id"))] += 1

    average_words_by_month = {
        month: round(user_words_by_month[month] / count, 2)
        for month, count in sorted(user_messages_by_month.items())
    }

    result: dict[str, Any] = {
        "messages_path": str(messages_path),
        "message_count": message_count,
        "user_message_count": user_message_count,
        "assistant_message_count": assistant_message_count,
        "average_user_message_words": round(user_words_total / user_message_count, 2)
        if user_message_count
        else 0,
        "busiest_months": dict(messages_by_month.most_common(10)),
        "average_user_message_words_by_month": average_words_by_month,
        "top_user_terms": terms.most_common(top_terms),
    }

    if search_pattern:
        result["search"] = {
            "query": search,
            "matching_conversations": len(search_hits),
            "total_user_message_hits": sum(search_hits.values()),
            "top_matching_conversations": [
                {"conversation_id": conversation_id, "hit_count": hit_count}
                for conversation_id, hit_count in search_hits.most_common(10)
            ],
        }

    return result


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            if line.strip():
                yield json.loads(line)


def month_from_timestamp(timestamp: Any) -> str | None:
    if not isinstance(timestamp, str) or len(timestamp) < 7:
        return None
    return timestamp[:7]


if __name__ == "__main__":
    main()
