"""Verified News and Weather Service for Project FRIDAY.

Fetches real-time, source-backed news across Indian national headlines, world affairs,
AI/tech, science, and weather metrics. Handles offline scenarios cleanly without hallucinating.
"""

import xml.etree.ElementTree as ET
import logging
import requests
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from app.config import config

logger = logging.getLogger(__name__)

# Reputable RSS feeds
NEWS_FEEDS: Dict[str, str] = {
    "India National": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "World Headlines": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "AI & Technology": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "Science & Space": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
}


@dataclass
class NewsItem:
    title: str
    summary: str
    link: str
    published: str
    category: str
    source: str


class NewsService:
    """Collects real-time, verified news and weather data."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def fetch_category_news(self, category: str, max_items: int = 3) -> List[NewsItem]:
        """Fetch news for a specific category from its RSS feed."""
        url = NEWS_FEEDS.get(category)
        if not url:
            return []

        items = []
        try:
            resp = requests.get(url, timeout=self.timeout, headers={"User-Agent": "FridayAssistant/1.0"})
            if resp.status_code != 200:
                logger.warning("Could not fetch news for %s: HTTP %s", category, resp.status_code)
                return []

            root = ET.fromstring(resp.content)
            # Find item elements in channel
            channel = root.find("channel")
            if channel is not None:
                source_title = channel.findtext("title", category)
                for item in channel.findall("item")[:max_items]:
                    title = item.findtext("title", "").strip()
                    desc = item.findtext("description", "").strip()
                    # Strip any raw HTML tags in description
                    desc_clean = desc.replace("<p>", "").replace("</p>", "").replace("<br>", " ")
                    if len(desc_clean) > 200:
                        desc_clean = desc_clean[:197] + "..."

                    link = item.findtext("link", "").strip()
                    pub_date = item.findtext("pubDate", "").strip()

                    if title:
                        items.append(
                            NewsItem(
                                title=title,
                                summary=desc_clean,
                                link=link,
                                published=pub_date,
                                category=category,
                                source=source_title,
                            )
                        )
        except Exception as e:
            logger.warning("Failed to fetch RSS news for %s: %s", category, e)

        return items

    def get_full_briefing_news(self, items_per_category: int = 2) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch headlines across all configured categories."""
        briefing: Dict[str, List[Dict[str, Any]]] = {}
        for cat in config.briefing.categories:
            if cat in NEWS_FEEDS:
                news_items = self.fetch_category_news(cat, max_items=items_per_category)
                briefing[cat] = [
                    {
                        "title": item.title,
                        "summary": item.summary,
                        "link": item.link,
                        "published": item.published,
                        "source": item.source,
                    }
                    for item in news_items
                ]
        return briefing

    def get_weather(self, city: Optional[str] = None) -> Dict[str, Any]:
        """Fetch weather metrics using the Open-Meteo free API."""
        target_city = city or config.briefing.weather_city or "Bengaluru"
        # Coordinates mapping for common Indian / world metros
        CITY_COORDS = {
            "bengaluru": (12.9716, 77.5946),
            "delhi": (28.6139, 77.2090),
            "mumbai": (19.0760, 72.8777),
            "hyderabad": (17.3850, 78.4867),
            "chennai": (13.0827, 80.2707),
            "london": (51.5074, -0.1278),
            "san francisco": (37.7749, -122.4194),
        }

        coords = CITY_COORDS.get(target_city.lower(), (12.9716, 77.5946))
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords[0]}&longitude={coords[1]}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"

        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                current = data.get("current", {})
                return {
                    "city": target_city.title(),
                    "temperature_c": current.get("temperature_2m"),
                    "humidity_percent": current.get("relative_humidity_2m"),
                    "wind_speed_kmh": current.get("wind_speed_10m"),
                }
        except Exception as e:
            logger.warning("Could not fetch weather: %s", e)

        return {"city": target_city.title(), "status": "Weather data currently unavailable"}


# Global singleton
news_service = NewsService()
