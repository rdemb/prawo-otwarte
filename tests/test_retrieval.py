"""Synthetic rules with arbitrary numbering; no corpus PDFs or private cases."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from prawo.answers import AnswerEngine
from prawo.evidence import retrieve
from prawo.settings import Settings
from prawo.store import Store


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(self.temp.name)

    def act(self, root, publication, name, body):
        for eli,title in [(root,name),(publication,'Obwieszczenie o tekście jednolitym '+name)]:
            self.store.upsert({'ELI':eli,'title':title,'changeDate':'2020-01-01'},source_url='synthetic')
        self.store.set_text(publication,body,body.encode(),'synthetic',kind='pdf')
        self.store.select_answer_publication(root,publication,'synthetic_test')

    def test_named_act_filters_before_candidate_limit(self):
        self.act('DU/2020/1','DU/2025/1','Ustawa o narzędziach',
                 'Art. 88. Zwrot narzędzia następuje po zakończeniu testowego pomiaru.')
        self.act('DU/2020/2','DU/2025/2','Ustawa o urządzeniach',
                 '\n'.join(f'Art. {n}. Narzędzia i zwrot narzędzi w odrębnym teście urządzeń.' for n in range(1,301)))
        rows=retrieve(self.store,'Co ustawa o narzędziach mówi o zwrocie?')
        self.assertTrue(rows);self.assertTrue(all(r['eli']=='DU/2025/1' for r in rows))

    def test_scope_rule_is_retained_for_scope_question(self):
        self.act('DU/2020/1','DU/2025/1','Ustawa o narzędziach',
                 'Art. 1. Ustawa określa zasady zwrotu narzędzi w teście.\n'
                 'Art. 88. Zwrot narzędzia następuje po zakończeniu testowego pomiaru.')
        self.assertEqual(retrieve(self.store,'Co reguluje ustawa o narzędziach?')[0]['label'],'Art. 1.')
        self.assertEqual(retrieve(self.store,'Kiedy ustawa o narzędziach przewiduje zwrot?')[0]['label'],'Art. 88.')

    def test_article_reference_matches_unit_not_cross_reference_or_amendment(self):
        self.act('DU/2020/1','DU/2025/1','Ustawa o narzędziach',
                 'Art. 77. Syntetyczna samodzielna reguła zwrotu narzędzia.\n'
                 'Art. 77[1]. Inna reguła testowa powołująca art. 77.\n'
                 'Art. 78. Szczególna reguła testowa powołująca art. 77.')
        self.act('DU/2020/2','DU/2025/2','Ustawa o urządzeniach',
                 'Art. 77. Odrębny syntetyczny przepis o urządzeniach.')
        rows=retrieve(self.store,'Pokaż artykuł 77 ustawy o narzędziach.')
        self.assertEqual([(r['eli'],r['label']) for r in rows],[('DU/2025/1','Art. 77.')])

    def test_inflected_concepts_find_rule_and_preserve_full_context(self):
        body='Art. 88. Zwrot kaucji z tytułu najmu lokalu następuje w testowym terminie, po spełnieniu testowego warunku.'
        self.act('DU/2020/1','DU/2025/1','Ustawa o narzędziach',body)
        rows=retrieve(self.store,'Kiedy zwraca się kaucję przy najmie mieszkania?')
        self.assertEqual(rows[0]['text'],body);self.assertFalse(rows[0]['temporal_verified'])

    def test_incidental_prefix_overlap_does_not_establish_query_coverage(self):
        self.act('DU/2020/1','DU/2025/1','Ustawa o obiektach',
                 'Art. 88. Obiekt budowlany jest przedmiotem syntetycznej reguły technicznej.')
        self.assertEqual(retrieve(self.store,'Jaki obiektyw do fotografowania planet teleskopem?'),[])

    def test_missing_document_type_never_substitutes_same_article_in_an_act(self):
        self.act('DU/2020/1','DU/2025/1','Ustawa o narzędziach',
                 'Art. 17. Syntetyczna reguła dotycząca testowego odszkodowania.')
        self.assertEqual(retrieve(self.store,'Co stanowi art. 17 rozporządzenia UE 9876/2030?'),[])

    def test_date_condition_is_kept_but_does_not_displace_general_rule(self):
        general='Art. 88. Kaucja podlega zwrotowi po spełnieniu testowego warunku zwrotu.'
        dated='Art. 89. Kaucja wpłacona przed dniem 31 grudnia 1901 r. podlega zwrotowi po testowym pomiarze.'
        self.act('DU/2020/1','DU/2025/1','Ustawa o narzędziach',general+'\n'+dated)
        rows=retrieve(self.store,'Kiedy następuje zwrot kaucji?')
        self.assertEqual(rows[0]['label'],'Art. 88.')
        self.assertIn(dated,[r['text'] for r in rows])
        self.assertEqual(retrieve(self.store,'Zwrot kaucji wpłaconej przed dniem 31 grudnia 1901 r.')[0]['label'],'Art. 89.')

    def test_how_question_prefers_requested_action_over_its_effect(self):
        self.act('DU/2020/1','DU/2025/1','Ustawa o narzędziach',
                 'Art. 88. Uczestnik składa oświadczenie o odbiorze narzędzia na testowym formularzu.\n'
                 'Art. 89. Po odbiorze narzędzia wygasa syntetyczne zobowiązanie. Jeżeli uczestnik złożył oświadczenie o odbiorze narzędzia, test zostaje zakończony.')
        self.assertEqual(retrieve(self.store,'Jak uczestnik może złożyć oświadczenie o odbiorze narzędzia?')[0]['label'],'Art. 88.')

    def test_underspecified_contract_asks_for_details_without_model(self):
        self.act('DU/2020/1','DU/2025/1','Ustawa o narzędziach',
                 'Art. 88. Wypowiedzenie umowy następuje po spełnieniu syntetycznego warunku.')
        router=Mock();fetcher=Mock(side_effect=AssertionError('No generation before clarification'))
        engine=AnswerEngine(Settings(Path(self.temp.name),generator_enabled=True),self.store,router,fetcher)
        result=engine.answer('Jak wypowiedzieć umowę?')
        self.assertEqual(result['generation']['status'],'clarification_needed')
        self.assertEqual(result['claims'],[]);self.assertIn('rodzaju',result['message'])
        fetcher.assert_not_called();router.check_evidence.assert_not_called()
