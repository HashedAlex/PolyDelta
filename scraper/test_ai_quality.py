#!/usr/bin/env python3
"""
AI Quality Test Script
Tests the new AI Generation Logic (Gemini Flash 2.0 + Dynamic Insights Prompt)

Samples:
- 3x NBA Daily Matches
- 3x NBA Championship Futures
- 3x FIFA World Cup Teams

Outputs: ai_audit_report.md
"""
import os
import json
import sys
from datetime import datetime

# Add scraper directory to path
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from sports_prompt_builder import generate_championship_analysis, generate_daily_match_analysis

# Cache file paths
CACHE_DIR = os.path.dirname(__file__)
NBA_CACHE = os.path.join(CACHE_DIR, "cache_nba.json")
FIFA_CACHE = os.path.join(CACHE_DIR, "cache_worldcup.json")
REPORT_FILE = os.path.join(CACHE_DIR, "ai_audit_report.md")


def load_cache(cache_file):
    """Load data from cache file"""
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
            return cache.get('data', [])
    return []


def extract_championship_teams(cache_data, limit=3):
    """Extract top teams from championship cache data"""
    teams = []
    for event in cache_data:
        if not event.get('has_outrights'):
            continue
        for bookmaker in event.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                if market.get('key') != 'outrights':
                    continue
                for outcome in market.get('outcomes', []):
                    name = outcome.get('name')
                    price = outcome.get('price', 1)
                    if name and price > 1:
                        prob = 1 / price
                        # Skip very low probability teams (<1%)
                        if prob >= 0.01:
                            teams.append({
                                'name': name,
                                'odds': price,
                                'probability': prob
                            })
            break  # Only use first bookmaker
        break  # Only use first event

    # Sort by probability (highest first) and take top N
    teams.sort(key=lambda x: x['probability'], reverse=True)
    return teams[:limit]


def format_sample_to_markdown(category: str, name: str, result: str, odds_info: str) -> str:
    """Format a single sample result to Markdown"""
    output = []
    output.append(f"### {name}")
    output.append(f"*{odds_info}*\n")

    if not result:
        output.append("❌ **No result returned**\n")
        return "\n".join(output)

    try:
        data = json.loads(result)

        # Extract strategy card
        strategy = data.get('strategy_card', {})
        news = data.get('news_card', {})

        # Tags
        tags = news.get('tags', [])
        output.append(f"**🏷️ Tags:** {', '.join(tags) if tags else 'N/A'}\n")

        # Headline
        headline = strategy.get('headline', 'N/A')
        output.append(f"**📰 Headline:** {headline}\n")

        # Status & Score
        status = strategy.get('status', 'N/A')
        score = strategy.get('score', 'N/A')
        output.append(f"**📊 Status:** {status} (Score: {score})\n")

        # Analysis
        analysis = strategy.get('analysis', 'N/A')
        output.append(f"**📝 Analysis:**\n> {analysis}\n")

        # Kelly Advice
        kelly = strategy.get('kelly_advice', '')
        if kelly:
            output.append(f"**💰 Kelly Advice:** {kelly}\n")

        # Risk
        risk = strategy.get('risk_text', '')
        if risk:
            output.append(f"**⚠️ Risk:** {risk}\n")

        # Pillars (detailed insights)
        pillars = news.get('pillars', [])
        if pillars:
            output.append("**💡 Key Insights:**")
            for pillar in pillars:
                icon = pillar.get('icon', '•')
                title = pillar.get('title', 'Insight')
                content = pillar.get('content', '')
                sentiment = pillar.get('sentiment', 'neutral')
                sentiment_emoji = {'positive': '🟢', 'negative': '🔴', 'neutral': '🟡'}.get(sentiment, '⚪')
                output.append(f"- {icon} **{title}** {sentiment_emoji}")
                output.append(f"  - {content}")
            output.append("")

        # Prediction
        prediction = news.get('prediction', '')
        confidence = news.get('confidence', '')
        confidence_pct = news.get('confidence_pct', '')
        if prediction:
            output.append(f"**🎯 Prediction:** {prediction} ({confidence} - {confidence_pct}%)\n")

    except json.JSONDecodeError:
        output.append(f"**Raw Output:**\n```\n{result}\n```\n")

    output.append("---\n")
    return "\n".join(output)


def run_quality_test():
    print("=" * 60)
    print("AI QUALITY TEST - Gemini Flash 2.0 + Dynamic Insights")
    print("=" * 60)

    # Markdown report content
    report = []
    report.append("# AI Audit Report")
    report.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    report.append("**Model:** `google/gemini-2.0-flash-001` via OpenRouter\n")
    report.append("---\n")

    # Load cache data
    print("\n--- Loading Cache Data ---")
    nba_cache = load_cache(NBA_CACHE)
    fifa_cache = load_cache(FIFA_CACHE)
    print(f"NBA Cache: {len(nba_cache)} events")
    print(f"FIFA Cache: {len(fifa_cache)} events")

    # ============================================
    # TEST 1: NBA Championship Futures (3 samples)
    # ============================================
    print("\n" + "=" * 60)
    print(">>> TEST 1: NBA CHAMPIONSHIP FUTURES (3 Samples)")
    print("=" * 60)

    report.append("## 🏀 NBA Championship Futures\n")

    nba_teams = extract_championship_teams(nba_cache, limit=3)
    print(f"Testing teams: {[t['name'] for t in nba_teams]}")

    for i, team in enumerate(nba_teams, 1):
        print(f"\n--- NBA Futures #{i}: {team['name']} ---")
        odds_info = f"Odds: {team['odds']:.2f} | Implied Prob: {team['probability']*100:.1f}%"
        print(odds_info)

        # Simulate Polymarket price (slightly different from Web2)
        poly_price = team['probability'] * (1 + (0.05 if i % 2 == 0 else -0.03))
        ev = (team['probability'] - poly_price) / poly_price if poly_price > 0 else 0

        result = generate_championship_analysis(
            team_name=team['name'],
            sport_type='nba',
            web2_odds=team['probability'],
            poly_price=poly_price,
            ev=ev
        )

        # Add to report
        report.append(format_sample_to_markdown("NBA Futures", team['name'], result, odds_info))

        if result:
            print("✅ Generated successfully")
        else:
            print("❌ No result returned")

    # ============================================
    # TEST 2: FIFA World Cup Teams (3 samples)
    # ============================================
    print("\n" + "=" * 60)
    print(">>> TEST 2: FIFA WORLD CUP TEAMS (3 Samples)")
    print("=" * 60)

    report.append("## ⚽ FIFA World Cup Futures\n")

    fifa_teams = extract_championship_teams(fifa_cache, limit=3)
    print(f"Testing teams: {[t['name'] for t in fifa_teams]}")

    for i, team in enumerate(fifa_teams, 1):
        print(f"\n--- FIFA Futures #{i}: {team['name']} ---")
        odds_info = f"Odds: {team['odds']:.2f} | Implied Prob: {team['probability']*100:.1f}%"
        print(odds_info)

        poly_price = team['probability'] * (1 + (0.04 if i % 2 == 0 else -0.02))
        ev = (team['probability'] - poly_price) / poly_price if poly_price > 0 else 0

        result = generate_championship_analysis(
            team_name=team['name'],
            sport_type='world_cup',
            web2_odds=team['probability'],
            poly_price=poly_price,
            ev=ev
        )

        # Add to report
        report.append(format_sample_to_markdown("FIFA Futures", team['name'], result, odds_info))

        if result:
            print("✅ Generated successfully")
        else:
            print("❌ No result returned")

    # ============================================
    # TEST 3: NBA Daily Matches (3 samples)
    # ============================================
    print("\n" + "=" * 60)
    print(">>> TEST 3: NBA DAILY MATCHES (3 Samples)")
    print("=" * 60)

    report.append("## 🏀 NBA Daily Matches\n")

    # Simulated daily match data with VARIED EV values
    daily_matches = [
        {"home": "Los Angeles Lakers", "away": "Boston Celtics", "home_odds": 0.45, "away_odds": 0.55, "poly_home": 0.42, "poly_away": 0.58},  # +7.1% EV on Lakers
        {"home": "Golden State Warriors", "away": "Phoenix Suns", "home_odds": 0.52, "away_odds": 0.48, "poly_home": 0.54, "poly_away": 0.46},  # -3.7% EV (Suns value)
        {"home": "Miami Heat", "away": "New York Knicks", "home_odds": 0.48, "away_odds": 0.52, "poly_home": 0.47, "poly_away": 0.53},  # +2.1% EV on Heat
    ]

    for i, match in enumerate(daily_matches, 1):
        match_name = f"{match['home']} vs {match['away']}"
        print(f"\n--- Daily Match #{i}: {match_name} ---")
        odds_info = f"Home: {match['home_odds']*100:.1f}% | Away: {match['away_odds']*100:.1f}%"
        print(odds_info)

        # Use provided Polymarket prices for varied EV
        poly_home = match['poly_home']
        poly_away = match['poly_away']
        max_ev = max(
            (match['home_odds'] - poly_home) / poly_home if poly_home > 0 else 0,
            (match['away_odds'] - poly_away) / poly_away if poly_away > 0 else 0
        )

        result = generate_daily_match_analysis(
            home_team=match['home'],
            away_team=match['away'],
            sport_type='nba',
            home_odds=match['home_odds'],
            away_odds=match['away_odds'],
            poly_home=poly_home,
            poly_away=poly_away,
            max_ev=max_ev
        )

        # Add to report
        report.append(format_sample_to_markdown("NBA Daily", match_name, result, odds_info))

        if result:
            print("✅ Generated successfully")
        else:
            print("❌ No result returned")

    # ============================================
    # Save Report
    # ============================================
    report_content = "\n".join(report)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print("\n" + "=" * 60)
    print(f"✅ AI QUALITY TEST COMPLETE")
    print(f"📄 Report saved to: {REPORT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    run_quality_test()
