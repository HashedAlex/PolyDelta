"""
WorldCup Alpha - 深度诊断脚本
用于：
1. 找到正确的 Polymarket 市场 ID（夺冠盘口，非小组出线）
2. 检查 The Odds API 是否支持 bookmaker 链接
"""
import os
import json
import requests
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

ODDS_API_KEY = os.getenv('ODDS_API_KEY')

# 分隔线样式
DIVIDER = "=" * 70
SUB_DIVIDER = "-" * 70


def diagnose_polymarket():
    """
    目标 1：找到正确的 Polymarket 市场 ID
    搜索 "Winner" 类型的市场，排除单一队伍 Yes/No 盘口
    """
    print(f"\n{DIVIDER}")
    print("🔍 [Polymarket] 诊断：寻找正确的夺冠盘口 Market ID")
    print(DIVIDER)

    # Gamma API endpoint
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "closed": "false",
        "limit": 500
    }

    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        markets = response.json()

        print(f"\n📊 共获取到 {len(markets)} 个活跃市场\n")

        # ============================================
        # 搜索 World Cup 2026 Winner 市场
        # ============================================
        print(f"{SUB_DIVIDER}")
        print("⚽ 搜索: World Cup 2026 Winner")
        print(SUB_DIVIDER)

        wc_candidates = []
        for market in markets:
            question = market.get("question", "").lower()
            description = market.get("description", "").lower()
            group_slug = market.get("groupSlug", "").lower()
            slug = market.get("slug", "")

            # 包含 world cup 和 2026
            if "world cup" in question and "2026" in question:
                # 检查是否是 "winner" 类型（非单一队伍）
                is_winner_market = (
                    "winner" in question or
                    "winner" in description or
                    "winner" in group_slug
                )

                # 检查是否是单一队伍 Yes/No 盘口（排除）
                is_single_team = (
                    "will " in question and
                    ("win the" in question or "qualify" in question)
                )

                # 获取 outcomes
                outcomes = market.get("outcomes", [])
                if isinstance(outcomes, str):
                    try:
                        outcomes = json.loads(outcomes)
                    except:
                        outcomes = []

                # 如果 outcomes 只有 Yes/No，说明是单一队伍盘口
                outcomes_lower = [o.lower() if isinstance(o, str) else "" for o in outcomes]
                is_yes_no = set(outcomes_lower) == {"yes", "no"}

                # 我们要找的是：多队伍选择盘口（outcomes 不是 Yes/No）
                # 或者明确包含 "winner" 且不是单一队伍
                if not is_yes_no and len(outcomes) > 2:
                    # 这是一个多选项市场（可能是夺冠盘口）
                    wc_candidates.append({
                        "id": market.get("id"),
                        "slug": slug,
                        "question": market.get("question"),
                        "description": market.get("description", "")[:100],
                        "outcomes_count": len(outcomes),
                        "outcomes_sample": outcomes[:5] if outcomes else [],
                        "group_slug": market.get("groupSlug", ""),
                    })
                elif is_winner_market and not is_single_team:
                    wc_candidates.append({
                        "id": market.get("id"),
                        "slug": slug,
                        "question": market.get("question"),
                        "description": market.get("description", "")[:100],
                        "outcomes_count": len(outcomes),
                        "outcomes_sample": outcomes[:5] if outcomes else [],
                        "group_slug": market.get("groupSlug", ""),
                    })

        # 打印 Top 3
        if wc_candidates:
            print(f"\n✅ 找到 {len(wc_candidates)} 个候选市场:\n")
            for i, market in enumerate(wc_candidates[:3], 1):
                print(f"  【候选 {i}】")
                print(f"  ID: {market['id']}")
                print(f"  Slug: {market['slug']}")
                print(f"  Question: {market['question']}")
                print(f"  Group Slug: {market['group_slug']}")
                print(f"  Outcomes ({market['outcomes_count']}): {market['outcomes_sample']}")
                print(f"  URL: https://polymarket.com/event/{market['slug']}")
                print()
        else:
            print("\n⚠️ 未找到多选项的 World Cup Winner 市场")
            print("   可能所有市场都是单一队伍 Yes/No 格式")

        # ============================================
        # 搜索 NBA Championship 市场
        # ============================================
        print(f"\n{SUB_DIVIDER}")
        print("🏀 搜索: NBA Championship Winner")
        print(SUB_DIVIDER)

        nba_candidates = []
        for market in markets:
            question = market.get("question", "").lower()
            description = market.get("description", "").lower()
            group_slug = market.get("groupSlug", "").lower()
            slug = market.get("slug", "")

            # 包含 nba 和 champion/finals
            if "nba" in question and ("champion" in question or "finals" in question):
                outcomes = market.get("outcomes", [])
                if isinstance(outcomes, str):
                    try:
                        outcomes = json.loads(outcomes)
                    except:
                        outcomes = []

                outcomes_lower = [o.lower() if isinstance(o, str) else "" for o in outcomes]
                is_yes_no = set(outcomes_lower) == {"yes", "no"}

                # 寻找多选项市场
                if not is_yes_no and len(outcomes) > 2:
                    nba_candidates.append({
                        "id": market.get("id"),
                        "slug": slug,
                        "question": market.get("question"),
                        "description": market.get("description", "")[:100],
                        "outcomes_count": len(outcomes),
                        "outcomes_sample": outcomes[:5] if outcomes else [],
                        "group_slug": market.get("groupSlug", ""),
                    })

        # 打印 Top 3
        if nba_candidates:
            print(f"\n✅ 找到 {len(nba_candidates)} 个候选市场:\n")
            for i, market in enumerate(nba_candidates[:3], 1):
                print(f"  【候选 {i}】")
                print(f"  ID: {market['id']}")
                print(f"  Slug: {market['slug']}")
                print(f"  Question: {market['question']}")
                print(f"  Group Slug: {market['group_slug']}")
                print(f"  Outcomes ({market['outcomes_count']}): {market['outcomes_sample']}")
                print(f"  URL: https://polymarket.com/event/{market['slug']}")
                print()
        else:
            print("\n⚠️ 未找到多选项的 NBA Championship 市场")
            print("   NBA 市场可能全是单一队伍 Yes/No 格式")

        # ============================================
        # 额外：列出所有 World Cup 相关市场（用于调试）
        # ============================================
        print(f"\n{SUB_DIVIDER}")
        print("📋 附录：所有 World Cup 2026 相关市场（前 10 个）")
        print(SUB_DIVIDER)

        all_wc = []
        for market in markets:
            question = market.get("question", "").lower()
            if "world cup" in question and "2026" in question:
                outcomes = market.get("outcomes", [])
                if isinstance(outcomes, str):
                    try:
                        outcomes = json.loads(outcomes)
                    except:
                        outcomes = []
                all_wc.append({
                    "question": market.get("question"),
                    "outcomes": outcomes[:3] if outcomes else [],
                    "slug": market.get("slug", ""),
                })

        for i, m in enumerate(all_wc[:10], 1):
            print(f"\n  {i}. {m['question'][:80]}...")
            print(f"     Outcomes: {m['outcomes']}")
            print(f"     Slug: {m['slug']}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Polymarket API 请求失败: {e}")


def diagnose_web2_api():
    """
    目标 2：检查 The Odds API 数据结构
    确认是否包含 bookmaker 链接字段
    """
    print(f"\n\n{DIVIDER}")
    print("🔍 [Web2] 诊断：检查 The Odds API 数据结构")
    print(DIVIDER)

    if not ODDS_API_KEY:
        print("\n❌ 错误: ODDS_API_KEY 未设置")
        return

    # 尝试获取 World Cup 数据
    endpoints = [
        ("soccer_fifa_world_cup_winner", "FIFA World Cup Winner"),
        ("basketball_nba_championship_winner", "NBA Championship Winner"),
    ]

    for sport_key, sport_name in endpoints:
        print(f"\n{SUB_DIVIDER}")
        print(f"📡 调用 API: {sport_name}")
        print(SUB_DIVIDER)

        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "us,uk,eu",
            "markets": "outrights",
            "oddsFormat": "decimal"
        }

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 404:
                print(f"\n⚠️ 市场暂未开放 (404)")
                continue

            if response.status_code == 401:
                print(f"\n❌ API Key 无效 (401)")
                continue

            response.raise_for_status()
            data = response.json()

            if not data:
                print(f"\n⚠️ API 返回空数据")
                continue

            # 获取第一个事件
            event = data[0] if data else {}
            bookmakers = event.get("bookmakers", [])

            print(f"\n✅ 成功获取数据")
            print(f"   事件数量: {len(data)}")
            print(f"   Bookmakers 数量: {len(bookmakers)}")

            # 检查前 3 个 bookmakers
            print(f"\n📊 前 3 个 Bookmakers 详情:")
            print(SUB_DIVIDER)

            for i, bookmaker in enumerate(bookmakers[:3], 1):
                print(f"\n  【Bookmaker {i}】")
                print(f"  Key (名称): {bookmaker.get('key')}")
                print(f"  Title: {bookmaker.get('title')}")

                # 检查是否有链接字段
                link = bookmaker.get('link')
                affiliate_url = bookmaker.get('affiliate_url')
                url_field = bookmaker.get('url')

                print(f"  link 字段: {link if link else '❌ 不存在'}")
                print(f"  affiliate_url 字段: {affiliate_url if affiliate_url else '❌ 不存在'}")
                print(f"  url 字段: {url_field if url_field else '❌ 不存在'}")

                # 获取赔率示例
                markets = bookmaker.get("markets", [])
                if markets:
                    outcomes = markets[0].get("outcomes", [])[:3]
                    print(f"  赔率示例:")
                    for outcome in outcomes:
                        name = outcome.get("name")
                        price = outcome.get("price")
                        print(f"    - {name}: {price}")

            # 打印完整的第一个 bookmaker 的 JSON 结构
            if bookmakers:
                print(f"\n\n📋 完整 Bookmaker JSON 结构（第一个）:")
                print(SUB_DIVIDER)
                first_bookmaker = bookmakers[0].copy()
                # 简化 markets 以便查看
                if "markets" in first_bookmaker:
                    first_bookmaker["markets"] = f"[{len(first_bookmaker['markets'])} markets...]"
                print(json.dumps(first_bookmaker, indent=2, ensure_ascii=False))

            # 检查 API 使用量
            remaining = response.headers.get('x-requests-remaining')
            used = response.headers.get('x-requests-used')
            if remaining:
                print(f"\n📈 API 配额: 已用 {used}, 剩余 {remaining}")

        except requests.exceptions.RequestException as e:
            print(f"\n❌ API 请求失败: {e}")


def main():
    """主函数"""
    print(DIVIDER)
    print("🔬 WorldCup Alpha - 深度诊断脚本")
    print("   目标 1: 找到正确的 Polymarket 市场 ID")
    print("   目标 2: 检查 Web2 API 是否支持 Bookmaker 链接")
    print(DIVIDER)

    # 诊断 Polymarket
    diagnose_polymarket()

    # 诊断 Web2 API
    diagnose_web2_api()

    # 总结
    print(f"\n\n{DIVIDER}")
    print("📝 诊断总结")
    print(DIVIDER)
    print("""
根据以上诊断结果：

1. [Polymarket] 如果找到了多选项市场（outcomes > 2），
   请记录其 ID 和 Slug，用于替换 scraper.py 中的关键词搜索。

2. [Web2] 如果 bookmaker 没有 link/url 字段，
   我们需要手动维护一个 bookmaker -> URL 的映射表。
   常见 bookmaker 官网：
   - bet365: https://www.bet365.com
   - draftkings: https://sportsbook.draftkings.com
   - fanduel: https://sportsbook.fanduel.com
   - betmgm: https://sports.betmgm.com
   - caesars: https://www.williamhill.com/us
""")
    print(DIVIDER)


if __name__ == "__main__":
    main()
