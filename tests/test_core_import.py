import tempfile
import unittest
from unittest.mock import Mock
from prawo.cli import import_core_act
from prawo.evidence import retrieve
from prawo.sources import SourceError, EliClient
from prawo.store import Store

class CoreImportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(self.temp.name)
        self.original={'ELI':'DU/1974/141','title':'Testowy kodeks','references':{'Inf. o tekście jednolitym':[{'id':'DU/2025/9'},{'id':'DU/2026/10'},{'id':'DU/2026/2'}]}}
        self.publication={'ELI':'DU/2026/10','title':'Testowa publikacja','legalStatusDate':'2026-01-01','references':{'Tekst jednolity dla aktu':[{'id':'DU/1974/141'}]},'texts':[{'fileName':'D20260010L.pdf','type':'T'}]}
        self.client=Mock()
        self.client.details.side_effect=lambda eli:(self.original if eli=='DU/1974/141' else self.publication,b'{}','official')
        self.client.pdf_text.return_value=('Art. 1. Syntetyczny tekst o reklamacji towaru, tylko do testowania.',b'%PDF-test','official')

    def test_latest_publication_uses_numeric_position_and_reverse_reference(self):
        result=import_core_act(self.store,self.client,'DU/1974/141',True)
        self.assertEqual(result['publication'],'DU/2026/10')
        self.client.pdf_text.assert_called_once_with('DU/2026/10','D20260010L.pdf','T')
        evidence=retrieve(self.store,'reklamacja')
        self.assertEqual(evidence[0]['eli'],'DU/2026/10')
        self.assertEqual(evidence[0]['legal_status_date'],'2026-01-01')

    def test_wrong_reverse_reference_rejected(self):
        self.publication['references']={}
        with self.assertRaises(SourceError):import_core_act(self.store,self.client,'DU/1974/141',True)
        self.client.pdf_text.assert_not_called()

    def test_failed_newest_pdf_does_not_fall_back_to_original_html(self):
        self.client.pdf_text.side_effect=SourceError('unavailable')
        with self.assertRaises(SourceError):import_core_act(self.store,self.client,'DU/1974/141',True)
        self.assertEqual(retrieve(self.store,'reklamacja'),[])

    def test_pdf_path_is_bounded_and_non_pdf_content_rejected(self):
        fetcher=Mock(return_value=b'<html>no PDF</html>');client=EliClient(fetcher=fetcher)
        for filename,kind in [('../secret','T'),('source.pdf','../U'),('x.pdf?key=y','T')]:
            with self.assertRaises(ValueError):client.pdf_text('DU/2026/10',filename,kind)
        with self.assertRaises(SourceError):client.pdf_text('DU/2026/10','D20260010L.pdf','T')
        self.assertEqual(fetcher.call_args.args[0],'https://api.sejm.gov.pl/eli/acts/DU/2026/10/text/T/D20260010L.pdf')
