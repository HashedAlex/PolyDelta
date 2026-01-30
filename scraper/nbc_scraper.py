"""
NBC Sports Edge NBA Player News Scraper

Fetches NBA player news and injury reports from NBC Sports via their Atom feed.
Outputs in the same standardized format as RSSFetcher for seamless integration.
"""

from typing import List, Optional

from .rss_service import RSSFetcher


class NBCScraper:
    """
    Scraper for NBC Sports Edge NBA player news.

    Uses the NBC Sports Atom feed (https://www.nbcsports.com/nba/news.atom)
    via the centralized RSSFetcher, ensuring a single source of truth for
    all feed URLs and consistent data normalization.
    """

    SOURCE_KEY = "NBC_Sports_Edge"

    def __init__(self):
        self._fetcher = RSSFetcher()

    def fetch_news(self, lookback_hours: Optional[int] = 24) -> List[dict]:
        """
        Fetch NBA player news from NBC Sports Edge.

        Args:
            lookback_hours: Only return articles within this window.
                            Defaults to 24. Pass None for all available.

        Returns:
            List of standardized article dicts (same format as RSSFetcher).
        """
        return self._fetcher.fetch_news(
            source_keys=[self.SOURCE_KEY],
            lookback_hours=lookback_hours,
        )
