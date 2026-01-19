"""
Polymarket 诊断脚本 v2
用于检查 Gamma API 返回的市场数据，找出正确的关键词
"""
import requests
import json
import re


def search_all_markets(keyword, exact=False):
    """
    搜索所有市场，支持精确匹配
    """
    print(f"\n{'='*70}")
    print(f"搜索关键词: '{keyword}' (精确匹配: {exact})")
    print("=" * 70)

    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "closed": "false",
        "limit": 500  # 增加到 500
    }

    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        markets = response.json()

        print(f"API 返回 {len(markets)} 个 markets")

        matched = []
        keyword_lower = keyword.lower()

        for market in markets:
            question = market.get("question", "")
            description = market.get("description", "")

            # 精确匹配（单词边界）或模糊匹配
            if exact:
                pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                if re.search(pattern, question.lower()) or re.search(pattern, description.lower()):
                    matched.append(market)
            else:
                if keyword_lower in question.lower() or keyword_lower in description.lower():
                    matched.append(market)

        print(f"匹配到 {len(matched)} 个市场\n")

        if matched:
            print(f"前 {min(15, len(matched))} 个匹配的市场:")
            print("-" * 70)
            for i, m in enumerate(matched[:15], 1):
                question = m.get("question", "N/A")
                market_id = m.get("id", "N/A")
                slug = m.get("slug", "N/A")

                # 解析 outcomes 和 prices
                outcomes = m.get("outcomes", [])
                prices = m.get("outcomePrices", [])
                if isinstance(outcomes, str):
                    try:
                        outcomes = json.loads(outcomes)
                    except:
                        outcomes = []
                if isinstance(prices, str):
                    try:
                        prices = json.loads(prices)
                    except:
                        prices = []

                print(f"\n[{i}] Question: {question}")
                print(f"    ID: {market_id}")
                print(f"    Slug: {slug}")
                print(f"    URL: https://polymarket.com/event/{slug}")
                print(f"    Outcomes: {outcomes[:6]}..." if len(outcomes) > 6 else f"    Outcomes: {outcomes}")
                if prices:
                    prices_formatted = [f"{float(p):.2%}" if p else "N/A" for p in prices[:6]]
                    print(f"    Prices: {prices_formatted}")
            print("-" * 70)

        return matched

    except Exception as e:
        print(f"API 请求失败: {e}")
        return []


def list_sports_categories():
    """
    列出所有体育类别的市场
    """
    print(f"\n{'='*70}")
    print("按体育类别分类所有市场")
    print("=" * 70)

    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "closed": "false",
        "limit": 500
    }

    categories = {
        "NBA/Basketball": ["nba", "basketball", "lakers", "celtics", "warriors", "nuggets", "cavaliers"],
        "NFL/Football": ["nfl", "super bowl", "patriots", "chiefs", "eagles", "49ers", "cowboys"],
        "Soccer/Football": ["premier league", "epl", "soccer", "world cup", "fifa", "manchester", "liverpool", "arsenal"],
        "MLB/Baseball": ["mlb", "baseball", "yankees", "dodgers", "world series"],
        "NHL/Hockey": ["nhl", "hockey", "stanley cup"],
        "UFC/MMA": ["ufc", "mma", "fight"],
        "Tennis": ["tennis", "wimbledon", "us open", "australian open"],
        "Golf": ["golf", "pga", "masters"],
    }

    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        markets = response.json()

        print(f"总共获取 {len(markets)} 个市场\n")

        for category, keywords in categories.items():
            matched = []
            for market in markets:
                question = market.get("question", "").lower()
                if any(re.search(r'\b' + kw + r'\b', question) for kw in keywords):
                    matched.append(market)

            print(f"\n{category}: {len(matched)} 个市场")
            if matched:
                for i, m in enumerate(matched[:5], 1):
                    q = m.get("question", "")[:60]
                    outcomes = m.get("outcomes", [])
                    if isinstance(outcomes, str):
                        try:
                            outcomes = json.loads(outcomes)
                        except:
                            outcomes = []
                    outcome_count = len(outcomes) if outcomes else 0
                    print(f"  [{i}] {q}... ({outcome_count} outcomes)")

    except Exception as e:
        print(f"请求失败: {e}")


def find_multi_outcome_markets():
    """
    找出有多个选项的市场（这些通常是冠军/赢家市场）
    """
    print(f"\n{'='*70}")
    print("寻找多选项市场（可能是冠军/赢家类市场）")
    print("=" * 70)

    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "closed": "false",
        "limit": 500
    }

    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        markets = response.json()

        multi_outcome = []
        for market in markets:
            outcomes = market.get("outcomes", [])
            if isinstance(outcomes, str):
                try:
                    outcomes = json.loads(outcomes)
                except:
                    outcomes = []

            # 找出超过 2 个选项的市场（不是简单的 Yes/No）
            if len(outcomes) > 2:
                multi_outcome.append({
                    "question": market.get("question", ""),
                    "outcomes": outcomes,
                    "prices": market.get("outcomePrices", []),
                    "slug": market.get("slug", ""),
                    "id": market.get("id", "")
                })

        print(f"找到 {len(multi_outcome)} 个多选项市场\n")

        # 按选项数量排序
        multi_outcome.sort(key=lambda x: len(x["outcomes"]), reverse=True)

        for i, m in enumerate(multi_outcome[:20], 1):
            print(f"\n[{i}] {m['question']}")
            print(f"    ID: {m['id']}")
            print(f"    URL: https://polymarket.com/event/{m['slug']}")
            print(f"    选项数量: {len(m['outcomes'])}")
            # 打印前 8 个选项
            outcomes_preview = m['outcomes'][:8]
            print(f"    选项: {outcomes_preview}{'...' if len(m['outcomes']) > 8 else ''}")

            # 解析价格
            prices = m['prices']
            if isinstance(prices, str):
                try:
                    prices = json.loads(prices)
                except:
                    prices = []
            if prices:
                top_prices = [(m['outcomes'][i], float(prices[i])) for i in range(min(5, len(prices))) if prices[i]]
                top_prices.sort(key=lambda x: x[1], reverse=True)
                print(f"    热门: {[(p[0], f'{p[1]:.1%}') for p in top_prices[:5]]}")

    except Exception as e:
        print(f"请求失败: {e}")


def main():
    print("=" * 70)
    print("Polymarket 诊断脚本 v2")
    print("=" * 70)

    # 1. 精确搜索 NBA
    search_all_markets("NBA", exact=True)

    # 2. 精确搜索篮球相关
    search_all_markets("basketball", exact=True)

    # 3. 精确搜索 Premier League
    search_all_markets("Premier League", exact=False)

    # 4. 按类别分类
    list_sports_categories()

    # 5. 找多选项市场（冠军类市场）
    find_multi_outcome_markets()


if __name__ == "__main__":
    main()
