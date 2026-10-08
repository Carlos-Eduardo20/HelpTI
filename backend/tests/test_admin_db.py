import os
from unittest.mock import patch

from backend import app as app_module
from backend import database
from backend.tests import test_multitenancy as _mt


class AdminDatabaseTests(_mt.MultiTenancyTests):
    # Reutiliza setUp e _register da suíte de multi-tenancy.
    test_workspaces_are_isolated = None
    test_legacy_database_is_migrated = None

    def _demo_client(self):
        patcher = patch.dict(os.environ, {'HELPTI_DEMO_MODE': 'true'})
        patcher.start()
        self.addCleanup(patcher.stop)
        database.initialize_database()
        client = app_module.app.test_client()
        r = client.post('/api/login', json={'email': 'test@helpiti.com', 'senha': 'HelpTI2026!'})
        self.assertEqual(r.status_code, 200, r.get_json())
        return client

    def test_stats_and_backup_are_scoped_and_redacted(self):
        a = self._register('a@outlook.com', 'Empresa A')
        b = self._register('b@outlook.com', 'Empresa B')
        for client, nome in ((a, 'SetorA'), (b, 'SetorB')):
            self.assertIn(client.post('/api/setores', json={'nome': nome, 'descricao': 'x', 'niveis': ['N1']}).status_code, (200, 201))

        stats = a.get('/api/admin/db/stats')
        self.assertEqual(stats.status_code, 200)
        dados = stats.get_json()
        self.assertEqual(dados['registros']['chamados'], 0)
        self.assertGreater(dados['tamanhoBytes'], 0)
        self.assertEqual(dados['versaoSchema'], database.SCHEMA_VERSION)
        self.assertFalse(dados['contaTeste'])

        backup = a.get('/api/admin/db/backup')
        self.assertEqual(backup.status_code, 200)
        sql = backup.get_data(as_text=True)
        self.assertIn('SetorA', sql)
        self.assertNotIn('SetorB', sql)
        self.assertNotIn('pbkdf2', sql)
        self.assertNotIn('scrypt', sql)

    def test_reset_demo_forbidden_for_real_workspace(self):
        a = self._register('a@outlook.com', 'Empresa A')
        self.assertEqual(a.post('/api/admin/db/reset-demo').status_code, 403)

    def test_reset_demo_restores_initial_state(self):
        client = self._demo_client()
        stats = client.get('/api/admin/db/stats').get_json()
        self.assertTrue(stats['contaTeste'])
        with patch.dict(os.environ, {'HELPTI_DEMO_MODE': 'true'}):
            r = client.post('/api/admin/db/reset-demo')
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertEqual(r.get_json()['registros']['chamados'], 0)
        nomes = [s['nome'].lower() for s in client.get('/api/setores').get_json()]
        self.assertIn('suporte', nomes)

    def test_requires_authentication(self):
        client = app_module.app.test_client()
        self.assertIn(client.get('/api/admin/db/stats').status_code, (401, 403))


if __name__ == '__main__':
    import unittest
    unittest.main()
