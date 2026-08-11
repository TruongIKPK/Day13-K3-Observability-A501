from __future__ import annotations

import hashlib
import re
from typing import Any

PII_PATTERNS: dict[str, str] = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "phone_vn": r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)",
    "cccd": r"\b\d{12}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "passport": r"(?<![A-Z0-9])(?:[A-Z]{1,2}\d{7})(?![A-Z0-9])",
    "address": r"\b(?:địa\s*chỉ|dia\s*chi|address)\s*[:=-]\s*[^\n;|]+",
}


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(
            pattern,
            f"[REDACTED_{name.upper()}]",
            safe,
            flags=re.IGNORECASE,
        )
    return safe


def scrub_value(value: Any) -> Any:
    """Recursively redact PII from every string value in a log event."""
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, dict):
        return {key: scrub_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(scrub_value(item) for item in value)
    if isinstance(value, set):
        return {scrub_value(item) for item in value}
    return value


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
