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

# AI analysis is now handled by the separate daily_analysis_job.py cron.
# The scraper's only job is to update Match and Odds data in the DB.

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
    "epl_winner": {
        "name": "English Premier League Winner",
        "web2_key": None,  # The Odds API 没有 EPL Winner 市场
        "cache_file": "cache_epl_winner.json",
        "poly_keywords": ["premier league", "epl", "english premier"],
        "poly_only": True,  # 仅 Polymarket 数据
    },
    "ucl_winner": {
        "name": "UEFA Champions League Winner",
        "web2_key": None,  # The Odds API 没有 UCL Winner 市场
        "cache_file": "cache_ucl_winner.json",
        "poly_keywords": ["champions league", "ucl", "uefa"],
        "poly_only": True,  # 仅 Polymarket 数据
    },
    "nba": {
        "name": "NBA Championship",
        "web2_key": "basketball_nba_championship_winner",
        "cache_file": "cache_nba.json",
        "poly_keywords": ["nba", "basketball", "nba champion"],
    },
}

# ============================================
# 每日比赛配置 (Daily Matches)
# ============================================
DAILY_SPORTS_CONFIG = {
    "nba": {
        "name": "NBA",
        "web2_key": "basketball_nba",
        "market": "h2h",  # 2-way: Home/Away
        "is_3way": False,
    },
    "epl": {
        "name": "English Premier League",
        "web2_key": "soccer_epl",
        "market": "h2h",  # 3-way: Home/Draw/Away
        "is_3way": True,
    },
    "ucl": {
        "name": "UEFA Champions League",
        "web2_key": "soccer_uefa_champs_league",
        "market": "h2h",  # 3-way: Home/Draw/Away
        "is_3way": True,
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

    # ========== UEFA Champions League 球队 ==========
    "Real Madrid": {"web2": "Real Madrid", "poly": "Real Madrid"},
    "Barcelona": {"web2": "Barcelona", "poly": "Barcelona"},
    "Bayern Munich": {"web2": "Bayern Munich", "poly": "Bayern Munich"},
    "Paris Saint-Germain": {"web2": "Paris Saint Germain", "poly": "PSG"},
    "Juventus": {"web2": "Juventus", "poly": "Juventus"},
    "AC Milan": {"web2": "AC Milan", "poly": "AC Milan"},
    "Inter Milan": {"web2": "Inter Milan", "poly": "Inter Milan"},
    "Atletico Madrid": {"web2": "Atletico Madrid", "poly": "Atletico Madrid"},
    "Borussia Dortmund": {"web2": "Borussia Dortmund", "poly": "Dortmund"},
    "RB Leipzig": {"web2": "RB Leipzig", "poly": "Leipzig"},
    "Benfica": {"web2": "Benfica", "poly": "Benfica"},
    "Porto": {"web2": "FC Porto", "poly": "Porto"},
    "Ajax": {"web2": "Ajax", "poly": "Ajax"},
    "Napoli": {"web2": "Napoli", "poly": "Napoli"},
    "Sevilla": {"web2": "Sevilla", "poly": "Sevilla"},
    "Sporting CP": {"web2": "Sporting CP", "poly": "Sporting"},
    "Celtic": {"web2": "Celtic", "poly": "Celtic"},
    "PSV": {"web2": "PSV Eindhoven", "poly": "PSV"},
    "Feyenoord": {"web2": "Feyenoord", "poly": "Feyenoord"},
    "Club Brugge": {"web2": "Club Brugge", "poly": "Club Brugge"},
    "Red Bull Salzburg": {"web2": "Red Bull Salzburg", "poly": "Salzburg"},
    "Shakhtar Donetsk": {"web2": "Shakhtar Donetsk", "poly": "Shakhtar"},
    "Dinamo Zagreb": {"web2": "Dinamo Zagreb", "poly": "Dinamo Zagreb"},
    "Young Boys": {"web2": "Young Boys", "poly": "Young Boys"},
    "Galatasaray": {"web2": "Galatasaray", "poly": "Galatasaray"},
    "Lazio": {"web2": "Lazio", "poly": "Lazio"},
    "Atalanta": {"web2": "Atalanta", "poly": "Atalanta"},
    "Monaco": {"web2": "Monaco", "poly": "Monaco"},
    "Lille": {"web2": "Lille", "poly": "Lille"},
    "Bayer Leverkusen": {"web2": "Bayer Leverkusen", "poly": "Leverkusen"},
    "Stuttgart": {"web2": "VfB Stuttgart", "poly": "Stuttgart"},
    "Girona": {"web2": "Girona", "poly": "Girona"},
    "Bologna": {"web2": "Bologna", "poly": "Bologna"},
    "Brest": {"web2": "Stade Brestois 29", "poly": "Brest"},
    "Sparta Prague": {"web2": "Sparta Prague", "poly": "Sparta Prague"},
    "Sturm Graz": {"web2": "Sturm Graz", "poly": "Sturm Graz"},
    "Slovan Bratislava": {"web2": "Slovan Bratislava", "poly": "Slovan Bratislava"},

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

# ============================================
# Soccer 队伍简称映射 (用于模糊匹配)
# ============================================
SOCCER_TEAM_ALIASES = {
    # EPL Teams
    "Arsenal": ["arsenal", "gunners"],
    "Manchester City": ["man city", "city", "manchester city"],
    "Liverpool": ["liverpool", "reds"],
    "Chelsea": ["chelsea", "blues"],
    "Manchester United": ["man utd", "man united", "manchester united", "united"],
    "Tottenham Hotspur": ["tottenham", "spurs", "tottenham hotspur"],
    "Newcastle United": ["newcastle", "magpies", "newcastle united"],
    "Aston Villa": ["aston villa", "villa"],
    "Brighton and Hove Albion": ["brighton", "brighton hove albion", "seagulls"],
    "West Ham United": ["west ham", "hammers", "west ham united"],
    "Fulham": ["fulham", "cottagers"],
    "Brentford": ["brentford", "bees"],
    "Crystal Palace": ["crystal palace", "palace", "eagles"],
    "Everton": ["everton", "toffees"],
    "Nottingham Forest": ["nottingham forest", "forest", "nott'm forest"],
    "AFC Bournemouth": ["bournemouth", "afc bournemouth", "cherries"],
    "Wolverhampton Wanderers": ["wolves", "wolverhampton", "wolverhampton wanderers"],
    "Leicester City": ["leicester", "foxes", "leicester city"],
    "Ipswich Town": ["ipswich", "ipswich town", "tractor boys"],
    "Southampton": ["southampton", "saints"],
    # UCL Teams
    "Real Madrid": ["real madrid", "real", "los blancos"],
    "Barcelona": ["barcelona", "barca", "fcb"],
    "Bayern Munich": ["bayern", "bayern munich", "bayern munchen"],
    "Paris Saint Germain": ["psg", "paris", "paris saint-germain", "paris sg"],
    "Juventus": ["juventus", "juve"],
    "AC Milan": ["ac milan", "milan"],
    "Inter Milan": ["inter", "inter milan", "internazionale"],
    "Atletico Madrid": ["atletico", "atletico madrid", "atleti"],
    "Borussia Dortmund": ["dortmund", "bvb", "borussia dortmund"],
    "RB Leipzig": ["leipzig", "rb leipzig"],
    "Benfica": ["benfica", "sl benfica"],
    "FC Porto": ["porto", "fc porto"],
    "Ajax": ["ajax", "afc ajax"],
    "Napoli": ["napoli", "ssc napoli"],
    "Sevilla": ["sevilla", "sevilla fc"],
    "Sporting CP": ["sporting", "sporting cp", "sporting lisbon"],
    "Celtic": ["celtic", "celtic fc"],
    "PSV Eindhoven": ["psv", "psv eindhoven"],
    "Feyenoord": ["feyenoord"],
    "Club Brugge": ["club brugge", "brugge"],
    "Red Bull Salzburg": ["salzburg", "rb salzburg", "red bull salzburg"],
    "Shakhtar Donetsk": ["shakhtar", "shakhtar donetsk"],
    "Galatasaray": ["galatasaray", "gala"],
    "Lazio": ["lazio", "ss lazio"],
    "Atalanta": ["atalanta"],
    "Monaco": ["monaco", "as monaco"],
    "Lille": ["lille", "losc", "losc lille"],
    "Bayer Leverkusen": ["leverkusen", "bayer leverkusen"],
    "VfB Stuttgart": ["stuttgart", "vfb stuttgart"],
}

# ============================================
# Strict Dictionary Mapping: The Odds API -> Polymarket
# (Applied BEFORE fuzzy matching for precise team name normalization)
# ============================================
SOCCER_TEAM_MAPPING = {
    # EPL Teams - The Odds API Name : Polymarket Name
    # Note: Polymarket uses "Team FC" format, we map to clean names
    "Wolverhampton Wanderers": "Wolves",
    "Wolverhampton Wanderers FC": "Wolves",
    "Brighton and Hove Albion": "Brighton",
    "Brighton and Hove Albion FC": "Brighton",
    "Brighton & Hove Albion FC": "Brighton",
    "Leeds United": "Leeds United",
    "Leeds United FC": "Leeds United",
    "West Ham United": "West Ham",
    "West Ham United FC": "West Ham",
    "Manchester United": "Manchester United",
    "Manchester United FC": "Manchester United",
    "Manchester City": "Manchester City",
    "Manchester City FC": "Manchester City",
    "Newcastle United": "Newcastle",
    "Newcastle United FC": "Newcastle",
    "Tottenham Hotspur": "Tottenham",
    "Tottenham Hotspur FC": "Tottenham",
    "Nottingham Forest": "Nottingham Forest",
    "Nottingham Forest FC": "Nottingham Forest",
    "Sheffield United": "Sheffield United",
    "Sheffield United FC": "Sheffield United",
    "Leicester City": "Leicester",
    "Leicester City FC": "Leicester",
    "AFC Bournemouth": "Bournemouth",
    "Bournemouth FC": "Bournemouth",
    "Ipswich Town": "Ipswich",
    "Ipswich Town FC": "Ipswich",
    "Arsenal": "Arsenal",
    "Arsenal FC": "Arsenal",
    "Chelsea": "Chelsea",
    "Chelsea FC": "Chelsea",
    "Liverpool": "Liverpool",
    "Liverpool FC": "Liverpool",
    "Everton": "Everton",
    "Everton FC": "Everton",
    "Aston Villa": "Aston Villa",
    "Aston Villa FC": "Aston Villa",
    "Crystal Palace": "Crystal Palace",
    "Crystal Palace FC": "Crystal Palace",
    "Fulham": "Fulham",
    "Fulham FC": "Fulham",
    "Brentford": "Brentford",
    "Brentford FC": "Brentford",
    "Southampton": "Southampton",
    "Southampton FC": "Southampton",
    # UCL Teams - Standard mappings
    "Paris Saint Germain": "PSG",
    "Paris Saint-Germain FC": "PSG",
    "Bayern Munich": "Bayern",
    "FC Bayern Munich": "Bayern",
    "Borussia Dortmund": "Dortmund",
    "RB Leipzig": "Leipzig",
    "Atletico Madrid": "Atletico",
    "Club Atlético De Madrid": "Atletico",
    "Inter Milan": "Inter",
    "AC Milan": "Milan",
    "Red Bull Salzburg": "Salzburg",
    "PSV Eindhoven": "PSV",
    "Shakhtar Donetsk": "Shakhtar",
    "Bayer Leverkusen": "Leverkusen",
    "VfB Stuttgart": "Stuttgart",
    "Sporting CP": "Sporting",
    "Sporting Lisbon": "Sporting",
    # UCL Teams - With Polymarket ticker prefixes (e.g., "ATM Club Atlético De Madrid")
    "FK Bodø/Glimt": "Bodo Glimt",
    "Bodo/Glimt": "Bodo Glimt",
    "Qairat FK": "Kairat Almaty",
    "FC Kairat": "Kairat Almaty",
    "Real Madrid": "Real Madrid",
    "Real Madrid CF": "Real Madrid",
    "FC Barcelona": "Barcelona",
    "Juventus": "Juventus",
    "Juventus FC": "Juventus",
    "Benfica": "Benfica",
    "SL Benfica": "Benfica",
    "Feyenoord": "Feyenoord",
    "Feyenoord Rotterdam": "Feyenoord",
    "Club Brugge": "Club Brugge",
    "Club Brugge KV": "Club Brugge",
    "Lille": "Lille",
    "Lille OSC": "Lille",
    "Celtic": "Celtic",
    "Celtic FC": "Celtic",
    "Monaco": "Monaco",
    "AS Monaco": "Monaco",
    "Atalanta": "Atalanta",
    "Atalanta BC": "Atalanta",
    "Aston Villa": "Aston Villa",
    "Girona": "Girona",
    "Girona FC": "Girona",
    "Stuttgart": "Stuttgart",
    "Dinamo Zagreb": "Dinamo Zagreb",
    "GNK Dinamo Zagreb": "Dinamo Zagreb",
    "Slovan Bratislava": "Slovan Bratislava",
    "SK Slovan Bratislava": "Slovan Bratislava",
    "Sturm Graz": "Sturm Graz",
    "SK Sturm Graz": "Sturm Graz",
    "Bologna": "Bologna",
    "Bologna FC": "Bologna",
    "Sparta Praha": "Sparta Prague",
    "Sparta Prague": "Sparta Prague",
    "AC Sparta Praha": "Sparta Prague",
    "Young Boys": "Young Boys",
    "BSC Young Boys": "Young Boys",
    "Crvena Zvezda": "Red Star Belgrade",
    "Red Star Belgrade": "Red Star Belgrade",
    "FK Crvena Zvezda": "Red Star Belgrade",
}

# Reverse mapping: Polymarket Name -> The Odds API Name
SOCCER_TEAM_MAPPING_REVERSE = {v: k for k, v in SOCCER_TEAM_MAPPING.items()}


def normalize_team_for_matching(name):
    """
    Normalize a team name for matching.
    1. Strip ticker prefixes (e.g., "ATM ", "BOG1 ")
    2. First try strict dictionary mapping
    3. Strip FC/AFC suffix and try again
    4. Return cleaned name if no mapping exists
    """
    name_stripped = name.strip()

    # Strip Polymarket ticker prefix (e.g., "ATM Club Atlético" -> "Club Atlético")
    # Pattern: 2-4 uppercase letters + optional digit + space at start
    name_no_ticker = re.sub(r'^[A-Z]{2,4}\d?\s+', '', name_stripped).strip()

    # Try all variants: original, without ticker, without FC suffix
    variants = [name_stripped, name_no_ticker]

    for variant in variants:
        # Check if it's a The Odds API name that needs mapping to Polymarket
        if variant in SOCCER_TEAM_MAPPING:
            return SOCCER_TEAM_MAPPING[variant]

    # Strip FC/AFC/CF suffix and try again
    name_clean = re.sub(r'\s*(FC|AFC|CF)$', '', name_stripped, flags=re.IGNORECASE).strip()
    name_no_ticker_clean = re.sub(r'\s*(FC|AFC|CF)$', '', name_no_ticker, flags=re.IGNORECASE).strip()

    for variant in [name_clean, name_no_ticker_clean]:
        if variant in SOCCER_TEAM_MAPPING:
            return SOCCER_TEAM_MAPPING[variant]

    # Check if it's already a Polymarket name (reverse lookup)
    for variant in [name_stripped, name_no_ticker, name_clean, name_no_ticker_clean]:
        if variant in SOCCER_TEAM_MAPPING_REVERSE:
            return variant  # Already in Polymarket format

    return name_no_ticker_clean  # Return cleaned version without ticker and FC suffix


def fuzzy_match_soccer_team(name, threshold=75):
    """
    使用模糊匹配找到最匹配的足球队伍
    返回: (标准队名, 匹配分数) 或 (None, 0)

    匹配顺序:
    1. 严格字典映射 (The Odds API -> Polymarket)
    2. 精确别名匹配
    3. 模糊匹配
    """
    name_stripped = name.strip()
    name_lower = name_stripped.lower()

    # 1. 严格字典映射 - 优先级最高
    if name_stripped in SOCCER_TEAM_MAPPING:
        mapped_name = SOCCER_TEAM_MAPPING[name_stripped]
        # 找到对应的标准队名
        for team, aliases in SOCCER_TEAM_ALIASES.items():
            if mapped_name.lower() in [a.lower() for a in aliases] or mapped_name.lower() == team.lower():
                return team, 100
        return name_stripped, 100  # 如果没找到别名，返回原始名称

    # 反向映射检查 (Polymarket 名称 -> 标准名称)
    if name_stripped in SOCCER_TEAM_MAPPING_REVERSE:
        original_name = SOCCER_TEAM_MAPPING_REVERSE[name_stripped]
        for team, aliases in SOCCER_TEAM_ALIASES.items():
            if original_name.lower() == team.lower():
                return team, 100
        return original_name, 100

    # 2. 精确别名匹配
    for team, aliases in SOCCER_TEAM_ALIASES.items():
        if name_lower == team.lower():
            return team, 100
        for alias in aliases:
            if name_lower == alias.lower():
                return team, 100

    # 模糊匹配
    best_match = None
    best_score = 0

    for team, aliases in SOCCER_TEAM_ALIASES.items():
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
            if alias.lower() in name_lower or name_lower in alias.lower():
                score = 90
                if score > best_score:
                    best_score = score
                    best_match = team

    if best_score >= threshold:
        return best_match, best_score
    return None, 0


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

    # 如果是 poly_only 配置，跳过 Web2 API 调用
    if config.get("poly_only"):
        print(f"\n[Web2] {config['name']} 为 Polymarket 专属市场，跳过 Web2 API")
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
            "odds": avg_prob,  # 临时存储原始概率，稍后去抽水
            "bookmaker": display_name,
            "bookmaker_key": bookmaker_key,
            "bookmaker_url": bookmaker_url,
        }

    # ============================================
    # De-vig: 去除博彩公司抽水 (Multiplicative Method)
    # 原理: 所有队伍的隐含概率总和 > 100%，超出部分就是 vig
    # 方法: 将每个队伍的概率除以总和，使其归一化为 100%
    # ============================================
    if team_data:
        total_implied_prob = sum(t["odds"] for t in team_data.values())
        vig_percentage = (total_implied_prob - 1) * 100  # 转为百分比显示

        print(f"[Web2] 原始隐含概率总和: {total_implied_prob:.4f} (抽水: {vig_percentage:.1f}%)")

        # 归一化去抽水
        for team in team_data:
            raw_prob = team_data[team]["odds"]
            devigged_prob = raw_prob / total_implied_prob
            team_data[team]["odds"] = round(devigged_prob, 4)

        print(f"[Web2] 去抽水后概率总和: {sum(t['odds'] for t in team_data.values()):.4f}")

    print(f"[Web2] 获取到 {len(team_data)} 支队伍的数据 (已去抽水)")
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
# Polymarket 流动性深度 (CLOB Order Book API)
# ============================================

def fetch_polymarket_liquidity(token_id, current_price, side="buy", depth_percent=0.02):
    """
    从 Polymarket CLOB API 获取订单簿深度
    计算在价格上涨 depth_percent (默认 2%) 范围内可买入的 USDC 数量

    Args:
        token_id: Polymarket 市场的 Token ID
        current_price: 当前价格 (0-1)
        side: "buy" 买入深度, "sell" 卖出深度
        depth_percent: 价格变动范围 (默认 2%)

    Returns:
        float: 可交易的 USDC 数量
    """
    if not token_id or not current_price:
        return None

    try:
        # Polymarket CLOB API endpoint
        url = f"https://clob.polymarket.com/book"
        params = {"token_id": token_id}

        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return None

        data = response.json()

        # 订单簿格式: {"bids": [[price, size], ...], "asks": [[price, size], ...]}
        # bids 是买单 (从高到低), asks 是卖单 (从低到高)
        # 买入 YES Token: 消耗 asks (卖单)
        # 卖出 YES Token: 消耗 bids (买单)

        if side == "buy":
            orders = data.get("asks", [])
            # 计算价格上限 (当前价格 + 2%)
            price_limit = current_price + depth_percent
        else:
            orders = data.get("bids", [])
            # 计算价格下限 (当前价格 - 2%)
            price_limit = current_price - depth_percent

        # 解析订单并按价格排序
        parsed_orders = []
        for order in orders:
            if isinstance(order, dict):
                price = float(order.get("price", 0))
                size = float(order.get("size", 0))
            elif isinstance(order, (list, tuple)) and len(order) >= 2:
                price = float(order[0])
                size = float(order[1])
            else:
                continue
            parsed_orders.append((price, size))

        # 排序: asks 按价格升序 (最低价优先), bids 按价格降序 (最高价优先)
        if side == "buy":
            parsed_orders.sort(key=lambda x: x[0])  # 升序
        else:
            parsed_orders.sort(key=lambda x: x[0], reverse=True)  # 降序

        total_usdc = 0.0

        for price, size in parsed_orders:
            # 检查是否在价格范围内
            if side == "buy" and price > price_limit:
                break
            if side == "sell" and price < price_limit:
                break

            # 计算 USDC 价值 (price * size)
            usdc_value = price * size
            total_usdc += usdc_value

        return round(total_usdc, 2)

    except Exception as e:
        # 静默失败，不影响主流程
        return None


def get_market_token_ids(market):
    """
    从 Polymarket 市场数据中提取 Token IDs
    返回: {"yes": token_id, "no": token_id} 或 {outcome_name: token_id, ...}
    """
    clob_token_ids = market.get("clobTokenIds")
    outcomes = market.get("outcomes", [])

    if isinstance(clob_token_ids, str):
        try:
            clob_token_ids = json.loads(clob_token_ids)
        except:
            return {}

    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except:
            return {}

    if not clob_token_ids or not outcomes:
        return {}

    # 将 outcome 名称与 token ID 配对
    token_map = {}
    for i, outcome in enumerate(outcomes):
        if i < len(clob_token_ids):
            token_map[outcome.lower()] = clob_token_ids[i]

    return token_map


# ============================================
# Polymarket 数据抓取 (Gamma API) - 多赛事支持
# ============================================

# 从问题中提取球队名的正则模式
# 注意：只匹配 "win the" 夺冠盘口，排除 "qualify" 出线盘口
TEAM_EXTRACT_PATTERNS = {
    "nba": re.compile(r"Will the (.+?) win the \d{4} NBA Finals", re.IGNORECASE),
    "world_cup": re.compile(r"Will (.+?) win the \d{4} FIFA World Cup", re.IGNORECASE),
    "epl_winner": re.compile(r"Will (.+?) win the \d{4}[–-]\d{2,4} English Premier League", re.IGNORECASE),
    "ucl_winner": re.compile(r"Will (.+?) win the \d{4}[–-]\d{2,4} Champions League", re.IGNORECASE),
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

    # Gamma API endpoint - 使用分页获取更多市场
    url = "https://gamma-api.polymarket.com/markets"

    # 收集所有市场数据（使用分页）
    all_markets = []
    for offset in [0, 500, 1000, 1500, 2000]:
        params = {
            "closed": "false",
            "limit": 500,
            "offset": offset
        }
        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            batch = response.json()
            all_markets.extend(batch)
            if len(batch) < 500:  # 没有更多数据了
                break
        except requests.exceptions.RequestException as e:
            print(f"[Polymarket] 分页请求失败 (offset={offset}): {e}")
            break

    markets = all_markets
    result = {}
    keywords = config['poly_keywords']
    pattern = TEAM_EXTRACT_PATTERNS.get(sport_type)

    try:

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

            # 对于 EPL Winner：必须包含 "win the" + "english premier league"
            elif sport_type == "epl_winner":
                if "english premier league" in question_lower and "win" in question_lower:
                    # 排除非夺冠盘口 (2nd place, 3rd place, last place, relegated, top 4, top goal scorer)
                    exclude_patterns = ["2nd place", "3rd place", "last place", "relegated", "top 4", "top goal scorer", "finish in"]
                    if not any(p in question_lower for p in exclude_patterns):
                        matched = True

            # 对于 UCL Winner：必须包含 "win the" + "champions league"
            elif sport_type == "ucl_winner":
                if "champions league" in question_lower and "win" in question_lower:
                    # 排除 "top scorer", "advance", "league phase" 等非夺冠盘口
                    exclude_patterns = ["top scorer", "advance", "league phase", "round of 16", "finish first"]
                    if not any(p in question_lower for p in exclude_patterns):
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
                                # 获取流动性数据
                                liquidity = None
                                token_map = get_market_token_ids(market)
                                yes_token_id = token_map.get("yes")
                                if yes_token_id:
                                    liquidity = fetch_polymarket_liquidity(yes_token_id, yes_price, side="buy")

                                result[standard_name] = {
                                    "price": round(yes_price, 4),
                                    "url": market_url,
                                    "liquidity": liquidity
                                }

        print(f"[Polymarket] 获取到 {len(result)} 支队伍的数据")
        return result

    except requests.exceptions.RequestException as e:
        print(f"[Polymarket] API 请求失败: {e}")
        return {}


def fetch_fifa_qualification_markets():
    """
    从 Polymarket 获取 FIFA World Cup 2026 出线预测市场
    Event ID: 26313 - "2026 FIFA World Cup: Which countries qualify?"
    返回: {country_name: {"price": float, "url": str, "liquidity": float}}
    """
    print(f"\n[Polymarket] 正在获取 FIFA World Cup 2026 出线预测...")

    EVENT_ID = "26313"
    url = f"https://gamma-api.polymarket.com/events/{EVENT_ID}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        event = response.json()

        markets = event.get("markets", [])
        result = {}

        # 匹配模式: "Will [Country] qualify for the 2026 FIFA World Cup?"
        pattern = re.compile(r"Will (.+?) qualify for the \d{4} FIFA World Cup", re.IGNORECASE)

        for market in markets:
            question = market.get("question", "")
            match = pattern.search(question)

            if match:
                country_name = match.group(1).strip()

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

                # 找到 Yes 选项的价格（出线概率）
                yes_price = None
                for i, outcome in enumerate(outcomes):
                    if outcome.lower() == "yes" and i < len(outcome_prices):
                        try:
                            yes_price = float(outcome_prices[i])
                        except (ValueError, TypeError):
                            pass
                        break

                if yes_price is not None:
                    # 获取流动性数据
                    liquidity = None
                    token_map = get_market_token_ids(market)
                    yes_token_id = token_map.get("yes")
                    if yes_token_id:
                        liquidity = fetch_polymarket_liquidity(yes_token_id, yes_price, side="buy")

                    # 生成市场 URL
                    slug = market.get("slug", market.get("id", ""))
                    market_url = f"https://polymarket.com/market/{slug}"

                    # 标准化国家名称
                    standard_name = standardize_name(country_name, "poly")
                    if not standard_name:
                        standard_name = country_name  # 如果不在映射中，使用原名

                    result[standard_name] = {
                        "price": round(yes_price, 4),
                        "url": market_url,
                        "liquidity": liquidity
                    }

        print(f"[Polymarket] 获取到 {len(result)} 个国家的出线预测数据")
        return result

    except requests.exceptions.RequestException as e:
        print(f"[Polymarket] 出线预测 API 请求失败: {e}")
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
    支持缓存：API 失败时使用缓存数据
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

    # 缓存文件路径
    cache_file = os.path.join(CACHE_DIR, "cache_daily_nba.json")

    def load_from_cache():
        """从缓存加载数据"""
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                matches = []
                for m in cached.get("matches", []):
                    m["commence_time"] = datetime.fromisoformat(m["commence_time"])
                    matches.append(m)
                cache_time = cached.get("cached_at", "unknown")
                print(f"[Web2] 使用 NBA 缓存数据 (缓存时间: {cache_time}), {len(matches)} 场比赛")
                return matches
            except Exception as e:
                print(f"[Web2] NBA 缓存加载失败: {e}")
        return []

    def save_to_cache(matches):
        """保存数据到缓存"""
        try:
            cache_data = []
            for m in matches:
                m_copy = m.copy()
                m_copy["commence_time"] = m["commence_time"].isoformat()
                cache_data.append(m_copy)
            with open(cache_file, 'w') as f:
                json.dump({
                    "matches": cache_data,
                    "cached_at": datetime.now().isoformat(),
                    "sport_key": "basketball_nba",
                    "sport_name": "NBA",
                }, f, indent=2)
            print(f"[Web2] NBA 数据已缓存到 {cache_file}")
        except Exception as e:
            print(f"[Web2] NBA 缓存保存失败: {e}")

    if not ODDS_API_KEY or ODDS_API_KEY == "你的_TheOddsAPI_Key":
        print("[Web2] 警告: ODDS_API_KEY 未设置，尝试使用缓存...")
        return load_from_cache()

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
            print("[Web2] NBA 比赛暂无数据，尝试使用缓存...")
            return load_from_cache()

        if response.status_code == 401:
            print("[Web2] API 配额已用尽，尝试使用缓存...")
            return load_from_cache()

        if response.status_code == 429:
            print("[Web2] API 请求过于频繁，尝试使用缓存...")
            return load_from_cache()

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

            # De-vig: 去除博彩公司抽水 (Multiplicative Method)
            # 对于 H2H，home + away 概率总和应为 100%
            total_prob = avg_home + avg_away
            devigged_home = avg_home / total_prob
            devigged_away = avg_away / total_prob

            bookmaker_url = BOOKMAKER_URLS.get(best_bk["key"], "")
            display_name = BOOKMAKER_DISPLAY_NAMES.get(best_bk["key"], best_bk["title"])

            matches.append({
                "match_id": match_id,
                "home_team": home_team,
                "away_team": away_team,
                "commence_time": datetime.fromisoformat(commence_time.replace("Z", "+00:00")),
                "home_odds": round(devigged_home, 4),
                "away_odds": round(devigged_away, 4),
                "bookmaker": display_name,
                "bookmaker_url": bookmaker_url,
            })

        print(f"[Web2] 获取到 {len(matches)} 场 NBA 比赛")

        # 成功获取数据后保存到缓存
        if matches:
            save_to_cache(matches)

        return matches

    except requests.exceptions.RequestException as e:
        print(f"[Web2] API 请求失败: {e}，尝试使用缓存...")
        return load_from_cache()


def fetch_nba_matches_polymarket():
    """
    从 Polymarket Gamma API 获取 NBA 每日比赛数据
    使用 Events API (tag_slug=nba)
    格式: "Team1 vs. Team2" (例如 "Grizzlies vs. Lakers")

    过滤条件:
    - 排除已结束的比赛 (价格接近 100%/0% 或结束时间已过)
    - 排除冠军、MVP 等非每日比赛盘口
    - 去重：同一场比赛可能有多个市场
    """
    print("\n[Polymarket] 正在获取 NBA 每日比赛数据...")

    # 使用 Events API 获取 NBA 比赛
    url = "https://gamma-api.polymarket.com/events"
    params = {
        "limit": 100,
        "active": "true",
        "closed": "false",
        "tag_slug": "nba",
    }

    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        events = response.json()

        # 用于去重的字典: {(team1, team2): match_data}
        unique_matches = {}
        all_events = []

        # 匹配模式: "Team1 vs. Team2" 或 "Team1 vs Team2"
        vs_pattern = re.compile(r"^(.+?)\s+vs\.?\s+(.+?)$", re.IGNORECASE)
        now = datetime.utcnow()

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
                continue

            # 解析结束时间，跳过已过期的比赛
            end_time = None
            if end_date_str:
                try:
                    end_time = datetime.fromisoformat(end_date_str.replace("Z", "+00:00").replace("+00:00", ""))
                    if end_time < now:
                        continue  # 跳过已过期
                except:
                    pass

            # 获取市场详情（价格）- 优先找主市场 (Moneyline)，避免匹配到 Spread
            event_markets = event.get("markets", [])

            team1_price = None
            team2_price = None
            best_match = None  # 存储最佳匹配的市场

            # 第一遍：寻找主市场 (Question 格式: "Team1 vs. Team2")
            for market in event_markets:
                question = market.get("question", "")
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

                # 只处理两个选项的市场，且选项不是 Yes/No/Over/Under
                if len(outcomes) != 2:
                    continue
                if any(o in ["Yes", "No", "Over", "Under"] for o in outcomes):
                    continue

                # 跳过 Spread、Over/Under、半场 (1H) 市场
                question_lower = question.lower()
                if any(kw in question_lower for kw in ["spread", "o/u", "1h"]):
                    continue

                # 尝试匹配两个选项为两支队伍
                matched_prices = {}
                for i, outcome in enumerate(outcomes):
                    if i >= len(outcome_prices):
                        continue
                    try:
                        price = float(outcome_prices[i])
                    except:
                        continue

                    outcome_team, _ = fuzzy_match_team(outcome)
                    if outcome_team in [std_team1, std_team2]:
                        matched_prices[outcome_team] = price

                # 如果成功匹配到两队价格
                if len(matched_prices) == 2:
                    # 优先选择 Question 格式为 "Team vs. Team" 的主市场
                    is_main_market = "vs." in question or "vs " in question.lower()

                    if is_main_market or best_match is None:
                        best_match = matched_prices
                        # 找到主市场就停止
                        if is_main_market:
                            break

            # 使用最佳匹配
            if best_match:
                team1_price = best_match.get(std_team1)
                team2_price = best_match.get(std_team2)

            # 过滤已结束的比赛 (价格接近 100%/0%)
            if team1_price is not None and team2_price is not None:
                if team1_price > 0.95 or team1_price < 0.05 or team2_price > 0.95 or team2_price < 0.05:
                    continue

            # 没有价格的跳过
            if team1_price is None or team2_price is None:
                continue

            # 构造市场 URL
            market_url = f"https://polymarket.com/event/{slug}" if slug else f"https://polymarket.com/event/{event_id}"

            # 去重：用排序后的队伍名作为 key
            match_key = tuple(sorted([std_team1, std_team2]))

            # 如果已存在，保留结束时间更近的（更新的比赛）
            if match_key in unique_matches:
                existing = unique_matches[match_key]
                if existing.get("end_time") and end_time:
                    if end_time <= existing["end_time"]:
                        continue  # 现有的更新，跳过

            # 获取 Token IDs 用于流动性查询 - 只从主市场获取
            token_ids = {}
            for market in event_markets:
                question = market.get("question", "")
                outcomes = market.get("outcomes", [])

                if isinstance(outcomes, str):
                    try:
                        outcomes = json.loads(outcomes)
                    except:
                        continue

                # 确保是主市场：包含 "vs." 且没有 Spread/O/U/Player
                if "vs." in question and len(outcomes) == 2:
                    question_lower = question.lower()
                    if not any(kw in question_lower for kw in ["spread", "o/u", "1h", "points", "assists", "rebounds"]):
                        token_map = get_market_token_ids(market)
                        if token_map:
                            token_ids = token_map
                            break

            unique_matches[match_key] = {
                "team1": std_team1,
                "team2": std_team2,
                "team1_price": round(team1_price, 4),
                "team2_price": round(team2_price, 4),
                "url": market_url,
                "raw_question": title,
                "end_time": end_time,
                "event_id": str(event_id),
                "token_ids": token_ids,  # 添加 Token IDs
            }

        matches = list(unique_matches.values())

        # 获取流动性数据 (批量处理)
        print(f"[Polymarket] 正在获取流动性数据...")
        # 获取所有今日比赛的流动性（不限制数量，因为流动性数据对用户很重要）
        for m in matches:
            token_ids = m.get("token_ids", {})
            team1_price = m.get("team1_price")
            team2_price = m.get("team2_price")

            # 尝试获取每个队伍的流动性
            team1_liq = None
            team2_liq = None

            # Token IDs 可能是 {team_name: token_id} 或 {"yes": token_id, "no": token_id}
            for outcome_name, token_id in token_ids.items():
                outcome_lower = outcome_name.lower()
                # 匹配 team1
                if m["team1"].lower() in outcome_lower or outcome_lower in m["team1"].lower():
                    team1_liq = fetch_polymarket_liquidity(token_id, team1_price, "buy")
                # 匹配 team2 (使用 if 而非 elif，确保两个队伍都获取流动性)
                if m["team2"].lower() in outcome_lower or outcome_lower in m["team2"].lower():
                    team2_liq = fetch_polymarket_liquidity(token_id, team2_price, "buy")

            m["team1_liquidity"] = team1_liq
            m["team2_liquidity"] = team2_liq

        for m in matches:
            liq1 = m.get("team1_liquidity")
            liq2 = m.get("team2_liquidity")
            liq_str = ""
            if liq1 or liq2:
                liq_str = f" [Liq: ${liq1 or 0:.0f} / ${liq2 or 0:.0f}]"
            print(f"[Polymarket] 找到比赛: {m['team1']} vs {m['team2']} ({m['team1_price']:.1%} / {m['team2_price']:.1%}){liq_str}")

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
                    "home_liquidity": poly.get("team1_liquidity"),
                    "away_liquidity": poly.get("team2_liquidity"),
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
                    "home_liquidity": poly.get("team2_liquidity"),
                    "away_liquidity": poly.get("team1_liquidity"),
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
                "liquidity_home": best_poly.get("home_liquidity"),
                "liquidity_away": best_poly.get("away_liquidity"),
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
                "liquidity_home": None,
                "liquidity_away": None,
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
            "liquidity_home": poly.get("team1_liquidity"),
            "liquidity_away": poly.get("team2_liquidity"),
        })
        poly_only_count += 1
        print(f"[Polymarket 独有] 添加: {poly['team1']} vs {poly['team2']} ({poly['team1_price']:.1%} / {poly['team2_price']:.1%})")

    print(f"[Polymarket 独有] 添加了 {poly_only_count} 场 Polymarket 独有比赛")
    print(f"\n[匹配] 最终合计: {len(merged)} 场比赛")

    return merged


def save_daily_matches(matches):
    """
    将每日比赛数据保存到数据库，并生成 AI 分析报告
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

        # 获取现有的 AI 分析报告 (用于 4 小时复用逻辑)
        cursor.execute("""
            SELECT match_id, ai_analysis, analysis_timestamp
            FROM daily_matches
            WHERE sport_type = 'nba' AND ai_analysis IS NOT NULL
        """)
        existing_reports = {row[0]: {"analysis": row[1], "timestamp": row[2]} for row in cursor.fetchall()}
        print(f"[入库] 获取到 {len(existing_reports)} 条现有 AI 报告")

        # 清空现有 NBA 每日比赛数据
        cursor.execute("DELETE FROM daily_matches WHERE sport_type = 'nba';")

        # 插入新数据 (包含 AI 分析字段和流动性)
        insert_sql = """
        INSERT INTO daily_matches
            (sport_type, match_id, home_team, away_team, commence_time,
             web2_home_odds, web2_away_odds, source_bookmaker, source_url,
             poly_home_price, poly_away_price, polymarket_url,
             liquidity_home, liquidity_away,
             ai_analysis, analysis_timestamp, last_updated)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
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
            liquidity_home = EXCLUDED.liquidity_home,
            liquidity_away = EXCLUDED.liquidity_away,
            ai_analysis = EXCLUDED.ai_analysis,
            analysis_timestamp = EXCLUDED.analysis_timestamp,
            last_updated = CURRENT_TIMESTAMP
        """

        history_saved = 0
        history_skipped = 0

        for m in matches:
            match_id = m["match_id"]

            # AI analysis is now handled by the separate daily_analysis_job.py cron.
            # Preserve any existing report; do not generate new ones here.
            existing = existing_reports.get(match_id, {})
            ai_analysis = existing.get("analysis")
            analysis_timestamp = existing.get("timestamp")

            cursor.execute(insert_sql, (
                "nba",
                match_id,
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
                m.get("liquidity_home"),
                m.get("liquidity_away"),
                ai_analysis,
                analysis_timestamp,
            ))
            # 保存历史记录 - 智能去重 (完整记录主客场数据)
            # 计算 EV (主队方向)
            home_ev = None
            if m["home_odds"] and m.get("poly_home_price") and m.get("poly_home_price") > 0:
                home_ev = (m["home_odds"] - m.get("poly_home_price")) / m.get("poly_home_price")

            if save_odds_history_daily(
                cursor,
                match_id=match_id,
                sport_type="nba",
                web2_home_odds=m["home_odds"],
                web2_away_odds=m["away_odds"],
                poly_home_price=m.get("poly_home_price"),
                poly_away_price=m.get("poly_away_price"),
                liquidity_home=m.get("liquidity_home"),
                liquidity_away=m.get("liquidity_away"),
                ev=home_ev
            ):
                history_saved += 1
            else:
                history_skipped += 1

        conn.commit()
        print(f"[入库] 成功保存 {len(matches)} 场比赛")
        print(f"[入库] 历史记录: 新增 {history_saved} 条, 跳过 {history_skipped} 条 (无变化)")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"[入库] 数据库错误: {e}")
        return False


# ============================================
# Soccer Daily Matches - 足球每日比赛 (3-way: Home/Draw/Away)
# ============================================

def fetch_soccer_matches_web2(sport_key, sport_name):
    """
    从 TheOddsAPI 获取足球每日比赛 (3-way H2H) 数据
    支持缓存：API 失败时使用缓存数据
    返回: [
        {
            "match_id": str,
            "home_team": str,
            "away_team": str,
            "commence_time": datetime,
            "home_odds": float,   # 去抽水后隐含胜率
            "draw_odds": float,   # 平局隐含胜率
            "away_odds": float,
            "bookmaker": str,
            "bookmaker_url": str,
        },
        ...
    ]
    """
    print(f"\n[Web2] 正在获取 {sport_name} 每日比赛 (3-way H2H) 数据...")

    # 缓存文件路径
    cache_file = os.path.join(CACHE_DIR, f"cache_daily_{sport_key}.json")

    def load_from_cache():
        """从缓存加载数据"""
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                # 转换 commence_time 字符串为 datetime
                matches = []
                for m in cached.get("matches", []):
                    m["commence_time"] = datetime.fromisoformat(m["commence_time"])
                    matches.append(m)
                cache_time = cached.get("cached_at", "unknown")
                print(f"[Web2] 使用缓存数据 (缓存时间: {cache_time})")
                return matches
            except Exception as e:
                print(f"[Web2] 缓存加载失败: {e}")
        return []

    def save_to_cache(matches):
        """保存数据到缓存"""
        try:
            # 转换 datetime 为字符串
            cache_data = []
            for m in matches:
                m_copy = m.copy()
                m_copy["commence_time"] = m["commence_time"].isoformat()
                cache_data.append(m_copy)
            with open(cache_file, 'w') as f:
                json.dump({
                    "matches": cache_data,
                    "cached_at": datetime.now().isoformat(),
                    "sport_key": sport_key,
                    "sport_name": sport_name,
                }, f, indent=2)
            print(f"[Web2] 数据已缓存到 {cache_file}")
        except Exception as e:
            print(f"[Web2] 缓存保存失败: {e}")

    if not ODDS_API_KEY or ODDS_API_KEY == "你的_TheOddsAPI_Key":
        print("[Web2] 警告: ODDS_API_KEY 未设置，尝试使用缓存...")
        return load_from_cache()

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us,uk,eu",
        "markets": "h2h",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }

    try:
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 404:
            print(f"[Web2] {sport_name} 比赛暂无数据，尝试使用缓存...")
            return load_from_cache()

        if response.status_code == 401:
            print(f"[Web2] API 配额已用尽，尝试使用缓存...")
            return load_from_cache()

        response.raise_for_status()
        events = response.json()

        matches = []
        PREFERRED_BOOKMAKERS = {"pinnacle", "bet365", "williamhill", "unibet", "betfair_ex_eu"}

        for event in events:
            match_id = event.get("id")
            home_team = event.get("home_team")
            away_team = event.get("away_team")
            commence_time = event.get("commence_time")

            if not all([match_id, home_team, away_team, commence_time]):
                continue

            # 收集所有 bookmaker 的赔率
            home_odds_list = []
            draw_odds_list = []
            away_odds_list = []

            for bookmaker in event.get("bookmakers", []):
                bk_key = bookmaker.get("key", "")
                bk_title = bookmaker.get("title", bk_key)

                for market in bookmaker.get("markets", []):
                    if market.get("key") != "h2h":
                        continue

                    outcomes = market.get("outcomes", [])
                    home_price = None
                    draw_price = None
                    away_price = None

                    for outcome in outcomes:
                        name = outcome.get("name")
                        price = outcome.get("price")
                        if name == home_team:
                            home_price = price
                        elif name == away_team:
                            away_price = price
                        elif name.lower() == "draw":
                            draw_price = price

                    if home_price and draw_price and away_price:
                        if home_price > 1 and draw_price > 1 and away_price > 1:
                            home_prob = 1 / home_price
                            draw_prob = 1 / draw_price
                            away_prob = 1 / away_price

                            home_odds_list.append({"prob": home_prob, "key": bk_key, "title": bk_title})
                            draw_odds_list.append({"prob": draw_prob, "key": bk_key, "title": bk_title})
                            away_odds_list.append({"prob": away_prob, "key": bk_key, "title": bk_title})

            if not home_odds_list:
                continue

            # 优先使用主流 bookmaker 的平均值
            preferred_home = [o for o in home_odds_list if o["key"] in PREFERRED_BOOKMAKERS]
            preferred_draw = [o for o in draw_odds_list if o["key"] in PREFERRED_BOOKMAKERS]
            preferred_away = [o for o in away_odds_list if o["key"] in PREFERRED_BOOKMAKERS]

            if preferred_home:
                avg_home = sum(o["prob"] for o in preferred_home) / len(preferred_home)
                avg_draw = sum(o["prob"] for o in preferred_draw) / len(preferred_draw)
                avg_away = sum(o["prob"] for o in preferred_away) / len(preferred_away)
                best_bk = preferred_home[0]
            else:
                avg_home = sum(o["prob"] for o in home_odds_list) / len(home_odds_list)
                avg_draw = sum(o["prob"] for o in draw_odds_list) / len(draw_odds_list)
                avg_away = sum(o["prob"] for o in away_odds_list) / len(away_odds_list)
                best_bk = home_odds_list[0]

            # De-vig: 去除博彩公司抽水 (Multiplicative Method)
            # 对于 3-way，home + draw + away 概率总和应为 100%
            total_prob = avg_home + avg_draw + avg_away
            devigged_home = avg_home / total_prob
            devigged_draw = avg_draw / total_prob
            devigged_away = avg_away / total_prob

            bookmaker_url = BOOKMAKER_URLS.get(best_bk["key"], "")
            display_name = BOOKMAKER_DISPLAY_NAMES.get(best_bk["key"], best_bk["title"])

            matches.append({
                "match_id": match_id,
                "home_team": home_team,
                "away_team": away_team,
                "commence_time": datetime.fromisoformat(commence_time.replace("Z", "+00:00")),
                "home_odds": round(devigged_home, 4),
                "draw_odds": round(devigged_draw, 4),
                "away_odds": round(devigged_away, 4),
                "bookmaker": display_name,
                "bookmaker_url": bookmaker_url,
            })

        print(f"[Web2] 获取到 {len(matches)} 场 {sport_name} 比赛")

        # 保存到缓存
        if matches:
            save_to_cache(matches)

        return matches

    except requests.exceptions.RequestException as e:
        print(f"[Web2] API 请求失败: {e}")
        print("[Web2] 尝试使用缓存数据...")
        return load_from_cache()


def fetch_soccer_matches_polymarket(sport_type):
    """
    从 Polymarket 获取足球每日比赛数据

    Polymarket 足球市场结构 (3个独立的 Yes/No 市场):
    - "Will [Team1] win on [date]?" → Yes price = Team1 win probability
    - "Will [Team2] win on [date]?" → Yes price = Team2 win probability
    - "Will [Team1] vs. [Team2] end in a draw?" → Yes price = Draw probability
    """
    tag_map = {
        "epl": "premier-league",
        "ucl": "ucl",
    }
    tag_slug = tag_map.get(sport_type, "soccer")

    print(f"\n[Polymarket] 正在获取 {sport_type.upper()} 每日比赛数据...")

    try:
        url = f"https://gamma-api.polymarket.com/events?tag_slug={tag_slug}&active=true&closed=false&limit=100"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        events = response.json()

        matches = []
        now = datetime.utcnow()
        vs_pattern = re.compile(r"^(.+?)\s+(?:vs\.?|v)\s+(.+?)$", re.IGNORECASE)

        # 用于解析 "Will [Team] win" 问题的正则
        team_win_pattern = re.compile(r"Will\s+(.+?)\s+win\s+on", re.IGNORECASE)
        draw_pattern = re.compile(r"end in a draw", re.IGNORECASE)

        for event in events:
            title = event.get("title", "")
            end_date_str = event.get("endDate")

            # 跳过冠军预测等非每日比赛
            if "winner" in title.lower() or "champion" in title.lower():
                continue

            # 尝试解析 "Team1 vs Team2" 格式
            match = vs_pattern.match(title)
            if not match:
                continue

            team1_raw = match.group(1).strip()
            team2_raw = match.group(2).strip()

            # 去除 "FC" 后缀进行更好的匹配
            team1_clean = re.sub(r'\s*(FC|AFC|CF)$', '', team1_raw, flags=re.IGNORECASE).strip()
            team2_clean = re.sub(r'\s*(FC|AFC|CF)$', '', team2_raw, flags=re.IGNORECASE).strip()

            # 解析结束时间
            end_time = None
            if end_date_str:
                try:
                    end_time = datetime.fromisoformat(end_date_str.replace("Z", "+00:00").replace("+00:00", ""))
                    if end_time < now:
                        continue
                except:
                    pass

            # 获取市场详情 - Polymarket 使用 3 个独立的 Yes/No 市场
            event_markets = event.get("markets", [])

            home_price = None
            draw_price = None
            away_price = None
            home_liq = None
            draw_liq = None
            away_liq = None
            poly_url = f"https://polymarket.com/event/{event.get('slug', '')}"

            for market in event_markets:
                question = market.get("question", "")
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

                # 找到 "Yes" 的价格 (通常是第一个 outcome)
                yes_price = None
                for i, outcome in enumerate(outcomes):
                    if outcome.lower() == "yes":
                        yes_price = float(outcome_prices[i]) if i < len(outcome_prices) else None
                        break

                if yes_price is None:
                    continue

                # 获取该市场的流动性
                market_liq = market.get("liquidityNum") or market.get("liquidity")
                if market_liq:
                    try:
                        market_liq = float(market_liq)
                    except:
                        market_liq = None

                # 检查是否是 "Draw" 市场
                if draw_pattern.search(question):
                    draw_price = yes_price
                    draw_liq = market_liq
                    continue

                # 检查是否是 "Will [Team] win" 市场
                team_match = team_win_pattern.search(question)
                if team_match:
                    team_in_question = team_match.group(1).strip()
                    team_in_question_clean = re.sub(r'\s*(FC|AFC|CF)$', '', team_in_question, flags=re.IGNORECASE).strip()

                    # 匹配 Team1 (Home)
                    if (team_in_question_clean.lower() == team1_clean.lower() or
                        team_in_question.lower() == team1_raw.lower() or
                        fuzz.ratio(team_in_question_clean.lower(), team1_clean.lower()) > 85):
                        home_price = yes_price
                        home_liq = market_liq
                    # 匹配 Team2 (Away)
                    elif (team_in_question_clean.lower() == team2_clean.lower() or
                          team_in_question.lower() == team2_raw.lower() or
                          fuzz.ratio(team_in_question_clean.lower(), team2_clean.lower()) > 85):
                        away_price = yes_price
                        away_liq = market_liq

            # 过滤已结束的比赛 - 只有当某队价格接近 99% 时才跳过
            # 有些比赛是真实的悬殊对决（如强队 vs 弱队，Arsenal 95% vs Qairat 1.5%）
            if home_price is not None and home_price > 0.99:
                continue
            if away_price is not None and away_price > 0.99:
                continue

            if home_price is None and away_price is None:
                continue

            # 使用原始队名（带FC后缀），便于后续匹配
            matches.append({
                "home_team": team1_raw,
                "away_team": team2_raw,
                "home_price": home_price,
                "draw_price": draw_price,
                "away_price": away_price,
                "home_liq": home_liq,
                "draw_liq": draw_liq,
                "away_liq": away_liq,
                "url": poly_url,
                "end_time": end_time,  # 比赛结束时间
            })

            home_pct = f"{home_price*100:.1f}%" if home_price else "-"
            draw_pct = f"{draw_price*100:.1f}%" if draw_price else "-"
            away_pct = f"{away_price*100:.1f}%" if away_price else "-"
            print(f"[Polymarket] 找到比赛: {team1_raw} vs {team2_raw} ({home_pct} / {draw_pct} / {away_pct})")

        print(f"[Polymarket] 获取到 {len(matches)} 场 {sport_type.upper()} 比赛市场")
        return matches

    except Exception as e:
        print(f"[Polymarket] 获取失败: {e}")
        return []


def match_soccer_games(web2_matches, poly_matches):
    """
    匹配 Web2 和 Polymarket 的足球比赛数据

    匹配策略:
    1. 首先应用严格字典映射 (SOCCER_TEAM_MAPPING)
    2. 然后使用模糊匹配作为后备
    3. 添加 Polymarket 独有的比赛 (Web2 没有的)
    """
    print("\n[匹配] 正在匹配 Web2 和 Polymarket 的足球比赛...")

    merged = []
    matched_poly_indices = set()  # 记录已匹配的 Polymarket 比赛索引

    for web2_match in web2_matches:
        home_team = web2_match["home_team"]
        away_team = web2_match["away_team"]

        # 先进行严格映射规范化
        home_normalized = normalize_team_for_matching(home_team)
        away_normalized = normalize_team_for_matching(away_team)

        # 在 Polymarket 中寻找匹配
        poly_match = None
        matched_idx = None
        for idx, pm in enumerate(poly_matches):
            pm_home = normalize_team_for_matching(pm["home_team"])
            pm_away = normalize_team_for_matching(pm["away_team"])

            # 正向匹配 - 先尝试严格映射后的名称
            if (pm_home.lower() == home_normalized.lower() and
                pm_away.lower() == away_normalized.lower()):
                poly_match = pm
                matched_idx = idx
                print(f"[匹配] 严格映射成功: {home_team} vs {away_team}")
                break

            # 反向匹配 - 先尝试严格映射后的名称
            if (pm_home.lower() == away_normalized.lower() and
                pm_away.lower() == home_normalized.lower()):
                poly_match = {
                    "home_team": pm["away_team"],
                    "away_team": pm["home_team"],
                    "home_price": pm["away_price"],
                    "draw_price": pm["draw_price"],
                    "away_price": pm["home_price"],
                    "home_liq": pm.get("away_liq"),
                    "draw_liq": pm.get("draw_liq"),
                    "away_liq": pm.get("home_liq"),
                    "url": pm.get("url"),
                }
                matched_idx = idx
                print(f"[匹配] 严格映射成功 (反向): {home_team} vs {away_team}")
                break

        # 如果严格映射失败，尝试模糊匹配
        if not poly_match:
            for idx, pm in enumerate(poly_matches):
                # 正向模糊匹配
                if (fuzzy_match_soccer_team(pm["home_team"])[0] == fuzzy_match_soccer_team(home_team)[0] and
                    fuzzy_match_soccer_team(pm["away_team"])[0] == fuzzy_match_soccer_team(away_team)[0]):
                    poly_match = pm
                    matched_idx = idx
                    print(f"[匹配] 模糊匹配成功: {home_team} vs {away_team}")
                    break
                # 反向模糊匹配
                if (fuzzy_match_soccer_team(pm["home_team"])[0] == fuzzy_match_soccer_team(away_team)[0] and
                    fuzzy_match_soccer_team(pm["away_team"])[0] == fuzzy_match_soccer_team(home_team)[0]):
                    poly_match = {
                        "home_team": pm["away_team"],
                        "away_team": pm["home_team"],
                        "home_price": pm["away_price"],
                        "draw_price": pm["draw_price"],
                        "away_price": pm["home_price"],
                        "home_liq": pm.get("away_liq"),
                        "draw_liq": pm.get("draw_liq"),
                        "away_liq": pm.get("home_liq"),
                        "url": pm.get("url"),
                    }
                    matched_idx = idx
                    print(f"[匹配] 模糊匹配成功 (反向): {home_team} vs {away_team}")
                    break

        if matched_idx is not None:
            matched_poly_indices.add(matched_idx)

        merged.append({
            **web2_match,
            "poly_home_price": poly_match["home_price"] if poly_match else None,
            "poly_draw_price": poly_match["draw_price"] if poly_match else None,
            "poly_away_price": poly_match["away_price"] if poly_match else None,
            "polymarket_url": poly_match["url"] if poly_match else None,
            "liquidity_home": poly_match.get("home_liq") if poly_match else None,
            "liquidity_draw": poly_match.get("draw_liq") if poly_match else None,
            "liquidity_away": poly_match.get("away_liq") if poly_match else None,
        })

    matched_count = sum(1 for m in merged if m.get("poly_home_price"))
    print(f"[匹配] Web2 比赛匹配完成: {len(merged)} 场, 成功匹配 Polymarket: {matched_count} 场")

    # ============================================
    # 新增：添加 Polymarket 独有的比赛
    # ============================================
    poly_only_count = 0
    print(f"\n[Polymarket 独有] 正在添加 Polymarket 独有的足球比赛...")

    for idx, pm in enumerate(poly_matches):
        if idx in matched_poly_indices:
            continue  # 跳过已匹配的

        # 只添加有价格的比赛
        if pm.get("home_price") is None or pm.get("away_price") is None:
            continue

        # 去除 FC 后缀，获取干净的队名
        home_clean = re.sub(r'\s*(FC|AFC|CF)$', '', pm["home_team"], flags=re.IGNORECASE).strip()
        away_clean = re.sub(r'\s*(FC|AFC|CF)$', '', pm["away_team"], flags=re.IGNORECASE).strip()

        # 创建 Polymarket-only 记录
        match_id = f"poly_soccer_{idx}"

        # 使用 Polymarket 的 end_time 作为比赛时间，如果没有则用当前时间
        match_time = pm.get("end_time") or datetime.utcnow()

        merged.append({
            "match_id": match_id,
            "home_team": home_clean,
            "away_team": away_clean,
            "commence_time": match_time,
            "web2_home_odds": None,
            "web2_away_odds": None,
            "web2_draw_odds": None,
            "source_bookmaker": None,
            "source_url": None,
            "poly_home_price": pm["home_price"],
            "poly_draw_price": pm.get("draw_price"),
            "poly_away_price": pm["away_price"],
            "polymarket_url": pm.get("url"),
            "liquidity_home": pm.get("home_liq"),
            "liquidity_draw": pm.get("draw_liq"),
            "liquidity_away": pm.get("away_liq"),
        })
        poly_only_count += 1
        home_pct = f"{pm['home_price']*100:.1f}%" if pm['home_price'] else "-"
        draw_pct = f"{pm.get('draw_price', 0)*100:.1f}%" if pm.get('draw_price') else "-"
        away_pct = f"{pm['away_price']*100:.1f}%" if pm['away_price'] else "-"
        print(f"[Polymarket 独有] 添加: {home_clean} vs {away_clean} ({home_pct} / {draw_pct} / {away_pct})")

    print(f"[Polymarket 独有] 添加了 {poly_only_count} 场足球比赛")
    print(f"\n[匹配] 最终合计: {len(merged)} 场比赛")

    return merged


def save_soccer_matches(matches, sport_type):
    """
    保存足球每日比赛到数据库 (支持 3-way)
    保留旧 Polymarket 数据：当新抓取没有 Poly 数据但旧记录有时，保留旧数据
    """
    if not matches:
        print("[入库] 无足球比赛数据需要保存")
        return False

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # 先获取现有的 Polymarket 数据，用于在新数据缺失时保留
        cursor.execute("""
            SELECT match_id, poly_home_price, poly_away_price, poly_draw_price,
                   polymarket_url, liquidity_home, liquidity_away, liquidity_draw
            FROM daily_matches
            WHERE sport_type = %s AND poly_home_price IS NOT NULL
        """, (sport_type,))
        existing_poly = {}
        for row in cursor.fetchall():
            existing_poly[row[0]] = {
                "poly_home_price": row[1],
                "poly_away_price": row[2],
                "poly_draw_price": row[3],
                "polymarket_url": row[4],
                "liquidity_home": row[5],
                "liquidity_away": row[6],
                "liquidity_draw": row[7],
            }

        # 对新数据中缺少 Polymarket 数据的比赛，从旧数据恢复
        preserved_count = 0
        for match in matches:
            mid = match["match_id"]
            if mid in existing_poly and not match.get("poly_home_price"):
                old = existing_poly[mid]
                match["poly_home_price"] = old["poly_home_price"]
                match["poly_away_price"] = old["poly_away_price"]
                match["poly_draw_price"] = old["poly_draw_price"]
                match["polymarket_url"] = old["polymarket_url"]
                match["liquidity_home"] = old["liquidity_home"]
                match["liquidity_away"] = old["liquidity_away"]
                match["liquidity_draw"] = old["liquidity_draw"]
                preserved_count += 1

        if preserved_count:
            print(f"[入库] 保留了 {preserved_count} 场比赛的 Polymarket 历史数据")

        # 删除该赛事旧数据
        cursor.execute("DELETE FROM daily_matches WHERE sport_type = %s", (sport_type,))

        insert_sql = """
        INSERT INTO daily_matches
            (sport_type, match_id, home_team, away_team, commence_time,
             web2_home_odds, web2_away_odds, web2_draw_odds,
             source_bookmaker, source_url,
             poly_home_price, poly_away_price, poly_draw_price,
             polymarket_url,
             liquidity_home, liquidity_away, liquidity_draw,
             last_updated)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """

        history_saved = 0
        history_skipped = 0

        for match in matches:
            cursor.execute(insert_sql, (
                sport_type,
                match["match_id"],
                match["home_team"],
                match["away_team"],
                match["commence_time"],
                match.get("home_odds"),
                match.get("away_odds"),
                match.get("draw_odds"),
                match.get("bookmaker"),
                match.get("bookmaker_url"),
                match.get("poly_home_price"),
                match.get("poly_away_price"),
                match.get("poly_draw_price"),
                match.get("polymarket_url"),
                match.get("liquidity_home"),
                match.get("liquidity_away"),
                match.get("liquidity_draw"),
            ))

            # 保存历史记录（智能去重，支持3-way）
            if save_odds_history_daily(
                cursor,
                match_id=match["match_id"],
                sport_type=sport_type,
                web2_home_odds=match.get("home_odds"),
                web2_away_odds=match.get("away_odds"),
                poly_home_price=match.get("poly_home_price"),
                poly_away_price=match.get("poly_away_price"),
                liquidity_home=match.get("liquidity_home"),
                liquidity_away=match.get("liquidity_away"),
                web2_draw_odds=match.get("draw_odds"),
                poly_draw_price=match.get("poly_draw_price"),
                liquidity_draw=match.get("liquidity_draw"),
            ):
                history_saved += 1
            else:
                history_skipped += 1

        conn.commit()
        print(f"[入库] 成功保存 {len(matches)} 场 {sport_type.upper()} 比赛")
        print(f"[入库] 历史记录: 新增 {history_saved} 条, 跳过 {history_skipped} 条 (无变化)")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"[入库] 数据库错误: {e}")
        return False


def fetch_and_save_soccer_matches(sport_type):
    """
    主函数：获取并保存足球每日比赛数据 (EPL/UCL)
    """
    config = DAILY_SPORTS_CONFIG.get(sport_type)
    if not config:
        print(f"[Soccer] 未知赛事类型: {sport_type}")
        return []

    print("\n" + "=" * 60)
    print(f"正在处理: {config['name']} 每日比赛 (3-way H2H)")
    print("=" * 60)

    # 1. 获取 Web2 数据
    web2_matches = fetch_soccer_matches_web2(config["web2_key"], config["name"])

    # 2. 获取 Polymarket 数据
    poly_matches = fetch_soccer_matches_polymarket(sport_type)

    # 3. 匹配并合并
    merged = match_soccer_games(web2_matches, poly_matches)

    # 4. 保存到数据库
    save_soccer_matches(merged, sport_type)

    return merged


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
            "liquidity_usdc": poly_info.get("liquidity") if isinstance(poly_info, dict) else None,
            # Kalshi 数据
            "kalshi_price": kalshi_info.get("price") if isinstance(kalshi_info, dict) else None,
            "kalshi_url": kalshi_info.get("url") if isinstance(kalshi_info, dict) else None,
        }
        merged_data.append(record)

    print(f"[合并] {sport_type}: {len(merged_data)} 支队伍待入库")
    return merged_data


def _check_value_changed(new_val, old_val, threshold):
    """检查单个值是否发生显著变化"""
    if new_val is not None and old_val is not None:
        return abs(new_val - old_val) >= threshold
    elif new_val is not None or old_val is not None:
        return True  # 从 None 变为有值，或反之
    return False


def save_odds_history_championship(cursor, event_id, sport_type, web2_odds, polymarket_price,
                                    liquidity_usdc=None, ev=None, threshold=0.005):
    """
    保存冠军盘口历史记录（智能去重）

    Returns:
        bool: True 表示插入了新记录，False 表示跳过
    """
    # 查询最新记录
    cursor.execute("""
        SELECT web2_odds, polymarket_price, liquidity_usdc, ev
        FROM odds_history
        WHERE event_type = 'championship' AND event_id = %s
        ORDER BY recorded_at DESC LIMIT 1
    """, (event_id,))
    last = cursor.fetchone()

    if last:
        last_web2, last_poly, last_liq, last_ev = last
        # 检查是否有显著变化
        if not any([
            _check_value_changed(web2_odds, last_web2, threshold),
            _check_value_changed(polymarket_price, last_poly, threshold),
            _check_value_changed(liquidity_usdc, last_liq, 1.0),  # 流动性变化 >= $1
            _check_value_changed(ev, last_ev, threshold),
        ]):
            return False

    cursor.execute("""
        INSERT INTO odds_history
            (event_type, event_id, sport_type, web2_odds, polymarket_price,
             liquidity_usdc, ev, recorded_at)
        VALUES ('championship', %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
    """, (event_id, sport_type, web2_odds, polymarket_price, liquidity_usdc, ev))
    return True


def save_odds_history_daily(cursor, match_id, sport_type,
                            web2_home_odds, web2_away_odds,
                            poly_home_price, poly_away_price,
                            liquidity_home=None, liquidity_away=None,
                            web2_draw_odds=None, poly_draw_price=None, liquidity_draw=None,
                            ev=None, threshold=0.005):
    """
    保存每日比赛历史记录（智能去重，支持足球3-way）

    Returns:
        bool: True 表示插入了新记录，False 表示跳过
    """
    # 查询最新记录
    cursor.execute("""
        SELECT web2_home_odds, web2_away_odds, poly_home_price, poly_away_price,
               liquidity_home, liquidity_away, web2_draw_odds, poly_draw_price, liquidity_draw, ev
        FROM odds_history
        WHERE event_type = 'daily' AND event_id = %s
        ORDER BY recorded_at DESC LIMIT 1
    """, (match_id,))
    last = cursor.fetchone()

    if last:
        (last_w2h, last_w2a, last_ph, last_pa, last_lh, last_la, last_w2d, last_pd, last_ld, last_ev) = last
        # 检查是否有显著变化
        if not any([
            _check_value_changed(web2_home_odds, last_w2h, threshold),
            _check_value_changed(web2_away_odds, last_w2a, threshold),
            _check_value_changed(poly_home_price, last_ph, threshold),
            _check_value_changed(poly_away_price, last_pa, threshold),
            _check_value_changed(liquidity_home, last_lh, 1.0),
            _check_value_changed(liquidity_away, last_la, 1.0),
            _check_value_changed(web2_draw_odds, last_w2d, threshold),
            _check_value_changed(poly_draw_price, last_pd, threshold),
            _check_value_changed(liquidity_draw, last_ld, 1.0),
            _check_value_changed(ev, last_ev, threshold),
        ]):
            return False

    cursor.execute("""
        INSERT INTO odds_history
            (event_type, event_id, sport_type,
             web2_home_odds, web2_away_odds, poly_home_price, poly_away_price,
             liquidity_home, liquidity_away,
             web2_draw_odds, poly_draw_price, liquidity_draw,
             ev, recorded_at)
        VALUES ('daily', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
    """, (match_id, sport_type, web2_home_odds, web2_away_odds,
          poly_home_price, poly_away_price, liquidity_home, liquidity_away,
          web2_draw_odds, poly_draw_price, liquidity_draw, ev))
    return True


def save_to_database(all_data):
    """
    将所有赛事数据写入 PostgreSQL 数据库
    包含 AI 分析报告生成 (使用 OpenRouter)
    """
    print("\n" + "=" * 60)
    print("[入库] 正在写入数据库...")

    if not DATABASE_URL:
        print("[入库] 错误: DATABASE_URL 未设置")
        return False

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # ============================================
        # 步骤 1: 获取现有的 AI 分析报告 (用于频次控制)
        # ============================================
        cursor.execute("""
            SELECT team_name, ai_analysis, analysis_timestamp
            FROM market_odds
            WHERE ai_analysis IS NOT NULL
        """)
        existing_reports = {}
        for row in cursor.fetchall():
            existing_reports[row[0]] = {
                "analysis": row[1],
                "timestamp": row[2]
            }
        print(f"[入库] 获取到 {len(existing_reports)} 条现有 AI 报告")

        # 清空现有数据
        cursor.execute("TRUNCATE TABLE market_odds RESTART IDENTITY;")

        # 插入新数据（包含 AI 分析字段、流动性、prop_type 和 event_id）
        insert_sql = """
        INSERT INTO market_odds
            (sport_type, team_name, web2_odds, source_bookmaker, source_url,
             polymarket_price, polymarket_url, kalshi_price, kalshi_url,
             liquidity_usdc, ai_analysis, analysis_timestamp, prop_type, event_id, last_updated)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """

        history_saved = 0
        history_skipped = 0

        for record in all_data:
            team_name = record["team_name"]
            web2_odds = record["web2_odds"]
            poly_price = record["polymarket_price"]

            # EV calculation (kept for history tracking)
            ev = 0
            if web2_odds and poly_price and poly_price > 0:
                ev = (web2_odds - poly_price) / poly_price

            # AI analysis is now handled by the separate daily_analysis_job.py cron.
            # Preserve any existing report; do not generate new ones here.
            existing = existing_reports.get(team_name, {})
            ai_analysis = existing.get("analysis")
            analysis_timestamp = existing.get("timestamp")

            cursor.execute(insert_sql, (
                record["sport_type"],
                record["team_name"],
                record["web2_odds"],
                record["source_bookmaker"],
                record["source_url"],
                record["polymarket_price"],
                record["polymarket_url"],
                record["kalshi_price"],
                record["kalshi_url"],
                record.get("liquidity_usdc"),
                ai_analysis,
                analysis_timestamp,
                record.get("prop_type", "championship"),
                record.get("event_id")
            ))
            # 保存历史记录 - 智能去重 (含流动性和 EV)
            if save_odds_history_championship(
                cursor,
                event_id=record["team_name"],
                sport_type=record["sport_type"],
                web2_odds=record["web2_odds"],
                polymarket_price=record["polymarket_price"],
                liquidity_usdc=record.get("liquidity_usdc"),
                ev=ev
            ):
                history_saved += 1
            else:
                history_skipped += 1

        conn.commit()
        print(f"[入库] 历史记录: 新增 {history_saved} 条, 跳过 {history_skipped} 条 (无变化)")
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


def save_fifa_qualification_markets():
    """
    获取并保存 FIFA World Cup 2026 出线预测市场
    """
    print("\n" + "=" * 60)
    print("[FIFA Props] 正在处理出线预测市场...")
    print("=" * 60)

    # 获取出线预测数据
    qualification_data = fetch_fifa_qualification_markets()

    if not qualification_data:
        print("[FIFA Props] 未获取到出线预测数据")
        return 0

    if not DATABASE_URL:
        print("[FIFA Props] 错误: DATABASE_URL 未设置")
        return 0

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # 插入出线预测数据
        insert_sql = """
        INSERT INTO market_odds
            (sport_type, team_name, polymarket_price, polymarket_url,
             liquidity_usdc, prop_type, event_id, last_updated)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """

        saved_count = 0
        for country, data in qualification_data.items():
            cursor.execute(insert_sql, (
                "world_cup",  # sport_type
                country,      # team_name
                data["price"],
                data["url"],
                data.get("liquidity"),
                "qualification",  # prop_type
                "26313"  # event_id for FIFA qualification event
            ))
            saved_count += 1

        conn.commit()
        print(f"[FIFA Props] 成功保存 {saved_count} 个国家的出线预测数据")

        # 显示预览
        cursor.execute("""
            SELECT team_name, polymarket_price, liquidity_usdc
            FROM market_odds
            WHERE prop_type = 'qualification'
            ORDER BY polymarket_price DESC
            LIMIT 10
        """)

        print("\n出线概率 Top 10:")
        print("-" * 60)
        print(f"{'国家':<25} {'出线概率':<15} {'流动性 (USDC)':<15}")
        print("-" * 60)
        for row in cursor.fetchall():
            prob = f"{row[1]:.1%}" if row[1] else "N/A"
            liq = f"${row[2]:.0f}" if row[2] else "N/A"
            print(f"{row[0]:<25} {prob:<15} {liq:<15}")
        print("-" * 60)

        cursor.close()
        conn.close()
        return saved_count

    except psycopg2.Error as e:
        print(f"[FIFA Props] 数据库错误: {e}")
        return 0


# ============================================
# 主函数
# ============================================
def main():
    """主函数：抓取所有赛事的数据并合并入库"""
    print("=" * 60)
    print("PolyDelta - 多平台多赛事数据抓取脚本")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("支持赛事: World Cup, EPL, UCL, NBA")
    print("数据源: Web2 (TheOddsAPI), Polymarket")
    print("功能: 冠军盘口 (Outrights) + 每日比赛 (H2H/3-way)")
    print("Kalshi: 已禁用 (网络限制)")
    print("=" * 60)

    # ============================================
    # 优先获取每日比赛 (API 配额优先给 daily 数据)
    # ============================================

    # 1. 获取 NBA 每日比赛 (H2H)
    daily_matches_nba = fetch_and_save_nba_matches()

    # 2. 获取足球每日比赛 (3-way H2H)
    daily_matches_epl = fetch_and_save_soccer_matches("epl")
    daily_matches_ucl = fetch_and_save_soccer_matches("ucl")

    # ============================================
    # 然后获取冠军盘口 (有缓存兜底，配额不够也没关系)
    # ============================================

    all_data = []
    stats = {}

    for sport_type in SPORTS_CONFIG.keys():
        print(f"\n{'='*60}")
        print(f"正在处理: {SPORTS_CONFIG[sport_type]['name']}")
        print("=" * 60)

        # 获取 Web2 数据
        web2_data = fetch_web2_odds(sport_type)

        # 获取 Polymarket 数据
        poly_data = fetch_polymarket_data(sport_type)

        # 获取 Kalshi 数据 (已禁用，返回空)
        kalshi_data = fetch_kalshi_data(sport_type)

        # 合并数据
        merged = merge_and_save_data(sport_type, web2_data, poly_data, kalshi_data)
        all_data.extend(merged)

        # 记录统计
        stats[sport_type] = {
            "web2": len(web2_data),
            "poly": len(poly_data),
            "kalshi": len(kalshi_data),
            "merged": len(merged)
        }

    # 统一入库 (冠军盘口)
    save_to_database(all_data)

    # 获取 FIFA 出线预测市场 (Props)
    fifa_qualification_count = save_fifa_qualification_markets()

    # 最终统计
    print("\n" + "=" * 60)
    print("抓取完成！最终统计:")
    print("=" * 60)
    print("\n[冠军盘口 Outrights]")
    for sport, s in stats.items():
        print(f"  {sport}: Web2={s['web2']}, Poly={s['poly']}, 合并={s['merged']}")
    print(f"  总计: {len(all_data)} 条记录")
    print(f"\n[FIFA Props]")
    print(f"  出线预测: {fifa_qualification_count} 个国家")
    print(f"\n[每日比赛 H2H]")
    print(f"  NBA: {len(daily_matches_nba)} 场比赛")
    nba_matched = sum(1 for m in daily_matches_nba if m.get("poly_home_price"))
    print(f"    Polymarket 匹配: {nba_matched} 场")
    print(f"  EPL: {len(daily_matches_epl)} 场比赛")
    epl_matched = sum(1 for m in daily_matches_epl if m.get("poly_home_price"))
    print(f"    Polymarket 匹配: {epl_matched} 场")
    print(f"  UCL: {len(daily_matches_ucl)} 场比赛")
    ucl_matched = sum(1 for m in daily_matches_ucl if m.get("poly_home_price"))
    print(f"    Polymarket 匹配: {ucl_matched} 场")
    print("=" * 60)


if __name__ == '__main__':
    main()
