#!/usr/bin/env python3
"""
Generate safe exam JSONs by copying all files from
ujian/data/exam/teacher/* to ujian/data/exam/safeexam/* and removing
sensitive fields: `answer` and `point` in each question's `jawab` object.

Usage: run from repository root or call directly.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # ujian/
TEACHER_DIR = ROOT / "data" / "exam" / "teacher"
SAFE_DIR = ROOT / "data" / "exam" / "safeexam"

def sanitize_question(q):
    # q is a dict representing a question
    if not isinstance(q, dict):
        return q
    jawab = q.get("jawab")
    if isinstance(jawab, dict):
        # Remove 'answer' and 'point' keys if present
        jawab.pop("answer", None)
        jawab.pop("point", None)
        # If opsi exists, keep it intact
        q["jawab"] = jawab
    return q


def process_file(src: Path, dst: Path):
    try:
        with src.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to load {src}: {e}")
        return False

    # If data has 'field' which is a list of questions, sanitize each
    if isinstance(data, dict) and "field" in data and isinstance(data["field"], list):
        data["field"] = [sanitize_question(q) for q in data["field"]]
    else:
        # best-effort: walk and sanitize any nested questions if the structure differs
        pass

    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        with dst.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Failed to write {dst}: {e}")
        return False
    return True


def main():
    if not TEACHER_DIR.exists():
        print(f"Teacher directory not found: {TEACHER_DIR}")
        return 2
    SAFE_DIR.mkdir(parents=True, exist_ok=True)

    count = 0
    failed = 0
    for kelas in [p for p in TEACHER_DIR.iterdir() if p.is_dir()]:
        for src in sorted(kelas.glob("*.json")):
            rel = src.relative_to(TEACHER_DIR)
            dst = SAFE_DIR / rel
            ok = process_file(src, dst)
            if ok:
                count += 1
            else:
                failed += 1
    print(f"Processed: {count}, Failed: {failed}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
