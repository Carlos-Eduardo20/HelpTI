import os
import unittest
from unittest.mock import patch

from backend import app as app_module
from backend import database
from backend.tests.db_support import use_temp_database


class DeskOpsProject3Tests(unittest.TestCase):
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
                    'telefone': '(11) 99999-9999', 'senha': 'senha-segura-123'}
        r = client.post('/api/contas', json=cadastro)
        self.assertEqual(r.status_code, 201, r.get_json())
        r = client.post('/api/login', json={'email': email, 'senha': cadastro['senha']})
        self.assertEqual(r.status_code, 200, r.get_json())
        return client

    def _setup_empresa_com_tecnico(self):
        admin = self._register('admin@helpti.test', 'TechDesk Corp')
        
        tecnico_resp = admin.post('/api/equipe', json={
            'nome': 'Carlos Silva',
            'email': 'carlos@helpti.test',
            'telefone': '(11) 99999-9999',
            'setor': 'Suporte N1',
        })
        tecnico_id = tecnico_resp.get_json()['id_grupo_solucionadores']
        return admin, 'Suporte N1', tecnico_id

    def _create_customer(self, admin, name, email, phone):
        response = admin.post('/api/clientes', json={
            'nome': name,
            'contatos': [{'nome': name, 'email': email, 'telefone': phone}],
        })
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()['id_cliente']

    def test_chamado_com_setor_atributo_simples(self):
        admin, setor, tecnico_id = self._setup_empresa_com_tecnico()
        customer_id = self._create_customer(
            admin, 'Empresa Alpha', 'contato@alpha.test', '11999999999'
        )
        
        with patch.object(app_module.smtplib, 'SMTP'):
            resp = admin.post('/api/chamados', json={
                'id_cliente': customer_id,
                'cliente': 'Empresa Alpha',
                'descricao': 'Servidor inacessivel',
                'email_cliente': 'contato@alpha.test',
                'telefone_cliente': '11999999999',
                'contato_cliente': 'João Solicitante',
                'telefone_contato': '11988888888',
                'setor': 'Suporte N1',
                'id_grupo_solucionadores': tecnico_id
            })
        self.assertEqual(resp.status_code, 201)
        dados = resp.get_json()
        self.assertEqual(dados['setor'], 'Suporte N1')
        self.assertGreaterEqual(dados['id_chamado'], 100000)
        self.assertLessEqual(dados['id_chamado'], 999999)

        # Buscar detalhes e verificar histórico com autor
        detalhe_resp = admin.get(f'/api/chamados/{dados["id_chamado"]}')
        self.assertEqual(detalhe_resp.status_code, 200)
        detalhe = detalhe_resp.get_json()
        self.assertTrue(len(detalhe['historico']) >= 1)
        self.assertIn('autor', detalhe['historico'][0])
        self.assertTrue(detalhe['historico'][0]['autor'])

    def test_metricas_deskops_calculo(self):
        admin, setor, tecnico_id = self._setup_empresa_com_tecnico()
        customer_1 = self._create_customer(admin, 'Cliente 1', 'c1@test.com', '111')
        customer_2 = self._create_customer(admin, 'Cliente 2', 'c2@test.com', '222')
        
        with patch.object(app_module.smtplib, 'SMTP'):
            r1 = admin.post('/api/chamados', json={
                'id_cliente': customer_1,
                'cliente': 'Cliente 1', 'descricao': 'D1', 'email_cliente': 'c1@test.com',
                'telefone_cliente': '111', 'contato_cliente': 'C1', 'telefone_contato': '111',
                'setor': setor, 'id_grupo_solucionadores': tecnico_id
            })
            r2 = admin.post('/api/chamados', json={
                'id_cliente': customer_2,
                'cliente': 'Cliente 2', 'descricao': 'D2', 'email_cliente': 'c2@test.com',
                'telefone_cliente': '222', 'contato_cliente': 'C2', 'telefone_contato': '222',
                'setor': setor, 'id_grupo_solucionadores': tecnico_id
            })
        
        id2 = r2.get_json()['id_chamado']
        self.assertEqual(id2, r1.get_json()['id_chamado'] + 1)
        # Iniciar e encerrar chamado 2
        admin.put(f'/api/chamados/{id2}', json={'acao': 'iniciar'})
        with patch.object(app_module.smtplib, 'SMTP'):
            admin.put(f'/api/chamados/{id2}', json={'acao': 'encerrar', 'descricao_final': 'Problema resolvido com sucesso'})

        metricas_resp = admin.get('/api/chamados/metricas')
        self.assertEqual(metricas_resp.status_code, 200)
        metricas = metricas_resp.get_json()
        self.assertEqual(metricas['total'], 2)
        self.assertEqual(metricas['triagem'], 1)
        self.assertEqual(metricas['resolvidos'], 1)
        self.assertIn('mttr_formatado', metricas)

    def test_crud_documentacao_tecnica(self):
        admin, _setor, tecnico_id = self._setup_empresa_com_tecnico()

        # Criar documentação
        create_resp = admin.post('/api/documentacoes', json={
            'id_grupo_solucionadores': tecnico_id,
            'titulo': 'Manual Servidor PowerEdge R740',
            'conteudo': 'Procedimentos para troca de discos em RAID 5.'
        })
        self.assertEqual(create_resp.status_code, 201)
        doc = create_resp.get_json()
        doc_id = doc['id_documentacao']
        self.assertEqual(doc['funcionario_nome'], 'Carlos Silva')

        # Listar documentações
        list_resp = admin.get('/api/documentacoes?busca=PowerEdge')
        self.assertEqual(list_resp.status_code, 200)
        docs = list_resp.get_json()
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]['id_documentacao'], doc_id)

        # Atualizar
        update_resp = admin.put(f'/api/documentacoes/{doc_id}', json={
            'titulo': 'Manual Servidor PowerEdge R740 v2',
            'conteudo': 'Atualizado com novas controladoras PERC.'
        })
        self.assertEqual(update_resp.status_code, 200)
        self.assertEqual(update_resp.get_json()['funcionario_nome'], 'Carlos Silva')

        # Deletar
        del_resp = admin.delete(f'/api/documentacoes/{doc_id}')
        self.assertEqual(del_resp.status_code, 200)
        self.assertEqual(admin.get(f'/api/documentacoes/{doc_id}').status_code, 404)


if __name__ == '__main__':
    unittest.main()
