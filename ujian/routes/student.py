from flask import Blueprint, request, jsonify, render_template
from db import db_cursor
import hashlib, uuid, json

#url = '/' + hashlib.sha512(uuid.uuid4().hex.encode()).hexdigest()
student_bp = Blueprint("student", __name__, url_prefix="/student")


@student_bp.route("/", methods=["GET", "POST"])  # directed to here
def examLoginPage():
    if request.method != "POST":
        rooms = [{"id": 1, "name": "Ruang 1"}, {"id": 2, "name": "Ruang 2"}, {"id": 3, "name": "Ruang 3"}]
        return render_template("studentlogin.html", rooms=rooms)

    req = request.get_json(force=True)
    token = req.get("token")
    room = req.get("room")
    nis = req.get("nis")
    if not (token and room and nis):
        return jsonify({"ok": False, "error": "missing token/room/nis"}), 400

    with db_cursor() as (conn, cur):
        # Check the token expiry and retrieve token metadata (room may be stored in `room` or legacy `token_type`)
        cur.execute("SELECT token, token_type, room, expires_at FROM tokens WHERE token = %s AND expires_at > NOW()", (token,))
        row = cur.fetchone()
        if not row:
            return jsonify({"status": 404, "message": f"Token {token} not found or expired."}), 404

        # token may store room in either `room` or older `token_type` field; prefer `room` column
        a, token_type, token_room, _ = row
        token_room_val = token_room if token_room else token_type
        if token_room_val != room:
            return jsonify({"status": 403, "message": f"Token {token} is not valid for room {room}."}), 403


        cur.execute("SELECT * FROM rooms WHERE nis = %s AND room = %s", (nis, room))
        if not cur.fetchone():
            return jsonify({"status": 404, "message": f"Student with NIS {nis} not found in room {room}."}), 404

        # Check the existing active session
        cur.execute("SELECT * FROM sessions WHERE nis = %s AND active = TRUE", (nis,))
        if cur.fetchone():
            return jsonify({"status": 409, "message": f"Student with NIS {nis} already has an active session."}), 409

        seed = str(uuid.uuid4()).replace("-", "")
        combined = ":".join(str([nis, room, token, seed]))
        combined_hash = hashlib.sha512(combined.encode("utf-8")).hexdigest()
        special_key = seed[:4] + combined_hash[:4]

        cur.execute(
            "INSERT INTO sessions (session_hash, nis, seed, started_at, active, special_key) VALUES (%s, %s, %s, NOW(), %s, %s)",
            (combined_hash, nis, seed, True, special_key),
        )

        return jsonify({"status": 200, "message": "Authorized", "exam-hash": combined_hash, "seed": seed, "special-key": special_key}), 200


@student_bp.route("/exam", methods=["GET", "POST"])  # add : embeded json output
def examDo():
    if request.method == "GET":
        return render_template("examsession.html")
    
    if request.method != "POST":
        req = request.get_json(force=True)
        session_hash = req.get("hash")
        nis = req.get("nis")

        if not (session_hash and nis):
            return jsonify({"ok": False, "error": "missing"}), 400

        with db_cursor() as (conn, cur):
            # validate active session
            cur.execute(
                "SELECT 1 FROM sessions WHERE session_hash = %s AND nis = %s AND active = TRUE",
                (session_hash, nis),
            )
            if not cur.fetchone():
                return jsonify({"status": 404, "message": "Exam session not found"}), 404

            # find student's grade (try common column names)
            cur.execute("SELECT grade FROM students WHERE nis = %s", (nis,))
            row = cur.fetchone()
            grade = row[0] if row else None

            if not grade:
                cur.execute("SELECT class FROM students WHERE nis = %s", (nis,))
                row = cur.fetchone()
                grade = row[0] if row else None

            if not grade:
                return jsonify({"status": 404, "message": f"Grade not found for student {nis}"}), 404

            # fetch all forms for the grade and embed JSON payloads
            cur.execute("SELECT subject, payload FROM exam_forms WHERE grade = %s", (grade,))
            rows = cur.fetchall()

            forms = {}
            for subject, payload in rows:
                try:
                    # payload may already be a dict (jsonb) or a JSON string
                    if isinstance(payload, (str, bytes)):
                        data = json.loads(payload)
                    else:
                        data = payload
                except Exception:
                    # fallback: return raw payload if parsing fails
                    data = payload
                forms[subject] = data

            return jsonify({"status": 200, "grade": grade, "forms": forms}), 200
    return jsonify({"ok": False, "message": "Method not allowed."}), 405

@student_bp.route("/finish", methods=["POST"])  # done
def examFinish():
    """
    { "hash": "...", "nis" : "2***"}
    """
    req = request.get_json(force=True)
    session_hash = req.get("hash")
    nis = req.get("nis")

    if not (session_hash and nis):
        return jsonify({"ok": False, "error": "missing"}), 400

    with db_cursor() as (conn, cur):
        cur.execute("SELECT * FROM sessions WHERE session_hash = %s AND nis = %s", (session_hash, nis))
        if not cur.fetchone():
            return jsonify({"status": 404, "message": "Exam session not found"}), 404

        cur.execute("UPDATE sessions SET active = FALSE WHERE session_hash = %s AND nis = %s", (session_hash, nis))

        return jsonify({"status": 200, "message": "Exam finished"}), 200
