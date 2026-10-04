from flask import Flask, request, jsonify, redirect, send_from_directory, session, g
from werkzeug.security import check_password_hash, generate_password_hash
from flask_cors import CORS
from sqlite3 import Error
import os
import json
import re
import secrets
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from dotenv import load_dotenv
import webbrowser
from threading import Timer

try:
    from .database import DATABASE_PATH, demo_mode_enabled, get_db_connection, initialize_database
    from .pc_explorer_3d import render_pc_explorer, render_pc_svg
except ImportError:
    from database import DATABASE_PATH, demo_mode_enabled, get_db_connection, initialize_database
    from pc_explorer_3d import render_pc_explorer, render_pc_svg

BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, '.env'))
load_dotenv()



app = Flask(__name__)
CORS(app)


def _get_session_secret():
    if os.getenv('FLASK_SECRET_KEY'):
        return os.environ['FLASK_SECRET_KEY']
    secret_path = DATABASE_PATH.parent / '.flask-session-secret'
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with secret_path.open('x', encoding='utf-8') as secret_file:
            secret_file.write(secrets.token_urlsafe(48))
    except FileExistsError:
        pass
    return secret_path.read_text(encoding='utf-8')


app.config.update(
    SECRET_KEY=_get_session_secret(),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.getenv('HELPTI_HTTPS_ONLY', 'false').strip().lower() in ('1', 'true', 'yes', 'on'),
)
app.permanent_session_lifetime = timedelta(days=30)

PERMISSOES_VALIDAS = {
    'dashboard', 'chamados', 'clientes', 'equipe', 'relatorios',
    'educacao', 'configuracoes', 'gerenciar_equipe'
}
PAGINAS_PUBLICAS = {
    'login.html', 'account.html', 'forgot-password.html'
}
PERMISSAO_PAGINA = {
    'dashboard.html': 'dashboard',
    'chamados.html': 'chamados',
    'chamados-detalhe.html': 'chamados',
    'clientes.html': 'clientes',
    'cliente-detalhe.html': 'clientes',
    'equipe.html': 'equipe',
    'equipe-detalhe.html': 'equipe',
    'relatorios.html': 'relatorios',
    'educacao.html': 'educacao',
    'settings.html': 'configuracoes',
}
PERMISSAO_API = {
    '/api/chamados': 'chamados',
    '/api/clientes': 'clientes',
    '/api/equipe': 'equipe',
    '/api/setores': 'equipe',
    '/api/relatorios': 'relatorios',
    '/api/configuracoes': 'configuracoes',
}
PERMISSOES_PADRAO_CARGO = {
    'rh': {'dashboard', 'clientes', 'equipe'},
    'suporte': {'dashboard', 'chamados', 'clientes', 'educacao'},
    'noc': {'dashboard', 'chamados'},
    'técnico': {'dashboard', 'chamados', 'educacao'},
    'tecnico': {'dashboard', 'chamados', 'educacao'},
    'personalizado': {'dashboard'},
}


def _permissoes_do_membro(membro):
    if (membro.get('cargo') or '').strip().lower() == 'administrador':
        return PERMISSOES_VALIDAS.copy()
    try:
        permissoes = json.loads(membro.get('permissoes') or '[]')
    except (TypeError, json.JSONDecodeError):
        permissoes = []
    return {permissao for permissao in permissoes if permissao in PERMISSOES_VALIDAS}


def _normalizar_permissoes(permissoes, cargo):
    if permissoes is None:
        permissoes = PERMISSOES_PADRAO_CARGO.get(
            (cargo or '').strip().lower(), {'dashboard', 'chamados'}
        )
    if not isinstance(permissoes, (list, set, tuple)):
        raise ValueError('As permissões devem ser uma lista.')
    selecionadas = {permissao for permissao in permissoes if permissao in PERMISSOES_VALIDAS}
    if not selecionadas.intersection(PERMISSOES_VALIDAS - {'gerenciar_equipe'}):
        raise ValueError('Selecione pelo menos uma aba para o funcionário.')
    if 'gerenciar_equipe' in selecionadas:
        selecionadas.add('equipe')
    return selecionadas


def _carregar_membro_da_sessao():
    membro_id = session.get('grupo_id')
    if not membro_id:
        return None
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute('''
            SELECT id_grupo_solucionadores, id_usuario, nome, email, cargo, status, permissoes
            FROM grupo_solucionadores
            WHERE id_grupo_solucionadores = %s
        ''', (membro_id,))
        membro = dict_fetchone(cursor)
        cursor.close()
        if membro and not demo_mode_enabled() and str(membro.get('email') or '').lower() in (
            'test@helpiti.com', 'teste@helpiti.com'
        ):
            session.clear()
            return None
        if not membro or membro.get('status') not in (None, 'ATIVO'):
            session.clear()
            return None
        return membro
    finally:
        connection.close()


@app.before_request
def proteger_paginas_e_api():
    caminho = request.path
    if caminho in ('/api/health', '/api/login', '/api/contas'):
        return None

    if caminho.startswith('/frontend/pages/'):
        pagina = os.path.basename(caminho)
        if pagina in PAGINAS_PUBLICAS:
            return None
        permissao = PERMISSAO_PAGINA.get(pagina)
        if not permissao:
            return 'Página não encontrada.', 404
    elif caminho in ('/educacao/pc-explorer', '/educacao/pc-explorer/modelo.svg'):
        permissao = 'educacao'
    elif caminho.startswith('/api/'):
        if caminho == '/api/logout':
            permissao = None
        elif caminho == '/api/sessao':
            permissao = None
        else:
            permissao = next((valor for prefixo, valor in PERMISSAO_API.items()
                              if caminho == prefixo or caminho.startswith(f'{prefixo}/')), None)
            if not permissao:
                return jsonify({'erro': 'Endpoint não encontrado'}), 404
    else:
        return None

    membro = _carregar_membro_da_sessao()
    if not membro:
        if caminho.startswith('/api/'):
            return jsonify({'erro': 'Faça login para continuar.'}), 401
        return redirect('/frontend/pages/login.html')

    g.membro = membro
    permissoes = _permissoes_do_membro(membro)
    leitura_de_apoio_a_chamados = (
        request.method == 'GET'
        and caminho in ('/api/clientes', '/api/equipe', '/api/setores')
        and 'chamados' in permissoes
    )
    if permissao and permissao not in permissoes and not leitura_de_apoio_a_chamados:
        if caminho.startswith('/api/'):
            return jsonify({'erro': 'Seu perfil não tem acesso a este recurso.'}), 403
        return 'Seu perfil não tem acesso a esta página.', 403

    if (caminho.startswith(('/api/equipe', '/api/setores'))
            and request.method != 'GET'
            and 'gerenciar_equipe' not in permissoes):
        return jsonify({'erro': 'Somente o administrador pode gerenciar a equipe.'}), 403
    return None

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))


@app.route('/')
def frontend_entrypoint():
    return redirect('/frontend/pages/login.html')


@app.route('/frontend/<path:filename>')
def frontend_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.route('/educacao/pc-explorer')
def pc_explorer_educacao():
    return render_pc_explorer(
        request.args.get('componente'),
        request.args.get('azimute', 18),
        request.args.get('elevacao', 18),
    )


@app.route('/educacao/pc-explorer/modelo.svg')
def pc_explorer_modelo_svg():
    svg = render_pc_svg(
        request.args.get('componente'),
        request.args.get('azimute', 18),
        request.args.get('elevacao', 18),
    )
    return app.response_class(svg, mimetype='image/svg+xml')


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


def registrar_historico(cursor, id_chamado, evento, descricao):
    cursor.execute(
        'INSERT INTO historico_chamado (id_chamado, evento, descricao) VALUES (%s, %s, %s)',
        (id_chamado, evento, descricao)
    )


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
        if chamado:
            cursor.execute('''
                SELECT evento, descricao, data_evento
                FROM historico_chamado
                WHERE id_chamado = %s
                ORDER BY data_evento, id_historico
            ''', (id,))
            chamado['historico'] = dict_fetchall(cursor)
        
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

        for _ in range(100):
            novo_id = 100000 + secrets.randbelow(900000)
            cursor.execute('SELECT id_chamado FROM chamado WHERE id_chamado = %s', (novo_id,))
            if not cursor.fetchone():
                break
        else:
            return jsonify({'erro': 'Não foi possível gerar um ID disponível para o chamado'}), 503
        
        query = """
            INSERT INTO chamado
                (id_chamado, id_tipo_chamado, id_setor, id_grupo_solucionadores, status, cliente, descricao,
                 email_cliente, telefone_cliente, contato_cliente, telefone_contato)
            VALUES (%s, %s, %s, %s, 'ABERTO', %s, %s, %s, %s, %s, %s);
        """
        cursor.execute(query, (novo_id, id_tipo_chamado, id_setor, id_grupo_solucionadores, cliente, descricao,
                               email_cliente, telefone_cliente, contato_cliente, telefone_contato))
        registrar_historico(cursor, novo_id, 'aberto', 'Chamado criado no sistema.')
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
        evento_historico = None
        descricao_historico = None
        email_enviado = None
        aviso_email = None
        if isinstance(inicio, str):
            inicio = datetime.fromisoformat(inicio)
        agora = datetime.now()

        if acao == 'agendar':
            agendamento = dados.get('data_agendada')
            if not agendamento:
                return jsonify({'erro': 'Informe a data e hora do agendamento'}), 400
            data, hora = agendamento.split('T', 1)
            cursor.execute('UPDATE chamado SET data_agendada = %s, hora_agendada = %s WHERE id_chamado = %s', (data, hora, id))
            evento_historico = 'agendado'
            descricao_historico = f'Atendimento agendado para {data} às {hora}.'
        elif acao == 'atualizar_contato':
            contato = (dados.get('contato_cliente') or '').strip()
            telefone = (dados.get('telefone_contato') or '').strip()
            if not contato:
                return jsonify({'erro': 'Selecione um contato válido'}), 400
            cursor.execute('UPDATE chamado SET contato_cliente = %s, telefone_contato = %s WHERE id_chamado = %s', (contato, telefone, id))
            evento_historico = 'contato_atualizado'
            descricao_historico = f'Contato do chamado alterado para {contato}.'
        elif acao == 'iniciar':
            if status not in ('ABERTO', 'PAUSADO', 'ANDAMENTO'):
                return jsonify({'erro': 'Este chamado não pode ser iniciado'}), 400
            cursor.execute("UPDATE chamado SET status = 'ANDAMENTO', tempo_inicio = COALESCE(tempo_inicio, %s) WHERE id_chamado = %s", (agora, id))
            evento_historico = 'iniciado'
            descricao_historico = 'Atendimento iniciado ou retomado.'
        elif acao == 'pausar':
            if status != 'ANDAMENTO' or not inicio:
                return jsonify({'erro': 'Somente um chamado em andamento pode ser pausado'}), 400
            segundos += max(0, int((agora - inicio).total_seconds()))
            cursor.execute("UPDATE chamado SET status = 'PAUSADO', tempo_inicio = NULL, tempo_decorrido_segundos = %s WHERE id_chamado = %s", (segundos, id))
            evento_historico = 'pausado'
            descricao_historico = f'Atendimento pausado após {segundos // 60:02d}:{segundos % 60:02d} de trabalho.'
        elif acao == 'escalonar':
            id_setor = dados.get('id_setor')
            id_tecnico = dados.get('id_grupo_solucionadores')
            motivo = (dados.get('descricao') or '').strip()
            if status != 'PAUSADO':
                return jsonify({'erro': 'Pause o chamado antes de escaloná-lo'}), 400
            if not id_setor or not id_tecnico or not motivo:
                return jsonify({'erro': 'Informe o setor, o técnico e a descrição do escalonamento'}), 400
            cursor.execute("SELECT nivel, nome FROM grupo_solucionadores WHERE id_grupo_solucionadores = %s AND id_setor = %s AND status = 'ATIVO'", (id_tecnico, id_setor))
            tecnico = cursor.fetchone()
            if not tecnico:
                return jsonify({'erro': 'O técnico selecionado não pertence ao setor informado ou está inativo'}), 400
            cursor.execute('UPDATE chamado SET id_setor = %s, id_grupo_solucionadores = %s WHERE id_chamado = %s', (id_setor, id_tecnico, id))
            cursor.execute('INSERT INTO escalonamento (id_chamado, motivo, nivel, data_escalonamento, id_setor_destino, id_grupo_destino) VALUES (%s, %s, %s, %s, %s, %s)', (id, motivo, tecnico[0], agora.date(), id_setor, id_tecnico))
            cursor.execute('SELECT nome FROM setor WHERE id_setor = %s', (id_setor,))
            setor = cursor.fetchone()
            evento_historico = 'escalonado'
            descricao_historico = f'Escalonado para {setor[0] if setor else "setor"} / {tecnico[1] or "técnico"}. Motivo: {motivo}'
        elif acao == 'encerrar':
            descricao_final = (dados.get('descricao_final') or '').strip()
            if status not in ('ANDAMENTO', 'PAUSADO') or not descricao_final:
                return jsonify({'erro': 'Informe a descrição final após iniciar o atendimento'}), 400
            if inicio:
                segundos += max(0, int((agora - inicio).total_seconds()))
            smtp_host = os.getenv('SMTP_HOST')
            smtp_user = os.getenv('SMTP_USER')
            smtp_password = ''.join((os.getenv('SMTP_PASSWORD') or '').split())
            destinatario = chamado.get('email_cliente')
            if all((smtp_host, smtp_user, smtp_password, destinatario)):
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
                    email_enviado = True
                except (OSError, smtplib.SMTPException, ValueError) as error:
                    email_enviado = False
                    aviso_email = f'Chamado encerrado; o e-mail não foi enviado: {error}'
            else:
                email_enviado = False
                aviso_email = 'Chamado encerrado; SMTP ou e-mail do cliente não está configurado.'
            cursor.execute("UPDATE chamado SET status = 'RESOLVIDO', tempo_inicio = NULL, tempo_decorrido_segundos = %s, descricao_final = %s WHERE id_chamado = %s", (segundos, descricao_final, id))
            evento_historico = 'encerrado'
            descricao_historico = f'Chamado encerrado. Solução: {descricao_final}'
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
            evento_historico = 'status_alterado'
            descricao_historico = f'Status alterado de {status} para {status_novo}.'
        else:
            return jsonify({'erro': 'Ação inválida'}), 400
        if evento_historico:
            registrar_historico(cursor, id, evento_historico, descricao_historico)
        conn.commit()
        
        cursor.execute('SELECT * FROM chamado WHERE id_chamado = %s;', (id,))
        chamado_atualizado = dict_fetchone(cursor)
        cursor.execute('''
            SELECT evento, descricao, data_evento
            FROM historico_chamado
            WHERE id_chamado = %s
            ORDER BY data_evento, id_historico
        ''', (id,))
        chamado_atualizado['historico'] = dict_fetchall(cursor)
        if email_enviado is not None:
            chamado_atualizado['email_enviado'] = email_enviado
            if aviso_email:
                chamado_atualizado['aviso_email'] = aviso_email
        
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
        cursor.execute("SELECT * FROM usuario WHERE tipo_usuario = 'CLIENTE';")
        clientes = dict_fetchall(cursor)

        if clientes:
            ids = [cliente['id_usuario'] for cliente in clientes]
            placeholders = ', '.join(['%s'] * len(ids))
            cursor.execute(f'SELECT id_usuario, nome, email, telefone FROM cliente WHERE id_usuario IN ({placeholders}) ORDER BY id_cliente', ids)
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
        if 'clientes' not in _permissoes_do_membro(g.membro):
            campos_de_apoio = ('id_usuario', 'nome', 'contato', 'email', 'telefone', 'telefone_empresa', 'cnpj', 'contatos')
            clientes = [{campo: cliente.get(campo) for campo in campos_de_apoio} for cliente in clientes]
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
            'INSERT INTO cliente (id_usuario, nome, email, telefone) VALUES (%s, %s, %s, %s)',
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
        cursor.execute(f"UPDATE usuario SET {', '.join(f'{campo} = %s' for campo in campos)} WHERE id_usuario = %s AND tipo_usuario = 'CLIENTE'", valores)
        conn.commit()
        cursor.execute("SELECT * FROM usuario WHERE id_usuario = %s AND tipo_usuario = 'CLIENTE'", (id,))
        cliente = dict_fetchone(cursor)
        cursor.close()
        conn.close()
        if not cliente:
            return jsonify({'erro': 'Cliente não encontrado'}), 404
        return jsonify(cliente), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/clientes/<int:id>/contatos', methods=['POST'])
def create_contato_cliente(id):
    dados = request.get_json() or {}
    contato = {campo: (dados.get(campo) or '').strip() for campo in ('nome', 'email', 'telefone')}
    if any(not valor for valor in contato.values()):
        return jsonify({'erro': 'Nome, e-mail e telefone são obrigatórios'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'erro': 'Erro ao conectar ao banco'}), 500

    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT email, telefone, contato FROM usuario WHERE id_usuario = %s AND tipo_usuario = 'CLIENTE'",
            (id,)
        )
        cliente = cursor.fetchone()
        if not cliente:
            return jsonify({'erro': 'Cliente não encontrado'}), 404

        cursor.execute('SELECT id_cliente FROM cliente WHERE id_usuario = %s LIMIT 1', (id,))
        if not cursor.fetchone() and any(cliente[indice] for indice in range(3)):
            cursor.execute(
                'INSERT INTO cliente (id_usuario, nome, email, telefone) VALUES (%s, %s, %s, %s)',
                (id, cliente[2] or 'Contato', cliente[0] or '', cliente[1] or '')
            )

        cursor.execute(
            'INSERT INTO cliente (id_usuario, nome, email, telefone) VALUES (%s, %s, %s, %s)',
            (id, contato['nome'], contato['email'], contato['telefone'])
        )
        conn.commit()

        cursor.execute(
            'SELECT nome, email, telefone FROM cliente WHERE id_usuario = %s ORDER BY id_cliente',
            (id,)
        )
        return jsonify({'contatos': dict_fetchall(cursor)}), 201
    except Error as error:
        conn.rollback()
        return jsonify({'erro': str(error)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/clientes/<int:id>', methods=['DELETE'])
def delete_cliente(id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usuario WHERE id_usuario = %s AND tipo_usuario = 'CLIENTE'", (id,))
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
            WHERE grupo_solucionadores.id_usuario = %s
            ORDER BY grupo_solucionadores.id_grupo_solucionadores DESC;
        ''', (g.membro['id_usuario'],))
        equipe = dict_fetchall(cursor)
        if 'equipe' not in _permissoes_do_membro(g.membro):
            campos_de_apoio = ('id_grupo_solucionadores', 'nome', 'descricao', 'cargo', 'nivel', 'id_setor', 'setor_nome', 'status')
            equipe = [{campo: membro.get(campo) for campo in campos_de_apoio} for membro in equipe]
        for membro in equipe:
            membro.pop('senha', None)
            try:
                membro['permissoes'] = json.loads(membro.get('permissoes') or '[]')
            except (TypeError, json.JSONDecodeError):
                membro['permissoes'] = []
        
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
        email = (dados.get('email') or '').strip().lower()
        senha = dados.get('senha')
        cargo = dados.get('cargo', 'tecnico')
        if (cargo or '').strip().lower() == 'administrador':
            return jsonify({'erro': 'O cargo Administrador não pode ser criado por este formulário.'}), 400
        try:
            permissoes = _normalizar_permissoes(dados.get('permissoes'), cargo)
        except ValueError as error:
            return jsonify({'erro': str(error)}), 400
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
        cursor.execute('SELECT 1 FROM grupo_solucionadores WHERE LOWER(email) = LOWER(%s)', (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'erro': 'Já existe um funcionário com este e-mail.'}), 409
        cursor.execute(
            """INSERT INTO grupo_solucionadores
            (descricao, nivel, nome, email, cargo, valor_hora, id_setor, data_inicio,
             status, senha, telefone, permissoes, id_usuario)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'ATIVO', %s, %s, %s, %s)""",
            (nome, nivel, nome, email, cargo, valor_hora, id_setor, data_inicio,
             generate_password_hash(senha), telefone, json.dumps(sorted(permissoes)), g.membro['id_usuario'])
        )
        conn.commit()
        novo_id = cursor.lastrowid
        cursor.execute('SELECT * FROM grupo_solucionadores WHERE id_grupo_solucionadores = %s', (novo_id,))
        novo_membro = dict_fetchone(cursor)
        novo_membro.pop('senha', None)
        novo_membro['permissoes'] = sorted(permissoes)
        cursor.close()
        conn.close()
        return jsonify(novo_membro), 201
    except Error as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/equipe/<int:id>', methods=['PUT'])
def update_equipe(id):
    dados = request.get_json() or {}
    if (dados.get('cargo') or '').strip().lower() == 'administrador':
        return jsonify({'erro': 'Funcionários não podem ser promovidos a administrador por esta operação.'}), 400
    campos = {campo: dados[campo] for campo in ('email', 'telefone', 'data_inicio', 'valor_hora', 'cargo', 'id_setor', 'nivel', 'status') if campo in dados}
    try:
        if 'permissoes' in dados:
            campos['permissoes'] = json.dumps(sorted(_normalizar_permissoes(dados['permissoes'], dados.get('cargo'))))
    except ValueError as error:
        return jsonify({'erro': str(error)}), 400
    if not campos:
        return jsonify({'erro': 'Nenhum campo para atualizar'}), 400
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        valores = list(campos.values()) + [id]
        cursor.execute(f"UPDATE grupo_solucionadores SET {', '.join(f'{campo} = %s' for campo in campos)} WHERE id_grupo_solucionadores = %s AND id_usuario = %s", valores + [g.membro['id_usuario']])
        conn.commit()
        cursor.execute('SELECT * FROM grupo_solucionadores WHERE id_grupo_solucionadores = %s AND id_usuario = %s', (id, g.membro['id_usuario']))
        membro = dict_fetchone(cursor)
        cursor.close()
        conn.close()
        if not membro:
            return jsonify({'erro': 'Membro não encontrado'}), 404
        membro.pop('senha', None)
        try:
            membro['permissoes'] = json.loads(membro.get('permissoes') or '[]')
        except (TypeError, json.JSONDecodeError):
            membro['permissoes'] = []
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
        cursor.execute('DELETE FROM grupo_solucionadores WHERE id_grupo_solucionadores = %s AND id_usuario = %s', (id, g.membro['id_usuario']))
        conn.commit()
        removido = cursor.rowcount
        cursor.close()
        conn.close()
        if not removido:
            return jsonify({'erro': 'Membro não encontrado'}), 404
        return jsonify({'mensagem': 'Membro removido com sucesso'}), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

def obter_nome_empresa(email):
    dominio = email.rsplit('@', 1)[1].lower()
    nome = re.split(r'[-_]+', dominio.split('.', 1)[0])
    return ' '.join(parte.capitalize() for parte in nome if parte)


def email_valido(email):
    return bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email))


@app.route('/api/contas', methods=['POST'])
def criar_conta():
    dados = request.get_json() or {}
    nome = (dados.get('nome') or '').strip()
    empresa = (dados.get('empresa') or '').strip() or 'HelpTI'
    email = (dados.get('email') or '').strip().lower()
    senha = dados.get('senha') or ''

    if not email or not senha:
        return jsonify({'erro': 'E-mail e senha são obrigatórios'}), 400
    if not email_valido(email):
        return jsonify({'erro': 'Informe um endereço de e-mail válido'}), 400
    if len(senha) < 8:
        return jsonify({'erro': 'A senha deve ter pelo menos 8 caracteres'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'erro': 'Erro ao conectar ao banco'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        conn.execute('BEGIN IMMEDIATE')
        cursor.execute('SELECT id_grupo_solucionadores FROM grupo_solucionadores WHERE LOWER(email) = %s LIMIT 1', (email,))
        if cursor.fetchone():
            return jsonify({'erro': 'Já existe uma conta cadastrada com este e-mail'}), 409

        cursor.execute("SELECT id_usuario, nome FROM usuario WHERE tipo_usuario = 'WORKSPACE' LIMIT 1")
        if cursor.fetchone():
            return jsonify({
                'erro': 'Este HelpTI já possui uma empresa cadastrada. Peça ao administrador para criar seu acesso.'
            }), 409

        cursor.execute(
            "INSERT INTO usuario (nome, email, status, tipo_usuario) VALUES (%s, %s, 'ATIVO', 'WORKSPACE')",
            (empresa, email)
        )
        workspace_id = cursor.lastrowid
        nome_empresa = empresa

        nome_membro = nome or re.sub(r'[-_.]+', ' ', email.split('@', 1)[0]).title()
        cargo = 'Administrador'
        permissoes = sorted(PERMISSOES_VALIDAS)
        cursor.execute('''
            INSERT INTO grupo_solucionadores
                (descricao, nome, email, cargo, status, senha, id_usuario, permissoes)
            VALUES (%s, %s, %s, %s, 'ATIVO', %s, %s, %s)
        ''', (nome_empresa, nome_membro, email, cargo, generate_password_hash(senha), workspace_id,
              json.dumps(permissoes)))
        membro_id = cursor.lastrowid
        conn.commit()
        session.clear()
        session['grupo_id'] = membro_id
        return jsonify({
            'id': membro_id,
            'nome': nome_membro,
            'email': email,
            'empresaNome': nome_empresa,
            'cargo': cargo,
            'permissoes': permissoes
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
    if not demo_mode_enabled() and email.lower() in ('test@helpiti.com', 'teste@helpiti.com'):
        return jsonify({'erro': 'E-mail ou senha inválidos'}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({'erro': 'Erro ao conectar ao banco'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('''
                        SELECT membro.id_grupo_solucionadores AS id, membro.id_usuario,
                                     membro.nome, membro.email, membro.cargo, membro.status,
                                     membro.senha, membro.permissoes, usuario.nome AS empresa_nome
                        FROM grupo_solucionadores AS membro
                        LEFT JOIN usuario ON usuario.id_usuario = membro.id_usuario
                        WHERE LOWER(membro.email) = LOWER(%s)
                            AND membro.senha IS NOT NULL
                            AND membro.senha <> ''
                        ORDER BY membro.id_grupo_solucionadores DESC
        ''', (email,))
        usuarios = [dict(usuario) for usuario in cursor.fetchall()]
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

    session.clear()
    session['grupo_id'] = usuario['id']
    session.permanent = bool(dados.get('lembrar'))
    permissoes = sorted(_permissoes_do_membro(usuario))
    return jsonify({
        'id': usuario['id'],
        'nome': usuario['nome'],
        'email': usuario['email'],
        'cargo': usuario['cargo'],
        'empresaNome': usuario.get('empresa_nome') or obter_nome_empresa(usuario['email']),
        'permissoes': permissoes
    }), 200


@app.route('/api/sessao', methods=['GET'])
def obter_sessao():
    membro = g.membro
    return jsonify({
        'id': membro['id_grupo_solucionadores'],
        'nome': membro['nome'],
        'email': membro['email'],
        'cargo': membro['cargo'],
        'permissoes': sorted(_permissoes_do_membro(membro))
    }), 200


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'mensagem': 'Sessão encerrada.'}), 200

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
    host = os.environ.get('HELPTI_HOST', '127.0.0.1')
    debug_requested = os.environ.get('HELPTI_DEBUG', 'true').strip().lower() in ('1', 'true', 'yes')
    debug = debug_requested and host in ('127.0.0.1', 'localhost', '::1')
    port = int(os.environ.get('HELPTI_PORT', '5000'))
    if debug and os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        Timer(1, lambda: webbrowser.open('http://127.0.0.1:5000/')).start()
    app.run(host=host, debug=debug, port=port)