"""
PolyDelta Context Builder

Intelligently fetches, filters, and formats real-time news for AI analysis prompts.
Maps leagues to relevant data sources and returns only team-specific context.
"""

from typing import List, Optional

try:
    from .rss_service import RSSFetcher
    from .epl_scraper import EPLScraper
except ImportError:
    from rss_service import RSSFetcher
    from epl_scraper import EPLScraper


# Common short-name aliases for fuzzy matching
_ALIASES = {
    # EPL
    "man utd": "manchester united",
    "man united": "manchester united",
    "man city": "manchester city",
    "wolves": "wolverhampton",
    "spurs": "tottenham",
    "saints": "southampton",
    "toon": "newcastle",
    "villa": "aston villa",
    "forest": "nottingham forest",
    "nottm forest": "nottingham forest",
    "west ham": "west ham united",
    # NBA
    "sixers": "76ers",
    "blazers": "trail blazers",
    "wolves": "timberwolves",
}

# League -> RSS source keys
_LEAGUE_SOURCES = {
    "NBA": [
        "NBC_Sports_Edge", "HoopsHype_NBA", "Rotoworld_NBA",
        "Yardbarker_NBA", "RealGM_NBA",
    ],
    "EPL": [
        "BBC_Football", "Yardbarker_EPL", "SkySports_Football",
    ],
    "UCL": [
        "Guardian_UCL", "SkySports_Football", "ESPN_FC",
    ],
    "FIFA": [
        "ESPN_FC", "SkySports_Football", "BBC_Football",
    ],
}


def _expand_team(name: str) -> List[str]:
    """Return a list of lowercase search variants for a team name."""
    low = name.lower().strip()
    variants = [low]
    # Add alias expansions
    for alias, full in _ALIASES.items():
        if alias == low:
            variants.append(full)
        elif full == low:
            variants.append(alias)
    # Also add individual words for multi-word names (e.g. "Lakers" from "Los Angeles Lakers")
    words = low.split()
    if len(words) > 1:
        variants.append(words[-1])  # last word is usually the mascot/short name
    return variants


def _is_relevant(text: str, team_variants: List[str]) -> bool:
    """Check if text mentions any team variant (case-insensitive)."""
    text_lower = text.lower()
    return any(v in text_lower for v in team_variants)


class ContextBuilder:
    """Builds match-specific real-time context for AI analysis prompts."""

    def __init__(self):
        self._rss = RSSFetcher()
        self._epl = EPLScraper()

    def build_match_context(
        self,
        home_team: str,
        away_team: str,
        league_code: str,
        lookback_hours: int = 48,
    ) -> str:
        """
        Fetch and filter real-time news relevant to a specific match.

        Args:
            home_team: Home team name.
            away_team: Away team name.
            league_code: One of "NBA", "EPL", "UCL", "FIFA".
            lookback_hours: How far back to look for news (default 48h).

        Returns:
            Formatted string ready to inject into an LLM prompt,
            or empty string if no relevant news found.
        """
        league = league_code.upper()
        source_keys = _LEAGUE_SOURCES.get(league, [])

        # Build search variants for both teams
        home_variants = _expand_team(home_team)
        away_variants = _expand_team(away_team)
        all_variants = home_variants + away_variants

        items: List[str] = []

        # Step 1: RSS feeds
        if source_keys:
            articles = self._rss.fetch_news(
                source_keys=source_keys,
                lookback_hours=lookback_hours,
            )
            for a in articles:
                searchable = f"{a['title']} {a['summary']}"
                if _is_relevant(searchable, all_variants):
                    items.append(
                        f"- (Source: {a['source']}) {a['title']}. {a['summary'][:150]}"
                    )

        # Step 2: EPL structured injuries (only for EPL)
        if league == "EPL":
            try:
                injuries = self._epl.fetch_injuries()
                for inj in injuries:
                    if _is_relevant(inj["title"], all_variants):
                        items.append(
                            f"- (Source: PremierInjuries) {inj['title']}. {inj['summary']}"
                        )
            except Exception as e:
                print(f"   [ContextBuilder] EPL injury fetch failed: {str(e)[:60]}")

        if not items:
            return ""

        header = (
            "[REAL-TIME NEWS / INJURIES]\n"
            "You MUST prioritize this news over general knowledge. "
            "If a key player is listed as 'Out' or 'Injured', heavily weight this in your prediction.\n"
        )
        return header + "\n".join(items[:15])  # Cap at 15 items to avoid prompt bloat
