from database import get_db_connection, initialize_database


initialize_database()
connection = get_db_connection()
try:
    cursor = connection.cursor()
    cursor.execute('SELECT COUNT(*) FROM tipo_chamado')
    total_tipos = cursor.fetchone()[0]
    cursor.execute('PRAGMA foreign_key_check')
    problemas_relacionais = cursor.fetchall()
    if total_tipos < 1 or problemas_relacionais:
        raise RuntimeError('O banco não passou na verificação de integridade.')
    print(f'Banco SQLite pronto; {total_tipos} tipos de chamado disponíveis.')
finally:
    connection.close()
