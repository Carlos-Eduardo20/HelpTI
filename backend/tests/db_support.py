import os
from pathlib import Path
from unittest.mock import patch

from backend import app as _app  # noqa: F401
from backend import database


def _remove_database(path):
    database_path = Path(path)
    for candidate in (
        database_path,
        Path(f'{database_path}-wal'),
        Path(f'{database_path}-shm'),
    ):
        candidate.unlink(missing_ok=True)


def use_temp_database(test):
    """Aponta o teste para um arquivo SQLite isolado, removido ao final."""
    path = database.INSTANCE_DIR / f'{test.id().replace(".", "_")}.sqlite3'
    overrides = {
        'DB_TYPE': 'sqlite',
        'DB_SQLITE_PATH': str(path),
    }
    env = patch.dict(os.environ, overrides)
    env.start()
    test.addCleanup(env.stop)
    test.addCleanup(_remove_database, path)
    return path
