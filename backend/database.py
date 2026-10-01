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
    """Cria as tabelas e os dados iniciais sem sobrescrever registros."""
    schema_path = Path(__file__).with_name('schema.sql')
    connection = get_db_connection()
    try:
        connection.executescript(schema_path.read_text(encoding='utf-8'))
        connection.commit()
    finally:
        connection.close()

