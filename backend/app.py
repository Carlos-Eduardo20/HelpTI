from flask import Flask, request, jsonify, redirect, send_from_directory, session, g
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
import os
import json
import base64
import re
import secrets
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit
import webbrowser
from threading import Lock, Timer


try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

try:
    import requests
except ImportError:
    class _RequestsAusente:
        class RequestException(Exception):
            pass

    requests = _RequestsAusente()

try:
    from .database import (DEMO_EMAIL, Error, INSTANCE_DIR, SCHEMA_VERSION, apply_demo_seed,
                           database_settings, demo_mode_enabled, get_db_connection,
                           initialize_database)
    from .pc_explorer_3d import DIAGNOSTICOS, render_pc_explorer, render_pc_svg
    from .security_check import run_security_checks
except ImportError:
    from database import (DEMO_EMAIL, Error, INSTANCE_DIR, SCHEMA_VERSION, apply_demo_seed,
                          database_settings, demo_mode_enabled, get_db_connection,
                          initialize_database)
    from pc_explorer_3d import DIAGNOSTICOS, render_pc_explorer, render_pc_svg
    from security_check import run_security_checks

BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, '.env'))
load_dotenv()


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)


def _get_session_secret():
    if os.getenv('FLASK_SECRET_KEY'):
        return os.environ['FLASK_SECRET_KEY']
    secret_path = INSTANCE_DIR / '.flask-session-secret'
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


def _same_origin(value):
    try:
        provided = urlsplit(value)
        expected = urlsplit(request.host_url)
        provided_port = provided.port or (443 if provided.scheme.lower() == 'https' else 80)
        expected_port = expected.port or (443 if expected.scheme.lower() == 'https' else 80)
    except ValueError:
        return False
    return (
        provided.scheme.lower() in {'http', 'https'}
        and provided.hostname is not None
        and provided.username is None
        and provided.password is None
        and provided.scheme.lower() == expected.scheme.lower()
        and provided.hostname.lower() == (expected.hostname or '').lower()
        and provided_port == expected_port
    )


def _registrar_tentativa_login():
    client = request.remote_addr or 'unknown'
    now = datetime.now().timestamp()
    with _LOGIN_RATE_LIMIT_LOCK:
        expired = [
            address for address, (started, _attempts) in _LOGIN_RATE_LIMIT.items()
            if now - started >= 15 * 60
        ]
        for address in expired:
            del _LOGIN_RATE_LIMIT[address]
        started, attempts = _LOGIN_RATE_LIMIT.get(client, (now, 0))
        if attempts >= 10:
            return False
        _LOGIN_RATE_LIMIT[client] = (started, attempts + 1)
        return True


_LOGIN_RATE_LIMIT = {}
_LOGIN_RATE_LIMIT_LOCK = Lock()


@app.before_request
def reject_cross_site_mutations():
    if request.method in {'GET', 'HEAD', 'OPTIONS'}:
        return None
    if request.headers.get('Sec-Fetch-Site', '').lower() == 'cross-site':
        return jsonify({'erro': 'Requisição entre sites não permitida.'}), 403
    origin = request.headers.get('Origin') or request.headers.get('Referer')
    if origin and not _same_origin(origin):
        return jsonify({'erro': 'Origem da requisição não permitida.'}), 403
    return None


@app.after_request
def set_security_headers(response):
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    if request.path.startswith('/educacao/pc-explorer'):
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault(
        'Permissions-Policy', 'camera=(), microphone=(), geolocation=()'
    )
    return response


PERMISSOES_VALIDAS = {
    'dashboard', 'chamados', 'clientes', 'equipe', 'relatorios',
    'educacao', 'configuracoes', 'gerenciar_equipe'
}
PAGINAS_PUBLICAS = {
    'login.html', 'account.html'
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
    '/api/educacao': 'educacao',
    '/api/chamados': 'chamados',
    '/api/documentacoes': 'chamados',
    '/api/clientes': 'clientes',
    '/api/equipe': 'equipe',
    '/api/setores': 'equipe',
    '/api/relatorios': 'relatorios',
    '/api/configuracoes': 'configuracoes',
    '/api/admin': 'configuracoes',
}
PERMISSOES_PADRAO_CARGO = {
    'rh': {'dashboard', 'clientes', 'equipe'},
    'suporte': {'dashboard', 'chamados', 'clientes', 'educacao'},
    'noc': {'dashboard', 'chamados'},
    'técnico': {'dashboard', 'chamados', 'educacao'},
    'tecnico': {'dashboard', 'chamados', 'educacao'},
    'cliente': {'chamados'},
    'personalizado': {'dashboard'},
}


def _e_cliente():
    """Verifica se o membro atual autenticado possui perfil de cliente."""
    if not hasattr(g, 'membro') or not g.membro:
        return False
    cargo = (g.membro.get('cargo') or '').strip().lower()
    return cargo == 'cliente'


def _permissoes_do_membro(membro):
    cargo = (membro.get('cargo') or '').strip().lower()
    if cargo == 'administrador':
        return PERMISSOES_VALIDAS.copy()
    if cargo == 'cliente':
        return {'chamados'}
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
            SELECT membro.id_grupo_solucionadores, membro.id_usuario, membro.nome,
                   membro.email, membro.cargo, membro.status, membro.permissoes,
                   membro.foto_perfil,
                   usuario.nome AS empresa_nome
            FROM grupo_solucionadores AS membro
            LEFT JOIN usuario ON usuario.id_usuario = membro.id_usuario
            WHERE membro.id_grupo_solucionadores = %s
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
    if caminho in (
        '/api/health', '/api/login', '/api/contas'
    ):
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
    return redirect('/frontend/planos.html')


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


@app.route('/api/educacao/diagnosticos')
def obter_diagnosticos_educacao():
    return jsonify(DIAGNOSTICOS)


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


def registrar_historico(cursor, id_chamado, evento, descricao, autor=None):
    if not autor:
        if hasattr(g, 'membro') and g.membro:
            autor = g.membro.get('nome') or 'Atendente'
        else:
            autor = session.get('usuario') or 'Sistema'
    cursor.execute(
        'INSERT INTO historico_chamado (id_chamado, evento, descricao, autor) VALUES (%s, %s, %s, %s)',
        (id_chamado, evento, descricao, autor)
    )


def provedor_email():
    return os.getenv('EMAIL_PROVIDER', 'smtp').strip().lower() or 'smtp'


def zoho_mail_api_configurado():
    return all(os.getenv(chave, '').strip() for chave in (
        'ZOHO_ACCOUNTS_BASE_URL',
        'ZOHO_MAIL_API_BASE_URL',
        'ZOHO_MAIL_ACCOUNT_ID',
        'ZOHO_MAIL_FROM_ADDRESS',
        'ZOHO_CLIENT_ID',
        'ZOHO_CLIENT_SECRET',
        'ZOHO_REFRESH_TOKEN',
    ))


def enviar_email_zoho_api(destinatario, assunto, conteudo):
    contas_base = os.getenv('ZOHO_ACCOUNTS_BASE_URL', '').strip().rstrip('/')
    mail_base = os.getenv('ZOHO_MAIL_API_BASE_URL', '').strip().rstrip('/')
    account_id = os.getenv('ZOHO_MAIL_ACCOUNT_ID', '').strip()
    remetente = os.getenv('ZOHO_MAIL_FROM_ADDRESS', '').strip()
    if not all((destinatario, contas_base, mail_base, account_id, remetente)):
        return False, 'A configuração da API do Zoho Mail está incompleta.'

    if any(urlsplit(url).scheme != 'https' or not urlsplit(url).netloc for url in (contas_base, mail_base)):
        return False, 'As URLs da API do Zoho precisam usar HTTPS.'

    try:
        token_response = requests.post(
            f'{contas_base}/oauth/v2/token',
            data={
                'refresh_token': os.getenv('ZOHO_REFRESH_TOKEN', '').strip(),
                'client_id': os.getenv('ZOHO_CLIENT_ID', '').strip(),
                'client_secret': os.getenv('ZOHO_CLIENT_SECRET', '').strip(),
                'grant_type': 'refresh_token',
            },
            timeout=15,
        )
        if not token_response.ok:
            return False, f'O Zoho não autorizou o envio (HTTP {token_response.status_code}).'
        token_payload = token_response.json()
        access_token = token_payload.get('access_token') if isinstance(token_payload, dict) else None
        if not isinstance(access_token, str) or not access_token:
            return False, 'O Zoho não retornou um token de acesso válido.'

        mail_response = requests.post(
            f'{mail_base}/api/accounts/{account_id}/messages',
            headers={
                'Authorization': f'Zoho-oauthtoken {access_token}',
                'Accept': 'application/json',
            },
            json={
                'fromAddress': remetente,
                'toAddress': destinatario,
                'subject': assunto,
                'content': conteudo,
                'mailFormat': 'plaintext',
            },
            timeout=20,
        )
        if not mail_response.ok:
            return False, f'A API de e-mail do Zoho respondeu HTTP {mail_response.status_code}.'
        resultado = mail_response.json()
        status = (resultado.get('status') or {}) if isinstance(resultado, dict) else {}
        if status.get('code') not in (200, '200'):
            return False, 'O Zoho recusou o envio do e-mail. Confira o remetente e as permissões OAuth.'
        return True, None
    except (requests.RequestException, ValueError) as error:
        app.logger.warning('Falha na API de e-mail do Zoho: %s', error)
        return False, 'Não foi possível conectar à API de e-mail do Zoho.'


def enviar_email(destinatario, assunto, conteudo):
    if not destinatario:
        return False, 'Informe o e-mail de destino.'

    provedor = provedor_email()
    if provedor == 'zoho_api':
        if not zoho_mail_api_configurado():
            return False, 'Configure as credenciais da API do Zoho nas variáveis de ambiente.'
        return enviar_email_zoho_api(destinatario, assunto, conteudo)
    if provedor != 'smtp':
        return False, 'EMAIL_PROVIDER deve ser smtp ou zoho_api.'

    smtp_host = os.getenv('SMTP_HOST', 'smtp.zoho.com').strip() or 'smtp.zoho.com'
    smtp_user = os.getenv('SMTP_USER', 'carlos.morais@helpiti.com.br').strip() or 'carlos.morais@helpiti.com.br'
    smtp_password = ''.join((os.getenv('SMTP_PASSWORD') or '').split())
    if not smtp_password:
        return False, 'O envio de e-mail não está configurado. Configure o provedor nas variáveis de ambiente.'

    mensagem = EmailMessage()
    mensagem['Subject'] = assunto
    mensagem['From'] = os.getenv('SMTP_FROM', 'carlos.morais@helpiti.com.br').strip() or 'carlos.morais@helpiti.com.br'
    mensagem['To'] = destinatario
    mensagem.set_content(conteudo)
    try:
        porta = int(os.getenv('SMTP_PORT', '465'))
        if porta == 465:
            servidor_smtp = smtplib.SMTP_SSL(smtp_host, porta, timeout=15)
        else:
            servidor_smtp = smtplib.SMTP(smtp_host, porta, timeout=15)
        with servidor_smtp as servidor:
            if porta != 465:
                servidor.starttls()
            servidor.login(smtp_user, smtp_password)
            servidor.send_message(mensagem)
        return True, None
    except (OSError, smtplib.SMTPException, ValueError) as error:
        return False, f'O e-mail não foi enviado: {error}'


DOMINIOS_EMAIL_BLOQUEADOS = {
    'gmail.com', 'googlemail.com',
    'mailinator.com', 'tempmail.com', 'temp-mail.org', 'yopmail.com',
    'teste.com', 'test.com', 'example.com', 'example.org', 'example.net',
    'dispostable.com', 'trashmail.com', 'guerrillamail.com', '10minutemail.com',
    'sharklasers.com', 'getnada.com', 'maildrop.cc', 'throwawaymail.com',
}


def dominio_email_bloqueado(email):
    dominio = email.rsplit('@', 1)[-1].strip().lower().rstrip('.')
    if dominio.startswith('yahoo.') or dominio in DOMINIOS_EMAIL_BLOQUEADOS:
        return True
    # Cobre subdomínios, ex.: foo.mailinator.com
    return any(dominio.endswith('.' + bloqueado) for bloqueado in DOMINIOS_EMAIL_BLOQUEADOS)


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

def _ws():
    """Id of the active workspace (company) for the authenticated session."""
    return g.membro['id_usuario']


# ============ ROTAS DE CHAMADOS ============

# Rota para listar todos os chamados
@app.route('/api/chamados', methods=['GET'])
def get_chamados():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()
        workspace_id = _ws()
        if _e_cliente():
            email_cliente = (g.membro.get('email') or '').strip()
            nome_cliente = (g.membro.get('nome') or '').strip()
            cursor.execute('''
                SELECT chamado.*, 
                       COALESCE(chamado.setor, 'Geral') AS setor_nome,
                       grupo_solucionadores.nome AS tecnico
                FROM chamado
                LEFT JOIN grupo_solucionadores ON grupo_solucionadores.id_grupo_solucionadores = chamado.id_grupo_solucionadores
                WHERE chamado.id_usuario = %s
                  AND (LOWER(chamado.email_cliente) = LOWER(%s) OR LOWER(chamado.cliente) = LOWER(%s))
                ORDER BY chamado.id_chamado DESC;
            ''', (workspace_id, email_cliente, nome_cliente))
        else:
            cursor.execute('''
                SELECT chamado.*, 
                       COALESCE(chamado.setor, 'Geral') AS setor_nome,
                       grupo_solucionadores.nome AS tecnico
                FROM chamado
                LEFT JOIN grupo_solucionadores ON grupo_solucionadores.id_grupo_solucionadores = chamado.id_grupo_solucionadores
                WHERE chamado.id_usuario = %s
                ORDER BY chamado.id_chamado DESC;
            ''', (workspace_id,))
        chamados = dict_fetchall(cursor)
        
        cursor.close()
        conn.close()
        return jsonify(chamados), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

# Rota para buscar métricas estilo DeskOps
@app.route('/api/chamados/metricas', methods=['GET'])
def get_metricas_deskops():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()
        workspace_id = _ws()
        
        filtro_usuario = 'WHERE ch.id_usuario = %s'
        params = [workspace_id]
        if _e_cliente():
            filtro_usuario += ' AND (LOWER(ch.email_cliente) = LOWER(%s) OR LOWER(ch.cliente) = LOWER(%s))'
            params.extend([(g.membro.get('email') or '').strip(), (g.membro.get('nome') or '').strip()])

        cursor.execute(f'''
            SELECT 
                COUNT(*) AS total,
                SUM(CASE WHEN UPPER(ch.status) = 'ABERTO' THEN 1 ELSE 0 END) AS triagem,
                SUM(CASE WHEN UPPER(ch.status) = 'ANDAMENTO' THEN 1 ELSE 0 END) AS em_andamento,
                SUM(CASE WHEN UPPER(ch.status) = 'PAUSADO' THEN 1 ELSE 0 END) AS pausados,
                SUM(CASE WHEN UPPER(ch.status) = 'RESOLVIDO' THEN 1 ELSE 0 END) AS resolvidos,
                SUM(CASE WHEN UPPER(ch.status) = 'RESOLVIDO' 
                         AND DATE(COALESCE(ch.data_fechamento, ch.data_abertura)) = DATE('now', 'localtime')
                         THEN 1 ELSE 0 END) AS resolvidos_hoje,
                AVG(CASE WHEN UPPER(ch.status) = 'RESOLVIDO' AND ch.tempo_decorrido_segundos > 0 
                         THEN ch.tempo_decorrido_segundos ELSE NULL END) AS mttr_segundos_medio
            FROM chamado ch
            {filtro_usuario}
        ''', tuple(params))
        resumo = dict_fetchone(cursor) or {}
        
        total = int(resumo.get('total') or 0)
        triagem = int(resumo.get('triagem') or 0)
        em_andamento = int(resumo.get('em_andamento') or 0)
        pausados = int(resumo.get('pausados') or 0)
        resolvidos = int(resumo.get('resolvidos') or 0)
        resolvidos_hoje = int(resumo.get('resolvidos_hoje') or 0)
        mttr_segundos = float(resumo.get('mttr_segundos_medio') or 0)

        mttr_minutos = int(mttr_segundos // 60)
        if mttr_minutos >= 60:
            horas = mttr_minutos // 60
            mins = mttr_minutos % 60
            mttr_formatado = f'{horas}h {mins:02d}m' if mins > 0 else f'{horas}h'
        elif mttr_minutos > 0:
            mttr_formatado = f'{mttr_minutos}m'
        else:
            mttr_formatado = '45m' if resolvidos > 0 else '0m'

        cursor.close()
        conn.close()

        return jsonify({
            'total': total,
            'triagem': triagem,
            'em_andamento': em_andamento,
            'pausados': pausados,
            'resolvidos': resolvidos,
            'resolvidos_hoje': resolvidos_hoje,
            'mttr_minutos': mttr_minutos,
            'mttr_formatado': mttr_formatado
        }), 200
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
        workspace_id = _ws()
        cursor.execute('''
            SELECT chamado.*, 
                   COALESCE(chamado.setor, 'Geral') AS setor_nome,
                   grupo_solucionadores.nome AS tecnico
            FROM chamado
            LEFT JOIN grupo_solucionadores ON grupo_solucionadores.id_grupo_solucionadores = chamado.id_grupo_solucionadores
            WHERE chamado.id_chamado = %s AND chamado.id_usuario = %s;
        ''', (id, workspace_id))
        chamado = dict_fetchone(cursor)
        if not chamado:
            cursor.close()
            conn.close()
            return jsonify({'erro': 'Chamado não encontrado'}), 404

        if _e_cliente():
            email_cliente = (g.membro.get('email') or '').strip().lower()
            nome_cliente = (g.membro.get('nome') or '').strip().lower()
            chamado_email = (chamado.get('email_cliente') or '').strip().lower()
            chamado_cli = (chamado.get('cliente') or '').strip().lower()
            if email_cliente != chamado_email and nome_cliente != chamado_cli:
                cursor.close()
                conn.close()
                return jsonify({'erro': 'Você não tem permissão para visualizar este chamado'}), 403

        cursor.execute('''
            SELECT evento, descricao, autor, data_evento
            FROM historico_chamado
            WHERE id_chamado = %s
            ORDER BY data_evento, id_historico
        ''', (id,))
        chamado['historico'] = dict_fetchall(cursor)
        
        cursor.close()
        conn.close()
        return jsonify(chamado), 200
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
        setor_nome = (dados.get('setor') or '').strip()
        id_grupo_solucionadores = dados.get('id_grupo_solucionadores')
        id_tipo_chamado = dados.get('id_tipo_chamado', 1)

        if not cliente or not email_cliente or not telefone_cliente or not contato_cliente or not telefone_contato or not descricao or not setor_nome or not id_grupo_solucionadores:
            return jsonify({'erro': 'Todos os campos do chamado são obrigatórios'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id_grupo_solucionadores, setor
            FROM grupo_solucionadores
            WHERE id_grupo_solucionadores = %s AND LOWER(TRIM(setor)) = LOWER(%s)
              AND status = 'ATIVO'
              AND id_usuario = %s
        ''', (id_grupo_solucionadores, setor_nome, _ws()))
        tecnico = cursor.fetchone()
        if not tecnico:
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
                (id_chamado, id_tipo_chamado, setor, id_grupo_solucionadores, status, cliente, descricao,
                 email_cliente, telefone_cliente, contato_cliente, telefone_contato, id_usuario)
            VALUES (%s, %s, %s, %s, 'ABERTO', %s, %s, %s, %s, %s, %s, %s);
        """
        cursor.execute(query, (novo_id, id_tipo_chamado, setor_nome, id_grupo_solucionadores,
                               cliente, descricao, email_cliente, telefone_cliente, contato_cliente, telefone_contato, _ws()))
        
        autor_chamado = g.membro.get('nome') if (hasattr(g, 'membro') and g.membro) else 'Sistema'
        registrar_historico(cursor, novo_id, 'aberto', 'Chamado criado no sistema.', autor=autor_chamado)
        conn.commit()

        cursor.execute('SELECT * FROM chamado WHERE id_chamado = %s;', (novo_id,))
        novo_chamado = dict_fetchone(cursor)
        
        cursor.close()
        conn.close()
        email_enviado, aviso_email = enviar_email(
            email_cliente,
            f'Chamado #{novo_id} recebido',
            f"Olá, {contato_cliente}.\n\n"
            f"Recebemos seu chamado #{novo_id} para {cliente}.\n"
            f"Descrição: {descricao}\n\n"
            'A equipe de suporte dará continuidade ao atendimento.'
        )
        novo_chamado['email_enviado'] = email_enviado
        if aviso_email:
            novo_chamado['aviso_email'] = aviso_email
        return jsonify(novo_chamado), 201
    except Error as e:
        return jsonify({'erro': str(e)}), 500

# Rota para atualizar um chamado
@app.route('/api/chamados/<int:id>', methods=['PUT'])
def update_chamado(id):
    try:
        dados = request.get_json() or {}
        acao = dados.get('acao')

        # Regra de permissão: somente atendente autorizado altera status de atendimento ou encerra chamado
        if _e_cliente():
            if acao in ('iniciar', 'pausar', 'escalonar', 'encerrar', 'agendar') or 'status' in dados:
                return jsonify({'erro': 'Somente atendentes autorizados podem alterar o status ou fluxo de atendimento do chamado'}), 403

        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()
        
        conn.execute('BEGIN IMMEDIATE')
        cursor.execute('SELECT * FROM chamado WHERE id_chamado = %s AND id_usuario = %s', (id, _ws()))
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
        autor_atual = g.membro.get('nome') if (hasattr(g, 'membro') and g.membro) else 'Atendente'

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
            setor_destino_nome = (dados.get('setor_destino') or '').strip()
            id_tecnico = dados.get('id_grupo_solucionadores')
            motivo = (dados.get('descricao') or '').strip()
            if status != 'PAUSADO':
                return jsonify({'erro': 'Pause o chamado antes de escaloná-lo'}), 400
            if not setor_destino_nome or not id_tecnico or not motivo:
                return jsonify({'erro': 'Informe o setor, o técnico e a descrição do escalonamento'}), 400
            cursor.execute('''
                SELECT nivel, nome, setor FROM grupo_solucionadores
                WHERE id_grupo_solucionadores = %s
                  AND LOWER(TRIM(setor)) = LOWER(%s)
                  AND status = 'ATIVO' AND id_usuario = %s
            ''', (id_tecnico, setor_destino_nome, _ws()))
            tecnico = cursor.fetchone()
            if not tecnico:
                return jsonify({'erro': 'O técnico selecionado não pertence ao setor informado ou está inativo'}), 400
            cursor.execute(
                'UPDATE chamado SET setor = %s, id_grupo_solucionadores = %s '
                'WHERE id_chamado = %s',
                (tecnico['setor'], id_tecnico, id),
            )
            cursor.execute('''
                INSERT INTO escalonamento
                    (id_chamado, motivo, nivel, data_escalonamento, setor_destino, id_grupo_destino)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (id, motivo, tecnico['nivel'], agora.date(), tecnico['setor'], id_tecnico))
            evento_historico = 'escalonado'
            descricao_historico = f'Escalonado para {tecnico["setor"] or "setor"} / {tecnico["nome"] or "técnico"}. Motivo: {motivo}'
        elif acao == 'encerrar':
            descricao_final = (dados.get('descricao_final') or '').strip()
            if status not in ('ANDAMENTO', 'PAUSADO') or not descricao_final:
                return jsonify({'erro': 'Informe a descrição final após iniciar o atendimento'}), 400
            if inicio:
                segundos += max(0, int((agora - inicio).total_seconds()))
            destinatario = chamado.get('email_cliente')
            email_enviado, aviso_email = enviar_email(
                destinatario,
                f'Chamado #{id} resolvido',
                f"Olá, {chamado.get('cliente') or 'cliente'}.\n\n"
                f"O chamado #{id} foi resolvido.\n"
                f"Tempo de atendimento: {segundos // 60} min.\n\n"
                f"Descrição inicial:\n{chamado.get('descricao') or 'Não informada'}\n\n"
                f'Solução aplicada:\n{descricao_final}'
            )
            data_fechamento_str = agora.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("UPDATE chamado SET status = 'RESOLVIDO', data_fechamento = %s, tempo_inicio = NULL, tempo_decorrido_segundos = %s, descricao_final = %s WHERE id_chamado = %s", (data_fechamento_str, segundos, descricao_final, id))
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
            registrar_historico(cursor, id, evento_historico, descricao_historico, autor=autor_atual)
        conn.commit()
        
        cursor.execute('SELECT * FROM chamado WHERE id_chamado = %s;', (id,))
        chamado_atualizado = dict_fetchone(cursor)
        cursor.execute('''
            SELECT evento, descricao, autor, data_evento
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
        cursor.execute('SELECT 1 FROM chamado WHERE id_chamado = %s AND id_usuario = %s;', (id, _ws()))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'erro': 'Chamado não encontrado'}), 404
        cursor.execute('DELETE FROM escalonamento WHERE id_chamado = %s;', (id,))
        cursor.execute('DELETE FROM chamado WHERE id_chamado = %s AND id_usuario = %s;', (id, _ws()))
        removido = cursor.rowcount
        conn.commit()

        cursor.close()
        conn.close()
        if not removido:
            return jsonify({'erro': 'Chamado não encontrado'}), 404
        return jsonify({'mensagem': 'Chamado encerrado e removido com sucesso'}), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

# ============ ROTAS DE DOCUMENTAÇÃO TÉCNICA (MODELAGEM ERD) ============

@app.route('/api/documentacoes', methods=['GET'])
def get_documentacoes():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        
        busca = (request.args.get('busca') or '').strip()
        filtro_fornecedor = (request.args.get('fornecedor') or '').strip()
        grupo_id = request.args.get('id_grupo_solucionadores')

        query = '''
            SELECT doc.*, gs.nome AS solucionador_nome, gs.cargo AS solucionador_cargo
            FROM documentacao doc
            LEFT JOIN grupo_solucionadores gs ON gs.id_grupo_solucionadores = doc.id_grupo_solucionadores
            WHERE doc.id_usuario = %s
        '''
        params = [_ws()]
        if busca:
            query += ' AND (LOWER(doc.titulo) LIKE %s OR LOWER(doc.conteudo) LIKE %s OR LOWER(doc.fornecedor) LIKE %s)'
            like_val = f'%{busca.lower()}%'
            params.extend([like_val, like_val, like_val])
        if filtro_fornecedor:
            query += ' AND LOWER(doc.fornecedor) = LOWER(%s)'
            params.append(filtro_fornecedor)
        if grupo_id:
            query += ' AND doc.id_grupo_solucionadores = %s'
            params.append(grupo_id)
        
        query += ' ORDER BY doc.data_atualizacao DESC, doc.id_documentacao DESC;'
        cursor.execute(query, tuple(params))
        documentos = dict_fetchall(cursor)
        cursor.close()
        conn.close()
        return jsonify(documentos), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/documentacoes/<int:id>', methods=['GET'])
def get_documentacao(id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute('''
            SELECT doc.*, gs.nome AS solucionador_nome, gs.cargo AS solucionador_cargo
            FROM documentacao doc
            LEFT JOIN grupo_solucionadores gs ON gs.id_grupo_solucionadores = doc.id_grupo_solucionadores
            WHERE doc.id_documentacao = %s AND doc.id_usuario = %s
        ''', (id, _ws()))
        documento = dict_fetchone(cursor)
        cursor.close()
        conn.close()
        if not documento:
            return jsonify({'erro': 'Documentação não encontrada'}), 404
        return jsonify(documento), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/documentacoes', methods=['POST'])
def create_documentacao():
    try:
        dados = request.get_json() or {}
        titulo = (dados.get('titulo') or '').strip()
        conteudo = (dados.get('conteudo') or '').strip()
        fornecedor = (dados.get('fornecedor') or '').strip()
        id_grupo = dados.get('id_grupo_solucionadores')
        if not id_grupo and hasattr(g, 'membro') and g.membro:
            id_grupo = g.membro.get('id_grupo_solucionadores')

        if not titulo or not conteudo:
            return jsonify({'erro': 'Título e conteúdo são obrigatórios'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO documentacao (fornecedor, id_grupo_solucionadores, titulo, conteudo, id_usuario)
            VALUES (%s, %s, %s, %s, %s)
        ''', (fornecedor, id_grupo, titulo, conteudo, _ws()))
        doc_id = cursor.lastrowid
        conn.commit()
        
        cursor.execute('SELECT * FROM documentacao WHERE id_documentacao = %s', (doc_id,))
        novo_doc = dict_fetchone(cursor)
        cursor.close()
        conn.close()
        return jsonify(novo_doc), 201
    except Error as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/documentacoes/<int:id>', methods=['PUT'])
def update_documentacao(id):
    try:
        dados = request.get_json() or {}
        titulo = (dados.get('titulo') or '').strip()
        conteudo = (dados.get('conteudo') or '').strip()
        fornecedor = (dados.get('fornecedor') or '').strip()
        id_grupo = dados.get('id_grupo_solucionadores')
        if not titulo or not conteudo:
            return jsonify({'erro': 'Título e conteúdo são obrigatórios'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE documentacao
            SET titulo = %s, conteudo = %s, fornecedor = %s, 
                id_grupo_solucionadores = COALESCE(%s, id_grupo_solucionadores),
                data_atualizacao = CURRENT_TIMESTAMP
            WHERE id_documentacao = %s AND id_usuario = %s
        ''', (titulo, conteudo, fornecedor, id_grupo, id, _ws()))
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'erro': 'Documentação não encontrada'}), 404
        conn.commit()

        cursor.execute('SELECT * FROM documentacao WHERE id_documentacao = %s', (id,))
        doc_atualizado = dict_fetchone(cursor)
        cursor.close()
        conn.close()
        return jsonify(doc_atualizado), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/documentacoes/<int:id>', methods=['DELETE'])
def delete_documentacao(id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute('DELETE FROM documentacao WHERE id_documentacao = %s AND id_usuario = %s', (id, _ws()))
        removido = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        if not removido:
            return jsonify({'erro': 'Documentação não encontrada'}), 404
        return jsonify({'mensagem': 'Documentação removida com sucesso'}), 200
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
        cursor.execute("SELECT * FROM usuario WHERE tipo_usuario = 'CLIENTE' AND id_workspace = %s;", (_ws(),))
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
            INSERT INTO usuario (nome, cnpj, telefone_empresa, endereco, email, telefone, contato, status, id_workspace)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'ATIVO', %s);
        """
        cnpj = (dados.get('cnpj') or '').strip() or None
        telefone_empresa = (dados.get('telefone_empresa') or '').strip() or None
        endereco = (dados.get('endereco') or '').strip() or None
        cursor.execute(query, (nome, cnpj, telefone_empresa, endereco, primeiro_contato['email'], primeiro_contato['telefone'], primeiro_contato['nome'], _ws()))
        novo_id = cursor.lastrowid
        cursor.executemany(
            'INSERT INTO cliente (id_usuario, nome, email, telefone, id_workspace) VALUES (%s, %s, %s, %s, %s)',
            [(novo_id, contato['nome'], contato['email'], contato['telefone'], _ws()) for contato in contatos]
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
        valores = list(campos.values()) + [id, _ws()]
        cursor.execute(f"UPDATE usuario SET {', '.join(f'{campo} = %s' for campo in campos)} WHERE id_usuario = %s AND tipo_usuario = 'CLIENTE' AND id_workspace = %s", valores)
        conn.commit()
        cursor.execute("SELECT * FROM usuario WHERE id_usuario = %s AND tipo_usuario = 'CLIENTE' AND id_workspace = %s", (id, _ws()))
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
            "SELECT email, telefone, contato FROM usuario WHERE id_usuario = %s AND tipo_usuario = 'CLIENTE' AND id_workspace = %s",
            (id, _ws())
        )
        cliente = cursor.fetchone()
        if not cliente:
            return jsonify({'erro': 'Cliente não encontrado'}), 404

        cursor.execute('SELECT id_cliente FROM cliente WHERE id_usuario = %s LIMIT 1', (id,))
        if not cursor.fetchone() and any(cliente[indice] for indice in range(3)):
            cursor.execute(
                'INSERT INTO cliente (id_usuario, nome, email, telefone, id_workspace) VALUES (%s, %s, %s, %s, %s)',
                (id, cliente[2] or 'Contato', cliente[0] or '', cliente[1] or '', _ws())
            )

        cursor.execute(
            'INSERT INTO cliente (id_usuario, nome, email, telefone, id_workspace) VALUES (%s, %s, %s, %s, %s)',
            (id, contato['nome'], contato['email'], contato['telefone'], _ws())
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
        cursor.execute("DELETE FROM usuario WHERE id_usuario = %s AND tipo_usuario = 'CLIENTE' AND id_workspace = %s", (id, _ws()))
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
            SELECT grupo_solucionadores.*
            FROM grupo_solucionadores
            WHERE grupo_solucionadores.id_usuario = %s
            ORDER BY grupo_solucionadores.id_grupo_solucionadores DESC;
        ''', (g.membro['id_usuario'],))
        equipe = dict_fetchall(cursor)
        if 'equipe' not in _permissoes_do_membro(g.membro):
            campos_de_apoio = ('id_grupo_solucionadores', 'nome', 'descricao', 'cargo', 'nivel', 'setor', 'status')
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
        nome = (dados.get('nome') or '').strip()
        email = (dados.get('email') or '').strip().lower()
        cargo = 'Técnico'
        nivel = dados.get('nivel') or None
        valor_hora = dados.get('valor_hora') or None
        telefone = dados.get('telefone') or None
        data_inicio = dados.get('data_inicio') or datetime.now().date()
        setor_nome = (dados.get('setor') or '').strip()
        if not nome or not email or not setor_nome:
            return jsonify({'erro': 'Nome, e-mail e setor são obrigatórios'}), 400

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
            (descricao, nivel, nome, email, cargo, setor, valor_hora, data_inicio,
             status, senha, telefone, permissoes, id_usuario)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'ATIVO', '', %s, '[]', %s)""",
            (nome, nivel, nome, email, cargo, setor_nome, valor_hora, data_inicio,
             telefone, g.membro['id_usuario'])
        )
        conn.commit()
        novo_id = cursor.lastrowid
        cursor.execute('SELECT * FROM grupo_solucionadores WHERE id_grupo_solucionadores = %s', (novo_id,))
        novo_membro = dict_fetchone(cursor)
        novo_membro.pop('senha', None)
        novo_membro.pop('permissoes', None)
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
    campos = {campo: dados[campo] for campo in ('email', 'telefone', 'data_inicio', 'valor_hora', 'setor', 'nivel', 'status') if campo in dados}
    if 'setor' in campos:
        campos['setor'] = (campos['setor'] or '').strip()
        if not campos['setor']:
            return jsonify({'erro': 'O setor não pode ficar vazio.'}), 400
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
    empresa = (dados.get('empresa') or '').strip()
    email = (dados.get('email') or '').strip().lower()
    senha = dados.get('senha') or ''

    if not nome or not empresa or not email or not senha:
        return jsonify({'erro': 'Nome, empresa, e-mail e senha são obrigatórios'}), 400
    if not email_valido(email):
        return jsonify({'erro': 'Informe um endereço de e-mail válido'}), 400
    if dominio_email_bloqueado(email):
        return jsonify({'erro': 'Use um e-mail empresarial; Gmail e Yahoo não são aceitos.'}), 400
    if len(senha) < 8:
        return jsonify({'erro': 'A senha deve ter pelo menos 8 caracteres'}), 400

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        conn.execute('BEGIN IMMEDIATE')
        cursor.execute('SELECT id_grupo_solucionadores FROM grupo_solucionadores WHERE LOWER(email) = %s LIMIT 1', (email,))
        if cursor.fetchone():
            conn.rollback()
            return jsonify({'erro': 'Já existe uma conta cadastrada com este e-mail'}), 409

        cursor.execute("SELECT id_usuario, nome FROM usuario WHERE tipo_usuario = 'WORKSPACE' AND LOWER(email) = %s LIMIT 1", (email,))
        if cursor.fetchone():
            conn.rollback()
            return jsonify({'erro': 'Já existe uma conta cadastrada com este e-mail'}), 409

        cursor.execute(
            "INSERT INTO usuario (nome, email, status, tipo_usuario, workspace_name, support_email) "
            "VALUES (%s, %s, 'ATIVO', 'WORKSPACE', %s, %s)",
            (empresa, email, empresa, email),
        )
        workspace_id = cursor.lastrowid
        permissoes = sorted(PERMISSOES_VALIDAS)
        cursor.execute('''
            INSERT INTO grupo_solucionadores
                (descricao, nome, email, cargo, setor, status, senha, id_usuario, permissoes)
            VALUES (%s, %s, %s, 'Administrador', 'Suporte', 'ATIVO', %s, %s, %s)
        ''', (
            empresa, nome, email, generate_password_hash(senha),
            workspace_id, json.dumps(permissoes)
        ))
        membro_id = cursor.lastrowid
        conn.commit()
    except Error as error:
        conn.rollback()
        app.logger.exception('Não foi possível criar a conta.', exc_info=error)
        return jsonify({'erro': 'Não foi possível criar a conta.'}), 500
    finally:
        cursor.close()
        conn.close()

    session.clear()
    session['grupo_id'] = membro_id
    return jsonify({
        'id': membro_id,
        'nome': nome,
        'email': email,
        'empresaNome': empresa,
        'cargo': 'Administrador',
        'permissoes': permissoes,
    }), 201


@app.route('/api/login', methods=['POST'])
def login():
    dados = request.get_json() or {}
    email = (dados.get('email') or '').strip()
    senha = dados.get('senha') or ''
    if not email or not senha:
        return jsonify({'erro': 'E-mail e senha são obrigatórios'}), 400
    if not _registrar_tentativa_login():
        return jsonify({
            'erro': 'Muitas tentativas de login. Aguarde 15 minutos e tente novamente.'
        }), 429
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
        check_password_hash(candidato['senha'], senha)
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
        'empresaNome': membro['empresa_nome'],
        'fotoPerfil': membro.get('foto_perfil'),
        'permissoes': sorted(_permissoes_do_membro(membro))
    }), 200


@app.route('/api/perfil/foto', methods=['PUT'])
def salvar_foto_perfil():
    foto = (request.get_json(silent=True) or {}).get('foto')
    match = re.fullmatch(
        r'data:image/(jpeg|png|webp);base64,([A-Za-z0-9+/]*={0,2})',
        foto if isinstance(foto, str) else '',
    )
    if not match or len(foto) > 1_500_000:
        return jsonify({'erro': 'Envie uma imagem JPEG, PNG ou WebP de até 1 MB.'}), 400
    try:
        conteudo = base64.b64decode(match.group(2), validate=True)
    except ValueError:
        return jsonify({'erro': 'A imagem enviada é inválida.'}), 400
    mime = match.group(1)
    valido = (
        (mime == 'jpeg' and conteudo.startswith(b'\xff\xd8\xff'))
        or (mime == 'png' and conteudo.startswith(b'\x89PNG\r\n\x1a\n'))
        or (mime == 'webp' and conteudo.startswith(b'RIFF') and conteudo[8:12] == b'WEBP')
    )
    if not conteudo or len(conteudo) > 1_000_000 or not valido:
        return jsonify({'erro': 'A imagem deve ser JPEG, PNG ou WebP e ter até 1 MB.'}), 400
    conn = get_db_connection()
    try:
        conn.execute(
            'UPDATE grupo_solucionadores SET foto_perfil = %s WHERE id_grupo_solucionadores = %s',
            (foto, g.membro['id_grupo_solucionadores']),
        )
        conn.commit()
        return jsonify({'fotoPerfil': foto}), 200
    except Error as error:
        app.logger.exception('Falha ao salvar foto de perfil.', exc_info=error)
        return jsonify({'erro': 'Não foi possível salvar a foto de perfil.'}), 500
    finally:
        conn.close()


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
        cursor.execute('''
            SELECT DISTINCT TRIM(setor) AS nome
            FROM grupo_solucionadores
            WHERE id_usuario = %s AND setor IS NOT NULL AND TRIM(setor) <> ''
            ORDER BY nome
        ''', (_ws(),))
        setores = dict_fetchall(cursor)
        cursor.close()
        conn.close()
        return jsonify(setores), 200
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
        filtro_data = 'WHERE id_usuario = %s'
        if periodo == 'mes':
            filtro_data += (
                " AND strftime('%Y', data_abertura) = strftime('%Y', 'now', 'localtime')"
                " AND strftime('%m', data_abertura) = strftime('%m', 'now', 'localtime')"
            )
        elif periodo == 'dia':
            filtro_data += " AND DATE(data_abertura) = DATE('now', 'localtime')"

        cursor.execute("""
            SELECT UPPER(TRIM(status)) AS status, COUNT(*) AS total
            FROM chamado
            """ + filtro_data + """
            GROUP BY UPPER(TRIM(status));
        """, (_ws(),))
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
            """ + filtro_data.replace('id_usuario', 'ch.id_usuario').replace('data_abertura', 'ch.data_abertura') + """
            GROUP BY 1
            ORDER BY total DESC, classificacao ASC;
        """, (_ws(),))
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
        cursor.execute('SELECT workspace_name, support_email, nome, email FROM usuario WHERE id_usuario = %s', (_ws(),))
        registro = cursor.fetchone()
        cursor.close()
        conn.close()
        configuracoes = {
            'workspaceName': (registro['workspace_name'] or registro['nome']) if registro else 'HelpTI Suporte',
            'supportEmail': (registro['support_email'] or registro['email']) if registro else 'suporte@helpti.com.br'
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
        cursor.execute(
            'UPDATE usuario SET workspace_name = %s, support_email = %s WHERE id_usuario = %s',
            (workspace_name, support_email, _ws()),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'workspaceName': workspace_name, 'supportEmail': support_email}), 200
    except Error as e:
        return jsonify({'erro': str(e)}), 500

# ============ GERENCIAMENTO DO BANCO (ADMIN) ============

# Tabelas do workspace e a cláusula que as restringe à empresa ativa.
_WS_TABELAS_BACKUP = (
    ('usuario', 'id_usuario = %s OR id_workspace = %s', 2),
    ('grupo_solucionadores', 'id_usuario = %s', 1),
    ('cliente', 'id_workspace = %s OR id_usuario IN (SELECT id_usuario FROM usuario WHERE id_workspace = %s)', 2),
    ('chamado', 'id_usuario = %s', 1),
    ('historico_chamado', 'id_chamado IN (SELECT id_chamado FROM chamado WHERE id_usuario = %s)', 1),
    ('escalonamento', 'id_chamado IN (SELECT id_chamado FROM chamado WHERE id_usuario = %s)', 1),
)
_COLUNAS_SECRETAS = {('usuario', 'senha_hash'), ('grupo_solucionadores', 'senha')}


def _exigir_administrador():
    if (g.membro.get('cargo') or '').strip().lower() != 'administrador':
        return jsonify({'erro': 'Somente o administrador pode gerenciar o banco de dados.'}), 403
    return None


def _sql_literal(valor):
    if valor is None:
        return 'NULL'
    if isinstance(valor, (int, float)):
        return repr(valor)
    if isinstance(valor, bytes):
        return "X'" + valor.hex() + "'"
    texto = str(valor).replace("'", "''")
    return "'" + texto + "'"


def _contagens_do_workspace(conn, ws):
    consultas = {
        'chamados': ('SELECT COUNT(*) FROM chamado WHERE id_usuario = %s', (ws,)),
        'clientes': ("SELECT COUNT(*) FROM usuario WHERE tipo_usuario = 'CLIENTE' AND id_workspace = %s", (ws,)),
        'equipe': ('SELECT COUNT(*) FROM grupo_solucionadores WHERE id_usuario = %s', (ws,)),
        'historico': ('SELECT COUNT(*) FROM historico_chamado WHERE id_chamado IN '
                      '(SELECT id_chamado FROM chamado WHERE id_usuario = %s)', (ws,)),
    }
    return {nome: conn.execute(sql, params).fetchone()[0] for nome, (sql, params) in consultas.items()}


@app.route('/api/admin/db/stats', methods=['GET'])
def admin_db_stats():
    negado = _exigir_administrador()
    if negado:
        return negado
    conn = get_db_connection()
    try:
        database_path = Path(database_settings()['database'])
        tamanho = sum(
            candidate.stat().st_size
            for candidate in (database_path, Path(f'{database_path}-wal'))
            if candidate.exists()
        )
        caminho = f"sqlite:///{database_path}"
        return jsonify({
            'tamanhoBytes': int(tamanho),
            'registros': _contagens_do_workspace(conn, _ws()),
            'caminho': caminho,
            'versaoSchema': SCHEMA_VERSION,
            'contaTeste': str(g.membro.get('email') or '').lower() == DEMO_EMAIL,
        }), 200
    finally:
        conn.close()


@app.route('/api/admin/db/backup', methods=['GET'])
def admin_db_backup():
    negado = _exigir_administrador()
    if negado:
        return negado
    ws = _ws()
    conn = get_db_connection()
    try:
        linhas = [
            '-- Backup HelpTI (somente dados deste workspace)',
            f'-- Gerado em {datetime.now().isoformat(timespec="seconds")}',
            f'-- Versão do schema: {SCHEMA_VERSION}',
            'PRAGMA foreign_keys = OFF;',
            'BEGIN;',
        ]
        for tabela, filtro, qtd in _WS_TABELAS_BACKUP:
            colunas = [
                coluna[1] for coluna in conn.execute(f'PRAGMA table_info({tabela})')
            ]
            lista = ', '.join(f'`{col}`' for col in colunas)
            for registro in conn.execute(f'SELECT {lista} FROM {tabela} WHERE {filtro}', (ws,) * qtd):
                valores = ', '.join(
                    "''" if (tabela, col) in _COLUNAS_SECRETAS else _sql_literal(registro[col])
                    for col in colunas
                )
                linhas.append(f'REPLACE INTO {tabela} ({lista}) VALUES ({valores});')
        linhas += [
            'COMMIT;',
            'PRAGMA foreign_keys = ON;',
            '',
        ]
    finally:
        conn.close()
    nome = f'helpti-backup-{ws}-{datetime.now():%Y%m%d-%H%M%S}.sql'
    return app.response_class(
        '\n'.join(linhas), mimetype='application/sql',
        headers={'Content-Disposition': f'attachment; filename="{nome}"'}
    )


@app.route('/api/admin/db/reset-demo', methods=['POST'])
def admin_db_reset_demo():
    negado = _exigir_administrador()
    if negado:
        return negado
    if str(g.membro.get('email') or '').lower() != DEMO_EMAIL or not demo_mode_enabled():
        return jsonify({'erro': 'A redefinição só está disponível na conta de teste.'}), 403
    ws = _ws()
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM chamado WHERE id_usuario = %s', (ws,))
        conn.execute("DELETE FROM usuario WHERE tipo_usuario = 'CLIENTE' AND id_workspace = %s", (ws,))
        conn.execute('DELETE FROM grupo_solucionadores WHERE id_usuario = %s AND LOWER(email) <> %s', (ws, DEMO_EMAIL))
        conn.commit()
        apply_demo_seed(conn)
        return jsonify({
            'mensagem': 'Demonstração restaurada ao estado inicial.',
            'registros': _contagens_do_workspace(conn, ws),
        }), 200
    finally:
        conn.close()


# ============ ROTA DE HEALTH CHECK ============

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'API rodando corretamente'}), 200

if __name__ == '__main__':
    if not run_security_checks(app):
        raise SystemExit('O HelpTI não iniciou porque uma verificação de segurança falhou.')
    initialize_database()
    host = os.environ.get('HELPTI_HOST', '127.0.0.1')
    debug_requested = os.environ.get('HELPTI_DEBUG', 'true').strip().lower() in ('1', 'true', 'yes', 'on')
    debug = debug_requested and host in ('127.0.0.1', 'localhost', '::1')
    port = int(os.environ.get('HELPTI_PORT', '5000'))
    if debug and os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        Timer(1, lambda: webbrowser.open('http://127.0.0.1:5000/')).start()
    app.run(host=host, debug=debug, port=port)
