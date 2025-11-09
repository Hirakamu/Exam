def run_server():
    from app import create_app
    create_app().run(host="0.0.0.0", port=5000, debug=False)
def initStudents():
    
    from config import STUDENTSJSON
    from db import getDB, putDB
    import os
    from pathlib import Path

    src = Path(STUDENTSJSON)

    if not src.exists():
        raise FileNotFoundError(f"students file not found: {STUDENTSJSON}")

    with src.open("r", encoding="utf-8") as f:
        students_data = json.load(f)

    conn = getDB()
    inserted = 0
    try:
        with conn:
            with conn.cursor() as cur:
                for student in students_data:
                    try:
                        sid = student.get("student_id") or student.get("nis") or student.get("id")
                        name = student.get("name") or student.get("nama") or ""
                        grade = student.get("grade") or None
                        class_ = student.get("class") or None
                        if sid is None:
                            logger.warning("Skipping student with no id: %s", student)
                            continue
                        cur.execute(
                            "INSERT INTO students (nis, name, grade, class) VALUES (%s, %s, %s, %s) ON CONFLICT (nis) DO NOTHING",
                            (sid, name, grade, class_),
                        )
                        inserted += cur.rowcount
                    except Exception:
                        logger.exception("Failed to insert student record: %s", student)
                        continue
    finally:
        putDB(conn)
    return {"inserted": inserted, "total": len(students_data)}
def initTeachers():
    
    from config import SCHOOLJSON
    from db import getDB, putDB
    import json, os
    
    with open(SCHOOLJSON, "r") as f:
        data = json.load(f)

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
def generateRoutes():
    
    from config import ROUTESJSON, ROOT, FULL_PREFIX
    import qrcode, os, uuid
    
    studenturl = '/' + uuid.uuid4().hex[:8]
    teacherurl = '/' + uuid.uuid4().hex[:8]

    with open(ROUTESJSON, "r") as f:
        routes = json.load(f)
    
    # ensure qrcode output directory exists
    qr_dir = os.path.join(ROOT, 'data', 'qrcodes')
    os.makedirs(qr_dir, exist_ok=True)

    studentimg = qrcode.make(FULL_PREFIX + routes['student_prefix'])
    student_path = os.path.join(qr_dir, 'student_qr.png')
    with open(student_path, "wb") as f:
        studentimg.save(f)

    teacherimg = qrcode.make(FULL_PREFIX + routes['teacher_prefix'])
    teacher_path = os.path.join(qr_dir, 'teacher_qr.png')
    with open(teacher_path, "wb") as f:
        teacherimg.save(f)
        
    with open(ROUTESJSON, "w") as f:
        json.dump({
            "student": studenturl,
            "teacher": teacherurl
        }, f, indent=2)

    return {
        'student_url': studenturl,
        'teacher_url': teacherurl
    }

import argparse, json, sys, logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(prog="hiraform", description="Hira Form System CLI")
sub = parser.add_subparsers(dest="cmd", required=True)

p_students = sub.add_parser("init-students", help="Initialize students from JSON files")
p_teachers = sub.add_parser("init-teachers", help="Initialize teachers from JSON files")
p_run_server = sub.add_parser("run-server", help="Run the Flask development server for debugging")
p_generate_routes = sub.add_parser("generate-routes", help="Generate new random routes for student and teacher access")

args = parser.parse_args()

setup_actions = {
    "init-students": initStudents,
    "run-server": run_server,
    "init-teachers": initTeachers,
    "generate-routes": generateRoutes,
}

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