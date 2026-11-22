"""Source-only regression tests; no network access, private data or host grants."""
import unittest

from children.specialty_passport_v01 import (
    ProfileError, _source_ref, match_task, synthesis_routing,
)

NOW = '2026-11-22T00:00:00Z'


class PublicPointerBoundaryTests(unittest.TestCase):
    def assert_pointer_denied(self, values):
        for url in values:
            with self.subTest(url=repr(url)):
                with self.assertRaises(ProfileError):
                    _source_ref(url)

    def test_public_dns_https_still_accepted(self):
        for url in (
            'https://example.org/public-document',
            'https://openalex.org/W123',
            'https://arxiv.org/abs/2601.12345',
            'https://example.org:443/review',
        ):
            with self.subTest(url=url):
                self.assertIsNone(_source_ref(url))

    def test_private_local_ip_or_metadata_pointer_rejected(self):
        self.assert_pointer_denied((
            'https://localhost/secret',
            'https://127.0.0.1/x',
            'https://169.254.169.254/latest/meta-data/',
            'https://[::1]/',
            'https://0x7f000001/x',
            'https://metadata.internal/',
            'https://x.local/',
            'https://myserver/',
            'https://x.onion/path',
            'https://example.org:8443/path',
        ))

    def test_control_chars_rejected_before_urlsplit(self):
        self.assert_pointer_denied((
            'https://example.org/a\nb',
            'https://example.org/a\tb',
            'https://example.org/\x00',
            'https://example.org/\x7f',
        ))

    def test_malformed_host_or_port_is_domain_error(self):
        self.assert_pointer_denied((
            'https://[malformed/',
            'https://example.org:badport/x',
            'https://example.org:65536/x',
            'https://[::1',
            'https://bad_host.org/x',
            'https://example.org./x',
        ))

    def test_credentials_query_fragment_and_empty_markers_rejected(self):
        self.assert_pointer_denied((
            'https://user:pass@example.org/path',
            'https://example.org/path?token=secret',
            'https://example.org/path#frag',
            'https://example.org/path?',
            'https://example.org/path#',
        ))

    def test_nonstring_source_pointer_fails_closed(self):
        self.assert_pointer_denied((
            {'url': 'https://example.org'},
            ['https://example.org'],
            None, 42,
        ))

    def test_unhashable_task_kind_raises_profile_error(self):
        for value in ([], {}, None, True, 3):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ProfileError):
                    match_task([], 'H01.S01.N01', value, NOW)

    def test_valid_task_kind_behavior_remains_candidate_only(self):
        for task_kind in ('review', 'build', 'research', 'teach', 'synthesize'):
            with self.subTest(task_kind=task_kind):
                result = match_task([], 'H01.S01.N01', task_kind, NOW)
                self.assertEqual(result['status'], 'HOLD_NO_OPTED_IN_SPECIALIST')
                self.assertTrue(result['no_work_performed'])

    def test_required_nonlist_or_unhashable_raises_profile_error(self):
        for required in (
            [['H01.S01.N01']], [{'h': 'H01.S01.N01'}],
            'H01.S01.N01', {}, [], [None], [False],
            ['H01.S01.N01', 'H01.S01.N01'],
        ):
            with self.subTest(required=repr(required)):
                with self.assertRaises(ProfileError):
                    synthesis_routing([], required, 'review', NOW)

    def test_valid_distinct_required_remains_unfilled(self):
        result = synthesis_routing([], ['H01.S01.N01', 'H02.S02.N02'], 'review', NOW)
        self.assertEqual(result['status'], 'HOLD_UNFILLED_ROLES')
        self.assertEqual(result['resident_identities_verified'], 0)
        self.assertEqual(result['specialists_actually_called'], 0)


if __name__ == '__main__':
    unittest.main()
