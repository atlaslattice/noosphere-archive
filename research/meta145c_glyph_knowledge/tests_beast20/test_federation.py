"""Source custody, namespace and real upstream delegate checks."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from src.beast20.federation import FederationError, PinnedFederation, SourceMount


PACKAGE = Path(__file__).resolve().parents[1]
REPOSITORY = PACKAGE.parents[1]
INVENTORY = json.loads((PACKAGE / "docs/native1728/PUBLIC_COMPONENT_INVENTORY.json").read_text())
PLAN_SHA = "47084b895a6317db16275a92c3878a340d31af15fb9ab479db7101953c18e49c"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def run_git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL).decode().strip()


class SourceMountContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "pkg").mkdir()
        (self.root / "pkg/__init__.py").write_text("from .value import VALUE\n")
        (self.root / "pkg/value.py").write_text("VALUE = 7\n")
        run_git(self.root, "init", "-q")
        run_git(self.root, "add", "pkg")
        run_git(self.root, "-c", "user.name=Federation Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "Pinned test package")
        self.commit = run_git(self.root, "rev-parse", "HEAD")
        files = []
        for path in sorted((self.root / "pkg").glob("*.py")):
            relative = str(path.relative_to(self.root))
            files.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "git_blob_sha": run_git(self.root, "rev-parse", self.commit + ":" + relative)})
        self.component = {"component_id": "TEST", "repository": "example/public", "commit": self.commit, "source_files": files}
        self.mounts = []

    def tearDown(self):
        for mount in self.mounts:
            mount.close()
        self.temp.cleanup()

    def mount(self, component=None):
        mount = SourceMount(self.root, component or self.component, "pkg")
        self.mounts.append(mount)
        return mount

    def test_verified_bytes_execute_and_descriptor_has_no_local_root(self):
        mount = self.mount()
        self.assertEqual(mount.load().VALUE, 7)
        self.assertNotIn(str(self.root), json.dumps(mount.descriptor()))
        self.assertEqual(mount.descriptor()["source_files"], 2)

    def test_post_mount_file_tampering_is_rejected(self):
        mount = self.mount()
        self.assertEqual(mount.load().VALUE, 7)
        (self.root / "pkg/value.py").write_text("VALUE = 999\n")
        with self.assertRaisesRegex(FederationError, "SOURCE_BYTES_CHANGED"):
            mount.load()

    def test_self_rehashed_replacement_still_disagrees_with_commit(self):
        path = self.root / "pkg/value.py"
        path.write_text("VALUE = 999\n")
        body = path.read_bytes()
        self.component["source_files"][1]["sha256"] = hashlib.sha256(body).hexdigest()
        self.component["source_files"][1]["git_blob_sha"] = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
        with self.assertRaisesRegex(FederationError, "SOURCE_BYTES_CHANGED"):
            self.mount()

    def test_missing_dependency_pin_rejected(self):
        self.component["source_files"].pop()
        with self.assertRaisesRegex(FederationError, "INCOMPLETE_PACKAGE_SOURCE_LOCK"):
            self.mount()

    def test_extra_python_file_rejected(self):
        (self.root / "pkg/extra.py").write_text("VALUE = 999\n")
        with self.assertRaisesRegex(FederationError, "UNPINNED_OR_MISSING_PACKAGE_FILE"):
            self.mount()

    def test_symlink_substitution_rejected(self):
        path = self.root / "pkg/value.py"
        target = self.root / "copied.py"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
        with self.assertRaisesRegex(FederationError, "SOURCE_SYMLINK_REJECTED"):
            self.mount()

    def test_traversal_and_duplicate_pins_rejected(self):
        with self.assertRaisesRegex(FederationError, "SOURCE_PATH_ESCAPE"):
            SourceMount(self.root, self.component, "../pkg")
        self.component["source_files"].append(dict(self.component["source_files"][0]))
        with self.assertRaisesRegex(FederationError, "DUPLICATE_SOURCE_PIN"):
            self.mount()

    def test_descendant_commit_allowed_only_with_original_package_bytes(self):
        (self.root / "unrelated.txt").write_text("preserved source history\n")
        run_git(self.root, "add", "unrelated.txt")
        run_git(self.root, "-c", "user.name=Federation Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "Unrelated integration")
        self.assertEqual(self.mount().load().VALUE, 7)

    def test_unknown_commit_rejected(self):
        self.component["commit"] = "1" * 40
        with self.assertRaisesRegex(FederationError, "SOURCE_GIT_IDENTITY_REJECTED"):
            self.mount()

    def test_separate_mounts_have_distinct_module_objects(self):
        one, two = self.mount(), self.mount()
        one.load().VALUE = 100
        self.assertEqual(two.load().VALUE, 7)
        one.close()
        self.assertEqual(two.load().VALUE, 7)


class ExistingGF9DelegateTests(unittest.TestCase):
    def setUp(self):
        self.federation = PinnedFederation.from_inventory(INVENTORY, roots={
            "GF9_ROSETTA_R2": str(REPOSITORY), "UNIFIED_ATLAS1728_PYTHON": str(REPOSITORY)})

    def tearDown(self):
        self.federation.close()

    def test_real_gf9_roundtrip_and_receipt(self):
        receipt = self.federation.call("gf9", "packet_roundtrip", {"module": 143, "chapter": 11, "repetition": 3})
        self.assertTrue(receipt["result"]["exact_roundtrip"])
        self.assertTrue(receipt["result"]["numerical_validation"])
        self.assertFalse(receipt["result"]["sender_authenticated"])
        self.assertEqual(receipt["result"]["message"]["m"], "H12.S12")
        self.assertEqual(receipt["result_sha256"], hashlib.sha256(canonical(receipt["result"])).hexdigest())
        stable = {k: v for k, v in receipt.items() if k not in ("receipt_sha256", "elapsed_ms")}
        self.assertEqual(receipt["receipt_sha256"], hashlib.sha256(canonical(stable)).hexdigest())

    def test_synthetic_registry_is_labelled_and_node_bodies_not_returned(self):
        source = self.federation.call("unified", "source_status")["result"]
        self.assertEqual((source["houses"], source["spheres"], source["nodes"]), (12, 144, 1728))
        self.assertFalse(source["original_source_verified"])
        node = self.federation.call("unified", "node_reference", {"coordinate": "H01.S01.N01"})["result"]
        self.assertFalse(node["source_body_returned"])
        self.assertNotIn("name", node)
        self.assertNotIn("definition", node)

    def test_real_unified_build_invokes_twelve_modules(self):
        result = self.federation.call("unified", "build_summary")["result"]
        self.assertEqual((result["house_modules"], result["sphere_pathways"], result["node_upgrades"]), (12, 144, 1728))
        self.assertEqual(result["module_node_checks"], 20736)
        self.assertTrue(result["independent_adapter_verification"])
        self.assertFalse(result["original_source_bytes_verified"])
        self.assertFalse(result["host_deployed"])

    def test_namespaces_cannot_be_substituted(self):
        for coordinate in ("EX.W01.C01.P01", "STRATEGY-0001", "H00.S00.N00"):
            with self.assertRaisesRegex(FederationError, "ORIGINAL_HSN_ID_REQUIRED"):
                self.federation.call("unified", "node_reference", {"coordinate": coordinate})
        with self.assertRaisesRegex(FederationError, "GF9_INTEGER_COORDINATES_REQUIRED"):
            self.federation.call("gf9", "packet_roundtrip", {"module": "H01.S01", "chapter": 1})
        with self.assertRaisesRegex(FederationError, "GF9_INTEGER_COORDINATES_REQUIRED"):
            self.federation.call("gf9", "packet_roundtrip", {"module": True, "chapter": 1})

    def test_unregistered_operation_and_extra_arguments_rejected(self):
        with self.assertRaisesRegex(FederationError, "OPERATION_NOT_EXPOSED"):
            self.federation.call("gf9", "run_agent", {})
        with self.assertRaisesRegex(FederationError, "OPERATION_ARGUMENTS_INVALID"):
            self.federation.call("gf9", "packet_roundtrip", {"module": 0, "chapter": 0, "authorized": True})
        with self.assertRaisesRegex(FederationError, "COMPONENT_NOT_MOUNTED"):
            self.federation.call("grokseek", "run", {})

    def test_unknown_root_and_duplicate_component_rejected(self):
        with self.assertRaisesRegex(FederationError, "UNSUPPORTED_COMPONENT_ROOT"):
            PinnedFederation.from_inventory(INVENTORY, roots={"UNKNOWN": str(REPOSITORY)})
        duplicate = json.loads(json.dumps(INVENTORY))
        duplicate["components"].append(duplicate["components"][0])
        with self.assertRaisesRegex(FederationError, "DUPLICATE_COMPONENT_ID"):
            PinnedFederation.from_inventory(duplicate, roots={"GF9_ROSETTA_R2": str(REPOSITORY)})

    def test_status_is_detached_and_public_metadata_only(self):
        status = self.federation.status()
        self.assertEqual(len(status["mounted_components"]), 2)
        self.assertNotIn(str(REPOSITORY), json.dumps(status))
        status["mounted_components"].clear()
        self.assertEqual(len(self.federation.status()["mounted_components"]), 2)

    def test_invalid_original_source_is_never_relabelled_synthetic(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "registry.json"
            source.write_text("{}")
            with PinnedFederation.from_inventory(INVENTORY, roots={"UNIFIED_ATLAS1728_PYTHON": str(REPOSITORY)}, registry_path=source) as federation:
                with self.assertRaisesRegex(FederationError, "UPSTREAM_DELEGATE_REJECTED"):
                    federation.call("unified", "source_status")


@unittest.skipUnless(os.environ.get("ATLAS_EXCELLENCE_ROOT") and os.environ.get("ATLAS_EXCELLENCE_PLAN"),
                     "Optional upstream checkout and compiled original program are explicitly configured")
class ExistingExcellenceDelegateTests(unittest.TestCase):
    def setUp(self):
        self.federation = PinnedFederation.from_inventory(INVENTORY,
            roots={"EXCELLENCE1728_CORE": os.environ["ATLAS_EXCELLENCE_ROOT"]},
            plan_path=os.environ["ATLAS_EXCELLENCE_PLAN"], expected_plan_sha256=PLAN_SHA)

    def tearDown(self):
        self.federation.close()

    def test_actual_program_validation_query_and_ready(self):
        status = self.federation.call("excellence", "plan_status")["result"]
        self.assertEqual(status["tasks"], 1728)
        self.assertEqual(status["completed_tasks"], 0)
        query = self.federation.call("excellence", "query", {"text": "memory", "limit": 3})["result"]
        self.assertGreater(query["total"], 0)
        self.assertLessEqual(len(query["tasks"]), 3)
        ready = self.federation.call("excellence", "ready", {"total_units": 36, "max_ready": 12})["result"]
        self.assertLessEqual(ready["estimated_work_units"], 12)
        self.assertFalse(ready["host_execution_authorized"])

    def test_actual_meta145_has_pending_source_perspectives(self):
        meta = self.federation.call("excellence", "meta145")["result"]
        self.assertEqual((len(meta["perspectives"]), len(meta["house_coverage"])), (144, 12))
        self.assertEqual(meta["verified_steps"], 0)
        self.assertEqual(meta["accepted_perspectives"], 0)
        sphere = self.federation.call("excellence", "perspective", {"sphere_id": "H12.S12"})["result"]
        self.assertEqual(sphere["status"], "PENDING_SOURCE_REVIEW")
        self.assertFalse(sphere["independent_resident_review"])

    def test_engineering_id_and_genuine_ledger_required(self):
        with self.assertRaisesRegex(FederationError, "ENGINEERING_ID_REQUIRED"):
            self.federation.call("excellence", "task", {"task_id": "H01.S01.N01"})
        with self.assertRaisesRegex(FederationError, "VERIFIED_ENGINEERING_LEDGER_REQUIRED"):
            self.federation.call("excellence", "review_perspective", {"sphere_id": "H01.S01", "task_ids": ["EX.W01.C01.P01"]})
        with self.assertRaisesRegex(FederationError, "GENUINE_PLAN_LEDGER_REQUIRED"):
            self.federation.bind_excellence_evidence({"verified": True})

    def test_actual_perspective_delegate_refuses_unverified_engineering_work(self):
        api, plan = self.federation._plan()
        policy = {"schema": "atlas.excellence.runner-policy.v1", "plan_sha256": PLAN_SHA,
                  "allowed_roots": [str(Path(os.environ["ATLAS_EXCELLENCE_ROOT"]).resolve())],
                  "source_paths": {}, "checks": []}
        runner = api.AcceptanceRunner(plan, policy, expected_policy_sha256=api.digest(policy), receipt_key=b"test-only-key-material-32-bytes!!")
        ledger = api.EvidenceLedger(plan, runner)
        self.federation.bind_excellence_evidence(ledger)
        with self.assertRaisesRegex(FederationError, "UPSTREAM_DELEGATE_REJECTED"):
            self.federation.call("excellence", "review_perspective", {"sphere_id": "H01.S01", "task_ids": ["EX.W01.C01.P01"]})
        self.assertEqual(self.federation.call("excellence", "meta145")["result"]["verified_steps"], 0)

    def test_plan_mutation_is_detected_before_return(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "plan.json"
            copy.write_bytes(Path(os.environ["ATLAS_EXCELLENCE_PLAN"]).read_bytes())
            with PinnedFederation.from_inventory(INVENTORY,
                    roots={"EXCELLENCE1728_CORE": os.environ["ATLAS_EXCELLENCE_ROOT"]},
                    plan_path=copy, expected_plan_sha256=PLAN_SHA) as federation:
                copy.write_bytes(copy.read_bytes() + b"\n")
                with self.assertRaisesRegex(FederationError, "PLAN_BYTES_CHANGED"):
                    federation.call("excellence", "plan_status")


if __name__ == "__main__":
    unittest.main()
