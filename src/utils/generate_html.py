import os
from datetime import datetime
from zoneinfo import ZoneInfo

# Filstier
OUTPUT_FILE = "web/postliste.html"
TEMPLATE_FILE = "web/postliste_template.html"

def generate_html():
    updated = datetime.now(ZoneInfo("Europe/Oslo")).strftime("%d.%m.%Y %H:%M")

    # Les template
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    # Sett inn kun {updated}
    html = template.replace("{updated}", updated)

    # Lagre ferdig HTML
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[INFO] Lagret HTML til {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_html()
