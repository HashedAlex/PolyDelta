"""
EPL Injury Scraper

Fetches Premier League injury and suspension data from sportsgambler.com.
Outputs in the same standardized format as RSSFetcher for seamless integration.
"""

from datetime import datetime, timezone
from typing import List

import requests
from bs4 import BeautifulSoup

TARGET_URL = "https://www.sportsgambler.com/injuries/football/england-premier-league/"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Map CSS class suffixes to human-readable status
_STATUS_MAP = {
    "injury-cross": "Ruled Out",
    "redcard": "Suspended",
    "injury-questionmark": "Doubtful",
    "injury-plus": "Injured",
}


class EPLScraper:
    """Scrapes EPL injury/suspension tables from sportsgambler.com."""

    def fetch_injuries(self) -> List[dict]:
        """
        Fetch current EPL injury data.

        Returns:
            List of standardized article dicts (same shape as RSSFetcher output).
            published_at is set to now() since this is a live table.
        """
        try:
            resp = requests.get(TARGET_URL, headers={"User-Agent": USER_AGENT}, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[EPL] Failed to fetch injury page: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        now = datetime.now(timezone.utc)
        now_str = now.strftime("%Y-%m-%d %H:%M")
        results: List[dict] = []

        for block in soup.find_all("div", class_="injury-block"):
            # Team name from <h3 class="injuries-title">
            h3 = block.find("h3", class_="injuries-title")
            team = h3.get_text(strip=True) if h3 else "Unknown"

            for container in block.find_all("div", class_="inj-container"):
                # Skip the header row
                if "inj-titles" in container.get("class", []):
                    continue

                player_el = container.find("span", class_="inj-player")
                if not player_el:
                    continue
                player_name = player_el.get_text(strip=True)
                if not player_name or player_name == "Name":
                    continue

                # Injury type / severity from icon class
                type_el = container.find("span", class_="inj-type")
                type_classes = type_el.get("class", []) if type_el else []
                status = "Unknown"
                for cls, label in _STATUS_MAP.items():
                    if cls in type_classes:
                        status = label
                        break

                # Structured data from sibling spans
                reason_el = container.find("span", class_="inj-info")
                return_el = container.find("span", class_="inj-return")
                reason = reason_el.get_text(strip=True) if reason_el else "Undisclosed"
                potential_return = return_el.get_text(strip=True) if return_el else "-"

                if not reason or reason == "-":
                    reason = "Undisclosed"
                if not potential_return or potential_return == "-":
                    potential_return = "Unknown"

                results.append(
                    {
                        "title": f"{team} - {player_name}: {reason}",
                        "summary": f"Status: {status}. Potential Return: {potential_return}",
                        "url": TARGET_URL,
                        "source": "PremierInjuries",
                        "published_at": now,
                        "published_str": now_str,
                    }
                )

        return results
