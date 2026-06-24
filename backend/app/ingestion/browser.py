import time
from contextlib import contextmanager

from loguru import logger
from playwright.sync_api import Page, TimeoutError, sync_playwright
from seleniumbase import sb_cdp
from xvfbwrapper import Xvfb

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)

_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


@contextmanager
def browser_context(headless: bool = True):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(
            user_agent=_USER_AGENT,
            extra_http_headers=_HEADERS,
            java_script_enabled=True,
            bypass_csp=True,
        )
        try:
            yield ctx
        finally:
            browser.close()


@contextmanager
def seleniumbase_browser_context(timeout:int = 100):
    with _selenium_base_cdp_chrome(timeout=timeout) as sb:
        endpoint_url = sb.get_endpoint_url()
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(endpoint_url)
            ctx = browser.contexts[0]
            try:
                yield ctx
            finally:
                browser.close()
            
@contextmanager
def _selenium_base_cdp_chrome(url=None, **kwargs):
    kwargs.setdefault("sandbox", False)
    with Xvfb():
        sb = sb_cdp.Chrome(url, **kwargs)
        try:
            yield sb
        finally:
            sb.driver.quit()


def deny_consent_banner(page: Page, selector: str, timeout: int = 10000) -> None:
    try:
        deny_button = page.locator(selector)
        logger.info("Waiting for consent banner...")
        deny_button.wait_for(state="visible", timeout=timeout)
        deny_button.click()
        logger.success("Successfully clicked the 'Deny All' button.")
    except TimeoutError:
        logger.warning(
            f"Timeout: Consent banner did not appear within {timeout}ms. "
            "It may be disabled or already accepted."
        )


def scroll_to_top(page: Page) -> None:
    page.evaluate(
        """
        var intervalID = setInterval(function () {
            window.scrollBy(0, -window.innerHeight);
        }, 200);
        """
    )
    counter = 0
    while True:
        if page.evaluate("window.scrollY <= window.innerHeight"):
            logger.success("Reached the top of the page.")
            page.evaluate("clearInterval(intervalID)")
            break
        counter += 1
        logger.debug(f"Scrolling... counter={counter}")
        time.sleep(0.5)
