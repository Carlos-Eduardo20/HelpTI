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
        clientes = client.get('/api/clientes').get_json()
        if not clientes:
            response = client.post('/api/clientes', json={
                'nome': 'C',
                'contatos': [{
                    'nome': 'c',
                    'email': 'c@x.test',
                    'telefone': '1',
                }],
            })
            self.assertEqual(response.status_code, 201, response.get_json())
            clientes = [response.get_json()]
        with patch.object(app_module.smtplib, 'SMTP'):
            return client.post('/api/chamados', json={
                'id_cliente': clientes[0]['id_cliente'],
                'cliente': clientes[0]['nome'], 'descricao': 'd', 'email_cliente': 'c@x.test',
                'telefone_cliente': '1', 'contato_cliente': 'c', 'telefone_contato': '1',
                'setor': setor, 'id_grupo_solucionadores': tecnico})

    def test_delete_client_removes_client_and_contact_records(self):
        client = self._register('owner@outlook.com', 'Empresa')
        created = client.post('/api/clientes', json={
            'nome': 'Cliente A',
            'contatos': [{
                'nome': 'Contato A',
                'email': 'contato.a@example.test',
                'telefone': '11999999999',
            }],
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        customer_id = created.get_json()['id_cliente']
        member = client.post('/api/equipe', json={
            'nome': 'Tecnica A', 'email': 'tecnica.a@helpti.test', 'setor': 'Suporte'
        })
        self.assertEqual(member.status_code, 201, member.get_json())
        ticket = self._ticket(
            client, 'Suporte', member.get_json()['id_grupo_solucionadores']
        )
        self.assertEqual(ticket.status_code, 201, ticket.get_json())

        deleted = client.delete(f'/api/clientes/{customer_id}')

        self.assertEqual(deleted.status_code, 200, deleted.get_json())
        connection = database.get_db_connection()
        try:
            self.assertIsNone(connection.execute(
                'SELECT 1 FROM cliente WHERE id_cliente = %s', (customer_id,)
            ).fetchone())
            self.assertEqual(connection.execute(
                'SELECT COUNT(*) FROM contato_cliente WHERE id_cliente = %s', (customer_id,)
            ).fetchone()[0], 0)
            preserved_ticket = connection.execute(
                'SELECT cliente, id_cliente FROM chamado WHERE id_chamado = %s',
                (ticket.get_json()['id_chamado'],),
            ).fetchone()
            self.assertEqual(preserved_ticket['cliente'], 'Cliente A')
            self.assertIsNone(preserved_ticket['id_cliente'])
        finally:
            connection.close()

    def test_customer_company_belongs_to_user_and_contact_updates_are_synchronized(self):
        client = self._register('owner@outlook.com', 'Empresa')
        created = client.post('/api/clientes', json={
            'nome': 'Cliente A',
            'cnpj': '123',
            'telefone_empresa': '1133334444',
            'contatos': [
                {'nome': 'Contato Principal', 'email': 'principal@example.test', 'telefone': '111'},
                {'nome': 'Contato Secundário', 'email': 'secundario@example.test', 'telefone': '222'},
            ],
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        company = created.get_json()
        customer_id = company['id_cliente']

        updated = client.put(f'/api/clientes/{customer_id}', json={
            'cnpj': '456',
            'contato': 'Principal Atualizado',
            'email': 'atualizado@example.test',
            'telefone': '333',
        })

        self.assertEqual(updated.status_code, 200, updated.get_json())
        self.assertEqual(updated.get_json()['cnpj'], '456')
        self.assertEqual(updated.get_json()['contatos'], [
            {'nome': 'Principal Atualizado', 'email': 'atualizado@example.test', 'telefone': '333'},
            {'nome': 'Contato Secundário', 'email': 'secundario@example.test', 'telefone': '222'},
        ])

        connection = database.get_db_connection()
        try:
            owner_id = connection.execute(
                "SELECT id_usuario FROM usuario WHERE email = 'owner@outlook.com'"
            ).fetchone()['id_usuario']
            relation = connection.execute(
                'SELECT id_usuario FROM cliente WHERE id_cliente = %s', (customer_id,)
            ).fetchone()
            customer_columns = {
                row[1] for row in connection.execute(
                    'PRAGMA table_info(cliente)'
                ).fetchall()
            }
            self.assertEqual(relation['id_usuario'], owner_id)
            self.assertNotIn('id_workspace', customer_columns)
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM usuario WHERE tipo_usuario = 'CLIENTE'"
                ).fetchone()[0],
                0,
            )
        finally:
            connection.close()

    def test_delete_team_member_removes_record_and_unassigns_tickets(self):
        client = self._register('owner@outlook.com', 'Empresa')
        created = client.post('/api/equipe', json={
            'nome': 'Tecnica A', 'email': 'tecnica.a@helpti.test', 'setor': 'Suporte'
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        member_id = created.get_json()['id_grupo_solucionadores']
        ticket = self._ticket(client, 'Suporte', member_id)
        self.assertEqual(ticket.status_code, 201, ticket.get_json())
        ticket_id = ticket.get_json()['id_chamado']

        deleted = client.delete(f'/api/equipe/{member_id}')

        self.assertEqual(deleted.status_code, 200, deleted.get_json())
        connection = database.get_db_connection()
        try:
            self.assertIsNone(connection.execute(
                'SELECT 1 FROM grupo_solucionadores WHERE id_grupo_solucionadores = %s',
                (member_id,),
            ).fetchone())
            self.assertIsNone(connection.execute(
                'SELECT id_grupo_solucionadores FROM chamado WHERE id_chamado = %s',
                (ticket_id,),
            ).fetchone()['id_grupo_solucionadores'])
        finally:
            connection.close()

    def test_delete_ticket_removes_history_and_escalations(self):
        client = self._register('owner@outlook.com', 'Empresa')
        member = client.post('/api/equipe', json={
            'nome': 'Tecnica A', 'email': 'tecnica.a@helpti.test', 'setor': 'Suporte'
        })
        self.assertEqual(member.status_code, 201, member.get_json())
        ticket = self._ticket(
            client, 'Suporte', member.get_json()['id_grupo_solucionadores']
        )
        self.assertEqual(ticket.status_code, 201, ticket.get_json())
        ticket_id = ticket.get_json()['id_chamado']
        connection = database.get_db_connection()
        try:
            connection.execute(
                'INSERT INTO historico_chamado (id_chamado, evento, descricao) '
                'VALUES (%s, %s, %s)',
                (ticket_id, 'teste', 'Registro de teste'),
            )
            connection.execute(
                'INSERT INTO escalonamento (id_chamado, motivo) VALUES (%s, %s)',
                (ticket_id, 'Registro de teste'),
            )
            connection.commit()
        finally:
            connection.close()

        deleted = client.delete(f'/api/chamados/{ticket_id}')

        self.assertEqual(deleted.status_code, 200, deleted.get_json())
        connection = database.get_db_connection()
        try:
            for table in ('chamado', 'historico_chamado', 'escalonamento'):
                self.assertEqual(connection.execute(
                    f'SELECT COUNT(*) FROM {table} WHERE id_chamado = %s',
                    (ticket_id,),
                ).fetchone()[0], 0)
        finally:
            connection.close()

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
        cross_workspace_ticket = b.post('/api/chamados', json={
            'id_cliente': ticket_a.get_json()['id_cliente'],
            'descricao': 'Tentativa entre workspaces',
            'email_cliente': 'c@x.test',
            'telefone_cliente': '1',
            'contato_cliente': 'c',
            'telefone_contato': '1',
            'setor': 'Apoio B',
            'id_grupo_solucionadores': tecnico_b.get_json()['id_grupo_solucionadores'],
        })
        self.assertEqual(cross_workspace_ticket.status_code, 400)

        self.assertEqual([ticket['setor'] for ticket in a.get('/api/chamados').get_json()], ['Apoio A'])
        self.assertEqual([ticket['setor'] for ticket in b.get('/api/chamados').get_json()], ['Apoio B'])
        self.assertEqual([row['nome'] for row in a.get('/api/clientes').get_json()], ['C'])
        self.assertEqual([row['nome'] for row in b.get('/api/clientes').get_json()], ['C'])
        cfg_a = a.get('/api/configuracoes').get_json()
        cfg_b = b.get('/api/configuracoes').get_json()
        self.assertNotEqual(cfg_a, cfg_b)


if __name__ == '__main__':
    unittest.main()
