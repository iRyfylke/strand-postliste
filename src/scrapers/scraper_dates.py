import json, os, sys
from datetime import datetime, date
from playwright.sync_api import sync_playwright

DATA_FILE = "postliste.json"
CONFIG_FILE = "config.json"
BASE_URL = "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    raise FileNotFoundError(f"{CONFIG_FILE} mangler – opprett filen med nødvendige innstillinger.")

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

def parse_dato_str(s):
    """Prøver å tolke dato fra streng i ulike formater."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        pass
    try:
        return datetime.strptime(s, "%d.%m.%Y").date()
    except Exception:
        pass
    try:
        return datetime.fromisoformat(s[:10]).date()
    except Exception:
        return None

def format_dato_ddmmYYYY(d):
    """Formatterer datoobjekt til dd.mm.yyyy."""
    return d.strftime("%d.%m.%Y") if d else ""

def hent_side(url, browser):
    page = browser.new_page()
    docs = []
    try:
        page.goto(url, timeout=20000)
        page.wait_for_selector("article.bc-content-teaser--item", timeout=8000)
    except Exception:
        page.close()
        return docs

    for art in page.query_selector_all("article.bc-content-teaser--item"):
        dokid = safe_text(art, ".bc-content-teaser-meta-property--dokumentID dd")
        if not dokid:
            continue
        tittel = safe_text(art, ".bc-content-teaser-title-text")
        dato_str = safe_text(art, ".bc-content-teaser-meta-property--dato dd")
        parsed_date = parse_dato_str(dato_str)
        doktype = safe_text(art, ".SakListItem_sakListItemTypeText__16759c")
        avsender = safe_text(art, ".bc-content-teaser-meta-property--avsender dd")
        mottaker = safe_text(art, ".bc-content-teaser-meta-property--mottaker dd")
        am = f"Avsender: {avsender}" if avsender else (f"Mottaker: {mottaker}" if mottaker else "")

        detalj_link = ""
        try:
            link_elem = art.evaluate_handle("node => node.closest('a')")
            detalj_link = link_elem.get_attribute("href") if link_elem else ""
        except Exception:
            detalj_link = ""
        if detalj_link and not detalj_link.startswith("http"):
            detalj_link = "https://www.strand.kommune.no" + detalj_link

        filer = []
        if detalj_link:
            dp = browser.new_page()
            try:
                dp.goto(detalj_link, timeout=20000)
                for fl in dp.query_selector_all("a"):
                    href, tekst = fl.get_attribute("href"), fl.inner_text()
                    if href and "/api/presentation/v2/nye-innsyn/filer" in href:
                        abs_url = href if href.startswith("http") else "https://www.strand.kommune.no" + href
                        filer.append({"tekst": tekst.strip(), "url": abs_url})
            except Exception:
                pass
            finally:
                dp.close()

        status = "Publisert" if filer else "Må bes om innsyn"

        docs.append({
            "tittel": tittel,
            "dato": format_dato_ddmmYYYY(parsed_date),   # alltid dd.mm.yyyy
            "dato_iso": parsed_date.isoformat() if parsed_date else None,  # ISO lagres også
            "dokumentID": dokid,
            "dokumenttype": doktype,
            "avsender_mottaker": am,
            "journal_link": detalj_link,
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
        changed_files = len(old.get("filer", [])) != len(d.get("filer", [])) if old else True
        changed_core = any(old.get(k) != d.get(k) for k in ["status","tittel","dokumenttype","avsender_mottaker","journal_link"]) if old else True
        if not old or changed_files or changed_core:
            updated[doc_id] = d
            print(f"[{'NEW' if not old else 'UPDATE'}] {doc_id} – {d['tittel']}")

    def sort_key(x):
        # Sortering basert på norsk format dd.mm.yyyy
        try:
            return datetime.strptime(x.get("dato"), "%d.%m.%Y").date()
        except Exception:
            return date.min

    data_list = sorted(updated.values(), key=sort_key, reverse=True)
    save_json(data_list)
    print(f"[INFO] Lagret JSON med {len(data_list)} dokumenter")

def within_range(d, start_date, end_date):
    if d is None:
        return False
    if start_date and d < start_date:
        return False
    if end_date and d > end_date:
        return False
    return True

def main(start_date=None, end_date=None):
    print("[INFO] Starter scraper_dates…")
    all_docs = []
    cfg = load_config()
    max_pages = int(cfg.get("max_pages_full", 200))
    per_page = int(cfg.get("per_page", 100))

    print(f"[INFO] Konfigurasjon fra config.json: max_pages_full={max_pages}, per_page={per_page}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page_num = 1
        while page_num <= max_pages:
            print(f"[INFO] Henter side {page_num} …")
            url = f"{BASE_URL}?page={page_num}&pageSize={per_page}"
            docs = hent_side(url, browser)
            if not docs:
                break
            for d in docs:
                pd = parse_dato_str(d.get("dato"))
                if within_range(pd, start_date, end_date):
                    all_docs.append(d)
            parsed_on_page = [parse_dato_str(x.get("dato")) for x in docs if x.get("dato")]
            if start_date and parsed_on_page and all(x and x < start_date for x in parsed_on_page):
                print(f"[INFO] Tidlig stopp: alle datoer på side {page_num} er eldre enn start_date")
                break
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
    if start_date and not end_date:
        end_date = start_date
    main(start_date=start_date, end_date=end_date)
