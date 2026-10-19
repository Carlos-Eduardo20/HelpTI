import os
import uuid
from unittest.mock import patch

from backend import app as _app  # noqa: F401  (carrega backend/.env com as credenciais do MySQL)
from backend import database


def _drop_database(name):
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
    env = patch.dict(os.environ, {'DB_NAME': name})
    env.start()
    test.addCleanup(env.stop)
    test.addCleanup(_drop_database, name)
    return name
