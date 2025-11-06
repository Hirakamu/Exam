#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.."
JSON_FILE="$ROOT_DIR/ujian/data/school.json"
PSQL_BIN="${PSQL_BIN:-psql}"
PG_OPTS="${PG_OPTS:--h localhost -U postgres -d sman2cikpusexam}"   # example: "-h localhost -U myuser -d mydb" or export PGHOST/PGUSER/PGDATABASE

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required. install it (sudo apt install jq) and retry." >&2
  exit 1
fi

if [ ! -f "$JSON_FILE" ]; then
  echo "school.json not found: $JSON_FILE" >&2
  exit 1
fi

# produce and pipe SQL to psql
jq -c '.guru[]' "$JSON_FILE" | while read -r guru; do
  id=$(jq -r '.id' <<<"$guru")
  name=$(jq -r '.name' <<<"$guru" | sed "s/'/''/g")
  job=$(jq -c '.subject' <<<"$guru")
  # use dollar-quoting for JSON value to avoid escaping
  printf "INSERT INTO teachers (id, name, job) VALUES (%d, '%s', \$json\$%s\$json\$) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, job = EXCLUDED.job;\n" \
    "$id" "$name" "$job"
done | ${PSQL_BIN} ${PG_OPTS} -v ON_ERROR_STOP=1 -q

# ensure serial sequence is in sync with inserted ids
${PSQL_BIN} ${PG_OPTS} -v ON_ERROR_STOP=1 -q <<'SQL'
SELECT setval(pg_get_serial_sequence('teachers','id'), coalesce((SELECT MAX(id) FROM teachers), 1), true);
SQL