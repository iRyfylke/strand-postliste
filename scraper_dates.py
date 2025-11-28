from playwright.sync_api import sync_playwright
import json, os
from datetime import datetime, date

DATA_FILE = "postliste.json"
BASE_URL = "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/"

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return {d["dokumentID"]: d for d in json.load(f) if "dokumentID" in d}
            except Exception:
                return {}
    return {}

def save_json(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def safe_text(el, sel):
    try:
        node = el.query_selector(sel)
        return node.inner_text().strip() if node else ""
    except Exception:
        return ""

def format_dato(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        return s

def parse_date_robust(s):
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def hent_side(url, browser):
    page = browser.new_page()
    try:
        page.goto(url, timeout=20000)
        page.wait_for_selector("article.bc-content-teaser--item", timeout=10000)
    except Exception as e:
        print(f"[WARN] Ingen oppføringer ({e})")
        page.close()
        return []
    docs = []
    for art in page.query_selector_all("article.bc-content-teaser--item"):
        dokid = safe_text(art, ".bc-content-teaser-meta-property--dokumentID dd")
        if not dokid:
            continue
        tittel = safe_text(art, ".bc-content-teaser-title-text")
        dato = format_dato(safe_text(art, ".bc-content-teaser-meta-property--dato dd"))
        doktype = safe_text(art, ".SakListItem_sakListItemTypeText__16759c")
        avsender = safe_text(art, ".bc-content-teaser-meta-property--avsender dd")
        mottaker = safe_text(art, ".bc-content-teaser-meta-property--mottaker dd")
        am = f"Avsender: {avsender}" if avsender else f"Mottaker: {mottaker}" if mottaker else ""

        detalj_link = ""
        filer = []
        try:
            link_elem = art.evaluate_handle("node => node.closest('a')")
            detalj_link = link_elem.get_attribute("href") if link_elem else ""
        except Exception:
            pass
        if detalj_link:
            dp = browser.new_page()
            try:
                dp.goto(detalj_link, timeout=20000)
                for fl in dp.query_selector_all("a"):
                    href, tekst = fl.get_attribute("href"), fl.inner_text()
                    if href and "/api/presentation/v2/nye-innsyn/filer" in href:
                        abs_url = href if href.startswith("http") else "https://www.strand.kommune.no" + href
                        filer.append({"tekst": tekst, "url": abs_url})
            finally:
                dp.close()

        status = "Publisert" if filer else "Må bes om innsyn"
        docs.append({
            "tittel": tittel,
            "dato": dato,
            "dokumentID": dokid,
            "dokumenttype": doktype,
            "avsender_mottaker": am,
            "detalj_link": detalj_link,
            "filer": filer,
            "status": status
        })
    page.close()
    return docs

def update_json(new_docs):
    existing = load_existing()
    updated = dict(existing)
    for d in new_docs:
        doc_id = d["dokumentID"]
        old = updated.get(doc_id)
        if not old or any(old.get(k) != d.get(k) for k in ["status","tittel","dokumenttype","avsender_mottaker"]) or len(old.get("filer",[])) != len(d.get("filer",[])):
            updated[doc_id] = d
            print(f"[{'NEW' if not old else 'UPDATE'}] {doc_id} – {d['tittel']}")
    data_list = sorted(updated.values(), key=lambda x: x.get("dato",""), reverse=True)
    save_json(data_list)
    print(f"[INFO] Lagret JSON med {len(data_list)} dokumenter")

def main(start_date=None, end_date=None):
    """
    - start_date + end_date → periode
    - bare start_date → spesifikk dato
    - ingen datoer → alt
    """
    print("[INFO] Starter scraper_dates…")
    all_docs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

        # Primær: bruk kommunens URL-filter
        if start_date and end_date:
            url = f"{BASE_URL}?Dato={start_date.isoformat()}&Dato={end_date.isoformat()}&Dato=Other"
        elif start_date:
            url = f"{BASE_URL}?Dato={start_date.isoformat()}&Dato={start_date.isoformat()}&Dato=Other"
        else:
            url = BASE_URL

        print(f"[INFO] Prøver primærmetode med URL-filter: {url}")
        docs = hent_side(url, browser)

        if docs:
            print(f"[INFO] Fant {len(docs)} oppføringer via URL-filter")
            all_docs.extend(docs)
        else:
            print("[WARN] Ingen treff via URL-filter, faller tilbake til robust metode…")
            page_num = 1
            while True:
                url = f"{BASE_URL}?page={page_num}&pageSize=100"
                docs = hent_side(url, browser)
                if not docs:
                    break
                for d in docs:
                    dt = parse_date_robust(d["dato"])
                    if not dt:
                        continue
                    if start_date and end_date:
                        if start_date <= dt <= end_date:
                            all_docs.append(d)
                    elif start_date:
                        if dt == start_date:
                            all_docs.append(d)
                    else:
                        all_docs.append(d)
                page_num += 1

        browser.close()

    update_json(all_docs)

if __name__ == "__main__":
    # Eksempel: spesifikk dato
    # main(start_date=date(2025,11,20))
    # Eksempel: periode
     main(start_date=date(2025,11,1), end_date=date(2025,11,18))
