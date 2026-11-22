"""Public-only Noosphere repository register; strict offline validation.

Everything returned is source/metadata, never a right to open, index, execute,
merge, train on, publish, or deploy repo content. No network/filesystem writes,
credential handling, private source extraction or semantic HSN routing.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit
from registry.strict_inventory_json import InventoryJSONError, strict_inventory_loads

SCHEMA = "atlas.public-repository-registry/v0.1"
SOURCE_QUERY = "org:atlaslattice"
COVERAGE = "PUBLIC_SEARCH_ENUMERATION_ONLY_NOT_FULL_ACCOUNT_OR_PRIVATE_CENSUS"
PUBLIC_PREFIX = "https://github.com/atlaslattice/"
ROLE_CANDIDATES = frozenset({
    "core_substrate", "domain_research", "governance_archive", "unclassified_public_repo"
})
NAME_FLAGS = frozenset({"NAME_ONLY_SENSITIVE_REVIEW_CANDIDATE", "UNREVIEWED"})
EXPECTED_TOP_KEYS = frozenset({
    "schema", "source", "source_query", "source_pages", "observed_date_utc",
    "coverage", "public_only", "source_page_lengths", "records_count",
    "excluded_nonpublic_count", "notes", "records"
})
EXPECTED_RECORD_KEYS = frozenset({
    "repo_full_name", "repository_id", "url", "visibility", "archived",
    "default_branch", "role_candidate", "sensitivity_name_flag", "readiness",
    "provenance_status", "runtime_status", "canon_status", "sphere144_tags",
    "related_core_repos", "notes"
})
NAME = re.compile(r"atlaslattice/[A-Za-z0-9_.-]{1,100}\Z")
BRANCH = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\/-]{0,180}\Z")
ISSUE_URL = re.compile(r"https://github\.com/(atlaslattice/[A-Za-z0-9_.-]{1,100})/(issues|pull)/(\d{1,12})\Z")
MAX_CATALOG_BYTES = 4 * 1024 * 1024  # public metadata import size guard


class RegistryError(ValueError):
    """Fail-closed error. Never infer missing private data from a result."""


def _require(check: bool, code: str) -> None:
    if not check:
        raise RegistryError(code)


def _string(v: Any) -> bool:
    return isinstance(v, str) and bool(v)


def _natural(v: Any) -> bool:
    return type(v) is int and v >= 0  # reject booleans


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Do not let a later public flag shadow earlier non-public metadata."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RegistryError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def load_catalog_text(source_text: str) -> dict[str, Any]:
    """Parse untrusted public metadata without duplicate-key or NaN ambiguity."""
    _require(type(source_text) is str, "CATALOG_TEXT_REQUIRED")
    _require(len(source_text.encode("utf-8")) <= MAX_CATALOG_BYTES, "CATALOG_TOO_LARGE")
    try:
        value = strict_inventory_loads(source_text)
    except InventoryJSONError as exc:
        # Preserve existing public CLI error codes for established consumers.
        code = {"DUPLICATE_REGISTRY_KEY": "DUPLICATE_JSON_KEY",
                "REGISTRY_BYTES_EXCEEDED": "CATALOG_TOO_LARGE"}.get(str(exc), str(exc))
        raise RegistryError(code) from exc
    except RecursionError as exc:
        raise RegistryError("CATALOG_NESTING_TOO_DEEP") from exc
    _require(type(value) is dict, "CATALOG_NOT_OBJECT")
    return value


def _reject_redirect_or_query(url: str, fullname: str) -> None:
    _require(url == PUBLIC_PREFIX + fullname.split("/", 1)[1], "NON_CANONICAL_PUBLIC_URL")
    p = urlsplit(url)
    _require(p.scheme == "https" and p.hostname == "github.com" and not p.query and not p.fragment and not p.username, "UNSAFE_URL")


def validate_catalog(raw: Any) -> dict[str, Any]:
    """Validate exact snapshot shape and identity, return structural counts only.

    This does not recheck current public visibility, permissions, source semantics,
    source completeness, repository contents or rights-at-return.
    """
    _require(type(raw) is dict, "CATALOG_NOT_OBJECT")
    _require(set(raw) == EXPECTED_TOP_KEYS, "CATALOG_FIELDS_UNEXPECTED_OR_MISSING")
    _require(raw["schema"] == SCHEMA, "SCHEMA_MISMATCH")
    _require(raw["source_query"] == SOURCE_QUERY and raw["coverage"] == COVERAGE, "SOURCE_SCOPE_MISMATCH")
    _require(raw["public_only"] is True, "PUBLIC_ONLY_REQUIRED")
    _require(_string(raw["source"]) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw["observed_date_utc"]) is not None, "MISSING_SNAPSHOT_PASSPORT")
    pages, lengths = raw["source_pages"], raw["source_page_lengths"]
    _require(type(pages) is list and type(lengths) is list and len(pages) == len(lengths) >= 2, "PAGE_CUT_MISSING")
    _require(all(type(x) is int and x == i + 1 for i, x in enumerate(pages)), "PAGE_SEQUENCE_INVALID")
    _require(all(_natural(n) for n in lengths) and lengths[-1] == 0, "INCOMPLETE_PAGE_FRONTIER")
    _require(_natural(raw["records_count"]) and _natural(raw["excluded_nonpublic_count"]), "COUNTS_NOT_INTEGER")
    _require(type(raw["notes"]) is list and all(_string(x) for x in raw["notes"]), "SOURCE_NOTES_INVALID")
    records = raw["records"]
    _require(type(records) is list and len(records) == raw["records_count"], "RECORD_COUNT_MISMATCH")
    _require(sum(lengths) == len(records) + raw["excluded_nonpublic_count"], "SOURCE_PAGE_RECONCILIATION_MISMATCH")
    seen_names, seen_ids = set(), set()
    roles, flags = Counter(), Counter()
    for r in records:
        _require(type(r) is dict and set(r) == EXPECTED_RECORD_KEYS, "RECORD_FIELDS_UNEXPECTED_OR_MISSING")
        n, rid, url = r["repo_full_name"], r["repository_id"], r["url"]
        _require(_string(n) and NAME.fullmatch(n) is not None and n not in seen_names, "REPO_NAME_INVALID_OR_DUPLICATE")
        _require(_string(rid) and re.fullmatch(r"[0-9]{1,25}", rid) is not None and rid not in seen_ids, "REPO_ID_INVALID_OR_DUPLICATE")
        seen_names.add(n); seen_ids.add(rid)
        _require(_string(url), "PUBLIC_URL_MISSING")
        _reject_redirect_or_query(url, n)
        _require(r["visibility"] == "public" and type(r["archived"]) is bool, "NONPUBLIC_RECORD")
        _require(_string(r["default_branch"]) and BRANCH.fullmatch(r["default_branch"]) is not None and ".." not in r["default_branch"], "BRANCH_INVALID")
        _require(_string(r["role_candidate"]) and r["role_candidate"] in ROLE_CANDIDATES, "UNREVIEWED_ROLE_UNSAFE")
        _require(_string(r["sensitivity_name_flag"]) and r["sensitivity_name_flag"] in NAME_FLAGS, "SENSITIVITY_FLAG_UNSAFE")
        _require(r["readiness"] == "HOLD_FOR_SOURCE_AND_RIGHTS_REVIEW", "READINESS_OVERCLAIM")
        _require(r["provenance_status"] == "GITHUB_PUBLIC_METADATA_OBSERVED", "PROVENANCE_OVERCLAIM")
        _require(r["runtime_status"] == "NOT_VERIFIED" and r["canon_status"] == "NOT_CANON", "AUTHORITY_OVERCLAIM")
        _require(r["sphere144_tags"] == [] and r["related_core_repos"] == [] and r["notes"] is None, "UNREVIEWED_LINKAGE_OR_PRIVATE_CONTENT")
        roles[r["role_candidate"]] += 1
        flags[r["sensitivity_name_flag"]] += 1
    return {
        "status": "PUBLIC_METADATA_STRUCTURALLY_VALID_NOT_LIVE_VERIFIED",
        "observed_date_utc": raw["observed_date_utc"],
        "record_count": len(records),
        "excluded_nonpublic_count": raw["excluded_nonpublic_count"],
        "role_candidates": dict(sorted(roles.items())),
        "sensitivity_flags": dict(sorted(flags.items())),
        "source_pages": pages,
        "source_page_lengths": lengths,
        "private_repo_names_returned": False,
        "host_or_canon_authority": "NONE",
    }


def lookup_public_repo(raw: Mapping[str, Any], name: str) -> dict[str, Any]:
    """Only return a pointer to an exactly indexed public repo; no fuzzy matches."""
    validate_catalog(raw)
    _require(type(name) is str and NAME.fullmatch(name) is not None, "INVALID_PUBLIC_LOOKUP")
    matches = [r for r in raw["records"] if r["repo_full_name"] == name]
    _require(len(matches) == 1, "PUBLIC_REPO_NOT_IN_SOURCE_CUT")
    x = matches[0]
    return {
        "repo_full_name": x["repo_full_name"], "url": x["url"],
        "default_branch_at_cut": x["default_branch"],
        "role_candidate": x["role_candidate"],
        "risk_review_required": True,
        "source_status": "PUBLIC_POINTER_ONLY",
        "rights_to_content_or_deploy": "NONE",
        "hsn_semantic_mapping": "UNREVIEWED",
    }


def route_public_issue(raw: Mapping[str, Any], url: str) -> dict[str, Any]:
    """Resolve GitHub issue/PR URL to one public repo pointer, never close or merge."""
    validate_catalog(raw)
    _require(type(url) is str, "INVALID_PUBLIC_LINK")
    m = ISSUE_URL.fullmatch(url)
    _require(m is not None and int(m.group(3)) > 0, "INVALID_PUBLIC_LINK")
    repo = lookup_public_repo(raw, m.group(1))
    return {
        "repo_full_name": repo["repo_full_name"],
        "resource_type": "PR" if m.group(2) == "pull" else "ISSUE",
        "resource_number": int(m.group(3)),
        "repo_source_status": "PUBLIC_POINTER_ONLY",
        "resource_existence": "NOT_CHECKED",
        "can_close_or_merge": False,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Offline, public-only Noosphere repo source registry")
    ap.add_argument("--input", type=Path, default=Path(__file__).resolve().parent / "public_repo_inventory_2026-11-22.json")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--lookup", help="exact atlaslattice/public repo name")
    group.add_argument("--issue", help="exact public GitHub issue or pull URL")
    args = ap.parse_args(argv)
    try:
        raw = load_catalog_text(args.input.read_text(encoding="utf-8"))
        result = route_public_issue(raw, args.issue) if args.issue is not None else lookup_public_repo(raw, args.lookup) if args.lookup is not None else validate_catalog(raw)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (RegistryError, json.JSONDecodeError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "HOLD", "reason": type(exc).__name__ + ": " + str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
