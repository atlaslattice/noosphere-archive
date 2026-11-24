"""Replay the focused integrity suite against current or explicitly pinned source.

Use --source-file only with the reviewed historical reasoning_filter.py whose
Git blob is recorded in GF8_CLAIM_REGRESSION.md. This is a local test runner.
"""
from pathlib import Path
import argparse
import importlib.util
import sys
import unittest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-file', type=Path)
    args = parser.parse_args()
    package = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(package))
    if args.source_file is not None:
        spec = importlib.util.spec_from_file_location('src.reasoning_filter', args.source_file)
        if spec is None or spec.loader is None:
            parser.error('Unable to load the supplied historical source file')
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.discover(
        str(package / 'tests'), pattern='test_reasoning_filter_integrity.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
