# utils_playwright_async.py

async def safe_text(element, selector):
    """
    Robust async-versjon av safe_text:
    - håndterer None-elementer
    - håndterer None-selectors
    - bruker try/except rundt alle await-kall
    - returnerer alltid en ren string
    """
    if element is None or not selector:
        return ""

    try:
        handle = await element.query_selector(selector)
        if not handle:
            return ""
    except Exception:
        return ""

    try:
        txt = await handle.inner_text()
        return txt.strip() if txt else ""
    except Exception:
        return ""


async def safe_goto(page, url, retries=3, timeout=10000):
    """
    Robust async-versjon av safe_goto:
    - retry ved feil
    - kort ventetid mellom forsøk
    - eksplisitt logging
    - returnerer False hvis alle forsøk feiler
    """
    if not url:
        print("[ERROR] safe_goto: URL mangler")
        return False

    for attempt in range(1, retries + 1):
        try:
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            return True

        except Exception as e:
            print(f"[WARN] safe_goto feilet (forsøk {attempt}/{retries}) mot {url}: {e}")

            # Kort pause før nytt forsøk
            try:
                await page.wait_for_timeout(200 + attempt * 100)
            except Exception:
                pass

    print(f"[ERROR] safe_goto: Klarte ikke åpne URL etter {retries} forsøk: {url}")
    return False
