import os
import re
import json
from datetime import datetime
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.strand.kommune.no"
POSTLISTE_URL = "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/"

OUTPUT_DIR = "."
PDF_DIR = os.path.join(OUTPUT_DIR, "pdf_dokumenter")
TEMPLATES_DIR = os.path.join(OUTPUT_DIR, "templates")
ASSETS_DIR = os.path.join(OUTPUT_DIR, "assets")

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

POSTMOTTAK_EMAIL = "postmottak@strand.kommune.no"  # endre om annen adresse er riktig

def hent_html(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PostlisteScraper/1.0)"
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def er_innsynsoppforing(celle_text: str) -> bool:
    """
    Heuristikk: Oppføringen krever innsyn hvis
    - lenke mangler
    - teksten inneholder typiske indikasjoner: 'innsyn', 'ikke publisert', 'begrenset'
    Juster ved behov etter faktisk HTML/tekst.
    """
    txt = celle_text.lower()
    hints = ["innsyn", "ikke publisert", "ikke offentlig", "begrenset", "unntatt offentlighet"]
    return any(h in txt for h in hints)

def parse_postliste(html):
    soup = BeautifulSoup(html, "html.parser")
    dokumenter = []

    # Juster selektorene etter faktisk struktur. Start generisk:
    # Let etter tabeller/lister med rader av saker/dokumenter.
    rows = soup.select("table tr")
    if not rows:
        # fallback: kortlistede kort/sekjsoner
        rows = soup.select(".list, .table, .content, .search-result, article")
    for rad in rows:
        celler = rad.find_all(["td", "div", "li"])
        if not celler:
            continue

        # Forsøk å hente standardfelter. Du må mappe disse mot faktisk HTML.
        dato = ""
        tittel = ""
        avsender = ""
        mottaker = ""
        saksnr = ""
        pdf_link = None

        # Eksempel-mapping: antar kolonne-rekkefølge [Dato, Tittel, Avsender, Mottaker, Saksnr]
        # Juster ved inspeksjon av faktisk DOM.
        if len(celler) >= 2:
            dato = celler[0].get_text(strip=True)
            tittel_elem = celler[1]
            tittel = tittel_elem.get_text(strip=True)
            link_tag = tittel_elem.find("a")
            if link_tag and link_tag.get("href"):
                href = link_tag["href"]
                # Hvis href peker til PDF eller dokument-detaljside:
                pdf_link = urljoin(BASE_URL, href) if href.startswith("/") else href

        if len(celler) >= 3:
            avsender = celler[2].get_text(strip=True)
        if len(celler) >= 4:
            mottaker = celler[3].get_text(strip=True)
        if len(celler) >= 5:
            saksnr = celler[4].get_text(strip=True)

        # Heuristikk for oppføringer som krever innsyn
        krever_innsyn = False
        # Hvis ingen lenke, men teksten antyder innsynsbehov
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

    # Rens tomme poster
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
    # Bygg forhåndsutfylt e-post for innsyn
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

def render_html(dokumenter):
    # Les base-mal
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

    # Les css
    css_path = os.path.join(ASSETS_DIR, "styles.css")
    if not os.path.exists(css_path):
        with open(css_path, "w", encoding="utf-8") as f:
            f.write("""body{font-family:system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;padding:0;background:#fafafa;color:#222}
header,footer{background:#fff;padding:16px;border-bottom:1px solid #eee}
main{padding:16px}
.list{display:grid;gap:12px}
.card{background:#fff;border:1px solid #e5e5e5;border-radius:8px;padding:12px}
.card h3{margin:0 0 8px;font-size:1.05rem}
.meta{font-size:.9rem;color:#555}
.actions{margin-top:8px;display:flex;gap:8px;flex-wrap:wrap}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;background:#f0f0f0;color:#333;font-size:.8rem}
.badge.innsyn{background:#ffe9c7;color:#8a5a00}
.badge.pdf{background:#cfe8ff;color:#074a94}
a.btn{display:inline-block;padding:6px 10px;border:1px solid #ddd;border-radius:6px;background:#f8f8f8;text-decoration:none;color:#0647a6}
a.btn:hover{background:#efefef}""")

    # Bygg innhold
    cards_html = []
    for dok in dokumenter:
        # Hovedkort
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
            actions.append(f'<a class="btn" href="{dok["pdf_link"]}" target="_blank" rel="noopener">Åpne PDF</a>')
        elif dok.get("detalj_link"):
            actions.append(f'<a class="btn" href="{dok["detalj_link"]}" target="_blank" rel="noopener">Detaljer</a>')
        # Innsynduplikat-lenke
        if dok.get("krever_innsyn"):
            actions.append(f'<a class="btn" href="{lag_mailto_innsyn(dok)}">Be om innsyn</a>')

        card = f"""
        <section class="card">
          <h3>{dok.get('tittel') or 'Uten tittel'}</h3>
          <div class="meta">{meta_html}</div>
          <div>{" ".join(badges)}</div>
          <div class="actions">{" ".join(actions)}</div>
        </section>
        """
        cards_html.append(card)

        # Duplisert oppføring som eksplisitt henviser til innsyn (kun hvis krever innsyn)
        if dok.get("krever_innsyn"):
            dup_title = f"Innsyn: {dok.get('tittel') or 'Uten tittel'}"
            dup_card = f"""
            <section class="card">
              <h3>{dup_title}</h3>
              <div class="meta">{meta_html}</div>
              <div><span class="badge innsyn">Må bes om innsyn</span></div>
              <div class="actions">
                <a class="btn" href="{lag_mailto_innsyn(dok)}">Send innsynsbegjæring</a>
                {"<a class='btn' href='"+dok["detalj_link"]+"' target='_blank' rel='noopener'>Detaljer</a>" if dok.get("detalj_link") else ""}
              </div>
            </section>
            """
            cards_html.append(dup_card)

    content = f'<div class="list">\n{"\n".join(cards_html)}\n</div>'

    # Render base
    with open(base_path, "r", encoding="utf-8") as f:
        template = f.read()

    html = template.replace("<!-- CONTENT -->", content).replace("{{timestamp}}", datetime.now().strftime("%Y-%m-%d %H:%M"))
    out_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

def main():
    html = hent_html(POSTLISTE_URL)
    dokumenter = parse_postliste(html)

    # Last ned PDF-er lokalt (opsjonelt)
    for dok in dokumenter:
        if dok.get("pdf_link"):
            # Lag filnavn
            base_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", (dok.get("tittel") or "dokument"))
            filnavn = f"{base_name}.pdf"
            path = last_ned_pdf(dok["pdf_link"], filnavn)
            if path:
                # Pek til lokal kopi i tillegg (kan publiseres via Pages)
                dok["pdf_local"] = os.path.relpath(path, OUTPUT_DIR)

    # Lagre JSON
    with open(os.path.join(OUTPUT_DIR, "postliste.json"), "w", encoding="utf-8") as f:
        json.dump(dokumenter, f, ensure_ascii=False, indent=2)

    # Generer HTML
    render_html(dokumenter)
    print("Ferdig: index.html og postliste.json generert.")

if __name__ == "__main__":
    main()
