from playwright.sync_api import sync_playwright
import json
import os
from datetime import datetime

OUTPUT_DIR = "."
BASE_URL = "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/?page={page}&pageSize=100"

def hent_side(page, browser):
    url = BASE_URL.format(page=page)
    page_obj = browser.new_page()
    page_obj.goto(url, timeout=60000)
    try:
        page_obj.wait_for_selector("article.bc-content-teaser--item", timeout=15000)
    except:
        print(f"Ingen oppføringer på side {page}")
        return []
    articles = page_obj.query_selector_all("article.bc-content-teaser--item")
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
            "mottaker": mottaker,
            "side": page
        })
    page_obj.close()
    return dokumenter

def main():
    alle_dokumenter = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # hent opptil 5 sider (kan økes)
        for page in range(1, 6):
            docs = hent_side(page, browser)
            if not docs:
                break
            alle_dokumenter.extend(docs)
        browser.close()

    # lagre JSON
    json_path = os.path.join(OUTPUT_DIR, "postliste.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(alle_dokumenter, f, ensure_ascii=False, indent=2)

    # lag HTML
    html_cards = "".join(
        f"<section><h3>{d['tittel']}</h3><p>{d['dato']} – {d['dokumentID']} – {d['mottaker']} (side {d['side']})</p></section>"
        for d in alle_dokumenter
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
