import os
import re
import json
from datetime import datetime
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup

# Konfigurasjon
BASE_URL = "https://www.strand.kommune.no"
POSTLISTE_URL = "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/"

OUTPUT_DIR = "."
PDF_DIR = os.path.join(OUTPUT_DIR, "pdf_dokumenter")
TEMPLATES_DIR = os.path.join(OUTPUT_DIR, "templates")
ASSETS_DIR = os.path.join(OUTPUT_DIR, "assets")

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

POSTMOTTAK_EMAIL = "postmottak@strand.kommune.no"

# ------------------- Hjelpefunksjoner -------------------

def hent_html(url):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; PostlisteScraper/1.0)"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def er_innsynsoppforing(celle_text: str) -> bool:
    txt = celle_text.lower()
    hints = ["innsyn", "ikke publisert", "ikke offentlig", "begrenset", "unntatt offentlighet"]
    return any(h in txt for h in hints)

def parse_postliste(html):
    soup = BeautifulSoup(html, "html.parser")
    dokumenter = []

    rows = soup.select("table tr")
    if not rows:
        rows = soup.select(".list, .table, .content, .search-result, article")

    for rad in rows:
        celler = rad.find_all(["td", "div", "li"])
        if not celler:
            continue

        dato, tittel, avsender, mottaker, saksnr, pdf_link = "", "", "", "", "", None

        if len(celler) >= 2:
            dato = celler[0].get_text(strip=True)
            tittel_elem = celler[1]
            tittel = tittel_elem.get_text(strip=True)
            link_tag = tittel_elem.find("a")
            if link_tag and link_tag.get("href"):
                href = link_tag["href"]
                pdf_link = urljoin(BASE_URL, href) if href.startswith("/") else href

        if len(celler) >= 3:
            avsender = celler[2].get_text(strip=True)
        if len(celler) >= 4:
            mottaker = celler[3].get_text(strip=True)
        if len(celler) >= 5:
            saksnr = celler[4].get_text(strip=True)

        krever_innsyn = False
        if pdf_link is None or (tittel and er_innsynsoppforing(tittel)):
            krever_innsyn = True

        dokumenter.append({
            "dato": dato,
            "tittel": tittel,
            "avsender": avsender,
            "mottaker": mottaker,
            "saksnr": saksnr,
            "pdf_link": pdf_link if (pdf_link and pdf_link.lower().endswith(".pdf")) else None,
            "detalj_link": pdf_link if (pdf_link and not pdf_link.lower().endswith(".pdf")) else None,
            "krever_innsyn": krever_innsyn
        })

    dokumenter = [d for d in dokumenter if any(d.get(k) for k in ["tittel", "pdf_link", "detalj_link"])]
    return dokumenter

def last_ned_pdf(url, filnavn):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PostlisteScraper/1.0)"}
        r = requests.get(url, headers=headers, timeout=60)
        r.raise_for_status()
        path = os.path.join(PDF_DIR, filnavn)
        with open(path, "wb") as f:
            f.write(r.content)
        return path
    except Exception as e:
        print(f"Feil ved nedlasting av {url}: {e}")
        return None

def lag_mailto_innsyn(dok):
    emne = f"Innsynsbegjæring – {dok.get('tittel') or 'Dokument'} ({dok.get('dato')})"
    body_lines = [
        "Hei Strand kommune,",
        "",
        "Jeg ber om innsyn i følgende dokument fra postlisten:",
        f"- Tittel: {dok.get('tittel')}",
        f"- Dato: {dok.get('dato')}",
        f"- Saksnummer: {dok.get('saksnr')}",
        f"- Avsender: {dok.get('avsender')}",
        f"- Mottaker: {dok.get('mottaker')}",
        "",
        "Hvis dokumentet er helt eller delvis unntatt offentlighet, ber jeg om en begrunnelse med hjemmel samt vurdering av meroffentlighet.",
        "",
        "Vennlig hilsen",
        "Navn",
    ]
    body = "\n".join(body_lines)
    return f"mailto:{POSTMOTTAK_EMAIL}?subject={quote(emne)}&body={quote(body)}"

# ------------------- HTML-rendering -------------------

def render_html(dokumenter):
    base_path = os.path.join(TEMPLATES_DIR, "base.html")
    if not os.path.exists(base_path):
        with open(base_path, "w", encoding="utf-8") as f:
            f.write("""<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <title>Strand kommune – uoffisiell postliste speilet</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="./assets/styles.css" rel="stylesheet">
</head>
<body>
<header>
  <h1>Postliste – Strand kommune (uoffisiell speiling)</h1>
  <p>Generert automatisk. Kilde: Strand kommune. Denne siden publiseres av en privat aktør.</p>
</header>
<main>
  <!-- CONTENT -->
</main>
<footer>
  <p>Oppdatert: {{timestamp}}</p>
</footer>
</body>
</html>""")

    css_path = os.path.join(ASSETS_DIR, "styles.css")
    if not os.path.exists(css_path):
        with open(css_path, "w", encoding="utf-8") as f:
            f.write("body{font-family:sans-serif;margin:0;padding:0;background:#fafafa;color:#222}")

    cards_html = []
    for dok in dokumenter:
        badges = []
        if dok.get("pdf_link"):
            badges.append('<span class="badge pdf">PDF</span>')
        if dok.get("krever_innsyn"):
            badges.append('<span class="badge innsyn">Krever innsyn</span>')

        meta_parts = []
        if dok.get("dato"): meta_parts.append(f"Dato: {dok['dato']}")
        if dok.get("saksnr"): meta_parts.append(f"Saksnr: {dok['saksnr']}")
        if dok.get("avsender"): meta_parts.append(f"Avsender: {dok['avsender']}")
        if dok.get("mottaker"): meta_parts.append(f"Mottaker: {dok['mottaker']}")
        meta_html = " · ".join(meta_parts)

        actions = []
        if dok.get("pdf_link"):
            actions.append(f"<a class='btn' href='{dok['pdf_link']}' target='_blank'>Åpne PDF</a>")
        elif dok.get("detalj_link"):
            actions.append(f"<a class='btn' href='{dok['detalj_link']}' target='_blank'>Detaljer</a>")
        if dok.get("krever_innsyn"):
            actions.append(f"<a class='btn' href='{lag_mailto_innsyn(dok)}'>Be om innsyn</a>")

        card = (
            "<section class='card'>"
            f"<h3>{dok.get('tittel') or 'Uten tittel'}</h3>"
            f"<div class='meta'>{meta_html}</div>"
            f"<div>{' '.join(badges)}</div>"
            f"<div class='actions'>{' '.join(actions)}</div>"
            "</section>"
        )
        cards_html.append(card)

        if dok.get("krever_innsyn"):
            dup_title = f"Innsyn: {dok.get('tittel') or 'Uten tittel'}"
            dup_actions = []
            dup_actions.append(
                f"<a class='btn' href='{lag_mailto_innsyn(dok)}'>Send innsynsbegjæring</a>"
            )
            if dok.get("detalj_link"):
                dup_actions.append(
                    f"<a class='btn' href='{dok['detalj_link']}' target='_blank' rel='noopener'>Detaljer</a>"
                )

            dup_card = (
                "<section class='card'>"
                f"<h3>{dup_title}</h3>"
                f"<div class='meta'>{meta_html}</div>"
                "<div><span class='badge innsyn'>Må bes om innsyn</span></div>"
                f"<div class='actions'>{' '.join(dup_actions)}</div>"
                "</section>"
            )

        cards_html.append(dup_card)
