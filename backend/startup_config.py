import os
from pathlib import Path


def configure_startup(input_fn=input, output_fn=print, project_dir=None):
    project_dir = Path(project_dir or Path(__file__).resolve().parent.parent)
    demo_setting = os.getenv('HELPTI_DEMO_MODE', 'prompt').strip().lower()

    if demo_setting in {'1', 'true', 'yes', 'on'}:
        use_demo = True
    elif demo_setting in {'0', 'false', 'no', 'off'}:
        use_demo = False
    else:
        while True:
            answer = input_fn(
                'Deseja iniciar com a conta de teste HelpTI? (S/N): '
            ).strip().lower()
            if answer in {'s', 'sim', 'y', 'yes'}:
                use_demo = True
                break
            if answer in {'n', 'nao', 'não', 'no'}:
                use_demo = False
                break
            output_fn('Resposta inválida. Digite S para sim ou N para não.')

    os.environ['HELPTI_DEMO_MODE'] = 'true' if use_demo else 'false'

    runtime = os.getenv('HELPTI_RUNTIME_ENV', '').strip().lower()
    if not runtime:
        runtime = (
            'codespace'
            if os.getenv('CODESPACES', '').strip().lower() == 'true'
            else 'local'
        )
    if runtime not in {'local', 'codespace'}:
        raise ValueError('HELPTI_RUNTIME_ENV deve ser "local" ou "codespace".')

    if not os.getenv('HELPTI_DB_PATH', '').strip():
        if runtime == 'codespace':
            database_name = (
                'helpti-codespace.sqlite3'
                if use_demo
                else 'helpti-codespace-empresa.sqlite3'
            )
        else:
            database_name = (
                'helpti.sqlite3'
                if use_demo
                else 'helpti-empresa-local.sqlite3'
            )
        database_path = project_dir / 'instance' / database_name
        os.environ['HELPTI_DB_PATH'] = str(database_path)

    return {
        'demo_mode': use_demo,
        'database_path': Path(os.environ['HELPTI_DB_PATH']).expanduser(),
        'runtime': runtime,
    }
