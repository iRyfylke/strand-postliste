import time

def safe_goto(page, url, retries=4):
    for attempt in range(1, retries + 1):
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            return True
        except Exception as e:
            print(f"[WARN] goto-feil (forsøk {attempt}/{retries}) mot {url}: {e}")
            if attempt < retries:
                time.sleep(2 * attempt)
            else:
                print(f"[ERROR] Klarte ikke åpne URL etter {retries} forsøk: {url}")
                return False

def safe_text(el, sel):
    try:
        node = el.query_selector(sel)
        return node.inner_text().strip() if node else ""
    except:
        return ""
