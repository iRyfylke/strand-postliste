# utils_playwright_sync.py

def safe_text(element, selector):
    """
    Synkron, robust tekstuthenting:
    - returnerer alltid en string
    - håndterer manglende elementer og exceptions
    """
    if element is None or not selector:
        return ""

    try:
        handle = element.query_selector(selector)
        if not handle:
            return ""
        txt = handle.inner_text()
        return txt.strip() if txt else ""
    except Exception:
        return ""


def safe_goto(page, url, retries=3, timeout=10_000):
    """
    Synkron, robust goto:
    - retry ved feil
    - kort ventetid mellom forsøk
    - returnerer False hvis alle forsøk feiler
    """
    if not url:
        print("[ERROR] safe_goto: URL mangler")
        return False

    for attempt in range(1, retries + 1):
        try:
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            return True
        except Exception as e:
            print(f"[WARN] safe_goto feilet ({attempt}/{retries}) mot {url}: {e}")
            try:
                page.wait_for_timeout(200 + attempt * 100)
            except Exception:
                pass

    print(f"[ERROR] safe_goto: Klarte ikke åpne URL etter {retries} forsøk: {url}")
    return False
