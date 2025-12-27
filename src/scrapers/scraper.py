from playwright.sync_api import sync_playwright
import json, os, time
from datetime import datetime, date

# Oppdaterte filstier etter omstrukturering
CONFIG_FILE = "src/config/config.json"
DATA_FILE = "data/postliste.json"
CHANGES_FILE = "data/changes.json"

BASE_URL = "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/?page={page}&pageSize=100"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "mode": "incremental",
        "max_pages_incremental": 10,
        "max_pages_update": 200,
        "max_pages_full": 500,
        "per_page": 50
    }

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return {d["dokumentID"]: d for d in json.load(f) if "dokumentID" in d}
            except Exception:
                return {}
    return {}

def load_changes():
    if os.path.exists(CHANGES_FILE):
        with open(CHANGES_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return data if isinstance(data, list) else []
            except Exception:
                return []
    return []

def save_changes(changes):
    with open(CHANGES_FILE, "w", encoding="utf-8") as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)

def safe_text(el, sel):
    try:
        node = el.query_selector(sel)
        return node.inner_text().strip() if node else ""
    except Exception:
        return ""

def parse_dato(s):
    """Parse dato og returner både norsk og ISO."""
    if not s:
        return None, None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            dt = datetime.strptime(s, fmt).date()
            return dt.strftime("%d.%m.%Y"), dt.strftime("%Y-%m-%d")
        except Exception:
            continue
    try:
        dt = datetime.fromisoformat(s[:10]).date()
        return dt.strftime("%d.%m.%Y"), dt.strftime("%Y-%m-%d")
    except Exception:
        return None, None

def hent_side(page_num, browser):
    url = BASE_URL.format(page=page_num)
    print(f"[INFO] Åpner side {page_num}")
    page = browser.new_page()
    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        time.sleep(2)
        page.wait_for_selector("article.bc-content-teaser--item", timeout=10000)
    except Exception:
        page.close()
        return []
    docs = []
    for art in page.query_selector_all("article.bc-content-teaser--item"):
        dokid = safe_text(art, ".bc-content-teaser-meta-property--dokumentID dd")
        if not dokid:
            continue
        tittel = safe_text(art, ".bc-content-teaser-title-text")
        dato_raw = safe_text(art, ".bc-content-teaser-meta-property--dato dd")
        dato_norsk, dato_iso = parse_dato(dato_raw)
        doktype = safe_text(art, ".SakListItem_sakListItemTypeText__16759c")
        avsender = safe_text(art, ".bc-content-teaser-meta-property--avsender dd")
        mottaker = safe_text(art, ".bc-content-teaser-meta-property--mottaker dd")
        am = f"Avsender: {avsender}" if avsender else (f"Mottaker: {mottaker}" if mottaker else "")
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
                dp.goto(detalj_link, timeout=60000, wait_until="domcontentloaded")
                time.sleep(2)
                for fl in dp.query_selector_all("a"):
                    href, tekst = fl.get_attribute("href"), fl.inner_text()
                    if href and "/api/presentation/v2/nye-innsyn/filer" in href:
                        abs_url = href if href.startswith("http") else "https://www.strand.kommune.no" + href
                        filer.append({"tekst": tekst.strip(), "url": abs_url})
            finally:
                dp.close()
        status = "Publisert" if filer else "Må bes om innsyn"
        docs.append({
            "tittel": tittel,
            "dato": dato_norsk or "",
            "dato_iso": dato_iso or None,
            "dokumentID": dokid,
            "dokumenttype": doktype,
            "avsender_mottaker": am,
            "side": page_num,
            "detalj_link": detalj_link,
            "filer": filer,
            "status": status
        })
    page.close()
    return docs

def main():
    print("[INFO] Starter scraper…")
    config = load_config()
    mode = config.get("mode", "incremental")
    max_pages = int(config.get(f"max_pages_{mode}", 50))
    existing = load_existing()
    updated = dict(existing)
    changes = load_changes()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for page_num in range(1, max_pages + 1):
            docs = hent_side(page_num, browser)
            if not docs:
                break
            for d in docs:
                doc_id = d["dokumentID"]
                old = updated.get(doc_id)
                if not old:
                    updated[doc_id] = d
                    changes.append({
                        "tidspunkt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "type": "NEW",
                        "dokumentID": doc_id,
                        "tittel": d.get("tittel"),
                        "endringer": {
                            "status": {"gammel": None, "ny": d.get("status")},
                            "tittel": {"gammel": None, "ny": d.get("tittel")},
                            "dokumenttype": {"gammel": None, "ny": d.get("dokumenttype")},
                            "avsender_mottaker": {"gammel": None, "ny": d.get("avsender_mottaker")},
                            "detalj_link": {"gammel": None, "ny": d.get("detalj_link")},
                            "dato": {"gammel": None, "ny": d.get("dato")},
                            "dato_iso": {"gammel": None, "ny": d.get("dato_iso")},
                            "filer_count": {"gammel": 0, "ny": len(d.get("filer", []))}
                        }
                    })
                    print(f"[NEW] {doc_id} – {d['tittel']}")
                else:
                    per_change = {}
                    for key in ["status", "tittel", "dokumenttype", "avsender_mottaker", "detalj_link", "dato", "dato_iso"]:
                        if old.get(key) != d.get(key):
                            per_change[key] = {"gammel": old.get(key), "ny": d.get(key)}
                    old_files = old.get("filer", [])
                    new_files = d.get("filer", [])
                    if len(old_files) != len(new_files):
                        per_change["filer_count"] = {"gammel": len(old_files), "ny": len(new_files)}
                    if per_change:
                        changes.append({
                            "tidspunkt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "UPDATE",
                            "dokumentID": doc_id,
                            "tittel": d.get("tittel"),
                            "endringer": per_change
                        })
                        print(f"[UPDATE] {doc_id} – {', '.join(per_change.keys())}")
                    updated[doc_id] = d

            if mode == "incremental":
                if all(d["dokumentID"] in existing for d in docs):
                    print("[INFO] Incremental: Stoppet – alle oppføringer på denne siden er kjente.")
                    break
        browser.close()

    def sort_key(x):
        try:
            return datetime.strptime(x.get("dato"), "%d.%m.%Y").date()
        except Exception:
            return date.min

    data_list = sorted(updated.values(), key=sort_key, reverse=True)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data_list, f, ensure_ascii=False, indent=2)
    save_changes(changes)

    print(f"[INFO] Lagret JSON med {len(data_list)} dokumenter")
    print(f"[INFO] Logget {len(changes)} endringshendelser i {CHANGES_FILE}")

if __name__ == "__main__":
    main()
