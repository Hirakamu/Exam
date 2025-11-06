from flask import Blueprint, request, jsonify, render_template
import hashlib, uuid

url = '/' + hashlib.sha512(uuid.uuid4().hex.encode()).hexdigest()
proctor_bp = Blueprint("proctor", __name__, url_prefix=url)

@proctor_bp.route("/", methods=["GET", "POST"]) # proctor login page
def proctorLoginPage():
    if request.method == 'GET':
        rooms = [{"id": 1, "name": "Ruang 1"}, {"id": 2, "name": "Ruang 2"}, {"id": 3, "name": "Ruang 3"}]
        return render_template("proctorlogin.html", rooms=rooms)
    if request.method == 'POST':
        return jsonify({"ok": True, "message": "Logged in"}), 200
    return jsonify({"ok": False, "message": "Method not allowed."}), 405
