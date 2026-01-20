"""
PolyDelta - NBA 市场名称调试脚本
用于调查 Polymarket 上 NBA 比赛的实际命名格式
"""
import requests
import json

def main():
    print("=" * 70)
    print("Polymarket NBA 市场调试")
    print("=" * 70)

    # 方法1: 使用 tag_slug=nba 查询 events
    print("\n[1] 使用 tag_slug=nba 查询 events...")
    url = "https://gamma-api.polymarket.com/events"
    params = {
        "limit": 50,
        "active": "true",
        "closed": "false",
        "tag_slug": "nba",
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        events = response.json()

        print(f"找到 {len(events)} 个 NBA events\n")

        # 打印所有 events
        print("-" * 70)
        print("所有 NBA Events:")
        print("-" * 70)
        for i, event in enumerate(events[:20]):
            title = event.get("title", "N/A")
            event_id = event.get("id", "N/A")
            slug = event.get("slug", "N/A")
            print(f"{i+1:2}. {title}")
            print(f"    ID: {event_id}")
            print(f"    Slug: {slug}")
            print()

        # 筛选带 "vs" 的比赛盘口
        print("-" * 70)
        print("带 'vs' 的比赛盘口:")
        print("-" * 70)
        vs_events = [e for e in events if "vs" in e.get("title", "").lower()]
        if vs_events:
            for i, event in enumerate(vs_events[:20]):
                title = event.get("title", "N/A")
                event_id = event.get("id", "N/A")
                print(f"{i+1:2}. {title} (ID: {event_id})")
        else:
            print("没有找到带 'vs' 的比赛盘口")

    except requests.exceptions.RequestException as e:
        print(f"Events API 请求失败: {e}")

    # 方法2: 使用 markets API 查询
    print("\n" + "=" * 70)
    print("[2] 使用 markets API 查询 NBA 关键词...")
    print("=" * 70)

    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": 100,
        "closed": "false",
    }

    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        markets = response.json()

        # 筛选 NBA 相关市场
        nba_markets = []
        for market in markets:
            question = market.get("question", "")
            if "nba" in question.lower():
                nba_markets.append(market)

        print(f"找到 {len(nba_markets)} 个 NBA 相关 markets\n")

        # 打印所有 NBA markets
        print("-" * 70)
        print("NBA Markets (前 20 个):")
        print("-" * 70)
        for i, market in enumerate(nba_markets[:20]):
            question = market.get("question", "N/A")
            slug = market.get("slug", "N/A")
            outcomes = market.get("outcomes", [])
            print(f"{i+1:2}. {question}")
            print(f"    Slug: {slug}")
            print(f"    Outcomes: {outcomes}")
            print()

        # 筛选带 "vs" 的比赛
        print("-" * 70)
        print("带 'vs' 的 NBA Markets:")
        print("-" * 70)
        vs_markets = [m for m in nba_markets if "vs" in m.get("question", "").lower()]
        if vs_markets:
            for i, market in enumerate(vs_markets[:20]):
                question = market.get("question", "N/A")
                print(f"{i+1:2}. {question}")
        else:
            print("没有找到带 'vs' 的 NBA 比赛市场")

    except requests.exceptions.RequestException as e:
        print(f"Markets API 请求失败: {e}")

    # 方法3: 搜索其他可能的比赛格式
    print("\n" + "=" * 70)
    print("[3] 搜索其他可能的 NBA 比赛格式...")
    print("=" * 70)

    # 搜索包含球队名的市场
    team_keywords = ["lakers", "celtics", "warriors", "nuggets", "heat", "bulls", "knicks"]

    try:
        response = requests.get("https://gamma-api.polymarket.com/markets", params={"limit": 500, "closed": "false"}, timeout=60)
        response.raise_for_status()
        markets = response.json()

        team_markets = []
        for market in markets:
            question = market.get("question", "").lower()
            for team in team_keywords:
                if team in question and ("beat" in question or "win" in question or "vs" in question):
                    team_markets.append(market)
                    break

        print(f"找到 {len(team_markets)} 个包含球队名的比赛市场\n")

        for i, market in enumerate(team_markets[:20]):
            question = market.get("question", "N/A")
            slug = market.get("slug", "N/A")
            print(f"{i+1:2}. {question}")
            print(f"    Slug: {slug}")
            print()

    except requests.exceptions.RequestException as e:
        print(f"搜索请求失败: {e}")

    print("\n" + "=" * 70)
    print("调试完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
