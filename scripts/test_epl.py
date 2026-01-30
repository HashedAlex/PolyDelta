"""Test script for EPLScraper — validates EPL injury data parsing."""
import os
import sys
import random

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from scraper.epl_scraper import EPLScraper

scraper = EPLScraper()

# ============================================================
# Fetch injury data
# ============================================================
print("=" * 55)
print("EPL Injury Scraper — sportsgambler.com")
print("=" * 55)

injuries = scraper.fetch_injuries()
print(f"  Total injured/suspended players: {len(injuries)}")
print()

# ============================================================
# Show 3 random players
# ============================================================
print("=" * 55)
print("Sample Players (3 random)")
print("=" * 55)

if injuries:
    sample = random.sample(injuries, min(3, len(injuries)))
    for i, item in enumerate(sample, 1):
        print(f"  [{i}] {item['title']}")
        print(f"      {item['summary']}")
        print(f"      Source: {item['source']}  |  Time: {item['published_str']}")
        print()

# ============================================================
# Validation
# ============================================================
print("=" * 55)
print("Validation")
print("=" * 55)

assert len(injuries) > 0, "FAIL: No injury data fetched"
print(f"  PASS: {len(injuries)} players found")

assert all("title" in i and "summary" in i and "source" in i for i in injuries), \
    "FAIL: Missing required fields"
print(f"  PASS: All entries have required fields")

teams = set(i["title"].split(" - ")[0] for i in injuries)
print(f"  PASS: Data covers {len(teams)} teams: {', '.join(sorted(teams)[:5])}...")
