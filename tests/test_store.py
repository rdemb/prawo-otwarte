import hashlib
import tempfile
import unittest

from prawo.store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.item = {'ELI':'DU/2020/1','title':'Testowa ustawa o pracy','changeDate':'2020-01-01T00:00:00','status':'obowiązujący'}
        self.url = 'https://api.sejm.gov.pl/eli/acts/DU/2020/1'

    def test_idempotency_and_exact_source_hash(self):
        for _ in range(2): self.store.upsert(self.item,source_url=self.url)
        raw = b'<p>Unique statutory text with enough characters</p>'
        self.store.set_text(self.item['ELI'],'Unique statutory text',raw,self.url+'/text.html')
        self.assertEqual(self.store.status()['metadata_count'],1)
        self.assertEqual(self.store.status()['text_count'],1)
        snapshots = self.store.get(self.item['ELI'])['snapshots']
        self.assertEqual(len(snapshots),2)
        self.assertIn(hashlib.sha256(raw).hexdigest(),[s['sha256'] for s in snapshots])
        self.assertFalse(self.store.status()['complete_polish_law'])

    def test_metadata_change_invalidates_text_index_but_preserves_snapshot(self):
        self.store.upsert(self.item,source_url=self.url)
        self.store.set_text(self.item['ELI'],'uniquehistoricalterm',b'original body',self.url)
        self.assertEqual(len(self.store.search('uniquehistoricalterm')),1)
        changed = dict(self.item,changeDate='2026-01-01T00:00:00')
        self.store.upsert(changed,source_url=self.url)
        self.assertEqual(self.store.search('uniquehistoricalterm'),[])
        self.assertEqual(self.store.status()['text_count'],0)
        record = self.store.get(self.item['ELI'])
        self.assertTrue(record['text_stale'])
        self.assertEqual(record['text'],'uniquehistoricalterm')
        self.assertEqual(len(record['snapshots']),3)
        self.store.set_text(self.item['ELI'],'freshterm',b'updated body',self.url)
        self.assertEqual(len(self.store.search('freshterm')),1)

    def test_search_does_not_execute_fts_or_sql_operators(self):
        self.store.upsert(self.item,source_url=self.url)
        for query in ['" OR * --', 'NOT () NEAR', "'); DROP TABLE acts; --", '***']:
            self.store.search(query)
        self.assertEqual(self.store.status()['metadata_count'],1)
        self.assertEqual(len(self.store.search('ustawa pracy')),1)

    def test_checkpoint_is_scope_specific(self):
        self.store.checkpoint('DU/2025',100,201,False)
        self.assertEqual(self.store.offset('DU/2025'),100)
        self.assertEqual(self.store.offset('MP/2025'),0)
