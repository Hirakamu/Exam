from flask import Blueprint, request, jsonify, render_template
from db import db_cursor
import hashlib, uuid, json
import uuid
import logging
from zipfile import Path
from flask import jsonify, request, render_template, send_from_directory
from psycopg2 import pool, sql
import psycopg2.extras as extras
import json
import sys
import os
from functools import lru_cache
import yaml
import hashlib
import atexit
import random
import string
from datetime import datetime, time, timezone, timedelta
from contextlib import contextmanager
from typing import Iterator, Tuple, Any, Dict, Optional
from flask_cors import CORS
import argparse
from pathlib import Path
from flask import Flask
from flask_cors import CORS
import logging, os, yaml, json
from psycopg2 import pool

#url = '/' + hashlib.sha512(uuid.uuid4().hex.encode()).hexdigest()
teacher_bp = Blueprint("teacher", __name__, url_prefix="/teacher")

@teacher_bp.route("/", methods=["GET", "POST"]) # teacher login page
def teacherLogin():
    if request.method == 'GET':
        teachers = []
        with db_cursor() as (conn, cur):
            cur.execute("SELECT id, name FROM teachers")
            rows = cur.fetchall()
            for row in rows:
                teachers.append({"id": row[0], "name": row[1]})
        teachers.sort(key=lambda x: x["name"])
        return render_template("teacherlogin.html", teacher=teachers)
    
    
    if request.method == 'POST':
        req = request.get_json(force=True)
        teacher = req.get("teacher")
        token = req.get("token")

        if not token or not teacher:
                return jsonify({"ok": False, "message": "Coba lagi."}), 400

        try:
            with db_cursor() as (conn, cur):
                cur.execute("SELECT 1 FROM tokens WHERE token_type=%s AND token=%s", ("teacher", token))
                if not cur.fetchone():
                    return jsonify({"ok": False, "message": "Token tidak valid"}), 401
                
                cur.execute("SELECT 1 FROM tokens WHERE token_type=%s AND token=%s AND expires_at > NOW()", ("teacher", token))
                if not cur.fetchone():
                    return jsonify({"ok": False, "message": "Token telah kedaluwarsa"}), 401

                cur.execute("SELECT name FROM teachers WHERE id=%s", (teacher,))
                row = cur.fetchone()
                if not row:
                    return jsonify({"ok": False, "message": "Guru tidak ditemukan"}), 404
                namet = row[0]
                
                seed = str(uuid.uuid4()).replace("-", "")
                combined = ":".join(str([token, seed, teacher, namet]))
                combined_hash = hashlib.sha512(combined.encode("utf-8")).hexdigest()
                # 8 letter special key
                specletter = seed[:4] + combined_hash[:4]

                return jsonify({"ok": True, "message": f"Login berhasil. Halo {namet}", "hash": combined_hash, "name": namet, "special-key": specletter}), 200
        except Exception as e:
            return jsonify({"ok": False, "message": f"Kesalahan server: {e}"}), 500
    return jsonify({"ok": False, "message": "Method not allowed."}), 405

@teacher_bp.route("/dashboard", methods=['GET','POST']) # teacher dashboard
def teacherDashboard():
    if request.method == 'GET':
        return render_template("teacherdashboard.html"), 200
        return """
        <!DOCTYPE html>
        <html>
        <head>
        <title>Dashboard Guru</title>
        </head>
        <body style="display:flex;justify-content:center;align-items:center;height:100vh;margin:0;font-family:system-ui,sans-serif;background:#fafafa;color:#555;">
            <h1 style="font-size:2rem;font-weight:500;letter-spacing:0.5px;color:#666;">Loading dashboard…</h1>
            <script>
            async function loadDashboard() {
                const payload = {
                    hash: localStorage.getItem("hash"),
                    nameT: localStorage.getItem("nameT"),
                    "special-letter": localStorage.getItem("special-letter")
                };
                
                const res = await fetch("./dashboard", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                
                if (res.ok) {
                    const html = await res.text();
                    document.open();
                    document.write(html);
                    document.close();
                } else {
                    const stored = {
                        hash: localStorage.getItem("hash") || "(none)",
                        nameT: localStorage.getItem("nameT") || "(none)",
                        specialLetter: localStorage.getItem("special-letter") || "(none)"
                    };
                    document.body.innerHTML = `
                        <div style="
                            font-family:system-ui,Arial,sans-serif;
                            color:#666;
                            text-align:center;
                            font-size:0.8rem;
                            line-height:1.4;
                            font-weight:500;
                        ">
                            <p style="margin-bottom:0.5em;font-size:2rem;">Gagal membuka dashboard</p>
                            <p style="margin-top:0.5em;margin-bottom:1em;font-size:1rem;">Laporkan kepada administrator.</p>
                            <div style="display:inline-block;text-align:center;">
                                <div style="word-break:break-all;overflow-wrap:break-word;max-width:460px;"><strong style="color:#444;">Hash:</strong><br> ${stored.hash}</div>
                                <div><strong style="color:#444;">Guru:</strong> ${stored.nameT}</div>
                                <div><strong style="color:#444;">Special key:</strong> ${stored.specialLetter}</div>
                            </div>
                        </div>
                    `;
                }
            }
            loadDashboard();
            </script>
        </body>
        </html>
        """
    
    if request.method == 'POST':
        resources = [
            {
                "name": "Matematika",
                "data": {
                    "stats": [
                        {
                            "title": "Siswa Belum Mengerjakan",
                            "value": 280
                        },
                        {
                            "title": "Siswa Mengerjakan",
                            "value": 20
                        }
                    ],
                    "gradeData": {
                        "X": {
                            "rooms": [
                                "E1",
                                "E2",
                                "E3",
                                "E4",
                                "E5",
                                "E6",
                                "E7",
                                "E8",
                                "E9"
                            ],
                            "submitted": [
                                "E1",
                                "E2",
                                "E3",
                                "E4",
                                "E5",
                                "E6",
                                "E7",
                                "E8",
                                "E9"
                            ]
                        },
                        "XI": {
                            "rooms": [
                                "F1",
                                "F2",
                                "F3",
                                "F4",
                                "F5",
                                "F6",
                                "F7",
                                "F8",
                                "F9"
                            ],
                            "submitted": [
                                "F1",
                                "F2",
                                "F3",
                                "F4",
                                "F5",
                                "F6",
                                "F7",
                                "F8",
                                "F9"
                            ]
                        },
                        "XII": {
                            "rooms": [
                                "F1",
                                "F2",
                                "F3",
                                "F4",
                                "F5",
                                "F6",
                                "F7",
                                "F8"
                            ],
                            "submitted": [
                                "F1"
                            ]
                        }
                    }
                }
            },
            {
                "name": "Bahasa Inggris",
                "data": {
                    "stats": [
                        {
                            "title": "Siswa Belum Mengerjakan",
                            "value": 200
                        },
                        {
                            "title": "Siswa Mengerjakan",
                            "value": 100
                        }
                    ],
                    "gradeData": {
                        "X": {
                            "rooms": [
                                "E1",
                                "E2",
                                "E3",
                                "E4",
                                "E5",
                                "E6",
                                "E7",
                                "E8",
                                "E9"
                            ],
                            "submitted": [
                                "E1",
                                "E2",
                                "E3",
                                "E4",
                                "E5",
                                "E6",
                                "E7",
                                "E8",
                                "E9"
                            ]
                        },
                        "XI": {
                            "rooms": [
                                "F1",
                                "F2",
                                "F3",
                                "F4",
                                "F5",
                                "F6",
                                "F7",
                                "F8",
                                "F9"
                            ],
                            "submitted": [
                                "F1",
                                "F2",
                                "F3",
                                "F4",
                                "F5"
                            ]
                        },
                        "XII": {
                            "rooms": [
                                "F1",
                                "F2",
                                "F3",
                                "F4",
                                "F5",
                                "F6",
                                "F7",
                                "F8"
                            ],
                            "submitted": [
                                "F1"
                            ]
                        }
                    }
                }
            }
        ]
        
        return jsonify(resources), 200
    
    return jsonify({"ok": False, "message": "Method not allowed."}), 405

@teacher_bp.route("/dashboard/<subject>/<grade>")
def teacherSubjectGrade(subject, grade):
    """
    Get list of classes for a specific subject and grade
    """
    # Produce randomized students_submitted for each class
    total_questions = 50
    prefixes = ["2324100", "2425100", "2526100"]
    used_nis = set()

    classes = [
        {"class": "E1", "total_students": 30},
        {"class": "E2", "total_students": 32},
        {"class": "E3", "total_students": 28},
        {"class": "E4", "total_students": 28},
        {"class": "E5", "total_students": 28},
        {"class": "E6", "total_students": 28},
        {"class": "E7", "total_students": 28},
        {"class": "E8", "total_students": 28},
        {"class": "E9", "total_students": 28},
    ]

    # Base submission time; each student's submission_time will be within 2 hours from here
    base_time = datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc)

    data = []
    for cls in classes:
        # number of students who submitted for this class (1..min(10, total_students))
        submitted_count = random.randint(1, min(random.randint(1, cls["total_students"]), cls["total_students"]))
        students = []
        for j in range(submitted_count):
            # generate mostly-unique NIS for this dataset
            attempts = 0
            while True:
                prefix = random.choice(prefixes)
                suffix = f"{random.randint(0, 99):02d}"
                nis_candidate = prefix + suffix
                if nis_candidate not in used_nis:
                    used_nis.add(nis_candidate)
                    nis = nis_candidate
                    break
                attempts += 1
                if attempts > 200:
                    nis = f"{prefix}{suffix}{j}"
                    break

            correct = random.randint(0, total_questions)
            offset_seconds = random.randint(0, 2 * 3600)
            submission_time = (base_time + timedelta(seconds=offset_seconds)).isoformat()
            # calculate percentage score (guard against division by zero)
            score_percentage = round((correct / total_questions) * 100, 2) if total_questions else 0.0

            students.append({
                "nis": nis,
                "name": f"Student {cls['class']}-{j+1}",
                "correct_answers": correct,
                "total_questions": total_questions,
                "score_percentage": score_percentage,
                "submission_time": submission_time
            })

        data.append({
            "class": cls["class"],
            "total_students": cls["total_students"],
            "students_submitted": students
        })

    return jsonify(data), 200

@teacher_bp.route("/dashboard/<subject>/<grade>/<classe>")
def teacherSubjectGradeClass(subject, grade, classe):
    """
    Get list of students for a specific subject, grade, and class
    """
    # Generate a randomized list of students (indices 0..50 inclusive)
    total_questions = 50
    entries_count = 50
    prefixes = ["2324100", "2425100", "2526100"]
    used_nis = set()
    data = []

    # Base submission time (example reference); submission_time will be within a 2-hour window
    base_time = datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc)

    for i in range(entries_count):
        # create a (mostly) unique NIS using the given prefixes and a two-digit suffix
        attempts = 0
        while True:
            prefix = random.choice(prefixes)
            suffix = f"{random.randint(0, 99):02d}"
            nis_candidate = prefix + suffix
            if nis_candidate not in used_nis:
                used_nis.add(nis_candidate)
                nis = nis_candidate
                break
            attempts += 1
            if attempts > 200:
                nis = f"{prefix}{suffix}{i}"
                break

        correct = random.randint(0, total_questions)
        offset_seconds = random.randint(0, 2 * 3600)
        submission_time = base_time + timedelta(seconds=offset_seconds)
        # calculate percentage score (guard against division by zero)
        score_percentage = round((correct / total_questions) * 100, 2) if total_questions else 0.0

        data.append({
            "nis": nis,
            "name": f"Student {i+1}",
            "correct_answers": correct,
            "total_questions": total_questions,
            "score_percentage": score_percentage,
            "submission_time": submission_time.isoformat()
        })

    return jsonify(data), 200

@teacher_bp.route("/tokens", methods=["POST"]) # need authentication
def teacherToken():
    """
    { "all":"True", "hash":"1a2b3c..." } -> { "ok":"True", "tokens":[...] }
    """
    args = request.get_json(force=False)
    all_tokens = args.get("all", "False") == "True"
    with db_cursor() as (conn, cur):
        if all_tokens:
            cur.execute("SELECT token, room, expires_at FROM tokens")
        else:
            cur.execute("SELECT token, room, expires_at FROM tokens WHERE expires_at > NOW()")
        tokens = [{"token": row[0], "room": row[1], "expires_at": row[2].isoformat() if row[2] else None} for row in cur.fetchall()]
        return jsonify({"ok": True, "tokens": tokens}), 200

@teacher_bp.route("/tokens/create", methods=["POST"]) # need authentication
def teacherTokenCreate():
    """
    { "room": "01", "expires_in_minutes": 5 }
    """
    req = request.get_json(force=True)
    room = req.get("room")
    mins = 5
    if not room:
        return jsonify({"ok": False, "error": "missing room"}), 400

    token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=mins)
    with db_cursor() as (conn, cur):
        cur.execute(
            "INSERT INTO tokens(token, room, expires_at) VALUES (%s, %s, %s) ON CONFLICT (token) DO UPDATE SET room=EXCLUDED.room, expires_at=EXCLUDED.expires_at",
            (token, room, expires_at),
        )
        return jsonify({"ok": True, "token": token, "expires_at": expires_at.isoformat()}), 200

@teacher_bp.route("/tokens/cleanup", methods=["POST"]) # need authentication
def teacherTokenCleanup():
    args = request.get_json(force=False)
    force = bool(args.get("force", False)) if args else False
    with db_cursor() as (conn, cur):
        if force:
            cur.execute("DELETE FROM tokens")
        else:
            cur.execute("DELETE FROM tokens WHERE expires_at <= NOW()")
        deleted_count = cur.rowcount
        return jsonify({"force": force, "deleted": deleted_count}), 200

@teacher_bp.route("/sessions/cleanup", methods=["POST"]) # need authentication
def teacherSessionCleanup():
    args = request.get_json(force=False)
    force = bool(args.get("force", False)) if args else False
    with db_cursor() as (conn, cur):
        if force:
            cur.execute("DELETE FROM sessions")
        else:
            cur.execute("DELETE FROM sessions WHERE active = FALSE")
        deleted_count = cur.rowcount
        return jsonify({"force": force, "deleted": deleted_count}), 200

@teacher_bp.route("/requestteacherjob", methods=["POST"])
def requestTeacher():
    req = request.get_json(force=True)
    name = req.get("name")
    
    if not name:
        return jsonify({"ok": False, "error": "missing name"}), 400
    
    with db_cursor() as (conn, cur):
        cur.execute("SELECT 1 FROM teachers WHERE name = %s", (name,))
        data = cur.fetchone()
        if not data:
            return jsonify({"ok": False, "message": "Guru tidak terdaftar."}), 404


        