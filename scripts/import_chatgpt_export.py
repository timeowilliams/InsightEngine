from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.chatgpt_export import conversation_summary, iter_conversations, iter_messages
    from scripts.profile_export import build_profile
except ModuleNotFoundError:  # pragma: no cover - supports direct script execution
    from chatgpt_export import conversation_summary, iter_conversations, iter_messages
    from profile_export import build_profile


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize a ChatGPT export ZIP into local JSONL files."
    )
    parser.add_argument("zip_path", type=Path, help="Path to the ChatGPT export ZIP.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/processed"),
        help="Directory for normalized output files.",
    )
    args = parser.parse_args()

    output = import_export(args.zip_path, args.out_dir)
    print(json.dumps(output, indent=2, ensure_ascii=False))


def import_export(zip_path: Path, out_dir: Path) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    conversations_path = out_dir / "conversations.jsonl"
    messages_path = out_dir / "messages.jsonl"
    summary_path = out_dir / "summary.json"

    conversation_count = 0
    message_count = 0

    with conversations_path.open("w", encoding="utf-8", newline="\n") as conversations_file:
        with messages_path.open("w", encoding="utf-8", newline="\n") as messages_file:
            for record in iter_conversations(zip_path):
                conversation_count += 1
                summary = conversation_summary(record)
                conversations_file.write(json.dumps(summary, ensure_ascii=False) + "\n")

                for message in iter_messages(record):
                    message_count += 1
                    messages_file.write(
                        json.dumps(message.__dict__, ensure_ascii=False) + "\n"
                    )

    profile = build_profile(zip_path, include_terms=False)
    summary = {
        "zip_path": str(zip_path),
        "out_dir": str(out_dir),
        "conversation_count": conversation_count,
        "message_count": message_count,
        "files": {
            "conversations": str(conversations_path),
            "messages": str(messages_path),
            "summary": str(summary_path),
        },
        "profile": profile,
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


if __name__ == "__main__":
    main()
