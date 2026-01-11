from playwright.async_api import async_playwright

async def create_playwright_context(block_resources=True):
    """
    Oppretter Playwright browser + context med optimaliserte innstillinger.
    Returnerer (browser, context).
    """

    p = await async_playwright().start()

    browser = await p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
        ],
    )

    context = await browser.new_context()

    if block_resources:
        async def _block(route):
            if route.request.resource_type in ["image", "media"]:
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", _block)

    return p, browser, context
