"""Browser Automation and Web Navigation for Project FRIDAY.

Provides authorized web navigation, default browser opening, and Playwright-backed
automation workflows with URL scheme validation.
"""

import webbrowser
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class BrowserAutomation:
    """Manages web browsing, searches, and Playwright workflows."""

    def open_url(self, url: str) -> Dict[str, Any]:
        """Open an authorized HTTP/HTTPS URL in the user's default browser."""
        clean_url = url.strip()
        parsed = urlparse(clean_url)

        if parsed.scheme not in ("http", "https"):
            return {
                "success": False,
                "error": f"Invalid URL scheme '{parsed.scheme}'. Only http and https are permitted.",
            }

        try:
            webbrowser.open(clean_url)
            logger.info("Opened URL in default browser: %s", clean_url)
            return {"success": True, "url": clean_url}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_web(self, query: str) -> Dict[str, Any]:
        """Execute a web search in the default browser."""
        import urllib.parse
        encoded = urllib.parse.quote_plus(query.strip())
        search_url = f"https://www.google.com/search?q={encoded}"
        return self.open_url(search_url)

    def extract_page_text(self, url: str, timeout_seconds: int = 15) -> Dict[str, Any]:
        """Fetch and extract visible text from a public web page via Playwright."""
        clean_url = url.strip()
        parsed = urlparse(clean_url)
        if parsed.scheme not in ("http", "https"):
            return {"success": False, "error": "Only http and https schemes are permitted."}

        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(clean_url, timeout=timeout_seconds * 1000)
                title = page.title()
                text = page.inner_text("body")
                browser.close()

                return {
                    "success": True,
                    "url": clean_url,
                    "title": title,
                    "content_preview": text[:2000],
                }
        except Exception as e:
            logger.warning("Playwright automation unavailable or failed: %s", e)
            return {
                "success": False,
                "error": f"Web extraction failed: {str(e)}",
            }


# Global singleton
browser_automation = BrowserAutomation()
