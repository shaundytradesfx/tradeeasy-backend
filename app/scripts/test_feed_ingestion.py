#!/usr/bin/env python
"""
Test RSS Feed Ingestion Script.

This script tests ingesting articles from an RSS feed with the enhanced extraction.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import feedparser

# Add the project root to the path so we can import our app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.database import SessionLocal
from app.rss_feeds import ALL_FEEDS
from app.rss_ingest import (
    extract_article_content,
    ingest_feed,
    parse_rss_feed,
    validate_feed,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_extract_article():
    """Test extracting articles from various feeds."""
    # Test with different RSS feeds
    feeds_to_test = ALL_FEEDS

    results = []
    successful_extractions = 0
    failed_extractions = 0
    fallback_used = 0

    for feed_url in feeds_to_test:
        print(f"\nTesting feed: {feed_url}")
        feed = feedparser.parse(feed_url)

        if not feed.entries:
            print(f"  No entries found in feed.")
            continue

        # Test with the first entry
        entry = feed.entries[0]
        print(f"  Testing article: {entry.title}")

        # Extract article content
        article_data = extract_article_content(
            entry.link, getattr(entry, "summary", "")
        )

        # Determine result
        if article_data["text"]:
            if article_data["error"] and "fallback" in article_data["error"]:
                print(f"  Extracted using fallback: {len(article_data['text'])} chars")
                print(f"  Error: {article_data['error']}")
                fallback_used += 1
            else:
                print(f"  Successfully extracted: {len(article_data['text'])} chars")
                successful_extractions += 1
        else:
            print(f"  Failed to extract content: {article_data['error']}")
            failed_extractions += 1

    # Print summary
    print("\n============= SUMMARY =============")
    print(f"Feeds tested: {len(feeds_to_test)}")
    print(f"Successful extractions: {successful_extractions}")
    print(f"Failed extractions: {failed_extractions}")
    print(f"Fallback mechanism used: {fallback_used}")
    print("==================================")


def test_feed_ingestion():
    """Test feed ingestion with database storage."""
    # Setup DB session
    db = SessionLocal()
    
    try:
        # Test all feeds
        for feed_category, feed_list in ALL_FEEDS.items():
            for feed_index, feed_url in enumerate(feed_list):
                # Skip after first feed in each category to save time
                if feed_index > 0:
                    continue
                    
                logger.info(f"Testing ingestion of {feed_url}")
                
                # Perform ingestion
                entries_processed, articles_created, errors = ingest_feed(db, feed_url)
                
                logger.info(f"Feed: {feed_url}")
                logger.info(f"  - Entries processed: {entries_processed}")
                logger.info(f"  - Articles created: {articles_created}")
                logger.info(f"  - Errors: {errors}")
    finally:
        db.close()


def main():
    """Main entry point for the test script."""
    logger.info("Starting RSS Feed Ingestion Test")
    
    # Test article extraction
    test_extract_article()
    
    # Test feed ingestion (uncomment when ready to test DB storage)
    # test_feed_ingestion()
    
    logger.info("Testing complete")


if __name__ == "__main__":
    main()
