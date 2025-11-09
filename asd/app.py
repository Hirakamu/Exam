# app.py (aggressive ban)
import sqlite3, time
from jwt import encode, decode  # explicit imports so static analyzers see encode/decode
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, disconnect

DB = "exam.db"
SECRET = "replace-with-secure-random-secret"
BAN_THRESHOLD = 1  # immediate ban on first violation

def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS bans (
        user_id TEXT PRIMARY KEY,
        violations INTEGER DEFAULT 0,
        banned_at INTEGER,
        reason TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS appeals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        appeal_text TEXT,
        created_at INTEGER DEFAULT (strftime('%s','now')),
        resolved INTEGER DEFAULT 0
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS tokens_revoked (
        token TEXT PRIMARY KEY,
        revoked_at INTEGER
    )""")
    conn.commit()
    conn.close()

init_db()
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

def get_db():
    return sqlite3.connect(DB, check_same_thread=False)

def token_revoked(token):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT 1 FROM tokens_revoked WHERE token = ?", (token,))
    r = cur.fetchone(); conn.close()
    return bool(r)

def revoke_token(token):
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO tokens_revoked(token, revoked_at) VALUES(?,?)", (token, int(time.time())))
    conn.commit(); conn.close()

@app.route('/')
def index():
    return "Aggressive exam server."
@app.route('/exam/<user_id>')
def exam_page(user_id):
    # In production use signed tokens; here we produce a simple JWT for demo
    payload = {"user_id": user_id, "iat": int(time.time())}
    # use explicit encode import; PyJWT v1 may return bytes, v2 returns str
    token = encode(payload, SECRET, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return render_template('exam.html', user_id=user_id, token=token)
    return render_template('exam.html', user_id=user_id, token=token)

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

@app.route('/admin/unban', methods=['POST'])
def unban():
    data = request.json or {}
    user_id = data.get("user_id")
    if not user_id:
        return {"ok": False, "error": "user_id required"}, 400
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM bans WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    socketio.emit('unbanned', {'user_id': user_id}, room=user_id)
    return {"ok": True}
    token = request.args.get('token')
    try:
        data = decode(token, SECRET, algorithms=["HS256"])
        user_id = data.get('user_id')
    except Exception:
        return False  # reject connect
        data = jwt.decode(token, SECRET, algorithms=["HS256"])
        user_id = data.get('user_id')
    except Exception:
        return False  # reject connect

    # reject if token revoked
    if token_revoked(token):
        return False

    # if banned, join room and notify (allow to send appeal)
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT reason FROM bans WHERE user_id = ?", (user_id,))
    r = cur.fetchone()
    if r:
        join_room(user_id)
        emit('ban', {'reason': r[0] or 'banned'})
        return

    # otherwise join room named user_id for later targeted messages
    join_room(user_id)
    # attach token and user_id to socket session via emit handshake
    emit('connected', {'user_id': user_id})

@socketio.on('violation')
def on_violation(payload):
    # aggressive: ban immediately
    token = payload.get('token')
    user_id = payload.get('user_id')
    reason = payload.get('reason', 'violation')
    if not user_id:
        return
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT violations FROM bans WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row:
        violations = row[0] + 1
        cur.execute("UPDATE bans SET violations = ? WHERE user_id = ?", (violations, user_id))
    else:
        violations = 1
        cur.execute("INSERT INTO bans(user_id, violations) VALUES(?,?)", (user_id, violations))
    conn.commit()
    if violations >= BAN_THRESHOLD:
        cur.execute("UPDATE bans SET banned_at = ?, reason = ? WHERE user_id = ?", (int(time.time()), reason, user_id))
        conn.commit()
        # revoke token if provided
        if token:
            revoke_token(token)
        # emit ban to the user's room so client shows overlay; keep socket open to accept appeal
        socketio.emit('ban', {'reason': reason}, room=user_id)
        socketio.emit('ban_notice', {'user_id': user_id, 'reason': reason, 'violations': violations}, room='admins')
    conn.close()

@socketio.on('appeal')
def on_appeal(payload):
    user_id = payload.get('user_id'); text = payload.get('text','')
    if not user_id: return
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO appeals (user_id, appeal_text) VALUES (?,?)", (user_id, text))
    conn.commit(); conn.close()
    socketio.emit('appeal_notice', {'user_id': user_id, 'text': text}, room='admins')
    emit('appeal_sent', {'ok': True})

@socketio.on('admin_unban')
def admin_unban(payload):
    user_id = payload.get('user_id')
    if not user_id: return
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM bans WHERE user_id = ?", (user_id,))
    conn.commit(); conn.close()
    socketio.emit('unbanned', {'user_id': user_id}, room=user_id)
    socketio.emit('unban_ack', {'user_id': user_id}, room='admins')

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
