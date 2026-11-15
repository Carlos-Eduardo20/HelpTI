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
    def test_ticket_ids_autoincrement_from_six_digits_and_continue_existing_sequence(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / 'helpti.sqlite3'
            with patch.dict(os.environ, {
                'DB_TYPE': 'sqlite',
                'DB_SQLITE_PATH': str(database_path),
                'HELPTI_DEMO_MODE': 'false',
            }):
                database.initialize_database()
                connection = database.get_db_connection()
                first = connection.execute(
                    "INSERT INTO chamado (cliente, descricao) VALUES ('Cliente', 'Primeiro')"
                ).lastrowid
                connection.execute(
                    "INSERT INTO chamado (id_chamado, cliente, descricao) "
                    "VALUES (456789, 'Cliente antigo', 'Chamado existente')"
                )
                connection.commit()
                connection.close()

                database.initialize_database()
                connection = database.get_db_connection()
                next_id = connection.execute(
                    "INSERT INTO chamado (cliente, descricao) VALUES ('Cliente', 'Próximo')"
                ).lastrowid
                connection.commit()
                connection.close()

        self.assertEqual(first, 100000)
        self.assertEqual(next_id, 456790)

    def test_mysql_configuration_is_rejected_instead_of_using_an_empty_database(self):
        with patch.dict(os.environ, {'DB_TYPE': 'mysql'}):
            with self.assertRaisesRegex(RuntimeError, 'somente SQLite'):
                database.database_settings()

    def test_initialization_drops_legacy_equipment_table(self):
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
                        "INSERT INTO usuario (nome, tipo_usuario) VALUES ('Workspace', 'WORKSPACE')"
                    )
                    customer_id = connection.execute(
                        'SELECT last_insert_rowid()'
                    ).fetchone()[0]
                    connection.execute('''
                        CREATE TABLE equipamento_cliente (
                            id_equipamento INTEGER PRIMARY KEY AUTOINCREMENT,
                            id_cliente INTEGER NOT NULL,
                            nome TEXT NOT NULL,
                            quantidade INTEGER NOT NULL DEFAULT 1,
                            FOREIGN KEY (id_cliente) REFERENCES usuario(id_usuario)
                        )
                    ''')
                    connection.execute(
                        'INSERT INTO equipamento_cliente (id_cliente, nome) VALUES (%s, %s)',
                        (customer_id, 'Notebook'),
                    )
                    connection.commit()
                finally:
                    connection.close()

                database.initialize_database()
                connection = database.get_db_connection()
                try:
                    table = connection.execute(
                        "SELECT name FROM sqlite_master "
                        "WHERE type = 'table' AND name = 'equipamento_cliente'"
                    ).fetchone()
                    self.assertIsNone(table)
                    self.assertEqual(
                        connection.execute('PRAGMA user_version').fetchone()[0],
                        database.SCHEMA_VERSION,
                    )
                finally:
                    connection.close()

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
                    self.assertNotIn('equipamento_cliente', tables)
                    self.assertNotIn('setor', tables)
                    self.assertIn('contato_cliente', tables)
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
                    customer_columns = {
                        row[1] for row in connection.execute(
                            'PRAGMA table_info(cliente)'
                        ).fetchall()
                    }
                    ticket_columns = {
                        row[1] for row in connection.execute(
                            'PRAGMA table_info(chamado)'
                        ).fetchall()
                    }
                    self.assertIn('id_usuario', customer_columns)
                    self.assertNotIn('id_workspace', customer_columns)
                    self.assertIn('id_cliente', ticket_columns)
                finally:
                    connection.close()

    def test_account_email_is_unique_without_case_or_outer_space_differences(self):
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
                        'INSERT INTO usuario (nome, email, tipo_usuario) '
                        'VALUES (%s, %s, %s)',
                        ('Workspace', 'owner@example.test', 'WORKSPACE'),
                    )
                    connection.commit()
                    with self.assertRaises(sqlite3.IntegrityError):
                        connection.execute(
                            'INSERT INTO usuario (nome, email, tipo_usuario) '
                            'VALUES (%s, %s, %s)',
                            ('Workspace duplicado', ' Owner@Example.Test ', 'WORKSPACE'),
                        )
                finally:
                    connection.close()

    def test_customer_migration_separates_companies_contacts_and_ticket_relation(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / 'legacy-customers.sqlite3'
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
                        contato TEXT,
                        email TEXT,
                        telefone TEXT,
                        telefone_empresa TEXT,
                        endereco TEXT,
                        status TEXT,
                        tipo_usuario TEXT,
                        cnpj TEXT,
                        plano TEXT,
                        acoes TEXT,
                        workspace_name TEXT,
                        support_email TEXT,
                        senha_hash TEXT,
                        id_workspace INTEGER
                    );
                    INSERT INTO usuario (
                        id_usuario, nome, email, status, tipo_usuario
                    ) VALUES (1, 'Workspace', 'owner@example.test', 'ATIVO', 'WORKSPACE');
                    INSERT INTO usuario (
                        id_usuario, nome, contato, email, telefone, telefone_empresa,
                        endereco, status, tipo_usuario, cnpj, plano, acoes, id_workspace
                    ) VALUES (
                        2, 'Empresa Alpha', 'Ana Atualizada', 'ana@example.test',
                        '11999990000', '1133334444', 'Rua A', 'ATIVO', 'CLIENTE',
                        '123', 'Plano A', 'Ativa', 1
                    );
                    INSERT INTO usuario (
                        id_usuario, nome, contato, email, telefone, status,
                        tipo_usuario, id_workspace
                    ) VALUES (
                        3, 'Empresa Alpha', 'Outro Contato', 'outro@example.test',
                        '11666666666', 'ATIVO', 'CLIENTE', 1
                    );
                    CREATE TABLE cliente (
                        id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
                        id_usuario INTEGER NOT NULL,
                        nome TEXT NOT NULL,
                        contato TEXT,
                        email TEXT NOT NULL,
                        telefone TEXT NOT NULL,
                        id_workspace INTEGER,
                        FOREIGN KEY (id_workspace) REFERENCES usuario(id_usuario),
                        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
                    );
                    INSERT INTO cliente (id_cliente, id_usuario, nome, email, telefone, id_workspace)
                    VALUES
                        (1, 2, 'Ana Antiga', 'ana-antiga@example.test', '11888888888', 1),
                        (2, 2, 'Maria', 'maria@example.test', '11777777777', 1),
                        (3, 3, 'Outro Contato', 'outro@example.test', '11666666666', 1);
                    CREATE TABLE chamado (
                        id_chamado INTEGER PRIMARY KEY AUTOINCREMENT,
                        id_tipo_chamado INTEGER NOT NULL DEFAULT 1,
                        setor TEXT,
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
                        id_usuario INTEGER
                    );
                    INSERT INTO chamado (
                        id_chamado, cliente, descricao, email_cliente, telefone_cliente,
                        contato_cliente, telefone_contato, id_usuario
                    ) VALUES (
                        123456, 'Empresa Alpha', 'Falha de acesso', 'ana@example.test',
                        '1133334444', 'Ana Atualizada', '11999990000', 1
                    );
                    INSERT INTO chamado (
                        id_chamado, cliente, descricao, id_usuario
                    ) VALUES (
                        123457, 'Empresa Alpha', 'Registro ambiguo', 1
                    );
                ''')
                legacy.close()

                database.initialize_database()

                connection = database.get_db_connection()
                try:
                    company = connection.execute(
                        'SELECT id_cliente, id_usuario, nome, telefone_empresa '
                        'FROM cliente WHERE id_cliente = 2'
                    ).fetchone()
                    self.assertEqual(
                        tuple(company),
                        (2, 1, 'Empresa Alpha', '1133334444'),
                    )
                    customer_columns = {
                        row[1] for row in connection.execute(
                            'PRAGMA table_info(cliente)'
                        ).fetchall()
                    }
                    self.assertNotIn('id_workspace', customer_columns)
                    self.assertEqual(
                        connection.execute(
                            'SELECT nome FROM contato_cliente WHERE id_cliente = 2 '
                            'ORDER BY id_contato_cliente'
                        ).fetchall(),
                        [('Ana Atualizada',), ('Maria',)],
                    )
                    self.assertEqual(
                        connection.execute(
                            'SELECT id_cliente FROM chamado WHERE id_chamado = 123456'
                        ).fetchone()['id_cliente'],
                        2,
                    )
                    self.assertIsNone(connection.execute(
                        'SELECT id_cliente FROM chamado WHERE id_chamado = 123457'
                    ).fetchone()['id_cliente'])
                    self.assertEqual(
                        connection.execute(
                            "SELECT COUNT(*) FROM usuario WHERE tipo_usuario = 'CLIENTE'"
                        ).fetchone()[0],
                        0,
                    )
                    self.assertEqual(
                        connection.execute('PRAGMA foreign_key_check').fetchall(),
                        [],
                    )
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