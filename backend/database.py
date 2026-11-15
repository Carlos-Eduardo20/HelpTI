import os
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = PROJECT_DIR / 'instance'
SCHEMA_VERSION = 11
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


def _seed_ticket_id_sequence(connection):
    max_id = connection.execute(
        'SELECT COALESCE(MAX(id_chamado), 0) FROM chamado'
    ).fetchone()[0]
    sequence = connection.execute(
        "SELECT seq FROM sqlite_sequence WHERE name = 'chamado'"
    ).fetchone()
    next_floor = max(99999, int(max_id or 0), int(sequence[0]) if sequence else 0)
    if sequence:
        connection.execute(
            "UPDATE sqlite_sequence SET seq = %s WHERE name = 'chamado'",
            (next_floor,),
        )
    else:
        connection.execute(
            "INSERT INTO sqlite_sequence (name, seq) VALUES ('chamado', %s)",
            (next_floor,),
        )


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


def _prepare_customer_migration(connection):
    tables = {
        row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    if 'cliente' not in tables or 'cliente_contatos_legados' in tables:
        return

    columns = {
        row[1] for row in connection.execute('PRAGMA table_info(cliente)').fetchall()
    }
    if not {'id_usuario', 'nome', 'email', 'telefone', 'id_workspace'}.issubset(columns):
        return

    connection.execute('PRAGMA foreign_keys = OFF')
    try:
        connection.execute('BEGIN IMMEDIATE')
        connection.execute('DROP INDEX IF EXISTS idx_cliente_usuario')
        connection.execute('DROP INDEX IF EXISTS idx_cliente_workspace')
        connection.execute('ALTER TABLE cliente RENAME TO cliente_contatos_legados')
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.execute('PRAGMA foreign_keys = ON')


def _migrate_customer_entities(connection):
    tables = {
        row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    called_columns = {
        row[1] for row in connection.execute('PRAGMA table_info(chamado)').fetchall()
    }
    has_legacy_contacts = 'cliente_contatos_legados' in tables
    has_legacy_companies = connection.execute(
        "SELECT 1 FROM usuario WHERE UPPER(tipo_usuario) = 'CLIENTE' LIMIT 1"
    ).fetchone() is not None

    if 'id_cliente' not in called_columns:
        connection.execute(
            'ALTER TABLE chamado ADD COLUMN id_cliente INTEGER '
            'REFERENCES cliente(id_cliente) ON DELETE SET NULL'
        )
    connection.execute(
        'CREATE INDEX IF NOT EXISTS idx_chamado_cliente ON chamado (id_cliente)'
    )

    if has_legacy_contacts or has_legacy_companies:
        connection.execute('BEGIN IMMEDIATE')
        try:
            companies = connection.execute(
                "SELECT id_usuario, nome, contato, email, telefone, cnpj, "
                "telefone_empresa, endereco, status, plano, acoes, id_workspace "
                "FROM usuario WHERE UPPER(tipo_usuario) = 'CLIENTE' "
                "ORDER BY id_usuario"
            ).fetchall()
            company_ids = set()

            for company in companies:
                (
                    old_id, name, primary_name, primary_email, primary_phone,
                    cnpj, company_phone, address, status, plan, actions, owner_id,
                ) = company
                owner = connection.execute(
                    'SELECT 1 FROM usuario WHERE id_usuario = %s', (owner_id,)
                ).fetchone()
                if not owner:
                    raise RuntimeError(
                        f'A empresa cliente legada {old_id} não possui uma conta '
                        'proprietária válida em usuario.id_workspace.'
                    )

                existing = connection.execute(
                    'SELECT id_usuario, nome FROM cliente WHERE id_cliente = %s',
                    (old_id,),
                ).fetchone()
                if existing and (
                    existing[0] != owner_id or (existing[1] or '') != (name or '')
                ):
                    raise RuntimeError(
                        f'Conflito ao migrar a empresa cliente legada {old_id}.'
                    )
                if not existing:
                    connection.execute('''
                        INSERT INTO cliente (
                            id_cliente, nome, cnpj, telefone_empresa, endereco,
                            status, plano, acoes, id_usuario
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        old_id, name or 'Cliente', cnpj, company_phone, address,
                        status or 'ATIVO', plan, actions, owner_id,
                    ))
                company_ids.add(old_id)

                legacy_contacts = []
                if has_legacy_contacts:
                    legacy_contacts = connection.execute(
                        'SELECT nome, email, telefone FROM cliente_contatos_legados '
                        'WHERE id_usuario = %s ORDER BY id_cliente',
                        (old_id,),
                    ).fetchall()

                primary = (
                    (primary_name or '').strip(),
                    (primary_email or '').strip(),
                    (primary_phone or '').strip(),
                )
                if all(primary):
                    connection.execute(
                        'INSERT INTO contato_cliente (id_cliente, nome, email, telefone) '
                        'VALUES (%s, %s, %s, %s)',
                        (old_id, *primary),
                    )
                    legacy_contacts = legacy_contacts[1:]
                elif legacy_contacts:
                    first = legacy_contacts.pop(0)
                    connection.execute(
                        'INSERT INTO contato_cliente (id_cliente, nome, email, telefone) '
                        'VALUES (%s, %s, %s, %s)',
                        (old_id, first[0], first[1], first[2]),
                    )

                for contact in legacy_contacts:
                    connection.execute(
                        'INSERT INTO contato_cliente (id_cliente, nome, email, telefone) '
                        'VALUES (%s, %s, %s, %s)',
                        (old_id, contact[0], contact[1], contact[2]),
                    )

            if has_legacy_contacts:
                orphan = connection.execute('''
                    SELECT id_usuario FROM cliente_contatos_legados
                    WHERE id_usuario NOT IN (
                        SELECT id_usuario FROM usuario
                        WHERE UPPER(tipo_usuario) = 'CLIENTE'
                    )
                    LIMIT 1
                ''').fetchone()
                if orphan:
                    raise RuntimeError(
                        f'O contato legado referencia a empresa inexistente {orphan[0]}.'
                    )

            tickets = connection.execute('''
                SELECT id_chamado, id_usuario, cliente, email_cliente,
                       telefone_cliente, contato_cliente, telefone_contato
                FROM chamado WHERE id_cliente IS NULL
            ''').fetchall()
            for ticket in tickets:
                (
                    ticket_id, owner_id, company_name, email, company_phone,
                    contact_name, contact_phone,
                ) = ticket
                candidates = connection.execute('''
                    SELECT id_cliente FROM cliente
                    WHERE id_usuario = %s AND LOWER(TRIM(nome)) = LOWER(TRIM(%s))
                    ORDER BY id_cliente
                ''', (owner_id, company_name)).fetchall()
                if len(candidates) == 1:
                    selected_id = candidates[0][0]
                elif len(candidates) > 1:
                    matches = []
                    for candidate in candidates:
                        contact_rows = connection.execute(
                            'SELECT nome, email, telefone FROM contato_cliente '
                            'WHERE id_cliente = %s',
                            (candidate[0],),
                        ).fetchall()
                        score = 0
                        for contact in contact_rows:
                            if email and (contact[1] or '').strip().lower() == email.strip().lower():
                                score += 1
                            if contact_name and (contact[0] or '').strip().lower() == contact_name.strip().lower():
                                score += 1
                            if contact_phone and (contact[2] or '').strip() == contact_phone.strip():
                                score += 1
                            if company_phone and (contact[2] or '').strip() == company_phone.strip():
                                score += 1
                        matches.append((score, candidate[0]))
                    highest = max((score for score, _ in matches), default=0)
                    best = [client_id for score, client_id in matches if score == highest and score > 0]
                    selected_id = best[0] if len(best) == 1 else None
                else:
                    selected_id = None

                if selected_id is not None:
                    connection.execute(
                        'UPDATE chamado SET id_cliente = %s WHERE id_chamado = %s',
                        (selected_id, ticket_id),
                    )

            if has_legacy_contacts:
                connection.execute('DROP TABLE cliente_contatos_legados')
            if company_ids:
                placeholders = ', '.join(['%s'] * len(company_ids))
                connection.execute(
                    f'DELETE FROM usuario WHERE id_usuario IN ({placeholders})',
                    tuple(sorted(company_ids)),
                )

            connection.commit()
        except Exception:
            connection.rollback()
            raise

    user_columns = {
        row[1] for row in connection.execute('PRAGMA table_info(usuario)').fetchall()
    }
    if 'email' in user_columns:
        duplicates = connection.execute('''
            SELECT LOWER(TRIM(email)), COUNT(*) FROM usuario
            WHERE email IS NOT NULL AND TRIM(email) <> ''
            GROUP BY LOWER(TRIM(email)) HAVING COUNT(*) > 1
            LIMIT 1
        ''').fetchone()
        if duplicates:
            raise RuntimeError(
                'Há contas com e-mails duplicados no SQLite. Corrija os e-mails '
                'duplicados em usuario antes de inicializar o HelpTI.'
            )
        connection.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_usuario_email_unique '
            'ON usuario (LOWER(TRIM(email))) '
            "WHERE email IS NOT NULL AND TRIM(email) <> ''"
        )
    connection.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')


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


def _migrate_sector_and_auth_tables(connection):
    """Move sector names to text fields and remove tables no longer used."""
    tables = {
        row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    group_columns = {
        row[1] for row in connection.execute(
            'PRAGMA table_info(grupo_solucionadores)'
        ).fetchall()
    } if 'grupo_solucionadores' in tables else set()
    ticket_columns = {
        row[1] for row in connection.execute(
            'PRAGMA table_info(chamado)'
        ).fetchall()
    } if 'chamado' in tables else set()
    escalation_columns = {
        row[1] for row in connection.execute(
            'PRAGMA table_info(escalonamento)'
        ).fetchall()
    } if 'escalonamento' in tables else set()

    remove_auth_tables = {
        'codigo_recuperacao_senha',
        'identidade_microsoft',
        'login_rate_limit',
        'verificacao_cadastro_email',
    } & tables
    remove_equipment_table = 'equipamento_cliente' in tables
    rebuild_group = bool(group_columns & {'id_setor', 'email_verificado'})
    rebuild_ticket = 'id_setor' in ticket_columns
    rebuild_escalation = 'id_setor_destino' in escalation_columns
    remove_sector_table = 'setor' in tables
    if not (
        remove_auth_tables or remove_equipment_table or rebuild_group or rebuild_ticket
        or rebuild_escalation or remove_sector_table
    ):
        connection.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')
        return

    connection.execute('PRAGMA foreign_keys = OFF')
    try:
        connection.execute('BEGIN IMMEDIATE')
        for table in remove_auth_tables:
            connection.execute(f'DROP TABLE IF EXISTS {table}')
        if remove_equipment_table:
            connection.execute('DROP TABLE equipamento_cliente')

        if 'id_setor' in group_columns and 'setor' not in group_columns:
            connection.execute('ALTER TABLE grupo_solucionadores ADD COLUMN setor TEXT')
        if 'id_setor' in ticket_columns and 'setor' not in ticket_columns:
            connection.execute('ALTER TABLE chamado ADD COLUMN setor TEXT')
        if 'id_setor_destino' in escalation_columns and 'setor_destino' not in escalation_columns:
            connection.execute('ALTER TABLE escalonamento ADD COLUMN setor_destino TEXT')

        if remove_sector_table and 'id_setor' in group_columns:
            connection.execute('''
                UPDATE grupo_solucionadores
                SET setor = (
                    SELECT setor.nome FROM setor
                    WHERE setor.id_setor = grupo_solucionadores.id_setor
                )
                WHERE (setor IS NULL OR TRIM(setor) = '') AND id_setor IS NOT NULL
            ''')
        if remove_sector_table and 'id_setor' in ticket_columns:
            connection.execute('''
                UPDATE chamado
                SET setor = (
                    SELECT setor.nome FROM setor
                    WHERE setor.id_setor = chamado.id_setor
                )
                WHERE (setor IS NULL OR TRIM(setor) = '') AND id_setor IS NOT NULL
            ''')
        if remove_sector_table and 'id_setor_destino' in escalation_columns:
            connection.execute('''
                UPDATE escalonamento
                SET setor_destino = (
                    SELECT setor.nome FROM setor
                    WHERE setor.id_setor = escalonamento.id_setor_destino
                )
                WHERE (setor_destino IS NULL OR TRIM(setor_destino) = '')
                  AND id_setor_destino IS NOT NULL
            ''')

        if rebuild_group:
            connection.execute('''
                CREATE TABLE grupo_solucionadores_novo (
                    id_grupo_solucionadores INTEGER PRIMARY KEY AUTOINCREMENT,
                    descricao TEXT,
                    nivel INTEGER,
                    data_inicio TEXT,
                    data_fim TEXT,
                    nome TEXT,
                    email TEXT,
                    cargo TEXT,
                    valor_hora NUMERIC,
                    telefone TEXT,
                    setor TEXT,
                    status TEXT NOT NULL DEFAULT 'ATIVO',
                    senha TEXT NOT NULL DEFAULT '',
                    permissoes TEXT NOT NULL DEFAULT '[]',
                    foto_perfil TEXT,
                    id_usuario INTEGER NOT NULL,
                    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE
                )
            ''')
            connection.execute('''
                INSERT INTO grupo_solucionadores_novo (
                    id_grupo_solucionadores, descricao, nivel, data_inicio, data_fim,
                    nome, email, cargo, valor_hora, telefone, setor, status, senha,
                    permissoes, foto_perfil, id_usuario
                )
                SELECT id_grupo_solucionadores, descricao, nivel, data_inicio, data_fim,
                       nome, email, cargo, valor_hora, telefone, setor, status, senha,
                       permissoes, foto_perfil, id_usuario
                FROM grupo_solucionadores
            ''')
            connection.execute('DROP TABLE grupo_solucionadores')
            connection.execute(
                'ALTER TABLE grupo_solucionadores_novo RENAME TO grupo_solucionadores'
            )
            connection.execute(
                'CREATE INDEX IF NOT EXISTS idx_grupo_solucionadores_setor '
                'ON grupo_solucionadores (setor)'
            )
            connection.execute(
                'CREATE INDEX IF NOT EXISTS idx_grupo_solucionadores_usuario '
                'ON grupo_solucionadores (id_usuario)'
            )
            connection.execute(
                'CREATE INDEX IF NOT EXISTS idx_grupo_solucionadores_email '
                'ON grupo_solucionadores (email)'
            )

        if rebuild_ticket:
            connection.execute('''
                CREATE TABLE chamado_novo (
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
                    id_usuario INTEGER,
                    FOREIGN KEY (id_tipo_chamado) REFERENCES tipo_chamado(id_tipo_chamado),
                    FOREIGN KEY (id_grupo_solucionadores)
                        REFERENCES grupo_solucionadores(id_grupo_solucionadores) ON DELETE SET NULL,
                    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE
                )
            ''')
            connection.execute('''
                INSERT INTO chamado_novo (
                    id_chamado, id_tipo_chamado, setor, id_grupo_solucionadores,
                    status, cliente, assunto, descricao, email_cliente, telefone_cliente,
                    contato_cliente, telefone_contato, descricao_final, documentacao,
                    tempo_decorrido_segundos, tempo_inicio, data_abertura, data_fechamento,
                    data_agendada, hora_agendada, classificacao, id_usuario
                )
                SELECT id_chamado, id_tipo_chamado, setor, id_grupo_solucionadores,
                       status, cliente, assunto, descricao, email_cliente, telefone_cliente,
                       contato_cliente, telefone_contato, descricao_final, documentacao,
                       tempo_decorrido_segundos, tempo_inicio, data_abertura, data_fechamento,
                       data_agendada, hora_agendada, classificacao, id_usuario
                FROM chamado
            ''')
            connection.execute('DROP TABLE chamado')
            connection.execute('ALTER TABLE chamado_novo RENAME TO chamado')
            connection.execute(
                'CREATE INDEX IF NOT EXISTS idx_chamado_status_data '
                'ON chamado (status, data_abertura)'
            )
            connection.execute(
                'CREATE INDEX IF NOT EXISTS idx_chamado_setor ON chamado (setor)'
            )
            connection.execute(
                'CREATE INDEX IF NOT EXISTS idx_chamado_workspace '
                'ON chamado (id_usuario, id_chamado)'
            )

        if rebuild_escalation:
            connection.execute('''
                CREATE TABLE escalonamento_novo (
                    id_escalonamento INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_chamado INTEGER NOT NULL,
                    motivo TEXT,
                    nivel INTEGER,
                    setor_destino TEXT,
                    id_grupo_destino INTEGER,
                    data_escalonamento TEXT,
                    FOREIGN KEY (id_chamado) REFERENCES chamado(id_chamado) ON DELETE CASCADE,
                    FOREIGN KEY (id_grupo_destino)
                        REFERENCES grupo_solucionadores(id_grupo_solucionadores) ON DELETE SET NULL
                )
            ''')
            connection.execute('''
                INSERT INTO escalonamento_novo (
                    id_escalonamento, id_chamado, motivo, nivel, setor_destino,
                    id_grupo_destino, data_escalonamento
                )
                SELECT id_escalonamento, id_chamado, motivo, nivel, setor_destino,
                       id_grupo_destino, data_escalonamento
                FROM escalonamento
            ''')
            connection.execute('DROP TABLE escalonamento')
            connection.execute('ALTER TABLE escalonamento_novo RENAME TO escalonamento')
            connection.execute(
                'CREATE INDEX IF NOT EXISTS idx_escalonamento_chamado '
                'ON escalonamento (id_chamado)'
            )

        if remove_sector_table:
            connection.execute('DROP TABLE setor')

        connection.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.execute('PRAGMA foreign_keys = ON')


def initialize_database():
    """Cria o banco, as tabelas e os dados iniciais sem sobrescrever registros existentes."""
    create_database_if_missing()
    connection = get_db_connection()
    try:
        _ensure_compatible_schema(connection)
        _migrate_sector_and_auth_tables(connection)
        _prepare_customer_migration(connection)
        connection.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
        _migrate_profile_and_settings(connection)
        connection.commit()
        _migrate_sector_and_auth_tables(connection)
        _migrate_customer_entities(connection)
        _seed_ticket_id_sequence(connection)
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
