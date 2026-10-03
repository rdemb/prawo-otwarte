import io
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from prawo.cases import BasalRouter, DOMAINS
from prawo.settings import Settings
from prawo.sources import SourceError
from prawo.web import App


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.settings = Settings(Path(self.temp.name),allow_eli=False)
        self.app = App(self.settings)

    def call(self,path,body=None,**overrides):
        raw = json.dumps(body).encode() if body is not None else b''
        env = {'PATH_INFO':path, 'REQUEST_METHOD':'POST' if body is not None else 'GET',
               'CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(raw)), 'wsgi.input':io.BytesIO(raw),
               'REMOTE_ADDR':'127.0.0.1','HTTP_HOST':'localhost:8080'}
        env.update(overrides); received = []
        output = b''.join(self.app(env,lambda status,headers:received.append((status,dict(headers)))))
        status,headers = received[0]
        return int(status.split()[0]),headers,json.loads(output) if 'application/json' in headers['Content-Type'] else output

    def test_missing_model_degrades_without_a_legal_answer(self):
        secret = 'CONFIDENTIAL_EXAMPLE_5874: umowa została wypowiedziana.'
        code,_,data = self.call('/api/intake',{'description':secret,'domain':'unknown','event_date':'2024-01-01'})
        self.assertEqual(code,200); self.assertEqual(data['routing']['method'],'unavailable')
        self.assertIsNone(data['legal_answer']); self.assertFalse(data['temporal_verified'])
        self.assertNotIn(secret,json.dumps(data))
        for path in Path(self.temp.name).rglob('*'):
            if path.is_file(): self.assertNotIn(secret.encode(),path.read_bytes())

    def test_manual_intake_never_calls_model(self):
        self.app.router.classify = lambda _:self.fail('Unexpected model call')
        code,_,data = self.call('/api/intake',{'description':'Mam pytanie o umowę o pracę i datę doręczenia.','domain':'work'})
        self.assertEqual(code,200); self.assertEqual(data['routing']['method'],'user')

    def test_disabled_source_returns_unavailable_not_fake_results(self):
        code,_,data = self.call('/api/search',{'query':'Kodeks pracy','mode':'eli'})
        self.assertEqual(code,503); self.assertNotIn('items',data)

    def test_source_outage_is_explicit(self):
        self.app.settings = replace(self.settings,allow_eli=True)
        def fail(*a,**k): raise SourceError('unavailable')
        self.app.eli.search = fail
        self.assertEqual(self.call('/api/search',{'query':'Kodeks','mode':'eli'})[0],503)

    def test_path_traversal_and_sensitive_paths_not_served(self):
        for path in ['/../../etc/passwd','/.env','/data/catalog.sqlite3','/AGENTS.md','/api/admin/delete']:
            self.assertEqual(self.call(path)[0],404)

    def test_cross_origin_request_rejected(self):
        self.assertEqual(self.call('/api/intake',{},HTTP_ORIGIN='https://evil.example')[0],403)

    def test_input_validation(self):
        for payload in [{'query':'x'}, {'query':'x'*161}, {'query':[]}, {'query':'test','mode':'unknown'}]:
            self.assertEqual(self.call('/api/search',payload)[0],400)
        self.assertEqual(self.call('/api/intake',{'description':'a'*30,'event_date':'9999-01-01'})[0],400)
        self.assertEqual(self.call('/api/search',{},CONTENT_LENGTH='20000')[0],400)

    def test_headers_and_empty_coverage_are_truthful(self):
        code,headers,data = self.call('/api/status')
        self.assertEqual(code,200); self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        self.assertEqual(data['corpus']['metadata_count'],0)
        self.assertFalse(data['generative_answers']); self.assertFalse(data['basal']['verified_live'])

    def test_rate_limit(self):
        codes = [self.call('/api/status')[0] for _ in range(31)]
        self.assertEqual(codes[-1],429)

    def test_search_filters_and_pagination_reach_official_client(self):
        self.app.settings = replace(self.settings,allow_eli=True)
        calls = []
        def search(query,**filters):
            calls.append((query,filters))
            return {'items':[], 'total':100,'fetched_at':'2026-10-03T00:00:00Z'}
        self.app.eli.search = search
        code,_,data = self.call('/api/search',{'query':'Kodeks','mode':'eli','publisher':'DU','year':'2025','offset':20})
        self.assertEqual(code,200); self.assertEqual(data['offset'],20)
        self.assertEqual(calls,[('Kodeks',{'publisher':'DU','year':2025,'offset':20,'limit':20})])
        self.assertFalse(data['temporal_verified'])

    def test_invalid_source_filters_never_reach_official_client(self):
        self.app.settings = replace(self.settings,allow_eli=True)
        self.app.eli.search = lambda *a,**k:self.fail('Invalid filter reached source')
        for values in [{'publisher':'XX'},{'year':True},{'year':[]},{'year':'9999'},{'offset':-1},{'offset':True}]:
            self.assertEqual(self.call('/api/search',{'query':'Kodeks','mode':'eli',**values})[0],400)


class BasalTests(unittest.TestCase):
    def router(self, raw):
        return BasalRouter(Settings(Path('.'),basal_enabled=True),fetcher=lambda *a,**k:raw)

    def response(self, probabilities, choice='work'):
        return json.dumps({'answers':{'domain':{'choice':choice,'probabilities':probabilities}}}).encode()

    def test_correct_contract_routes(self):
        probs = {key:0 for key in DOMAINS}; probs['work']=1
        result = self.router(self.response(probs)).classify('opis')
        self.assertEqual(result['domain'],'work'); self.assertEqual(result['method'],'basal')

    def test_uncertain_model_abstains(self):
        probs = {key:1/len(DOMAINS) for key in DOMAINS}
        self.assertEqual(self.router(self.response(probs)).classify('opis')['method'],'basal_abstained')

    def test_invalid_output_and_nan_fail_closed(self):
        probs = {key:0 for key in DOMAINS}; probs['work']=float('nan')
        for raw in [b'{}',b'not json',self.response(probs),self.response({'work':1}),self.response({k:0 for k in DOMAINS})]:
            self.assertEqual(self.router(raw).classify('opis')['method'],'unavailable')

    def test_model_busy_does_not_queue_unbounded_work(self):
        router = self.router(b'{}'); router.slot.acquire()
        try: self.assertEqual(router.classify('opis')['method'],'unavailable')
        finally: router.slot.release()

    def test_model_url_cannot_be_remote_or_include_credentials(self):
        for url in ['https://api.example.com','http://localhost:8766','http://127.0.0.1.evil.com','http://user:pass@127.0.0.1:8766','http://127.0.0.1:8766/other']:
            with self.subTest(url=url),self.assertRaises(ValueError): BasalRouter(Settings(Path('.'),basal_url=url))

    def test_model_timeout_stays_within_browser_budget(self):
        for timeout in [0, -1, 31, float('inf'), float('nan')]:
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                BasalRouter(Settings(Path('.'), basal_timeout=timeout))
        self.assertEqual(BasalRouter(Settings(Path('.'), basal_timeout=30)).settings.basal_timeout, 30)

    def test_timeout_returns_manual_fallback_and_releases_client_slot(self):
        observed = []
        def unavailable(*args, **kwargs):
            observed.append(kwargs['timeout'])
            raise SourceError('model request timed out')
        router = BasalRouter(Settings(Path('.'), basal_enabled=True, basal_timeout=30), fetcher=unavailable)
        for _ in range(2):
            self.assertEqual(router.classify('syntetyczny opis')['method'], 'unavailable')
        self.assertEqual(observed, [30, 30])
