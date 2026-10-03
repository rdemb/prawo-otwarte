import unittest

from scripts.check_public_repo import inspect


class PublicRepositoryTests(unittest.TestCase):
    def test_private_material_is_blocked_without_exposing_values(self):
        for name in ['AGENTS.md','docs/agents.md','.env.production','data/catalog.sqlite3','weights/model.safetensors','raport-vps.txt','.codex/config.toml']:
            with self.subTest(name=name): self.assertTrue(inspect(name,b'example'))
        key = b'-----BEGIN ' + b'OPENSSH PRIVATE KEY-----'
        self.assertEqual(inspect('innocent.txt',key),['credential pattern'])
        token = b'ghp' + b'_' + b'x'*36
        self.assertEqual(inspect('notes.txt',token),['credential pattern'])

    def test_public_examples_and_documents_are_allowed(self):
        for name in ['.env.example','docs/DEPLOYMENT.md','prawo/cases.py','LICENSE']:
            with self.subTest(name=name): self.assertEqual(inspect(name,b'public documentation'),[])
