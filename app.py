import os
import webbrowser
from threading import Timer


if __name__ == '__main__':
    from dotenv import load_dotenv

    project_dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(project_dir, 'backend', '.env'))
    load_dotenv(os.path.join(project_dir, '.env'))

    from backend.startup_config import configure_startup

    os.environ['HELPTI_DEMO_MODE'] = 'prompt'
    os.environ.pop('HELPTI_DB_PATH', None)
    startup = configure_startup(project_dir=project_dir)

    from backend.app import app, initialize_database, run_security_checks
    from backend.database import DATABASE_PATH, demo_mode_enabled

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
    app.run(host=host, debug=debug, port=port, use_reloader=False)
