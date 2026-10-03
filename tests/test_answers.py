import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

from prawo.answers import AnswerEngine, validate_claims
from prawo.cases import BasalRouter, DOMAINS
from prawo.evidence import retrieve
from prawo.settings import Settings
from prawo.sources import SourceError
from prawo.store import Store


class AnswersTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.settings = Settings(Path(self.temp.name),allow_eli=False)
        self.store = Store(self.temp.name)
        self.item = {'ELI':'DU/2020/1','title':'Syntetyczny akt testowy','changeDate':'2020-01-01'}
        self.store.upsert(self.item,source_url='https://api.sejm.gov.pl/eli/acts/DU/2020/1')
        self.body = 'Art. 1. Syntetyczny przepis testowy o zakupach i reklamacji towaru. Nie jest to rzeczywisty przepis.\nArt. 2. Inna testowa zasada dotycząca pracy.'
        self.store.set_text('DU/2020/1',self.body,self.body.encode(),'https://api.sejm.gov.pl/eli/acts/DU/2020/1/text.html',kind='pdf')
        self.store.select_answer_publication('DU/2020/1','DU/2020/1','synthetic_test')
        self.router = Mock(); self.router.check_evidence.return_value = {'verdict':'supported','checked':True}

    def engine(self, fetcher=None, **settings):
        return AnswerEngine(replace(self.settings,**settings),self.store,self.router,fetcher=fetcher or Mock(side_effect=AssertionError('Unexpected generator call')))

    def generated(self, claims=None, finish='stop'):
        if claims is None:
            claims = [{'source_id':'S1','quote':'Syntetyczny przepis testowy o zakupach i reklamacji towaru.','explanation':'Fragment wspomina zakupy i reklamację towaru.'}]
        return json.dumps({'choices':[{'finish_reason':finish,'message':{'content':json.dumps({'claims':claims})}}]}).encode()

    def test_excerpts_work_without_any_model_or_classification(self):
        data = self.engine().answer('Co mówią źródła o reklamacji?')
        self.assertEqual(data['mode'],'excerpts'); self.assertEqual(len(data['sources']),1)
        self.assertFalse(data['temporal_verified']); self.assertEqual(data['claims'],[])
        self.router.classify.assert_not_called(); self.router.check_evidence.assert_not_called()

    def test_retrieval_excludes_stale_text_and_metadata_only(self):
        self.store.upsert(dict(self.item,changeDate='2026-01-01'),source_url='official')
        self.assertEqual(retrieve(self.store,'reklamacja'),[])
        self.assertEqual(self.engine().answer('Pytanie o reklamację')['mode'],'no_sources')
        self.store.set_text('DU/2020/1',self.body,self.body.encode(),'official',kind='pdf')
        self.assertEqual(len(retrieve(self.store,'reklamacja')),1)
        self.assertEqual(Store(self.temp.name).status()['passage_count'],2)

    def test_no_evidence_never_calls_generator(self):
        data=self.engine(generator_enabled=True).answer('Niezidentyfikowanasprawa bezpodstaw')
        self.assertEqual(data['mode'],'no_sources')

    def test_verified_citations_and_basal_support_publish_draft(self):
        calls=[]
        def fetcher(url,**kwargs):
            calls.append((url,json.loads(kwargs['body'])))
            return self.generated()
        data=self.engine(fetcher,generator_enabled=True).answer('Pytanie o reklamację', '2020-01-01')
        self.assertEqual(data['mode'],'draft'); self.assertEqual(len(data['claims']),1)
        self.assertEqual(calls[0][0],'http://127.0.0.1:8767/v1/chat/completions')
        self.assertEqual(calls[0][1]['max_tokens'],700)
        self.assertFalse(data['temporal_verified']); self.assertEqual(data['event_date'],'2020-01-01')

    def test_fabricated_citation_or_unfinished_output_never_published(self):
        for raw in [self.generated([{'source_id':'S99','quote':'Nieistniejący cytat testowy.','explanation':'Fałszywe objaśnienie testowe.'}]),self.generated(finish='length'),b'not json']:
            with self.subTest(raw=raw):
                data=self.engine(lambda *a,**k:raw,generator_enabled=True).answer('Pytanie o reklamację')
                self.assertEqual(data['mode'],'excerpts'); self.assertEqual(data['claims'],[])
                self.assertEqual(data['generation']['status'],'unavailable')

    def test_basal_uncertainty_preserves_sources_but_hides_generated_claim(self):
        for verdict in ['unclear','unsupported','unavailable']:
            self.router.check_evidence.return_value={'verdict':verdict,'checked':verdict!='unavailable'}
            data=self.engine(lambda *a,**k:self.generated(),generator_enabled=True).answer('Pytanie o reklamację')
            self.assertEqual(data['mode'],'excerpts'); self.assertEqual(data['claims'],[])
            self.assertEqual(len(data['sources']),1)

    def test_busy_or_failed_generator_preserves_evidence_and_releases_slot(self):
        engine=self.engine(lambda *a,**k: (_ for _ in ()).throw(SourceError('down')),generator_enabled=True)
        engine.slot.acquire()
        self.assertEqual(engine.answer('Pytanie o reklamację')['generation']['status'],'busy')
        engine.slot.release()
        self.assertEqual(engine.answer('Pytanie o reklamację')['generation']['status'],'unavailable')
        self.assertTrue(engine.slot.acquire(blocking=False));engine.slot.release()

    def test_question_is_not_persisted(self):
        secret='PRIVATE_4388 pytanie o reklamację'
        self.engine().answer(secret)
        for path in Path(self.temp.name).rglob('*'):
            if path.is_file(): self.assertNotIn(secret.encode(),path.read_bytes())

    def test_model_url_cannot_target_public_or_hostname_endpoints(self):
        for url in ['https://example.com','http://localhost:8767','http://127.0.0.1:8767/path','http://user@127.0.0.1','http://10.0.0.1']:
            with self.subTest(url=url),self.assertRaises(ValueError):self.engine(generator_url=url)
        for timeout in [float('nan'),0,91]:
            with self.assertRaises(ValueError):self.engine(generator_timeout=timeout)

    def test_router_explains_abstention_without_lowering_threshold(self):
        probabilities={k:.025 for k in DOMAINS};probabilities['work']=.8
        probabilities['work']=.6; probabilities['civil']=.225
        raw=json.dumps({'answers':{'domain':{'choice':'work','probabilities':probabilities}}}).encode()
        router=BasalRouter(replace(self.settings,basal_enabled=True),fetcher=lambda *a,**k:raw)
        data=router.classify('Przykład syntetyczny')
        self.assertEqual(data['method'],'basal_abstained')
        self.assertEqual(data['diagnostics']['candidate'],'work')
        self.assertEqual(data['diagnostics']['score'],.6)
        self.assertEqual(data['diagnostics']['threshold'],.8)

    def test_basal_evidence_decision_is_typed_and_thresholded(self):
        for scores,expected in [({'supported':.9,'unsupported':.05,'unclear':.05},'supported'),({'supported':.5,'unsupported':.25,'unclear':.25},'unclear')]:
            raw=json.dumps({'answers':{'evidence':{'choice':'supported','probabilities':scores}}}).encode()
            router=BasalRouter(replace(self.settings,basal_enabled=True),fetcher=lambda *a,**k:raw)
            self.assertEqual(router.check_evidence([])['verdict'],expected)

    def test_original_html_is_never_an_answer_source_even_if_selected(self):
        self.store.set_text('DU/2020/1',self.body,self.body.encode(),'official',kind='html')
        self.assertEqual(retrieve(self.store,'reklamacja'),[])
        self.assertEqual(self.store.status()['answer_source_count'],0)
