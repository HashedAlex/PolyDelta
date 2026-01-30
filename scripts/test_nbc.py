"""Test script for NBCScraper — validates NBA player news fetching."""
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from scraper.nbc_scraper import NBCScraper

scraper = NBCScraper()

# ============================================================
# Fetch last 24 hours of NBA news
# ============================================================
print("=" * 55)
print("NBC Sports Edge — NBA News (last 24h)")
print("=" * 55)

articles = scraper.fetch_news(lookback_hours=24)
print(f"  Articles found: {len(articles)}")
print()

for i, article in enumerate(articles[:3], 1):
    print(f"  [{i}] {article['title'][:80]}")
    print(f"      Source:    {article['source']}")
    print(f"      Published: {article['published_str']}")
    print(f"      URL:       {article['url'][:80]}")
    print(f"      Summary:   {article['summary'][:100]}...")
    print()

# ============================================================
# Validation
# ============================================================
print("=" * 55)
print("Validation")
print("=" * 55)

all_articles = scraper.fetch_news(lookback_hours=None)
print(f"  24h articles:  {len(articles)}")
print(f"  All articles:  {len(all_articles)}")

assert len(all_articles) > 0, "FAIL: No articles fetched at all"
print(f"  PASS: Feed is active ({len(all_articles)} articles available)")

assert all("title" in a and "summary" in a and "url" in a for a in all_articles), \
    "FAIL: Articles missing required fields"
print(f"  PASS: All articles have required fields (title, summary, url)")
