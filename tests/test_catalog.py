import json
import tempfile
import unittest
from prawo.catalog import sync_catalog
from prawo.sources import EliClient, SourceError
from prawo.store import Store


def item(eli):
    return {'ELI':eli,'title':'Synthetic metadata fixture','changeDate':'2026-01-01'}


class Client:
    def __init__(self):
        self.calls=[]
        self.pages={('DU',2026,0):[item('DU/2026/1')],('DU',2026,1):[item('DU/2026/2')],
                    ('MP',2025,0):[item('MP/2025/1')]}
    def publishers(self):
        return {'publishers':[{'publisher':'DU','years':[2026],'reported_total':2},
                              {'publisher':'MP','years':[2025],'reported_total':1}]}
    def search(self, *, publisher,year,offset,limit):
        key=(publisher,year,offset);self.calls.append(key)
        return {'items':self.pages.get(key,[]),'total':2 if publisher=='DU' else 1,'url':'https://api.sejm.gov.pl/eli/acts/search'}


class CatalogTests(unittest.TestCase):
    def test_bound_resume_and_completed_scopes_do_not_generate_answer_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);client=Client();pauses=[]
            first=list(sync_catalog(store,client,max_pages=1,sleep=pauses.append))
            self.assertFalse(first[-1]['enumeration_finished']);self.assertEqual(len(client.calls),1)
            second=list(sync_catalog(store,client,max_pages=2,sleep=pauses.append))
            self.assertEqual(client.calls,[('DU',2026,0),('DU',2026,1),('MP',2025,0)])
            self.assertTrue(all(row['enumeration_finished'] for row in second))
            self.assertEqual(list(sync_catalog(store,client,sleep=pauses.append)),[])
            self.assertEqual(store.status()['metadata_count'],3)
            self.assertEqual(store.status()['answer_source_count'],0)
            self.assertFalse(store.status()['complete_polish_law'])

    def test_moving_pages_cannot_claim_complete_catalog(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);client=Client();client.pages[('DU',2026,1)]=[item('DU/2026/1')]
            with self.assertRaises(SourceError):list(sync_catalog(store,client,sleep=lambda _:None))
            self.assertFalse(store.status()['imports'][0]['completed'])

    def test_wrong_scope_does_not_advance_checkpoint_or_write_items(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);client=Client();client.pages[('DU',2026,0)]=[item('MP/2025/1')]
            with self.assertRaises(SourceError):list(sync_catalog(store,client,sleep=lambda _:None))
            self.assertEqual(store.offset('DU/2026'),0);self.assertEqual(store.status()['metadata_count'],0)

    def test_discovery_uses_official_years_and_rejects_missing_publisher(self):
        data=[{'code':'DU','years':[1918,2026,1918],'actsCount':2}, {'code':'MP','years':[1930],'actsCount':1}]
        def fetch(url,**kwargs):
            self.assertEqual(url,'https://api.sejm.gov.pl/eli/acts');return json.dumps(data).encode()
        self.assertEqual(EliClient(fetcher=fetch).publishers()['publishers'][0]['years'],[2026,1918])
        data.pop()
        with self.assertRaises(SourceError):EliClient(fetcher=fetch).publishers()
