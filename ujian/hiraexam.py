"""
------------------ Hira Form System ------------------
- Single app built using flask to serve API endpoints
  for student and teachers to manage form and keep
  centralized data.
- Uses PostgreSQL as database backend.
- Configurable using config.yaml file.
------------------------------------------------------

"""

from __future__ import annotations
from flask import jsonify
from db import getDB, putDB, close_db_pool, config
from psycopg2 import sql
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

app.register_blueprint(student_bp)
app.register_blueprint(teacher_bp)
app.register_blueprint(proctor_bp)
teacherUrl = teacher_bp.url_prefix
studentUrl = student_bp.url_prefix
proctorUrl = proctor_bp.url_prefix

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
def initStudents() -> bool: # used if new students are added
    baseDir = os.path.join(os.path.dirname(__file__), "data", "siswa")
    if not os.path.isdir(baseDir):
        logger.warning("Students base directory %s not found", baseDir)
        return False

    jsonFiles = [f for f in os.listdir(baseDir) if f.endswith(".json")]
    conn = getDB()
    try:
        with conn:
            with conn.cursor() as cur:
                for fileName in jsonFiles:
                    filePath = os.path.join(baseDir, fileName)
                    with open(filePath, "r") as f:
                        data = json.load(f)

                    grade = data.get("grade")
                    sections = data.get("sections", {})
                    if not grade:
                        logger.warning("Skipping %s: missing grade", filePath)
                        continue
                    cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(grade)))
                    cur.execute(sql.SQL(
                        """
                        CREATE TABLE {} (
                            nis VARCHAR(20),
                            name VARCHAR(100),
                            class VARCHAR(10)
                        )
                        """
                    ).format(sql.Identifier(grade)))
                    for section, students in sections.items():
                        for s in students:
                            cur.execute(
                                sql.SQL("INSERT INTO {} (nis, name, class) VALUES (%s, %s, %s)").format(sql.Identifier(grade)),
                                (s.get("nis"), s.get("name"), s.get("class") if s.get("class") else section),
                            )
        return True
    finally:
        putDB(conn)
def importForms():
    base_dir = os.path.join(ROOT, "data", "exam", "safeexam")
    forms = []

    if not os.path.isdir(base_dir):
        logger.warning("Safe exam directory not found: %s", base_dir)
        return forms

    for dirpath, dirnames, filenames in os.walk(base_dir):
        for fname in filenames:
            file_path = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(file_path, base_dir)
            try:
                if fname.lower().endswith(".json"):
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = json.load(f)
                elif fname.lower().endswith((".yml", ".yaml")):
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = yaml.safe_load(f)
                else:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()

                # on successful read append the record
                forms.append({"path": rel_path, "name": fname, "content": content, "error": None})

            except Exception:
                logger.exception("Failed to read file while scanning safeexam: %s", file_path)
                # fatal: exit the process on any error during scanning
                sys.exit(1)

    logger.info("Scanned %d items in %s", len(forms), base_dir)

    # Bulk insert / upsert the scanned forms in a single transaction
    if not forms:
        return forms

    conn = getDB()
    try:
        with conn:
            with conn.cursor() as cur:
                rows = []
                for f in forms:
                    # Determine grade from the first path component under safeexam
                    parts = os.path.normpath(f["path"]).split(os.sep)
                    grade = parts[0] if parts and parts[0] else None
                    if not grade:
                        logger.warning("Skipping %s: cannot determine grade from path", f["path"])
                        continue

                    # subject from filename (without extension)
                    subject = os.path.splitext(f["name"])[0]

                    # payload should be JSON-serializable for jsonb
                    if f["content"] is None:
                        # skip entries that failed to read
                        logger.warning("Skipping %s: content is None (read failed)", f["path"])
                        continue
                    elif isinstance(f["content"], (dict, list)):
                        payload = f["content"]
                    else:
                        # wrap raw text into an object so it's valid JSON
                        payload = {"content": str(f["content"])}

                    # store as JSON text and cast to jsonb in SQL
                    payload_text = json.dumps(payload, ensure_ascii=False)
                    rows.append((grade, subject, payload_text))

                try:
                    # Delete any existing rows for these (grade,subject) pairs so we fully replace
                    pairs = [(r[0], r[1]) for r in rows]
                    if pairs:
                        try:
                            cur.execute("DELETE FROM exam_forms WHERE (grade, subject) IN %s", (tuple(pairs),))
                        except Exception:
                            logger.exception("Failed to delete existing exam_forms before insert")
                            # fatal: exit the process if we cannot remove existing rows
                            sys.exit(1)

                    cur.executemany(
                        "INSERT INTO exam_forms (grade, subject, payload) VALUES (%s, %s, %s::jsonb)",
                        rows,
                    )
                except Exception:
                    logger.exception("Failed to bulk upsert forms into database")
                    # fatal: exit the process on DB errors during import
                    sys.exit(1)
    finally:
        putDB(conn)

    return forms

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
    return jsonify({
        "ok": True,
        "teacher-url": teacherUrl,
        "student-url": studentUrl,
        "proctor-url": proctorUrl
    })

@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception("Unhandled exception in request")
    return jsonify({"ok": False, "error": str(e)}), 500

# ------------------------------------------------------------ CLI
if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="hiraform", description="Hira Form System CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_import = sub.add_parser("import-forms", help="Import all exam forms into database")
    p_students = sub.add_parser("init-students", help="Initialize students from JSON files")
    p_run_server = sub.add_parser("run-server", help="Run the Flask development server for debugging")

    args = parser.parse_args()

    setup_actions = {
        "import-forms": importForms,
        "init-students": initStudents,
        "run-server": app.run(host="0.0.0.0")
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