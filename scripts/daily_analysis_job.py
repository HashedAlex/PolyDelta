"""
PolyDelta Daily Analysis Job

Standalone script for cron execution. Generates AI analysis for upcoming matches
that don't already have predictions cached.

Usage:
    python scripts/daily_analysis_job.py

Cron example (every hour):
    0 * * * * cd /path/to/worldcup-alpha && python scripts/daily_analysis_job.py
"""

import os
import sys
import time
from datetime import datetime, timedelta

import psycopg2
from dotenv import load_dotenv

# Setup project path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from scraper.ai_analyst import generate_ai_report, parse_analysis_output

DATABASE_URL = os.getenv("DATABASE_URL")
RATE_LIMIT_DELAY = 2  # seconds between AI calls


def fetch_pending_matches(cursor):
    """
    Fetch future daily matches that need AI analysis: new OR stale.

    Time windows (for new matches without analysis):
      - NBA: 3 days | EPL: 7 days | UCL: no limit | Default: 3 days

    Staleness refresh:
      - <24h to kickoff (all leagues): refresh every job run (if analysis >1h old)
      - NBA (>24h out): refresh if analysis >24h old
      - EPL (>24h out): refresh if analysis >48h old
      - UCL (>24h out): refresh if analysis >72h old
    """
    cursor.execute("""
        SELECT id, sport_type, home_team, away_team, commence_time,
               web2_home_odds, web2_away_odds, web2_draw_odds,
               poly_home_price, poly_away_price, poly_draw_price,
               ai_generated_at, ai_prediction
        FROM daily_matches
        WHERE commence_time > NOW()
          AND (
              -- NEW: No analysis yet, within time window
              (ai_prediction IS NULL AND (
                  (sport_type = 'nba' AND commence_time < NOW() + INTERVAL '3 days') OR
                  (sport_type = 'epl' AND commence_time < NOW() + INTERVAL '7 days') OR
                  (sport_type = 'ucl') OR
                  (sport_type NOT IN ('nba', 'epl', 'ucl') AND commence_time < NOW() + INTERVAL '3 days')
              ))
              OR
              -- URGENT REFRESH: <24h to kickoff, all leagues — refresh if analysis >1h old
              (commence_time < NOW() + INTERVAL '24 hours'
               AND ai_prediction IS NOT NULL
               AND (ai_generated_at IS NULL OR ai_generated_at < NOW() - INTERVAL '1 hour'))
              OR
              -- STALE REFRESH: >24h to kickoff — league-specific staleness
              (commence_time >= NOW() + INTERVAL '24 hours'
               AND ai_prediction IS NOT NULL
               AND (
                  (sport_type = 'nba' AND (ai_generated_at IS NULL OR ai_generated_at < NOW() - INTERVAL '24 hours') AND commence_time < NOW() + INTERVAL '3 days') OR
                  (sport_type = 'epl' AND (ai_generated_at IS NULL OR ai_generated_at < NOW() - INTERVAL '48 hours') AND commence_time < NOW() + INTERVAL '7 days') OR
                  (sport_type = 'ucl' AND (ai_generated_at IS NULL OR ai_generated_at < NOW() - INTERVAL '72 hours')) OR
                  (sport_type NOT IN ('nba', 'epl', 'ucl') AND (ai_generated_at IS NULL OR ai_generated_at < NOW() - INTERVAL '24 hours') AND commence_time < NOW() + INTERVAL '3 days')
              ))
          )
        ORDER BY commence_time ASC
    """)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def calculate_ev(home_odds, away_odds, poly_home, poly_away):
    """Calculate maximum EV between home and away."""
    evs = []
    if home_odds and poly_home and poly_home > 0:
        evs.append((home_odds - poly_home) / poly_home)
    if away_odds and poly_away and poly_away > 0:
        evs.append((away_odds - poly_away) / poly_away)
    return max(evs) if evs else 0


def league_from_sport_type(sport_type):
    """Map sport_type DB values to league codes."""
    mapping = {
        "nba": "NBA",
        "epl": "EPL",
        "ucl": "UCL",
        "soccer_epl": "EPL",
        "soccer_uefa_champs_league": "UCL",
        "world_cup": "FIFA",
        "fifa": "FIFA",
    }
    return mapping.get(sport_type.lower(), "NBA")


def process_match(cursor, match):
    """Generate AI analysis for a single match and update the DB."""
    match_id = match["id"]
    home = match["home_team"]
    away = match["away_team"]
    sport_type = match["sport_type"]
    is_refresh = match.get("ai_prediction") is not None

    home_odds = match.get("web2_home_odds") or 0
    away_odds = match.get("web2_away_odds") or 0
    poly_home = match.get("poly_home_price") or 0
    poly_away = match.get("poly_away_price") or 0

    ev = calculate_ev(home_odds, away_odds, poly_home, poly_away)
    league = league_from_sport_type(sport_type)

    tag = "REFRESH" if is_refresh else "NEW"
    print(f"\n   [{match_id}] [{tag}] {home} vs {away} ({sport_type}) — EV: {ev*100:+.1f}%")

    # Build match_data for generate_ai_report
    match_data = {
        "title": f"{home} vs {away}",
        "ev": ev,
        "web2_odds": home_odds * 100,
        "polymarket_price": poly_home * 100,
        "home_team": home,
        "away_team": away,
    }

    result = generate_ai_report(match_data, is_championship=False, league=league, force_analysis=True)

    if not result:
        print(f"   [{match_id}] Skipped (no report generated)")
        return False

    # Safety net: NBA/basketball has no draws — pick winner from best available odds
    if sport_type == "nba" and result.get("predicted_winner", "").lower() == "draw":
        if home_odds > 0 or away_odds > 0:
            winner = home if home_odds > away_odds else away
            source = "trad odds"
        elif poly_home > 0 or poly_away > 0:
            winner = home if poly_home > poly_away else away
            source = "poly odds"
        else:
            winner = home
            source = "no odds available, defaulted to home"
        result["predicted_winner"] = winner
        print(f"   [{match_id}] Fixed Draw → {winner} (NBA has no draws, picked by {source})")

    # Update database with structured fields + full markdown report.
    # Write to both ai_analysis (read by frontend) and ai_analysis_full (backup).
    cursor.execute("""
        UPDATE daily_matches SET
            ai_prediction = %s,
            ai_probability = %s,
            ai_market = %s,
            ai_risk = %s,
            ai_analysis = %s,
            ai_analysis_full = %s,
            ai_generated_at = NOW()
        WHERE id = %s
    """, (
        result["predicted_winner"],
        result["win_probability"],
        result["recommended_market"],
        result["risk_level"],
        result.get("full_report_markdown"),
        result.get("full_report_markdown"),
        match_id,
    ))

    winner = result["predicted_winner"] or "N/A"
    prob = result["win_probability"]
    prob_str = f"{prob}%" if prob else "N/A"
    market = result["recommended_market"] or "N/A"
    risk = result["risk_level"] or "N/A"

    print(f"   [{match_id}] ✓ Winner: {winner} | Prob: {prob_str} | Market: {market} | Risk: {risk}")
    return True


def fetch_pending_championships(cursor):
    """
    Fetch championship/winner markets that do NOT already have an AI prediction.
    """
    cursor.execute("""
        SELECT id, sport_type, team_name, web2_odds,
               polymarket_price, prop_type
        FROM market_odds
        WHERE ai_prediction IS NULL
          AND web2_odds IS NOT NULL
          AND polymarket_price IS NOT NULL
        ORDER BY sport_type, team_name
    """)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def process_championship(cursor, market):
    """Generate AI analysis for a single championship market and update the DB."""
    market_id = market["id"]
    team = market["team_name"]
    sport_type = market["sport_type"]
    web2_odds = market.get("web2_odds") or 0
    poly_price = market.get("polymarket_price") or 0

    ev = ((web2_odds - poly_price) / poly_price) if poly_price > 0 else 0
    league = league_from_sport_type(sport_type)

    print(f"\n   [C-{market_id}] {team} ({sport_type}) — EV: {ev*100:+.1f}%")

    match_data = {
        "title": f"{team} — Championship Winner",
        "ev": ev,
        "web2_odds": web2_odds * 100,
        "polymarket_price": poly_price * 100,
        "home_team": team,
        "away_team": "Championship Field",
    }

    result = generate_ai_report(match_data, is_championship=True, league=league)

    if not result:
        print(f"   [C-{market_id}] Skipped (no report generated)")
        return False

    cursor.execute("""
        UPDATE market_odds SET
            ai_prediction = %s,
            ai_probability = %s,
            ai_market = %s,
            ai_risk = %s,
            ai_analysis = %s,
            ai_analysis_full = %s,
            ai_generated_at = NOW()
        WHERE id = %s
    """, (
        result["predicted_winner"],
        result["win_probability"],
        result["recommended_market"],
        result["risk_level"],
        result.get("full_report_markdown"),
        result.get("full_report_markdown"),
        market_id,
    ))

    winner = result["predicted_winner"] or "N/A"
    prob = result["win_probability"]
    prob_str = f"{prob}%" if prob else "N/A"
    risk = result["risk_level"] or "N/A"

    print(f"   [C-{market_id}] ✓ {team}: {winner} | Prob: {prob_str} | Risk: {risk}")
    return True


def main():
    """Main entry point for the daily analysis job."""
    print("=" * 60)
    print("PolyDelta Daily Analysis Job")
    print(f"Run time: {datetime.utcnow().isoformat()}Z")
    print("=" * 60)

    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        # --- Phase 1: Daily Matches ---
        print("\n--- Phase 1: Daily Matches ---")
        matches = fetch_pending_matches(cursor)
        print(f"Found {len(matches)} matches needing AI analysis (new + stale)")

        daily_generated = 0
        daily_skipped = 0

        for i, match in enumerate(matches):
            success = process_match(cursor, match)
            if success:
                daily_generated += 1
                conn.commit()
            else:
                daily_skipped += 1

            if success and i < len(matches) - 1:
                time.sleep(RATE_LIMIT_DELAY)

        # --- Phase 2: Championship / Winner Markets ---
        print("\n--- Phase 2: Championship Markets ---")
        championships = fetch_pending_championships(cursor)
        print(f"Found {len(championships)} championships needing AI analysis")

        champ_generated = 0
        champ_skipped = 0

        for i, market in enumerate(championships):
            success = process_championship(cursor, market)
            if success:
                champ_generated += 1
                conn.commit()
            else:
                champ_skipped += 1

            if success and i < len(championships) - 1:
                time.sleep(RATE_LIMIT_DELAY)

        total_gen = daily_generated + champ_generated
        total_skip = daily_skipped + champ_skipped
        print(f"\n{'=' * 60}")
        print(f"Job complete: {total_gen} generated ({daily_generated} daily + {champ_generated} champ), {total_skip} skipped")
        print(f"{'=' * 60}")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
