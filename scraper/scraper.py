"""
PolyDelta - 多平台多赛事数据抓取脚本
支持: World Cup, EPL (英超), NBA
数据源: Web2 (TheOddsAPI), Polymarket
功能:
  1. 冠军盘口 (Outrights) - 谁会夺冠
  2. 每日比赛 (H2H) - 今日比赛胜负盘
Kalshi: 已禁用 (网络限制)
"""
import os
import json
import re
import requests
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv
from thefuzz import fuzz

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DATABASE_URL = os.getenv('DATABASE_URL')
ODDS_API_KEY = os.getenv('ODDS_API_KEY')

# 缓存文件目录
CACHE_DIR = os.path.dirname(__file__)

# ============================================
# Bookmaker URL 映射表
# The Odds API 不提供链接，需要手动维护
# ============================================
BOOKMAKER_URLS = {
    "draftkings": "https://sportsbook.draftkings.com",
    "fanduel": "https://sportsbook.fanduel.com",
    "betmgm": "https://sports.betmgm.com",
    "pinnacle": "https://www.pinnacle.com",
    "betfair_ex_eu": "https://www.betfair.com",
    "bet365": "https://www.bet365.com",
    "bovada": "https://www.bovada.lv",
    "unibet": "https://www.unibet.com",
    "williamhill": "https://sports.williamhill.com",
    "caesars": "https://www.caesars.com/sportsbook-and-casino",
    "pointsbet": "https://pointsbet.com",
    "betrivers": "https://www.betrivers.com",
    "superbook": "https://co.superbook.com",
    "lowvig": "https://www.lowvig.ag",
    "betonlineag": "https://www.betonline.ag",
    "mybookieag": "https://mybookie.ag",
    "betus": "https://www.betus.com.pa",
    "wynnbet": "https://www.wynnbet.com",
    "betfred": "https://www.betfred.com",
    "ladbrokes": "https://sports.ladbrokes.com",
    "coral": "https://sports.coral.co.uk",
    "paddypower": "https://www.paddypower.com",
    "skybet": "https://www.skybet.com",
    "888sport": "https://www.888sport.com",
    "betsson": "https://www.betsson.com",
    "nordicbet": "https://www.nordicbet.com",
}

# Bookmaker 显示名称（美化）
BOOKMAKER_DISPLAY_NAMES = {
    "draftkings": "DraftKings",
    "fanduel": "FanDuel",
    "betmgm": "BetMGM",
    "pinnacle": "Pinnacle",
    "betfair_ex_eu": "Betfair",
    "bet365": "Bet365",
    "bovada": "Bovada",
    "unibet": "Unibet",
    "williamhill": "William Hill",
    "caesars": "Caesars",
    "pointsbet": "PointsBet",
    "betrivers": "BetRivers",
    "betonlineag": "BetOnline",
    "mybookieag": "MyBookie",
}

# ============================================
# 赛事配置
# ============================================
SPORTS_CONFIG = {
    "world_cup": {
        "name": "FIFA World Cup 2026",
        "web2_key": "soccer_fifa_world_cup_winner",
        "cache_file": "cache_worldcup.json",
        "poly_keywords": ["world cup", "fifa", "2026"],
    },
    "epl": {
        "name": "English Premier League",
        "web2_key": "soccer_epl_winner",
        "cache_file": "cache_epl.json",
        "poly_keywords": ["premier league", "epl", "english premier"],
    },
    "nba": {
        "name": "NBA Championship",
        "web2_key": "basketball_nba_championship_winner",
        "cache_file": "cache_nba.json",
        "poly_keywords": ["nba", "basketball", "nba champion"],
    },
}

# ============================================
# 名称映射字典 - 多赛事支持
# ============================================
MAPPING = {
    # ========== 英超球队 (EPL) ==========
    "Arsenal": {"web2": "Arsenal", "poly": "Arsenal"},
    "Manchester City": {"web2": "Manchester City", "poly": "Manchester City"},
    "Liverpool": {"web2": "Liverpool", "poly": "Liverpool"},
    "Chelsea": {"web2": "Chelsea", "poly": "Chelsea"},
    "Manchester United": {"web2": "Manchester United", "poly": "Manchester United"},
    "Tottenham": {"web2": "Tottenham Hotspur", "poly": "Tottenham"},
    "Newcastle": {"web2": "Newcastle United", "poly": "Newcastle"},
    "Aston Villa": {"web2": "Aston Villa", "poly": "Aston Villa"},
    "Brighton": {"web2": "Brighton and Hove Albion", "poly": "Brighton"},
    "West Ham": {"web2": "West Ham United", "poly": "West Ham"},
    "Fulham": {"web2": "Fulham", "poly": "Fulham"},
    "Brentford": {"web2": "Brentford", "poly": "Brentford"},
    "Crystal Palace": {"web2": "Crystal Palace", "poly": "Crystal Palace"},
    "Everton": {"web2": "Everton", "poly": "Everton"},
    "Nottingham Forest": {"web2": "Nottingham Forest", "poly": "Nottingham Forest"},
    "Bournemouth": {"web2": "AFC Bournemouth", "poly": "Bournemouth"},
    "Wolves": {"web2": "Wolverhampton Wanderers", "poly": "Wolves"},
    "Leicester": {"web2": "Leicester City", "poly": "Leicester"},
    "Ipswich": {"web2": "Ipswich Town", "poly": "Ipswich"},
    "Southampton": {"web2": "Southampton", "poly": "Southampton"},

    # ========== NBA 球队 ==========
    "Boston Celtics": {"web2": "Boston Celtics", "poly": "Boston Celtics"},
    "Denver Nuggets": {"web2": "Denver Nuggets", "poly": "Denver Nuggets"},
    "Los Angeles Lakers": {"web2": "Los Angeles Lakers", "poly": "Lakers"},
    "Golden State Warriors": {"web2": "Golden State Warriors", "poly": "Warriors"},
    "Milwaukee Bucks": {"web2": "Milwaukee Bucks", "poly": "Bucks"},
    "Phoenix Suns": {"web2": "Phoenix Suns", "poly": "Suns"},
    "Philadelphia 76ers": {"web2": "Philadelphia 76ers", "poly": "76ers"},
    "Miami Heat": {"web2": "Miami Heat", "poly": "Heat"},
    "Cleveland Cavaliers": {"web2": "Cleveland Cavaliers", "poly": "Cavaliers"},
    "New York Knicks": {"web2": "New York Knicks", "poly": "Knicks"},
    "Dallas Mavericks": {"web2": "Dallas Mavericks", "poly": "Mavericks"},
    "Memphis Grizzlies": {"web2": "Memphis Grizzlies", "poly": "Grizzlies"},
    "Sacramento Kings": {"web2": "Sacramento Kings", "poly": "Kings"},
    "LA Clippers": {"web2": "Los Angeles Clippers", "poly": "Clippers"},
    "Minnesota Timberwolves": {"web2": "Minnesota Timberwolves", "poly": "Timberwolves"},
    "New Orleans Pelicans": {"web2": "New Orleans Pelicans", "poly": "Pelicans"},
    "Oklahoma City Thunder": {"web2": "Oklahoma City Thunder", "poly": "Thunder"},
    "Brooklyn Nets": {"web2": "Brooklyn Nets", "poly": "Nets"},
    "Atlanta Hawks": {"web2": "Atlanta Hawks", "poly": "Hawks"},
    "Chicago Bulls": {"web2": "Chicago Bulls", "poly": "Bulls"},
    "Toronto Raptors": {"web2": "Toronto Raptors", "poly": "Raptors"},
    "Indiana Pacers": {"web2": "Indiana Pacers", "poly": "Pacers"},
    "Orlando Magic": {"web2": "Orlando Magic", "poly": "Magic"},
    "Houston Rockets": {"web2": "Houston Rockets", "poly": "Rockets"},

    # ========== 世界杯国家队 ==========
    "Argentina": {"web2": "Argentina", "poly": "Argentina"},
    "Brazil": {"web2": "Brazil", "poly": "Brazil"},
    "France": {"web2": "France", "poly": "France"},
    "Germany": {"web2": "Germany", "poly": "Germany"},
    "England": {"web2": "England", "poly": "England"},
    "Spain": {"web2": "Spain", "poly": "Spain"},
    "Portugal": {"web2": "Portugal", "poly": "Portugal"},
    "Netherlands": {"web2": "Netherlands", "poly": "Netherlands"},
    "Belgium": {"web2": "Belgium", "poly": "Belgium"},
    "Italy": {"web2": "Italy", "poly": "Italy"},
    "Croatia": {"web2": "Croatia", "poly": "Croatia"},
    "Uruguay": {"web2": "Uruguay", "poly": "Uruguay"},
    "USA": {"web2": "United States", "poly": "USA"},
    "Mexico": {"web2": "Mexico", "poly": "Mexico"},
    "Japan": {"web2": "Japan", "poly": "Japan"},
}


def create_reverse_mapping():
    """创建反向映射：从各平台名称 -> 标准名称"""
    reverse = {"web2": {}, "poly": {}}
    for standard_name, platforms in MAPPING.items():
        for platform, name in platforms.items():
            reverse[platform][name.lower()] = standard_name
    return reverse


REVERSE_MAPPING = create_reverse_mapping()


# ============================================
# NBA 队伍简称映射 (用于模糊匹配)
# ============================================
NBA_TEAM_ALIASES = {
    "Boston Celtics": ["celtics", "boston"],
    "Brooklyn Nets": ["nets", "brooklyn"],
    "New York Knicks": ["knicks", "new york", "ny knicks"],
    "Philadelphia 76ers": ["76ers", "sixers", "philadelphia", "philly"],
    "Toronto Raptors": ["raptors", "toronto"],
    "Chicago Bulls": ["bulls", "chicago"],
    "Cleveland Cavaliers": ["cavaliers", "cavs", "cleveland"],
    "Detroit Pistons": ["pistons", "detroit"],
    "Indiana Pacers": ["pacers", "indiana"],
    "Milwaukee Bucks": ["bucks", "milwaukee"],
    "Atlanta Hawks": ["hawks", "atlanta"],
    "Charlotte Hornets": ["hornets", "charlotte"],
    "Miami Heat": ["heat", "miami"],
    "Orlando Magic": ["magic", "orlando"],
    "Washington Wizards": ["wizards", "washington"],
    "Denver Nuggets": ["nuggets", "denver"],
    "Minnesota Timberwolves": ["timberwolves", "wolves", "minnesota"],
    "Oklahoma City Thunder": ["thunder", "okc", "oklahoma"],
    "Portland Trail Blazers": ["trail blazers", "blazers", "portland"],
    "Utah Jazz": ["jazz", "utah"],
    "Golden State Warriors": ["warriors", "golden state", "gsw"],
    "Los Angeles Clippers": ["clippers", "la clippers", "lac"],
    "Los Angeles Lakers": ["lakers", "la lakers", "lal"],
    "Phoenix Suns": ["suns", "phoenix"],
    "Sacramento Kings": ["kings", "sacramento"],
    "Dallas Mavericks": ["mavericks", "mavs", "dallas"],
    "Houston Rockets": ["rockets", "houston"],
    "Memphis Grizzlies": ["grizzlies", "memphis"],
    "New Orleans Pelicans": ["pelicans", "new orleans"],
    "San Antonio Spurs": ["spurs", "san antonio"],
}


def standardize_name(name, platform):
    """将平台特定名称转换为标准名称"""
    if not name:
        return None
    name_lower = name.lower()
    # 先尝试精确匹配
    if name_lower in REVERSE_MAPPING.get(platform, {}):
        return REVERSE_MAPPING[platform][name_lower]
    # 再尝试部分匹配
    for mapped_name, standard in REVERSE_MAPPING.get(platform, {}).items():
        if mapped_name in name_lower or name_lower in mapped_name:
            return standard
    # 如果都没匹配到，返回原始名称（清理后）
    return name.strip()


# ============================================
# Web2 数据抓取 (TheOddsAPI) - 多赛事支持
# ============================================
def fetch_web2_odds(sport_type):
    """
    从 TheOddsAPI 获取指定赛事的赔率数据
    返回: {team_name: implied_probability}
    """
    config = SPORTS_CONFIG.get(sport_type)
    if not config:
        print(f"[Web2] 未知赛事类型: {sport_type}")
        return {}

    print(f"\n[Web2] 正在获取 {config['name']} 数据...")
    cache_file = os.path.join(CACHE_DIR, config['cache_file'])

    if not ODDS_API_KEY or ODDS_API_KEY == "你的_TheOddsAPI_Key":
        print(f"[Web2] 警告: ODDS_API_KEY 未设置，使用缓存数据")
        return load_web2_cache(cache_file)

    # TheOddsAPI endpoint
    url = f"https://api.the-odds-api.com/v4/sports/{config['web2_key']}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us,uk,eu",
        "markets": "outrights",
        "oddsFormat": "decimal"
    }

    try:
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 404:
            print(f"[Web2] {config['name']} 市场暂未开放，尝试使用缓存...")
            return load_web2_cache(cache_file)

        if response.status_code == 401:
            print(f"[Web2] API Key 无效")
            return load_web2_cache(cache_file)

        response.raise_for_status()
        data = response.json()

        # 保存到缓存
        save_web2_cache(data, cache_file)

        # 处理数据
        return process_web2_data(data)

    except requests.exceptions.RequestException as e:
        print(f"[Web2] API 请求失败: {e}")
        return load_web2_cache(cache_file)


def process_web2_data(data):
    """
    处理 TheOddsAPI 返回的数据
    返回: {team_name: {"odds": float, "bookmaker": str, "bookmaker_url": str}}

    策略：优先选择主流 bookmaker，计算平均胜率
    """
    # 主流 bookmaker 列表（优先使用这些来源）
    PREFERRED_BOOKMAKERS = {
        "draftkings", "fanduel", "betmgm", "pinnacle",
        "williamhill", "caesars", "pointsbet", "betrivers"
    }

    # 收集每个队伍的所有赔率数据
    team_odds_collection = {}  # {team: [(implied_prob, bookmaker_key, bookmaker_title), ...]}

    if not data:
        return {}

    for event in data:
        bookmakers = event.get("bookmakers", [])
        for bookmaker in bookmakers:
            bookmaker_key = bookmaker.get("key", "")
            bookmaker_title = bookmaker.get("title", bookmaker_key)

            markets = bookmaker.get("markets", [])
            for market in markets:
                if market.get("key") == "outrights":
                    outcomes = market.get("outcomes", [])
                    for outcome in outcomes:
                        team = outcome.get("name")
                        odds = outcome.get("price")

                        if team and odds and odds > 1:  # 赔率必须 > 1
                            standard_name = standardize_name(team, "web2")
                            if standard_name:
                                implied_prob = 1 / odds

                                # 过滤异常数据：单队胜率不应超过 60%
                                if implied_prob > 0.60:
                                    continue

                                if standard_name not in team_odds_collection:
                                    team_odds_collection[standard_name] = []

                                team_odds_collection[standard_name].append({
                                    "prob": implied_prob,
                                    "key": bookmaker_key,
                                    "title": bookmaker_title,
                                })

    # 为每个队伍选择最佳来源
    team_data = {}
    for team, odds_list in team_odds_collection.items():
        # 优先选择主流 bookmaker
        preferred = [o for o in odds_list if o["key"] in PREFERRED_BOOKMAKERS]

        if preferred:
            # 从主流 bookmaker 中计算平均胜率，并选择一个代表
            avg_prob = sum(o["prob"] for o in preferred) / len(preferred)
            # 选择最接近平均值的主流 bookmaker 作为来源
            best = min(preferred, key=lambda x: abs(x["prob"] - avg_prob))
        else:
            # 没有主流 bookmaker，使用所有来源的平均值
            avg_prob = sum(o["prob"] for o in odds_list) / len(odds_list)
            best = min(odds_list, key=lambda x: abs(x["prob"] - avg_prob))

        bookmaker_key = best["key"]
        bookmaker_url = BOOKMAKER_URLS.get(bookmaker_key, "")
        display_name = BOOKMAKER_DISPLAY_NAMES.get(bookmaker_key, best["title"])

        team_data[team] = {
            "odds": round(avg_prob, 4),  # 使用平均胜率
            "bookmaker": display_name,
            "bookmaker_key": bookmaker_key,
            "bookmaker_url": bookmaker_url,
        }

    print(f"[Web2] 获取到 {len(team_data)} 支队伍的数据")
    return team_data


def save_web2_cache(data, cache_file):
    """保存 Web2 数据到缓存文件"""
    cache_data = {
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print(f"[Web2] 数据已缓存到 {cache_file}")
    except Exception as e:
        print(f"[Web2] 缓存保存失败: {e}")


def load_web2_cache(cache_file):
    """从缓存文件加载 Web2 数据"""
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            print(f"[Web2] 从缓存加载数据 (时间: {cache.get('timestamp', 'unknown')})")
            return process_web2_data(cache.get("data", []))
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[Web2] 缓存文件损坏: {e}")
    return {}


# ============================================
# Polymarket 数据抓取 (Gamma API) - 多赛事支持
# ============================================

# 从问题中提取球队名的正则模式
# 注意：只匹配 "win the" 夺冠盘口，排除 "qualify" 出线盘口
TEAM_EXTRACT_PATTERNS = {
    "nba": re.compile(r"Will the (.+?) win the \d{4} NBA Finals", re.IGNORECASE),
    "world_cup": re.compile(r"Will (.+?) win the \d{4} FIFA World Cup", re.IGNORECASE),
    "epl": re.compile(r"Will (.+?) win the (?:Premier League|\d{4})", re.IGNORECASE),
}


def fetch_polymarket_data(sport_type):
    """
    从 Polymarket Gamma API 获取指定赛事的市场数据
    Polymarket 的市场是按球队拆分的 Yes/No 格式
    返回: {team_name: {"price": float, "url": str}}
    """
    config = SPORTS_CONFIG.get(sport_type)
    if not config:
        print(f"[Polymarket] 未知赛事类型: {sport_type}")
        return {}

    print(f"\n[Polymarket] 正在获取 {config['name']} 数据...")

    # Gamma API endpoint
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "closed": "false",
        "limit": 500  # 增加限制以获取更多市场
    }

    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        markets = response.json()

        result = {}
        keywords = config['poly_keywords']
        pattern = TEAM_EXTRACT_PATTERNS.get(sport_type)

        for market in markets:
            question = market.get("question", "")
            question_lower = question.lower()

            # ============================================
            # 严格过滤：只匹配"夺冠"盘口，排除"出线"盘口
            # ============================================
            matched = False

            # 对于 NBA：必须包含 "win the" + "nba finals"
            if sport_type == "nba":
                if "nba finals" in question_lower and "win the" in question_lower:
                    matched = True

            # 对于 World Cup：必须包含 "win the" + "fifa world cup"，排除 "qualify"
            elif sport_type == "world_cup":
                if "fifa world cup" in question_lower:
                    # 必须是 "win the"，不能是 "qualify"
                    if "win the" in question_lower and "qualify" not in question_lower:
                        matched = True

            # 对于 EPL：必须包含 "win the" + "premier league"
            elif sport_type == "epl":
                if "premier league" in question_lower and "win" in question_lower:
                    matched = True

            if matched:
                slug = market.get("slug", market.get("id", ""))
                market_url = f"https://polymarket.com/event/{slug}"

                # 获取 outcomes 和 prices
                outcomes = market.get("outcomes", [])
                outcome_prices = market.get("outcomePrices", [])

                # 处理 JSON 字符串格式
                if isinstance(outcomes, str):
                    try:
                        outcomes = json.loads(outcomes)
                    except:
                        outcomes = []
                if isinstance(outcome_prices, str):
                    try:
                        outcome_prices = json.loads(outcome_prices)
                    except:
                        outcome_prices = []

                # Polymarket 市场是 Yes/No 格式，从问题中提取球队名
                # 例如: "Will the Oklahoma City Thunder win the 2026 NBA Finals?"
                team_name = None

                # 使用正则提取
                if pattern:
                    match = pattern.search(question)
                    if match:
                        team_name = match.group(1).strip()

                # 如果正则失败，尝试其他方法
                if not team_name:
                    # 尝试从问题中直接提取
                    for std_name, platforms in MAPPING.items():
                        poly_name = platforms.get("poly", "").lower()
                        web2_name = platforms.get("web2", "").lower()
                        if poly_name and poly_name in question_lower:
                            team_name = std_name
                            break
                        if web2_name and web2_name in question_lower:
                            team_name = std_name
                            break

                if team_name and outcomes and outcome_prices:
                    # 找到 Yes 选项的价格
                    yes_price = None
                    for i, outcome in enumerate(outcomes):
                        if outcome.lower() == "yes" and i < len(outcome_prices):
                            try:
                                yes_price = float(outcome_prices[i])
                            except (ValueError, TypeError):
                                pass
                            break

                    if yes_price and yes_price > 0:
                        # 标准化名称
                        standard_name = standardize_name(team_name, "poly")
                        if standard_name:
                            # 如果已存在，保留价格更高的
                            if standard_name not in result or yes_price > result[standard_name]["price"]:
                                result[standard_name] = {
                                    "price": round(yes_price, 4),
                                    "url": market_url
                                }

        print(f"[Polymarket] 获取到 {len(result)} 支队伍的数据")
        return result

    except requests.exceptions.RequestException as e:
        print(f"[Polymarket] API 请求失败: {e}")
        return {}


# ============================================
# Kalshi 数据抓取 - 已禁用 (网络限制)
# ============================================
def fetch_kalshi_data(sport_type):
    """
    Kalshi 数据抓取 - 已禁用
    由于网络限制（非美国地区 DNS 解析失败），暂时跳过 Kalshi
    """
    print(f"\n[Kalshi] 已禁用 (网络限制，非美国地区无法访问)")
    return {}

    # ============================================
    # 以下代码已注释 - Kalshi 原始实现
    # ============================================
    # config = SPORTS_CONFIG.get(sport_type)
    # if not config:
    #     return {}
    #
    # print(f"\n[Kalshi] 正在获取 {config['name']} 数据...")
    #
    # url = "https://api.kalshi.com/trade-api/v2/markets"
    # params = {
    #     "limit": 200,
    #     "status": "open"
    # }
    #
    # try:
    #     response = requests.get(url, params=params, timeout=30)
    #     response.raise_for_status()
    #     data = response.json()
    #     markets = data.get("markets", [])
    #     result = {}
    #
    #     for market in markets:
    #         title = market.get("title", "").lower()
    #         ticker = market.get("ticker", "")
    #         # 匹配关键词...
    #         # 价格转换: cents -> decimal (÷100)
    #         # yes_price = market.get("yes_bid", 0) / 100.0
    #
    #     return result
    #
    # except Exception as e:
    #     print(f"[Kalshi] 请求失败: {e}")
    #     return {}


# ============================================
# Daily Matches - 每日比赛 H2H 数据抓取
# ============================================

def fuzzy_match_team(name, threshold=75):
    """
    使用模糊匹配找到最匹配的 NBA 队伍
    返回: (标准队名, 匹配分数) 或 (None, 0)
    """
    name_lower = name.lower().strip()

    # 先尝试精确匹配
    for team, aliases in NBA_TEAM_ALIASES.items():
        if name_lower == team.lower():
            return team, 100
        for alias in aliases:
            if name_lower == alias.lower():
                return team, 100

    # 模糊匹配
    best_match = None
    best_score = 0

    for team, aliases in NBA_TEAM_ALIASES.items():
        # 匹配标准队名
        score = fuzz.ratio(name_lower, team.lower())
        if score > best_score:
            best_score = score
            best_match = team

        # 匹配别名
        for alias in aliases:
            score = fuzz.ratio(name_lower, alias.lower())
            if score > best_score:
                best_score = score
                best_match = team

            # 部分匹配（队名包含别名）
            if alias.lower() in name_lower:
                score = 90
                if score > best_score:
                    best_score = score
                    best_match = team

    if best_score >= threshold:
        return best_match, best_score
    return None, 0


def fetch_nba_matches_web2():
    """
    从 TheOddsAPI 获取 NBA 每日比赛 (H2H) 数据
    返回: [
        {
            "match_id": str,
            "home_team": str,
            "away_team": str,
            "commence_time": datetime,
            "home_odds": float,  # 隐含胜率
            "away_odds": float,
            "bookmaker": str,
            "bookmaker_url": str,
        },
        ...
    ]
    """
    print("\n[Web2] 正在获取 NBA 每日比赛 (H2H) 数据...")

    if not ODDS_API_KEY or ODDS_API_KEY == "你的_TheOddsAPI_Key":
        print("[Web2] 警告: ODDS_API_KEY 未设置")
        return []

    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }

    try:
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 404:
            print("[Web2] NBA 比赛暂无数据")
            return []

        response.raise_for_status()
        events = response.json()

        matches = []
        PREFERRED_BOOKMAKERS = {"draftkings", "fanduel", "betmgm", "pinnacle"}

        for event in events:
            match_id = event.get("id")
            home_team = event.get("home_team")
            away_team = event.get("away_team")
            commence_time = event.get("commence_time")

            if not all([match_id, home_team, away_team, commence_time]):
                continue

            # 收集所有 bookmaker 的赔率
            home_odds_list = []
            away_odds_list = []
            best_bookmaker = None

            for bookmaker in event.get("bookmakers", []):
                bk_key = bookmaker.get("key", "")
                bk_title = bookmaker.get("title", bk_key)

                for market in bookmaker.get("markets", []):
                    if market.get("key") != "h2h":
                        continue

                    outcomes = market.get("outcomes", [])
                    home_price = None
                    away_price = None

                    for outcome in outcomes:
                        if outcome.get("name") == home_team:
                            home_price = outcome.get("price")
                        elif outcome.get("name") == away_team:
                            away_price = outcome.get("price")

                    if home_price and away_price and home_price > 1 and away_price > 1:
                        home_prob = 1 / home_price
                        away_prob = 1 / away_price

                        home_odds_list.append({
                            "prob": home_prob,
                            "key": bk_key,
                            "title": bk_title,
                        })
                        away_odds_list.append({
                            "prob": away_prob,
                            "key": bk_key,
                            "title": bk_title,
                        })

            if not home_odds_list:
                continue

            # 优先使用主流 bookmaker 的平均值
            preferred_home = [o for o in home_odds_list if o["key"] in PREFERRED_BOOKMAKERS]
            preferred_away = [o for o in away_odds_list if o["key"] in PREFERRED_BOOKMAKERS]

            if preferred_home:
                avg_home = sum(o["prob"] for o in preferred_home) / len(preferred_home)
                avg_away = sum(o["prob"] for o in preferred_away) / len(preferred_away)
                best_bk = preferred_home[0]
            else:
                avg_home = sum(o["prob"] for o in home_odds_list) / len(home_odds_list)
                avg_away = sum(o["prob"] for o in away_odds_list) / len(away_odds_list)
                best_bk = home_odds_list[0]

            bookmaker_url = BOOKMAKER_URLS.get(best_bk["key"], "")
            display_name = BOOKMAKER_DISPLAY_NAMES.get(best_bk["key"], best_bk["title"])

            matches.append({
                "match_id": match_id,
                "home_team": home_team,
                "away_team": away_team,
                "commence_time": datetime.fromisoformat(commence_time.replace("Z", "+00:00")),
                "home_odds": round(avg_home, 4),
                "away_odds": round(avg_away, 4),
                "bookmaker": display_name,
                "bookmaker_url": bookmaker_url,
            })

        print(f"[Web2] 获取到 {len(matches)} 场 NBA 比赛")
        return matches

    except requests.exceptions.RequestException as e:
        print(f"[Web2] API 请求失败: {e}")
        return []


def fetch_nba_matches_polymarket():
    """
    从 Polymarket Gamma API 获取 NBA 每日比赛数据
    使用 Events API (tag_slug=nba) 而不是 Markets API
    格式: "Team1 vs. Team2" (例如 "Grizzlies vs. Lakers")

    过滤条件:
    - 排除已结束的比赛 (价格接近 100%/0%)
    - 排除冠军、MVP 等非每日比赛盘口
    """
    print("\n[Polymarket] 正在获取 NBA 每日比赛数据...")

    # 使用 Events API 获取 NBA 比赛
    url = "https://gamma-api.polymarket.com/events"
    params = {
        "limit": 50,
        "active": "true",
        "closed": "false",
        "tag_slug": "nba",
    }

    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        events = response.json()

        matches = []
        all_events = []  # 用于调试

        # 匹配模式: "Team1 vs. Team2" 或 "Team1 vs Team2"
        vs_pattern = re.compile(r"^(.+?)\s+vs\.?\s+(.+?)$", re.IGNORECASE)

        for event in events:
            title = event.get("title", "")
            event_id = event.get("id", "")
            slug = event.get("slug", "")
            end_date_str = event.get("endDate", "")

            all_events.append({"title": title, "id": event_id})

            # 排除非比赛盘口（冠军、MVP等）
            title_lower = title.lower()
            if any(kw in title_lower for kw in ["champion", "mvp", "rookie", "division", "playoff", "record", "player", "coach", "leader", "conference"]):
                continue

            # 尝试解析 "Team1 vs. Team2" 格式
            match = vs_pattern.match(title)
            if not match:
                continue

            team1_raw = match.group(1).strip()
            team2_raw = match.group(2).strip()

            # 模糊匹配队伍名
            std_team1, score1 = fuzzy_match_team(team1_raw)
            std_team2, score2 = fuzzy_match_team(team2_raw)

            if not std_team1 or not std_team2:
                print(f"[Polymarket] 无法识别队伍: {team1_raw} vs {team2_raw}")
                continue

            # 获取市场详情（价格）
            # 需要从 event 中获取 markets 数据
            event_markets = event.get("markets", [])

            team1_price = None
            team2_price = None

            for market in event_markets:
                outcomes = market.get("outcomes", [])
                outcome_prices = market.get("outcomePrices", [])

                if isinstance(outcomes, str):
                    try:
                        outcomes = json.loads(outcomes)
                    except:
                        outcomes = []
                if isinstance(outcome_prices, str):
                    try:
                        outcome_prices = json.loads(outcome_prices)
                    except:
                        outcome_prices = []

                for i, outcome in enumerate(outcomes):
                    if i < len(outcome_prices):
                        try:
                            price = float(outcome_prices[i])
                        except:
                            continue

                        # 匹配队伍
                        outcome_team, _ = fuzzy_match_team(outcome)
                        if outcome_team == std_team1:
                            team1_price = price
                        elif outcome_team == std_team2:
                            team2_price = price

            # 过滤已结束的比赛 (价格接近 100%/0% 或 0%/100%)
            if team1_price is not None and team2_price is not None:
                # 如果任一价格 > 0.95 或 < 0.05，说明比赛已结束或接近结束
                if team1_price > 0.95 or team1_price < 0.05 or team2_price > 0.95 or team2_price < 0.05:
                    print(f"[Polymarket] 跳过已结束比赛: {std_team1} vs {std_team2} ({team1_price:.1%} / {team2_price:.1%})")
                    continue

            # 解析结束时间
            end_time = None
            if end_date_str:
                try:
                    end_time = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                except:
                    pass

            # 构造市场 URL
            market_url = f"https://polymarket.com/event/{slug}" if slug else f"https://polymarket.com/event/{event_id}"

            matches.append({
                "team1": std_team1,
                "team2": std_team2,
                "team1_price": round(team1_price, 4) if team1_price else None,
                "team2_price": round(team2_price, 4) if team2_price else None,
                "url": market_url,
                "raw_question": title,
                "end_time": end_time,
                "event_id": str(event_id),
            })

            if team1_price and team2_price:
                print(f"[Polymarket] 找到比赛: {std_team1} vs {std_team2} ({team1_price:.2%} / {team2_price:.2%})")
            else:
                print(f"[Polymarket] 找到比赛: {std_team1} vs {std_team2} (无价格)")

        print(f"[Polymarket] 获取到 {len(matches)} 场 NBA 比赛市场")

        return matches, all_events

    except requests.exceptions.RequestException as e:
        print(f"[Polymarket] API 请求失败: {e}")
        return [], []


def match_daily_games(web2_matches, poly_data):
    """
    增强版：使用模糊匹配将 Web2 和 Polymarket 的比赛配对
    支持双向匹配、宽松日期检查、详细调试日志

    新功能：添加 Polymarket 独有的比赛（Web2 没有的）
    """
    print("\n[匹配] 正在匹配 Web2 和 Polymarket 的比赛...")

    # 解包 poly_data
    if isinstance(poly_data, tuple):
        poly_matches, all_nba_markets = poly_data
    else:
        poly_matches = poly_data
        all_nba_markets = []

    merged = []
    matched_poly_indices = set()  # 记录已匹配的 Polymarket 比赛索引

    for w2 in web2_matches:
        w2_home = w2["home_team"]
        w2_away = w2["away_team"]

        # 标准化 Web2 队名
        std_home, _ = fuzzy_match_team(w2_home)
        std_away, _ = fuzzy_match_team(w2_away)

        if not std_home or not std_away:
            print(f"[匹配] 警告: 无法标准化队名 {w2_home} vs {w2_away}")
            merged.append({
                **w2,
                "poly_home_price": None,
                "poly_away_price": None,
                "polymarket_url": None,
            })
            continue

        # 调试日志
        print(f"[匹配] Web2 找到: {std_home} vs {std_away}，正在 Polymarket 寻找...")

        # 在 Polymarket 中查找匹配的比赛
        best_poly = None
        best_poly_idx = None
        best_candidate = None
        best_similarity = 0

        for idx, poly in enumerate(poly_matches):
            p_team1 = poly["team1"]
            p_team2 = poly["team2"]

            # 计算相似度（用于调试）
            similarity = 0
            if std_home == p_team1:
                similarity += 50
            if std_away == p_team2:
                similarity += 50
            if std_home == p_team2:
                similarity += 50
            if std_away == p_team1:
                similarity += 50

            # 记录最佳候选
            if similarity > best_similarity:
                best_similarity = similarity
                best_candidate = poly

            # 检查两种可能的匹配顺序（双向匹配）
            # 顺序1: web2_home = poly_team1, web2_away = poly_team2
            if std_home == p_team1 and std_away == p_team2:
                best_poly = {
                    "home_price": poly["team1_price"],
                    "away_price": poly["team2_price"],
                    "url": poly["url"],
                }
                best_poly_idx = idx
                print(f"[匹配] 成功匹配: {poly['raw_question'][:60]}...")
                break
            # 顺序2: web2_home = poly_team2, web2_away = poly_team1
            elif std_home == p_team2 and std_away == p_team1:
                best_poly = {
                    "home_price": poly["team2_price"],
                    "away_price": poly["team1_price"],
                    "url": poly["url"],
                }
                best_poly_idx = idx
                print(f"[匹配] 成功匹配 (反向): {poly['raw_question'][:60]}...")
                break

        if best_poly:
            matched_poly_indices.add(best_poly_idx)
            merged.append({
                **w2,
                "home_team": std_home,
                "away_team": std_away,
                "poly_home_price": best_poly["home_price"],
                "poly_away_price": best_poly["away_price"],
                "polymarket_url": best_poly["url"],
            })
        else:
            # 匹配失败，打印调试信息
            if best_candidate:
                print(f"[匹配] 失败: Polymarket 最接近的候选项是 '{best_candidate['team1']} vs {best_candidate['team2']}' (相似度: {best_similarity}%)")
            else:
                print(f"[匹配] 失败: Polymarket 没有找到 {std_home} vs {std_away} 的市场")

            merged.append({
                **w2,
                "home_team": std_home,
                "away_team": std_away,
                "poly_home_price": None,
                "poly_away_price": None,
                "polymarket_url": None,
            })

    print(f"\n[匹配] Web2 比赛匹配完成: {len(merged)} 场")
    matched_count = sum(1 for m in merged if m.get("poly_home_price"))
    print(f"[匹配] 成功匹配 Polymarket: {matched_count} 场")

    # ============================================
    # 新增：添加 Polymarket 独有的比赛
    # ============================================
    poly_only_count = 0
    print(f"\n[Polymarket 独有] 正在添加 Polymarket 独有的比赛...")

    for idx, poly in enumerate(poly_matches):
        if idx in matched_poly_indices:
            continue  # 跳过已匹配的

        # 只添加有价格的比赛
        if poly["team1_price"] is None or poly["team2_price"] is None:
            continue

        # 创建 Polymarket-only 记录
        # 使用 event_id 作为 match_id
        match_id = f"poly_{poly.get('event_id', idx)}"

        merged.append({
            "match_id": match_id,
            "home_team": poly["team1"],
            "away_team": poly["team2"],
            "commence_time": poly.get("end_time") or datetime.now(),
            "home_odds": None,  # 没有 Web2 赔率
            "away_odds": None,
            "bookmaker": None,
            "bookmaker_url": None,
            "poly_home_price": poly["team1_price"],
            "poly_away_price": poly["team2_price"],
            "polymarket_url": poly["url"],
        })
        poly_only_count += 1
        print(f"[Polymarket 独有] 添加: {poly['team1']} vs {poly['team2']} ({poly['team1_price']:.1%} / {poly['team2_price']:.1%})")

    print(f"[Polymarket 独有] 添加了 {poly_only_count} 场 Polymarket 独有比赛")
    print(f"\n[匹配] 最终合计: {len(merged)} 场比赛")

    return merged


def save_daily_matches(matches):
    """
    将每日比赛数据保存到数据库
    """
    print("\n[入库] 正在保存每日比赛数据...")

    if not DATABASE_URL:
        print("[入库] 错误: DATABASE_URL 未设置")
        return False

    if not matches:
        print("[入库] 没有比赛数据可保存")
        return True

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # 清空现有 NBA 每日比赛数据
        cursor.execute("DELETE FROM daily_matches WHERE sport_type = 'nba';")

        # 插入新数据
        insert_sql = """
        INSERT INTO daily_matches
            (sport_type, match_id, home_team, away_team, commence_time,
             web2_home_odds, web2_away_odds, source_bookmaker, source_url,
             poly_home_price, poly_away_price, polymarket_url, last_updated)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (sport_type, match_id) DO UPDATE SET
            home_team = EXCLUDED.home_team,
            away_team = EXCLUDED.away_team,
            commence_time = EXCLUDED.commence_time,
            web2_home_odds = EXCLUDED.web2_home_odds,
            web2_away_odds = EXCLUDED.web2_away_odds,
            source_bookmaker = EXCLUDED.source_bookmaker,
            source_url = EXCLUDED.source_url,
            poly_home_price = EXCLUDED.poly_home_price,
            poly_away_price = EXCLUDED.poly_away_price,
            polymarket_url = EXCLUDED.polymarket_url,
            last_updated = CURRENT_TIMESTAMP
        """

        for m in matches:
            cursor.execute(insert_sql, (
                "nba",
                m["match_id"],
                m["home_team"],
                m["away_team"],
                m["commence_time"],
                m["home_odds"],
                m["away_odds"],
                m["bookmaker"],
                m.get("bookmaker_url"),
                m.get("poly_home_price"),
                m.get("poly_away_price"),
                m.get("polymarket_url"),
            ))

        conn.commit()
        print(f"[入库] 成功保存 {len(matches)} 场比赛")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"[入库] 数据库错误: {e}")
        return False


def fetch_and_save_nba_matches():
    """
    主函数：获取并保存 NBA 每日比赛数据
    """
    print("\n" + "=" * 60)
    print("正在处理: NBA 每日比赛 (H2H)")
    print("=" * 60)

    # 1. 获取 Web2 数据
    web2_matches = fetch_nba_matches_web2()

    # 2. 获取 Polymarket 数据
    poly_matches = fetch_nba_matches_polymarket()

    # 3. 匹配并合并
    merged = match_daily_games(web2_matches, poly_matches)

    # 4. 保存到数据库
    save_daily_matches(merged)

    return merged


# ============================================
# 数据合并与入库
# ============================================
def merge_and_save_data(sport_type, web2_data, poly_data, kalshi_data):
    """
    合并三个平台的数据并写入数据库
    web2_data 现在是 {team: {"odds": float, "bookmaker": str, "bookmaker_url": str}}
    """
    print(f"\n[合并] 正在合并 {sport_type} 数据...")

    # 获取所有出现过的队伍
    all_teams = set()
    all_teams.update(web2_data.keys())
    all_teams.update(poly_data.keys())
    all_teams.update(kalshi_data.keys())

    # 准备入库数据
    merged_data = []
    for team in all_teams:
        web2_info = web2_data.get(team, {})
        poly_info = poly_data.get(team, {})
        kalshi_info = kalshi_data.get(team, {})

        record = {
            "sport_type": sport_type,
            "team_name": team,
            # Web2 数据（包含 bookmaker 信息）
            "web2_odds": web2_info.get("odds") if isinstance(web2_info, dict) else None,
            "source_bookmaker": web2_info.get("bookmaker") if isinstance(web2_info, dict) else None,
            "source_url": web2_info.get("bookmaker_url") if isinstance(web2_info, dict) else None,
            # Polymarket 数据
            "polymarket_price": poly_info.get("price") if isinstance(poly_info, dict) else None,
            "polymarket_url": poly_info.get("url") if isinstance(poly_info, dict) else None,
            # Kalshi 数据
            "kalshi_price": kalshi_info.get("price") if isinstance(kalshi_info, dict) else None,
            "kalshi_url": kalshi_info.get("url") if isinstance(kalshi_info, dict) else None,
        }
        merged_data.append(record)

    print(f"[合并] {sport_type}: {len(merged_data)} 支队伍待入库")
    return merged_data


def save_to_database(all_data):
    """
    将所有赛事数据写入 PostgreSQL 数据库
    """
    print("\n" + "=" * 60)
    print("[入库] 正在写入数据库...")

    if not DATABASE_URL:
        print("[入库] 错误: DATABASE_URL 未设置")
        return False

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # 清空现有数据
        cursor.execute("TRUNCATE TABLE market_odds RESTART IDENTITY;")

        # 插入新数据（包含 bookmaker 信息）
        insert_sql = """
        INSERT INTO market_odds
            (sport_type, team_name, web2_odds, source_bookmaker, source_url,
             polymarket_price, polymarket_url, kalshi_price, kalshi_url, last_updated)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """

        for record in all_data:
            cursor.execute(insert_sql, (
                record["sport_type"],
                record["team_name"],
                record["web2_odds"],
                record["source_bookmaker"],
                record["source_url"],
                record["polymarket_price"],
                record["polymarket_url"],
                record["kalshi_price"],
                record["kalshi_url"]
            ))

        conn.commit()
        print(f"[入库] 成功写入 {len(all_data)} 条记录")

        # 显示各赛事统计
        cursor.execute("""
            SELECT sport_type, COUNT(*) as cnt,
                   COUNT(web2_odds) as web2_cnt,
                   COUNT(polymarket_price) as poly_cnt
            FROM market_odds
            GROUP BY sport_type
            ORDER BY sport_type;
        """)

        print("\n各赛事数据统计:")
        print("-" * 60)
        print(f"{'赛事':<15} {'总数':<10} {'Web2':<10} {'Polymarket':<10}")
        print("-" * 60)
        for row in cursor.fetchall():
            print(f"{row[0]:<15} {row[1]:<10} {row[2]:<10} {row[3]:<10}")
        print("-" * 60)

        # 显示前 5 条数据预览
        cursor.execute("""
            SELECT sport_type, team_name, web2_odds, polymarket_price
            FROM market_odds
            WHERE web2_odds IS NOT NULL
            ORDER BY web2_odds DESC
            LIMIT 10;
        """)

        print("\n热门队伍 Top 10 (按 Web2 胜率排序):")
        print("-" * 70)
        print(f"{'赛事':<12} {'队伍':<25} {'Web2胜率':<12} {'Poly价格':<12}")
        print("-" * 70)
        for row in cursor.fetchall():
            web2 = f"{row[2]:.4f}" if row[2] else "N/A"
            poly = f"{row[3]:.4f}" if row[3] else "N/A"
            print(f"{row[0]:<12} {row[1]:<25} {web2:<12} {poly:<12}")
        print("-" * 70)

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"[入库] 数据库错误: {e}")
        return False


# ============================================
# 主函数
# ============================================
def main():
    """主函数：抓取所有赛事的数据并合并入库"""
    print("=" * 60)
    print("PolyDelta - 多平台多赛事数据抓取脚本")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("支持赛事: World Cup, EPL, NBA")
    print("数据源: Web2 (TheOddsAPI), Polymarket")
    print("功能: 冠军盘口 (Outrights) + 每日比赛 (H2H)")
    print("Kalshi: 已禁用 (网络限制)")
    print("=" * 60)

    all_data = []
    stats = {}

    # 循环抓取每个赛事
    for sport_type in SPORTS_CONFIG.keys():
        print(f"\n{'='*60}")
        print(f"正在处理: {SPORTS_CONFIG[sport_type]['name']}")
        print("=" * 60)

        # 1. 获取 Web2 数据
        web2_data = fetch_web2_odds(sport_type)

        # 2. 获取 Polymarket 数据
        poly_data = fetch_polymarket_data(sport_type)

        # 3. 获取 Kalshi 数据 (已禁用，返回空)
        kalshi_data = fetch_kalshi_data(sport_type)

        # 4. 合并数据
        merged = merge_and_save_data(sport_type, web2_data, poly_data, kalshi_data)
        all_data.extend(merged)

        # 记录统计
        stats[sport_type] = {
            "web2": len(web2_data),
            "poly": len(poly_data),
            "kalshi": len(kalshi_data),
            "merged": len(merged)
        }

    # 5. 统一入库 (冠军盘口)
    save_to_database(all_data)

    # 6. 获取每日比赛 (H2H)
    daily_matches = fetch_and_save_nba_matches()

    # 最终统计
    print("\n" + "=" * 60)
    print("抓取完成！最终统计:")
    print("=" * 60)
    print("\n[冠军盘口 Outrights]")
    for sport, s in stats.items():
        print(f"  {sport}: Web2={s['web2']}, Poly={s['poly']}, 合并={s['merged']}")
    print(f"  总计: {len(all_data)} 条记录")
    print(f"\n[每日比赛 H2H]")
    print(f"  NBA: {len(daily_matches)} 场比赛")
    matched = sum(1 for m in daily_matches if m.get("poly_home_price"))
    print(f"  Polymarket 匹配: {matched} 场")
    print("=" * 60)


if __name__ == '__main__':
    main()
