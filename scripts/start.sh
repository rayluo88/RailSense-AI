#!/bin/sh
set -e

echo "Running Alembic migrations..."

# If alembic_version table doesn't exist (tables were bootstrapped by create_all,
# not by migrations), stamp at the initial revision so Alembic knows the baseline.
python - <<'EOF'
import os
from sqlalchemy import create_engine, inspect, text

engine = create_engine(os.environ["DATABASE_URL"])
insp = inspect(engine)
if not insp.has_table("alembic_version"):
    print("No alembic_version table found — stamping at initial revision 91711aab5efb")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE alembic_version "
            "(version_num VARCHAR(32) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
        ))
        conn.execute(text("INSERT INTO alembic_version VALUES ('91711aab5efb')"))
else:
    print("alembic_version table found — skipping stamp")
EOF

alembic upgrade head

echo "Starting server..."
exec uvicorn src.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
