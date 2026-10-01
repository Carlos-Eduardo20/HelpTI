import os
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

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


def initialize_database():
    """Migra bancos antigos e cria tabelas/dados iniciais sem sobrescrever registros."""
    schema_path = Path(__file__).with_name('schema.sql')
    connection = get_db_connection()
    try:
        _migrate_legacy_schema(connection)
        connection.executescript(schema_path.read_text(encoding='utf-8'))
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
    finally:
        connection.close()


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

