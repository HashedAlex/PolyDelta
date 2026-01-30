"""Test script for RSSFetcher — validates Prediction vs Chatbot data strategies."""
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from scraper.rss_service import RSSFetcher

fetcher = RSSFetcher()

# ============================================================
# Test Case 1: Prediction Mode — last 24h NBA news only
# ============================================================
print("=" * 55)
print("Test 1: Prediction Mode (NBA, last 24h)")
print("=" * 55)

prediction_news = fetcher.fetch_news(source_keys=["HoopsHype_NBA"], lookback_hours=24)
print(f"  Articles found: {len(prediction_news)}")
for article in prediction_news[:3]:
    print(f"  - [{article['published_str']}] {article['title'][:70]}")

# ============================================================
# Test Case 2: Chatbot Mode — ALL available Football news
# ============================================================
print()
print("=" * 55)
print("Test 2: Chatbot Mode (Football, ALL history)")
print("=" * 55)

chatbot_news = fetcher.fetch_news(source_keys=["BBC_Football"], lookback_hours=None)
print(f"  Articles found: {len(chatbot_news)}")
for article in chatbot_news[:3]:
    print(f"  - [{article['published_str']}] {article['title'][:70]}")

# ============================================================
# Test Case 3: UCL & International Football feeds
# ============================================================
print()
print("=" * 55)
print("Test 3: UCL & International Football")
print("=" * 55)

ucl_news = fetcher.fetch_news(source_keys=["Guardian_UCL", "SkySports_Football"], lookback_hours=None)
print(f"  Articles found: {len(ucl_news)}")
for article in ucl_news[:2]:
    print(f"  - [{article['source']}] {article['title'][:70]}")

# ============================================================
# Comparison
# ============================================================
print()
print("=" * 55)
print("Comparison")
print("=" * 55)

all_24h = fetcher.fetch_news(lookback_hours=24)
all_full = fetcher.fetch_news(lookback_hours=None)
print(f"  All feeds (24h):  {len(all_24h)} articles")
print(f"  All feeds (full): {len(all_full)} articles")
print(f"  Difference:       {len(all_full) - len(all_24h)} older articles available for Chatbot")
