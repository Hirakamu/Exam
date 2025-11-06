# simulating exam traffic
import uuid
from flask import Flask, jsonify, request, render_template
from psycopg2 import pool, sql
import json
import os
from functools import lru_cache
import yaml
import hashlib
import atexit
import random
import string
from datetime import datetime, timezone, timedelta
import requests
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(ROOT, "config.yaml"), "r") as f:
    config = yaml.safe_load(f)

DBCONFIG = {
    "dbname": f"{config['database']['name']}",
    "user": f"{config['database']['user']}",
    "password": f"{config['database']['password']}",
    "host": f"{config['database']['host']}"
}
dbPool = pool.ThreadedConnectionPool(
    1,
    50,
    **DBCONFIG
)

# ensure pool is closed on exit
atexit.register(dbPool.closeall)

def getDB():
    return dbPool.getconn()

def putDB(conn):
    dbPool.putconn(conn)

query = sql.SQL("SELECT * FROM students")
conn = getDB()
cur = conn.cursor()
cur.execute(query)
students = cur.fetchall()
cur.close()
putDB(conn)

headers = {"Content-Type": "application/json", "User-Agent": "cbt-exam-browser"}

token = {}
register = {}

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

token_lock = threading.Lock()

# records of student run durations
durations_lock = threading.Lock()
durations = []  # list of dicts: {"nis": ..., "duration": float, "success": bool}

for tok in range(1, 27):
    payload = {"room": tok}
    try:
        resp = requests.post("http://localhost:5000/teacher/tokens/create", json=payload, headers=headers, timeout=5)
        t = resp.json().get("token")
        with token_lock:
            token[tok] = t
        print(f"Room {tok}: Token {t}")
    except Exception as e:
        print(f"Failed creating token for room {tok}: {e}")

def student_worker(student):
    """Worker that simulates a single student: create/get token, start exam, finish exam."""
    nis = student[0]

    # student[4] may be str or int, try multiple lookups to find the token
    room_key = student[4]
    with token_lock:
        t = token.get(room_key)
        if t is None:
            try:
                t = token.get(int(room_key))
            except Exception:
                pass
        if t is None:
            t = token.get(str(room_key))
    if not t:
        print(f"NIS {nis}: no token for room {room_key}")
        return

    # measure duration from before start -> after finish (or failure)
    start_time = time.perf_counter()

    # Start
    start_payload = {"room": student[4], "nis": nis, "token": t}
    exam_hash = None
    try:
        resp = requests.post("http://localhost:5000/start", json=start_payload, headers=headers, timeout=10)
        # safe-guard if response is not JSON
        try:
            exam_hash = resp.json().get("exam-hash")
        except Exception:
            exam_hash = None

        if not exam_hash:
            duration = time.perf_counter() - start_time
            print(f"NIS {nis}: failed to obtain exam-hash (response: {resp.text})")
            with durations_lock:
                durations.append({"nis": nis, "duration": duration, "success": False})
            return
    except Exception as e:
        duration = time.perf_counter() - start_time
        print(f"NIS {nis}: start POST failed: {e}")
        with durations_lock:
            durations.append({"nis": nis, "duration": duration, "success": False})
        return

    # Finish
    finish_payload = {"nis": nis, "hash": exam_hash}
    try:
        resp = requests.post("http://localhost:5000/finish", json=finish_payload, headers=headers, timeout=10)
        duration = time.perf_counter() - start_time
        with durations_lock:
            durations.append({"nis": nis, "duration": duration, "success": True})
    except Exception as e:
        print(f"NIS {nis}: finish POST failed: {e}")
        duration = time.perf_counter() - start_time
        with durations_lock:
            durations.append({"nis": nis, "duration": duration, "success": False})


def run_threaded(students_list):
    if not students_list:
        print("No students found to simulate.")
        return
    max_workers = min(50, len(students_list))
    print(f"Running {len(students_list)} students with up to {max_workers} threads (1 student per thread)...")
    overall_start = time.perf_counter()
    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for s in students_list:
            futures.append(ex.submit(student_worker, s))

        for fut in as_completed(futures):
            # exceptions (if any) will be raised here and printed
            try:
                fut.result()
            except Exception as e:
                print(f"Worker raised: {e}")

    wall_time = time.perf_counter() - overall_start
    print("All workers done.")

    # compute stats from recorded durations
    with durations_lock:
        recs = list(durations)

    total_runs = len(recs)
    successes = [r for r in recs if r.get("success")]
    success_count = len(successes)
    total_duration = sum(r.get("duration", 0) for r in successes)
    average_duration = (total_duration / success_count) if success_count else 0.0
    print(f"Summary: wall_time={wall_time:.3f}s, total_records={total_runs}, successes={success_count}, total_duration={total_duration:.3f}s, average={average_duration:.3f}s.")
    print("Dont forget to cleanup the sessions and tokens in the database.")


if __name__ == '__main__':
    # run the threaded simulation
    run_threaded(students)