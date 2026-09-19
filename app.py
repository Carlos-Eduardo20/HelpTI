import os
import webbrowser
from threading import Timer

from backend.app import app, apply_schema_if_missing, ensure_data_columns


if __name__ == '__main__':
    apply_schema_if_missing()
    ensure_data_columns()
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        Timer(1, lambda: webbrowser.open('http://127.0.0.1:5000/')).start()
    app.run(debug=True, port=5000)
