"""Portable, exact-source delegates for existing Atlas computation packages.

The integrating host selects checkout roots and immutable source locks.  This
module performs local computations only: it never creates an agent, sends a
message, calls a model API, or records a production task as completed.  A source
lock is an integrity contract, not an authentication service or an OS sandbox.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import threading
import time
from typing import Mapping


class FederationError(ValueError):
    """A bounded source, input, or delegate contract was not satisfied."""


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _copy(value):
    return json.loads(_canonical(value))


def _require(condition, code):
    if not condition:
        raise FederationError(code)


HEX40 = re.compile(r"^[a-f0-9]{40}$")
HEX64 = re.compile(r"^[a-f0-9]{64}$")
HSN = re.compile(r"^H(?:0[1-9]|1[0-2])\.S(?:0[1-9]|1[0-2])\.N(?:0[1-9]|1[0-2])$")
SPHERE = re.compile(r"^H(?:0[1-9]|1[0-2])\.S(?:0[1-9]|1[0-2])$")
ENGINEERING = re.compile(r"^EX\.W(?:0[1-9]|1[0-2])\.C(?:0[1-9]|1[0-2])\.P(?:0[1-9]|1[0-2])$")

# Only these inspected package entry points are exposed by the federation.
COMPONENTS = {
    "excellence": {
        "id": "EXCELLENCE1728_CORE", "namespace": "EX1728_ENGINEERING",
        "package": "programs/excellence1728/runtime/excellence1728",
        "operations": ("plan_status", "task", "query", "ready", "perspective", "review_perspective", "meta145"),
    },
    "gf9": {
        "id": "GF9_ROSETTA_R2", "namespace": "GF9_SYNTHETIC_PACKET",
        "package": "research/meta145c_glyph_knowledge/gf9_rosetta_v2/src",
        "operations": ("packet_roundtrip",),
    },
    "unified": {
        "id": "UNIFIED_ATLAS1728_PYTHON", "namespace": "ARIADNE_HSN_SOURCE",
        "package": "research/meta145c_glyph_knowledge/gf9_rosetta_v2/unified_1728_r1/atlas1728",
        "operations": ("source_status", "node_reference", "build_summary"),
    },
}


class _VerifiedLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Compile the bytes just verified, never an unchecked .pyc or extra file."""

    def __init__(self, name, sources):
        self.name, self.sources = name, dict(sources)

    def _entry(self, fullname):
        relative = fullname[len(self.name):].lstrip(".").replace(".", "/")
        package = (relative + "/" if relative else "") + "__init__.py"
        if package in self.sources:
            return package, True
        module = relative + ".py"
        if relative and module in self.sources:
            return module, False
        raise ImportError("UNPINNED_PACKAGE_MODULE")

    def find_spec(self, fullname, path=None, target=None):
        if fullname != self.name and not fullname.startswith(self.name + "."):
            return None
        _, package = self._entry(fullname)
        return importlib.util.spec_from_loader(fullname, self, is_package=package)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        entry, package = self._entry(module.__name__)
        module.__file__ = "verified-atlas-source://" + self.name + "/" + entry
        if package:
            module.__path__ = []
        exec(compile(self.sources[entry], module.__file__, "exec"), module.__dict__)


_IMPORT_LOCK = threading.RLock()


class SourceMount:
    """An explicit checkout plus full Python-package pins at an ancestor commit."""

    def __init__(self, root, component, package):
        self._root = Path(root).resolve(strict=True)
        _require(self._root.is_dir(), "CHECKOUT_ROOT_REQUIRED")
        self._component = _copy(component)
        self._package = self._relative(package)
        self._commit = component.get("commit")
        _require(type(self._commit) is str and HEX40.fullmatch(self._commit), "IMMUTABLE_COMMIT_REQUIRED")
        rows = component.get("source_files")
        _require(type(rows) is list and 1 <= len(rows) <= 4096, "SOURCE_LOCK_REQUIRED")
        self._files = {}
        for row in rows:
            _require(type(row) is dict, "SOURCE_LOCK_INVALID")
            path = self._relative(row.get("path"))
            if path.startswith(self._package + "/") and path.endswith(".py"):
                _require(path not in self._files, "DUPLICATE_SOURCE_PIN")
                _require(type(row.get("sha256")) is str and HEX64.fullmatch(row["sha256"]), "SOURCE_SHA256_REQUIRED")
                _require(type(row.get("git_blob_sha")) is str and HEX40.fullmatch(row["git_blob_sha"]), "SOURCE_BLOB_REQUIRED")
                self._files[path] = (row["sha256"], row["git_blob_sha"])
        _require(self._package + "/__init__.py" in self._files, "COMPLETE_PACKAGE_PIN_REQUIRED")
        self._identity = {"component_id": component["component_id"], "commit": self._commit,
                          "package": self._package, "files": self._files}
        self.lock_sha256 = _digest(self._identity)
        self._sources = self.verify()
        self._module = None
        self._loader = None

    @staticmethod
    def _relative(value):
        _require(type(value) is str and value and "\\" not in value and "\x00" not in value, "RELATIVE_SOURCE_PATH_REQUIRED")
        p = PurePosixPath(value)
        _require(not p.is_absolute() and all(x not in ("", ".", "..") for x in value.split("/")), "SOURCE_PATH_ESCAPE")
        return str(p)

    def _git(self, *args):
        # A partial clone must fail locally rather than silently fetching objects.
        env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0"}
        result = subprocess.run(["git", "-c", "protocol.allow=never", "-C", str(self._root), *args],
                                capture_output=True, timeout=15, check=False, env=env)
        _require(result.returncode == 0, "SOURCE_GIT_IDENTITY_REJECTED")
        _require(len(result.stdout) <= 2 * 1024 * 1024, "SOURCE_GIT_OUTPUT_BOUND")
        return result.stdout

    def verify(self):
        top = Path(self._git("rev-parse", "--show-toplevel").decode().strip()).resolve()
        _require(top == self._root, "CHECKOUT_ROOT_MISMATCH")
        self._git("merge-base", "--is-ancestor", self._commit, "HEAD")
        tree = {}
        for line in self._git("ls-tree", "-r", self._commit, "--", self._package).decode().splitlines():
            metadata, path = line.split("\t", 1)
            mode, kind, sha = metadata.split()
            if path.endswith(".py"):
                _require(kind == "blob" and mode in ("100644", "100755"), "SOURCE_FILE_TYPE_REJECTED")
                tree[path] = sha
        _require(set(tree) == set(self._files), "INCOMPLETE_PACKAGE_SOURCE_LOCK")
        package_path = self._root / self._package
        working = {str(p.relative_to(self._root)) for p in package_path.rglob("*.py")}
        _require(working == set(self._files), "UNPINNED_OR_MISSING_PACKAGE_FILE")
        sources = {}
        for relative, (expected, blob) in self._files.items():
            path = self._root / relative
            _require(not any(p.is_symlink() for p in [path, *path.parents] if p != self._root.parent), "SOURCE_SYMLINK_REJECTED")
            _require(path.is_file() and path.stat().st_size <= 2 * 1024 * 1024, "SOURCE_FILE_BOUND")
            body = path.read_bytes()
            actual_blob = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
            _require(tree[relative] == blob == actual_blob and hashlib.sha256(body).hexdigest() == expected,
                     "SOURCE_BYTES_CHANGED")
            sources[relative[len(self._package) + 1:]] = body
        return sources

    def load(self):
        self.verify()
        with _IMPORT_LOCK:
            if self._module is None:
                # Unique per mount: a mutable module in another mount cannot replace it.
                name = "_atlas_federation_" + self.lock_sha256[:20] + "_" + str(id(self))
                self._loader = _VerifiedLoader(name, self._sources)
                sys.meta_path.insert(0, self._loader)
                try:
                    self._module = importlib.import_module(name)
                except BaseException:
                    self.close()
                    raise
            return self._module

    def submodule(self, name):
        root = self.load()
        _require(type(name) is str and re.fullmatch(r"[a-z][a-z0-9_]*", name), "MODULE_NAME_REJECTED")
        return importlib.import_module(root.__name__ + "." + name)

    def descriptor(self):
        return {"component_id": self._component["component_id"], "repository": self._component.get("repository"),
                "source_commit": self._commit, "package": self._package, "source_files": len(self._files),
                "source_lock_sha256": self.lock_sha256, "revision_policy": "ANCESTOR_WITH_EXACT_PACKAGE_BYTES"}

    def close(self):
        with _IMPORT_LOCK:
            if self._loader is not None:
                if self._loader in sys.meta_path:
                    sys.meta_path.remove(self._loader)
                for name in list(sys.modules):
                    if name == self._loader.name or name.startswith(self._loader.name + "."):
                        del sys.modules[name]
            self._module = self._loader = None


class PinnedFederation:
    """Source-locked read/compute delegates; paths come only from the host config."""

    def __init__(self, mounts: Mapping[str, SourceMount], *, plan_path=None, expected_plan_sha256=None,
                 registry_path=None, topics_path=None):
        _require(bool(mounts) and set(mounts) <= set(COMPONENTS), "SUPPORTED_MOUNT_REQUIRED")
        self._mounts = dict(mounts)
        self._plan_path = Path(plan_path).resolve() if plan_path is not None else None
        self._plan_sha = expected_plan_sha256
        if "excellence" in mounts:
            _require(self._plan_path is not None and type(self._plan_sha) is str and HEX64.fullmatch(self._plan_sha),
                     "EXTERNAL_PLAN_PIN_REQUIRED")
        self._registry = Path(registry_path).resolve() if registry_path is not None else None
        self._topics = Path(topics_path).resolve() if topics_path is not None else None
        _require(self._topics is None or self._registry is not None, "TOPICS_REQUIRE_ORIGINAL_REGISTRY")
        self._ledger = None
        self._perspectives = []

    @classmethod
    def from_inventory(cls, inventory, *, roots, **kwargs):
        _require(type(inventory) is dict and type(inventory.get("components")) is list, "COMPONENT_INVENTORY_REQUIRED")
        components = inventory["components"]
        by_id = {x["component_id"]: x for x in components}
        _require(len(by_id) == len(components), "DUPLICATE_COMPONENT_ID")
        _require(type(roots) is dict and set(roots) <= {v["id"] for v in COMPONENTS.values()}, "UNSUPPORTED_COMPONENT_ROOT")
        mounts = {}
        try:
            for alias, spec in COMPONENTS.items():
                if spec["id"] in roots:
                    _require(spec["id"] in by_id, "COMPONENT_SOURCE_LOCK_MISSING")
                    mounts[alias] = SourceMount(roots[spec["id"]], by_id[spec["id"]], spec["package"])
            return cls(mounts, **kwargs)
        except BaseException:
            for mount in mounts.values():
                mount.close()
            raise

    def _plan(self):
        _require(self._plan_path is not None and self._plan_path.is_file() and self._plan_path.stat().st_size <= 48 * 1024 * 1024,
                 "PLAN_FILE_REQUIRED")
        body = self._plan_path.read_bytes()
        _require(hashlib.sha256(body).hexdigest() == self._plan_sha, "PLAN_BYTES_CHANGED")
        api = self._mounts["excellence"].load()
        plan = api.strict_loads(body)
        api.validate_plan(plan, expected_sha256=self._plan_sha)
        _require(api.canonical_bytes(plan) == body, "CANONICAL_PLAN_REQUIRED")
        return api, plan

    def bind_excellence_evidence(self, ledger, perspective_receipts=()):
        """Host-only Python binding; JSON tool arguments cannot supply a ledger."""
        api, plan = self._plan()
        _require(type(ledger) is api.EvidenceLedger and ledger.plan_sha256 == self._plan_sha,
                 "GENUINE_PLAN_LEDGER_REQUIRED")
        receipts = _copy(list(perspective_receipts))
        api.aggregate_meta145(plan, ledger, receipts)
        self._ledger, self._perspectives = ledger, receipts

    @staticmethod
    def _args(arguments, allowed, required=()):
        _require(type(arguments) is dict and set(arguments) <= set(allowed) and set(required) <= set(arguments),
                 "OPERATION_ARGUMENTS_INVALID")
        _require(len(_canonical(arguments)) <= 256 * 1024, "ARGUMENT_PAYLOAD_BOUND")
        return _copy(arguments)

    def status(self):
        rows = []
        for alias, mount in sorted(self._mounts.items()):
            mount.verify()
            rows.append({**mount.descriptor(), "alias": alias, "namespace": COMPONENTS[alias]["namespace"],
                         "operations": list(COMPONENTS[alias]["operations"]), "source_verified_now": True})
        return {"schema": "atlas.native.federation-status/v1", "mounted_components": rows,
                "external_effects": False, "model_api_calls": 0, "hosted_deployment_verified": False,
                "namespace_equivalence_inferred": False}

    def _excellence(self, operation, arguments):
        api, plan = self._plan()
        if operation == "plan_status":
            self._args(arguments, ())
            checked = api.validate_plan(plan, expected_sha256=self._plan_sha)
            order = checked.pop("topological_order", [])
            return {**checked, "topological_tasks": len(order), "topological_order_sha256": _digest(order)}
        if operation == "task":
            args = self._args(arguments, ("task_id",), ("task_id",))
            _require(type(args["task_id"]) is str and ENGINEERING.fullmatch(args["task_id"]), "ENGINEERING_ID_REQUIRED")
            return api.read_task(plan, args["task_id"], expected_sha256=self._plan_sha)
        if operation == "query":
            args = self._args(arguments, ("text", "workstream_id", "phase_id", "limit", "offset"))
            return api.query_tasks(plan, **args)
        if operation == "ready":
            args = self._args(arguments, ("total_units", "used_work_units", "max_ready", "limit"))
            limit = args.pop("limit", None)
            budget = api.WorkBudget(**{"total_units": 36, **args})
            return api.ready_tasks(plan, self._ledger, budget=budget, limit=limit)
        if operation == "review_perspective":
            args = self._args(arguments, ("sphere_id", "task_ids"), ("sphere_id", "task_ids"))
            _require(self._ledger is not None, "VERIFIED_ENGINEERING_LEDGER_REQUIRED")
            return api.review_perspective(plan, self._ledger, args["sphere_id"], args["task_ids"])
        if operation == "meta145":
            self._args(arguments, ())
            return api.aggregate_meta145(plan, self._ledger, self._perspectives)
        args = self._args(arguments, ("sphere_id",), ("sphere_id",))
        _require(type(args["sphere_id"]) is str and SPHERE.fullmatch(args["sphere_id"]), "ORIGINAL_SPHERE_ID_REQUIRED")
        meta = api.aggregate_meta145(plan, self._ledger, self._perspectives)
        row = next(x for x in meta["perspectives"] if x["sphere_id"] == args["sphere_id"])
        return {"schema": "atlas.native.source-perspective-slot/v1", **row, "kind": "SOURCE_COVERAGE_SLOT",
                "plan_sha256": self._plan_sha, "ariadne_source_sha256": plan["coverage"]["ariadne_source_sha256"],
                "independent_resident_review": False, "semantic_crosswalk_accepted": False}

    def _gf9(self, arguments):
        args = self._args(arguments, ("module", "chapter", "repetition", "decimals"), ("module", "chapter"))
        _require(type(args["module"]) is int and 0 <= args["module"] < 144 and type(args["chapter"]) is int and 0 <= args["chapter"] < 12,
                 "GF9_INTEGER_COORDINATES_REQUIRED")
        api = self._mounts["gf9"].submodule("protocol")
        policy = api.Policy(args.get("repetition", 1), args.get("decimals", 6))
        message = api.make_message(args["module"], args["chapter"], policy)
        wire = api.serialize_repetition(api.encode(message, policy), policy)
        recovered, recovery = api.recover(wire, policy)
        return {"message": message, "recovered": recovered, "recovery": recovery,
                "wire_bytes": len(wire), "wire_sha256": hashlib.sha256(wire).hexdigest(),
                "exact_roundtrip": recovered == message,
                "numerical_validation": api.valid_message(recovered, args["module"], args["chapter"]),
                "scope": "BOUNDED_SYNTHETIC_PROTOCOL_COMPUTATION", "sender_authenticated": False}

    def _corpus(self):
        api = self._mounts["unified"].load()
        if self._registry is None:
            return api, api.Corpus.synthetic()
        return api, api.Corpus.original(self._registry, self._topics)

    def _unified(self, operation, arguments):
        allowed = ("coordinate",) if operation == "node_reference" else ()
        args = self._args(arguments, allowed, allowed)
        api, corpus = self._corpus()
        if operation == "source_status":
            return {"source_sha256": corpus.registry_sha, "original_source_verified": corpus.exact_source_verified,
                    "houses": len(corpus.houses), "spheres": len(corpus.spheres), "nodes": len(corpus.nodes),
                    "historical_topics": len(corpus.topics), "semantic_crosswalk_accepted": False}
        if operation == "node_reference":
            _require(type(args["coordinate"]) is str and HSN.fullmatch(args["coordinate"]), "ORIGINAL_HSN_ID_REQUIRED")
            node = corpus.safe_node(args["coordinate"])
            return {"coordinate": node["id"], "sphere": node["parent"], "kind": node["kind"],
                    "source_record_sha256": node["source_record_sha256"], "registry_sha256": corpus.registry_sha,
                    "original_source_verified": corpus.exact_source_verified, "source_body_returned": False}
        build = api.compile_build(corpus)
        api.verify_build(build, corpus)
        return {**build["summary"], "independent_adapter_verification": True, "source_bodies_returned": False}

    def call(self, component, operation, arguments=None):
        _require(type(component) is str and component in self._mounts, "COMPONENT_NOT_MOUNTED")
        _require(type(operation) is str and operation in COMPONENTS[component]["operations"], "OPERATION_NOT_EXPOSED")
        arguments = {} if arguments is None else arguments
        mount = self._mounts[component]
        mount.verify()
        started = time.perf_counter_ns()
        try:
            result = self._excellence(operation, arguments) if component == "excellence" else (
                self._gf9(arguments) if component == "gf9" else self._unified(operation, arguments))
        except (ValueError, TypeError, KeyError, StopIteration) as exc:
            if isinstance(exc, FederationError):
                raise
            raise FederationError("UPSTREAM_DELEGATE_REJECTED") from exc
        mount.verify()
        if component == "excellence":
            self._plan()  # Independently re-read input before returning.
        elif component == "unified" and self._registry is not None:
            self._corpus()  # Exact original registry/crosswalk must still match.
        result = _copy(result)
        receipt = {"schema": "atlas.native.federation-call/v1", "component_id": COMPONENTS[component]["id"],
                   "operation": operation, "namespace": COMPONENTS[component]["namespace"],
                   "source_commit": mount.descriptor()["source_commit"], "source_lock_sha256": mount.lock_sha256,
                   "input_sha256": _digest(arguments), "result_sha256": _digest(result), "result": result,
                   "source_verified_before_and_after": True, "network_requests": 0, "model_calls": 0,
                   "work_messages_posted": 0, "hosted_authority_granted": False,
                   "elapsed_ms": round((time.perf_counter_ns() - started) / 1e6, 3)}
        receipt["receipt_sha256"] = _digest({k: v for k, v in receipt.items() if k != "elapsed_ms"})
        return receipt

    def close(self):
        for mount in self._mounts.values():
            mount.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
