from playwright.sync_api import sync_playwright
import json, os
from datetime import datetime

CONFIG_FILE = "config.json"
DATA_FILE = "postliste.json"
BASE_URL = "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/postliste-dokumenter-og-vedtak/sok-i-post-dokumenter-og-saker/#/?page={page}&pageSize=100"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    return {"mode":"incremental","max_pages_incremental":5,"max_pages_update":200,"max_pages_full":500,"per_page":50}

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE,"r",encoding="utf-8") as f:
            try: return {d["dokumentID"]:d for d in json.load(f) if "dokumentID" in d}
            except: return {}
    return {}

def safe_text(el,sel):
    try: node=el.query_selector(sel); return node.inner_text().strip() if node else ""
    except: return ""

def format_dato(s):
    try: return datetime.strptime(s,"%Y-%m-%d").strftime("%d.%m.%Y")
    except: return s

def hent_side(page_num,browser):
    url=BASE_URL.format(page=page_num); print(f"[INFO] Åpner side {page_num}")
    page=browser.new_page()
    try:
        page.goto(url,timeout=15000); page.wait_for_selector("article.bc-content-teaser--item",timeout=5000)
    except: page.close(); return []
    docs=[]
    for art in page.query_selector_all("article.bc-content-teaser--item"):
        dokid=safe_text(art,".bc-content-teaser-meta-property--dokumentID dd")
        if not dokid: continue
        tittel=safe_text(art,".bc-content-teaser-title-text")
        dato=format_dato(safe_text(art,".bc-content-teaser-meta-property--dato dd"))
        doktype=safe_text(art,".SakListItem_sakListItemTypeText__16759c")
        avsender=safe_text(art,".bc-content-teaser-meta-property--avsender dd")
        mottaker=safe_text(art,".bc-content-teaser-meta-property--mottaker dd")
        am=f"Avsender: {avsender}" if avsender else f"Mottaker: {mottaker}" if mottaker else ""
        detalj_link=""; filer=[]
        try:
            link_elem=art.evaluate_handle("node => node.closest('a')")
            detalj_link=link_elem.get_attribute("href") if link_elem else ""
        except: pass
        if detalj_link:
            dp=browser.new_page()
            try:
                dp.goto(detalj_link,timeout=15000)
                for fl in dp.query_selector_all("a"):
                    href,tekst=fl.get_attribute("href"),fl.inner_text()
                    if href and "/api/presentation/v2/nye-innsyn/filer" in href:
                        abs_url=href if href.startswith("http") else "https://www.strand.kommune.no"+href
                        filer.append({"tekst":tekst,"url":abs_url})
            finally: dp.close()
        status="Publisert" if filer else "Må bes om innsyn"
        docs.append({"tittel":tittel,"dato":dato,"dokumentID":dokid,"dokumenttype":doktype,
                     "avsender_mottaker":am,"side":page_num,"detalj_link":detalj_link,
                     "filer":filer,"status":status})
    page.close(); return docs

def main():
    print("[INFO] Starter scraper…")
    config=load_config(); mode=config.get("mode","incremental")
    max_pages=config.get(f"max_pages_{mode}",50)
    existing=load_existing(); updated=dict(existing)

    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        for page_num in range(1,max_pages+1):
            docs=hent_side(page_num,browser)
            if not docs: break
            for d in docs:
                doc_id=d["dokumentID"]; old=updated.get(doc_id)
                if not old or any(old.get(k)!=d.get(k) for k in ["status","tittel","dokumenttype","avsender_mottaker"]) or len(old.get("filer",[]))!=len(d.get("filer",[])):
                    updated[doc_id]=d
                    print(f"[{'NEW' if not old else 'UPDATE'}] {doc_id} – {d['tittel']}")
            if mode=="incremental" and any(d["dokumentID"] in existing for d in docs):
                print("[INFO] Incremental: Stoppet – fant eksisterende oppføring på denne siden."); break
        browser.close()

    data_list=sorted(updated.values(),key=lambda x:x.get("dato",""),reverse=True)
    with open(DATA_FILE,"w",encoding="utf-8") as f: json.dump(data_list,f,ensure_ascii=False,indent=2)
    print(f"[INFO] Lagret JSON med {len(data_list)} dokumenter")

if __name__=="__main__": main()
