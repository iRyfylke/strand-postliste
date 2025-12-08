import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

DATA_FILE = "postliste.json"        # ligger i rot
OUTPUT_FILE = "index.html"          # skal ligge i rot
TEMPLATE_FILE = "web/template.html" # ligger i web/

PER_PAGE = 50  # standard antall per side (kan endres)

def load_data():
    if not os.path.exists(DATA_FILE):
        print(f"[ERROR] Fant ikke {DATA_FILE}")
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                print(f"[INFO] Lastet {len(data)} oppføringer fra {DATA_FILE}")
                return data
            else:
                print(f"[ERROR] JSON-formatet er ikke en liste. Type: {type(data)}")
                return []
    except Exception as e:
        print(f"[ERROR] Kunne ikke laste {DATA_FILE}: {e}")
        return []

def generate_html():
    data = load_data()
    updated = datetime.now(ZoneInfo("Europe/Oslo")).strftime("%d.%m.%Y %H:%M")

    # Les template.html
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    # Sett inn placeholders manuelt
    html = (
        template
        .replace("{updated}", updated)
        .replace("{per_page}", str(PER_PAGE))
        .replace("{data_json}", json.dumps(data, ensure_ascii=False))
    )

    # Lagre ferdig index.html
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[INFO] Lagret HTML til {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_html()
