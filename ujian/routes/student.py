from flask import Blueprint, request, jsonify, render_template
from db import db_cursor
import hashlib, uuid, json

#url = '/' + hashlib.sha512(uuid.uuid4().hex.encode()).hexdigest()
bp = Blueprint("student", __name__)


@bp.route("/", methods=["GET", "POST"])  # directed to here
def examLogin():
    if request.method != "POST":
        rooms = [{"id": 1, "name": "Ruang 1"}, {"id": 2, "name": "Ruang 2"}, {"id": 3, "name": "Ruang 3"}]
        return render_template("studentlogin.html", rooms=rooms)

    req = request.get_json(force=True)
    class_ = req.get("class")
    subject = req.get("subject")
    nis = req.get("nis")
    if not (class_ and subject and nis):
        return jsonify({"ok": False, "error": " Kelas atau NIS atau Mata Pelajaran tidak boleh kosong"}), 400

    with db_cursor() as (conn, cur):
        # check the student exists
        cur.execute("SELECT * FROM students WHERE nis = %s AND class = %s", (nis, class_))
        if not cur.fetchone():
            return jsonify({"status": 404, "message": f"Siswa dengan NIS {nis} tidak ditemukan dalam {class_}."}), 404

        # Check the student does not have an active session
        cur.execute("SELECT * FROM sessions WHERE nis = %s AND active = TRUE", (nis,))
        if cur.fetchone():
            return jsonify({"status": 409, "message": f"Siswa dengan NIS {nis} sudah memiliki sesi aktif."}), 409


        cur.execute("SELECT name FROM students WHERE nis = %s", (nis,))
        student_name = cur.fetchone()
        if student_name:
            student_name = student_name[0]
        else:
            student_name = "Unknown"

        seed = str(uuid.uuid4()).replace("-", "")
        combined = ":".join(str([nis, class_, student_name, subject, seed]))
        combined_hash = hashlib.sha512(combined.encode("utf-8")).hexdigest()
        special_key = seed[:4] + combined_hash[:4]
        
        cur.execute(
            "INSERT INTO sessions (session_hash, nis, seed, started_at, active, subject, special_key) VALUES (%s, %s, %s, NOW(), %s, %s, %s)",
            (combined_hash, nis, seed, True, subject, special_key),
        )

        return jsonify({"status": 200, "message": f"Akses diterima, Halo {student_name}", "exam-hash": combined_hash, "exam-seed": seed, "exam-special-key": special_key}), 200

@bp.route("/whoami", methods=["POST"])  # done
def whoAmI():
    """
    {"exam-id":"1001001"}
    """
    req = request.get_json(force=True)
    id = req.get("exam_id")
    if not id:
        return jsonify({"ok": False, "error": "missing exam_id"}), 400
    with db_cursor() as (conn, cur):
        cur.execute("SELECT name FROM students WHERE nis = %s", (id,))
        student = cur.fetchone()
        if not student:
            return jsonify({"ok": False, "error": "student not found"}), 404
        return jsonify({"ok": True, "name": student[0]}), 200

@bp.route("/exam", methods=["GET", "POST"])  # add : embeded json output
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

@bp.route("/finish", methods=["POST"])  # done
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
