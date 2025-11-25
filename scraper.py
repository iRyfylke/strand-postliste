from playwright.sync_api import sync_playwright
import json
import os
from datetime import datetime

OUTPUT_DIR = "."
URL = "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/?page=1&pageSize=100"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, timeout=60000)

        # Vent til oppføringene er lastet inn
        page.wait_for_selector("article.bc-content-teaser--item")

        # Hent alle oppføringer
        articles = page.query_selector_all("article.bc-content-teaser--item")
        dokumenter = []
        for art in articles:
            tittel = art.query_selector(".bc-content-teaser-title-text").inner_text()
            dato = art.query_selector(".bc-content-teaser-meta-property--dato dd").inner_text()
            dokid = art.query_selector(".bc-content-teaser-meta-property--dokumentID dd").inner_text()
            mottaker_elem = art.query_selector(".bc-content-teaser-meta-property--mottaker dd")
            mottaker = mottaker_elem.inner_text() if mottaker_elem else ""

            dokumenter.append({
                "tittel": tittel,
                "dato": dato,
                "dokumentID": dokid,
                "mottaker": mottaker
            })

        browser.close()

    # Lagre som JSON
    json_path = os.path.join(OUTPUT_DIR, "postliste.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dokumenter, f, ensure_ascii=False, indent=2)

    # Lag enkel HTML
    html_cards = "".join(
        f"<section><h3>{d['tittel']}</h3><p>{d['dato']} – {d['dokumentID']} – {d['mottaker']}</p></section>"
        for d in dokumenter
    )
    html = f"""<!doctype html>
<html lang="no">
<head><meta charset="utf-8"><title>Postliste</title></head>
<body>
<h1>Postliste – Strand kommune</h1>
<p>Oppdatert: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
{html_cards}
</body></html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    main()
