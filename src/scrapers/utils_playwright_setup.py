from playwright.async_api import async_playwright

async def create_playwright_context(block_resources=False):
    """
    Oppretter Playwright browser + context med stealth-mode og ekte fingerprint.
    Returnerer (p, browser, context).
    """

    p = await async_playwright().start()

    # Ekte Chrome user-agent (Windows 10, norsk)
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.6099.200 Safari/537.36"
    )

    browser = await p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
        ],
    )

    context = await browser.new_context(
        user_agent=USER_AGENT,
        locale="nb-NO",
        timezone_id="Europe/Oslo",
        viewport={"width": 1366, "height": 768},
        device_scale_factor=1.0,
        color_scheme="light",
        permissions=[],
        java_script_enabled=True,
        extra_http_headers={
            "Accept-Language": "nb-NO,nb;q=0.9,en;q=0.8",
            "Referer": "https://www.strand.kommune.no/",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
        },
    )

    # ---------------------------------------------------------
    # STEALTH PATCHES (anti-bot)
    # ---------------------------------------------------------
    await context.add_init_script("""
        // Skjul webdriver-flagget
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
        });

        // Fake plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3],
        });

        // Fake languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['nb-NO', 'nb', 'en'],
        });

        // Fake Chrome runtime
        window.chrome = {
            runtime: {},
        };

        // Fake permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters)
        );

        // Fake user activation
        Object.defineProperty(navigator, 'userActivation', {
            get: () => ({ hasBeenActive: true, isActive: true }),
        });
    """)

    # ---------------------------------------------------------
    # IKKE blokker bilder i stealth-mode
    # Kommunens bot-filter reagerer på manglende ressurser
    # ---------------------------------------------------------
    if block_resources:
        async def _block(route):
            if route.request.resource_type in ["media"]:
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", _block)

    return p, browser, context
