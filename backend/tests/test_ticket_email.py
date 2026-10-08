import os
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch
from werkzeug.security import check_password_hash

from backend import app as app_module
from backend import database
from backend.startup_config import configure_startup
from backend.security_check import run_security_checks


class TicketEmailTests(unittest.TestCase):
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
        self.environment = patch.dict(os.environ, {
            'HELPTI_DEMO_MODE': 'false',
            'SMTP_HOST': 'smtp.example.test',
            'SMTP_PORT': '587',
            'SMTP_USER': 'help@example.test',
            'SMTP_PASSWORD': 'test-password',
            'SMTP_FROM': 'help@example.test',
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        database.initialize_database()
        app_module.app.config.update(TESTING=True, SECRET_KEY='test-secret')
        self.client = app_module.app.test_client()

    def _create_account(self):
        cadastro = {
            'nome': 'Ana Teste',
            'empresa': 'Empresa Teste',
            'email': 'admin@outlook.com',
            'senha': 'senha-segura-123',
        }
        smtp_context = MagicMock()
        smtp_server = smtp_context.__enter__.return_value
        with patch.object(app_module.smtplib, 'SMTP', return_value=smtp_context):
            response = self.client.post('/api/contas', json=cadastro)
        self.assertEqual(response.status_code, 202, response.get_json())
        message = smtp_server.send_message.call_args.args[0]
        code = re.search(r'\b(\d{6})\b', message.get_content()).group(1)
        confirmation = self.client.post('/api/confirmar-conta', json={
            'email': cadastro['email'],
            'codigo': code,
        })
        self.assertEqual(confirmation.status_code, 201, confirmation.get_json())
        return confirmation.get_json()

    def _prepare_ticket(self):
        account = self._create_account()
        connection = database.get_db_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO setor (nome, descricao) VALUES ('Suporte', 'Atendimento')"
            )
            sector_id = cursor.lastrowid
            cursor.execute(
                'UPDATE grupo_solucionadores SET id_setor = %s WHERE id_grupo_solucionadores = %s',
                (sector_id, account['id'])
            )
            connection.commit()
            return sector_id
        finally:
            connection.close()

    def _ticket_payload(self, sector_id):
        return {
            'cliente': 'Empresa Teste',
            'descricao': 'Não consigo acessar o sistema.',
            'email_cliente': 'solicitante@example.test',
            'telefone_cliente': '11999990000',
            'contato_cliente': 'Ana Teste',
            'telefone_contato': '11999990000',
            'id_setor': sector_id,
            'id_grupo_solucionadores': self.client.get('/api/sessao').get_json()['id'],
        }

    def test_startup_prompt_selects_test_or_company_database_per_environment(self):
        project_dir = Path(self.temp_dir.name) / 'startup-config'
        with patch.dict(os.environ, {
            'HELPTI_DEMO_MODE': 'prompt',
            'HELPTI_RUNTIME_ENV': 'local',
            'HELPTI_DB_PATH': '',
        }):
            demo = configure_startup(
                input_fn=lambda _prompt: 's',
                project_dir=project_dir,
            )
        self.assertTrue(demo['demo_mode'])
        self.assertEqual(demo['database_path'], project_dir / 'instance' / 'helpti.sqlite3')

        with patch.dict(os.environ, {
            'HELPTI_DEMO_MODE': 'prompt',
            'HELPTI_RUNTIME_ENV': 'codespace',
            'HELPTI_DB_PATH': '',
        }):
            company = configure_startup(
                input_fn=lambda _prompt: 'n',
                project_dir=project_dir,
            )
        self.assertFalse(company['demo_mode'])
        self.assertEqual(
            company['database_path'],
            project_dir / 'instance' / 'helpti-codespace-empresa.sqlite3',
        )
        self.assertNotEqual(demo['database_path'], company['database_path'])

    def test_startup_retries_invalid_answers_and_respects_explicit_mode(self):
        answers = iter(('talvez', 'sim'))
        messages = []
        with patch.dict(os.environ, {
            'HELPTI_DEMO_MODE': 'prompt',
            'HELPTI_RUNTIME_ENV': 'local',
            'HELPTI_DB_PATH': '',
        }):
            result = configure_startup(
                input_fn=lambda _prompt: next(answers),
                output_fn=messages.append,
                project_dir=self.temp_dir.name,
            )
        self.assertTrue(result['demo_mode'])
        self.assertEqual(len(messages), 1)

        with patch.dict(os.environ, {
            'HELPTI_DEMO_MODE': 'false',
            'HELPTI_RUNTIME_ENV': 'local',
            'HELPTI_DB_PATH': '',
        }):
            result = configure_startup(
                input_fn=lambda _prompt: self.fail('Não deveria solicitar entrada.'),
                project_dir=self.temp_dir.name,
            )
        self.assertFalse(result['demo_mode'])

    def test_new_account_starts_without_demo_tickets_and_can_log_in(self):
        connection = database.get_db_connection()
        try:
            self.assertEqual(
                connection.execute('SELECT COUNT(*) FROM chamado').fetchone()[0], 0
            )
            self.assertEqual(
                connection.execute('SELECT COUNT(*) FROM usuario WHERE tipo_usuario = ?',
                                   ('CLIENTE',)).fetchone()[0],
                0
            )
            self.assertEqual(
                connection.execute('SELECT COUNT(*) FROM cliente').fetchone()[0], 0
            )
            self.assertEqual(
                connection.execute('SELECT COUNT(*) FROM setor').fetchone()[0], 0
            )
        finally:
            connection.close()

        account = self._create_account()
        self.assertEqual(self.client.get('/api/chamados').get_json(), [])
        self.assertEqual(self.client.post('/api/logout').status_code, 200)

        response = self.client.post('/api/login', json={
            'email': account['email'],
            'senha': 'senha-segura-123',
        })
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()['id'], account['id'])

    def test_signup_blocks_gmail_and_yahoo_but_allows_outlook(self):
        for email in ('admin@gmail.com', 'admin@yahoo.com.br'):
            response = self.client.post('/api/contas', json={
                'nome': 'Admin',
                'empresa': 'Empresa',
                'email': email,
                'senha': 'senha-segura-123',
            })
            self.assertEqual(response.status_code, 400)
            self.assertIn('Gmail e Yahoo', response.get_json()['erro'])

        smtp_context = MagicMock()
        with patch.object(app_module.smtplib, 'SMTP', return_value=smtp_context):
            response = self.client.post('/api/contas', json={
                'nome': 'Admin',
                'empresa': 'Empresa',
                'email': 'admin@outlook.com',
                'senha': 'senha-segura-123',
            })
        self.assertEqual(response.status_code, 202, response.get_json())
        message = smtp_context.__enter__.return_value.send_message.call_args.args[0]
        code = re.search(r'\b(\d{6})\b', message.get_content()).group(1)
        account = self.client.post('/api/confirmar-conta', json={
            'email': 'admin@outlook.com',
            'codigo': code,
        })
        self.assertEqual(account.status_code, 201, account.get_json())
        self.assertEqual(account.get_json()['email'], 'admin@outlook.com')

    def test_signup_requires_mailbox_code_before_creating_workspace(self):
        smtp_context = MagicMock()
        with patch.object(app_module.smtplib, 'SMTP', return_value=smtp_context):
            signup = self.client.post('/api/contas', json={
                'nome': 'Ana Teste',
                'empresa': 'Empresa Teste',
                'email': 'admin@outlook.com',
                'senha': 'senha-segura-123',
            })
        self.assertEqual(signup.status_code, 202, signup.get_json())
        connection = database.get_db_connection()
        try:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM usuario WHERE tipo_usuario = 'WORKSPACE'"
                ).fetchone()[0],
                0,
            )
        finally:
            connection.close()

        message = smtp_context.__enter__.return_value.send_message.call_args.args[0]
        code = re.search(r'\b(\d{6})\b', message.get_content()).group(1)
        codigo_incorreto = f'{(int(code) + 1) % 1_000_000:06d}'
        invalid = self.client.post('/api/confirmar-conta', json={
            'email': 'admin@outlook.com',
            'codigo': codigo_incorreto,
        })
        self.assertEqual(invalid.status_code, 400)

        confirmed = self.client.post('/api/confirmar-conta', json={
            'email': 'admin@outlook.com',
            'codigo': code,
        })
        self.assertEqual(confirmed.status_code, 201, confirmed.get_json())
        self.assertEqual(self.client.get('/api/sessao').status_code, 200)

    def test_microsoft_sign_in_links_verified_email_and_starts_session(self):
        account = self._create_account()
        microsoft = MagicMock()
        microsoft.authorize_access_token.return_value = {
            'userinfo': {
                'sub': 'microsoft-subject-123',
                'tid': 'microsoft-tenant-456',
                'email': account['email'],
                'name': account['nome'],
            }
        }

        with patch.object(app_module, 'cliente_microsoft', return_value=microsoft):
            response = self.client.get('/auth/microsoft/callback')

        claims_options = microsoft.authorize_access_token.call_args.kwargs['claims_options']
        self.assertTrue(claims_options['iss']['essential'])
        self.assertTrue(claims_options['tid']['essential'])
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers['Location'].endswith(
            '/frontend/pages/login.html?microsoft=ok'
        ))
        session_response = self.client.get('/api/sessao')
        self.assertEqual(session_response.status_code, 200)
        self.assertEqual(session_response.get_json()['empresaNome'], 'Empresa Teste')

        connection = database.get_db_connection()
        try:
            self.assertEqual(
                connection.execute('SELECT COUNT(*) FROM identidade_microsoft').fetchone()[0],
                1,
            )
        finally:
            connection.close()

    def test_microsoft_issuer_validation_matches_only_the_token_tenant(self):
        tenant_id = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
        claims = {'tid': tenant_id}
        self.assertTrue(app_module._validar_issuer_microsoft(
            claims, f'https://login.microsoftonline.com/{tenant_id}/v2.0'
        ))
        self.assertFalse(app_module._validar_issuer_microsoft(
            claims, 'https://attacker.example/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
        ))
        self.assertFalse(app_module._tenant_microsoft_valido({}, 'not-a-tenant-id'))

    def test_microsoft_sign_in_without_configuration_returns_to_login_with_explanation(self):
        with patch.dict(os.environ, {
            'MICROSOFT_CLIENT_ID': '',
            'MICROSOFT_CLIENT_SECRET': '',
        }):
            response = self.client.get('/auth/microsoft')

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers['Location'].endswith(
            '/frontend/pages/login.html?erro=microsoft_nao_configurado'
        ))

    def test_documented_demo_account_can_log_in(self):
        self.database_path.unlink(missing_ok=True)
        with patch.dict(os.environ, {'HELPTI_DEMO_MODE': 'true'}):
            database.initialize_database()
            self.assertTrue(database.demo_mode_enabled())
            connection = database.get_db_connection()
            try:
                row = connection.execute(
                    "SELECT senha FROM grupo_solucionadores WHERE email = 'test@helpiti.com'"
                ).fetchone()
                self.assertIsNotNone(row)
                self.assertTrue(check_password_hash(row['senha'], 'HelpTI2026!'))
                self.assertEqual(
                    connection.execute('SELECT COUNT(*) FROM chamado').fetchone()[0], 0
                )
                self.assertEqual(
                    connection.execute('SELECT COUNT(*) FROM cliente').fetchone()[0], 0
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM usuario WHERE tipo_usuario = 'CLIENTE'"
                    ).fetchone()[0],
                    0
                )
                self.assertEqual(
                    connection.execute('SELECT COUNT(*) FROM setor').fetchone()[0], 1
                )
                demo = connection.execute('''
                    SELECT usuario.nome AS empresa, membro.id_grupo_solucionadores,
                           membro.id_setor, membro.nome, membro.cargo
                    FROM grupo_solucionadores AS membro
                    JOIN usuario ON usuario.id_usuario = membro.id_usuario
                    WHERE membro.email = 'test@helpiti.com'
                ''').fetchone()
                self.assertEqual(demo['empresa'], 'HelpTI')
                self.assertEqual(demo['nome'], 'Conta teste HelpTI')
                self.assertEqual(demo['cargo'], 'Administrador')
                self.assertIsNotNone(demo['id_setor'])
            finally:
                connection.close()

            response = self.client.post('/api/login', json={
                'email': 'test@helpiti.com',
                'senha': 'HelpTI2026!',
            })
        self.assertEqual(response.status_code, 200, response.get_json())
        with patch.dict(os.environ, {'HELPTI_DEMO_MODE': 'true'}), \
                patch.object(app_module.smtplib, 'SMTP') as smtp:
            ticket_response = self.client.post('/api/chamados', json={
                'cliente': 'Cliente de teste',
                'descricao': 'Chamado criado no teste automatizado.',
                'email_cliente': 'cliente@example.test',
                'telefone_cliente': '11999990000',
                'contato_cliente': 'Contato Teste',
                'telefone_contato': '11999990000',
                'id_setor': demo['id_setor'],
                'id_grupo_solucionadores': demo['id_grupo_solucionadores'],
            })
        self.assertEqual(ticket_response.status_code, 201, ticket_response.get_json())
        self.assertTrue(ticket_response.get_json()['email_enviado'])

    def test_legacy_demo_password_hash_is_updated(self):
        legacy_hash = (
            'pbkdf2:sha256:600000$helpti-demo-salt$'
            'ed4fcd7c8cb5bf394a9afaf63f2d687d4dd9a68e5728307f9ab8291b4a671aac'
        )
        with patch.dict(os.environ, {'HELPTI_DEMO_MODE': 'true'}):
            database.initialize_database()
            connection = database.get_db_connection()
            try:
                connection.execute(
                    "UPDATE grupo_solucionadores SET senha = ? WHERE email = 'test@helpiti.com'",
                    (legacy_hash,)
                )
                connection.commit()
            finally:
                connection.close()

            database.initialize_database()

        connection = database.get_db_connection()
        try:
            row = connection.execute(
                "SELECT senha FROM grupo_solucionadores WHERE email = 'test@helpiti.com'"
            ).fetchone()
            self.assertTrue(check_password_hash(row['senha'], 'HelpTI2026!'))
        finally:
            connection.close()

    def test_legacy_plaintext_team_password_is_hashed_on_startup(self):
        account = self._create_account()
        connection = database.get_db_connection()
        try:
            connection.execute(
                'UPDATE grupo_solucionadores SET senha = ? WHERE id_grupo_solucionadores = ?',
                ('senha-legada-123', account['id'])
            )
            connection.commit()
        finally:
            connection.close()

        database.initialize_database()
        connection = database.get_db_connection()
        try:
            stored_password = connection.execute(
                'SELECT senha FROM grupo_solucionadores WHERE id_grupo_solucionadores = ?',
                (account['id'],)
            ).fetchone()['senha']
        finally:
            connection.close()
        self.assertNotEqual(stored_password, 'senha-legada-123')
        self.assertTrue(check_password_hash(stored_password, 'senha-legada-123'))

    def test_opening_and_resolving_ticket_send_email_when_smtp_is_configured(self):
        sector_id = self._prepare_ticket()
        smtp_context = MagicMock()
        smtp_server = smtp_context.__enter__.return_value

        with patch.object(app_module.smtplib, 'SMTP', return_value=smtp_context) as smtp:
            response = self.client.post(
                '/api/chamados', json=self._ticket_payload(sector_id)
            )
            self.assertEqual(response.status_code, 201, response.get_json())
            ticket = response.get_json()
            self.assertTrue(ticket['email_enviado'])
            first_message = smtp_server.send_message.call_args.args[0]
            self.assertEqual(first_message['To'], 'solicitante@example.test')
            self.assertEqual(first_message['Subject'], f"Chamado #{ticket['id_chamado']} recebido")

            started = self.client.put(
                f"/api/chamados/{ticket['id_chamado']}", json={'acao': 'iniciar'}
            )
            self.assertEqual(started.status_code, 200, started.get_json())

            resolved = self.client.put(
                f"/api/chamados/{ticket['id_chamado']}",
                json={'acao': 'encerrar', 'descricao_final': 'Acesso restabelecido.'},
            )
            self.assertEqual(resolved.status_code, 200, resolved.get_json())
            self.assertTrue(resolved.get_json()['email_enviado'])
            self.assertEqual(resolved.get_json()['status'], 'RESOLVIDO')
            reports = self.client.get('/api/relatorios?periodo=todos')
            self.assertEqual(reports.status_code, 200, reports.get_json())
            self.assertEqual(reports.get_json()['total_resolvidos'], 1)
            self.assertEqual(smtp.call_count, 2)

    def test_ticket_is_saved_and_warning_returned_when_smtp_is_not_configured(self):
        sector_id = self._prepare_ticket()
        with patch.dict(os.environ, {
            'SMTP_HOST': '',
            'SMTP_USER': '',
            'SMTP_PASSWORD': '',
            'SMTP_FROM': '',
        }), patch.object(app_module.smtplib, 'SMTP') as smtp:
            response = self.client.post(
                '/api/chamados', json=self._ticket_payload(sector_id)
            )

        self.assertEqual(response.status_code, 201, response.get_json())
        self.assertFalse(response.get_json()['email_enviado'])
        self.assertIn('não está configurado', response.get_json()['aviso_email'])
        smtp.assert_not_called()
        self.assertEqual(len(self.client.get('/api/chamados').get_json()), 1)

    def test_password_recovery_sends_one_time_code_and_replaces_password(self):
        account = self._create_account()
        smtp_context = MagicMock()
        smtp_server = smtp_context.__enter__.return_value

        with patch.object(app_module.smtplib, 'SMTP', return_value=smtp_context):
            response = self.client.post(
                '/api/solicitar-codigo-recuperacao',
                json={'email': account['email']}
            )
        self.assertEqual(response.status_code, 202, response.get_json())
        message = smtp_server.send_message.call_args.args[0]
        self.assertEqual(message['To'], account['email'])
        code = re.search(r'\b(\d{6})\b', message.get_content()).group(1)

        reset = self.client.post('/api/redefinir-senha', json={
            'email': account['email'],
            'codigo': code,
            'senha': 'nova-senha-segura-456',
        })
        self.assertEqual(reset.status_code, 200, reset.get_json())
        self.assertEqual(self.client.post('/api/logout').status_code, 200)
        self.assertEqual(self.client.post('/api/login', json={
            'email': account['email'],
            'senha': 'senha-segura-123',
        }).status_code, 401)
        self.assertEqual(self.client.post('/api/login', json={
            'email': account['email'],
            'senha': 'nova-senha-segura-456',
        }).status_code, 200)
        self.assertEqual(self.client.post('/api/redefinir-senha', json={
            'email': account['email'],
            'codigo': code,
            'senha': 'outra-senha-segura-789',
        }).status_code, 400)

    def test_password_recovery_requests_are_rate_limited(self):
        account = self._create_account()
        smtp_context = MagicMock()
        with patch.object(app_module.smtplib, 'SMTP', return_value=smtp_context) as smtp:
            first = self.client.post(
                '/api/solicitar-codigo-recuperacao',
                json={'email': account['email']}
            )
            second = self.client.post(
                '/api/solicitar-codigo-recuperacao',
                json={'email': account['email']}
            )

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(first.get_json()['mensagem'], second.get_json()['mensagem'])
        smtp.assert_called_once()

    def test_security_check_passes_safe_local_configuration(self):
        app_module.app.config['SECRET_KEY'] = 'x' * 48
        output = StringIO()
        with patch.dict(os.environ, {
            'HELPTI_HOST': '127.0.0.1',
            'HELPTI_DEBUG': 'true',
            'HELPTI_HTTPS_ONLY': 'false',
            'HELPTI_DEMO_MODE': 'true',
        }), redirect_stdout(output):
            passed = run_security_checks(app_module.app)
        self.assertTrue(passed)
        self.assertIn('Validando a configuração básica de segurança', output.getvalue())

    def test_security_check_rejects_exposed_debug_without_secure_cookie(self):
        app_module.app.config['SECRET_KEY'] = 'x' * 48
        output = StringIO()
        with patch.dict(os.environ, {
            'HELPTI_HOST': '0.0.0.0',
            'HELPTI_DEBUG': 'true',
            'HELPTI_HTTPS_ONLY': 'false',
            'HELPTI_DEMO_MODE': 'true',
        }), redirect_stdout(output):
            passed = run_security_checks(app_module.app)
        self.assertFalse(passed)
        self.assertIn('[FALHA] Cookie seguro para acesso remoto', output.getvalue())
        self.assertIn('[FALHA] Modo de depuração seguro', output.getvalue())


if __name__ == '__main__':
    unittest.main()
