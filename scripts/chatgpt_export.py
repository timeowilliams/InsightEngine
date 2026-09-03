"""Utilities for reading ChatGPT conversation exports.

The functions in this module intentionally avoid third-party dependencies so
the first ingestion milestone can run on a fresh Python install.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CONVERSATION_FILE_RE = re.compile(r"^conversations(?:-\d+)?\.json$")


@dataclass(frozen=True)
class ConversationRecord:
    source_file: str
    source_index: int
    conversation: dict[str, Any]


@dataclass(frozen=True)
class MessageRecord:
    conversation_id: str
    conversation_title: str | None
    message_id: str
    parent_id: str | None
    role: str | None
    create_time: str | None
    update_time: str | None
    content_type: str | None
    text: str
    text_sha256: str
    word_count: int
    char_count: int


def conversation_entry_names(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path) as archive:
        names = [
            info.filename
            for info in archive.infolist()
            if CONVERSATION_FILE_RE.match(Path(info.filename).name)
        ]
    return sorted(names)


def iter_conversations(zip_path: Path) -> Iterator[ConversationRecord]:
    with zipfile.ZipFile(zip_path) as archive:
        for name in conversation_entry_names(zip_path):
            with archive.open(name) as file_obj:
                payload = json.load(file_obj)

            if isinstance(payload, list):
                conversations = payload
            elif isinstance(payload, dict) and isinstance(payload.get("conversations"), list):
                conversations = payload["conversations"]
            else:
                raise ValueError(f"{name} does not look like a conversation export file")

            for index, conversation in enumerate(conversations):
                if isinstance(conversation, dict):
                    yield ConversationRecord(name, index, conversation)


def iter_messages(record: ConversationRecord) -> Iterator[MessageRecord]:
    conversation = record.conversation
    mapping = conversation.get("mapping") or {}
    if not isinstance(mapping, dict):
        return

    conversation_id = str(
        conversation.get("conversation_id")
        or conversation.get("id")
        or stable_id(record.source_file, str(record.source_index))
    )
    title = conversation.get("title")
    if title is not None:
        title = str(title)

    for node_id, node in mapping.items():
        if not isinstance(node, dict):
            continue

        message = node.get("message")
        if not isinstance(message, dict):
            continue

        text = extract_text(message.get("content"))
        role = extract_role(message)
        create_time = normalize_timestamp(message.get("create_time") or node.get("create_time"))
        update_time = normalize_timestamp(message.get("update_time") or node.get("update_time"))
        content = message.get("content") if isinstance(message.get("content"), dict) else {}
        content_type = content.get("content_type") if isinstance(content, dict) else None
        message_id = str(message.get("id") or node_id)
        parent_id = node.get("parent")
        if parent_id is not None:
            parent_id = str(parent_id)

        yield MessageRecord(
            conversation_id=conversation_id,
            conversation_title=title,
            message_id=message_id,
            parent_id=parent_id,
            role=role,
            create_time=create_time,
            update_time=update_time,
            content_type=str(content_type) if content_type is not None else None,
            text=text,
            text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            word_count=count_words(text),
            char_count=len(text),
        )


def conversation_summary(record: ConversationRecord) -> dict[str, Any]:
    conversation = record.conversation
    conversation_id = str(
        conversation.get("conversation_id")
        or conversation.get("id")
        or stable_id(record.source_file, str(record.source_index))
    )
    messages = list(iter_messages(record))

    return {
        "conversation_id": conversation_id,
        "title": conversation.get("title"),
        "create_time": normalize_timestamp(conversation.get("create_time")),
        "update_time": normalize_timestamp(conversation.get("update_time")),
        "source_file": record.source_file,
        "source_index": record.source_index,
        "message_count": len(messages),
        "user_message_count": sum(1 for message in messages if message.role == "user"),
        "assistant_message_count": sum(1 for message in messages if message.role == "assistant"),
        "total_words": sum(message.word_count for message in messages),
    }


def extract_role(message: dict[str, Any]) -> str | None:
    author = message.get("author")
    if isinstance(author, dict) and author.get("role") is not None:
        return str(author["role"])
    return None


def extract_text(content: Any) -> str:
    if not isinstance(content, dict):
        return ""

    parts = content.get("parts")
    text_values: list[str] = []

    if isinstance(parts, list):
        for part in parts:
            if isinstance(part, str):
                text_values.append(part)
            elif isinstance(part, dict):
                if isinstance(part.get("text"), str):
                    text_values.append(part["text"])
                elif isinstance(part.get("content"), str):
                    text_values.append(part["content"])

    if isinstance(content.get("text"), str):
        text_values.append(content["text"])

    return "\n".join(value.strip() for value in text_values if value and value.strip())


def normalize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    if isinstance(value, str):
        return value
    return None


def count_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", text))


def stable_id(*parts: str) -> str:
    joined = "\0".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:24]


def json_default(value: Any) -> Any:
    if hasattr(value, "__dict__"):
        return value.__dict__
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
