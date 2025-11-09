import json
from pathlib import Path

DATA_DIR = Path(__file__).parent
FILES = ["X.json", "XI.json", "XII.json"]
OUTPUT = DATA_DIR / "students.json"

def id_for(student: dict) -> str:
    """Return a simple dedupe id for a student: prefer 'nis', else normalized name."""
    nis = student.get("nis")
    if nis:
        return str(nis).strip()
    name = student.get("name", "")
    return name.strip().lower()

merged = {}
files_found = 0
for fname in FILES:
    p = DATA_DIR / fname
    if not p.exists():
        continue
    files_found += 1
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"skipping {p}: {e}")
        continue

    grade = d.get("grade", p.stem)
    classes = d.get("classes", {})
    grade_map = merged.setdefault(grade, {})
    for cls_name, students in classes.items():
        out_list = grade_map.setdefault(cls_name, [])
        seen = {s.get("nis") for s in out_list if isinstance(s, dict) and s.get("nis")}
        for s in students:
            if not isinstance(s, dict):
                continue
            sid = id_for(s)
            if sid in seen:
                continue
            seen.add(sid)
            out_list.append(s)

result = {"grades": {}}
for grade, classes in merged.items():
    result["grades"][grade] = {"classes": classes}

with OUTPUT.open("w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"Merged {files_found} files -> {OUTPUT}")