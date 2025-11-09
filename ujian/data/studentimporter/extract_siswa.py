import xml.etree.ElementTree as ET
import json

"""
school provides -> manual extract -> python process -> json -> sql
"""

XML_PATH = r"siswa sman2cikarangpusat.xml"
OUT_PATH = r"siswa_sman2cikarangpusat.json"

# Namespace used in the file for ss: attributes
SS_NS = 'urn:schemas-microsoft-com:office:spreadsheet'
TYPE_KEY = '{' + SS_NS + '}Type'

# Parse and gather Data elements in document order
tree = ET.parse(XML_PATH)
datas = tree.findall('.//{{{ns}}}Data'.format(ns=SS_NS))

records = []
i = 0
while i < len(datas):
    t = datas[i].attrib.get(TYPE_KEY)
    if t == 'Number':
        num = datas[i].text.strip() if datas[i].text else ''
        # search forward for the next String Data element
        j = i + 1
        while j < len(datas):
            t2 = datas[j].attrib.get(TYPE_KEY)
            if t2 == 'String':
                name = datas[j].text.strip() if datas[j].text else ''
                try:
                    idv = int(num)
                except Exception:
                    idv = num
                # Build id as a string for output, but keep numeric value for sorting
                id_str = str(idv)
                # Extract grade and class from the id string when possible
                grade = id_str[:2] if len(id_str) >= 2 else ''
                class_ = id_str[2:4] if len(id_str) >= 4 else ''
                # Store a temporary numeric value to keep numeric sorting stable
                records.append({"grade": grade, "class": class_, "id": id_str, "name": name, "_num": idv if isinstance(idv, int) else None})
                i = j
                break
            j += 1
    i += 1

# Sort records: numeric IDs first (ascending), then any non-numeric IDs
def _sort_key(rec):
    # Prefer numeric sort when available (we kept a temporary _num key)
    num = rec.get('_num')
    if isinstance(num, int):
        return (0, num)
    # fallback: sort by id string
    return (1, str(rec.get('id')))

records.sort(key=_sort_key)

# Remove internal helper keys before writing
cleaned = []
for rec in records:
    rec_copy = {k: v for k, v in rec.items() if k != '_num'}
    cleaned.append(rec_copy)

# Write JSON
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(cleaned, f, ensure_ascii=False, indent=2)

print(f"Wrote {len(cleaned)} records to {OUT_PATH}")
# print a small preview
for r in cleaned[:10]:
    print(r)
