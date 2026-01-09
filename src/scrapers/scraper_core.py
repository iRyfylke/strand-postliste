import time
from utils_playwright import safe_text, safe_goto
from utils_dates import parse_date_from_page, format_date

BASE_URL = (
    "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/"
    "postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/"
    "?page={page}&pageSize={page_size}"
)


def hent_side(page_num, browser, per_page, page=None, retries=5, timeout=10_000):
    """
    Optimalisert versjon:
      - Gjenbruker page-instans hvis gitt
      - Blokkerer unødvendige ressurser (gjøres i context)
      - Lavere timeout
      - Raskere parsing
      - Mindre memory leaks
    """

    url = BASE_URL.format(page=page_num, page_size=per_page)

    for attempt in range(1, retries + 1):
        try:
            print(f"[INFO] Åpner side {page_num} (forsøk {attempt}/{retries}): {url}")

            # Gjenbruk page hvis mulig
            if page is None:
                page = browser.new_page()

            # Naviger
            if not safe_goto(page, url, retries=1):
                raise RuntimeError("safe_goto feilet")

            # Vent kort for rendering
            page.wait_for_timeout(300)

            # Vent på artikler (kort timeout)
            try:
                page.wait_for_selector("article.bc-content-teaser--item", timeout=timeout)
            except Exception as e:
                print(f"[WARN] Ingen artikler funnet på side {page_num}: {e}")
                raise

            artikler = page.query_selector_all("article.bc-content-teaser--item")
            antall = len(artikler)
            print(f"[INFO] Fant {antall} dokumenter på side {page_num}")

            if antall == 0:
                raise RuntimeError("0 artikler funnet")

            docs = []

            # Hent detaljvisning i samme page (raskere)
            for art in artikler:
                dokid = safe_text(art, ".bc-content-teaser-meta-property--dokumentID dd")
                if not dokid:
                    continue

                tittel = safe_text(art, ".bc-content-teaser-title-text")
                dato_raw = safe_text(art, ".bc-content-teaser-meta-property--dato dd")
                parsed = parse_date_from_page(dato_raw)

                doktype = safe_text(art, ".SakListItem_sakListItemTypeText__16759c")
                avsender = safe_text(art, ".bc-content-teaser-meta-property--avsender dd")
                mottaker = safe_text(art, ".bc-content-teaser-meta-property--mottaker dd")

                am = (
                    f"Avsender: {avsender}"
                    if avsender
                    else (f"Mottaker: {mottaker}" if mottaker else "")
                )

                # Hent detalj-link
                detalj_link = ""
                try:
                    link_elem = art.evaluate_handle("node => node.closest('a')")
                    detalj_link = link_elem.get_attribute("href") if link_elem else ""
                except Exception:
                    pass

                if detalj_link and not detalj_link.startswith("http"):
                    detalj_link = "https://www.strand.kommune.no" + detalj_link

                # Hent filer (raskere, med gjenbruk av page)
                filer = []
                if detalj_link:
                    try:
                        if safe_goto(page, detalj_link, retries=1):
                            page.wait_for_timeout(200)
                            for fl in page.query_selector_all("a"):
                                href = fl.get_attribute("href")
                                tekst = fl.inner_text()
                                if href and "/api/presentation/v2/nye-innsyn/filer" in href:
                                    abs_url = href if href.startswith("http") else "https://www.strand.kommune.no" + href
                                    filer.append({
                                        "tekst": (tekst or "").strip(),
                                        "url": abs_url
                                    })
                    except Exception as e:
                        print(f"[WARN] Klarte ikke hente filer for {dokid}: {e}")
                    finally:
                        # Gå tilbake til hovedsiden uten å lage ny page
                        safe_goto(page, url, retries=1)
                        page.wait_for_timeout(100)

                status = "Publisert" if filer else "Må bes om innsyn"

                docs.append({
                    "tittel": tittel,
                    "dato": format_date(parsed),
                    "dato_iso": parsed.isoformat() if parsed else None,
                    "dokumentID": dokid,
                    "dokumenttype": doktype,
                    "avsender_mottaker": am,
                    "journal_link": detalj_link,
                    "filer": filer,
                    "status": status,
                })

            return docs

        except Exception as e:
            print(f"[WARN] Feil ved lasting/parsing av side {page_num} (forsøk {attempt}/{retries}): {e}")
            time.sleep(1)

    print(f"[ERROR] Side {page_num} feilet etter {retries} forsøk.")
    return None
