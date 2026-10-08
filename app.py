import os
import sys
import webbrowser
from threading import Timer


def dependency_setup_message(module_name, project_dir):
    requirements_path = os.path.join(project_dir, 'backend', 'requirements.txt')
    launcher_path = os.path.join(project_dir, 'app.py')
    return (
        f'Dependência Python ausente: {module_name}.\n'
        f'Interpretador em uso: {sys.executable}\n'
        'Instale os requisitos nesse mesmo interpretador e tente novamente:\n'
        f'  & "{sys.executable}" -m pip install -r "{requirements_path}"\n'
        f'  & "{sys.executable}" "{launcher_path}"'
    )


if __name__ == '__main__':
    project_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        load_dotenv = None

    if load_dotenv:
        load_dotenv(os.path.join(project_dir, 'backend', '.env'))
        load_dotenv(os.path.join(project_dir, '.env'))

    from backend.startup_config import configure_startup

    os.environ['HELPTI_DEMO_MODE'] = 'prompt'
    os.environ.pop('HELPTI_DB_PATH', None)
    startup = configure_startup(project_dir=project_dir)

    try:
        from backend.app import app, initialize_database, run_security_checks
        from backend.database import DATABASE_PATH, demo_mode_enabled
    except ModuleNotFoundError as error:
        if error.name not in {
            'flask', 'authlib', 'joserfc', 'requests', 'werkzeug',
        }:
            raise
        raise SystemExit(dependency_setup_message(error.name, project_dir)) from error

    print(f"Ambiente selecionado: {startup['runtime']}")
    if not run_security_checks(app):
        raise SystemExit('O HelpTI não iniciou porque uma verificação de segurança falhou.')
    initialize_database()
    demo_status = 'habilitada' if demo_mode_enabled() else 'desabilitada'
    print(f'Banco SQLite ativo: {DATABASE_PATH.resolve()}')
    print(f'Conta teste HelpTI: {demo_status}')
    host = os.environ.get('HELPTI_HOST', '127.0.0.1')
    debug_requested = os.environ.get('HELPTI_DEBUG', 'false').strip().lower() in ('1', 'true', 'yes', 'on')
    debug = debug_requested and host in ('127.0.0.1', 'localhost', '::1')
    port = int(os.environ.get('HELPTI_PORT', '5000'))
    open_browser = os.environ.get('HELPTI_OPEN_BROWSER', 'true').strip().lower() in (
        '1', 'true', 'yes', 'on'
    )
    if open_browser and host in ('127.0.0.1', 'localhost', '::1'):
        Timer(1, lambda: webbrowser.open(f'http://127.0.0.1:{port}/')).start()
    production = (
        os.environ.get('FLASK_ENV', '').strip().lower() == 'production'
        or os.environ.get('HELPTI_ENV', '').strip().lower() == 'production'
    )
    if production:
        threads = int(os.environ.get('HELPTI_THREADS', '8'))
        if os.name == 'nt':
            from waitress import serve
            print(f'Produção: Waitress em {host}:{port}')
            serve(app, host=host, port=port, threads=threads)
        else:
            from gunicorn.app.base import BaseApplication

            class _Gunicorn(BaseApplication):
                def load_config(self):
                    self.cfg.set('bind', f'{host}:{port}')
                    self.cfg.set('workers', int(os.environ.get('WEB_CONCURRENCY', '2')))
                    self.cfg.set('threads', threads)

                def load(self):
                    return app

            print(f'Produção: Gunicorn em {host}:{port}')
            _Gunicorn().run()
    else:
        app.run(host=host, debug=debug, port=port, use_reloader=False)
