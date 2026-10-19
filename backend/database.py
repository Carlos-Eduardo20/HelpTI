import os
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import mysql.connector
from mysql.connector.constants import ClientFlag

PROJECT_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = PROJECT_DIR / 'instance'
SCHEMA_VERSION = 5
DEMO_EMAIL = 'test@helpiti.com'


def database_settings():
    """Lê a configuração do MySQL a cada chamada para respeitar variáveis alteradas em runtime."""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'helpti_app'),
    }


class Row(tuple):
    """Linha que aceita acesso por posição e por nome da coluna."""

    def __new__(cls, columns, values):
        row = super().__new__(cls, values)
        row._columns = columns
        return row

    def __getitem__(self, key):
        if isinstance(key, str):
            try:
                return super().__getitem__(self._columns.index(key))
            except ValueError:
                raise KeyError(key) from None
        return super().__getitem__(key)

    def keys(self):
        return list(self._columns)


def _convert(value):
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() and value.as_tuple().exponent >= 0 else float(value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode('utf-8', errors='replace')
    return value


class Cursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=None):
        self._cursor.execute(query, tuple(params) if params else None)
        return self

    def executemany(self, query, parameters):
        self._cursor.executemany(query, [tuple(row) for row in parameters])
        return self

    def _row(self, values):
        columns = [description[0] for description in self._cursor.description]
        return Row(columns, [_convert(value) for value in values])

    def fetchone(self):
        values = self._cursor.fetchone()
        return None if values is None else self._row(values)

    def fetchall(self):
        return [self._row(values) for values in self._cursor.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class Connection:
    def __init__(self, connection):
        self._connection = connection

    def cursor(self, dictionary=False):
        return Cursor(self._connection.cursor())

    def execute(self, query, params=None):
        return self.cursor().execute(query, params)

    def executescript(self, script):
        """Executa vários comandos terminados em ';' no fim da linha."""
        script = re.sub(r'^\s*--.*$', '', script, flags=re.MULTILINE)
        for statement in re.split(r';\s*(?:\n|$)', script):
            if statement.strip():
                cursor = self._connection.cursor()
                cursor.execute(statement)
                cursor.close()

    def __getattr__(self, name):
        return getattr(self._connection, name)


def _connect(with_database=True):
    settings = database_settings()
    if not with_database:
        settings.pop('database')
    return mysql.connector.connect(
        **settings,
        charset='utf8mb4',
        autocommit=False,
        connection_timeout=10,
        client_flags=[ClientFlag.FOUND_ROWS],
    )


def get_db_connection():
    """Abre uma conexão MySQL; a transação é iniciada implicitamente (autocommit desligado)."""
    return Connection(_connect())


def apply_demo_seed(connection):
    """Reaplica o seed idempotente da conta de demonstração."""
    connection.executescript(Path(__file__).with_name('demo_seed.sql').read_text(encoding='utf-8'))
    connection.commit()


def demo_mode_enabled():
    """Whether startup should create the public demonstration data and account."""
    return os.getenv('HELPTI_DEMO_MODE', 'true').strip().lower() in ('1', 'true', 'yes', 'on')


def create_database_if_missing():
    name = database_settings()['database']
    if not re.fullmatch(r'[A-Za-z0-9_$]+', name):
        raise ValueError('DB_NAME deve conter apenas letras, números, "_" ou "$".')
    server = _connect(with_database=False)
    try:
        cursor = server.cursor()
        try:
            cursor.execute(
                f'CREATE DATABASE IF NOT EXISTS `{name}` '
                'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
            )
        except mysql.connector.Error as error:
            # Usuários sem privilégio global usam um banco já criado pelo administrador.
            if error.errno not in (1044, 1227):
                raise
        cursor.close()
    finally:
        server.close()


def _ensure_compatible_schema(connection):
    """Interrompe a inicialização se o banco contém tabelas de uma versão antiga do HelpTI."""
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = DATABASE() AND table_name = 'usuario'"
    ).fetchone()
    if not row[0]:
        return
    column = connection.execute(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = 'usuario' "
        "AND column_name = 'id_workspace'"
    ).fetchone()
    if not column[0]:
        raise RuntimeError(
            'O banco MySQL configurado em DB_NAME contém tabelas de uma versão antiga '
            'do HelpTI. Use outro valor em DB_NAME (por exemplo, helpti_app) ou migre '
            'os dados antes de iniciar.'
        )


def initialize_database():
    """Cria o banco, as tabelas e os dados iniciais sem sobrescrever registros existentes."""
    create_database_if_missing()
    connection = get_db_connection()
    try:
        _ensure_compatible_schema(connection)
        connection.executescript(
            Path(__file__).with_name('schema.sql').read_text(encoding='utf-8')
        )
        if demo_mode_enabled():
            connection.executescript(
                Path(__file__).with_name('demo_seed.sql').read_text(encoding='utf-8')
            )
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
