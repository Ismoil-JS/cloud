#!/bin/sh
set -e

echo "==> Waiting for PostgreSQL..."
python << 'PYEOF'
import sys
import time
import os
import psycopg2

host = os.environ.get('DB_HOST', 'db')
port = int(os.environ.get('DB_PORT', '5432'))
name = os.environ.get('DB_NAME', 'taskmanager')
user = os.environ.get('DB_USER', 'taskmanager')
password = os.environ.get('DB_PASSWORD', '')

for attempt in range(1, 31):
    try:
        conn = psycopg2.connect(
            dbname=name, user=user, password=password,
            host=host, port=port,
        )
        conn.close()
        print("PostgreSQL is ready!")
        sys.exit(0)
    except psycopg2.OperationalError:
        print(f"  Attempt {attempt}/30 — not ready yet, retrying in 1s...")
        time.sleep(1)

print("ERROR: Could not connect to PostgreSQL after 30 attempts.")
sys.exit(1)
PYEOF

echo "==> Running database migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Starting application..."
exec "$@"
