FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system --gid 10001 help-ti \
    && useradd --system --uid 10001 --gid help-ti --home-dir /app help-ti \
    && mkdir -p /app/instance \
    && chown help-ti:help-ti /app/instance

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY --chown=help-ti:help-ti app.py wsgi.py ./
COPY --chown=help-ti:help-ti backend ./backend
COPY --chown=help-ti:help-ti frontend ./frontend

EXPOSE 5000

ENTRYPOINT ["python", "backend/container_entrypoint.py"]
CMD ["sh", "-c", "exec gunicorn --workers ${WEB_CONCURRENCY:-2} --threads ${GUNICORN_THREADS:-4} --timeout 60 --access-logfile - --bind 0.0.0.0:${PORT:-5000} wsgi:app"]
