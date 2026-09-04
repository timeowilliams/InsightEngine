from __future__ import annotations

import json
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from chatgpt_export import conversation_entry_names, iter_conversations, iter_messages


class ChatGPTExportTests(unittest.TestCase):
    def test_reads_chunked_conversation_files(self) -> None:
        with TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "export.zip"
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("conversations-001.json", json.dumps([conversation("two")]))
                archive.writestr("conversations-000.json", json.dumps([conversation("one")]))
                archive.writestr("not-conversations.json", "[]")

            self.assertEqual(
                conversation_entry_names(zip_path),
                ["conversations-000.json", "conversations-001.json"],
            )
            records = list(iter_conversations(zip_path))
            self.assertEqual([record.conversation["id"] for record in records], ["one", "two"])

    def test_extracts_message_role_timestamp_text_and_empty_messages(self) -> None:
        with TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "export.zip"
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("conversations-000.json", json.dumps([conversation("one")]))

            record = next(iter_conversations(zip_path))
            messages = list(iter_messages(record))

        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0].message_id, "msg-user")
        self.assertEqual(messages[0].role, "user")
        self.assertEqual(messages[0].parent_id, "root")
        self.assertEqual(messages[0].create_time, "2024-09-13T12:00:00+00:00")
        self.assertEqual(messages[0].update_time, "2024-09-13T12:01:00+00:00")
        self.assertEqual(messages[0].text, "Maybe debug this error?")
        self.assertEqual(messages[0].word_count, 4)
        self.assertEqual(messages[1].role, "assistant")
        self.assertEqual(messages[2].text, "")
        self.assertEqual(messages[2].word_count, 0)


def conversation(conversation_id: str) -> dict[str, object]:
    return {
        "id": conversation_id,
        "title": "Fixture Conversation",
        "create_time": 1726228800.0,
        "update_time": 1726228860.0,
        "mapping": {
            "root": {"id": "root", "message": None, "parent": None},
            "user": {
                "id": "user",
                "parent": "root",
                "message": {
                    "id": "msg-user",
                    "author": {"role": "user"},
                    "create_time": 1726228800.0,
                    "update_time": 1726228860.0,
                    "content": {
                        "content_type": "text",
                        "parts": ["Maybe debug this error?"],
                    },
                },
            },
            "assistant": {
                "id": "assistant",
                "parent": "user",
                "message": {
                    "id": "msg-assistant",
                    "author": {"role": "assistant"},
                    "create_time": 1726228870.0,
                    "content": {
                        "content_type": "text",
                        "parts": ["Here is one way to fix it."],
                    },
                },
            },
            "empty": {
                "id": "empty",
                "parent": "assistant",
                "message": {
                    "id": "msg-empty",
                    "author": {"role": "user"},
                    "create_time": 1726228880.0,
                    "content": {"content_type": "text", "parts": []},
                },
            },
        },
    }


if __name__ == "__main__":
    unittest.main()
