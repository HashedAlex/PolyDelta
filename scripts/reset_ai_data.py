"""
Reset AI Analysis Data (Soft Reset)

Nullifies all AI-related fields in daily_matches and market_odds tables,
forcing daily_analysis_job.py to re-generate analysis with the new JSON format.
Does NOT delete match/odds data — only AI fields.

Usage:
    python scripts/reset_ai_data.py
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")


def main():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    try:
        # --- Reset daily_matches ---
        cursor.execute("SELECT COUNT(*) FROM daily_matches WHERE ai_analysis IS NOT NULL OR ai_prediction IS NOT NULL")
        daily_count = cursor.fetchone()[0]

        cursor.execute("""
            UPDATE daily_matches SET
                ai_prediction = NULL,
                ai_probability = NULL,
                ai_market = NULL,
                ai_risk = NULL,
                ai_analysis = NULL,
                ai_analysis_full = NULL,
                ai_generated_at = NULL
        """)
        print(f"[daily_matches] Reset {daily_count} rows with AI data (all AI fields set to NULL)")

        # --- Reset market_odds ---
        cursor.execute("SELECT COUNT(*) FROM market_odds WHERE ai_analysis IS NOT NULL OR ai_prediction IS NOT NULL OR ai_analysis_full IS NOT NULL")
        market_count = cursor.fetchone()[0]

        cursor.execute("""
            UPDATE market_odds SET
                ai_prediction = NULL,
                ai_probability = NULL,
                ai_market = NULL,
                ai_risk = NULL,
                ai_analysis = NULL,
                ai_analysis_full = NULL,
                ai_generated_at = NULL
        """)
        print(f"[market_odds] Reset {market_count} rows with AI data (all AI fields set to NULL)")

        conn.commit()
        print("\nDone. Run 'python scripts/daily_analysis_job.py' to re-generate analysis.")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
