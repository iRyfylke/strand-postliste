import json
from pathlib import Path

ARCHIVE_DIR = Path("data/archive")

def extract_year_from_filename(filename):
    # Forventer format: postliste_YYYY_H1.json
    parts = filename.split("_")
    if len(parts) < 2:
        return None
    year = parts[1]
    return int(year) if year.isdigit() else None

def verify_file(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        return {
            "count": 0,
            "years": set(),
            "status": "EMPTY"
        }

    years = set()
    for entry in data:
        iso = entry.get("dato_iso")
        if iso and len(iso) >= 4:
            years.add(int(iso[:4]))

    return {
        "count": len(data),
        "years": years,
        "status": "OK" if len(years) == 1 else "MIXED"
    }

def main():
    print("=== Verifiserer arkivfiler ===")
    for file in sorted(ARCHIVE_DIR.glob("postliste_*_H*.json")):
        expected_year = extract_year_from_filename(file.name)
        result = verify_file(file)

        print(f"\nFil: {file.name}")
        print(f"  Antall oppføringer: {result['count']}")
        print(f"  År funnet i filen: {sorted(result['years'])}")

        if result["count"] == 0:
            print("  STATUS: ❗ TOM FIL")
        elif result["status"] == "MIXED":
            print("  STATUS: ❗ BLANDEDE ÅR (må fikses)")
        elif expected_year not in result["years"]:
            print(f"  STATUS: ❗ FEIL ÅR (forventet {expected_year})")
        else:
            print("  STATUS: ✔ OK")

if __name__ == "__main__":
    main()
