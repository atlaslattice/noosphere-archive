"""Public Atlas registry JSON entry gate: syntax and size only, no host authority.

Reject ambiguous keys (including Unicode-escaped duplicates), non-finite/float
numbers, oversized integers, invalid UTF-8 and >4 MiB payloads before typed
public-repository validation. This is NOT a schema, rights or source attestation.
"""
from __future__ import annotations

import json
from typing import Any

MAX_INVENTORY_BYTES = 4 * 1024 * 1024


class InventoryJSONError(ValueError):
    """Malformed or ambiguous metadata input; preserve original for review."""


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InventoryJSONError("DUPLICATE_REGISTRY_KEY")
        result[key] = value
    return result


def _reject_nonfinite(_: str) -> None:
    raise InventoryJSONError("NONFINITE_NUMBER")


def _reject_float(_: str) -> None:
    # Registry counts and identifiers use integers or strings, never floats.
    raise InventoryJSONError("FLOAT_REGISTRY_VALUE")


def _bounded_int(value: str) -> int:
    if len(value.lstrip("-")) > 20:
        raise InventoryJSONError("OVERSIZED_REGISTRY_INTEGER")
    return int(value)


def strict_inventory_loads(raw: str | bytes) -> Any:
    if type(raw) not in (str, bytes):
        raise InventoryJSONError("REGISTRY_TEXT_REQUIRED")
    try:
        payload = raw.encode("utf-8") if type(raw) is str else raw
        if len(payload) > MAX_INVENTORY_BYTES:
            raise InventoryJSONError("REGISTRY_BYTES_EXCEEDED")
        parsed = json.loads(payload.decode("utf-8"),
                            object_pairs_hook=_unique_pairs,
                            parse_constant=_reject_nonfinite,
                            parse_float=_reject_float,
                            parse_int=_bounded_int)
        # JSON escape sequences may encode *unpaired* surrogates, which
        # Python accepts but which cannot round-trip as Unicode scalar UTF-8.
        # Deny them before carrying ambiguous text into a provenance digest.
        json.dumps(parsed, ensure_ascii=False, allow_nan=False).encode("utf-8")
        return parsed
    except InventoryJSONError:
        raise
    except (UnicodeError, RecursionError, OverflowError, ValueError) as exc:
        raise InventoryJSONError("REGISTRY_JSON_INVALID") from exc
