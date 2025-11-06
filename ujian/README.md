# ujian (Hira Form System)

This folder contains a small Flask-based exam system (students, teachers, proctors) backed by PostgreSQL.

Quick start (local development)

1. Create database and run the schema:

```bash
# create DB (example)
createdb ujian_local
psql -d ujian_local -f ujian/scripts/schema.sql
```

2. Create `ujian/data/config.yaml` with your database connection info, for example:

```yaml
database:
  name: ujian_local
  user: yourdbuser
  password: secret
  host: localhost
```

3. Install dependencies and run the app (recommended in a virtualenv):

```bash
python -m pip install -r requirements.txt
python -m ujian.hiraexam
```

Notes and suggestions

- The project includes `ujian/scripts/schema.sql` for schema bootstrapping. Review it before applying to production.
- `ujian/db.py` now includes a `db_cursor()` context manager to simplify safe DB access:

```py
from ujian.db import db_cursor
with db_cursor() as (conn, cur):
    cur.execute("SELECT 1")
    row = cur.fetchone()
```

- Recommended next steps:
  - Add a docker-compose file for reproducible local environment (Postgres + app).
  - Add unit tests using pytest for core flows (token validation, session creation, answer submit).
  - Add migration tooling (Alembic) if you plan iterative schema changes.
  - Consolidate startup code in `hiraexam.py` to use `db.py` helpers only.

If you want, I can now:
- refactor `hiraexam.py` to use the new helpers and remove duplicate pool creation, or
- update a few route handlers to use `db_cursor()` to reduce boilerplate, or
- add a docker-compose and a basic test.
