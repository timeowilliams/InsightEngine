from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

try:
    from scripts.analyze_messages import month_from_timestamp, read_jsonl
except ModuleNotFoundError:  # pragma: no cover - supports direct script execution
    from analyze_messages import month_from_timestamp, read_jsonl


QUESTION_TYPE_PATTERNS: dict[str, tuple[str, ...]] = {
    "debugging": (
        "error",
        "traceback",
        "exception",
        "bug",
        "broken",
        "failing",
        "fails",
        "fix",
        "debug",
        "stack trace",
    ),
    "planning": (
        "plan",
        "roadmap",
        "next step",
        "timeline",
        "milestone",
        "strategy",
        "approach",
        "schedule",
    ),
    "reassurance_seeking": (
        "are you sure",
        "does this make sense",
        "am i right",
        "is this okay",
        "should i be worried",
        "is that normal",
    ),
    "reflective": (
        "why do i",
        "how have i",
        "what does it say",
        "what does this mean",
        "i feel",
        "i think i",
        "my thinking",
    ),
    "argumentative": (
        "i disagree",
        "push back",
        "counterargument",
        "isn't it",
        "but wouldn't",
        "that seems wrong",
    ),
    "exploratory": (
        "what if",
        "could we",
        "how might",
        "explore",
        "brainstorm",
        "compare",
        "tradeoff",
    ),
    "factual": (
        "what is",
        "when did",
        "who is",
        "define",
        "explain",
        "summarize",
        "list",
    ),
}

UNCERTAINTY_MARKERS = (
    "maybe",
    "i think",
    "i guess",
    "not sure",
    "unsure",
    "possibly",
    "probably",
    "are you sure",
    "could be",
)

REASONING_MARKERS = (
    "because",
    "therefore",
    "so that",
    "tradeoff",
    "assumption",
    "evidence",
    "evaluate",
    "reason",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract deterministic linguistic features from normalized messages."
    )
    parser.add_argument(
        "--messages",
        type=Path,
        default=Path("data/processed/messages.jsonl"),
        help="Path to messages.jsonl from import_chatgpt_export.py.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/processed/message_features.jsonl"),
        help="Path for non-text message feature JSONL output.",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("data/processed/feature_summary.json"),
        help="Path for aggregate feature summary JSON output.",
    )
    args = parser.parse_args()

    summary = build_message_features(args.messages, args.out, args.summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def build_message_features(
    messages_path: Path,
    out_path: Path,
    summary_path: Path,
) -> dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    feature_count = 0
    role_counts: Counter[str] = Counter()
    question_type_counts: Counter[str] = Counter()
    uncertainty_by_month: defaultdict[str, int] = defaultdict(int)
    user_messages_by_month: Counter[str] = Counter()
    user_words_by_month: defaultdict[str, int] = defaultdict(int)
    question_types_by_month: defaultdict[str, Counter[str]] = defaultdict(Counter)

    with out_path.open("w", encoding="utf-8", newline="\n") as out_file:
        for message in read_jsonl(messages_path):
            feature = extract_message_features(message)
            feature_count += 1
            out_file.write(json.dumps(feature, ensure_ascii=False) + "\n")

            role = str(feature.get("role") or "unknown")
            role_counts[role] += 1
            if role != "user":
                continue

            month = feature.get("month")
            question_type = str(feature["question_type"])
            question_type_counts[question_type] += 1
            if isinstance(month, str):
                user_messages_by_month[month] += 1
                user_words_by_month[month] += int(feature["word_count"])
                uncertainty_by_month[month] += int(feature["uncertainty_marker_count"])
                question_types_by_month[month][question_type] += 1

    summary = {
        "messages_path": str(messages_path),
        "features_path": str(out_path),
        "feature_count": feature_count,
        "role_counts": dict(role_counts.most_common()),
        "user_question_type_counts": dict(question_type_counts.most_common()),
        "average_user_words_by_month": {
            month: round(user_words_by_month[month] / count, 2)
            for month, count in sorted(user_messages_by_month.items())
        },
        "uncertainty_markers_by_month": dict(sorted(uncertainty_by_month.items())),
        "dominant_question_type_by_month": {
            month: monthly_counts.most_common(1)[0][0]
            for month, monthly_counts in sorted(question_types_by_month.items())
            if monthly_counts
        },
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summary


def extract_message_features(message: dict[str, Any]) -> dict[str, Any]:
    text = str(message.get("text") or "")
    lower_text = text.lower()
    role = message.get("role")
    timestamp = message.get("create_time")
    question_type = classify_question_type(lower_text) if role == "user" else "not_user"
    sentence_count = count_sentences(text)
    word_count = int(message.get("word_count") or 0)

    return {
        "conversation_id": message.get("conversation_id"),
        "message_id": message.get("message_id"),
        "parent_id": message.get("parent_id"),
        "role": role,
        "create_time": timestamp,
        "month": month_from_timestamp(timestamp),
        "content_type": message.get("content_type"),
        "text_sha256": message.get("text_sha256"),
        "word_count": word_count,
        "char_count": int(message.get("char_count") or 0),
        "sentence_count": sentence_count,
        "average_sentence_words": round(word_count / sentence_count, 2)
        if sentence_count
        else 0,
        "question_mark_count": text.count("?"),
        "has_question_mark": "?" in text,
        "uncertainty_marker_count": count_markers(lower_text, UNCERTAINTY_MARKERS),
        "reasoning_marker_count": count_markers(lower_text, REASONING_MARKERS),
        "code_block_count": lower_text.count("```"),
        "url_count": len(re.findall(r"https?://", lower_text)),
        "question_type": question_type,
    }


def classify_question_type(lower_text: str) -> str:
    scores = {
        question_type: count_markers(lower_text, patterns)
        for question_type, patterns in QUESTION_TYPE_PATTERNS.items()
    }
    best_type, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score > 0:
        return best_type
    if "?" in lower_text:
        return "general_question"
    return "statement_or_instruction"


def count_markers(text: str, markers: Iterable[str]) -> int:
    return sum(1 for marker in markers if marker in text)


def count_sentences(text: str) -> int:
    sentences = [part for part in re.split(r"[.!?]+", text) if part.strip()]
    return len(sentences)


if __name__ == "__main__":
    main()
