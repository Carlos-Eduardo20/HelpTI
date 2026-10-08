import os
import re
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend import app as app_module
from backend import database


class MultiTenancyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def setUp(self):
        self.database_path = Path(self.temp_dir.name) / f'{self.id()}.sqlite3'
        database.DATABASE_PATH = self.database_path
        app_module.DATABASE_PATH = self.database_path
        env = patch.dict(os.environ, {
            'HELPTI_DEMO_MODE': 'false',
            'SMTP_HOST': 'smtp.example.test', 'SMTP_PORT': '587',
            'SMTP_USER': 'help@example.test', 'SMTP_PASSWORD': 'x',
            'SMTP_FROM': 'help@example.test',
        })
        env.start()
        self.addCleanup(env.stop)
        database.initialize_database()
        app_module.app.config.update(TESTING=True, SECRET_KEY='test-secret')

    def _register(self, email, empresa):
        client = app_module.app.test_client()
        cadastro = {'nome': empresa, 'empresa': empresa, 'email': email,
                    'senha': 'senha-segura-123'}
        smtp = MagicMock()
        server = smtp.__enter__.return_value
        with patch.object(app_module.smtplib, 'SMTP', return_value=smtp):
            self.assertEqual(client.post('/api/contas', json=cadastro).status_code, 202)
        code = re.search(r'\b(\d{6})\b', server.send_message.call_args.args[0].get_content()).group(1)
        r = client.post('/api/confirmar-conta', json={'email': email, 'codigo': code})
        self.assertIn(r.status_code, (200, 201), r.get_json())
        r = client.post('/api/login', json={'email': email, 'senha': cadastro['senha']})
        self.assertEqual(r.status_code, 200, r.get_json())
        return client

    def _ticket(self, client, setor, tecnico):
        with patch.object(app_module.smtplib, 'SMTP'):
            return client.post('/api/chamados', json={
                'cliente': 'C', 'descricao': 'd', 'email_cliente': 'c@x.test',
                'telefone_cliente': '1', 'contato_cliente': 'c', 'telefone_contato': '1',
                'id_setor': setor, 'id_grupo_solucionadores': tecnico})

    def test_workspaces_are_isolated(self):
        a = self._register('a@outlook.com', 'Empresa A')
        b = self._register('b@outlook.com', 'Empresa B')

        r = a.post('/api/setores', json={'nome': 'Suporte', 'descricao': 'x', 'niveis': ['N1']})
        self.assertIn(r.status_code, (200, 201), r.get_json())
        r = b.post('/api/setores', json={'nome': 'Suporte', 'descricao': 'y', 'niveis': ['N1']})
        self.assertIn(r.status_code, (200, 201), r.get_json())

        setores_a = a.get('/api/setores').get_json()
        setores_b = b.get('/api/setores').get_json()
        self.assertEqual(len(setores_a), 1)
        self.assertEqual(len(setores_b), 1)
        self.assertNotEqual(setores_a[0]['id_setor'], setores_b[0]['id_setor'])

        connection = sqlite3.connect(self.database_path)
        owners = {row[0] for row in connection.execute('SELECT id_usuario FROM setor')}
        connection.close()
        self.assertEqual(len(owners), 2)
        self.assertNotIn(None, owners)

        self.assertEqual(a.delete(f"/api/setores/{setores_b[0]['id_setor']}").status_code, 404)
        self.assertEqual(len(b.get('/api/setores').get_json()), 1)

        self.assertEqual(a.get('/api/chamados').get_json(), [])
        self.assertEqual(a.get('/api/clientes').get_json(), [])
        cfg_a = a.get('/api/configuracoes').get_json()
        cfg_b = b.get('/api/configuracoes').get_json()
        self.assertNotEqual(cfg_a, cfg_b)

    def test_legacy_database_is_migrated(self):
        legacy = Path(self.temp_dir.name) / 'legacy.sqlite3'
        root = Path(__file__).resolve().parents[2]
        old_schema = subprocess.run(
            ['git', 'show', 'HEAD:backend/schema.sql'], cwd=root,
            capture_output=True, text=True, check=True).stdout
        connection = sqlite3.connect(legacy)
        connection.executescript(old_schema)
        connection.commit()
        connection.close()

        database.DATABASE_PATH = legacy
        database.initialize_database()
        database.initialize_database()
        connection = sqlite3.connect(legacy)
        for table in ('chamado', 'setor', 'configuracao'):
            columns = [row[1] for row in connection.execute(f'PRAGMA table_info({table})')]
            self.assertIn('id_usuario', columns, table)
        connection.close()


if __name__ == '__main__':
    unittest.main()
