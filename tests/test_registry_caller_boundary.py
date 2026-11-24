"""Offline registry boundary controls using only synthetic public metadata."""
import unittest

from registry.public_registry import (
    RegistryError, _snapshot_catalog, lookup_public_repo, route_public_issue,
    validate_catalog,
)
from test_snapshot_calendar_date import synthetic_catalog


class RegistryCallerBoundaryTests(unittest.TestCase):
    def test_behavioral_scalar_cannot_replace_a_validated_pointer(self):
        catalog = synthetic_catalog()
        record = catalog['records'][0]
        calls = []

        class MutatingVisibility(str):
            def __eq__(self, other):
                calls.append(other)
                record['url'] = 'https://example.invalid/synthetic-unreviewed-pointer'
                return super().__eq__(other)

        record['visibility'] = MutatingVisibility('public')
        with self.assertRaisesRegex(RegistryError, '^CATALOG_NON_JSON_VALUE$'):
            lookup_public_repo(catalog, record['repo_full_name'])
        self.assertEqual(calls, [])
        self.assertEqual(record['url'],
                         'https://github.com/atlaslattice/synthetic-fixture-repo')

    def test_plain_metadata_lookup_and_route_keep_source_only_status(self):
        catalog = synthetic_catalog()
        pointer = lookup_public_repo(catalog, 'atlaslattice/synthetic-fixture-repo')
        self.assertEqual(pointer['url'],
                         'https://github.com/atlaslattice/synthetic-fixture-repo')
        self.assertEqual(pointer['rights_to_content_or_deploy'], 'NONE')
        route = route_public_issue(catalog,
            'https://github.com/atlaslattice/synthetic-fixture-repo/issues/123')
        self.assertEqual(route['resource_number'], 123)
        self.assertEqual(route['resource_existence'], 'NOT_CHECKED')
        self.assertIs(route['can_close_or_merge'], False)

    def test_summary_cannot_mutate_original_source_pages(self):
        catalog = synthetic_catalog()
        summary = validate_catalog(catalog)
        summary['source_pages'].append(99)
        summary['source_page_lengths'][0] = 99
        self.assertEqual(catalog['source_pages'], [1, 2])
        self.assertEqual(catalog['source_page_lengths'], [1, 0])

    def test_caller_edits_cannot_change_an_already_returned_summary(self):
        catalog = synthetic_catalog()
        summary = validate_catalog(catalog)
        catalog['source_pages'].append(99)
        catalog['source_page_lengths'][0] = 99
        self.assertEqual(summary['source_pages'], [1, 2])
        self.assertEqual(summary['source_page_lengths'], [1, 0])

    def test_scalar_container_and_key_subclasses_fail_closed(self):
        class CallerString(str):
            pass
        class CallerList(list):
            pass
        class CallerDict(dict):
            pass
        class CallerInteger(int):
            pass

        cases = []
        catalog = synthetic_catalog(); catalog['source'] = CallerString('synthetic:source'); cases.append(catalog)
        catalog = synthetic_catalog(); catalog['notes'] = CallerList(['synthetic']); cases.append(catalog)
        catalog = synthetic_catalog(); catalog['records'][0] = CallerDict(catalog['records'][0]); cases.append(catalog)
        catalog = synthetic_catalog(); catalog['source_pages'][0] = CallerInteger(1); cases.append(catalog)
        catalog = synthetic_catalog(); catalog[CallerString('schema')] = catalog.pop('schema'); cases.append(catalog)
        catalog = synthetic_catalog(); catalog['source'] = object(); cases.append(catalog)
        for index, catalog in enumerate(cases):
            with self.subTest(case=index), self.assertRaisesRegex(RegistryError, '^CATALOG_NON_JSON_VALUE$'):
                validate_catalog(catalog)

    def test_cyclic_python_input_is_a_bounded_hold(self):
        catalog = synthetic_catalog()
        catalog['notes'].append(catalog)
        with self.assertRaisesRegex(RegistryError, '^CATALOG_CYCLIC_VALUE$'):
            validate_catalog(catalog)

    def test_shared_list_and_dict_graphs_stay_small_and_detached(self):
        def container_ids(value):
            pending, seen = [value], set()
            while pending:
                item = pending.pop()
                if type(item) not in (list, dict) or id(item) in seen:
                    continue
                seen.add(id(item))
                pending.extend(item if type(item) is list else item.values())
            return seen

        for kind in ('list', 'dict'):
            with self.subTest(kind=kind):
                leaf = {'note': 'synthetic'}
                shared = leaf
                for _ in range(12):
                    shared = ([shared, shared] if kind == 'list'
                              else {'left': shared, 'right': shared})
                catalog = synthetic_catalog()
                catalog['notes'] = shared
                owned = _snapshot_catalog(catalog)
                original_ids = container_ids(catalog)
                owned_ids = container_ids(owned)
                self.assertEqual(len(owned_ids), len(original_ids))
                self.assertTrue(original_ids.isdisjoint(owned_ids))
                copied_leaf = owned['notes']
                for _ in range(12):
                    if kind == 'list':
                        self.assertIs(copied_leaf[0], copied_leaf[1])
                        copied_leaf = copied_leaf[0]
                    else:
                        self.assertIs(copied_leaf['left'], copied_leaf['right'])
                        copied_leaf = copied_leaf['left']
                copied_leaf['note'] = 'owned-only'
                self.assertEqual(leaf['note'], 'synthetic')
                with self.assertRaisesRegex(RegistryError, '^SOURCE_NOTES_INVALID$'):
                    validate_catalog(catalog)

    def test_deep_python_input_is_a_structured_hold(self):
        catalog = synthetic_catalog()
        value = []
        for _ in range(2000):
            value = [value]
        catalog['notes'] = value
        with self.assertRaisesRegex(RegistryError, '^CATALOG_NESTING_TOO_DEEP$'):
            validate_catalog(catalog)

    def test_non_ascii_issue_digits_do_not_alias_an_ascii_resource(self):
        for digits in ('１２３', '١٢٣', '१२३', '1２3'):
            with self.subTest(digits=digits), self.assertRaisesRegex(RegistryError, '^INVALID_PUBLIC_LINK$'):
                route_public_issue(synthetic_catalog(),
                    'https://github.com/atlaslattice/synthetic-fixture-repo/issues/' + digits)

    def test_ascii_issue_digit_bounds_are_preserved(self):
        root = 'https://github.com/atlaslattice/synthetic-fixture-repo/pull/'
        for digits in ('1', '999999999999'):
            with self.subTest(digits=digits):
                route = route_public_issue(synthetic_catalog(), root + digits)
                self.assertEqual(route['resource_number'], int(digits))
                self.assertEqual(route['resource_type'], 'PR')
        for digits in ('0', '1000000000000'):
            with self.subTest(digits=digits), self.assertRaisesRegex(RegistryError, '^INVALID_PUBLIC_LINK$'):
                route_public_issue(synthetic_catalog(), root + digits)


if __name__ == '__main__':
    unittest.main()
