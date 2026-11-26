FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8766 \
    DATABASE_PATH=/data/support.sqlite3

WORKDIR /app
COPY . /app
RUN mkdir -p /data

EXPOSE 8766
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8766/health', timeout=2)"]
CMD ["python", "app.py"]
