"""Entrada WSGI de produção: `gunicorn wsgi:app` ou `waitress-serve wsgi:app`."""
from backend.app import app
from backend.database import initialize_database

initialize_database()

__all__ = ['app']
