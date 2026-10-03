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

    def test_public_ip_https_can_be_built_without_buying_a_domain(self):
        # Configuration-only examples: tests never contact these addresses.
        for configured,expected in [('https://1.1.1.1:443/', 'https://1.1.1.1'),
                                    ('https://[2606:4700:4700:0:0:0:0:1111]', 'https://[2606:4700:4700::1111]')]:
            with self.subTest(configured=configured),tempfile.TemporaryDirectory() as folder:
                build(folder,configured)
                data = json.loads((Path(folder) / 'pages-data.json').read_text())
                self.assertEqual(data['api_base_url'],expected)

    def test_nonpublic_and_ambiguous_ip_addresses_are_rejected(self):
        for host in ['127.0.0.1', '10.0.0.1', '172.16.0.1', '192.168.1.1', '169.254.169.254',
                     '100.64.0.1', '0.0.0.0', '192.0.2.1', '224.0.0.1', '240.0.0.1',
                     '127.1', '2130706433', '0x7f000001', '[::1]', '[::]', '[fe80::1]',
                     '[fc00::1]', '[2001:db8::1]', '[ff02::1]', '[::ffff:1.1.1.1]',
                     '[2606:4700:4700::1111%eth0]']:
            with self.subTest(host=host),tempfile.TemporaryDirectory() as folder:
                with self.assertRaises(ValueError): build(folder, 'https://' + host)
                self.assertEqual(list(Path(folder).iterdir()),[])
