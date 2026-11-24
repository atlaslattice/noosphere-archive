"""CLI/package integration regression; only synthetic and public metadata inputs."""
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RegistryModuleExecutionTests(unittest.TestCase):
    def run_cli(self, *args):
        optimize = ["-O"] if sys.flags.optimize else []
        return subprocess.run(
            [sys.executable, *optimize, "-W", "error", "-m", "registry.public_registry", *args],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )

    def test_warning_strict_cli_accepts_public_snapshot(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        summary = json.loads(result.stdout)
        self.assertEqual(summary["record_count"], 272)
        self.assertEqual(summary["host_or_canon_authority"], "NONE")

    def test_warning_strict_cli_holds_invalid_synthetic_input(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic_invalid_catalog.json"
            path.write_text("{}", encoding="utf-8")
            result = self.run_cli("--input", str(path))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stderr, "")
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["status"], "HOLD")
        self.assertIn("CATALOG_FIELDS_UNEXPECTED_OR_MISSING", receipt["reason"])
        self.assertNotIn(str(path), result.stdout)

    def test_public_package_exports_preserve_object_identity(self):
        import registry
        from registry import validate_catalog, lookup_public_repo, route_public_issue, RegistryError
        implementation = importlib.import_module("registry.public_registry")
        names = ["validate_catalog", "lookup_public_repo", "route_public_issue", "RegistryError"]
        self.assertEqual(registry.__all__, names)
        imported = [validate_catalog, lookup_public_repo, route_public_issue, RegistryError]
        for name, value in zip(names, imported):
            with self.subTest(name=name):
                self.assertIs(getattr(registry, name), getattr(implementation, name))
                self.assertIs(value, getattr(implementation, name))
        with self.assertRaises(AttributeError):
            getattr(registry, "nonexistent_public_registry_attribute")


if __name__ == "__main__":
    unittest.main()
