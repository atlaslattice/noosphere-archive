"""Deterministic, bounded, JSON-serializable source receipts."""
import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def valid_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def nonempty_string(value: Any, max_len: int = 500) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= max_len


def snapshot(value: Any) -> Any:
    """Value-isolate on ingest and return (callers cannot mutate history)."""
    return json.loads(canonical_json(value))
