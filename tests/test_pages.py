import tempfile
import json
import unittest
from pathlib import Path

from scripts.build_pages import build, PUBLIC_FILES


class PagesBuildTests(unittest.TestCase):
    def test_build_only_contains_public_assets_and_uses_relative_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            build(folder)
            target = Path(folder)
            self.assertEqual({p.name for p in target.iterdir()},set(PUBLIC_FILES)|{"pages-data.json",".nojekyll"})
            html = (target / "index.html").read_text()
            self.assertNotIn('src="/',html)
            self.assertNotIn('href="/',html)
            self.assertLess(html.index('src="./pages.js"'),html.index('src="./app.js"'))

    def test_build_rejects_directory_with_unrelated_content(self):
        with tempfile.TemporaryDirectory() as folder:
            private = Path(folder) / "private.txt"
            private.write_text("do not publish")
            with self.assertRaises(ValueError): build(folder)
            self.assertEqual(private.read_text(),"do not publish")

    def test_api_is_disabled_by_default_and_explicitly_configurable(self):
        for configured,expected in [('', ''),('https://api.example.org/', 'https://api.example.org')]:
            with tempfile.TemporaryDirectory() as folder:
                build(folder,configured)
                data = json.loads((Path(folder) / 'pages-data.json').read_text())
                self.assertEqual(data['api_base_url'],expected)

    def test_unsafe_api_configuration_is_rejected_before_writing(self):
        for address in ['http://api.example.org','https://127.0.0.1','https://server.local','https://api.example.org:8766',
                        'https://user:pass@api.example.org','https://api.example.org/api','https://api.example.org?token=secret']:
            with self.subTest(address=address),tempfile.TemporaryDirectory() as folder:
                with self.assertRaises(ValueError): build(folder,address)
                self.assertEqual(list(Path(folder).iterdir()),[])
