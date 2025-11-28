from playwright.sync_api import sync_playwright
import json, os, sys
from datetime import datetime

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

# Funksjon for å velge dato i date-picker
def velg_dato(page, dato, felt_selector):
    måneder = ["Januar","Februar","Mars","April","Mai","Juni","Juli","August","September","Oktober","November","Desember"]

    # Klikk i inputfeltet for å åpne date-picker
    page.click(felt_selector)

    # Klikk på måned/år-velger
    page.click("div.bc-datepicker-header-month")

    # Velg år
    page.click(f"div.datePicker-module__years_9333_U1RF0 div:has-text('{dato.year}')")

    # Velg måned
    page.click(f"div.datePicker-module__months_9333_QuMa8 div:has-text('{måneder[dato.month-1]}')")

    # Velg dag
    page.click(f"div.datePicker-module__days_9333_vpqVw div:has-text('{dato.day}')")

def main(start_date=None, end_date=None):
    print("[INFO] Starter scraper_dates…")
    all_docs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(BASE_URL, timeout=20000)

        # Vent til backdrop er fjernet
        try:
            page.wait_for_selector("div.bc-content-modal-backdrop", state="detached", timeout=10000)
        except Exception:
            pass

        # Klikk radioknappen "Velg periode"
        page.click("input[type='radio'][value='Other']", force=True)

        # Velg fra- og til-dato via date-picker
        if start_date:
            velg_dato(page, start_date, "input[id*='Dato'][id*='start']")
        if end_date:
            velg_dato(page, end_date, "input[id*='Dato'][id*='end']")

        # Klikk på "Ferdig" i date-picker
        page.click("button:has-text('Ferdig')")

        # Vent på resultater
        page.wait_for_selector("article.bc-content-teaser--item", timeout=10000)

        # Iterer gjennom sider med filtrerte resultater
        page_num = 1
        while True:
            url = f"{BASE_URL}?page={page_num}&pageSize=100"
            docs = hent_side(url, browser)
            if not docs:
                break
            all_docs.extend(docs)
            page_num += 1

        browser.close()

    update_json(all_docs)

if __name__ == "__main__":
    args = sys.argv[1:]
    start_date = None
    end_date = None

    if len(args) >= 1 and args[0]:
        start_date = datetime.strptime(args[0], "%Y-%m-%d").date()
    if len(args) >= 2 and args[1]:
        end_date = datetime.strptime(args[1], "%Y-%m-%d").date()

    main(start_date=start_date, end_date=end_date)
