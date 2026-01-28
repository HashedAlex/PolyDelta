#!/usr/bin/env python3
"""快速更新 NBA Daily Matches 数据"""
import os
import sys

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import (
    fetch_nba_matches_web2,
    fetch_nba_matches_polymarket,
    match_daily_games,
    save_daily_matches,
    DATABASE_URL
)
import psycopg2

def main():
    print("=" * 60)
    print("NBA Daily Matches 快速更新")
    print("=" * 60)

    # 1. 获取 Web2 数据
    print("\n[1/4] 从 The Odds API 获取 NBA 比赛...")
    web2_matches = fetch_nba_matches_web2()
    print(f"✓ 获取到 {len(web2_matches)} 场比赛")

    # 2. 获取 Polymarket 数据
    print("\n[2/4] 从 Polymarket 获取 NBA 比赛...")
    poly_data = fetch_nba_matches_polymarket()
    if isinstance(poly_data, tuple):
        poly_matches, _ = poly_data
    else:
        poly_matches = poly_data
    print(f"✓ 获取到 {len(poly_matches)} 场比赛")

    # 3. 匹配数据
    print("\n[3/4] 匹配 Web2 和 Polymarket 数据...")
    merged = match_daily_games(web2_matches, poly_data)
    print(f"✓ 匹配完成，共 {len(merged)} 场比赛")

    # 4. 更新数据库
    print("\n[4/4] 更新数据库...")
    try:
        save_daily_matches(merged)
        print("✓ 数据库更新成功！")
    except Exception as e:
        print(f"❌ 数据库更新失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. 显示更新结果
    print("\n" + "=" * 60)
    print("更新完成！前5场比赛:")
    print("=" * 60)
    for i, m in enumerate(merged[:5], 1):
        print(f"\n{i}. {m['home_team']} vs {m['away_team']}")
        print(f"   Web2: {m['home_team']} {m['home_odds']*100:.1f}% | {m['away_team']} {m['away_odds']*100:.1f}% ({m['bookmaker']})")
        if m.get('poly_home_price'):
            print(f"   Poly: {m['home_team']} {m['poly_home_price']*100:.1f}% | {m['away_team']} {m['poly_away_price']*100:.1f}%")
        else:
            print(f"   Poly: 无数据")

if __name__ == "__main__":
    main()
