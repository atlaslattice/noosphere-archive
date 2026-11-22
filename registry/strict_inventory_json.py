"""Strict metadata-only Atlas inventory JSON reader; never fetches source URLs.

Reject duplicate *decoded* keys, nonfinite values and excessive input bytes
before trusting registry assertions. A parsed inventory grants no host rights.
"""
from __future__ import annotations

import json
from typing import Any

MAX_INVENTORY_BYTES = 4 * 1024 * 1024


class InventoryJSONError(ValueError):
    pass


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise InventoryJSONError("DUPLICATE_REGISTRY_KEY")
        obj[key] = value
    return obj


def _reject_nonfinite(_: str) -> None:
    raise InventoryJSONError("NONFINITE_REGISTRY_VALUE")


def strict_inventory_loads(raw: str | bytes) -> Any:
    if type(raw) not in (str, bytes):
        raise InventoryJSONError("REGISTRY_TEXT_REQUIRED")
    try:
        payload = raw.encode("utf-8") if type(raw) is str else raw
        if len(payload) > MAX_INVENTORY_BYTES:
            raise InventoryJSONError("REGISTRY_BYTES_EXCEEDED")
        return json.loads(payload.decode("utf-8"),
                          object_pairs_hook=_unique_pairs,
                          parse_constant=_reject_nonfinite)
    except (UnicodeError, RecursionError, OverflowError, json.JSONDecodeError) as exc:
        raise InventoryJSONError("REGISTRY_JSON_INVALID") from exc
