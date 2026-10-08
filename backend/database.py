import os
import json
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from werkzeug.security import generate_password_hash

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = Path(os.getenv(
    'HELPTI_DB_PATH', PROJECT_DIR / 'instance' / 'helpti.sqlite3'
)).expanduser()


class SQLiteCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=()):
        query = re.sub(r'\s+FOR UPDATE\b', '', query, flags=re.IGNORECASE)
        query = query.replace('%s', '?')
        self._cursor.execute(query, tuple(_adapt_parameter(value) for value in (params or ())))
        return self

    def executemany(self, query, parameters):
        query = query.replace('%s', '?')
        adapted = [tuple(_adapt_parameter(value) for value in row) for row in parameters]
        self._cursor.executemany(query, adapted)
        return self

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class SQLiteConnection:
    def __init__(self, connection):
        self._connection = connection

    def cursor(self, dictionary=False):
        return SQLiteCursor(self._connection.cursor())

    def __getattr__(self, name):
        return getattr(self._connection, name)


def _adapt_parameter(value):
    if isinstance(value, datetime):
        return value.isoformat(sep=' ')
    if isinstance(value, date):
        return value.isoformat()
    return value


def get_db_connection():
    """Abre o banco SQLite local e aplica as opções necessárias à conexão."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    connection.execute('PRAGMA busy_timeout = 10000')
    return SQLiteConnection(connection)


SCHEMA_VERSION = 3
DEMO_EMAIL = 'test@helpiti.com'


def apply_demo_seed(connection):
    """Reaplica o seed idempotente da conta de demonstração."""
    connection.executescript(Path(__file__).with_name('demo_seed.sql').read_text(encoding='utf-8'))


def demo_mode_enabled():
    """Whether startup should create the public demonstration data and account."""
    return os.getenv('HELPTI_DEMO_MODE', 'true').strip().lower() in ('1', 'true', 'yes', 'on')


def initialize_database():
    """Migra bancos antigos e cria tabelas/dados iniciais sem sobrescrever registros."""
    schema_path = Path(__file__).with_name('schema.sql')
    demo_seed_path = Path(__file__).with_name('demo_seed.sql')
    connection = get_db_connection()
    try:
        _migrate_legacy_schema(connection)
        _migrate_multitenant_schema(connection)
        connection.executescript(schema_path.read_text(encoding='utf-8'))
        _migrate_email_auth_schema(connection)
        if demo_mode_enabled():
            connection.executescript(demo_seed_path.read_text(encoding='utf-8'))
        _migrate_plaintext_passwords(connection)
        connection.execute('''
            INSERT INTO historico_chamado (id_chamado, evento, descricao, data_evento)
            SELECT chamado.id_chamado, 'aberto', 'Chamado criado no sistema.', chamado.data_abertura
            FROM chamado
            WHERE NOT EXISTS (
                SELECT 1 FROM historico_chamado
                WHERE historico_chamado.id_chamado = chamado.id_chamado
            )
        ''')
        connection.commit()
        connection.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')
    finally:
        connection.close()


def _columns(connection, table):
    return {row['name'] for row in connection.execute(f'PRAGMA table_info({table})')}


def _migrate_multitenant_schema(connection):
    """Adds per-workspace ownership columns to existing databases without losing data."""
    tables = {
        row['name']
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    if 'usuario' not in tables:
        return

    connection.commit()
    connection.execute('PRAGMA foreign_keys = OFF')
    try:
        workspace = connection.execute(
            "SELECT id_usuario FROM usuario WHERE tipo_usuario = 'WORKSPACE' "
            'ORDER BY id_usuario LIMIT 1'
        ).fetchone()
        workspace_id = workspace['id_usuario'] if workspace else None

        ref = 'INTEGER REFERENCES usuario(id_usuario) ON DELETE CASCADE'
        for table, column in (
            ('usuario', 'id_workspace'),
            ('cliente', 'id_workspace'),
            ('chamado', 'id_usuario'),
            ('configuracao', 'id_usuario'),
        ):
            if table in tables and column not in _columns(connection, table):
                connection.execute(f'ALTER TABLE {table} ADD COLUMN {column} {ref}')

        if 'setor' in tables and 'id_usuario' not in _columns(connection, 'setor'):
            connection.execute('DROP TABLE IF EXISTS setor_new')
            connection.execute(f'''
                CREATE TABLE setor_new (
                    id_setor INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    descricao TEXT,
                    niveis TEXT,
                    id_usuario {ref},
                    UNIQUE (id_usuario, nome)
                )
            ''')
            connection.execute('''
                INSERT INTO setor_new (id_setor, nome, descricao, niveis, id_usuario)
                SELECT id_setor, nome, descricao, niveis, ? FROM setor
            ''', (workspace_id,))
            connection.execute('DROP TABLE setor')
            connection.execute('ALTER TABLE setor_new RENAME TO setor')

        if workspace_id is not None:
            connection.execute(
                "UPDATE usuario SET id_workspace = ? "
                "WHERE tipo_usuario = 'CLIENTE' AND id_workspace IS NULL",
                (workspace_id,)
            )
            if 'cliente' in tables:
                connection.execute(
                    'UPDATE cliente SET id_workspace = ? WHERE id_workspace IS NULL',
                    (workspace_id,)
                )
            if 'chamado' in tables:
                connection.execute(
                    'UPDATE chamado SET id_usuario = ? WHERE id_usuario IS NULL',
                    (workspace_id,)
                )
            if 'setor' in tables:
                connection.execute(
                    'UPDATE setor SET id_usuario = ? WHERE id_usuario IS NULL',
                    (workspace_id,)
                )
            if 'configuracao' in tables:
                connection.execute(
                    'UPDATE configuracao SET id_usuario = ? '
                    'WHERE id_configuracao = (SELECT MIN(id_configuracao) FROM configuracao '
                    'WHERE id_usuario IS NULL) AND NOT EXISTS '
                    '(SELECT 1 FROM configuracao WHERE id_usuario = ?)',
                    (workspace_id, workspace_id)
                )

        if 'configuracao' in tables:
            connection.execute(
                'CREATE UNIQUE INDEX IF NOT EXISTS idx_configuracao_workspace '
                'ON configuracao(id_usuario)'
            )
        connection.execute('DROP INDEX IF EXISTS idx_usuario_workspace_unico')
        connection.commit()
    finally:
        connection.execute('PRAGMA foreign_keys = ON')


def _migrate_email_auth_schema(connection):
    columns = {
        row['name']
        for row in connection.execute('PRAGMA table_info(grupo_solucionadores)')
    }
    if 'email_verificado' not in columns:
        connection.execute(
            'ALTER TABLE grupo_solucionadores '
            'ADD COLUMN email_verificado INTEGER NOT NULL DEFAULT 1'
        )


def _migrate_plaintext_passwords(connection):
    for member in connection.execute(
        "SELECT id_grupo_solucionadores, senha FROM grupo_solucionadores "
        "WHERE senha <> '' AND senha NOT LIKE 'pbkdf2:%' AND senha NOT LIKE 'scrypt:%'"
    ):
        connection.execute(
            'UPDATE grupo_solucionadores SET senha = ? WHERE id_grupo_solucionadores = ?',
            (generate_password_hash(member['senha']), member['id_grupo_solucionadores'])
        )


def _migrate_legacy_schema(connection):
    tables = {
        row['name']
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }

    if 'cliente_contato' in tables and 'cliente' not in tables:
        connection.execute('ALTER TABLE cliente_contato RENAME TO cliente')
        columns = {
            row['name'] for row in connection.execute('PRAGMA table_info(cliente)')
        }
        if 'id_cliente_contato' in columns:
            connection.execute(
                'ALTER TABLE cliente RENAME COLUMN id_cliente_contato TO id_cliente'
            )
        connection.execute('DROP INDEX IF EXISTS idx_cliente_contato_usuario')

    if 'documentacao' in tables:
        total = connection.execute('SELECT COUNT(*) FROM documentacao').fetchone()[0]
        if total:
            suffix = 1
            archive_name = 'documentacao_legado'
            while archive_name in tables:
                suffix += 1
                archive_name = f'documentacao_legado_{suffix}'
            connection.execute(
                f'ALTER TABLE documentacao RENAME TO {archive_name}'
            )
        else:
            connection.execute('DROP TABLE documentacao')

    if 'chamado' in tables:
        columns = {
            row['name'] for row in connection.execute('PRAGMA table_info(chamado)')
        }
        if 'documentacao' not in columns:
            connection.execute('ALTER TABLE chamado ADD COLUMN documentacao TEXT')

    if 'usuario' in tables:
        user_columns = {
            row['name'] for row in connection.execute('PRAGMA table_info(usuario)')
        }
        if 'tipo_usuario' not in user_columns:
            connection.execute(
                "ALTER TABLE usuario ADD COLUMN tipo_usuario TEXT NOT NULL DEFAULT 'CLIENTE'"
            )

    if 'grupo_solucionadores' not in tables:
        return

    member_columns = {
        row['name'] for row in connection.execute('PRAGMA table_info(grupo_solucionadores)')
    }
    if 'permissoes' not in member_columns:
        connection.execute(
            "ALTER TABLE grupo_solucionadores ADD COLUMN permissoes TEXT NOT NULL DEFAULT '[]'"
        )
    if 'id_usuario' not in member_columns:
        connection.execute(
            'ALTER TABLE grupo_solucionadores ADD COLUMN id_usuario INTEGER REFERENCES usuario(id_usuario) ON DELETE CASCADE'
        )

    workspace = connection.execute(
        "SELECT id_usuario FROM usuario WHERE tipo_usuario = 'WORKSPACE' ORDER BY id_usuario LIMIT 1"
    ).fetchone()
    if workspace:
        workspace_id = workspace['id_usuario']
    else:
        administrator = connection.execute(
            "SELECT descricao, nome, email FROM grupo_solucionadores WHERE LOWER(cargo) = 'administrador' ORDER BY id_grupo_solucionadores LIMIT 1"
        ).fetchone()
        workspace_name = (administrator['descricao'] or administrator['nome']) if administrator else 'HelpTI'
        workspace_email = administrator['email'] if administrator else None
        connection.execute(
            "INSERT INTO usuario (nome, email, status, tipo_usuario) VALUES (?, ?, 'ATIVO', 'WORKSPACE')",
            (workspace_name, workspace_email)
        )
        workspace_id = connection.execute('SELECT last_insert_rowid()').fetchone()[0]

    connection.execute(
        'UPDATE grupo_solucionadores SET id_usuario = ? WHERE id_usuario IS NULL',
        (workspace_id,)
    )

    defaults_by_role = {
        'rh': ['dashboard', 'clientes', 'equipe'],
        'suporte': ['dashboard', 'chamados', 'clientes', 'educacao'],
        'noc': ['dashboard', 'chamados'],
        'técnico': ['dashboard', 'chamados', 'educacao'],
        'tecnico': ['dashboard', 'chamados', 'educacao'],
    }
    for member in connection.execute(
        "SELECT id_grupo_solucionadores, cargo FROM grupo_solucionadores WHERE permissoes = '[]'"
    ):
        role = (member['cargo'] or '').strip().lower()
        permissions = defaults_by_role.get(role, ['dashboard', 'chamados'])
        connection.execute(
            'UPDATE grupo_solucionadores SET permissoes = ? WHERE id_grupo_solucionadores = ?',
            (json.dumps(permissions), member['id_grupo_solucionadores'])
        )
