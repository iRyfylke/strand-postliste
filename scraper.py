import os
import json
from datetime import datetime
from urllib.parse import urljoin, quote
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.strand.kommune.no"
POSTLISTE_BASE = (
    "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/"
    "postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/"
)
OUTPUT_DIR = "."
POSTMOTTAK_EMAIL = "postmottak@strand.kommune.no"

def hent_html(url):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; PostlisteScraper/1.0)"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def parse_postliste(html):
    soup = BeautifulSoup(html, "html.parser")
    dokumenter = []

    # Hver oppføring ligger i <a class="SakListItem_sakListLink__...">
    links = soup.select("a.SakListItem_sakListLink__16759c")
    for link in links:
        detalj_link = link.get("href")
        art = link.find("article")

        # Tittel
        title_elem = art.select_one(".bc-content-teaser-title-text")
        tittel = title_elem.get_text(strip=True) if title_elem else ""

        # DokumentID
        dokid_elem = art.select_one(".bc-content-teaser-meta-property--dokumentID dd")
        saksnr = dokid_elem.get_text(strip=True) if dokid_elem else ""

        # Dato
        dato_elem = art.select_one(".bc-content-teaser-meta-property--dato dd")
        dato = dato_elem.get_text(strip=True) if dato_elem else ""

        # Mottaker
        mottaker_elem = art.select_one(".bc-content-teaser-meta-property--mottaker dd")
        mottaker = mottaker_elem.get_text(strip=True) if mottaker_elem else ""

        # Gå inn på detaljsiden for å finne PDF
        pdf_link = None
        krever_innsyn = False
        if detalj_link:
            try:
                detalj_html = hent_html(detalj_link)
                detalj_soup = BeautifulSoup(detalj_html, "html.parser")
                pdf_tag = detalj_soup.find("a", href=lambda h: h and h.lower().endswith(".pdf"))
                if pdf_tag:
                    pdf_link = urljoin(BASE_URL, pdf_tag["href"])
                else:
                    krever_innsyn = True
            except Exception as e:
                print(f"Feil ved henting av detaljside {detalj_link}: {e}")
                krever_innsyn = True

        dokumenter.append({
            "dato": dato,
            "tittel": tittel,
            "mottaker": mottaker,
            "saksnr": saksnr,
            "pdf_link": pdf_link,
            "detalj_link": detalj_link,
            "krever_innsyn": krever_innsyn
        })

    print(f"Fant {len(dokumenter)} dokumenter i postlisten.")
    return dokumenter

def lag_mailto_innsyn(dok):
    emne = f"Innsynsbegjæring – {dok.get('tittel') or 'Dokument'} ({dok.get('dato')})"
    body = f"Hei Strand kommune,\n\nJeg ber om innsyn i dokumentet:\n{dok}\n\nVennlig hilsen\nNavn"
    return f"mailto:{POSTMOTTAK_EMAIL}?subject={quote(emne)}&body={quote(body)}"

def render_html(dokumenter):
    if not dokumenter:
        content = "<p>Ingen dokumenter funnet i postlisten.</p>"
    else:
        cards = []
        for dok in dokumenter:
            title = dok.get("tittel") or "Uten tittel"
            meta = f"Dato: {dok.get('dato','')} · Saksnr: {dok.get('saksnr','')}"
            actions = []
            if dok.get("pdf_link"):
                actions.append(f"<a href='{dok['pdf_link']}' target='_blank'>Åpne PDF</a>")
            elif dok.get("detalj_link"):
                actions.append(f"<a href='{dok['detalj_link']}' target='_blank'>Detaljer</a>")
            if dok.get("krever_innsyn"):
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

def hent_alle_sider(max_pages=5, page_size=100):
    alle_dokumenter = []
    for page in range(1, max_pages+1):
        url = f"{POSTLISTE_BASE}?page={page}&pageSize={page_size}"
        print(f"Henter side {page}: {url}")
        try:
            html = hent_html(url)
            dokumenter = parse_postliste(html)
            print(f"Side {page}: fant {len(dokumenter)} dokumenter")
            alle_dokumenter.extend(dokumenter)
            if not dokumenter:
                break
        except Exception as e:
            print(f"Feil ved henting av side {page}: {e}")
            break
    return alle_dokumenter

def main():
    dokumenter = hent_alle_sider(max_pages=5, page_size=100)
    render_html(dokumenter)
    json_path = os.path.join(OUTPUT_DIR, "postliste.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dokumenter, f, ensure_ascii=False, indent=2)
    print(f"Lagret JSON til {json_path}")

if __name__ == "__main__":
    main()
