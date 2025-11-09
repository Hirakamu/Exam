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

import logging, os, yaml, json, sys, atexit
from db import close_db_pool
from routes.student import bp as student_bp
from routes.teacher import bp as teacher_bp
from flask import jsonify, request, Flask
from flask_cors import CORS
from config import APP_NAME, APP_VERSION, ROOT, ROUTESJSON

# ---------------------------- APP

def create_app():
    app = Flask(APP_NAME+' '+APP_VERSION, template_folder=os.path.join(ROOT, "htmls"))
    CORS(app)
    with open(ROUTESJSON, "r") as f:
        config = json.load(f)
    app.register_blueprint(student_bp, url_prefix=config.get('student'))
    app.register_blueprint(teacher_bp, url_prefix=config.get('teacher'))

    atexit.register(close_db_pool)

    from functools import lru_cache
    @lru_cache(maxsize=128)
    @app.route('/favicon.ico')
    def favicon():
        return '', 200

    @app.route('/')
    def nonono():
        return jsonify({"ok":"false", "message":"Gunakan link yang lain"})

    @app.route('/adminsgetlinks', methods=['GET'])
    def getLinks():
        baseUrl = request.host_url.rstrip('/')
        return jsonify({
            "ok": True,
            "teacher-url": baseUrl + app.url_map._rules_by_endpoint['teacher.teacherLogin'][0].rule,
            "student-url": baseUrl + app.url_map._rules_by_endpoint['student.examLogin'][0].rule
        })

    return app