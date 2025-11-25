import os
import json
from datetime import datetime
from urllib.parse import quote
import requests

API_URL = "https://www.strand.kommune.no/api/presentation/v2/nye-innsyn/overview"
OUTPUT_DIR = "."
POSTMOTTAK_EMAIL = "postmottak@strand.kommune.no"

def hent_side(page=1, page_size=100):
    headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
    params = {"pageNumber": page, "pageSize": page_size}
    r = requests.get(API_URL, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["content"]["searchItems"]["items"]

def lag_mailto_innsyn(dok):
    emne = f"Innsynsbegjæring – {dok.get('title')} ({dok.get('dato')})"
    body = f"Hei Strand kommune,\n\nJeg ber om innsyn i dokumentet:\n{dok}\n\nVennlig hilsen\nNavn"
    return f"mailto:{POSTMOTTAK_EMAIL}?subject={quote(emne)}&body={quote(body)}"

def render_html(dokumenter):
    if not dokumenter:
        content = "<p>Ingen dokumenter funnet i postlisten.</p>"
    else:
        cards = []
        for dok in dokumenter:
            title = dok.get("title") or "Uten tittel"
            meta = f"Dato: {dok.get('dato','')} · DokumentID: {dok.get('dokumentID','')}"
            actions = []
            # foreløpig ingen PDF‑lenker i API, så bare innsyn
            actions.append(f"<a href='{lag_mailto_innsyn(dok)}'>Be om innsyn</a>")
            card = (
                "<section class='card'>"
                f"<h3>{title}</h3>"
                f"<div class='meta'>{meta}</div>"
                f"<div class='actions'>{' '.join(actions)}</div>"
                "</section>"
            )
            cards.append(card)
        content = "\n".join(cards)

    html = f"""<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <title>Strand kommune – uoffisiell postliste</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; background: #fafafa; }}
    .card {{ background: #fff; padding: 1rem; margin-bottom: 1rem; border: 1px solid #ddd; }}
    .meta {{ color: #555; font-size: 0.9em; margin-bottom: 0.5rem; }}
    .actions a {{ margin-right: 1rem; }}
  </style>
</head>
<body>
  <h1>Postliste – Strand kommune (uoffisiell speiling)</h1>
  <p>Oppdatert: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
  {content}
</body>
</html>
"""
    out_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Skrev index.html til {out_path}")

def main():
    alle_dokumenter = []
    for page in range(1, 6):  # hent opptil 5 sider
        items = hent_side(page=page, page_size=100)
        if not items:
            break
        for it in items:
            dok = {
                "title": it.get("title"),
                "type": it.get("type"),
                "dokumentID": it.get("properties", {}).get("dokumentID"),
                "dato": it.get("properties", {}).get("dato"),
                "identifier": it.get("identifier"),
                "parentIdentifier": it.get("parentIdentifier"),
            }
            alle_dokumenter.append(dok)

    render_html(alle_dokumenter)
    json_path = os.path.join(OUTPUT_DIR, "postliste.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(alle_dokumenter, f, ensure_ascii=False, indent=2)
    print(f"Lagret JSON til {json_path}")

if __name__ == "__main__":
    main()
