import os
import webbrowser
from threading import Timer

from backend.app import app, initialize_database


if __name__ == '__main__':
    initialize_database()
    host = os.environ.get('HELPTI_HOST', '127.0.0.1')
    debug_requested = os.environ.get('HELPTI_DEBUG', 'true').strip().lower() in ('1', 'true', 'yes')
    debug = debug_requested and host in ('127.0.0.1', 'localhost', '::1')
    port = int(os.environ.get('HELPTI_PORT', '5000'))
    if debug and os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        Timer(1, lambda: webbrowser.open('http://127.0.0.1:5000/')).start()
    app.run(host=host, debug=debug, port=port)
