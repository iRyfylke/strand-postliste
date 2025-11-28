from playwright.sync_api import sync_playwright
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

DATA_FILE = "postliste.json"

BASE_URL = (
    "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/"
    "postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/?page={page}&pageSize=100"
)

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return {d["dokumentID"]: d for d in data if "dokumentID" in d}
            except Exception:
                return {}
    return {}

def save_json(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def safe_text(element, selector: str) -> str:
    try:
        node = element.query_selector(selector)
        return node.inner_text().strip() if node else ""
    except Exception:
        return ""

def format_dato(dato_str: str) -> str:
    try:
        dt = datetime.strptime(dato_str, "%Y-%m-%d")
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return dato_str

def hent_side(page_num: int, browser):
    url = BASE_URL.format(page=page_num)
    print(f"[INFO] Åpner side {page_num}: {url}")
    page = browser.new_page()
    try:
        page.goto(url, timeout=15000)
        page.wait_for_selector("article.bc-content-teaser--item", timeout=5000)
    except Exception as e:
        print(f"[WARN] Ingen oppføringer på side {page_num} ({e})")
        page.close()
        return []

    articles = page.query_selector_all("article.bc-content-teaser--item")
    dokumenter = []
    for art in articles:
        tittel = safe_text(art, ".bc-content-teaser-title-text")
        dato_raw = safe_text(art, ".bc-content-teaser-meta-property--dato dd")
        dato = format_dato(dato_raw)
        dokid = safe_text(art, ".bc-content-teaser-meta-property--dokumentID dd")
        doktype = safe_text(art, ".SakListItem_sakListItemTypeText__16759c")

        avsender = safe_text(art, ".bc-content-teaser-meta-property--avsender dd")
        mottaker = safe_text(art, ".bc-content-teaser-meta-property--mottaker dd")
        if avsender:
            am = f"Avsender: {avsender}"
        elif mottaker:
            am = f"Mottaker: {mottaker}"
        else:
            am = ""

        if not dokid:
            continue

        detalj_link = ""
        try:
            link_elem = art.evaluate_handle("node => node.closest('a')")
            detalj_link = link_elem.get_attribute("href") if link_elem else ""
        except Exception:
            detalj_link = ""

        filer = []
        if detalj_link:
            detail_page = browser.new_page()
            try:
                detail_page.goto(detalj_link, timeout=15000)
                file_links = detail_page.query_selector_all("a")
                for fl in file_links:
                    href = fl.get_attribute("href")
                    tekst = fl.inner_text()
                    if href and "/api/presentation/v2/nye-innsyn/filer" in href:
                        abs_url = href if href.startswith("http") else "https://www.strand.kommune.no" + href
                        filer.append({"tekst": tekst, "url": abs_url})
            finally:
                detail_page.close()

        dokumenter.append({
            "tittel": tittel,
            "dato": dato,
            "dokumentID": dokid,
            "dokumenttype": doktype,
            "avsender_mottaker": am,
            "side": page_num,
            "detalj_link": detalj_link,
            "filer": filer,
            "status": "Publisert" if filer else "Må bes om innsyn"
        })
    page.close()
    return dokumenter

def update_json(new_docs):
    existing = load_existing()
    updated = dict(existing)

    for d in new_docs:
        doc_id = d["dokumentID"]
        if doc_id not in updated:
            print(f"[NEW] {doc_id} – {d['tittel']}")
            updated[doc_id] = d
        else:
            old = updated[doc_id]
            changed = (
                old.get("status") != d.get("status") or
                len(old.get("filer", [])) != len(d.get("filer", [])) or
                old.get("tittel") != d.get("tittel") or
                old.get("dokumenttype") != d.get("dokumenttype") or
                old.get("avsender_mottaker") != d.get("avsender_mottaker")
            )
            if changed:
                print(f"[UPDATE] {doc_id} – {d['tittel']}")
                updated[doc_id] = d

    data_list = list(updated.values())
    try:
        data_list.sort(key=lambda x: x.get("dato", ""), reverse=True)
    except Exception:
        pass

    save_json(data_list)
    print(f"[INFO] Lagret JSON med {len(data_list)} dokumenter")

def main(start_date=None, end_date=None):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page_num = 1
        all_docs = []
        while True:
            docs = hent_side(page_num, browser)
            if not docs:
                break
            for d in docs:
                try:
                    dt = datetime.strptime(d["dato"], "%d.%m.%Y").date()
                except Exception:
                    continue
                if start_date and end_date:
                    if start_date <= dt <= end_date:
                        all_docs.append(d)
                elif start_date:
                    if dt == start_date:
                        all_docs.append(d)
            page_num += 1
        browser.close()
        update_json(all_docs)

if __name__ == "__main__":
    # Eksempel: kjør med én dato
     main(start_date=datetime(2025,11,20).date())
    # Eksempel: kjør med periode
    # main(start_date=datetime(2025,11,20).date(), end_date=datetime(2025,11,27).date())
    pass
