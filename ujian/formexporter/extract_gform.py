import json
import pickle
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# ----------------------------
# CONFIGURATION
# ----------------------------
FORM_URLS = [
    "https://docs.google.com/forms/d/1il--mc2AvnFNU6aBKIbMQLc4yOm3Sxc_zV9dk9lEzWM/edit"
]

SCOPES = ['https://www.googleapis.com/auth/forms.body.readonly']
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.pkl"
OUTPUT_DIR = "forms_json"  # directory to save JSON files

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------------------
# AUTHENTICATION
# ----------------------------
def authenticate():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    return creds

# ----------------------------
# HELPER FUNCTION TO EXTRACT FORM ID
# ----------------------------
def get_form_id(url):
    if "/d/" in url:
        return url.split("/d/")[1].split("/")[0]
    else:
        raise ValueError(f"Invalid form URL: {url}")

# ----------------------------
# FETCH FORM STRUCTURE
# ----------------------------
def fetch_forms_structure():
    creds = authenticate()
    service = build('forms', 'v1', credentials=creds)

    for url in FORM_URLS:
        form_id = get_form_id(url)
        form = service.forms().get(formId=form_id).execute()
        form_title = form.get("info", {}).get("title", "Untitled Form")

        form_data = {
            "form_title": form_title,
            "form_id": form_id,
            "questions": []
        }

        with open(f"response_{form_title}.json", "w") as f:
            json.dump(form, f)

        for item in form.get("items", []):
            question_title = item.get("title", "")
            item_type = "DESCRIPTION"
            points = 0
            choices = []
            correct_answers = []

            if "questionItem" in item:
                question = item["questionItem"]["question"]
                item_type = question.get("questionType", "OTHER")
                points = question.get("pointValue", 0)

                # Multiple Choice / MCMA
                if "choiceQuestion" in question:
                    choices = [opt["value"] for opt in question["choiceQuestion"].get("options", [])]
                    correct_answers = question["choiceQuestion"].get("correctAnswers", [])
                elif "checkboxQuestion" in question:
                    choices = [opt["value"] for opt in question["checkboxQuestion"].get("options", [])]
                    correct_answers = question["checkboxQuestion"].get("correctAnswers", [])
                elif "textQuestion" in question:
                    # Short / Long answer
                    choices = []
                    correct_answers = question["textQuestion"].get("answers", [])
                elif "scaleQuestion" in question:
                    scale = question["scaleQuestion"]
                    choices = [f"{scale.get('lowLabel','')} - {scale.get('low',0)}", f"{scale.get('highLabel','')} - {scale.get('high',0)}"]
                elif "gridQuestion" in question:
                    grid = question["gridQuestion"]
                    choices = grid.get("rows", [])  # rows as choices
                elif "dropdownQuestion" in question:
                    choices = [opt["value"] for opt in question["dropdownQuestion"].get("options", [])]

            form_data["questions"].append({
                "question": question_title,
                "type": item_type,
                "points": points,
                "choices": choices,
                "correct_answers": correct_answers
            })

        # Save each form as separate JSON file
        safe_title = "".join(c if c.isalnum() or c in "_-" else "_" for c in form_title)
        output_file = os.path.join(OUTPUT_DIR, f"{safe_title}_{form_id}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(form_data, f, indent=4, ensure_ascii=False)

        print(f"✅ Exported {form_title} → {output_file}")

# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    fetch_forms_structure()
