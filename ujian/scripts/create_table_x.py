#!/usr/bin/env python3
"""
Create a Postgres table named `x` and populate it with students from
`ujian/data/X.json`, `ujian/data/XI.json`, and `ujian/data/XII.json` (if present).

Columns: nis (PK), name, grade

Usage: python3 create_table_x.py

Requirements: pyyaml (already used in project) and psycopg2-binary.
Install psycopg2-binary with: pip install psycopg2-binary
"""
import json
import os
import sys
from pathlib import Path

try:
    import yaml
except Exception:
    print("PyYAML is required. Please install with: pip install pyyaml")
    raise

try:
    import psycopg2
    from psycopg2.extras import execute_values
except Exception:
    print("psycopg2 is required. Please install with: pip install psycopg2-binary")
    raise


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CONFIG_FILE = ROOT / "config.yaml"


def load_config(path):
    if not path.exists():
        raise FileNotFoundError(f"config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def connect_db(cfg):
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


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS x (
    nis VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    grade VARCHAR(10) NOT NULL
);
"""


def upsert_students(conn, rows):
    """rows: list of (nis, name, grade) tuples"""
    if not rows:
        return 0
    with conn.cursor() as cur:
        sql = (
            "INSERT INTO x (nis, name, grade) VALUES %s "
            "ON CONFLICT (nis) DO UPDATE SET name = EXCLUDED.name, grade = EXCLUDED.grade"
        )
        execute_values(cur, sql, rows, template=None, page_size=100)
        return len(rows)


def load_grade_file(path, grade_label):
    if not path.exists():
        print(f"Grade file not found, skipping: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    students = []
    sections = data.get("sections", {})
    for section, entries in sections.items():
        for e in entries:
            nis = e.get("nis") or e.get("NIS") or e.get("no")
            name = e.get("name") or e.get("NAME")
            if not nis or not name:
                # skip malformed entries
                continue
            students.append((str(nis).strip(), name.strip(), grade_label))
    return students


def main():
    cfg = load_config(CONFIG_FILE)
    conn = connect_db(cfg)

    print("Creating table `x` if it does not exist...")
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)

    grades = ["X", "XI", "XII"]
    total = 0
    for g in grades:
        filename = DATA_DIR / f"{g}.json"
        rows = load_grade_file(filename, g)
        if rows:
            inserted = upsert_students(conn, rows)
            print(f"Processed grade {g}: {inserted} rows")
            total += inserted
        else:
            print(f"No rows for grade {g}")

    # summary checks
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM x")
        row = cur.fetchone()
        count = row[0] if row else 0
        print(f"Table x now contains {count} rows (total processed: {total})")

        # show a few sample rows grouped by grade
        cur.execute("SELECT nis, name, grade FROM x ORDER BY grade, nis LIMIT 10")
        samples = cur.fetchall()
        if samples:
            print("Sample rows:")
            for nis, name, grade in samples:
                print(f"  {nis}\t{grade}\t{name}")

    conn.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Error:", e)
        sys.exit(1)
