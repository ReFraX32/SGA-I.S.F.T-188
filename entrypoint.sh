#!/bin/sh
set -e

echo "Esperando a que la base de datos PostgreSQL esté lista..."
while ! python -c "import psycopg2, os; psycopg2.connect(dbname=os.environ.get('DB_NAME','sistema_alumnos_db'), user=os.environ.get('DB_USER','postgres'), password=os.environ.get('DB_PASSWORD','postgres'), host=os.environ.get('DB_HOST','db'), port=os.environ.get('DB_PORT','5432'))" 2>/dev/null; do
  sleep 1
done
echo "PostgreSQL está listo"

echo "Ejecutando migraciones de base de datos..."
python manage.py migrate --noinput

echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

echo "Verificando y cargando datos recopilados (Fixtures iniciales)..."
python manage.py loaddata initial_data || true

exec "$@"
