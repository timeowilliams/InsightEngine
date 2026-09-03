from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from chatgpt_export import conversation_entry_names, iter_conversations, iter_messages


STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "because",
    "been",
    "before",
    "being",
    "could",
    "from",
    "have",
    "into",
    "just",
    "like",
    "more",
    "some",
    "than",
    "that",
    "their",
    "there",
    "these",
    "they",
    "this",
    "with",
    "would",
    "your",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile a ChatGPT export ZIP.")
    parser.add_argument("zip_path", type=Path, help="Path to the ChatGPT export ZIP.")
    parser.add_argument(
        "--include-terms",
        action="store_true",
        help="Include top user-message terms in the printed summary.",
    )
    parser.add_argument(
        "--include-titles",
        action="store_true",
        help="Include conversation titles in the longest-conversations list.",
    )
    args = parser.parse_args()

    profile = build_profile(
        args.zip_path,
        include_terms=args.include_terms,
        include_titles=args.include_titles,
    )
    print(json.dumps(profile, indent=2, ensure_ascii=False))


def build_profile(
    zip_path: Path,
    include_terms: bool = False,
    include_titles: bool = False,
) -> dict[str, object]:
    conversation_count = 0
    message_count = 0
    user_message_count = 0
    assistant_message_count = 0
    nonempty_message_count = 0
    total_user_words = 0
    months: Counter[str] = Counter()
    roles: Counter[str] = Counter()
    user_terms: Counter[str] = Counter()
    longest_conversations: list[dict[str, object]] = []

    for record in iter_conversations(zip_path):
        conversation_count += 1
        conversation_messages = list(iter_messages(record))
        conversation_words = sum(message.word_count for message in conversation_messages)
        longest_conversations.append(
            {
                "conversation_id": record.conversation.get("conversation_id")
                or record.conversation.get("id"),
                "message_count": len(conversation_messages),
                "total_words": conversation_words,
            }
        )
        if include_titles:
            longest_conversations[-1]["title"] = record.conversation.get("title")

        for message in conversation_messages:
            message_count += 1
            if message.text:
                nonempty_message_count += 1
            if message.role:
                roles[message.role] += 1
            if message.create_time:
                months[message.create_time[:7]] += 1
            if message.role == "user":
                user_message_count += 1
                total_user_words += message.word_count
                if include_terms:
                    user_terms.update(tokenize(message.text))
            elif message.role == "assistant":
                assistant_message_count += 1

    profile: dict[str, object] = {
        "zip_path": str(zip_path),
        "conversation_files": conversation_entry_names(zip_path),
        "conversation_count": conversation_count,
        "message_count": message_count,
        "nonempty_message_count": nonempty_message_count,
        "user_message_count": user_message_count,
        "assistant_message_count": assistant_message_count,
        "average_user_message_words": round(
            total_user_words / user_message_count, 2
        )
        if user_message_count
        else 0,
        "roles": dict(roles.most_common()),
        "messages_by_month": dict(sorted(months.items())),
        "longest_conversations": sorted(
            longest_conversations,
            key=lambda item: int(item["total_words"]),
            reverse=True,
        )[:10],
    }

    if include_terms:
        profile["top_user_terms"] = user_terms.most_common(50)

    return profile


def tokenize(text: str) -> list[str]:
    import re

    terms = []
    for token in re.findall(r"[A-Za-z][A-Za-z0-9']{2,}", text.lower()):
        if token not in STOPWORDS:
            terms.append(token)
    return terms


if __name__ == "__main__":
    main()
