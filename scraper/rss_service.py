"""
PolyDelta RSS Feed Service

Flexible RSS fetcher serving both the AI Prediction Engine and User Chatbot.
- AI Analysis: recent data (last 24-48h) via lookback_hours parameter
- Chatbot: broader history (all available) via lookback_hours=None
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import feedparser
from dateutil import parser as dateutil_parser


class RSSFetcher:
    """Fetches and normalizes news from multiple RSS feeds."""

    FEEDS: Dict[str, str] = {
        # Football / Soccer
        "BBC_Football": "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "ESPN_FC": "https://www.espn.com/espn/rss/soccer/news",
        "Yardbarker_EPL": "https://www.yardbarker.com/rss/sport/premier_league",
        # UCL / International Football
        "Guardian_UCL": "https://www.theguardian.com/football/championsleague/rss",
        "SkySports_Football": "https://www.skysports.com/rss/11095",
        # NBA
        "Yardbarker_NBA": "https://www.yardbarker.com/rss/sport/nba",
        "HoopsHype_NBA": "https://feeds.hoopshype.com/xml/rumors.xml",
        "Rotoworld_NBA": "https://www.nbcsports.com/rss/basketball/nba",
        "RealGM_NBA": "https://basketball.realgm.com/rss/wiretap/0/0.xml",
        "NBC_Sports_Edge": "https://www.nbcsports.com/nba/news.atom",
    }

    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""
        clean = re.sub(r"<[^>]+>", "", text)
        return clean.strip()

    def _parse_date(self, entry) -> Optional[datetime]:
        """Parse published date from a feed entry, returning a timezone-aware datetime."""
        raw = entry.get("published") or entry.get("updated")
        if not raw:
            return None
        try:
            dt = dateutil_parser.parse(raw)
            # Ensure timezone-aware (assume UTC if naive)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            return None

    def fetch_news(
        self,
        source_keys: Optional[List[str]] = None,
        lookback_hours: Optional[int] = None,
    ) -> List[dict]:
        """
        Fetch news from RSS feeds.

        Args:
            source_keys: List of feed keys to fetch (e.g. ["BBC_Football"]).
                         If None, fetch all feeds.
            lookback_hours: Only return articles published within this many hours.
                            If None, return everything available in the feed.

        Returns:
            List of standardized article dicts sorted by published_at descending.
        """
        if source_keys is None:
            feeds_to_fetch = self.FEEDS
        else:
            feeds_to_fetch = {k: v for k, v in self.FEEDS.items() if k in source_keys}

        cutoff = None
        if lookback_hours is not None:
            cutoff = datetime.now(timezone.utc).replace(
                second=0, microsecond=0
            ) - timedelta(hours=lookback_hours)

        articles = []

        for source_name, feed_url in feeds_to_fetch.items():
            try:
                feed = feedparser.parse(feed_url)
            except Exception as e:
                print(f"[RSS] Failed to fetch {source_name}: {e}")
                continue

            for entry in feed.entries:
                published_at = self._parse_date(entry)

                # Apply lookback filter
                if cutoff is not None:
                    if published_at is None or published_at < cutoff:
                        continue

                summary = self._strip_html(
                    entry.get("summary") or entry.get("description") or ""
                )

                articles.append(
                    {
                        "title": entry.get("title", ""),
                        "summary": summary,
                        "url": entry.get("link", ""),
                        "source": source_name,
                        "published_at": published_at,
                        "published_str": (
                            published_at.strftime("%Y-%m-%d %H:%M")
                            if published_at
                            else "Unknown"
                        ),
                    }
                )

        # Sort newest first
        articles.sort(
            key=lambda a: a["published_at"] or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return articles
