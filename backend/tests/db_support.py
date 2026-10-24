import os
import uuid
from pathlib import Path
from unittest.mock import patch

from backend import app as _app  # noqa: F401  (carrega backend/.env com as credenciais do MySQL)
from backend import database


def _drop_database(name):
    if database.database_settings()['type'] == 'sqlite':
        Path(database.database_settings()['database']).unlink(missing_ok=True)
        return
    server = database._connect(with_database=False)
    try:
        cursor = server.cursor()
        cursor.execute(f'DROP DATABASE IF EXISTS `{name}`')
        cursor.close()
    finally:
        server.close()


def use_temp_database(test):
    """Aponta o teste para um banco MySQL exclusivo, removido ao final."""
    name = f'helpti_test_{uuid.uuid4().hex[:12]}'
    overrides = {'DB_NAME': name}
    if database.database_settings()['type'] == 'sqlite':
        overrides['DB_SQLITE_PATH'] = str(database.INSTANCE_DIR / f'{name}.sqlite3')
    env = patch.dict(os.environ, overrides)
    env.start()
    test.addCleanup(env.stop)
    test.addCleanup(_drop_database, name)
    return name
