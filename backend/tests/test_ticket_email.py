import os
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import MagicMock, patch
from werkzeug.security import check_password_hash

from backend import app as app_module
from backend import database
from backend.startup_config import configure_startup
from backend.security_check import run_security_checks
from backend.tests.db_support import use_temp_database


class TicketEmailTests(unittest.TestCase):
    def setUp(self):
        use_temp_database(self)
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
        app_module._LOGIN_RATE_LIMIT.clear()
        self.client = app_module.app.test_client()

    def _create_account(self):
        cadastro = {
            'nome': 'Ana Teste',
            'empresa': 'Empresa Teste',
            'email': 'admin@outlook.com',
            'senha': 'senha-segura-123',
        }
        response = self.client.post('/api/contas', json=cadastro)
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()

    def _prepare_ticket(self):
        self._create_account()
        return 'Suporte'

    def _ticket_payload(self, sector_id):
        return {
            'cliente': 'Empresa Teste',
            'descricao': 'Não consigo acessar o sistema.',
            'email_cliente': 'solicitante@example.test',
            'telefone_cliente': '11999990000',
            'contato_cliente': 'Ana Teste',
            'telefone_contato': '11999990000',
            'setor': sector_id,
            'id_grupo_solucionadores': self.client.get('/api/sessao').get_json()['id'],
        }

    def test_startup_prompt_selects_demo_mode_and_default_database(self):
        with patch.dict(os.environ, {'HELPTI_DEMO_MODE': 'prompt'}):
            os.environ.pop('DB_SQLITE_PATH', None)
            demo = configure_startup(input_fn=lambda _prompt: 's')
            self.assertTrue(demo['demo_mode'])
            self.assertEqual(demo['database'], 'instance/helpti.sqlite3')

        with patch.dict(os.environ, {'HELPTI_DEMO_MODE': 'prompt'}):
            company = configure_startup(input_fn=lambda _prompt: 'n')
            self.assertFalse(company['demo_mode'])
            self.assertEqual(os.environ['HELPTI_DEMO_MODE'], 'false')

    def test_startup_retries_invalid_answers_and_respects_explicit_mode(self):
        answers = iter(('talvez', 'sim'))
        messages = []
        with patch.dict(os.environ, {'HELPTI_DEMO_MODE': 'prompt'}):
            result = configure_startup(
                input_fn=lambda _prompt: next(answers),
                output_fn=messages.append,
            )
        self.assertTrue(result['demo_mode'])
        self.assertEqual(len(messages), 1)

        with patch.dict(os.environ, {'HELPTI_DEMO_MODE': 'false'}):
            result = configure_startup(
                input_fn=lambda _prompt: self.fail('Não deveria solicitar entrada.'),
            )
        self.assertFalse(result['demo_mode'])

    def test_new_account_starts_without_demo_tickets_and_can_log_in(self):
        connection = database.get_db_connection()
        try:
            self.assertEqual(
                connection.execute('SELECT COUNT(*) FROM chamado').fetchone()[0], 0
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM usuario WHERE tipo_usuario = 'CLIENTE'").fetchone()[0],
                0
            )
            self.assertEqual(
                connection.execute('SELECT COUNT(*) FROM cliente').fetchone()[0], 0
            )
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            self.assertNotIn('setor', tables)
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

        account = self.client.post('/api/contas', json={
            'nome': 'Admin',
            'empresa': 'Empresa',
            'email': 'admin@outlook.com',
            'senha': 'senha-segura-123',
        })
        self.assertEqual(account.status_code, 201, account.get_json())
        self.assertEqual(account.get_json()['email'], 'admin@outlook.com')
        connection = database.get_db_connection()
        try:
            self.assertEqual(connection.execute(
                "SELECT COUNT(*) FROM usuario WHERE tipo_usuario = 'WORKSPACE'"
            ).fetchone()[0], 1)
        finally:
            connection.close()
        self.assertEqual(self.client.get('/api/sessao').status_code, 200)
        for endpoint in (
            '/api/confirmar-conta',
            '/api/solicitar-codigo-recuperacao',
            '/api/redefinir-senha',
            '/auth/microsoft',
            '/auth/microsoft/callback',
        ):
            self.assertIn(self.client.post(endpoint).status_code, (404, 405))

    def test_documented_demo_account_can_log_in(self):
        with patch.dict(os.environ, {'HELPTI_DEMO_MODE': 'true'}):
            database.initialize_database()
            self.assertTrue(database.demo_mode_enabled())
            connection = database.get_db_connection()
            try:
                row = connection.execute(
                    "SELECT senha FROM grupo_solucionadores WHERE email = 'test@helpiti.com'"
                ).fetchone()
                self.assertIsNotNone(row)
                self.assertTrue(check_password_hash(row['senha'], 'HelpTI2026!!'))
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
                tables = {
                    item[0] for item in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                self.assertNotIn('setor', tables)
                demo = connection.execute('''
                    SELECT usuario.nome AS empresa, membro.id_grupo_solucionadores,
                           membro.setor, membro.nome, membro.cargo
                    FROM grupo_solucionadores AS membro
                    JOIN usuario ON usuario.id_usuario = membro.id_usuario
                    WHERE membro.email = 'test@helpiti.com'
                ''').fetchone()
                self.assertEqual(demo['empresa'], 'HelpTI')
                self.assertEqual(demo['nome'], 'Conta teste HelpTI')
                self.assertEqual(demo['cargo'], 'Administrador')
                self.assertEqual(demo['setor'], 'Suporte')
            finally:
                connection.close()

            response = self.client.post('/api/login', json={
                'email': 'test@helpiti.com',
                'senha': 'HelpTI2026!!',
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
                'setor': demo['setor'],
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
                    "UPDATE grupo_solucionadores SET senha = %s WHERE email = 'test@helpiti.com'",
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
            self.assertTrue(check_password_hash(row['senha'], 'HelpTI2026!!'))
        finally:
            connection.close()

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
            self.assertEqual(
                first_message['Subject'],
                f"Chamado #TK-{ticket['id_chamado']:06d} recebido",
            )

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

    def test_mutating_requests_reject_cross_site_origins(self):
        response = self.client.post(
            '/api/logout',
            headers={
                'Origin': 'https://attacker.example',
                'Sec-Fetch-Site': 'cross-site',
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_login_attempts_are_rate_limited_per_client(self):
        for _ in range(10):
            response = self.client.post('/api/login', json={
                'email': 'unknown@example.test',
                'senha': 'wrong-password',
            })
            self.assertEqual(response.status_code, 401)

        limited = self.client.post('/api/login', json={
            'email': 'unknown@example.test',
            'senha': 'wrong-password',
        })

        self.assertEqual(limited.status_code, 429)

    def test_security_headers_are_set_on_responses(self):
        response = self.client.get('/api/health')

        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
        self.assertEqual(
            response.headers['Referrer-Policy'],
            'strict-origin-when-cross-origin',
        )

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
