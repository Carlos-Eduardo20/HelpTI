import os
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = PROJECT_DIR / 'instance'
SCHEMA_VERSION = 6
DEMO_EMAIL = 'test@helpiti.com'
Error = sqlite3.Error


def database_settings():
    """Retorna o caminho do banco SQLite configurado."""
    database_type = os.getenv('DB_TYPE', 'sqlite').strip().lower()
    if database_type != 'sqlite':
        raise RuntimeError(
            'O HelpTI agora usa somente SQLite. Remova a configuração DB_TYPE '
            'legada e configure DB_SQLITE_PATH. Bancos MySQL existentes precisam '
            'ser exportados antes da troca; eles não são convertidos automaticamente.'
        )

    database_path = Path(os.getenv(
        'DB_SQLITE_PATH', str(INSTANCE_DIR / 'helpti.sqlite3')
    )).expanduser()
    if not database_path.is_absolute():
        database_path = PROJECT_DIR / database_path
    return {
        'type': 'sqlite',
        'database': str(database_path.resolve()),
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


class Cursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=None):
        query = query.replace('%s', '?')
        if params is None:
            self._cursor.execute(query)
        else:
            self._cursor.execute(query, tuple(_sqlite_value(value) for value in params))
        return self

    def executemany(self, query, parameters):
        query = query.replace('%s', '?')
        rows = [tuple(_sqlite_value(value) for value in row) for row in parameters]
        self._cursor.executemany(query, rows)
        return self

    def _row(self, values):
        columns = [description[0] for description in self._cursor.description]
        return Row(columns, values)

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
        self._connection.executescript(script)

    def __getattr__(self, name):
        return getattr(self._connection, name)


def get_db_connection():
    """Abre uma conexão SQLite; transações são explícitas."""
    path = Path(database_settings()['database'])
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.execute('PRAGMA foreign_keys = ON')
    return Connection(connection)


def apply_demo_seed(connection):
    """Reaplica o seed idempotente da conta de demonstração."""
    connection.executescript(Path(__file__).with_name('demo_seed.sql').read_text(encoding='utf-8'))
    connection.commit()


def demo_mode_enabled():
    """Whether startup should create the public demonstration data and account."""
    return os.getenv('HELPTI_DEMO_MODE', 'true').strip().lower() in ('1', 'true', 'yes', 'on')


def create_database_if_missing():
    Path(database_settings()['database']).parent.mkdir(parents=True, exist_ok=True)


def _ensure_compatible_schema(connection):
    """Interrompe a inicialização se o arquivo contém tabelas de uma versão antiga."""
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


def _migrate_profile_and_settings(connection):
    for table, column, sql_type in (
        ('usuario', 'workspace_name', 'VARCHAR(255)'),
        ('usuario', 'support_email', 'VARCHAR(255)'),
        ('grupo_solucionadores', 'foto_perfil', 'TEXT'),
    ):
        existing = {
            row[1] for row in connection.execute(f'PRAGMA table_info({table})').fetchall()
        }
        if column not in existing:
            connection.execute(f'ALTER TABLE {table} ADD COLUMN {column} {sql_type}')

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
