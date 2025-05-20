"""
RSS Feed Ingestion Module for TradeEasy.

This module contains the functionality to fetch, validate, parse and store
RSS feed content from various financial news sources.
"""

import hashlib
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import backoff
import feedparser
import nltk
import requests
from newspaper import Article as NewsArticle
from sqlalchemy.orm import Session

from . import crud, schemas
from .rss_feeds import ALL_FEEDS, FEED_CATEGORIES

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download necessary NLTK resources for article extraction
try:
    nltk.download("punkt", quiet=True)
    nltk.download("stopwords", quiet=True)
    # Create punkt_tab if it doesn't exist
    try:
        # Check if punkt_tab exists first to avoid unnecessary downloads
        nltk.data.find("tokenizers/punkt_tab/english/")
    except LookupError:
        # If punkt_tab doesn't exist, use punkt instead
        punkt_path = nltk.data.find("tokenizers/punkt")
        logger.info("Using punkt instead of punkt_tab for NLP operations")
except Exception as e:
    logger.warning(f"Failed to download NLTK resources: {e}")

# Maximum number of retries for article extraction
MAX_RETRIES = 3
# Timeout for article downloads (seconds)
DOWNLOAD_TIMEOUT = 10


def validate_feed(url: str) -> Tuple[bool, str]:
    """
    Validate a feed URL by checking if it returns valid RSS/Atom content.

    Args:
        url: The URL of the RSS feed to validate

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    try:
        feed = feedparser.parse(url)

        # Check if feed has bozo exception (invalid XML)
        if feed.bozo:
            return False, f"Feed has invalid XML: {feed.bozo_exception}"

        # Check if feed has entries
        if not feed.entries:
            return False, "Feed has no entries"

        # Check if entries have required fields
        required_fields = ["title", "link"]
        sample_entry = feed.entries[0]
        missing_fields = [
            field for field in required_fields if not hasattr(sample_entry, field)
        ]

        if missing_fields:
            return (
                False,
                f"Feed entries missing required fields: {', '.join(missing_fields)}",
            )

        return True, "Feed is valid"

    except Exception as e:
        return False, f"Error validating feed: {str(e)}"


def parse_rss_feed(url: str) -> List[Dict[str, Any]]:
    """
    Parse an RSS feed and return a list of standardized items.

    Args:
        url: The URL of the RSS feed to parse

    Returns:
        List of dictionaries containing parsed feed entries
    """
    logger.info(f"Parsing RSS feed: {url}")
    feed = feedparser.parse(url)

    if feed.bozo:
        logger.error(f"Error parsing RSS feed {url}: {feed.bozo_exception}")
        return []

    standardized_entries = []
    for entry in feed.entries:
        # Skip entries without required fields
        if not hasattr(entry, "link") or not hasattr(entry, "title"):
            continue

        # Create a standardized entry dictionary
        std_entry = {
            "title": entry.title,
            "link": entry.link,
            "published_at": None,
            "source": url,
            "summary": getattr(entry, "summary", ""),
            "asset_class": FEED_CATEGORIES.get(url, "unknown"),
        }

        # Try to get published date in a standardized format
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published_time = time.mktime(entry.published_parsed)
                std_entry["published_at"] = datetime.fromtimestamp(published_time)
            except (TypeError, ValueError) as e:
                logger.warning(f"Could not parse publication date: {e}")

        standardized_entries.append(std_entry)

    logger.info(f"Parsed {len(standardized_entries)} entries from {url}")
    return standardized_entries


# Define a backoff strategy for retries with exponential backoff
@backoff.on_exception(
    backoff.expo,
    (
        requests.exceptions.RequestException,
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
    ),
    max_tries=MAX_RETRIES,
    jitter=backoff.full_jitter,
)
def download_article(url: str) -> NewsArticle:
    """
    Download an article with retries and exception handling.

    Args:
        url: The URL of the article to download

    Returns:
        A newspaper.Article object with the downloaded content

    Raises:
        Various requests exceptions if download fails after retries
    """
    # Create an article object with a realistic user agent to avoid basic blocking
    article = NewsArticle(url, timeout=DOWNLOAD_TIMEOUT)

    # Set a common browser user agent to avoid simple anti-scraping blocks
    article.config.browser_user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

    # Download the article
    article.download()
    return article


def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid.

    Args:
        url: The URL to validate

    Returns:
        True if the URL appears to be valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in the text - replace multiple spaces, tabs, newlines with a single space.

    Args:
        text: The text to normalize

    Returns:
        Normalized text
    """
    # Replace multiple whitespace characters with a single space
    text = re.sub(r"\s+", " ", text)
    # Remove leading/trailing whitespace
    text = text.strip()
    # Normalize paragraphs - ensure a single newline between paragraphs
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text


def extract_article_content(url: str, rss_summary: str = "") -> Dict[str, Any]:
    """
    Extract the full content and metadata of an article from its URL using newspaper3k.
    Falls back to RSS summary if extraction fails.

    Args:
        url: The URL of the article to extract content from
        rss_summary: Optional RSS feed summary to use as fallback

    Returns:
        Dictionary containing article text, publish date, authors, and other metadata
    """
    article_data = {
        "text": "",
        "authors": [],
        "publish_date": None,
        "top_image": "",
        "keywords": [],
        "summary": "",
        "error": None,
    }

    if not is_valid_url(url):
        logger.error(f"Invalid URL: {url}")
        article_data["error"] = "Invalid URL format"
        # Use RSS summary as fallback if available
        if rss_summary:
            article_data["text"] = normalize_whitespace(rss_summary)
            article_data["summary"] = (
                article_data["text"][:200] + "..."
                if len(article_data["text"]) > 200
                else article_data["text"]
            )
            article_data["error"] = "Using RSS summary as fallback (invalid URL)"
            logger.info(f"Using RSS summary as fallback for invalid URL: {url}")
        return article_data

    # Special handling for Yahoo Finance URLs which often block scrapers
    original_url = url
    parsed_url = urlparse(url)
    if "finance.yahoo.com" in parsed_url.netloc:
        # For Yahoo Finance, we need to clean the URL
        url = f"https://{parsed_url.netloc}{parsed_url.path}"
        logger.info(f"Modified Yahoo Finance URL from {original_url} to {url}")

    try:
        # Download with retry mechanism
        article = download_article(url)

        # Parse the article
        article.parse()

        # Extract basic text content
        article_data["text"] = normalize_whitespace(article.text)

        # Get and process authors
        if article.authors:
            try:
                authors_list = list(article.authors)
                if authors_list and len(authors_list) > 0:
                    article_data['authors'] = authors_list
            except Exception as e:
                logger.warning(f"Failed to extract authors: {e}")
                
        # Extract summary if available
        if hasattr(article, 'summary') and article.summary:
            try:
                summary_text = article.summary
                if summary_text and len(summary_text) > 3:
                    # Clean up and normalize the summary
                    article_data['summary'] = normalize_whitespace(summary_text)
            except Exception as e:
                logger.warning(f"Failed to extract summary: {e}")

        # Extract keywords if available
        if hasattr(article, 'keywords') and article.keywords:
            try:
                keywords_list = list(article.keywords)
                if keywords_list and len(keywords_list) > 0:
                    article_data['keywords'] = keywords_list
            except Exception as e:
                logger.warning(f"Failed to extract keywords: {e}")

        # Extract publish date if available
        if article.publish_date:
            article_data["publish_date"] = article.publish_date

        # Extract top image if available
        if hasattr(article, 'top_image') and article.top_image:
            try:
                image_url = article.top_image
                if image_url and len(image_url) > 5:  # Basic URL length check
                    article_data['top_image'] = image_url
            except Exception as e:
                logger.warning(f"Failed to extract top image: {e}")

        # Natural language processing for additional metadata
        try:
            # Skip NLP if text is very short
            if len(article_data["text"]) > 100:
                article.nlp()
                article_data["keywords"] = article.keywords
                article_data["summary"] = article.summary
            else:
                # For short articles, use the text as summary
                article_data["summary"] = article_data["text"]
        except Exception as e:
            logger.warning(f"NLP processing failed for {url}: {e}")
            # Create a basic summary if NLP fails
            if article_data["text"]:
                article_data["summary"] = (
                    article_data["text"][:200] + "..."
                    if len(article_data["text"]) > 200
                    else article_data["text"]
                )

        # Log successful extraction
        logger.info(
            f"Successfully extracted article from {original_url}: {len(article_data['text'])} chars"
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error extracting content from {url}: {error_msg}")
        article_data["error"] = f"Extraction error: {error_msg}"

        # Use RSS summary as fallback if available
        if rss_summary:
            article_data["text"] = normalize_whitespace(rss_summary)
            article_data["summary"] = (
                article_data["text"][:200] + "..."
                if len(article_data["text"]) > 200
                else article_data["text"]
            )
            article_data["error"] = f"Using RSS summary as fallback ({error_msg})"
            logger.info(
                f"Using RSS summary as fallback for {url} due to extraction error"
            )

    # If we still don't have any text content and have RSS summary, use it
    if not article_data["text"] and rss_summary:
        article_data["text"] = normalize_whitespace(rss_summary)
        article_data["summary"] = (
            article_data["text"][:200] + "..."
            if len(article_data["text"]) > 200
            else article_data["text"]
        )
        if not article_data["error"]:
            article_data[
                "error"
            ] = "Using RSS summary as fallback (no content extracted)"
        logger.info(f"Using RSS summary as fallback for {url} due to no content")

    return article_data


def calculate_content_hash(content: str) -> str:
    """
    Calculate a hash of the article content for deduplication.

    Args:
        content: The article content to hash

    Returns:
        A SHA-256 hash of the content
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def ingest_feed(db: Session, feed_url: str) -> Tuple[int, int, int]:
    """
    Ingest a single RSS feed, parse entries, fetch full content and store in database.

    Args:
        db: SQLAlchemy database session
        feed_url: URL of the RSS feed to ingest

    Returns:
        Tuple of (entries_processed, articles_created, errors)
    """
    entries_processed = 0
    articles_created = 0
    errors = 0

    try:
        # Parse RSS feed
        entries = parse_rss_feed(feed_url)

        for entry in entries:
            entries_processed += 1

            try:
                # Skip if no link
                if "link" not in entry:
                    continue

                # Check if article already exists
                existing_article = crud.get_article_by_url(db, entry["link"])
                if existing_article:
                    logger.info(f"Article already exists: {entry['title']}")
                    continue

                # Extract content and metadata
                article_data = extract_article_content(
                    entry["link"], entry.get("summary", "")
                )

                # Skip if extraction failed
                if not article_data["text"]:
                    logger.warning(
                        f"Could not extract content for: {entry['title']} - {article_data['error']}"
                    )
                    errors += 1
                    continue

                # Use article publish date if available, otherwise use RSS feed date or current time
                published_at = article_data.get("publish_date") or entry.get(
                    "published_at", datetime.utcnow()
                )

                # Create article
                article_data = schemas.ArticleCreate(
                    source=entry.get("source", feed_url),
                    title=entry.get("title", "No title"),
                    content=article_data["text"],
                    url=entry["link"],
                    published_at=published_at,
                    authors=", ".join(article_data["authors"])
                    if article_data["authors"]
                    else None,
                    image_url=article_data["top_image"]
                    if article_data["top_image"]
                    else None,
                    summary=article_data["summary"]
                    if article_data["summary"]
                    else entry.get("summary", ""),
                )

                new_article = crud.create_article(db, article_data)
                articles_created += 1
                logger.info(f"Created new article: {new_article.title}")

            except Exception as e:
                logger.error(
                    f"Error processing entry {entry.get('title', 'unknown')}: {e}"
                )
                errors += 1

    except Exception as e:
        logger.error(f"Error processing RSS feed {feed_url}: {e}")
        errors += 1

    return (entries_processed, articles_created, errors)


def ingest_all_feeds(db: Session) -> Dict[str, Any]:
    """
    Ingest all RSS feeds and return statistics.

    Args:
        db: SQLAlchemy database session

    Returns:
        Dictionary with ingestion statistics
    """
    start_time = time.time()

    total_feeds = len(ALL_FEEDS)
    total_entries = 0
    total_articles = 0
    total_errors = 0
    feeds_with_errors = 0

    for feed_url in ALL_FEEDS:
        try:
            # Validate feed before attempting to ingest
            is_valid, error_message = validate_feed(feed_url)
            if not is_valid:
                logger.error(f"Skipping invalid feed {feed_url}: {error_message}")
                feeds_with_errors += 1
                continue

            entries, articles, errors = ingest_feed(db, feed_url)

            total_entries += entries
            total_articles += articles
            total_errors += errors

            if errors > 0:
                feeds_with_errors += 1

        except Exception as e:
            logger.error(f"Unexpected error processing feed {feed_url}: {e}")
            feeds_with_errors += 1

    end_time = time.time()
    processing_time = end_time - start_time

    stats = {
        "total_feeds_processed": total_feeds,
        "feeds_with_errors": feeds_with_errors,
        "total_entries_processed": total_entries,
        "articles_created": total_articles,
        "errors": total_errors,
        "processing_time_seconds": processing_time,
    }

    logger.info(f"RSS ingestion complete. Stats: {stats}")
    return stats
