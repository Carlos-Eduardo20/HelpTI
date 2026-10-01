from flask import Flask, request, jsonify, redirect, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from flask_cors import CORS
from sqlite3 import Error
import os
import json
import re
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from dotenv import load_dotenv
import webbrowser
from threading import Timer

try:
    from .database import get_db_connection, initialize_database
except ImportError:
    from database import get_db_connection, initialize_database

BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, '.env'))
load_dotenv()



app = Flask(__name__)
CORS(app)

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))


@app.route('/')
def frontend_entrypoint():
    return redirect('/frontend/pages/login.html')


@app.route('/frontend/<path:filename>')
def frontend_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)

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
        cursor.execute('''
            SELECT chamado.*, setor.nome AS setor_nome, grupo_solucionadores.nome AS tecnico
            FROM chamado
            LEFT JOIN setor ON setor.id_setor = chamado.id_setor
            LEFT JOIN grupo_solucionadores ON grupo_solucionadores.id_grupo_solucionadores = chamado.id_grupo_solucionadores
            ORDER BY chamado.id_chamado DESC;
        ''')
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
        cursor.execute('''
            SELECT chamado.*, setor.nome AS setor_nome, grupo_solucionadores.nome AS tecnico
            FROM chamado
            LEFT JOIN setor ON setor.id_setor = chamado.id_setor
            LEFT JOIN grupo_solucionadores ON grupo_solucionadores.id_grupo_solucionadores = chamado.id_grupo_solucionadores
            WHERE chamado.id_chamado = %s;
        ''', (id,))
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
        dados = request.get_json() or {}
        
        cliente = (dados.get('cliente') or '').strip()
        descricao = (dados.get('descricao') or '').strip()
        email_cliente = (dados.get('email_cliente') or '').strip()
        telefone_cliente = (dados.get('telefone_cliente') or '').strip()
        contato_cliente = (dados.get('contato_cliente') or '').strip()
        telefone_contato = (dados.get('telefone_contato') or '').strip()
        id_setor = dados.get('id_setor')
        id_grupo_solucionadores = dados.get('id_grupo_solucionadores')
        id_tipo_chamado = dados.get('id_tipo_chamado', 1)

        if not cliente or not email_cliente or not telefone_cliente or not contato_cliente or not telefone_contato or not descricao or not id_setor or not id_grupo_solucionadores:
            return jsonify({'erro': 'Todos os campos do chamado são obrigatórios'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id_grupo_solucionadores
            FROM grupo_solucionadores
            WHERE id_grupo_solucionadores = %s AND id_setor = %s AND status = 'ATIVO'
        ''', (id_grupo_solucionadores, id_setor))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'erro': 'O técnico selecionado não pertence ao setor informado ou está inativo'}), 400
        
        query = """
            INSERT INTO chamado
                (id_tipo_chamado, id_setor, id_grupo_solucionadores, status, cliente, descricao,
                 email_cliente, telefone_cliente, contato_cliente, telefone_contato)
            VALUES (%s, %s, %s, 'ABERTO', %s, %s, %s, %s, %s, %s);
        """
        cursor.execute(query, (id_tipo_chamado, id_setor, id_grupo_solucionadores, cliente, descricao,
                               email_cliente, telefone_cliente, contato_cliente, telefone_contato))
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
        dados = request.get_json() or {}
        acao = dados.get('acao')

        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM chamado WHERE id_chamado = %s FOR UPDATE', (id,))
        chamado = dict_fetchone(cursor)
        if not chamado:
            cursor.close()
            conn.close()
            return jsonify({'erro': 'Chamado não encontrado'}), 404

        status = chamado.get('status') or 'ABERTO'
        segundos = int(chamado.get('tempo_decorrido_segundos') or 0)
        inicio = chamado.get('tempo_inicio')
        if isinstance(inicio, str):
            inicio = datetime.fromisoformat(inicio)
        agora = datetime.now()

        if acao == 'agendar':
            agendamento = dados.get('data_agendada')
            if not agendamento:
                return jsonify({'erro': 'Informe a data e hora do agendamento'}), 400
            data, hora = agendamento.split('T', 1)
            cursor.execute('UPDATE chamado SET data_agendada = %s, hora_agendada = %s WHERE id_chamado = %s', (data, hora, id))
        elif acao == 'atualizar_contato':
            contato = (dados.get('contato_cliente') or '').strip()
            telefone = (dados.get('telefone_contato') or '').strip()
            if not contato:
                return jsonify({'erro': 'Selecione um contato válido'}), 400
            cursor.execute('UPDATE chamado SET contato_cliente = %s, telefone_contato = %s WHERE id_chamado = %s', (contato, telefone, id))
        elif acao == 'iniciar':
            if status not in ('ABERTO', 'PAUSADO', 'ANDAMENTO'):
                return jsonify({'erro': 'Este chamado não pode ser iniciado'}), 400
            cursor.execute("UPDATE chamado SET status = 'ANDAMENTO', tempo_inicio = COALESCE(tempo_inicio, %s) WHERE id_chamado = %s", (agora, id))
        elif acao == 'pausar':
            if status != 'ANDAMENTO' or not inicio:
                return jsonify({'erro': 'Somente um chamado em andamento pode ser pausado'}), 400
            segundos += max(0, int((agora - inicio).total_seconds()))
            cursor.execute("UPDATE chamado SET status = 'PAUSADO', tempo_inicio = NULL, tempo_decorrido_segundos = %s WHERE id_chamado = %s", (segundos, id))
        elif acao == 'escalonar':
            id_setor = dados.get('id_setor')
            id_tecnico = dados.get('id_grupo_solucionadores')
            motivo = (dados.get('descricao') or '').strip()
            if status != 'PAUSADO':
                return jsonify({'erro': 'Pause o chamado antes de escaloná-lo'}), 400
            if not id_setor or not id_tecnico or not motivo:
                return jsonify({'erro': 'Informe o setor, o técnico e a descrição do escalonamento'}), 400
            cursor.execute("SELECT nivel FROM grupo_solucionadores WHERE id_grupo_solucionadores = %s AND id_setor = %s AND status = 'ATIVO'", (id_tecnico, id_setor))
            tecnico = cursor.fetchone()
            if not tecnico:
                return jsonify({'erro': 'O técnico selecionado não pertence ao setor informado ou está inativo'}), 400
            cursor.execute('UPDATE chamado SET id_setor = %s, id_grupo_solucionadores = %s WHERE id_chamado = %s', (id_setor, id_tecnico, id))
            cursor.execute('INSERT INTO escalonamento (id_chamado, motivo, nivel, data_escalonamento, id_setor_destino, id_grupo_destino) VALUES (%s, %s, %s, %s, %s, %s)', (id, motivo, tecnico[0], agora.date(), id_setor, id_tecnico))
        elif acao == 'encerrar':
            descricao_final = (dados.get('descricao_final') or '').strip()
            if status not in ('ANDAMENTO', 'PAUSADO') or not descricao_final:
                return jsonify({'erro': 'Informe a descrição final após iniciar o atendimento'}), 400
            if inicio:
                segundos += max(0, int((agora - inicio).total_seconds()))
            smtp_host = os.getenv('SMTP_HOST')
            smtp_user = os.getenv('SMTP_USER')
            smtp_password = os.getenv('SMTP_PASSWORD')
            destinatario = chamado.get('email_cliente')
            if not all((smtp_host, smtp_user, smtp_password, destinatario)):
                return jsonify({'erro': 'Configure o SMTP e o e-mail do cliente antes de encerrar o chamado'}), 503
            mensagem = EmailMessage()
            mensagem['Subject'] = f'Chamado #{id} resolvido'
            mensagem['From'] = os.getenv('SMTP_FROM') or smtp_user
            mensagem['To'] = destinatario
            mensagem.set_content(f"Olá, {chamado.get('cliente') or 'cliente'}.\n\nO chamado #{id} foi resolvido.\nTempo de atendimento: {segundos // 60} min.\n\nDescrição inicial:\n{chamado.get('descricao') or 'Não informada'}\n\nSolução aplicada:\n{descricao_final}")
            try:
                with smtplib.SMTP(smtp_host, int(os.getenv('SMTP_PORT', '587')), timeout=15) as servidor:
                    servidor.starttls()
                    servidor.login(smtp_user, smtp_password)
                    servidor.send_message(mensagem)
            except (OSError, smtplib.SMTPException, ValueError) as error:
                cursor.close()
                conn.close()
                return jsonify({'erro': f'Não foi possível enviar o e-mail: {error}'}), 502
            cursor.execute("UPDATE chamado SET status = 'RESOLVIDO', tempo_inicio = NULL, tempo_decorrido_segundos = %s, descricao_final = %s WHERE id_chamado = %s", (segundos, descricao_final, id))
        elif 'status' in dados:
            status_novo = dados.get('status')
            if status_novo == 'RESOLVIDO':
                return jsonify({'erro': 'Encerre o chamado pelo atendimento para enviar o e-mail de resolução'}), 400
            if status_novo not in ('ABERTO', 'ANDAMENTO', 'AGUARDANDO', 'PAUSADO'):
                return jsonify({'erro': 'Status inválido'}), 400
            if status_novo == 'PAUSADO' and status != 'ANDAMENTO':
                return jsonify({'erro': 'Inicie o atendimento antes de pausá-lo'}), 400
            if status == 'ANDAMENTO' and status_novo != 'ANDAMENTO' and inicio:
                segundos += max(0, int((agora - inicio).total_seconds()))
                inicio = None
            if status_novo == 'ANDAMENTO' and status != 'ANDAMENTO':
                inicio = agora
            cursor.execute('UPDATE chamado SET status = %s, tempo_inicio = %s, tempo_decorrido_segundos = %s WHERE id_chamado = %s', (status_novo, inicio, segundos, id))
        else:
            return jsonify({'erro': 'Ação inválida'}), 400
        conn.commit()
        
        cursor.execute('SELECT * FROM chamado WHERE id_chamado = %s;', (id,))
        chamado_atualizado = dict_fetchone(cursor)
        
        cursor.close()
        conn.close()
        
        return jsonify(chamado_atualizado), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/chamados/<int:id>', methods=['DELETE'])
def delete_chamado(id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500

        cursor = conn.cursor()
        cursor.execute('DELETE FROM escalonamento WHERE id_chamado = %s;', (id,))
        cursor.execute('DELETE FROM chamado WHERE id_chamado = %s;', (id,))
        removido = cursor.rowcount
        conn.commit()

        cursor.close()
        conn.close()
        if not removido:
            return jsonify({'erro': 'Chamado não encontrado'}), 404
        return jsonify({'mensagem': 'Chamado encerrado e removido com sucesso'}), 200
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

        if clientes:
            ids = [cliente['id_usuario'] for cliente in clientes]
            placeholders = ', '.join(['%s'] * len(ids))
            cursor.execute(f'SELECT id_usuario, nome, email, telefone FROM cliente_contato WHERE id_usuario IN ({placeholders}) ORDER BY id_cliente_contato', ids)
            contatos_por_cliente = {}
            for contato in dict_fetchall(cursor):
                contatos_por_cliente.setdefault(contato['id_usuario'], []).append({
                    'nome': contato['nome'],
                    'email': contato['email'],
                    'telefone': contato['telefone']
                })
            for cliente in clientes:
                contatos = contatos_por_cliente.get(cliente['id_usuario'])
                if not contatos and any(cliente.get(campo) for campo in ('contato', 'email', 'telefone')):
                    contatos = [{
                        'nome': cliente.get('contato') or '',
                        'email': cliente.get('email') or '',
                        'telefone': cliente.get('telefone') or ''
                    }]
                cliente['contatos'] = contatos or []
        
        cursor.close()
        conn.close()
        return jsonify(clientes), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

# Rota para criar um novo cliente
@app.route('/api/clientes', methods=['POST'])
def create_cliente():
    try:
        dados = request.get_json() or {}
        nome = (dados.get('nome') or '').strip()
        contatos = dados.get('contatos') or []
        if not contatos and any(dados.get(campo) for campo in ('email', 'telefone', 'contato')):
            contatos = [{
                'email': dados.get('email'),
                'telefone': dados.get('telefone'),
                'nome': dados.get('contato')
            }]
        contatos = [{campo: (item.get(campo) or '').strip() for campo in ('email', 'nome', 'telefone')} for item in contatos if isinstance(item, dict)]

        if not nome or not contatos:
            return jsonify({'erro': 'Empresa e pelo menos um contato são obrigatórios'}), 400
        if any(not contato[campo] for contato in contatos for campo in ('email', 'nome', 'telefone')):
            return jsonify({'erro': 'Preencha e-mail, nome e telefone de todos os contatos'}), 400

        primeiro_contato = contatos[0]

        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()
        
        query = """
            INSERT INTO usuario (nome, cnpj, telefone_empresa, endereco, email, telefone, contato, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'ATIVO');
        """
        cnpj = (dados.get('cnpj') or '').strip() or None
        telefone_empresa = (dados.get('telefone_empresa') or '').strip() or None
        endereco = (dados.get('endereco') or '').strip() or None
        cursor.execute(query, (nome, cnpj, telefone_empresa, endereco, primeiro_contato['email'], primeiro_contato['telefone'], primeiro_contato['nome']))
        novo_id = cursor.lastrowid
        cursor.executemany(
            'INSERT INTO cliente_contato (id_usuario, nome, email, telefone) VALUES (%s, %s, %s, %s)',
            [(novo_id, contato['nome'], contato['email'], contato['telefone']) for contato in contatos]
        )
        conn.commit()
        
        cursor.execute('SELECT * FROM usuario WHERE id_usuario = %s;', (novo_id,))
        novo_cliente = dict_fetchone(cursor)
        
        novo_cliente['contatos'] = contatos
        return jsonify(novo_cliente), 201
    except Error as e:
        if 'conn' in locals() and conn:
            conn.rollback()
        return jsonify({'erro': str(e)}), 500
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

@app.route('/api/clientes/<int:id>', methods=['PUT'])
def update_cliente(id):
    dados = request.get_json() or {}
    campos = {campo: dados[campo] for campo in ('cnpj', 'email', 'telefone', 'telefone_empresa', 'endereco', 'status', 'contato') if campo in dados}
    if not campos:
        return jsonify({'erro': 'Nenhum campo para atualizar'}), 400
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        valores = list(campos.values()) + [id]
        cursor.execute(f"UPDATE usuario SET {', '.join(f'{campo} = %s' for campo in campos)} WHERE id_usuario = %s", valores)
        conn.commit()
        cursor.execute('SELECT * FROM usuario WHERE id_usuario = %s', (id,))
        cliente = dict_fetchone(cursor)
        cursor.close()
        conn.close()
        if not cliente:
            return jsonify({'erro': 'Cliente não encontrado'}), 404
        return jsonify(cliente), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/clientes/<int:id>', methods=['DELETE'])
def delete_cliente(id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute('DELETE FROM usuario WHERE id_usuario = %s', (id,))
        conn.commit()
        removido = cursor.rowcount
        cursor.close()
        conn.close()
        if not removido:
            return jsonify({'erro': 'Cliente não encontrado'}), 404
        return jsonify({'mensagem': 'Cliente removido com sucesso'}), 200
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
        cursor.execute('''
            SELECT grupo_solucionadores.*, setor.nome AS setor_nome
            FROM grupo_solucionadores
            LEFT JOIN setor ON setor.id_setor = grupo_solucionadores.id_setor
            ORDER BY grupo_solucionadores.id_grupo_solucionadores DESC;
        ''')
        equipe = dict_fetchall(cursor)
        for membro in equipe:
            membro.pop('senha', None)
        
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
        senha = dados.get('senha')
        cargo = dados.get('cargo', 'tecnico')
        nivel = dados.get('nivel') or None
        valor_hora = dados.get('valor_hora') or None
        id_setor = dados.get('id_setor') or None
        telefone = dados.get('telefone') or None
        data_inicio = dados.get('data_inicio') or datetime.now().date()
        if not nome or not email or not senha:
            return jsonify({'erro': 'Nome, e-mail e senha são obrigatórios'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO grupo_solucionadores
            (descricao, nivel, nome, email, cargo, valor_hora, id_setor, data_inicio, status, senha, telefone)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'ATIVO', %s, %s)""",
            (nome, nivel, nome, email, cargo, valor_hora, id_setor, data_inicio, senha, telefone)
        )
        conn.commit()
        novo_id = cursor.lastrowid
        cursor.execute('SELECT * FROM grupo_solucionadores WHERE id_grupo_solucionadores = %s', (novo_id,))
        novo_membro = dict_fetchone(cursor)
        novo_membro.pop('senha', None)
        cursor.close()
        conn.close()
        return jsonify(novo_membro), 201
    except Error as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/equipe/<int:id>', methods=['PUT'])
def update_equipe(id):
    dados = request.get_json() or {}
    campos = {campo: dados[campo] for campo in ('email', 'telefone', 'data_inicio', 'valor_hora', 'cargo', 'id_setor', 'nivel', 'status') if campo in dados}
    if not campos:
        return jsonify({'erro': 'Nenhum campo para atualizar'}), 400
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        valores = list(campos.values()) + [id]
        cursor.execute(f"UPDATE grupo_solucionadores SET {', '.join(f'{campo} = %s' for campo in campos)} WHERE id_grupo_solucionadores = %s", valores)
        conn.commit()
        cursor.execute('SELECT * FROM grupo_solucionadores WHERE id_grupo_solucionadores = %s', (id,))
        membro = dict_fetchone(cursor)
        cursor.close()
        conn.close()
        if not membro:
            return jsonify({'erro': 'Membro não encontrado'}), 404
        membro.pop('senha', None)
        return jsonify(membro), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/equipe/<int:id>', methods=['DELETE'])
def delete_equipe(id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute('DELETE FROM grupo_solucionadores WHERE id_grupo_solucionadores = %s', (id,))
        conn.commit()
        removido = cursor.rowcount
        cursor.close()
        conn.close()
        if not removido:
            return jsonify({'erro': 'Membro não encontrado'}), 404
        return jsonify({'mensagem': 'Membro removido com sucesso'}), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

DOMINIOS_EMAIL_PESSOAL = {
    'aol.com', 'bol.com.br', 'email.com', 'fastmail.com', 'gmail.com',
    'gmx.com', 'googlemail.com', 'hotmail.com', 'hotmail.com.br', 'icloud.com',
    'ig.com.br', 'live.com', 'mail.com', 'me.com', 'msn.com', 'outlook.com',
    'outlook.com.br', 'pm.me', 'proton.me', 'protonmail.com', 'terra.com.br',
    'uol.com.br', 'yahoo.com', 'yahoo.com.br', 'yandex.com', 'zoho.com'
}


def obter_nome_empresa(email):
    dominio = email.rsplit('@', 1)[1].lower()
    nome = re.split(r'[-_]+', dominio.split('.', 1)[0])
    return ' '.join(parte.capitalize() for parte in nome if parte)


def email_corporativo_valido(email):
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
        return False
    dominio = email.rsplit('@', 1)[1].lower()
    return not any(
        dominio == bloqueado or dominio.endswith(f'.{bloqueado}')
        for bloqueado in DOMINIOS_EMAIL_PESSOAL
    )


@app.route('/api/contas', methods=['POST'])
def criar_conta():
    dados = request.get_json() or {}
    empresa = (dados.get('empresa') or '').strip()
    email = (dados.get('email') or '').strip().lower()
    senha = dados.get('senha') or ''

    if not empresa or not email or not senha:
        return jsonify({'erro': 'Empresa, e-mail e senha são obrigatórios'}), 400
    if not email_corporativo_valido(email):
        return jsonify({'erro': 'Use um e-mail corporativo; provedores de e-mail pessoal não são aceitos'}), 400
    if len(senha) < 8:
        return jsonify({'erro': 'A senha deve ter pelo menos 8 caracteres'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'erro': 'Erro ao conectar ao banco'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('SELECT id_grupo_solucionadores FROM grupo_solucionadores WHERE LOWER(email) = %s LIMIT 1', (email,))
        if cursor.fetchone():
            return jsonify({'erro': 'Já existe uma conta cadastrada com este e-mail'}), 409

        nome_empresa = obter_nome_empresa(email)
        cursor.execute('''
            INSERT INTO grupo_solucionadores (descricao, nome, email, cargo, status, senha)
            VALUES (%s, %s, %s, 'Administrador', 'ATIVO', %s)
        ''', (empresa, nome_empresa, email, generate_password_hash(senha)))
        conn.commit()
        return jsonify({
            'id': cursor.lastrowid,
            'nome': nome_empresa,
            'email': email,
            'empresaNome': nome_empresa
        }), 201
    except Error as error:
        conn.rollback()
        print(f'Erro ao criar conta: {error}')
        return jsonify({'erro': 'Não foi possível criar a conta'}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/login', methods=['POST'])
def login():
    dados = request.get_json() or {}
    email = (dados.get('email') or '').strip()
    senha = dados.get('senha') or ''
    if not email or not senha:
        return jsonify({'erro': 'E-mail e senha são obrigatórios'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'erro': 'Erro ao conectar ao banco'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('''
            SELECT id_grupo_solucionadores AS id, nome, email, cargo, status, senha
            FROM grupo_solucionadores
            WHERE LOWER(email) = LOWER(%s)
              AND senha IS NOT NULL
              AND senha <> ''
            ORDER BY id_grupo_solucionadores DESC
        ''', (email,))
        usuarios = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    usuario = next((candidato for candidato in usuarios if (
        candidato['senha'] == senha or check_password_hash(candidato['senha'], senha)
    )), None)
    if not usuario:
        return jsonify({'erro': 'E-mail ou senha inválidos'}), 401
    if usuario['status'] not in (None, 'ATIVO'):
        return jsonify({'erro': 'Esta conta está inativa'}), 403

    return jsonify({
        'id': usuario['id'],
        'nome': usuario['nome'],
        'email': usuario['email'],
        'cargo': usuario['cargo'],
        'empresaNome': obter_nome_empresa(usuario['email'])
    }), 200

@app.route('/api/setores', methods=['GET'])
def get_setores():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute('SELECT id_setor, nome, descricao, niveis FROM setor ORDER BY nome;')
        setores = dict_fetchall(cursor)
        for setor in setores:
            try:
                setor['niveis'] = json.loads(setor.get('niveis') or '[]')
            except (TypeError, json.JSONDecodeError):
                setor['niveis'] = []
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
        descricao = (dados.get('descricao') or '').strip()
        niveis = dados.get('niveis') or []
        if not nome:
            return jsonify({'erro': 'Nome do setor é obrigatório'}), 400
        if not isinstance(niveis, list):
            return jsonify({'erro': 'Os níveis devem ser uma lista'}), 400
        niveis = [f'Nível {indice}' for indice, _ in enumerate(niveis, start=1)]
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute('SELECT id_setor, nome, descricao, niveis FROM setor WHERE LOWER(nome) = LOWER(%s) LIMIT 1;', (nome,))
        setor = dict_fetchone(cursor)
        if not setor:
            cursor.execute('INSERT INTO setor (nome, descricao, niveis) VALUES (%s, %s, %s);', (nome, descricao, json.dumps(niveis, ensure_ascii=False)))
            conn.commit()
            cursor.execute('SELECT id_setor, nome, descricao, niveis FROM setor WHERE id_setor = %s;', (cursor.lastrowid,))
            setor = dict_fetchone(cursor)
        cursor.close()
        conn.close()
        try:
            setor['niveis'] = json.loads(setor.get('niveis') or '[]')
        except (TypeError, json.JSONDecodeError):
            setor['niveis'] = []
        return jsonify(setor), 201
    except Error as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/setores/<int:id>', methods=['DELETE'])
def delete_setor(id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500

        cursor = conn.cursor()
        cursor.execute('UPDATE grupo_solucionadores SET id_setor = NULL, nivel = NULL WHERE id_setor = %s;', (id,))
        cursor.execute('UPDATE chamado SET id_setor = NULL WHERE id_setor = %s;', (id,))
        cursor.execute('DELETE FROM setor WHERE id_setor = %s;', (id,))
        removido = cursor.rowcount
        conn.commit()

        cursor.close()
        conn.close()
        if not removido:
            return jsonify({'erro': 'Setor não encontrado'}), 404
        return jsonify({'mensagem': 'Setor e níveis removidos com sucesso'}), 200
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
        
        periodo = request.args.get('periodo', 'todos')
        filtro_data = ''
        if periodo == 'mes':
            filtro_data = "WHERE strftime('%Y-%m', data_abertura) = strftime('%Y-%m', 'now', 'localtime')"
        elif periodo == 'dia':
            filtro_data = "WHERE date(data_abertura) = date('now', 'localtime')"

        cursor.execute("""
            SELECT UPPER(TRIM(status)) AS status, COUNT(*) AS total
            FROM chamado
            """ + filtro_data + """
            GROUP BY status;
        """)
        chamados_status = dict_fetchall(cursor)

        cursor.execute("""
            SELECT COALESCE(
                NULLIF(TRIM(tc.classificacao), ''),
                NULLIF(TRIM(tc.nome), ''),
                'Sem classificação'
            ) AS classificacao,
            COUNT(*) AS total
            FROM chamado ch
            LEFT JOIN tipo_chamado tc ON tc.id_tipo_chamado = ch.id_tipo_chamado
            """ + filtro_data.replace('data_abertura', 'ch.data_abertura') + """
            GROUP BY 1
            ORDER BY total DESC, classificacao ASC;
        """)
        chamados_classificacao = dict_fetchall(cursor)

        total_chamados = sum(int(item['total']) for item in chamados_status)
        contagens = {}
        for item in chamados_status:
            status = item['status'] or 'SEM STATUS'
            if status == 'EM ANDAMENTO':
                status = 'ANDAMENTO'
            elif status.startswith('AGUARDANDO'):
                status = 'AGUARDANDO'
            contagens[status] = contagens.get(status, 0) + int(item['total'])
        total_resolvidos = contagens.get('RESOLVIDO', 0)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'chamados_por_status': chamados_status,
            'total_chamados': total_chamados,
            'total_resolvidos': total_resolvidos,
            'total_pendentes': total_chamados - total_resolvidos,
            'status': contagens,
            'chamados_por_classificacao': chamados_classificacao
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
            ON CONFLICT(id_configuracao) DO UPDATE SET
                workspace_name = excluded.workspace_name,
                support_email = excluded.support_email""",
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
    initialize_database()
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        Timer(1, lambda: webbrowser.open('http://127.0.0.1:5000/')).start()
    app.run(debug=True, port=5000)