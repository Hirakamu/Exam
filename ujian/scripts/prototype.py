import os
import json
import hashlib
from datetime import datetime, timezone
from flask import Flask, request, jsonify, abort
import psycopg2
from psycopg2 import pool, sql, errors
from psycopg2.extras import RealDictCursor
import random, string

# Config
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:hirakamucatodevsql@localhost:5432/sman2cikpusexam")
SALT = os.getenv("SALT", "replace-with-strong-random-salt")
PORT = int(os.getenv("PORT", "5000"))

app = Flask(__name__)

# Connection pool
pg_pool = pool.ThreadedConnectionPool(minconn=1, maxconn=10, dsn=DATABASE_URL)

def get_conn():
    return pg_pool.getconn()

def put_conn(conn):
    pg_pool.putconn(conn)

def sha256_hexdigest(*parts: str) -> str:
    h = hashlib.sha256()
    joined = "|".join(parts) + "|" + SALT
    h.update(joined.encode("utf-8"))
    return h.hexdigest()

def query_one(cur, q, params=()):
    cur.execute(q, params)
    return cur.fetchone()

@app.route("/student/check", methods=["POST"]) # not yet tested
def student_check():
    """
    Request JSON:
    { "nis": "252610001", "grade": "XI", "class": "F2" }
    Response:
    { "ok": true, "name": "Student Name" }
    """
    req = request.get_json(force=True)
    nis = req.get("nis")
    grade = req.get("grade")
    klas = req.get("class")  # 'class' is a reserved keyword in Python; use klas

    if not (nis and grade and klas):
        return jsonify({"ok": False, "error": "missing fields"}), 400

    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT nis, name, grade, room FROM students WHERE nis = %s",
                    (nis,)
                )
                student = cur.fetchone()
                if not student:
                    return jsonify({"ok": False, "error": "nis not found"}), 404
                if student["grade"] != grade or student["class"] != klas:
                    return jsonify({"ok": False, "error": "grade/class mismatch"}), 403

                return jsonify({"ok": True, "name": student["name"]}), 200
    finally:
        put_conn(conn)

@app.route("/student/login", methods=["POST"]) #not yet tested
def student_login():
    """
    Request JSON:
    { "nis": "252610001", "room": "01", "grade": "XI", "class": "F2", "token": "ABCDE" }
    Response:
    { "ok": true, "exam": {...}, "session_hash": "..." }
    """
    req = request.get_json(force=True)
    nis = req.get("nis")
    room = req.get("room")
    grade = req.get("grade")
    klas = req.get("class")  # 'class' is a reserved keyword in Python; use klas
    token = req.get("token")

    if not (nis and room and grade and klas and token):
        return jsonify({"ok": False, "error": "missing fields"}), 400

    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1) Verify token exists, matches room, not expired
                cur.execute(
                    "SELECT token, room, expires_at FROM tokens WHERE token = %s",
                    (token,)
                )
                token_row = cur.fetchone()
                if not token_row or token_row["room"] != room:
                    return jsonify({"ok": False, "error": "invalid token or room"}), 403
                if token_row["expires_at"] <= datetime.now(timezone.utc):
                    return jsonify({"ok": False, "error": "token expired"}), 403

                # 2) Verify NIS exists and matches grade/room
                cur.execute(
                    "SELECT nis, name, grade, room FROM students WHERE nis = %s",
                    (nis,)
                )
                student = cur.fetchone()
                if not student:
                    return jsonify({"ok": False, "error": "nis not found"}), 404
                if student["grade"] != grade or student["room"] != room:
                    return jsonify({"ok": False, "error": "grade/room mismatch"}), 403

                # 3) Compute session hash
                session_hash = sha256_hexdigest(nis, room, token)

                # 4) Try to create an active session. Unique partial index prevents duplicate active sessions.
                try:
                    cur.execute("""
                        INSERT INTO sessions (nis, room, grade, class, session_hash)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id, started_at
                    """, (nis, room, grade, klas, session_hash))
                    sess = cur.fetchone()
                except errors.UniqueViolation:
                    # another active session exists for this nis
                    conn.rollback()
                    return jsonify({"ok": False, "error": "already logged in"}), 409

                # 5) Fetch exam form(s) for this grade/class
                cur.execute("""
                    SELECT id, subject, payload
                    FROM exam_forms
                    WHERE grade = %s AND (class IS NULL OR class = %s)
                    ORDER BY id
                """, (grade, klas))
                forms = cur.fetchall()
                exams = [f["payload"] for f in forms]

                return jsonify({
                    "ok": True,
                    "session_id": str(sess["id"]) if sess else None,
                    "session_hash": session_hash,
                    "exam": exams
                }), 200
    finally:
        put_conn(conn)

@app.route("/student/finish", methods=["POST"]) # not yet tested
def student_finish():
    """
    Request JSON:
    { "nis": "...", "session_hash": "...", "answers": {...} }
    """
    req = request.get_json(force=True)
    nis = req.get("nis")
    session_hash = req.get("session_hash")
    answers = req.get("answers")

    if not (nis and session_hash and isinstance(answers, dict)):
        return jsonify({"ok": False, "error": "missing fields"}), 400

    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, active, session_hash FROM sessions
                    WHERE nis = %s AND active = true
                    FOR UPDATE
                """, (nis,))
                session = cur.fetchone()
                if not session:
                    return jsonify({"ok": False, "error": "no active session"}), 404
                if session["session_hash"] != session_hash:
                    return jsonify({"ok": False, "error": "invalid session hash"}), 403

                # store answers
                cur.execute("""
                    INSERT INTO answers (session_id, answers)
                    VALUES (%s, %s::jsonb)
                    RETURNING id, submitted_at
                """, (session["id"], json.dumps(answers)))
                ans = cur.fetchone()

                # mark session finished
                cur.execute("""
                    UPDATE sessions SET active = false, finished_at = now()
                    WHERE id = %s
                """, (session["id"],))

                return jsonify({"ok": True, "answer_id": str(ans["id"]), "submitted_at": ans["submitted_at"]}), 200
    finally:
        put_conn(conn)

@app.route("/monitoring/sessions", methods=["GET"]) # not yet tested
def monitoring_sessions():
    """Return active sessions. Teacher/monitoring use. No auth for brevity; add auth in production."""
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, nis, room, grade, class, started_at FROM sessions WHERE active = true")
                rows = cur.fetchall()
                return jsonify({"ok": True, "active_sessions": rows}), 200
    finally:
        put_conn(conn)

@app.route("/teacher/token/create", methods=["GET", "POST"]) # not yet
def teacher_create_token():
    """
    { "token": "ABCDE", "room": "01", "expires_in_minutes": 5 }
    """
    req = request.get_json(force=True)
    token = ''.join(random.choices(string.ascii_uppercase, k=5))
    room = req.get("room")
    mins = int(req.get("expires_in_minutes", 5))
    if not (token and room):
        return jsonify({"ok": False, "error": "missing"}), 400

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=mins)
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO tokens(token, room, expires_at) VALUES (%s, %s, %s) ON CONFLICT (token) DO UPDATE SET room=EXCLUDED.room, expires_at=EXCLUDED.expires_at", (token, room, expires_at))
                return jsonify({"ok": True, "token": token, "expires_at": expires_at.isoformat()}), 200
    finally:
        put_conn(conn)

@app.route("/teacher/token/", methods=["POST"]) # not yet
def teacher_list_tokens():
    """List all tokens. Requires room; add auth in production."""
    req = request.get_json(force=True)
    room = req.get("room")
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT token, room, expires_at FROM tokens ORDER BY expires_at DESC")
                rows = cur.fetchall()
                return jsonify({"ok": True, "tokens": rows}), 200
    finally:
        put_conn(conn)

@app.route("/admin/cleanup/tokens") # done
def admin_cleanup_tokens():
    """Cleanup expired tokens."""
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM tokens WHERE expires_at < now()")
                return jsonify({"ok": True}), 200
    finally:
        put_conn(conn)
        
@app.route("/admin/cleanup/sessions") # done
def admin_cleanup_sessions():
    """Cleanup finished sessions if indicates False."""
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM sessions WHERE active = false")
                return jsonify({"ok": True}), 200
    finally:
        put_conn(conn)

# Add other teacher utilities as needed:
# - upload exam forms
# - bulk insert students
# - revoke token
# - monitoring with websocket (not implemented here)

if __name__ == "__main__":
    # Simple dev server. Use gunicorn/uvicorn for production.
    from datetime import timedelta
    app.run(host="0.0.0.0", port=PORT)
