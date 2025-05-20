#!/usr/bin/env python
"""
Validate RSS Feeds Script.

This script validates all RSS feeds defined in the rss_feeds.py file.
It tests each feed URL to ensure it provides valid RSS/Atom content
and contains the necessary fields for article extraction.

Usage:
    python -m app.scripts.validate_feeds
"""

import logging
import sys

# Add the project root to the path so we can import our app modules
# This may not be necessary if you run this as a module: python -m app.scripts.validate_feeds
from pathlib import Path

from tabulate import tabulate

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.rss_feeds import ALL_FEEDS, FEED_CATEGORIES
from app.rss_ingest import parse_rss_feed, validate_feed

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """
    Main function to validate all RSS feeds.
    """
    print(f"Validating {len(ALL_FEEDS)} RSS feeds...\n")

    results = []
    valid_count = 0
    invalid_count = 0

    for i, feed_url in enumerate(ALL_FEEDS):
        category = FEED_CATEGORIES.get(feed_url, "unknown")
        is_valid, message = validate_feed(feed_url)

        if is_valid:
            valid_count += 1
            status = "✓ VALID"
            # Try to parse the feed to get entry count
            entries = parse_rss_feed(feed_url)
            entry_count = len(entries)
        else:
            invalid_count += 1
            status = "✗ INVALID"
            entry_count = 0

        results.append([i + 1, feed_url, category, status, entry_count, message])

    # Print results in a table
    headers = ["#", "Feed URL", "Category", "Status", "Entries", "Message"]
    print(tabulate(results, headers=headers, tablefmt="grid"))

    # Print summary
    print(f"\nSummary: {valid_count} valid feeds, {invalid_count} invalid feeds")

    # Print category breakdown
    print("\nCategory Breakdown:")
    category_counts = {}
    for feed_url in ALL_FEEDS:
        category = FEED_CATEGORIES.get(feed_url, "unknown")
        if category not in category_counts:
            category_counts[category] = 0
        category_counts[category] += 1

    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count} feeds")

    # Return appropriate exit code
    return 0 if invalid_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
