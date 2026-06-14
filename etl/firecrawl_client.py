"""Thin HTTP client for the Firecrawl scrape API.

Wraps a single ``POST /scrape`` call and returns the response JSON. All network
behaviour is isolated here so the rest of the ETL pipeline can be tested with
fixtures and mocks.
"""

from __future__ import annotations

import requests

from core.config import Settings
from core.exceptions import ETLError


class FirecrawlClient:
    """Minimal Firecrawl client returning scraped page payloads."""

    def __init__(self, settings: Settings) -> None:
        """Store settings used for auth, base URL, and timeouts.

        Args:
            settings: Application settings supplying Firecrawl configuration.
        """
        self._settings = settings

    def scrape(self, url: str) -> dict:
        """Scrape a single URL and return the raw Firecrawl response JSON.

        Args:
            url: The page URL to scrape.

        Returns:
            The parsed JSON body returned by Firecrawl.

        Raises:
            ETLError: On missing API key, HTTP errors, timeouts, or bad JSON.
        """
        if not self._settings.firecrawl_api_key:
            raise ETLError("FIRECRAWL_API_KEY is not configured.")

        endpoint = f"{self._settings.firecrawl_base_url.rstrip('/')}/scrape"
        headers = {
            "Authorization": f"Bearer {self._settings.firecrawl_api_key}",
            "Content-Type": "application/json",
        }
        payload = {"url": url, "formats": ["markdown", "html"]}

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self._settings.firecrawl_timeout_seconds,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            raise ETLError(f"Firecrawl scrape failed for {url}: {exc}") from exc
        except ValueError as exc:  # JSON decode
            raise ETLError(f"Firecrawl returned invalid JSON for {url}: {exc}") from exc
