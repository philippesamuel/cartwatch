from contextlib import contextmanager

from playwright.sync_api import sync_playwright
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
            