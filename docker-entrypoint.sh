#!/bin/sh
set -e

# 1. Wait until PostgreSQL accepts connections (the "db" service may still be starting)
echo "Waiting for PostgreSQL at ${DATABASE_URL##*@} ..."
tries=0
until python -c "import os, psycopg2; psycopg2.connect(os.environ['DATABASE_URL']).close()" 2>/dev/null; do
  tries=$((tries + 1))
  if [ "$tries" -ge 30 ]; then
    echo "ERROR: PostgreSQL is not reachable after 60 seconds. Check DATABASE_URL and the db service."
    exit 1
  fi
  sleep 2
done
echo "PostgreSQL is ready."

# 2. Apply pending migrations (uses the committed files in ./migrations, creates nothing new)
echo "Applying database migrations..."
flask db upgrade

# 3. Optional: load sample data + development admin (safe to run repeatedly)
if [ "${SEED_ON_START:-false}" = "true" ]; then
  echo "Seeding sample data..."
  flask seed
fi

# 4. Start the app (Gunicorn, from the Dockerfile CMD)
echo "Starting: $*"
exec "$@"
