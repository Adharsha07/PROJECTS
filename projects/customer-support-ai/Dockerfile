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
CMD ["python", "app.py"]

