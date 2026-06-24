"""
Minimal smoke-test flow to verify scraping works from an ECS environment.

Scrapes a single REWE store and logs what it found. Does NOT upload to Supabase.
Check the Prefect UI / CloudWatch logs for the output.

Indicators of bot detection:
  - page title contains "captcha", "robot", "blocked", "access denied"
  - articles_found == 0 despite a valid URL
  - cookie_banner_found == False (page never fully loaded)
"""

from prefect import flow, get_run_logger

from ingestion.browser import browser_context
from ingestion.offers.rewe_scrapper import deny_usercentrics_banner

_TEST_STORE_URL = (
    "https://www.rewe.de/angebote/berlin-wedding/1765982/rewe-markt-muellerstr-141/"
)


@flow(name="test-ecs-scraping")
def test_ecs_scraping_flow(url: str = _TEST_STORE_URL) -> dict:
    logger = get_run_logger()
    logger.info("Starting ECS scraping smoke test against: {}", url)

    with browser_context(headless=True) as ctx:
        page = ctx.new_page()
        response = page.goto(url, wait_until="domcontentloaded", timeout=30_000)

        status_code = response.status if response else None
        title = page.title()
        logger.info("HTTP status: {} | Page title: {}", status_code, title)

        # Check for bot detection signals in the title
        bot_signals = ["captcha", "robot", "blocked", "access denied", "403", "429"]
        title_lower = title.lower()
        bot_detected = any(signal in title_lower for signal in bot_signals)
        if bot_detected:
            logger.warning("Possible bot detection! Title suggests a block page.")

        # Try to dismiss the cookie banner
        try:
            deny_usercentrics_banner(page)
            cookie_banner_found = True
        except Exception as e:
            logger.warning("Cookie banner handling failed: {}", e)
            cookie_banner_found = False

        # Wait a moment for content to settle after banner dismissal
        page.wait_for_timeout(2000)

        # Count articles as the key signal that real content loaded
        articles = page.locator("article").all()
        articles_found = len(articles)
        logger.info("Articles found: {}", articles_found)

        # Grab a small snippet of the main content for visual inspection
        try:
            main_html_snippet = page.locator("main").inner_html()[:500]
        except Exception:
            main_html_snippet = "(could not read main element)"

    result = {
        "url": url,
        "http_status": status_code,
        "page_title": title,
        "cookie_banner_found": cookie_banner_found,
        "articles_found": articles_found,
        "bot_detected": bot_detected,
        "main_html_snippet": main_html_snippet,
    }

    logger.info("Smoke test result: {}", result)

    if articles_found == 0:
        logger.error("No articles found — scraping likely blocked or page failed to load.")
    else:
        logger.info("SUCCESS! Scraping looks healthy: {} articles found.", articles_found)

    return result


if __name__ == "__main__":
    test_ecs_scraping_flow()
