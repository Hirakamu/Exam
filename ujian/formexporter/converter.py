import json

def transform_form_json(raw_data):
    # Initialize result with form info fields and empty lists
    result = {
        "nama": "",    # e.g., fill manually if desired
        "kelas": "",
        "semester": "",
        "tahun": "",
        "field": [],
        "metadata": []
    }
    q_id = 1
    m_id = 1

    # Iterate over form items
    for item in raw_data.get("items", []):
        # Skip non-question items
        if "questionItem" not in item and "questionGroupItem" not in item:
            continue

        # Handle grid (True/False) questions
        if "questionGroupItem" in item:
            group = item["questionGroupItem"]
            prompt = item.get("title", "")
            # Build shared options list (e.g. ["Benar", "Salah"])
            opsi = []
            for idx, opt in enumerate(group["grid"]["columns"]["options"], start=1):
                opsi.append({"id": idx, "text": opt.get("value", "")})
            # Collect all row statements and correct indices
            statements = []
            correct_indices = []
            for idx, row in enumerate(group["questions"], start=1):
                statements.append(row["rowQuestion"]["title"])
                # If the row's correct answer is the first option (e.g. "Benar"), mark it
                answers = row["grading"]["correctAnswers"]["answers"]
                if answers and answers[0]["value"] == opsi[0]["text"]:
                    correct_indices.append(idx)
            result["field"].append({
                "id": q_id,
                "pertanyaan": prompt,
                "jawab": {
                    "tipe": "TF",
                    "opsi": opsi,
                    "pertanyaan": statements,
                    "answer": correct_indices,
                    "point": group["questions"][0]["grading"]["pointValue"]
                }
            })
            q_id += 1
            continue

        # Handle single-question items
        q = item["questionItem"]["question"]
        title = item.get("title", "")

        # Skip items without grading (like name/class fields)
        if "grading" not in q:
            continue

        # Scale (metadata) question
        if "scaleQuestion" in q:
            result["metadata"].append({
                "id": m_id,
                "pertanyaan": title,
                "jawab": {
                    "tipe": "SKALA",
                    "opsi": [],
                    "answer": "",
                    "point": q["grading"]["pointValue"]
                }
            })
            m_id += 1
            continue

        # Multiple-choice or dropdown
        if "choiceQuestion" in q:
            qtype = q["choiceQuestion"]["type"]
            tipe = "PG" if qtype in ("RADIO", "DROP_DOWN") else qtype
            opsi = []
            for idx, opt in enumerate(q["choiceQuestion"]["options"], start=1):
                opsi.append({"id": idx, "text": opt.get("value", "")})
            # Determine correct answer(s) by matching values
            ans_values = [ans["value"] for ans in q["grading"]["correctAnswers"]["answers"]]
            ans_ids = []
            for val in ans_values:
                for opt in opsi:
                    if opt["text"] == val:
                        ans_ids.append(opt["id"])
            answer_field = ans_ids[0] if len(ans_ids) == 1 else ans_ids
            result["field"].append({
                "id": q_id,
                "pertanyaan": title,
                "jawab": {
                    "tipe": tipe,
                    "opsi": opsi,
                    "answer": answer_field,
                    "point": q["grading"]["pointValue"]
                }
            })
            q_id += 1
            continue

        # (Other types like text questions could be handled here)

    return result

# Example usage:
with open("sdfg.json", "r", encoding="utf-8") as infile:
    raw_form = json.load(infile)
structured_data = transform_form_json(raw_form)

# Write output JSON
with open("structured_output.json", "w", encoding="utf-8") as outfile:
    json.dump(structured_data, outfile, ensure_ascii=False, indent=2)
