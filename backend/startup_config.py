import os


def configure_startup(input_fn=input, output_fn=print):
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
    os.environ.setdefault('DB_NAME', 'helpti_app')

    return {
        'demo_mode': use_demo,
        'database': os.environ['DB_NAME'],
    }

