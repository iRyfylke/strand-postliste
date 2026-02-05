import time
from utils_playwright_sync import safe_goto, safe_text
from utils_dates import parse_date_from_page, format_date

BASE_URL = (
    "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/"
    "postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/"
    "?page={page}&pageSize=100"
)


def hent_side_incremental(page_num, browser):
    url = BASE_URL.format(page=page_num)
    print(f"[INFO] Åpner side {page_num}: {url}")

    page = browser.new_page()

    # Første forsøk
    if not safe_goto(page, url):
        page.close()
        return []

    # Vent på artikler
    if not _wait_for_articles(page, page_num):
        page.close()
        return []

    artikler = page.query_selector_all("article.bc-content-teaser--item")
    print(f"[INFO] Fant {len(artikler)} artikler på side {page_num}")

    docs = []
    for art in artikler:
        dokid = safe_text(art, ".bc-content-teaser-meta-property--dokumentID dd")
        if not dokid:
            continue

        tittel = safe_text(art, ".bc-content-teaser-title-text")
        dato_raw = safe_text(art, ".bc-content-teaser-meta-property--dato dd")

        parsed = parse_date_from_page(dato_raw)
        dato_norsk = format_date(parsed) if parsed else ""
        dato_iso = parsed.isoformat() if parsed else None

        doktype = safe_text(art, ".SakListItem_sakListItemTypeText__16759c")
        avsender = safe_text(art, ".bc-content-teaser-meta-property--avsender dd")
        mottaker = safe_text(art, ".bc-content-teaser-meta-property--mottaker dd")

        am = f"Avsender: {avsender}" if avsender else (f"Mottaker: {mottaker}" if mottaker else "")

        detalj_link = _extract_detail_link(art)

        filer = _fetch_files(browser, detalj_link, dokid)

        status = "Publisert" if filer else "Må bes om innsyn"

        docs.append({
            "tittel": tittel,
            "dato": dato_norsk,
            "dato_iso": dato_iso,
            "dokumentID": dokid,
            "dokumenttype": doktype,
            "avsender_mottaker": am,
            "side": page_num,
            "detalj_link": detalj_link,
            "filer": filer,
            "status": status,
        })

    page.close()
    return docs


# ---------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------

def _wait_for_articles(page, page_num):
    """Vent på artikler med retry."""
    try:
        page.wait_for_selector("article.bc-content-teaser--item", timeout=15000)
        return True
    except Exception:
        print(f"[WARN] Ingen artikler på side {page_num}, prøver igjen…")
        time.sleep(2)

    try:
        page.wait_for_selector("article.bc-content-teaser--item", timeout=15000)
        return True
    except Exception:
        print(f"[ERROR] Side {page_num} feilet to ganger.")
        return False


def _extract_detail_link(art):
    """Hent detaljlenke fra artikkel."""
    try:
        link_elem = art.evaluate_handle("node => node.closest('a')")
        href = link_elem.get_attribute("href") if link_elem else ""
    except Exception:
        return ""

    if href and not href.startswith("http"):
        return "https://www.strand.kommune.no" + href
    return href or ""


def _fetch_files(browser, detalj_link, dokid):
    """Hent filer fra detaljsiden."""
    if not detalj_link:
        return []

    filer = []
    dp = browser.new_page()

    if safe_goto(dp, detalj_link):
        time.sleep(1)
        try:
            for fl in dp.query_selector_all("a"):
                href = fl.get_attribute("href")
                tekst = fl.inner_text()
                if href and "/api/presentation/v2/nye-innsyn/filer" in href:
                    abs_url = href if href.startswith("http") else "https://www.strand.kommune.no" + href
                    filer.append({"tekst": (tekst or "").strip(), "url": abs_url})
        except Exception as e:
            print(f"[WARN] Klarte ikke hente filer for {dokid}: {e}")

    dp.close()
    return filer
