from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os
import re
import secrets
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
import webbrowser
from threading import Timer

load_dotenv()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='/frontend')
CORS(app)


@app.route('/')
def index():
    return redirect('/frontend/pages/login.html')

# Conexão com o banco de dados MySQL
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'helpti'),
            port=int(os.getenv('DB_PORT', '3306'))
        )
        return conn
    except Error as e:
        print(f"Erro ao conectar: {e}")
        return None

def ensure_data_columns():
    """Mantém bancos antigos compatíveis com os campos usados pela aplicação."""
    conn = get_db_connection()
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS configuracao (
        id_configuracao INT NOT NULL PRIMARY KEY,
        workspace_name VARCHAR(200) NOT NULL,
        support_email VARCHAR(255) NOT NULL
    )""")
    cursor.execute("""INSERT IGNORE INTO configuracao
        (id_configuracao, workspace_name, support_email)
        VALUES (1, 'HelpTI Suporte', 'suporte@helpti.com.br')""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS setor (
        id_setor INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(150) NOT NULL UNIQUE,
        descricao VARCHAR(500)
    )""")
    statements = (
        "ALTER TABLE usuario ADD COLUMN cnpj VARCHAR(30)",
        "ALTER TABLE usuario ADD COLUMN plano VARCHAR(100)",
        "ALTER TABLE usuario ADD COLUMN acoes VARCHAR(500)",
        "ALTER TABLE chamado AUTO_INCREMENT = 100000",
        "ALTER TABLE chamado ADD COLUMN cliente VARCHAR(200)",
        "ALTER TABLE chamado ADD COLUMN assunto VARCHAR(255)",
        "ALTER TABLE chamado ADD COLUMN descricao TEXT",
        "ALTER TABLE chamado ADD COLUMN email_cliente VARCHAR(255)",
        "ALTER TABLE chamado ADD COLUMN data_agendada DATE",
        "ALTER TABLE chamado ADD COLUMN hora_agendada TIME",
        "ALTER TABLE grupo_solucionadores ADD COLUMN nome VARCHAR(200)",
        "ALTER TABLE grupo_solucionadores ADD COLUMN email VARCHAR(255)",
        "ALTER TABLE grupo_solucionadores ADD COLUMN cargo VARCHAR(100)",
        "ALTER TABLE grupo_solucionadores ADD COLUMN valor_hora DECIMAL(10, 2)",
        "ALTER TABLE grupo_solucionadores ADD COLUMN status VARCHAR(50) DEFAULT 'ATIVO'",
        "ALTER TABLE grupo_solucionadores ADD COLUMN senha VARCHAR(255)",
        "ALTER TABLE grupo_solucionadores ADD COLUMN id_setor INT"
    )
    for statement in statements:
        try:
            cursor.execute(statement)
        except Error as error:
            if error.errno not in (1060, 1146):
                print(f"Aviso na compatibilidade do banco: {error}")
    conn.commit()
    try:
        cursor.execute("ALTER TABLE grupo_solucionadores ADD CONSTRAINT fk_grupo_setor FOREIGN KEY (id_setor) REFERENCES setor(id_setor)")
        conn.commit()
    except Error as error:
        if error.errno not in (1060, 1826, 1828):
            print(f"Aviso ao vincular setores: {error}")
    cursor.close()
    conn.close()

def email_valido(email):
    return bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email or ''))

def enviar_email_resolucao(chamado):
    smtp_host = os.getenv('SMTP_HOST')
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    smtp_from = os.getenv('SMTP_FROM', smtp_user)
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_tls = os.getenv('SMTP_TLS', 'true').lower() == 'true'
    smtp_auth = os.getenv('SMTP_AUTH', 'true').lower() == 'true'

    if not smtp_host or not smtp_from or (smtp_auth and not all((smtp_user, smtp_password))):
        raise RuntimeError('SMTP não configurado. Preencha as variáveis SMTP no backend/.env')

    mensagem = EmailMessage()
    mensagem['Subject'] = f'Chamado #{chamado["id_chamado"]} resolvido - HelpTI'
    mensagem['From'] = smtp_from
    mensagem['To'] = chamado['email_cliente']
    mensagem.set_content(
        f'Olá, {chamado.get("cliente") or "cliente"}!\n\n'
        f'O chamado #{chamado["id_chamado"]} foi marcado como resolvido.\n'
        f'Assunto: {chamado.get("assunto") or "-"}\n\n'
        f'Descrição: {chamado.get("descricao") or "-"}\n'
        f'Data agendada: {chamado.get("data_agendada") or "-"}\n\n'
        'Se o problema continuar, entre em contato com o suporte.\n\n'
        'Equipe HelpTI'
    )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as servidor:
        if smtp_tls:
            servidor.starttls()
        if smtp_auth:
            servidor.login(smtp_user, smtp_password)
        servidor.send_message(mensagem)

@app.route('/api/login', methods=['POST'])
def login():
    dados = request.get_json(silent=True) or {}
    email = (dados.get('email') or '').strip().lower()
    senha = dados.get('senha') or ''

    if not email or not senha:
        return jsonify({'erro': 'E-mail e senha são obrigatórios'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'erro': 'Erro ao conectar ao banco'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id_grupo_solucionadores, nome, email, senha FROM grupo_solucionadores WHERE LOWER(email) = %s AND status = 'ATIVO' LIMIT 1",
            (email,)
        )
        usuario = cursor.fetchone()

        if not usuario or usuario['senha'] != senha:
            return jsonify({'erro': 'E-mail ou senha inválidos'}), 401

        return jsonify({
            'id': usuario['id_grupo_solucionadores'],
            'nome': usuario['nome'] or email.split('@')[0],
            'email': usuario['email']
        }), 200
    except Error as error:
        return jsonify({'erro': str(error)}), 500
    finally:
        cursor.close()
        conn.close()

# Helper para converter resultado em dicionário
def dict_fetchall(cursor):
    """Converte resultados do cursor em lista de dicionários"""
    columns = [description[0] for description in cursor.description]
    return [normalize_record(dict(zip(columns, row))) for row in cursor.fetchall()]

def dict_fetchone(cursor):
    """Converte um resultado do cursor em dicionário"""
    columns = [description[0] for description in cursor.description]
    row = cursor.fetchone()
    if row:
        return normalize_record(dict(zip(columns, row)))
    return None

def normalize_record(record):
    record.pop('senha', None)
    record.pop('senha_hash', None)
    for key, value in record.items():
        if isinstance(value, timedelta):
            total_seconds = int(value.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            record[key] = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
        elif hasattr(value, 'isoformat'):
            record[key] = value.isoformat()
    return record

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
        descricao = dados.get('descricao', '')
        email_cliente = (dados.get('email_cliente') or '').strip().lower()
        id_tipo_chamado = dados.get('id_tipo_chamado', 1)
        data_agendada = dados.get('data_agendada') or None
        hora_agendada = dados.get('hora_agendada') or None

        if not cliente or not assunto or not email_valido(email_cliente):
            return jsonify({'erro': 'Cliente, assunto e um e-mail válido são obrigatórios'}), 400

        if data_agendada:
            try:
                data_agendada_date = datetime.strptime(data_agendada, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'erro': 'Data de agendamento inválida'}), 400
            if data_agendada_date.weekday() >= 5:
                return jsonify({'erro': 'Chamados só podem ser agendados de segunda a sexta-feira'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()
        
        novo_id = None
        for _ in range(10):
            candidato = secrets.randbelow(900000) + 100000
            cursor.execute('SELECT 1 FROM chamado WHERE id_chamado = %s;', (candidato,))
            if not cursor.fetchone():
                novo_id = candidato
                break
        if novo_id is None:
            cursor.close()
            conn.close()
            return jsonify({'erro': 'Não foi possível gerar um ID disponível'}), 503

        query = """
            INSERT INTO chamado
                (id_chamado, id_tipo_chamado, status, cliente, email_cliente, assunto, descricao, data_agendada, hora_agendada)
            VALUES (%s, %s, 'ABERTO', %s, %s, %s, %s, %s, %s);
        """
        cursor.execute(query, (novo_id, id_tipo_chamado, cliente, email_cliente, assunto, descricao, data_agendada, hora_agendada))
        conn.commit()
        
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
        if status not in ('ABERTO', 'ANDAMENTO', 'AGUARDANDO', 'RESOLVIDO'):
            return jsonify({'erro': 'Status inválido'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM chamado WHERE id_chamado = %s;', (id,))
        chamado_atual = dict_fetchone(cursor)
        if not chamado_atual:
            cursor.close()
            conn.close()
            return jsonify({'erro': 'Chamado não encontrado'}), 404
        if status == 'RESOLVIDO' and chamado_atual['status'] != 'RESOLVIDO':
            if not email_valido(chamado_atual.get('email_cliente')):
                cursor.close()
                conn.close()
                return jsonify({'erro': 'Este chamado não possui um e-mail válido para notificação'}), 400
            try:
                enviar_email_resolucao(chamado_atual)
            except (OSError, smtplib.SMTPException, RuntimeError) as error:
                cursor.close()
                conn.close()
                return jsonify({'erro': f'Não foi possível enviar o e-mail de resolução: {error}'}), 502
        
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
        cnpj = dados.get('cnpj')
        plano = dados.get('plano')
        acoes = dados.get('acoes')

        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()
        
        senha = dados.get('senha') or ''
        query = """
            INSERT INTO usuario (nome, email, telefone, contato, cnpj, plano, acoes, senha_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """
        senha_hash = generate_password_hash(senha) if senha else None
        cursor.execute(query, (nome, email, telefone, contato, cnpj, plano, acoes, senha_hash))
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
        cursor.execute('''SELECT g.*, s.nome AS setor_nome
                  FROM grupo_solucionadores g
                  LEFT JOIN setor s ON s.id_setor = g.id_setor
                  ORDER BY g.id_grupo_solucionadores DESC;''')
        equipe = dict_fetchall(cursor)
        
        cursor.close()
        conn.close()
        return jsonify(equipe), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/equipe', methods=['POST'])
def create_equipe():
    try:
        dados = request.get_json() or {}
        nome = dados.get('nome')
        email = dados.get('email')
        cargo = dados.get('cargo', 'tecnico')
        valor_hora = dados.get('valor_hora') or None
        senha = dados.get('senha') or ''
        id_setor = dados.get('id_setor') or None
        if not nome or not email:
            return jsonify({'erro': 'Nome e e-mail são obrigatórios'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO grupo_solucionadores
            (descricao, nivel, nome, email, cargo, valor_hora, senha, status, id_setor)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'ATIVO', %s)""",
            (nome, 1, nome, email, cargo, valor_hora,
             senha, id_setor)
        )
        conn.commit()
        novo_id = cursor.lastrowid
        cursor.execute('SELECT * FROM grupo_solucionadores WHERE id_grupo_solucionadores = %s', (novo_id,))
        novo_membro = dict_fetchone(cursor)
        cursor.close()
        conn.close()
        return jsonify(novo_membro), 201
    except Error as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/setores', methods=['GET'])
def get_setores():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute('''SELECT s.id_setor, s.nome, s.descricao,
                                 COUNT(g.id_grupo_solucionadores) AS total_membros
                          FROM setor s
                          LEFT JOIN grupo_solucionadores g ON g.id_setor = s.id_setor
                          GROUP BY s.id_setor, s.nome, s.descricao
                          ORDER BY s.nome''')
        setores = dict_fetchall(cursor)
        cursor.close()
        conn.close()
        return jsonify(setores), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/setores', methods=['POST'])
def create_setor():
    try:
        dados = request.get_json() or {}
        nome = (dados.get('nome') or '').strip()
        descricao = (dados.get('descricao') or '').strip() or None
        if not nome:
            return jsonify({'erro': 'O nome do setor é obrigatório'}), 400
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute('INSERT INTO setor (nome, descricao) VALUES (%s, %s)', (nome, descricao))
        conn.commit()
        novo_id = cursor.lastrowid
        cursor.execute('SELECT id_setor, nome, descricao, 0 AS total_membros FROM setor WHERE id_setor = %s', (novo_id,))
        novo_setor = dict_fetchone(cursor)
        cursor.close()
        conn.close()
        return jsonify(novo_setor), 201
    except Error as e:
        if e.errno == 1062:
            return jsonify({'erro': 'Já existe um setor com esse nome'}), 409
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
        periodo = request.args.get('periodo', 'todos')
        filtro_periodo = ''
        if periodo == 'dia':
            filtro_periodo = ' WHERE data_agendada = CURDATE()'
        elif periodo == 'mes':
            filtro_periodo = ' WHERE YEAR(data_agendada) = YEAR(CURDATE()) AND MONTH(data_agendada) = MONTH(CURDATE())'
        
        # Total de chamados por status
        cursor.execute("""
            SELECT status, COUNT(*) as total 
            FROM chamado 
        """ + filtro_periodo + " GROUP BY status;")
        chamados_status = dict_fetchall(cursor)
        
        # Taxa de SLA
        cursor.execute("""
            SELECT COUNT(*) as total_resolvidos 
            FROM chamado 
            """ + (' WHERE status = \'RESOLVIDO\'' if not filtro_periodo else filtro_periodo + " AND status = 'RESOLVIDO'") + ";")
        total_resolvidos = cursor.fetchone()[0]

        total_chamados = sum(int(item['total']) for item in chamados_status)
        pendentes = total_chamados - total_resolvidos
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'chamados_por_status': chamados_status,
            'total_chamados': total_chamados,
            'total_resolvidos': total_resolvidos,
            'total_pendentes': pendentes,
            'periodo': periodo
        }), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

# ============ ROTAS DE CONFIGURAÇÕES ============

# Rota para obter configurações
@app.route('/api/configuracoes', methods=['GET'])
def get_configuracoes():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT workspace_name, support_email FROM configuracao WHERE id_configuracao = 1')
        registro = cursor.fetchone()
        cursor.close()
        conn.close()
        configuracoes = {
            'workspaceName': registro['workspace_name'] if registro else 'HelpTI Suporte',
            'supportEmail': registro['support_email'] if registro else 'suporte@helpti.com.br'
        }
        return jsonify(configuracoes), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

# Rota para salvar configurações
@app.route('/api/configuracoes', methods=['PUT'])
def update_configuracoes():
    try:
        dados = request.get_json() or {}
        workspace_name = dados.get('workspaceName')
        support_email = dados.get('supportEmail')
        if not workspace_name or not support_email:
            return jsonify({'erro': 'Nome do workspace e e-mail são obrigatórios'}), 400
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO configuracao
            (id_configuracao, workspace_name, support_email) VALUES (1, %s, %s)
            ON DUPLICATE KEY UPDATE workspace_name = VALUES(workspace_name), support_email = VALUES(support_email)""",
            (workspace_name, support_email))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'workspaceName': workspace_name, 'supportEmail': support_email}), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

# ============ ROTA DE HEALTH CHECK ============

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'API rodando corretamente'}), 200

if __name__ == '__main__':
    ensure_data_columns()
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in ('1', 'true', 'yes', 'on')
    frontend_url = 'http://127.0.0.1:5000/'
    if not debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        Timer(1, lambda: webbrowser.open(frontend_url)).start()
    app.run(debug=debug, port=5000)