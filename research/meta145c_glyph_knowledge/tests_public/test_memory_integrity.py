"""Public, synthetic regressions for integrity, concurrent writes and checkpoints.

No original ontology, provider calls, host grants or protected histories are used.
The checkpoints here are retained by the test caller outside the mutable ledger.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src.knowledge import topic_view
from src.memory import LocalMemory, canonical, sha


COORDINATE = 'H01.S07.N12'
TOPIC = 'T10020'
PAYLOAD_FIELDS = ('event_id', 'mode', 'coordinate', 'topic_id', 'action',
                  'source_ref', 'source_digest', 'retract_event_id')


def event(event_id='note01', action='NOTE', **changes):
    return {'event_id': event_id, 'mode': 'WORK',
            'scope': 'SYNTHETIC_LOCAL_REVIEW', 'coordinate': COORDINATE,
            'topic_id': TOPIC, 'action': action,
            'source_ref': 'urn:atlas:synthetic:integrity-regression',
            'source_digest': 'a' * 64, **changes}


class _MemoryFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'memory.sqlite'
        self.memory = LocalMemory(self.path)

    def tearDown(self):
        self.memory.close()
        self.tmp.cleanup()

    def anchor(self):
        # Test-only trusted custody: captured before each deliberate mutation.
        v = self.memory.verify()
        self.assertEqual(v['status'], 'LOCAL_HASH_CHAIN_VERIFIED')
        return {'expected_tip': v['tip'], 'expected_count': v['count']}

    def batch(self, checkpoint, coordinates=None):
        return self.memory.verified_triage_batch(
            coordinates or [COORDINATE], **checkpoint)

    def rehash(self):
        previous = '0' * 64
        for row in self.memory.events():
            payload = {key: row[key] for key in PAYLOAD_FIELDS}
            stamp = sha(previous + '|' + canonical(payload))
            self.memory.db.execute(
                'UPDATE review_events SET prev_hash=?,event_hash=? WHERE seq=?',
                (previous, stamp, row['seq']))
            previous = stamp
        self.memory.db.commit()


class MemoryIntegrityTests(_MemoryFixture):
    def test_corruption_cannot_change_legacy_triage(self):
        changes = {'action': 'CHALLENGE', 'mode': 'PLAY',
                   'coordinate': 'H02.S01.N01', 'topic_id': 'T99999',
                   'source_ref': 'urn:atlas:synthetic:changed',
                   'source_digest': 'b' * 64, 'retract_event_id': 'fake01'}
        for column, value in changes.items():
            with self.subTest(column=column):
                self.memory.db.execute('DELETE FROM review_events')
                self.memory.db.commit()
                self.memory.append(event())
                self.memory.db.execute(
                    f'UPDATE review_events SET {column}=?', (value,))
                self.memory.db.commit()
                with self.assertRaisesRegex(ValueError, 'FAIL_CHAIN'):
                    self.memory.triage_delta(COORDINATE, TOPIC)

    def test_corrupted_chain_refuses_append_and_releases_transaction(self):
        self.memory.append(event())
        self.memory.db.execute("UPDATE review_events SET action='CHALLENGE'")
        self.memory.db.commit()
        before = self.memory.events()
        with self.assertRaisesRegex(ValueError, 'FAIL_CHAIN'):
            self.memory.append(event('note02'))
        self.assertEqual(self.memory.events(), before)
        self.assertFalse(self.memory.db.in_transaction)

    def test_missing_middle_event_rejected_by_both_read_paths(self):
        for index in range(3):
            self.memory.append(event(f'note0{index}'))
        checkpoint = self.anchor()
        self.memory.db.execute('DELETE FROM review_events WHERE seq=2')
        self.memory.db.commit()
        with self.assertRaises(ValueError):
            self.memory.triage_delta(COORDINATE, TOPIC)
        with self.assertRaisesRegex(ValueError, 'FAIL_CHAIN'):
            self.batch(checkpoint)

    def test_concurrent_writers_preserve_one_chain(self):
        # The barrier deterministically exposes the old read-before-lock race.
        # Correct code obtains BEGIN IMMEDIATE before this shared snapshot read.
        barrier = Barrier(4)

        class SynchronizedMemory(LocalMemory):
            synchronized = False

            def events(local):
                rows = super(SynchronizedMemory, local).events()
                if not local.db.in_transaction and not local.synchronized:
                    local.synchronized = True
                    barrier.wait(timeout=10)
                return rows

        def writer(index):
            memory = SynchronizedMemory(self.path)
            try:
                return memory.append(event(f'writer{index}'))
            finally:
                memory.close()

        with ThreadPoolExecutor(max_workers=4) as pool:
            receipts = list(pool.map(writer, range(4)))
        self.assertEqual(len(receipts), 4)
        result = self.memory.verify()
        self.assertEqual(result['status'], 'LOCAL_HASH_CHAIN_VERIFIED')
        self.assertEqual(result['count'], 4)
        self.assertEqual(self.memory.triage_delta(COORDINATE, TOPIC), 4)

    def test_failed_insert_rolls_back_and_next_connection_can_write(self):
        self.memory.db.execute("CREATE TRIGGER reject_bad BEFORE INSERT ON review_events "
                               "WHEN NEW.event_id='reject01' BEGIN SELECT RAISE(ABORT,'fixture'); END")
        self.memory.db.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.memory.append(event('reject01'))
        self.assertFalse(self.memory.db.in_transaction)
        other = LocalMemory(self.path)
        try:
            other.append(event('accept01'))
        finally:
            other.close()
        self.assertEqual(self.memory.verify()['count'], 1)

    def test_append_does_not_commit_callers_unrelated_transaction(self):
        self.memory.db.execute('CREATE TABLE caller_data(value TEXT)')
        self.memory.db.execute("INSERT INTO caller_data VALUES('pending')")
        with self.assertRaisesRegex(ValueError, 'TRANSACTION_ALREADY_ACTIVE'):
            self.memory.append(event())
        self.assertTrue(self.memory.db.in_transaction)
        self.memory.db.rollback()
        self.assertEqual(self.memory.db.execute('SELECT COUNT(*) FROM caller_data').fetchone()[0], 0)
        self.assertEqual(self.memory.events(), [])

    def test_rehashed_private_mode_is_not_work_evidence(self):
        self.memory.append(event())
        self.memory.db.execute("UPDATE review_events SET mode='PALACE'")
        self.memory.db.commit()
        self.rehash()
        self.assertNotEqual(self.memory.verify()['status'], 'LOCAL_HASH_CHAIN_VERIFIED')
        with self.assertRaises(ValueError):
            self.memory.triage_delta(COORDINATE, TOPIC)

    def test_rehashed_invalid_source_is_rejected(self):
        self.memory.append(event())
        self.memory.db.execute("UPDATE review_events SET source_ref='file:///private'")
        self.memory.db.commit()
        self.rehash()
        with self.assertRaises(ValueError):
            self.memory.triage_delta(COORDINATE, TOPIC)

    def test_rehashed_retraction_cannot_change_another_topic(self):
        self.memory.append(event())
        self.memory.append(event('retract01', 'RETRACT', retract_event_id='note01'))
        self.memory.db.execute("UPDATE review_events SET topic_id='T99999' WHERE action='RETRACT'")
        self.memory.db.commit()
        self.rehash()
        with self.assertRaises(ValueError):
            self.memory.triage_delta(COORDINATE, TOPIC)

    def test_trusted_checkpoint_detects_tail_truncation(self):
        self.memory.append(event())
        self.memory.append(event('note02'))
        checkpoint = self.anchor()
        self.memory.db.execute('DELETE FROM review_events WHERE seq=2')
        self.memory.db.commit()
        # An unanchored self-hash cannot detect deletion of a valid suffix.
        self.assertEqual(self.memory.verify()['status'], 'LOCAL_HASH_CHAIN_VERIFIED')
        with self.assertRaisesRegex(ValueError, 'CHECKPOINT_CHANGED'):
            self.batch(checkpoint)

    def test_trusted_checkpoint_detects_complete_deletion(self):
        self.memory.append(event())
        checkpoint = self.anchor()
        self.memory.db.execute('DELETE FROM review_events')
        self.memory.db.commit()
        with self.assertRaisesRegex(ValueError, 'CHECKPOINT_CHANGED'):
            self.batch(checkpoint)

    def test_trusted_checkpoint_detects_rehashed_rewrite(self):
        self.memory.append(event())
        checkpoint = self.anchor()
        self.memory.db.execute("UPDATE review_events SET action='CHALLENGE'")
        self.memory.db.commit()
        self.rehash()
        with self.assertRaisesRegex(ValueError, 'CHECKPOINT_CHANGED'):
            self.batch(checkpoint)

    def test_stale_checkpoint_refuses_newer_snapshot(self):
        checkpoint = self.anchor()
        self.memory.append(event())
        with self.assertRaisesRegex(ValueError, 'CHECKPOINT_CHANGED'):
            self.batch(checkpoint)

    def test_checkpoint_bound_append_rejects_rollback_without_mutation(self):
        self.memory.append(event())
        checkpoint = self.anchor()
        self.memory.db.execute('DELETE FROM review_events')
        self.memory.db.commit()
        with self.assertRaisesRegex(ValueError, 'CHECKPOINT_CHANGED'):
            self.memory.append(event('note02'), **checkpoint)
        self.assertEqual(self.memory.events(), [])
        self.assertFalse(self.memory.db.in_transaction)

    def test_append_receipt_advances_external_checkpoint(self):
        checkpoint = {'expected_tip': '0' * 64, 'expected_count': 0}
        receipt = self.memory.append(event(), **checkpoint)
        checkpoint = {'expected_tip': receipt['event_hash'], 'expected_count': receipt['count']}
        self.assertEqual(self.batch(checkpoint), {COORDINATE: {TOPIC: 1}})
        self.memory.close()
        self.memory = LocalMemory(self.path)
        self.assertEqual(self.batch(checkpoint), {COORDINATE: {TOPIC: 1}})

    def test_batch_retraction_and_all_coordinate_output_parity(self):
        coordinates = [f'H{h:02d}.S{s:02d}.N{n:02d}' for h in range(1, 13)
                       for s in range(1, 13) for n in range(1, 13)]
        self.memory.append(event())
        self.memory.append(event('chall01', 'CHALLENGE', topic_id='T10021'))
        self.memory.append(event('plain01', topic_id=None))
        self.memory.append(event('retract01', 'RETRACT', retract_event_id='note01'))
        checkpoint = self.anchor()
        actual = self.batch(checkpoint, coordinates)
        self.assertEqual(len(actual), 1728)
        self.assertEqual(actual[COORDINATE], {'T10021': -1, None: 1})
        for coordinate in coordinates:
            for topic in (TOPIC, 'T10021', None):
                self.assertEqual(actual[coordinate].get(topic, 0),
                                 self.memory.triage_delta(coordinate, topic))

    def test_batch_verifies_the_exact_snapshot_it_uses(self):
        self.memory.append(event())
        checkpoint = self.anchor()
        original = self.memory.events
        calls = []

        def one_snapshot():
            calls.append(1)
            rows = original()
            if len(calls) == 1:
                self.memory.db.execute("UPDATE review_events SET action='CHALLENGE'")
                self.memory.db.commit()
            return rows

        with patch.object(self.memory, 'events', one_snapshot):
            self.assertEqual(self.batch(checkpoint), {COORDINATE: {TOPIC: 1}})
        self.assertEqual(len(calls), 1)
        with self.assertRaisesRegex(ValueError, 'FAIL_CHAIN'):
            self.batch(checkpoint)

    def test_invalid_checkpoint_and_batch_shapes_fail_closed(self):
        empty = self.anchor()
        invalid = [dict(empty, expected_tip='bad'), dict(empty, expected_count=True),
                   dict(empty, expected_count=-1), dict(empty, expected_tip=None)]
        for checkpoint in invalid:
            with self.subTest(checkpoint=checkpoint), self.assertRaisesRegex(ValueError, 'CHECKPOINT_INVALID'):
                self.batch(checkpoint)
        for coordinates in ([], [COORDINATE] * 2, ['GF7.B01.M07.C12'], [COORDINATE] * 1729, COORDINATE):
            with self.subTest(coordinates=coordinates[:2]), self.assertRaises(ValueError):
                self.memory.verified_triage_batch(coordinates, **empty)


class TopicViewCheckpointTests(_MemoryFixture):
    def setUp(self):
        super().setUp()
        self.db = sqlite3.connect(':memory:')
        self.db.executescript('CREATE TABLE topics(id TEXT,label TEXT,original_status TEXT);'
                             'CREATE TABLE topic_candidates(topic_id TEXT,hsn TEXT,rank INTEGER);')
        self.db.executemany('INSERT INTO topics VALUES(?,?,?)',
                            [(TOPIC, 'primary', 'UNREVIEWED'), ('T10021', 'alternate', 'UNREVIEWED')])
        self.db.executemany('INSERT INTO topic_candidates VALUES(?,?,?)',
                            [(TOPIC, COORDINATE, 1), ('T10021', COORDINATE, 2)])

    def tearDown(self):
        self.db.close()
        super().tearDown()

    def test_topic_consumer_requires_external_checkpoint(self):
        with self.assertRaisesRegex(ValueError, 'CHECKPOINT_REQUIRED'):
            topic_view(self.db, COORDINATE, self.memory)

    def test_topic_consumer_uses_one_verified_batch(self):
        self.memory.append(event(topic_id='T10021'))
        checkpoint = self.anchor()
        with patch.object(self.memory, 'triage_delta', side_effect=AssertionError('legacy path used')), \
             patch.object(self.memory, 'events', wraps=self.memory.events) as read:
            result = topic_view(self.db, COORDINATE, self.memory, memory_checkpoint=checkpoint)
        self.assertEqual(read.call_count, 1)
        self.assertEqual(result['items'][0]['topic_id'], 'T10021')
        self.assertEqual(result['memory_integrity'], 'CALLER_CHECKPOINT_MATCHED_LOCAL_SNAPSHOT')
        self.assertFalse(result['hosted_verified'])
        self.assertFalse(result['semantic_equivalence_approved'])

    def test_topic_consumer_discloses_no_page_on_stale_checkpoint(self):
        checkpoint = self.anchor()
        self.memory.append(event())
        with self.assertRaisesRegex(ValueError, 'CHECKPOINT_CHANGED'):
            topic_view(self.db, COORDINATE, self.memory, memory_checkpoint=checkpoint)

    def test_topic_without_memory_preserves_original_order(self):
        result = topic_view(self.db, COORDINATE)
        self.assertEqual([x['topic_id'] for x in result['items']], [TOPIC, 'T10021'])
        self.assertFalse(result['triage_memory_used'])


if __name__ == '__main__':
    unittest.main()
