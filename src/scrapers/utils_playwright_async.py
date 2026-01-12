import asyncio
from playwright.async_api import TimeoutError as PlaywrightTimeout


# ---------------------------------------------------------
# SAFE TEXT
# ---------------------------------------------------------
async def safe_text(element, selector, timeout=3000):
    """
    Robust async-versjon av safe_text:
    - hard timeout rundt hele operasjonen
    - håndterer None-elementer
    - håndterer None-selectors
    - returnerer alltid en ren string
    """

    if element is None or not selector:
        return ""

    try:
        return await asyncio.wait_for(_safe_text_inner(element, selector), timeout / 1000)
    except Exception:
        return ""


async def _safe_text_inner(element, selector):
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


# ---------------------------------------------------------
# SAFE GOTO
# ---------------------------------------------------------
async def safe_goto(page, url, retries=3, timeout=10000):
    """
    Deadlock-sikker versjon av safe_goto:
    - hard timeout rundt page.goto
    - aborterer navigasjon ved heng
    - retry med eksponentiell backoff
    - returnerer False ved feil
    """

    if not url:
        print("[ERROR] safe_goto: URL mangler")
        return False

    for attempt in range(1, retries + 1):
        try:
            # HARD TIMEOUT RUNDT HELE GOTO
            await asyncio.wait_for(
                page.goto(url, timeout=timeout, wait_until="domcontentloaded"),
                timeout=timeout / 1000 + 2,  # ekstra margin
            )
            return True

        except (PlaywrightTimeout, asyncio.TimeoutError):
            print(f"[WARN] safe_goto timeout (forsøk {attempt}/{retries}) mot {url}")

        except Exception as e:
            print(f"[WARN] safe_goto feilet (forsøk {attempt}/{retries}) mot {url}: {e}")

        # Abort navigation hvis Playwright sitter fast
        try:
            await page.evaluate("() => window.stop()")
        except Exception:
            pass

        # Backoff
        try:
            await page.wait_for_timeout(200 + attempt * 150)
        except Exception:
            pass

    print(f"[ERROR] safe_goto: Klarte ikke åpne URL etter {retries} forsøk: {url}")
    return False
