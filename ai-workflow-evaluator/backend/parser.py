from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Any


@dataclass
class Message:
    role: str
    content: str


def _normalize_role(raw: str) -> str:
    lowered = raw.strip().lower()
    if lowered in {"user", "assistant", "system", "tool"}:
        return lowered
    return "user"


def _extract_messages_from_json(obj: Any) -> list[Message]:
    messages: list[Message] = []

    if isinstance(obj, dict):
        if "messages" in obj and isinstance(obj["messages"], list):
            for item in obj["messages"]:
                if isinstance(item, dict):
                    role = _normalize_role(str(item.get("role", "user")))
                    content = item.get("content", "")
                    if isinstance(content, list):
                        content = " ".join(str(x) for x in content)
                    messages.append(Message(role=role, content=str(content).strip()))
            return [m for m in messages if m.content]

        if "mapping" in obj and isinstance(obj["mapping"], dict):
            for node in obj["mapping"].values():
                message = node.get("message") if isinstance(node, dict) else None
                if not isinstance(message, dict):
                    continue
                author = message.get("author", {})
                role = _normalize_role(str(author.get("role", "user")))
                content_obj = message.get("content", {})
                parts = content_obj.get("parts", []) if isinstance(content_obj, dict) else []
                content = " ".join(str(p) for p in parts if p)
                if content.strip():
                    messages.append(Message(role=role, content=content.strip()))
            return messages

    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                role = _normalize_role(str(item.get("role", "user")))
                content = str(item.get("content", "")).strip()
                if content:
                    messages.append(Message(role=role, content=content))
        return messages

    return []


def _parse_plain_text(text: str) -> list[Message]:
    messages: list[Message] = []
    role_pattern = re.compile(r"^\s*(user|assistant|system|tool)\s*:\s*(.*)$", re.IGNORECASE)
    current_role = "user"
    current_lines: list[str] = []

    for line in text.splitlines():
        match = role_pattern.match(line)
        if match:
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    messages.append(Message(role=current_role, content=content))
            current_role = _normalize_role(match.group(1))
            current_lines = [match.group(2).strip()]
            continue
        current_lines.append(line)

    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            messages.append(Message(role=current_role, content=content))
    return messages


def _parse_markdown_transcript(text: str) -> list[Message]:
    messages: list[Message] = []
    role_header = re.compile(r"^\s{0,3}(?:#{1,6}\s*)?(user|assistant|system|tool)\s*$", re.IGNORECASE)
    current_role: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.strip().endswith(":") and line.strip()[:-1].strip().lower() in {"user", "assistant", "system", "tool"}:
            header = line.strip()[:-1].strip()
            match = role_header.match(header)
        else:
            match = role_header.match(line.strip())
        if match:
            if current_role and current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    messages.append(Message(role=current_role, content=content))
            current_role = _normalize_role(match.group(1))
            current_lines = []
            continue
        if current_role:
            current_lines.append(line)

    if current_role and current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            messages.append(Message(role=current_role, content=content))
    return messages


def detect_transcript_format(raw_text: str) -> str:
    text = raw_text.strip()
    if not text:
        return "empty"
    try:
        json.loads(text)
        return "json"
    except json.JSONDecodeError:
        pass
    if re.search(r"^\s{0,3}(#{1,6}\s*)?(user|assistant|system|tool)\s*$", text, re.IGNORECASE | re.MULTILINE):
        return "markdown"
    return "plain_text"


def parse_transcript_text(raw_text: str) -> list[Message]:
    text = raw_text.strip()
    if not text:
        return []

    try:
        parsed = json.loads(text)
        msgs = _extract_messages_from_json(parsed)
        if msgs:
            return msgs
    except json.JSONDecodeError:
        pass

    markdown_messages = _parse_markdown_transcript(text)
    if markdown_messages:
        return markdown_messages
    return _parse_plain_text(text)


def parse_transcript_file(path: str | Path) -> list[Message]:
    content = Path(path).read_text(encoding="utf-8")
    return parse_transcript_text(content)


def transcript_to_chunk(messages: list[Message], max_chars: int) -> str:
    lines = [f"{m.role}: {m.content}" for m in messages]
    joined = "\n".join(lines)
    return joined[:max_chars]
