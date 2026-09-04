from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.analyze_messages import analyze_messages
    from scripts.build_message_features import build_message_features
except ModuleNotFoundError:  # pragma: no cover - supports direct script execution
    from analyze_messages import analyze_messages
    from build_message_features import build_message_features


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a local Markdown profile report from processed data."
    )
    parser.add_argument(
        "--messages",
        type=Path,
        default=Path("data/processed/messages.jsonl"),
        help="Path to messages.jsonl from import_chatgpt_export.py.",
    )
    parser.add_argument(
        "--features",
        type=Path,
        default=Path("data/processed/message_features.jsonl"),
        help="Path to write or read message feature JSONL.",
    )
    parser.add_argument(
        "--feature-summary",
        type=Path,
        default=Path("data/processed/feature_summary.json"),
        help="Path to write or read feature summary JSON.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/processed/profile_report.md"),
        help="Path for the generated Markdown report.",
    )
    args = parser.parse_args()

    analysis = analyze_messages(args.messages, top_terms=25)
    feature_summary = build_message_features(
        args.messages,
        args.features,
        args.feature_summary,
    )
    report = render_report(analysis, feature_summary)
    args.out.write_text(report, encoding="utf-8")
    print(json.dumps({"report_path": str(args.out)}, indent=2))


def render_report(analysis: dict[str, Any], feature_summary: dict[str, Any]) -> str:
    lines = [
        "# Cognitive Mirror Local Profile",
        "",
        "This local report summarizes deterministic signals from the processed",
        "conversation export. It describes behavioral and linguistic patterns in",
        "the data; it does not make psychological or clinical claims.",
        "",
        "## Dataset",
        "",
        f"- Messages: {analysis['message_count']:,}",
        f"- User messages: {analysis['user_message_count']:,}",
        f"- Assistant messages: {analysis['assistant_message_count']:,}",
        f"- Average user message length: {analysis['average_user_message_words']} words",
        "",
        "## Busiest Months",
        "",
        "| Month | Messages |",
        "| --- | ---: |",
    ]

    for month, count in analysis["busiest_months"].items():
        lines.append(f"| {month} | {count:,} |")

    lines.extend(
        [
            "",
            "## User Message Length Over Time",
            "",
            "| Month | Average words |",
            "| --- | ---: |",
        ]
    )
    for month, average_words in analysis["average_user_message_words_by_month"].items():
        lines.append(f"| {month} | {average_words} |")

    lines.extend(
        [
            "",
            "## Heuristic Question Types",
            "",
            "| Type | User messages |",
            "| --- | ---: |",
        ]
    )
    for question_type, count in feature_summary["user_question_type_counts"].items():
        lines.append(f"| {question_type} | {count:,} |")

    lines.extend(
        [
            "",
            "## Dominant Question Type By Month",
            "",
            "| Month | Dominant type |",
            "| --- | --- |",
        ]
    )
    for month, question_type in feature_summary["dominant_question_type_by_month"].items():
        lines.append(f"| {month} | {question_type} |")

    lines.extend(
        [
            "",
            "## Uncertainty Markers By Month",
            "",
            "| Month | Marker count |",
            "| --- | ---: |",
        ]
    )
    for month, count in feature_summary["uncertainty_markers_by_month"].items():
        lines.append(f"| {month} | {count:,} |")

    lines.extend(
        [
            "",
            "## Top User Terms",
            "",
            "| Term | Count |",
            "| --- | ---: |",
        ]
    )
    for term, count in analysis["top_user_terms"]:
        lines.append(f"| {term} | {count:,} |")

    lines.extend(
        [
            "",
            "## Next ML Steps",
            "",
            "1. Replace heuristic question types with a labeled dataset and classifier.",
            "2. Add embeddings for user messages and conversation-level summaries.",
            "3. Run dimensionality reduction with UMAP or PCA.",
            "4. Compare HDBSCAN and K-Means for topic and thinking-mode clusters.",
            "5. Evaluate cluster stability, retrieval quality, and answer faithfulness.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
