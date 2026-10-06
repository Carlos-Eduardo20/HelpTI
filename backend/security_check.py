import ast
import os
from pathlib import Path


def _source_security_issues(source_path):
    source = Path(source_path).read_text(encoding='utf-8')
    tree = ast.parse(source, filename=str(source_path))
    issues = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            function = node.func
            name = function.id if isinstance(function, ast.Name) else ''
            if name in {'eval', 'exec'}:
                issues.append(f'uso de {name}() na linha {node.lineno}')
            if isinstance(function, ast.Attribute):
                if function.attr == 'system' and isinstance(function.value, ast.Name):
                    if function.value.id == 'os':
                        issues.append(f'uso de os.system() na linha {node.lineno}')
                if function.attr in {'run', 'Popen', 'call'}:
                    if any(
                        keyword.arg == 'shell'
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                        for keyword in node.keywords
                    ):
                        issues.append(f'subprocess com shell=True na linha {node.lineno}')
    return issues


def run_security_checks(app, source_path=None):
    checks = []

    def record(label, passed, detail=''):
        checks.append((passed, label, detail))

    secret = app.config.get('SECRET_KEY')
    record(
        'Comprimento mínimo da chave de sessão',
        isinstance(secret, str) and len(secret) >= 32,
        'A chave deve ter pelo menos 32 caracteres.'
    )
    record(
        'Cookie de sessão protegido',
        app.config.get('SESSION_COOKIE_HTTPONLY') is True
        and app.config.get('SESSION_COOKIE_SAMESITE') in {'Lax', 'Strict'},
        'HTTPOnly e SameSite=Lax/Strict devem estar ativos.'
    )

    host = os.getenv('HELPTI_HOST', '127.0.0.1').strip().lower()
    loopback = host in {'127.0.0.1', 'localhost', '::1'}
    https_only = os.getenv('HELPTI_HTTPS_ONLY', 'false').strip().lower() in {
        '1', 'true', 'yes', 'on'
    }
    if not loopback and not https_only:
        record(
            'Cookie seguro para acesso remoto',
            False,
            'Defina HELPTI_HTTPS_ONLY=true ao acessar por HTTPS.'
        )
    else:
        record('Cookie seguro para acesso remoto', True)

    debug_requested = os.getenv('HELPTI_DEBUG', 'false').strip().lower() in {
        '1', 'true', 'yes', 'on'
    }
    record(
        'Modo de depuração seguro',
        loopback or not debug_requested,
        'Desative HELPTI_DEBUG ao expor o servidor na rede.'
    )

    if not loopback and os.getenv('HELPTI_DEMO_MODE', 'true').strip().lower() in {
        '1', 'true', 'yes', 'on'
    }:
        record(
            'Conta compartilhada de demonstração',
            True,
            'AVISO: a conta de teste fica ativa. Não exponha uma instalação com dados reais.'
        )
    else:
        record('Conta compartilhada de demonstração', True)

    source_path = source_path or Path(__file__).with_name('app.py')
    try:
        issues = _source_security_issues(source_path)
    except (OSError, SyntaxError) as error:
        record('Inspeção estática de padrões perigosos', False, str(error))
    else:
        record(
            'Inspeção estática de padrões perigosos',
            not issues,
            '; '.join(issues) if issues else 'Nenhum padrão de risco alto foi encontrado.'
        )

    print('Validando a configuração básica de segurança do HelpTI...')
    failed = False
    for passed, label, detail in checks:
        if passed:
            status = 'AVISO' if detail.startswith('AVISO:') else 'OK'
            print(f'[{status}] {label}' + (f' — {detail}' if detail else ''))
        else:
            failed = True
            print(f'[FALHA] {label}' + (f' — {detail}' if detail else ''))
    print(
        'Verificação concluída; esta checagem local não substitui auditoria completa '
        'nem análise de CVEs das dependências.'
    )
    return not failed
