import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

load_dotenv()

host = os.getenv('DB_HOST', 'localhost')
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD', '')
database = os.getenv('DB_NAME', 'HelpTI')
try:
    port = int(os.getenv('DB_PORT', '3306'))
except (TypeError, ValueError):
    port = 3306

print(f"Tentando conectar em {user}@{host}:{port}/{database}")
try:
    conn = mysql.connector.connect(host=host, user=user, password=password, database=database, port=port)
    if conn.is_connected():
        print("Conectado ao MySQL — versão:", conn.get_server_info())
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES;")
        print("Databases:", [row[0] for row in cursor.fetchall()])
        cursor.execute("SHOW TABLES;")
        print("Tables:", [row[0] for row in cursor.fetchall()])
        cursor.close()
        conn.close()
    else:
        print("Não foi possível conectar (conn.is_connected() retornou False)")
except Error as e:
    print("Erro ao conectar:", e)
