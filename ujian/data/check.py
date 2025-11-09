#!/usr/bin/env python3
"""
detect_nis_duplicates.py

Usage:
  python3 detect_nis_duplicates.py uji an/data/students.json
"""

import json
import argparse
from collections import defaultdict

def normalize_nis(n):
    if n is None:
        return None
    return str(n).strip()

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    p = argparse.ArgumentParser(description="Find duplicate NIS in students JSON")
    p.add_argument('file', help='path to students.json')
    p.add_argument('--show-records', action='store_true', help='Show full records for each duplicate')
    p.add_argument('--output', help='Write duplicates summary to a JSON file')
    args = p.parse_args()

    data = load_json(args.file)

    # Normalize possible structures: top-level list or dict with classes, etc.
    records = []
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        # flatten dict values if they are lists
        for v in data.values():
            if isinstance(v, list):
                records.extend(v)
    else:
        raise SystemExit("Unsupported JSON top-level type: {}".format(type(data)))

    nis_map = defaultdict(list)  # nis -> list of (index, record)
    for i, rec in enumerate(records):
        # try common key names; adjust if your file uses a different key
        nis_val = None
        for key in ("NIS", "nis", "student_id", "id"):
            if isinstance(rec, dict) and key in rec:
                nis_val = rec.get(key)
                break
        nis = normalize_nis(nis_val)
        nis_map[nis].append((i, rec))

    duplicates = {nis: items for nis, items in nis_map.items() if nis is not None and len(items) > 1}
    empties = {nis: items for nis, items in nis_map.items() if (nis is None or nis == "") and len(items) > 1}

    if not duplicates and not empties:
        print("No duplicated NIS found.")
        return

    if duplicates:
        print("Duplicated NIS (value -> count):")
        for nis, items in sorted(duplicates.items(), key=lambda kv: -len(kv[1])):
            print(f"{nis!r} -> {len(items)}")
            if args.show_records:
                for idx, rec in items:
                    print(f"  index {idx}: {rec}")
    if empties:
        print("\nEmpty/Null NIS duplicated (these may indicate missing data):")
        for nis, items in empties.items():
            print(f"(empty) -> {len(items)}")
            if args.show_records:
                for idx, rec in items:
                    print(f"  index {idx}: {rec}")

    if args.output:
        out = {
            "duplicates": {nis: [idx for idx,_ in items] for nis, items in duplicates.items()},
            "empty_duplicates_count": { "count": sum(len(v) for v in empties.values())}
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(f"\nSummary written to {args.output}")

if __name__ == "__main__":
    main()