import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from werkzeug.security import check_password_hash

from backend import app as app_module
from backend import database


class SQLiteDatabaseTests(unittest.TestCase):
    def test_initialization_preserves_records_in_configured_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / 'helpti.sqlite3'
            with patch.dict(os.environ, {
                'DB_TYPE': 'sqlite',
                'DB_SQLITE_PATH': str(database_path),
                'HELPTI_DEMO_MODE': 'false',
            }):
                database.initialize_database()
                connection = database.get_db_connection()
                try:
                    connection.execute(
                        'INSERT INTO tipo_chamado (nome, classificacao, descricao) '
                        'VALUES (%s, %s, %s)',
                        ('Persistente', 'Teste', 'Registro de validação'),
                    )
                    connection.commit()
                finally:
                    connection.close()

                database.initialize_database()
                connection = database.get_db_connection()
                try:
                    record = connection.execute(
                        'SELECT descricao FROM tipo_chamado WHERE nome = %s',
                        ('Persistente',),
                    ).fetchone()
                    self.assertEqual(record['descricao'], 'Registro de validação')
                finally:
                    connection.close()

    def test_initialization_creates_demo_account_and_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / 'helpti.sqlite3'
            with patch.dict(os.environ, {
                'DB_TYPE': 'sqlite',
                'DB_SQLITE_PATH': str(database_path),
                'HELPTI_DEMO_MODE': 'true',
            }):
                database.initialize_database()
                connection = database.get_db_connection()
                try:
                    account = connection.execute(
                        'SELECT senha FROM grupo_solucionadores WHERE email = %s',
                        (database.DEMO_EMAIL,),
                    ).fetchone()
                    self.assertIsNotNone(account)
                    self.assertTrue(check_password_hash(account['senha'], 'HelpTI2026!'))
                    self.assertEqual(
                        connection.execute('SELECT COUNT(*) FROM tipo_chamado').fetchone()[0],
                        4,
                    )
                finally:
                    connection.close()

                app_module.app.config.update(TESTING=True)
                client = app_module.app.test_client()
                response = client.post('/api/login', json={
                    'email': database.DEMO_EMAIL,
                    'senha': 'HelpTI2026!',
                })
                self.assertEqual(response.status_code, 200, response.get_json())
                stats = client.get('/api/admin/db/stats')
                self.assertEqual(stats.status_code, 200, stats.get_json())
                self.assertTrue(stats.get_json()['caminho'].startswith('sqlite:///'))
                backup = client.get('/api/admin/db/backup')
                self.assertEqual(backup.status_code, 200, backup.get_json())
                self.assertIn('PRAGMA foreign_keys = OFF;', backup.get_data(as_text=True))
            self.assertTrue(database_path.is_file())


if __name__ == '__main__':
    unittest.main()