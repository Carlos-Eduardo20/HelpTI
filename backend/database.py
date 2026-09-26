import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Carregar a configuração do backend independentemente do diretório de execução.
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

class Database:
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.database = os.getenv('DB_NAME', 'HelpTI')
        self.user = os.getenv('DB_USER', 'root')
        self.password = os.getenv('DB_PASSWORD', '')
        self.port = os.getenv('DB_PORT', '3306')
        self.conn = None
        self.cursor = None

    def connect(self):
        """Conecta ao banco de dados"""
        try:
            self.conn = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
            self.cursor = self.conn.cursor(dictionary=True)
            print("Conexão com o banco de dados MySQL estabelecida com sucesso!")
            return True
        except Error as e:
            print(f"Erro ao conectar ao banco de dados: {e}")
            return False

    def disconnect(self):
        """Desconecta do banco de dados"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("Desconectado do banco de dados")

    def execute_query(self, query, params=None):
        """Executa uma query SELECT"""
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchall()
        except Error as e:
            print(f"Erro ao executar query: {e}")
            return None

    def execute_update(self, query, params):
        """Executa INSERT, UPDATE ou DELETE"""
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except Error as e:
            self.conn.rollback()
            print(f"Erro ao executar update: {e}")
            return False

    def execute_insert(self, query, params):
        """Executa INSERT e retorna o ID gerado"""
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return self.cursor.lastrowid
        except Error as e:
            self.conn.rollback()
            print(f"Erro ao executar insert: {e}")
            return None

# Instância global do banco de dados
db = Database()

# Função helper para obter conexão
def get_db_connection():
    """Retorna uma nova conexão com o banco de dados MySQL"""
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'HelpTI'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            port=os.getenv('DB_PORT', '3306')
        )
        return conn
    except Error as e:
        print(f"Erro ao conectar: {e}")
        return None

