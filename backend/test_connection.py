from database import get_db_connection, initialize_database


initialize_database()
connection = get_db_connection()
try:
    cursor = connection.cursor()
    cursor.execute('SELECT COUNT(*) FROM tipo_chamado')
    total_tipos = cursor.fetchone()[0]
    if total_tipos < 1:
        raise RuntimeError('O banco não passou na verificação de integridade.')
    print(f'Banco MySQL pronto; {total_tipos} tipos de chamado disponíveis.')
finally:
    connection.close()
