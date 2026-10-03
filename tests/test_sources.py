import json
import unittest

from prawo.sources import EliClient, SourceError, html_to_text, normalize_act, validate_eli


class SourcesTests(unittest.TestCase):
    def test_eli_path_rejects_arbitrary_urls_and_traversal(self):
        for value in ['http://localhost/secret', '../etc/passwd', 'DU/2026/2?redirect=x', 'DU/2026/2/../../', None]:
            with self.subTest(value=value), self.assertRaises(ValueError): validate_eli(value)
        self.assertEqual(validate_eli('MP/1946/0490096'), 'MP/1946/0490096')

    def test_search_uses_encoded_title_not_arbitrary_endpoint(self):
        urls = []
        def fetcher(url, **kwargs):
            urls.append(url)
            return json.dumps({'items':[], 'totalCount':0}).encode()
        result = EliClient(fetcher=fetcher).search('praca & limit=9999')
        self.assertEqual(result['total'], 0)
        self.assertIn('title=praca+%26+limit%3D9999', urls[0])
        self.assertIn('limit=20', urls[0])

    def test_malformed_source_fails_closed(self):
        for raw in [b'<html>error</html>', b'[]', b'{"items":[],"totalCount":"many"}']:
            with self.subTest(raw=raw), self.assertRaises(SourceError):
                EliClient(fetcher=lambda *args, **kwargs:raw).search('test')

    def test_source_status_is_not_temporal_validation(self):
        item = {'ELI':'DU/2020/1','title':'Przykładowy akt','inForce':'IN_FORCE','entryIntoForce':'2020-01-01'}
        self.assertFalse(normalize_act(item)['temporal_verified'])

    def test_detail_identity_mismatch_is_rejected(self):
        raw = json.dumps({'ELI':'DU/2020/2','title':'Inny akt'}).encode()
        with self.assertRaises(SourceError): EliClient(fetcher=lambda *a,**k:raw).details('DU/2020/1')

    def test_html_import_removes_script_and_retains_plain_text(self):
        raw = '<html><head><style>bad</style></head><body><p>Art. 1.</p><p>Treść &amp; treść.</p><script>alert(1)</script></body></html>'.encode()
        text = html_to_text(raw)
        self.assertIn('Art. 1.',text); self.assertIn('Treść & treść.',text)
        self.assertNotIn('alert',text); self.assertNotIn('bad',text)
