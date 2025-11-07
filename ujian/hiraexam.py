"""
------------------ Hira Form System ------------------
- App built using flask to serve API endpoints
  for student and teachers to manage form and keep
  centralized data.
- Uses PostgreSQL as database backend.
- Configurable using config.yaml file.

Currently the app were hardcoded for SMAN 2 Cikarang Pusat
but can be adapted to other uses by changing the
configuration files and database schema as needed.
------------------------------------------------------
"""

from __future__ import annotations
from flask import jsonify, request
from db import getDB, putDB, close_db_pool, config
import sys
import atexit
import argparse
from flask import Flask
from flask_cors import CORS
import logging, os, yaml, json
from routes.student import student_bp
from routes.teacher import teacher_bp
from routes.proctor import proctor_bp

# ------------------------------------------------------------ INIT

ROOT = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__, template_folder=os.path.join(ROOT, "htmls"))
CORS(app)

def _load_file(rel_path: str, *, try_yaml_json: bool = False, required: bool = True):
    abs_path = os.path.join(ROOT, rel_path)
    if not os.path.exists(abs_path):
        if required:
            logger.fatal("Required file not found: %s", abs_path)
            sys.exit(1)
        else:
            logger.warning("Optional file not found: %s", abs_path)
            return None

    try:
        name = os.path.basename(abs_path).lower()
        if try_yaml_json or name.endswith('.json') or name.endswith('.yml') or name.endswith('.yaml'):
            with open(abs_path, 'r', encoding='utf-8') as f:
                # prefer json for .json, yaml otherwise (yaml can also parse json)
                if name.endswith('.json'):
                    return json.load(f)
                else:
                    return yaml.safe_load(f)
        else:
            with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
    except Exception:
        logger.exception("Failed to load file: %s", abs_path)
        if required:
            sys.exit(1)
        return None
def saveConfig() -> bool:
    try:
        with open(os.path.join(ROOT, "config.yaml"), "w") as f:
            yaml.safe_dump(config, f)
        return True
    except Exception:
        logger.exception("Failed to save config.yaml")
        return False
def initStudents():
    students_file = os.path.join(ROOT, "data", "students.json")
    students_data = _load_file(students_file, try_yaml_json=True)

    if not isinstance(students_data, list):
        raise ValueError("students.json must contain a list of student records")

    conn = getDB()
    inserted = 0
    try:
        with conn:
            with conn.cursor() as cur:
                for student in students_data:
                    try:
                        cur.execute(
                            "INSERT INTO students (student_id, name, grade) VALUES (%s, %s, %s) ON CONFLICT (student_id) DO NOTHING",
                            (student["student_id"], student["name"], student["grade"]),
                        )
                        inserted += cur.rowcount
                    except Exception:
                        logger.exception("Failed to insert student record: %s", student)
                        continue
    finally:
        putDB(conn)
    return {"inserted": inserted, "total": len(students_data)}
def initTeachers():
    teachers_file = os.path.join(ROOT, "data", "school.json")
    data = _load_file(teachers_file, try_yaml_json=True)

    if not isinstance(data, dict) or "guru" not in data or not isinstance(data["guru"], list):
        raise ValueError("school.json must contain a 'guru' list of teacher records")

    conn = getDB()
    inserted = 0
    try:
        with conn:
            with conn.cursor() as cur:
                for teacher in data["guru"]:
                    try:
                        tid = teacher["id"]
                        name = teacher.get("name", "")
                        job = teacher.get("subject", {})
                        job_json = json.dumps(job, ensure_ascii=False)
                        cur.execute(
                            "INSERT INTO teachers (id, name, job) VALUES (%s, %s, %s::json) "
                            "ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, job = EXCLUDED.job",
                            (tid, name, job_json),
                        )
                        inserted += cur.rowcount
                    except Exception:
                        logger.exception("Failed to insert teacher record: %s", teacher)
                        continue
                try:
                    cur.execute(
                        "SELECT setval(pg_get_serial_sequence('teachers','id'), coalesce((SELECT MAX(id) FROM teachers), 1), true);"
                    )
                except Exception:
                    logger.exception("Failed to sync teachers sequence")
    finally:
        putDB(conn)
    return {"inserted": inserted, "total": len(data["guru"])}

app.register_blueprint(student_bp)
app.register_blueprint(teacher_bp)
app.register_blueprint(proctor_bp)
teacherUrl = teacher_bp.url_prefix
studentUrl = student_bp.url_prefix
proctorUrl = proctor_bp.url_prefix

app_config = _load_file(os.path.join('data', 'config.yaml'), try_yaml_json=True)
school = _load_file(os.path.join('data', 'school.json'), try_yaml_json=True)
schedule = _load_file(os.path.join('data', 'exam', 'schedule.json'), try_yaml_json=True)

atexit.register(close_db_pool)
atexit.register(saveConfig)

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/')
def nonono():
    return jsonify({"ok":"false", "message":"Gunakan link yang lain"})

@app.route('/adminsgetlinks', methods=['GET'])
def getLinks():
    baseUrl = request.host_url.rstrip('/')
    return jsonify({
        "ok": True,
        "teacher-url": baseUrl + teacherUrl, # type: ignore
        "student-url": baseUrl + studentUrl, # type: ignore
        "proctor-url": baseUrl + proctorUrl  # type: ignore
    })

@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception("Unhandled exception in request")
    return jsonify({"ok": False, "error": str(e)}), 500

# ------------------------------------------------------------ CLI
if __name__ == "__main__":

    def run_server():
        print("teacher:", teacherUrl, "\nstudent:", studentUrl, "\nproctor:", proctorUrl)
        app.run(host="0.0.0.0", port=5000, debug=False)
        
    parser = argparse.ArgumentParser(prog="hiraform", description="Hira Form System CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_students = sub.add_parser("init-students", help="Initialize students from JSON files")
    p_teachers = sub.add_parser("init-teachers", help="Initialize teachers from JSON files")
    p_run_server = sub.add_parser("run-server", help="Run the Flask development server for debugging")

    args = parser.parse_args()

    setup_actions = {
        "init-students": initStudents,
        "run-server": run_server(),
        "init-teachers": initTeachers,
    }
    if args.cmd == "run-server":
        exit()

    func = setup_actions.get(args.cmd)
    if not func:
        parser.print_help()
        sys.exit(1)

    try:
        result = func()
        if isinstance(result, tuple):
            ok, val = result
            print(json.dumps({"ok": ok, "result": val}, indent=2))
        else:
            print(json.dumps({"ok": True, "result": result}, indent=2))
    except Exception as e:
        logger.exception("CLI execution failed")
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)