import os
import re
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

try:
    import mysql.connector
    from mysql.connector.constants import ClientFlag
except ImportError:
    mysql = None
    ClientFlag = None

PROJECT_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = PROJECT_DIR / 'instance'
SCHEMA_VERSION = 6
DEMO_EMAIL = 'test@helpiti.com'
Error = (mysql.connector.Error, sqlite3.Error) if mysql else sqlite3.Error


def database_settings():
    """Lê a configuração do banco a cada chamada para respeitar mudanças em runtime."""
    # SQLite lets production environments such as Render boot without a local MySQL server.
    database_type = os.getenv('DB_TYPE', 'sqlite').strip().lower()
    if database_type == 'sqlite':
        database_path = Path(os.getenv(
            'DB_SQLITE_PATH', str(INSTANCE_DIR / 'helpti.sqlite3')
        )).expanduser()
        if not database_path.is_absolute():
            database_path = PROJECT_DIR / database_path
        return {
            'type': database_type,
            'database': str(database_path.resolve()),
        }
    if database_type != 'mysql':
        raise ValueError('DB_TYPE deve ser "sqlite" ou "mysql".')
    return {
        'type': database_type,
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
    def __init__(self, cursor, database_type):
        self._cursor = cursor
        self._database_type = database_type

    def execute(self, query, params=None):
        query = _adapt_query(query, self._database_type)
        if params:
            values = tuple(_sqlite_value(value) for value in params) if self._database_type == 'sqlite' else tuple(params)
            self._cursor.execute(query, values)
        else:
            self._cursor.execute(query)
        return self

    def executemany(self, query, parameters):
        query = _adapt_query(query, self._database_type)
        rows = [
            tuple(_sqlite_value(value) for value in row)
            if self._database_type == 'sqlite' else tuple(row)
            for row in parameters
        ]
        self._cursor.executemany(query, rows)
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
    def __init__(self, connection, database_type):
        self._connection = connection
        self._database_type = database_type

    def cursor(self, dictionary=False):
        return Cursor(self._connection.cursor(), self._database_type)

    def execute(self, query, params=None):
        return self.cursor().execute(query, params)

    def executescript(self, script):
        """Executa vários comandos terminados em ';' no fim da linha."""
        if self._database_type == 'sqlite':
            self._connection.executescript(_sqlite_schema(script))
            return
        script = re.sub(r'^\s*--.*$', '', script, flags=re.MULTILINE)
        for statement in re.split(r';\s*(?:\n|$)', script):
            if statement.strip():
                cursor = self._connection.cursor()
                cursor.execute(statement)
                cursor.close()

    def __getattr__(self, name):
        return getattr(self._connection, name)


def _adapt_query(query, database_type):
    if database_type != 'sqlite':
        return query
    query = query.replace('%s', '?')
    query = re.sub(r'\s+FOR UPDATE\b', '', query, flags=re.IGNORECASE)
    query = re.sub(
        r'SHOW COLUMNS FROM ([A-Za-z_][A-Za-z0-9_]*)',
        r"SELECT name FROM pragma_table_info('\1')",
        query,
        flags=re.IGNORECASE,
    )
    query = re.sub(
        r'YEAR\((\w+(?:\.\w+)?)\)\s*=\s*YEAR\(CURDATE\(\)\)',
        r"strftime('%Y', \1) = strftime('%Y', 'now', 'localtime')",
        query,
        flags=re.IGNORECASE,
    )
    query = re.sub(
        r'MONTH\((\w+(?:\.\w+)?)\)\s*=\s*MONTH\(CURDATE\(\)\)',
        r"strftime('%m', \1) = strftime('%m', 'now', 'localtime')",
        query,
        flags=re.IGNORECASE,
    )
    query = re.sub(r'\bCURDATE\(\)', "DATE('now', 'localtime')", query, flags=re.IGNORECASE)
    return query


def _sqlite_value(value):
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    return value


def _sqlite_schema(script):
    script = re.sub(r'^\s*--.*$', '', script, flags=re.MULTILINE)
    script = re.sub(
        r'\bINT\s+AUTO_INCREMENT\s+PRIMARY KEY\b',
        'INTEGER PRIMARY KEY AUTOINCREMENT',
        script,
        flags=re.IGNORECASE,
    )
    script = re.sub(r'^\s*INDEX\s+[A-Za-z_][A-Za-z0-9_]*\s*\([^\n]+\),?\s*$', '', script, flags=re.MULTILINE)
    script = re.sub(
        r'UNIQUE KEY\s+[A-Za-z_][A-Za-z0-9_]*\s*(\([^\n]+\))',
        r'UNIQUE \1', script, flags=re.IGNORECASE
    )
    script = re.sub(r'\bMEDIUMTEXT\b', 'TEXT', script, flags=re.IGNORECASE)
    script = re.sub(r'\)\s*ENGINE=InnoDB DEFAULT CHARSET=utf8mb4', ')', script, flags=re.IGNORECASE)
    script = re.sub(r',\s*\)', '\n)', script)
    script = re.sub(r'\bINSERT IGNORE\b', 'INSERT OR IGNORE', script, flags=re.IGNORECASE)
    script = re.sub(r'\bFROM DUAL\b', '', script, flags=re.IGNORECASE)
    return script


def _connect(with_database=True):
    settings = database_settings()
    database_type = settings.pop('type')
    if database_type == 'sqlite':
        path = Path(settings['database'])
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=10)
        connection.execute('PRAGMA foreign_keys = ON')
        connection.row_factory = None
        return Connection(connection, database_type)
    if mysql is None:
        raise RuntimeError(
            'O driver MySQL não está instalado. Instale backend/requirements.txt '
            'ou use DB_TYPE=sqlite.'
        )
    if not with_database:
        settings.pop('database')
    return Connection(mysql.connector.connect(
        **settings,
        charset='utf8mb4',
        autocommit=False,
        connection_timeout=10,
        client_flags=[ClientFlag.FOUND_ROWS],
    ), database_type)


def get_db_connection():
    """Abre uma conexão com o banco configurado; transações são explícitas."""
    return _connect()


def apply_demo_seed(connection):
    """Reaplica o seed idempotente da conta de demonstração."""
    connection.executescript(Path(__file__).with_name('demo_seed.sql').read_text(encoding='utf-8'))
    connection.commit()


def demo_mode_enabled():
    """Whether startup should create the public demonstration data and account."""
    return os.getenv('HELPTI_DEMO_MODE', 'true').strip().lower() in ('1', 'true', 'yes', 'on')


def create_database_if_missing():
    if database_settings()['type'] == 'sqlite':
        path = Path(database_settings()['database'])
        path.parent.mkdir(parents=True, exist_ok=True)
        return
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
    if database_settings()['type'] == 'sqlite':
        row = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'usuario'"
        ).fetchone()
        if not row[0]:
            return
        columns = {row[1] for row in connection.execute('PRAGMA table_info(usuario)')}
        if 'id_workspace' not in columns:
            raise RuntimeError(
                'O arquivo SQLite configurado contém tabelas de uma versão antiga '
                'do HelpTI. Defina outro DB_SQLITE_PATH ou migre os dados.'
            )
        return
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


def _migrate_profile_and_settings(connection):
    sqlite_mode = database_settings()['type'] == 'sqlite'
    for table, column, sql_type in (
        ('usuario', 'workspace_name', 'VARCHAR(255)'),
        ('usuario', 'support_email', 'VARCHAR(255)'),
        ('grupo_solucionadores', 'foto_perfil', 'TEXT' if sqlite_mode else 'MEDIUMTEXT'),
    ):
        existing = {row[0] for row in connection.execute(f'SHOW COLUMNS FROM {table}').fetchall()}
        if column not in existing:
            connection.execute(f'ALTER TABLE {table} ADD COLUMN {column} {sql_type}')

    if sqlite_mode:
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()}
        if 'configuracao' in tables:
            for row in connection.execute(
                'SELECT id_usuario, workspace_name, support_email FROM configuracao'
            ).fetchall():
                connection.execute(
                    'UPDATE usuario SET workspace_name = %s, support_email = %s '
                    'WHERE id_usuario = %s',
                    (row[1], row[2], row[0]),
                )
            connection.execute('DROP TABLE configuracao')


def initialize_database():
    """Cria o banco, as tabelas e os dados iniciais sem sobrescrever registros existentes."""
    create_database_if_missing()
    connection = get_db_connection()
    try:
        _ensure_compatible_schema(connection)
        connection.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
        _migrate_profile_and_settings(connection)
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
