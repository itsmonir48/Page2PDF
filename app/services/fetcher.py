"""
Page2PDF — Content Fetcher
Fetches webpage content via HTTP or headless browser.
"""

import os
import logging
import httpx
from typing import Optional, Tuple

from app.services.security import validate_url_security, validate_redirect_url

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_PAGE_SIZE_MB = int(os.getenv("MAX_PAGE_SIZE_MB", "20"))
MAX_REDIRECTS = int(os.getenv("MAX_REDIRECTS", "5"))
MAX_PAGE_SIZE_BYTES = MAX_PAGE_SIZE_MB * 1024 * 1024

# Headers to mimic a real browser
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


async def fetch_with_http(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch webpage content using httpx.
    Returns (html_content, error_message).
    """
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(REQUEST_TIMEOUT),
            follow_redirects=True,
            max_redirects=MAX_REDIRECTS,
            headers=DEFAULT_HEADERS,
            verify=True,
        ) as client:
            response = await client.get(url)

            # Validate redirect chain
            for redirect in response.history:
                redirect_url = str(redirect.headers.get("location", ""))
                if redirect_url:
                    is_safe, error = validate_redirect_url(redirect_url)
                    if not is_safe:
                        return None, f"Redirect blocked: {error}"

            # Check status code
            if response.status_code == 403:
                return None, "This website blocked automated access (403 Forbidden)."
            elif response.status_code == 404:
                return None, "The page was not found (404)."
            elif response.status_code == 429:
                return None, "Too many requests. Please try again later."
            elif response.status_code >= 400:
                return None, f"The webpage returned an error (HTTP {response.status_code})."

            # Check content size
            content_length = len(response.content)
            if content_length > MAX_PAGE_SIZE_BYTES:
                return None, f"The webpage is too large to process ({content_length / 1024 / 1024:.1f} MB)."

            # Check content type
            content_type = response.headers.get("content-type", "")
            if not any(ct in content_type.lower() for ct in ["text/html", "application/xhtml", "text/plain"]):
                return None, f"Unsupported content type: {content_type}"

            # Decode content
            html = response.text
            if not html or len(html.strip()) < 100:
                return None, "The webpage returned very little content."

            return html, None

    except httpx.TimeoutException:
        return None, "The webpage took too long to respond. Please try again."
    except httpx.TooManyRedirects:
        return None, "Too many redirects. The URL may be invalid."
    except httpx.ConnectError:
        return None, "Unable to connect to the server. Please check the URL."
    except httpx.RequestError as e:
        logger.error(f"HTTP request error for {url}: {e}")
        return None, "Unable to access this webpage. Please check the URL."
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}")
        return None, "An unexpected error occurred while fetching the webpage."


async def fetch_with_playwright(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch webpage content using Playwright (headless browser).
    Used for JavaScript-heavy pages.
    Returns (html_content, error_message).
    """
    enable_playwright = os.getenv("ENABLE_PLAYWRIGHT", "true").lower() == "true"
    if not enable_playwright:
        return None, "JavaScript rendering is not enabled on this server."

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("Playwright is not installed. JS rendering unavailable.")
        return None, "JavaScript rendering is not available."

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            )
            context = await browser.new_context(
                user_agent=DEFAULT_HEADERS["User-Agent"],
                viewport={"width": 1280, "height": 720},
            )
            page = await context.new_page()

            # Navigate with timeout
            try:
                await page.goto(url, wait_until="networkidle", timeout=REQUEST_TIMEOUT * 1000)
            except Exception:
                # Try with domcontentloaded as fallback
                await page.goto(url, wait_until="domcontentloaded", timeout=REQUEST_TIMEOUT * 1000)

            # Wait for content to load
            await page.wait_for_timeout(2000)

            # Get page content
            html = await page.content()

            await browser.close()

            if not html or len(html.strip()) < 100:
                return None, "No meaningful content found even with JavaScript rendering."

            return html, None

    except Exception as e:
        logger.error(f"Playwright error for {url}: {e}")
        return None, "Failed to render the page with JavaScript. The page may require authentication or be blocked."


async def fetch_webpage(url: str) -> Tuple[Optional[str], Optional[str], str]:
    """
    Main fetch function. Tries HTTP first, falls back to Playwright if needed.
    Returns (html_content, error_message, fetch_method).
    """
    # Validate URL security first
    is_safe, security_error = validate_url_security(url)
    if not is_safe:
        return None, security_error, "none"

    # Try HTTP first
    html, error = await fetch_with_http(url)
    if html:
        return html, None, "http"

    # If HTTP fails with access denied, try Playwright
    if error and any(keyword in error.lower() for keyword in ["blocked", "forbidden", "javascript"]):
        logger.info(f"HTTP fetch failed for {url}, trying Playwright: {error}")
        html_pw, error_pw = await fetch_with_playwright(url)
        if html_pw:
            return html_pw, None, "playwright"
        # Return the Playwright error if it also failed
        return None, error_pw or error, "none"

    return None, error, "none"
