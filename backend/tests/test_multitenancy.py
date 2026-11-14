import os
import unittest
from unittest.mock import patch

from backend import app as app_module
from backend import database
from backend.tests.db_support import use_temp_database


class MultiTenancyTests(unittest.TestCase):
    def setUp(self):
        use_temp_database(self)
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
        r = client.post('/api/contas', json=cadastro)
        self.assertEqual(r.status_code, 201, r.get_json())
        r = client.post('/api/login', json={'email': email, 'senha': cadastro['senha']})
        self.assertEqual(r.status_code, 200, r.get_json())
        return client

    def _ticket(self, client, setor, tecnico):
        with patch.object(app_module.smtplib, 'SMTP'):
            return client.post('/api/chamados', json={
                'cliente': 'C', 'descricao': 'd', 'email_cliente': 'c@x.test',
                'telefone_cliente': '1', 'contato_cliente': 'c', 'telefone_contato': '1',
                'setor': setor, 'id_grupo_solucionadores': tecnico})

    def test_workspaces_are_isolated(self):
        a = self._register('a@outlook.com', 'Empresa A')
        b = self._register('b@outlook.com', 'Empresa B')

        tecnico_a = a.post('/api/equipe', json={
            'nome': 'Tecnica A', 'email': 'tecnica.a@helpti.test', 'setor': 'Apoio A'
        })
        tecnico_b = b.post('/api/equipe', json={
            'nome': 'Tecnico B', 'email': 'tecnico.b@helpti.test', 'setor': 'Apoio B'
        })
        self.assertEqual(tecnico_a.status_code, 201, tecnico_a.get_json())
        self.assertEqual(tecnico_b.status_code, 201, tecnico_b.get_json())

        setores_a = {item['nome'] for item in a.get('/api/setores').get_json()}
        setores_b = {item['nome'] for item in b.get('/api/setores').get_json()}
        self.assertEqual(setores_a, {'Suporte', 'Apoio A'})
        self.assertEqual(setores_b, {'Suporte', 'Apoio B'})
        self.assertEqual(a.delete('/api/setores').status_code, 405)

        connection = database.get_db_connection()
        owners = {row[0] for row in connection.execute('SELECT DISTINCT id_usuario FROM grupo_solucionadores')}
        connection.close()
        self.assertEqual(len(owners), 2)
        self.assertNotIn('Apoio B', setores_a)
        self.assertNotIn('Apoio A', setores_b)
        ticket_a = self._ticket(
            a, 'Apoio A', tecnico_a.get_json()['id_grupo_solucionadores']
        )
        ticket_b = self._ticket(
            b, 'Apoio B', tecnico_b.get_json()['id_grupo_solucionadores']
        )
        self.assertEqual(ticket_a.status_code, 201, ticket_a.get_json())
        self.assertEqual(ticket_b.status_code, 201, ticket_b.get_json())

        self.assertEqual([ticket['setor'] for ticket in a.get('/api/chamados').get_json()], ['Apoio A'])
        self.assertEqual([ticket['setor'] for ticket in b.get('/api/chamados').get_json()], ['Apoio B'])
        self.assertEqual(a.get('/api/clientes').get_json(), [])
        cfg_a = a.get('/api/configuracoes').get_json()
        cfg_b = b.get('/api/configuracoes').get_json()
        self.assertNotEqual(cfg_a, cfg_b)


if __name__ == '__main__':
    unittest.main()
