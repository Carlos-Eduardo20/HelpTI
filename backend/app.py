from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Conexão com o banco de dados MySQL
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'helpti')
        )
        return conn
    except Error as e:
        print(f"Erro ao conectar: {e}")
        return None

# Helper para converter resultado em dicionário
def dict_fetchall(cursor):
    """Converte resultados do cursor em lista de dicionários"""
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def dict_fetchone(cursor):
    """Converte um resultado do cursor em dicionário"""
    columns = [description[0] for description in cursor.description]
    row = cursor.fetchone()
    if row:
        return dict(zip(columns, row))
    return None

# ============ ROTAS DE CHAMADOS ============

# Rota para listar todos os chamados
@app.route('/api/chamados', methods=['GET'])
def get_chamados():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM chamado ORDER BY id_chamado DESC;')
        chamados = dict_fetchall(cursor)
        
        cursor.close()
        conn.close()
        return jsonify(chamados), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

# Rota para buscar um chamado específico
@app.route('/api/chamados/<int:id>', methods=['GET'])
def get_chamado(id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM chamado WHERE id_chamado = %s;', (id,))
        chamado = dict_fetchone(cursor)
        
        cursor.close()
        conn.close()
        
        if chamado:
            return jsonify(chamado), 200
        else:
            return jsonify({'erro': 'Chamado não encontrado'}), 404
    except Error as e:
        return jsonify({'erro': str(e)}), 500

# Rota para criar um novo chamado
@app.route('/api/chamados', methods=['POST'])
def create_chamado():
    try:
        dados = request.get_json()
        
        cliente = dados.get('cliente')
        assunto = dados.get('assunto')
        prioridade = dados.get('prioridade', 'MEDIA')
        descricao = dados.get('descricao', '')
        id_tipo_chamado = dados.get('id_tipo_chamado', 1)

        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()
        
        query = """
            INSERT INTO chamado (id_tipo_chamado, status)
            VALUES (%s, 'ABERTO');
        """
        cursor.execute(query, (id_tipo_chamado,))
        conn.commit()
        
        novo_id = cursor.lastrowid
        
        cursor.execute('SELECT * FROM chamado WHERE id_chamado = %s;', (novo_id,))
        novo_chamado = dict_fetchone(cursor)
        
        cursor.close()
        conn.close()
        
        return jsonify(novo_chamado), 201
    except Error as e:
        return jsonify({'erro': str(e)}), 500

# Rota para atualizar um chamado
@app.route('/api/chamados/<int:id>', methods=['PUT'])
def update_chamado(id):
    try:
        dados = request.get_json()
        status = dados.get('status')

        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()
        
        query = "UPDATE chamado SET status = %s WHERE id_chamado = %s;"
        cursor.execute(query, (status, id))
        conn.commit()
        
        cursor.execute('SELECT * FROM chamado WHERE id_chamado = %s;', (id,))
        chamado_atualizado = dict_fetchone(cursor)
        
        cursor.close()
        conn.close()
        
        return jsonify(chamado_atualizado), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

# ============ ROTAS DE CLIENTES ============

# Rota para listar todos os clientes
@app.route('/api/clientes', methods=['GET'])
def get_clientes():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuario;')
        clientes = dict_fetchall(cursor)
        
        cursor.close()
        conn.close()
        return jsonify(clientes), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

# Rota para criar um novo cliente
@app.route('/api/clientes', methods=['POST'])
def create_cliente():
    try:
        dados = request.get_json()
        
        nome = dados.get('nome')
        email = dados.get('email')
        telefone = dados.get('telefone')
        contato = dados.get('contato')

        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()
        
        query = """
            INSERT INTO usuario (nome, email, telefone, contato)
            VALUES (%s, %s, %s, %s);
        """
        cursor.execute(query, (nome, email, telefone, contato))
        conn.commit()
        
        novo_id = cursor.lastrowid
        
        cursor.execute('SELECT * FROM usuario WHERE id_usuario = %s;', (novo_id,))
        novo_cliente = dict_fetchone(cursor)
        
        cursor.close()
        conn.close()
        
        return jsonify(novo_cliente), 201
    except Error as e:
        return jsonify({'erro': str(e)}), 500

# ============ ROTAS DE EQUIPE ============

# Rota para listar equipe
@app.route('/api/equipe', methods=['GET'])
def get_equipe():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM grupo_solucionadores;')
        equipe = dict_fetchall(cursor)
        
        cursor.close()
        conn.close()
        return jsonify(equipe), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

# ============ ROTAS DE RELATÓRIOS ============

# Rota para obter dados de relatórios
@app.route('/api/relatorios', methods=['GET'])
def get_relatorios():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()
        
        # Total de chamados por status
        cursor.execute("""
            SELECT status, COUNT(*) as total 
            FROM chamado 
            GROUP BY status;
        """)
        chamados_status = dict_fetchall(cursor)
        
        # Taxa de SLA
        cursor.execute("""
            SELECT COUNT(*) as total_resolvidos 
            FROM chamado 
            WHERE status = 'RESOLVIDO';
        """)
        cursor.fetchone()
        total_resolvidos = cursor.fetchone()[0] if cursor.fetchone() else 0
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'chamados_por_status': chamados_status,
            'total_resolvidos': total_resolvidos
        }), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

# ============ ROTAS DE CONFIGURAÇÕES ============

# Rota para obter configurações
@app.route('/api/configuracoes', methods=['GET'])
def get_configuracoes():
    try:
        # Por enquanto, retorna valores padrão
        # Você pode adicionar uma tabela de configurações no banco
        configuracoes = {
            'workspaceName': 'HelpTI Suporte',
            'supportEmail': 'suporte@helpti.com.br'
        }
        return jsonify(configuracoes), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# Rota para salvar configurações
@app.route('/api/configuracoes', methods=['PUT'])
def update_configuracoes():
    try:
        dados = request.get_json()
        # Aqui você pode salvar as configurações no banco de dados
        # Por enquanto, apenas retorna os dados recebidos
        return jsonify(dados), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ============ ROTA DE HEALTH CHECK ============

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'API rodando corretamente'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)