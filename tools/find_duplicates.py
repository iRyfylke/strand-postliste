import json
from pathlib import Path
from collections import defaultdict

POSTLISTE_PATH = Path("data/postliste.json")

def main():
    print("=== Søker etter duplikater i postliste.json ===")

    data = json.loads(POSTLISTE_PATH.read_text(encoding="utf-8"))

    seen = defaultdict(list)

    for idx, entry in enumerate(data):
        dokid = entry.get("dokumentID")
        if dokid:
            seen[dokid].append(idx)

    duplicates = {k: v for k, v in seen.items() if len(v) > 1}

    if not duplicates:
        print("✔ Ingen duplikater funnet")
        return

    print(f"❗ Fant {len(duplicates)} duplikat-IDer:\n")

    for dokid, indices in duplicates.items():
        print(f"- dokumentID '{dokid}' forekommer {len(indices)} ganger på indeksene {indices}")

    print("\nSTATUS: ❗ Duplikater må håndteres")

if __name__ == "__main__":
    main()
