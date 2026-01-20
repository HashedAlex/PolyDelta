"""
PolyDelta - NBA 市场数据诊断脚本
用于诊断 TheOddsAPI 返回的 NBA 市场数据，找出"病根"
"""
import os
import requests
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
ODDS_API_KEY = os.getenv('ODDS_API_KEY')

def main():
    print("=" * 80)
    print("TheOddsAPI NBA 市场数据诊断")
    print("=" * 80)

    if not ODDS_API_KEY:
        print("错误: ODDS_API_KEY 未设置")
        return

    # ============================================
    # 测试 1: 列出所有可用的 NBA 相关 sports
    # ============================================
    print("\n[1] 列出所有可用的 Sports (筛选 NBA)...")
    print("-" * 80)

    url = "https://api.the-odds-api.com/v4/sports"
    params = {"apiKey": ODDS_API_KEY}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        sports = response.json()

        nba_sports = [s for s in sports if 'nba' in s.get('key', '').lower() or 'nba' in s.get('title', '').lower()]

        print(f"找到 {len(nba_sports)} 个 NBA 相关的 Sport Keys:\n")
        for s in nba_sports:
            active = "✅ Active" if s.get('active') else "❌ Inactive"
            print(f"  Key: {s.get('key')}")
            print(f"  Title: {s.get('title')}")
            print(f"  Status: {active}")
            print()

    except requests.exceptions.RequestException as e:
        print(f"API 请求失败: {e}")

    # ============================================
    # 测试 2: 获取 championship_winner 数据
    # ============================================
    print("\n[2] 获取 basketball_nba_championship_winner 数据...")
    print("-" * 80)

    url = "https://api.the-odds-api.com/v4/sports/basketball_nba_championship_winner/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us,uk,eu",
        "markets": "outrights",
        "oddsFormat": "decimal"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        print(f"返回 {len(data)} 个 Event(s)\n")

        for event_idx, event in enumerate(data):
            print(f"Event #{event_idx + 1}:")
            print(f"  ID: {event.get('id')}")
            print(f"  Sport Key: {event.get('sport_key')}")
            print(f"  Sport Title: {event.get('sport_title')}")
            print()

            bookmakers = event.get('bookmakers', [])
            print(f"  Bookmakers: {len(bookmakers)}")
            print()

            # 分析每个 bookmaker 的 markets
            for bk in bookmakers[:3]:  # 只显示前3个 bookmaker
                bk_title = bk.get('title', 'Unknown')
                markets = bk.get('markets', [])

                print(f"  📚 Bookmaker: {bk_title}")

                for market in markets:
                    market_key = market.get('key', 'unknown')
                    outcomes = market.get('outcomes', [])

                    print(f"     Market Key: {market_key}")
                    print(f"     Outcomes ({len(outcomes)} teams):")

                    # 显示前5个和包含特定关键词的
                    shown = 0
                    for outcome in outcomes:
                        name = outcome.get('name', '')
                        price = outcome.get('price', 0)
                        implied_prob = (1 / price * 100) if price > 1 else 0

                        # 显示前5个或者特定球队
                        if shown < 5 or any(k in name.lower() for k in ['thunder', 'pistons', 'celtics']):
                            marker = "⚠️ " if implied_prob > 40 else ""
                            print(f"       {marker}{name}: {price:.2f} ({implied_prob:.1f}%)")
                            shown += 1

                    if len(outcomes) > shown:
                        print(f"       ... and {len(outcomes) - shown} more teams")
                    print()

    except requests.exceptions.RequestException as e:
        print(f"API 请求失败: {e}")

    # ============================================
    # 测试 3: 直接获取 basketball_nba H2H 数据
    # ============================================
    print("\n[3] 获取 basketball_nba (常规比赛) 数据对比...")
    print("-" * 80)

    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        print(f"返回 {len(data)} 场常规比赛")

        # 检查是否有 Thunder 相关的比赛
        for event in data[:3]:
            home = event.get('home_team', '')
            away = event.get('away_team', '')
            print(f"  {home} vs {away}")

    except requests.exceptions.RequestException as e:
        print(f"API 请求失败: {e}")

    # ============================================
    # 测试 4: 检查缓存文件
    # ============================================
    print("\n[4] 检查本地缓存文件...")
    print("-" * 80)

    cache_file = os.path.join(os.path.dirname(__file__), 'cache_nba.json')

    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cache = json.load(f)

        timestamp = cache.get('timestamp', 'Unknown')
        data = cache.get('data', [])

        print(f"缓存时间: {timestamp}")
        print(f"Events 数量: {len(data)}")

        for event in data:
            sport_key = event.get('sport_key')
            sport_title = event.get('sport_title')
            print(f"\n  Sport Key: {sport_key}")
            print(f"  Sport Title: {sport_title}")

            # 找到 Thunder 的赔率
            for bk in event.get('bookmakers', []):
                for market in bk.get('markets', []):
                    for outcome in market.get('outcomes', []):
                        if 'thunder' in outcome.get('name', '').lower():
                            price = outcome.get('price', 0)
                            prob = (1 / price * 100) if price > 1 else 0
                            print(f"\n  ⚡ Thunder 数据 (from {bk.get('title')}):")
                            print(f"     Market Key: {market.get('key')}")
                            print(f"     Price: {price:.2f}")
                            print(f"     Implied Prob: {prob:.1f}%")
                            break
    else:
        print("缓存文件不存在")

    print("\n" + "=" * 80)
    print("诊断完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
