#!/usr/bin/env python3
"""
Scan a directory recursively for student JSON files and populate a Postgres
table with (nis, name, grade). This is a reusable version of
`create_table_x.py`.

Features:
- Recursively scans a data directory for `*.json` files
- Detects files that look like student lists (contain a top-level "sections"
  mapping or a top-level list of student objects)
- Extracts grade from the JSON (`grade` field) or from the filename
- Upserts into a configurable table name (default: `x`)
- Supports `--dry-run` to print what would be inserted without connecting

Usage examples:
  python3 create_table_from_jsons.py                       # uses ujian/config.yaml and ujian/data
  python3 create_table_from_jsons.py --data ./data --table students --dry-run

Requirements: pyyaml (project already uses it) and psycopg2-binary for DB access
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

try:
    import yaml
except Exception:
    print("PyYAML is required. Please install with: pip install pyyaml")
    raise

try:
    import psycopg2
    from psycopg2.extras import execute_values
except Exception:
    # We'll allow dry-run without psycopg2 installed
    psycopg2 = None
    execute_values = None


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data"
DEFAULT_CONFIG = ROOT / "config.yaml"


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def connect_db(cfg: dict):
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not installed. Install with: pip install psycopg2-binary")
    db = cfg.get("database", {})
    engine = db.get("engine", "postgresql")
    if engine != "postgresql":
        raise RuntimeError(f"Unsupported database engine in config: {engine}")
    conn = psycopg2.connect(
        dbname=db.get("name"),
        user=db.get("user"),
        password=db.get("password"),
        host=db.get("host", "localhost"),
        port=int(db.get("port", 5432)),
    )
    conn.autocommit = True
    return conn


def find_json_files(data_dir: Path) -> Iterable[Path]:
    for p in data_dir.rglob("*.json"):
        # skip files under exam/safeexam/teacher directories which are not student lists
        # allow caller to filter more strictly if needed
        yield p


def extract_students_from_json(path: Path) -> Tuple[Optional[str], List[Tuple[str, str]]]:
    """Return (grade_label_or_none, list_of_(nis,name))."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None, []

    grade = None
    if isinstance(data, dict):
        grade = data.get("grade")

        # common student format used in this project: { "sections": { ... } }
        sections = data.get("sections")
        if isinstance(sections, dict):
            students = []
            for section, entries in sections.items():
                if not isinstance(entries, list):
                    continue
                for e in entries:
                    if not isinstance(e, dict):
                        continue
                    nis = e.get("nis") or e.get("NIS") or e.get("no")
                    name = e.get("name") or e.get("NAME")
                    if nis and name:
                        students.append((str(nis).strip(), name.strip()))
            return grade, students

        # fallback: maybe it's a top-level list under some key like "students"
        for key in ("students", "data", "items"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                students = []
                for e in candidate:
                    if not isinstance(e, dict):
                        continue
                    nis = e.get("nis") or e.get("NIS") or e.get("no")
                    name = e.get("name") or e.get("NAME")
                    if nis and name:
                        students.append((str(nis).strip(), name.strip()))
                if students:
                    return grade, students

    elif isinstance(data, list):
        students = []
        for e in data:
            if not isinstance(e, dict):
                continue
            nis = e.get("nis") or e.get("NIS") or e.get("no")
            name = e.get("name") or e.get("NAME")
            if nis and name:
                students.append((str(nis).strip(), name.strip()))
        return None, students

    return None, []


def upsert_into_table(conn, table: str, rows: List[Tuple[str, str, str]]) -> int:
    """Upsert rows (nis, name, grade) into `table`. Returns number of rows."""
    if not rows:
        return 0
    with conn.cursor() as cur:
        if execute_values:
            sql = (
                f"INSERT INTO {table} (nis, name, grade) VALUES %s "
                f"ON CONFLICT (nis) DO UPDATE SET name = EXCLUDED.name, grade = EXCLUDED.grade"
            )
            execute_values(cur, sql, rows, template=None, page_size=100)
            return len(rows)
        else:
            # fallback: execute single-row INSERT ... ON CONFLICT per row
            insert_sql = (
                f"INSERT INTO {table} (nis, name, grade) VALUES (%s, %s, %s) "
                f"ON CONFLICT (nis) DO UPDATE SET name = EXCLUDED.name, grade = EXCLUDED.grade"
            )
            for r in rows:
                cur.execute(insert_sql, r)
            return len(rows)


def create_table_if_not_exists(conn, table: str):
    sql = (
        f"CREATE TABLE IF NOT EXISTS {table} ("
        "nis VARCHAR(50) PRIMARY KEY,"
        "name VARCHAR(200) NOT NULL,"
        "grade VARCHAR(10) NOT NULL"
        ");"
    )
    with conn.cursor() as cur:
        cur.execute(sql)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create/upsert students into a Postgres table from JSON files")
    parser.add_argument("--data", default=str(DEFAULT_DATA_DIR), help="Data directory to scan")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to config.yaml")
    parser.add_argument("--table", default="x", help="DB table to write to (default: x)")
    parser.add_argument("--dry-run", action="store_true", help="Don't connect to DB, just print actions")
    args = parser.parse_args(argv)

    data_dir = Path(args.data)
    cfg = load_config(Path(args.config))

    found_rows = []  # (nis, name, grade)

    for p in find_json_files(data_dir):
        grade_label, students = extract_students_from_json(p)
        if not students:
            # skip non-student json files
            continue
        label = grade_label if grade_label else p.stem.upper()
        for nis, name in students:
            found_rows.append((nis, name, label))

    if not found_rows:
        print("No student records found under", data_dir)
        return 0

    # group counts by grade for reporting
    counts = {}
    for _, _, g in found_rows:
        counts[g] = counts.get(g, 0) + 1
    print("Found student counts by grade:")
    for g, c in sorted(counts.items()):
        print(f"  {g}: {c}")

    if args.dry_run:
        print("Dry-run mode: not connecting to DB. Sample rows:")
        for nis, name, grade in found_rows[:20]:
            print(f"  {nis}\t{grade}\t{name}")
        return 0

    conn = connect_db(cfg)
    create_table_if_not_exists(conn, args.table)
    inserted = upsert_into_table(conn, args.table, found_rows)

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {args.table}")
        row = cur.fetchone()
        total = row[0] if row else 0
        print(f"Table {args.table} now contains {total} rows (inserted/updated: {inserted})")

        cur.execute(f"SELECT nis, grade, name FROM {args.table} ORDER BY grade, nis LIMIT 10")
        samples = cur.fetchall()
        if samples:
            print("Sample rows:")
            for nis, grade, name in samples:
                print(f"  {nis}\t{grade}\t{name}")

    conn.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print("Error:", e)
        sys.exit(1)
