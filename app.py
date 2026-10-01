import os
import webbrowser
from threading import Timer

from backend.app import app, initialize_database


if __name__ == '__main__':
    initialize_database()
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        Timer(1, lambda: webbrowser.open('http://127.0.0.1:5000/')).start()
    app.run(debug=True, port=5000)
