import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from werkzeug.security import check_password_hash

from backend import app as app_module
from backend import database


class SQLiteDatabaseTests(unittest.TestCase):
    def test_mysql_configuration_is_rejected_instead_of_using_an_empty_database(self):
        with patch.dict(os.environ, {'DB_TYPE': 'mysql'}):
            with self.assertRaisesRegex(RuntimeError, 'somente SQLite'):
                database.database_settings()

    def test_initialization_preserves_records_in_configured_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / 'helpti.sqlite3'
            with patch.dict(os.environ, {
                'DB_TYPE': 'sqlite',
                'DB_SQLITE_PATH': str(database_path),
                'HELPTI_DEMO_MODE': 'false',
            }):
                database.initialize_database()
                connection = database.get_db_connection()
                try:
                    connection.execute(
                        'INSERT INTO tipo_chamado (nome, classificacao, descricao) '
                        'VALUES (%s, %s, %s)',
                        ('Persistente', 'Teste', 'Registro de validação'),
                    )
                    connection.commit()
                finally:
                    connection.close()

                database.initialize_database()
                connection = database.get_db_connection()
                try:
                    record = connection.execute(
                        'SELECT descricao FROM tipo_chamado WHERE nome = %s',
                        ('Persistente',),
                    ).fetchone()
                    self.assertEqual(record['descricao'], 'Registro de validação')
                finally:
                    connection.close()

    def test_initialization_creates_demo_account_and_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / 'helpti.sqlite3'
            with patch.dict(os.environ, {
                'DB_TYPE': 'sqlite',
                'DB_SQLITE_PATH': str(database_path),
                'HELPTI_DEMO_MODE': 'true',
            }):
                database.initialize_database()
                connection = database.get_db_connection()
                try:
                    account = connection.execute(
                        'SELECT senha FROM grupo_solucionadores WHERE email = %s',
                        (database.DEMO_EMAIL,),
                    ).fetchone()
                    self.assertIsNotNone(account)
                    self.assertTrue(check_password_hash(account['senha'], 'HelpTI2026!!'))
                    self.assertEqual(
                        connection.execute('SELECT COUNT(*) FROM tipo_chamado').fetchone()[0],
                        4,
                    )
                finally:
                    connection.close()

                app_module.app.config.update(TESTING=True)
                client = app_module.app.test_client()
                response = client.post('/api/login', json={
                    'email': database.DEMO_EMAIL,
                    'senha': 'HelpTI2026!!',
                })
                self.assertEqual(response.status_code, 200, response.get_json())
                member_response = client.post('/api/equipe', json={
                    'nome': 'Tecnico SQLite',
                    'email': 'tecnico@helpti.test',
                    'setor': 'Suporte',
                })
                self.assertEqual(member_response.status_code, 201, member_response.get_json())
                connection = database.get_db_connection()
                try:
                    member_record = connection.execute(
                        'SELECT cargo, senha, permissoes, setor FROM grupo_solucionadores '
                        'WHERE email = %s',
                        ('tecnico@helpti.test',),
                    ).fetchone()
                    self.assertEqual(member_record['cargo'], 'Técnico')
                    self.assertEqual(member_record['senha'], '')
                    self.assertEqual(member_record['permissoes'], '[]')
                finally:
                    connection.close()
                app_module._LOGIN_RATE_LIMIT.clear()
                member_login = client.post('/api/login', json={
                    'email': 'tecnico@helpti.test',
                    'senha': 'qualquer-senha',
                })
                self.assertEqual(member_login.status_code, 401)
                stats = client.get('/api/admin/db/stats')
                self.assertEqual(stats.status_code, 200, stats.get_json())
                self.assertTrue(stats.get_json()['caminho'].startswith('sqlite:///'))
                backup = client.get('/api/admin/db/backup')
                self.assertEqual(backup.status_code, 200, backup.get_json())
                self.assertIn('PRAGMA foreign_keys = OFF;', backup.get_data(as_text=True))
            self.assertTrue(database_path.is_file())

    def test_schema_has_only_text_sectors_and_no_retired_auth_tables(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / 'helpti.sqlite3'
            with patch.dict(os.environ, {
                'DB_TYPE': 'sqlite',
                'DB_SQLITE_PATH': str(database_path),
                'HELPTI_DEMO_MODE': 'false',
            }):
                database.initialize_database()
                connection = database.get_db_connection()
                try:
                    tables = {
                        row[0] for row in connection.execute(
                            "SELECT name FROM sqlite_master WHERE type = 'table'"
                        ).fetchall()
                    }
                    self.assertNotIn('setor', tables)
                    self.assertTrue({
                        'codigo_recuperacao_senha',
                        'identidade_microsoft',
                        'login_rate_limit',
                        'verificacao_cadastro_email',
                    }.isdisjoint(tables))
                    group_columns = {
                        row[1] for row in connection.execute(
                            'PRAGMA table_info(grupo_solucionadores)'
                        ).fetchall()
                    }
                    self.assertIn('setor', group_columns)
                    self.assertNotIn('id_setor', group_columns)
                finally:
                    connection.close()

    def test_legacy_sector_data_is_preserved_when_schema_is_migrated(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / 'legacy.sqlite3'
            with patch.dict(os.environ, {
                'DB_TYPE': 'sqlite',
                'DB_SQLITE_PATH': str(database_path),
                'HELPTI_DEMO_MODE': 'false',
            }):
                legacy = sqlite3.connect(database_path)
                legacy.executescript('''
                    CREATE TABLE usuario (
                        id_usuario INTEGER PRIMARY KEY,
                        nome TEXT,
                        tipo_usuario TEXT,
                        id_workspace INTEGER
                    );
                    INSERT INTO usuario VALUES (1, 'Empresa', 'WORKSPACE', NULL);
                    CREATE TABLE setor (
                        id_setor INTEGER PRIMARY KEY,
                        nome TEXT NOT NULL
                    );
                    INSERT INTO setor VALUES (1, 'Suporte legado');
                    CREATE TABLE grupo_solucionadores (
                        id_grupo_solucionadores INTEGER PRIMARY KEY,
                        descricao TEXT,
                        nivel INTEGER,
                        data_inicio TEXT,
                        data_fim TEXT,
                        nome TEXT,
                        email TEXT,
                        cargo TEXT,
                        valor_hora NUMERIC,
                        telefone TEXT,
                        status TEXT NOT NULL DEFAULT 'ATIVO',
                        senha TEXT NOT NULL DEFAULT '',
                        permissoes TEXT NOT NULL DEFAULT '[]',
                        foto_perfil TEXT,
                        id_usuario INTEGER NOT NULL,
                        id_setor INTEGER,
                        email_verificado INTEGER,
                        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario),
                        FOREIGN KEY (id_setor) REFERENCES setor(id_setor)
                    );
                    INSERT INTO grupo_solucionadores (
                        id_grupo_solucionadores, nome, email, id_usuario, id_setor
                    ) VALUES (1, 'Tecnico legado', 'tecnico@example.test', 1, 1);
                    CREATE TABLE chamado (
                        id_chamado INTEGER PRIMARY KEY,
                        id_tipo_chamado INTEGER NOT NULL DEFAULT 1,
                        id_grupo_solucionadores INTEGER,
                        status TEXT NOT NULL DEFAULT 'ABERTO',
                        cliente TEXT NOT NULL,
                        assunto TEXT,
                        descricao TEXT,
                        email_cliente TEXT,
                        telefone_cliente TEXT,
                        contato_cliente TEXT,
                        telefone_contato TEXT,
                        descricao_final TEXT,
                        documentacao TEXT,
                        tempo_decorrido_segundos INTEGER NOT NULL DEFAULT 0,
                        tempo_inicio TEXT,
                        data_abertura TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        data_fechamento TEXT,
                        data_agendada TEXT,
                        hora_agendada TEXT,
                        classificacao TEXT,
                        id_usuario INTEGER,
                        id_setor INTEGER,
                        FOREIGN KEY (id_tipo_chamado) REFERENCES tipo_chamado(id_tipo_chamado),
                        FOREIGN KEY (id_grupo_solucionadores)
                            REFERENCES grupo_solucionadores(id_grupo_solucionadores),
                        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario),
                        FOREIGN KEY (id_setor) REFERENCES setor(id_setor)
                    );
                    INSERT INTO chamado (
                        id_chamado, cliente, descricao, id_usuario, id_setor,
                        id_grupo_solucionadores
                    ) VALUES (1, 'Cliente legado', 'Falha antiga', 1, 1, 1);
                    CREATE TABLE escalonamento (
                        id_escalonamento INTEGER PRIMARY KEY,
                        id_chamado INTEGER NOT NULL,
                        motivo TEXT,
                        nivel INTEGER,
                        id_grupo_destino INTEGER,
                        data_escalonamento TEXT,
                        id_setor_destino INTEGER,
                        FOREIGN KEY (id_chamado) REFERENCES chamado(id_chamado),
                        FOREIGN KEY (id_grupo_destino)
                            REFERENCES grupo_solucionadores(id_grupo_solucionadores),
                        FOREIGN KEY (id_setor_destino) REFERENCES setor(id_setor)
                    );
                    INSERT INTO escalonamento (
                        id_escalonamento, id_chamado, id_setor_destino
                    ) VALUES (1, 1, 1);
                    CREATE TABLE codigo_recuperacao_senha (id INTEGER);
                    CREATE TABLE identidade_microsoft (id INTEGER);
                    CREATE TABLE login_rate_limit (id INTEGER);
                    CREATE TABLE verificacao_cadastro_email (id INTEGER);
                ''')
                legacy.close()

                database.initialize_database()

                connection = database.get_db_connection()
                try:
                    self.assertEqual(
                        connection.execute(
                            'SELECT setor FROM grupo_solucionadores WHERE id_grupo_solucionadores = 1'
                        ).fetchone()['setor'],
                        'Suporte legado',
                    )
                    self.assertEqual(
                        connection.execute(
                            'SELECT setor FROM chamado WHERE id_chamado = 1'
                        ).fetchone()['setor'],
                        'Suporte legado',
                    )
                    self.assertEqual(
                        connection.execute(
                            'SELECT setor_destino FROM escalonamento WHERE id_escalonamento = 1'
                        ).fetchone()['setor_destino'],
                        'Suporte legado',
                    )
                    tables = {
                        row[0] for row in connection.execute(
                            "SELECT name FROM sqlite_master WHERE type = 'table'"
                        ).fetchall()
                    }
                    self.assertNotIn('setor', tables)
                    self.assertTrue({
                        'codigo_recuperacao_senha',
                        'identidade_microsoft',
                        'login_rate_limit',
                        'verificacao_cadastro_email',
                    }.isdisjoint(tables))
                    self.assertEqual(
                        connection.execute('PRAGMA foreign_key_check').fetchall(),
                        [],
                    )
                finally:
                    connection.close()


if __name__ == '__main__':
    unittest.main()