import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend import app as app_module
from backend import database


class DeskOpsProject3Tests(unittest.TestCase):
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

    def _setup_empresa_com_tecnico(self):
        admin = self._register('admin@helpti.test', 'TechDesk Corp')
        setor_resp = admin.post('/api/setores', json={'nome': 'Suporte N1', 'descricao': 'Primeiro nivel', 'niveis': ['N1']})
        setor_id = setor_resp.get_json()['id_setor']
        
        tecnico_resp = admin.post('/api/equipe', json={
            'nome': 'Carlos Silva',
            'email': 'carlos@helpti.test',
            'senha': 'senha-tecnico-123',
            'cargo': 'tecnico',
            'id_setor': setor_id,
            'setor': 'Suporte N1',
            'nivel': 1,
            'permissoes': ['dashboard', 'chamados']
        })
        tecnico_id = tecnico_resp.get_json()['id_grupo_solucionadores']
        return admin, setor_id, tecnico_id

    def test_chamado_com_setor_atributo_e_prioridade(self):
        admin, setor_id, tecnico_id = self._setup_empresa_com_tecnico()
        
        with patch.object(app_module.smtplib, 'SMTP'):
            resp = admin.post('/api/chamados', json={
                'cliente': 'Empresa Alpha',
                'descricao': 'Servidor inacessivel',
                'email_cliente': 'contato@alpha.test',
                'telefone_cliente': '11999999999',
                'contato_cliente': 'João Solicitante',
                'telefone_contato': '11988888888',
                'id_setor': setor_id,
                'setor': 'Suporte N1',
                'prioridade': 'ALTA',
                'id_grupo_solucionadores': tecnico_id
            })
        self.assertEqual(resp.status_code, 201)
        dados = resp.get_json()
        self.assertEqual(dados['prioridade'], 'ALTA')
        self.assertEqual(dados['setor'], 'Suporte N1')

        # Buscar detalhes e verificar histórico com autor
        detalhe_resp = admin.get(f'/api/chamados/{dados["id_chamado"]}')
        self.assertEqual(detalhe_resp.status_code, 200)
        detalhe = detalhe_resp.get_json()
        self.assertTrue(len(detalhe['historico']) >= 1)
        self.assertIn('autor', detalhe['historico'][0])
        self.assertTrue(detalhe['historico'][0]['autor'])

    def test_metricas_deskops_calculo(self):
        admin, setor_id, tecnico_id = self._setup_empresa_com_tecnico()
        
        with patch.object(app_module.smtplib, 'SMTP'):
            r1 = admin.post('/api/chamados', json={
                'cliente': 'Cliente 1', 'descricao': 'D1', 'email_cliente': 'c1@test.com',
                'telefone_cliente': '111', 'contato_cliente': 'C1', 'telefone_contato': '111',
                'id_setor': setor_id, 'id_grupo_solucionadores': tecnico_id, 'prioridade': 'CRITICA'
            })
            r2 = admin.post('/api/chamados', json={
                'cliente': 'Cliente 2', 'descricao': 'D2', 'email_cliente': 'c2@test.com',
                'telefone_cliente': '222', 'contato_cliente': 'C2', 'telefone_contato': '222',
                'id_setor': setor_id, 'id_grupo_solucionadores': tecnico_id, 'prioridade': 'BAIXA'
            })
        
        id2 = r2.get_json()['id_chamado']
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
        admin, setor_id, tecnico_id = self._setup_empresa_com_tecnico()

        # Criar documentação
        create_resp = admin.post('/api/documentacoes', json={
            'fornecedor': 'Dell EMC',
            'id_grupo_solucionadores': tecnico_id,
            'titulo': 'Manual Servidor PowerEdge R740',
            'conteudo': 'Procedimentos para troca de discos em RAID 5.'
        })
        self.assertEqual(create_resp.status_code, 201)
        doc = create_resp.get_json()
        doc_id = doc['id_documentacao']
        self.assertEqual(doc['fornecedor'], 'Dell EMC')

        # Listar documentações
        list_resp = admin.get('/api/documentacoes?busca=PowerEdge')
        self.assertEqual(list_resp.status_code, 200)
        docs = list_resp.get_json()
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]['id_documentacao'], doc_id)

        # Atualizar
        update_resp = admin.put(f'/api/documentacoes/{doc_id}', json={
            'fornecedor': 'Dell Technologies',
            'titulo': 'Manual Servidor PowerEdge R740 v2',
            'conteudo': 'Atualizado com novas controladoras PERC.'
        })
        self.assertEqual(update_resp.status_code, 200)
        self.assertEqual(update_resp.get_json()['fornecedor'], 'Dell Technologies')

        # Deletar
        del_resp = admin.delete(f'/api/documentacoes/{doc_id}')
        self.assertEqual(del_resp.status_code, 200)
        self.assertEqual(admin.get(f'/api/documentacoes/{doc_id}').status_code, 404)


if __name__ == '__main__':
    unittest.main()
