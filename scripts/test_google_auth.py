"""Logic Test: Anchor & Adjust Verification.

Verifies that the LLM respects the Market Baseline (Odds) when there is no news.
Simulates a fake match with perfectly even odds (~50/50).
"""
import os
import sys
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from scraper.ai_analyst import generate_ai_report


def test_anchor_logic():
    print("STARTING LOGIC TEST: Anchor & Adjust Verification")
    print()

    # Define a Mock Match with EVEN ODDS (Implied Prob ~50%)
    # Using fake names ensures NO NEWS is found by scrapers
    mock_match = {
        "title": "Simulation Alpha FC vs Simulation Beta Utd",
        "home_team": "Simulation Alpha FC",
        "away_team": "Simulation Beta Utd",
        "ev": 0.03,            # 3% EV to pass threshold
        "web2_odds": 50.0,     # 50% implied probability (even odds)
        "polymarket_price": 47.0,
    }

    print(f"Mock Match: {mock_match['home_team']} vs {mock_match['away_team']}")
    print(f"Odds: 50.0% vs 50.0% (Implied ~50/50)")
    print(f"Polymarket: {mock_match['polymarket_price']}%")
    print("Fetching Analysis (expecting 'No News' fallback)...")
    print()

    # Generate Analysis
    try:
        result = generate_ai_report(mock_match, is_championship=False, league="NBA")

        # Parse & Display Results
        print("=" * 50)
        print("AI OUTPUT SUMMARY")
        print("=" * 50)

        if result and isinstance(result, dict):
            print(f"Predicted Winner: {result.get('predicted_winner')}")
            print(f"Win Probability:  {result.get('win_probability')}%")
            print(f"Risk Level:       {result.get('risk_level')}")
            print(f"Market:           {result.get('recommended_market')}")

            print()
            print("FULL REASONING SNIPPET:")
            print("-" * 30)
            print(result.get('full_report_markdown', '')[:800] + "...")

            # Logical Assertion
            prob = result.get('win_probability', 0)
            if prob and 45 <= prob <= 55:
                print(f"\nPASS: Probability ({prob}%) stayed close to the Market Anchor (50%) in absence of news.")
            elif prob:
                print(f"\nFAIL: Probability ({prob}%) deviated too far from Anchor (50%) without news evidence!")
            else:
                print(f"\nWARN: Could not parse win_probability from output.")
        else:
            print("No result returned (API may be unavailable or EV threshold not met).")

    except Exception as e:
        print(f"Error during generation: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_anchor_logic()
