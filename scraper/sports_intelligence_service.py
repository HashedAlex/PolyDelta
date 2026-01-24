"""
PolyDelta Multi-Source Intelligence Aggregator (Cost-Optimized Version)
多源情报聚合服务 - 成本优化版本

实现 "Smart Throttling" 智能节流算法:
- Tier 1 (Free): RSS Feeds + Cached Odds API - 始终免费获取
- Tier 2 (Low Cost): Twitter/X via RapidAPI - 仅在特定条件下触发
- Tier 3 (High Cost): SerpApi - 最后手段

触发条件:
- Crunch Time Rule: 比赛开始前 2 小时内
- Volatility Rule: 赔率波动超过 5%
"""

import os
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False
    print("⚠️ feedparser not installed. Run: pip install feedparser")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("⚠️ requests not installed. Run: pip install requests")

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


class SportType(Enum):
    NBA = "nba"
    FIFA = "fifa"


class EventType(Enum):
    DAILY = "daily"
    FUTURE = "future"


class DataTier(Enum):
    """数据源层级"""
    TIER_1_FREE = "free"        # RSS + Cached Odds
    TIER_2_LOW_COST = "twitter"  # Twitter via RapidAPI (~$0.01/call)
    TIER_3_HIGH_COST = "search"  # SerpApi (last resort)


@dataclass
class IntelligenceItem:
    """单条情报数据"""
    source: str
    content: str
    timestamp: datetime
    tier: DataTier = DataTier.TIER_1_FREE
    priority: int = 1
    category: str = "general"
    url: Optional[str] = None

    def to_display(self) -> str:
        age = self._get_age()
        return f"- {self.source} ({age}): {self.content}"

    def _get_age(self) -> str:
        now = datetime.now()
        diff = now - self.timestamp
        if diff.total_seconds() < 3600:
            mins = int(diff.total_seconds() / 60)
            return f"{mins} mins ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hrs ago"
        else:
            return f"{diff.days} days ago"


@dataclass
class IntelligenceContext:
    """聚合后的情报上下文"""
    sport: SportType
    event_type: EventType
    team_a: str
    team_b: Optional[str] = None
    match_time: Optional[datetime] = None

    # 情报数据
    breaking_news: List[IntelligenceItem] = field(default_factory=list)
    injury_updates: List[IntelligenceItem] = field(default_factory=list)
    lineup_info: List[IntelligenceItem] = field(default_factory=list)
    narrative_trends: List[IntelligenceItem] = field(default_factory=list)
    odds_info: Optional[Dict[str, Any]] = None

    # 成本追踪
    tiers_used: List[DataTier] = field(default_factory=list)
    fetch_timestamp: datetime = field(default_factory=datetime.now)
    sources_used: List[str] = field(default_factory=list)

    # 触发原因
    twitter_trigger_reason: Optional[str] = None

    def to_prompt_injection(self) -> str:
        """生成注入到 System Prompt 的文本块"""
        lines = ["=== INTELLIGENCE REPORT ==="]

        # 赔率信息
        if self.odds_info:
            lines.append("\n[ODDS]")
            for team, odds in self.odds_info.items():
                lines.append(f"{team}: {odds}")

        # RSS 新闻 (Tier 1 - FREE)
        rss_items = [i for i in (self.breaking_news + self.injury_updates)
                    if i.tier == DataTier.TIER_1_FREE]
        if rss_items:
            lines.append("\n[NEWS SOURCE: RSS (FREE)]")
            for item in rss_items[:5]:
                lines.append(item.to_display())

        # Twitter 新闻 (Tier 2 - TRIGGERED)
        twitter_items = [i for i in (self.lineup_info + self.breaking_news)
                        if i.tier == DataTier.TIER_2_LOW_COST]
        if twitter_items:
            trigger_reason = self.twitter_trigger_reason or "CONDITION MET"
            lines.append(f"\n[NEWS SOURCE: TWITTER (TRIGGERED: {trigger_reason})]")
            for item in twitter_items[:3]:
                lines.append(item.to_display())

        # 搜索结果 (Tier 3 - FALLBACK)
        search_items = [i for i in self.narrative_trends
                       if i.tier == DataTier.TIER_3_HIGH_COST]
        if search_items:
            lines.append("\n[NEWS SOURCE: WEB SEARCH (FALLBACK)]")
            for item in search_items[:2]:
                lines.append(item.to_display())

        # 成本摘要
        tier_names = {
            DataTier.TIER_1_FREE: "Free",
            DataTier.TIER_2_LOW_COST: "Twitter ($0.01)",
            DataTier.TIER_3_HIGH_COST: "Search ($)"
        }
        tiers_str = ", ".join([tier_names.get(t, str(t)) for t in set(self.tiers_used)])
        lines.append(f"\n[Cost Tiers Used: {tiers_str}]")
        lines.append("=== END REPORT ===")

        return "\n".join(lines)

    def to_chatbot_context(self) -> Dict[str, Any]:
        """生成 Chatbot 可用的上下文"""
        return {
            "sport": self.sport.value,
            "event_type": self.event_type.value,
            "teams": [self.team_a, self.team_b] if self.team_b else [self.team_a],
            "intelligence": {
                "breaking": [{"source": i.source, "content": i.content, "age": i._get_age()}
                            for i in self.breaking_news],
                "injuries": [{"source": i.source, "content": i.content, "age": i._get_age()}
                            for i in self.injury_updates],
                "lineups": [{"source": i.source, "content": i.content, "age": i._get_age()}
                           for i in self.lineup_info],
            },
            "tiers_used": [t.value for t in self.tiers_used],
            "twitter_trigger": self.twitter_trigger_reason,
            "sources": self.sources_used,
            "fetched_at": self.fetch_timestamp.isoformat()
        }


class SportsIntelligenceService:
    """
    成本优化的多源情报聚合服务
    实现 Smart Throttling 算法
    """

    # ===== RSS Feed 配置 (Tier 1 - FREE) =====
    RSS_FEEDS = {
        SportType.NBA: [
            ("Rotoworld NBA", "https://www.nbcsports.com/rss/basketball/nba"),
            ("RealGM Wiretap", "https://basketball.realgm.com/rss/wiretap/0/0.xml"),
        ],
        SportType.FIFA: [
            ("ESPN FC", "https://www.espn.com/espn/rss/soccer/news"),
            ("BBC Sport", "http://feeds.bbci.co.uk/sport/football/rss.xml"),
        ]
    }

    # ===== Twitter 账号配置 (Tier 2 - LOW COST) =====
    TWITTER_TARGETS = {
        SportType.NBA: ["Underdog__NBA", "ShamsCharania", "wojespn"],
        SportType.FIFA: ["FabrizioRomano", "David_Ornstein"],
    }

    # ===== 触发条件配置 =====
    CRUNCH_TIME_HOURS = 2      # 比赛前 2 小时触发 Twitter
    VOLATILITY_THRESHOLD = 5   # 赔率波动 5% 触发 Twitter
    CACHE_TTL_MINUTES = 5      # 缓存有效期 5 分钟

    def __init__(self):
        self._cache: Dict[str, IntelligenceContext] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._odds_cache: Dict[str, Dict[str, float]] = {}

        # API Keys
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
        self.serpapi_key = os.getenv("SERPAPI_KEY", "")
        self.odds_api_key = os.getenv("ODDS_API_KEY", "")

    def get_intelligence(
        self,
        sport: SportType,
        team_a: str,
        team_b: Optional[str] = None,
        match_time: Optional[datetime] = None,
        current_odds: Optional[Dict[str, float]] = None
    ) -> IntelligenceContext:
        """
        主入口：智能节流算法获取情报

        Args:
            sport: 运动类型
            team_a: 主队/目标队伍
            team_b: 客队 (可选)
            match_time: 比赛开始时间 (用于 Crunch Time 判断)
            current_odds: 当前赔率 (用于 Volatility 判断)

        Returns:
            IntelligenceContext
        """
        cache_key = self._generate_cache_key(sport, team_a, team_b)

        # Step 0: 检查缓存 (< 5 mins old)
        cached = self._get_cached(cache_key)
        if cached:
            print(f"📦 [Intelligence] Cache hit for {team_a}")
            return cached

        print(f"🔍 [Intelligence] Fetching for {team_a}" + (f" vs {team_b}" if team_b else ""))

        # 创建上下文
        context = IntelligenceContext(
            sport=sport,
            event_type=EventType.DAILY if team_b else EventType.FUTURE,
            team_a=team_a,
            team_b=team_b,
            match_time=match_time
        )

        teams = [team_a]
        if team_b:
            teams.append(team_b)

        # ===== Step 1: Tier 1 - FREE (Always Execute) =====
        self._fetch_tier1_rss(context, teams)
        context.tiers_used.append(DataTier.TIER_1_FREE)

        # ===== Step 2: Tier 2 - Twitter (Conditional) =====
        twitter_trigger = self._should_trigger_twitter(match_time, current_odds, cache_key)
        if twitter_trigger:
            context.twitter_trigger_reason = twitter_trigger
            self._fetch_tier2_twitter(context, teams)
            context.tiers_used.append(DataTier.TIER_2_LOW_COST)

        # ===== Step 3: Tier 3 - Search (Fallback) =====
        total_items = (len(context.breaking_news) + len(context.injury_updates) +
                      len(context.lineup_info))
        if total_items == 0:
            self._fetch_tier3_search(context, teams)
            context.tiers_used.append(DataTier.TIER_3_HIGH_COST)

        # 缓存结果
        self._set_cached(cache_key, context)

        # 更新赔率缓存 (用于 Volatility 检测)
        if current_odds:
            self._odds_cache[cache_key] = current_odds

        return context

    # ========================================================================
    # 触发条件检测
    # ========================================================================

    def _should_trigger_twitter(
        self,
        match_time: Optional[datetime],
        current_odds: Optional[Dict[str, float]],
        cache_key: str
    ) -> Optional[str]:
        """
        判断是否应该触发 Twitter API

        Returns:
            触发原因字符串，或 None (不触发)
        """
        # Condition A: Crunch Time Rule (比赛前 2 小时)
        if match_time:
            time_to_match = match_time - datetime.now()
            hours_to_match = time_to_match.total_seconds() / 3600

            if 0 < hours_to_match <= self.CRUNCH_TIME_HOURS:
                print(f"   ⏰ Twitter triggered: CRUNCH TIME ({hours_to_match:.1f}h to match)")
                return "PRE-GAME"

        # Condition B: Volatility Rule (赔率波动 > 5%)
        if current_odds and cache_key in self._odds_cache:
            old_odds = self._odds_cache[cache_key]
            for team, new_odd in current_odds.items():
                if team in old_odds:
                    old_odd = old_odds[team]
                    if old_odd > 0:
                        change_pct = abs((new_odd - old_odd) / old_odd) * 100
                        if change_pct >= self.VOLATILITY_THRESHOLD:
                            print(f"   📊 Twitter triggered: VOLATILITY ({team} shifted {change_pct:.1f}%)")
                            return f"ODDS SHIFT {change_pct:.0f}%"

        return None

    # ========================================================================
    # Tier 1: RSS Feeds (FREE)
    # ========================================================================

    def _fetch_tier1_rss(self, context: IntelligenceContext, teams: List[str]):
        """Tier 1: 获取免费的 RSS 新闻"""
        if not HAS_FEEDPARSER:
            return

        feeds = self.RSS_FEEDS.get(context.sport, [])
        print(f"   📡 [Tier 1] Fetching {len(feeds)} RSS feeds (FREE)")

        for feed_name, feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)

                for entry in feed.entries[:15]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", entry.get("description", ""))
                    full_text = f"{title} {summary}".lower()

                    # 检查相关性
                    is_relevant = any(team.lower() in full_text for team in teams)
                    if not is_relevant:
                        continue

                    # 解析时间
                    pub_time = self._parse_rss_time(entry)
                    category = self._categorize_content(full_text)

                    item = IntelligenceItem(
                        source=feed_name,
                        content=title[:150],
                        timestamp=pub_time,
                        tier=DataTier.TIER_1_FREE,
                        priority=2 if category == "injury" else 1,
                        category=category,
                        url=entry.get("link")
                    )

                    if category == "injury":
                        context.injury_updates.append(item)
                    else:
                        context.breaking_news.append(item)

                    context.sources_used.append(feed_name)

            except Exception as e:
                print(f"   ⚠️ RSS Error ({feed_name}): {str(e)[:40]}")

    def _parse_rss_time(self, entry) -> datetime:
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6])
        except:
            pass
        return datetime.now() - timedelta(hours=1)

    # ========================================================================
    # Tier 2: Twitter via RapidAPI (LOW COST - ~$0.01/call)
    # ========================================================================

    def _fetch_tier2_twitter(self, context: IntelligenceContext, teams: List[str]):
        """Tier 2: 获取 Twitter 内幕 (仅在触发条件满足时调用)"""
        if not self.rapidapi_key or not HAS_REQUESTS:
            # 无 API Key 时使用模拟数据
            self._get_simulated_twitter(context, teams)
            return

        targets = self.TWITTER_TARGETS.get(context.sport, [])
        print(f"   🐦 [Tier 2] Fetching Twitter ({len(targets)} accounts) - COST: ~$0.01")

        for handle in targets[:2]:  # 限制调用次数
            try:
                # RapidAPI Twitter endpoint (示例)
                url = "https://twitter-api45.p.rapidapi.com/timeline.php"
                headers = {
                    "X-RapidAPI-Key": self.rapidapi_key,
                    "X-RapidAPI-Host": "twitter-api45.p.rapidapi.com"
                }
                params = {"screenname": handle, "count": "5"}

                response = requests.get(url, headers=headers, params=params, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    tweets = data.get("timeline", [])

                    for tweet in tweets[:3]:
                        text = tweet.get("text", "")

                        # 检查相关性
                        if not any(team.lower() in text.lower() for team in teams):
                            continue

                        item = IntelligenceItem(
                            source=f"@{handle}",
                            content=text[:150],
                            timestamp=datetime.now() - timedelta(minutes=10),
                            tier=DataTier.TIER_2_LOW_COST,
                            priority=3,
                            category=self._categorize_content(text)
                        )

                        if "lineup" in text.lower() or "starting" in text.lower():
                            context.lineup_info.append(item)
                        else:
                            context.breaking_news.append(item)

                        context.sources_used.append(f"@{handle}")

            except Exception as e:
                print(f"   ⚠️ Twitter Error (@{handle}): {str(e)[:40]}")

    def _get_simulated_twitter(self, context: IntelligenceContext, teams: List[str]):
        """模拟 Twitter 数据 (开发模式)"""
        handle = self.TWITTER_TARGETS.get(context.sport, ["Twitter"])[0]

        for team in teams[:2]:
            context.lineup_info.append(IntelligenceItem(
                source=f"@{handle}",
                content=f"{team} starting lineup confirmed. All starters available.",
                timestamp=datetime.now() - timedelta(minutes=15),
                tier=DataTier.TIER_2_LOW_COST,
                priority=3,
                category="lineup"
            ))
        context.sources_used.append(f"@{handle} (simulated)")

    # ========================================================================
    # Tier 3: Google Search via SerpApi (HIGH COST - FALLBACK)
    # ========================================================================

    def _fetch_tier3_search(self, context: IntelligenceContext, teams: List[str]):
        """Tier 3: 搜索备用 (仅当 Tier 1 & 2 无结果时)"""
        if not self.serpapi_key or not HAS_REQUESTS:
            print(f"   🔍 [Tier 3] Skipped (no SERPAPI_KEY)")
            return

        print(f"   🔍 [Tier 3] Triggering Web Search (FALLBACK) - COST: $$")

        try:
            team_str = " vs ".join(teams) if len(teams) > 1 else teams[0]
            query = f"{team_str} injury report lineup latest"

            response = requests.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": self.serpapi_key,
                    "num": 3,
                    "tbm": "nws"
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                for result in data.get("news_results", [])[:3]:
                    context.narrative_trends.append(IntelligenceItem(
                        source=result.get("source", "Web"),
                        content=result.get("title", "")[:150],
                        timestamp=datetime.now() - timedelta(hours=1),
                        tier=DataTier.TIER_3_HIGH_COST,
                        priority=1,
                        category="general",
                        url=result.get("link")
                    ))
                context.sources_used.append("Web Search")

        except Exception as e:
            print(f"   ⚠️ Search Error: {str(e)[:40]}")

    # ========================================================================
    # 工具方法
    # ========================================================================

    def _categorize_content(self, text: str) -> str:
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["injury", "out", "ruled out", "questionable", "gtd", "dnp"]):
            return "injury"
        elif any(kw in text_lower for kw in ["starting", "lineup", "confirmed", "available"]):
            return "lineup"
        elif any(kw in text_lower for kw in ["trade", "traded", "signing", "contract"]):
            return "trade"
        return "general"

    def _generate_cache_key(self, sport: SportType, team_a: str, team_b: Optional[str]) -> str:
        key_str = f"{sport.value}:{team_a}:{team_b or ''}"
        return hashlib.md5(key_str.encode()).hexdigest()[:16]

    def _get_cached(self, key: str) -> Optional[IntelligenceContext]:
        if key in self._cache:
            cached_time = self._cache_timestamps.get(key)
            if cached_time:
                age = datetime.now() - cached_time
                if age.total_seconds() < self.CACHE_TTL_MINUTES * 60:
                    return self._cache[key]
        return None

    def _set_cached(self, key: str, context: IntelligenceContext):
        self._cache[key] = context
        self._cache_timestamps[key] = datetime.now()


# ============================================================================
# 便捷函数
# ============================================================================

_service_instance: Optional[SportsIntelligenceService] = None


def get_intelligence_service() -> SportsIntelligenceService:
    global _service_instance
    if _service_instance is None:
        _service_instance = SportsIntelligenceService()
    return _service_instance


def get_match_intelligence(
    sport: str,
    team_a: str,
    team_b: Optional[str] = None,
    event_type: str = "daily",  # noqa: ARG001 - reserved for future use
    match_time: Optional[datetime] = None,
    current_odds: Optional[Dict[str, float]] = None
) -> str:
    """
    便捷函数：获取比赛情报并返回可注入的文本

    Args:
        sport: "nba" 或 "fifa"
        team_a: 主队/目标队伍
        team_b: 客队 (可选)
        event_type: "daily" 或 "future"
        match_time: 比赛开始时间 (触发 Crunch Time)
        current_odds: 当前赔率 (触发 Volatility)

    Returns:
        可注入到 System Prompt 的文本块
    """
    service = get_intelligence_service()
    sport_type = SportType.NBA if sport.lower() == "nba" else SportType.FIFA

    context = service.get_intelligence(sport_type, team_a, team_b, match_time, current_odds)
    return context.to_prompt_injection()


def get_chatbot_context(
    sport: str,
    team_a: str,
    team_b: Optional[str] = None,
    event_type: str = "daily"  # noqa: ARG001 - reserved for future use
) -> Dict[str, Any]:
    """获取 Chatbot 可用的情报上下文"""
    service = get_intelligence_service()
    sport_type = SportType.NBA if sport.lower() == "nba" else SportType.FIFA

    context = service.get_intelligence(sport_type, team_a, team_b)
    return context.to_chatbot_context()


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Cost-Optimized SportsIntelligenceService")
    print("=" * 60)

    service = SportsIntelligenceService()

    # Test 1: 正常情况 (只用 Tier 1)
    print("\n--- Test 1: Normal Case (Tier 1 Only) ---")
    context = service.get_intelligence(
        SportType.NBA,
        "Los Angeles Lakers",
        "Golden State Warriors"
    )
    print(context.to_prompt_injection())
    print(f"\nTiers Used: {[t.value for t in context.tiers_used]}")

    # Test 2: Crunch Time (触发 Tier 2)
    print("\n--- Test 2: Crunch Time (Trigger Tier 2) ---")
    match_time = datetime.now() + timedelta(hours=1)  # 1 小时后开始
    context = service.get_intelligence(
        SportType.NBA,
        "Boston Celtics",
        "Miami Heat",
        match_time=match_time
    )
    print(context.to_prompt_injection())
    print(f"\nTiers Used: {[t.value for t in context.tiers_used]}")
    print(f"Twitter Trigger: {context.twitter_trigger_reason}")

    # Test 3: Volatility (触发 Tier 2)
    print("\n--- Test 3: Volatility Trigger ---")
    # 先设置旧赔率
    service._odds_cache["test_key"] = {"Team A": 1.50}
    # 触发 volatility
    context = service.get_intelligence(
        SportType.NBA,
        "Denver Nuggets",
        "Phoenix Suns",
        current_odds={"Team A": 1.65}  # 10% 变化
    )
    print(f"Tiers Used: {[t.value for t in context.tiers_used]}")
