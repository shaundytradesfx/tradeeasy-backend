"""
RSS Feed Ingestion Module for TradeEasy.

This module contains the functionality to fetch, validate, parse and store
RSS feed content from various financial news sources with comprehensive
metrics tracking and enhanced error handling.
"""

import hashlib
import logging
import re
import time
from datetime import datetime, timedelta
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
from .metrics import metrics
from . import models

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global flag to track NLTK resource availability
NLTK_RESOURCES_AVAILABLE = False

# Download necessary NLTK resources for article extraction
try:
    # Download core tokenization resources
    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)  # Explicitly download punkt_tab
    nltk.download("stopwords", quiet=True)
    
    # Verify resources are available
    try:
        nltk.data.find("tokenizers/punkt_tab/english/")
        NLTK_RESOURCES_AVAILABLE = True
        logger.info("NLTK resources successfully downloaded and verified")
    except LookupError:
        try:
            # Fallback to punkt if punkt_tab is not available
            nltk.data.find("tokenizers/punkt")
            NLTK_RESOURCES_AVAILABLE = True
            logger.info("Using punkt tokenizer (punkt_tab not available)")
        except LookupError:
            logger.warning("Neither punkt_tab nor punkt tokenizers are available - NLP features will be limited")
            NLTK_RESOURCES_AVAILABLE = False
            
except Exception as e:
    logger.warning(f"Failed to download NLTK resources: {e} - NLP features will be limited")
    NLTK_RESOURCES_AVAILABLE = False

# Enhanced retry configuration
MAX_RETRIES = 5
DOWNLOAD_TIMEOUT = 15
BASE_DELAY = 1.0  # Base delay for exponential backoff
MAX_DELAY = 60.0  # Maximum delay between retries


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
            metrics.record_error('feed_validation_error', FEED_CATEGORIES.get(url, 'unknown'))
            return False, f"Feed has invalid XML: {feed.bozo_exception}"

        # Check if feed has entries
        if not feed.entries:
            metrics.record_error('feed_no_entries', FEED_CATEGORIES.get(url, 'unknown'))
            return False, "Feed has no entries"

        # Check if entries have required fields
        required_fields = ["title", "link"]
        sample_entry = feed.entries[0]
        missing_fields = [
            field for field in required_fields if not hasattr(sample_entry, field)
        ]

        if missing_fields:
            metrics.record_error('feed_missing_fields', FEED_CATEGORIES.get(url, 'unknown'))
            return (
                False,
                f"Feed entries missing required fields: {', '.join(missing_fields)}",
            )

        return True, "Feed is valid"

    except Exception as e:
        metrics.record_error('feed_validation_exception', FEED_CATEGORIES.get(url, 'unknown'))
        return False, f"Error validating feed: {str(e)}"


def parse_rss_feed(url: str) -> List[Dict[str, Any]]:
    """
    Parse an RSS feed and return a list of standardized items.

    Args:
        url: The URL of the RSS feed to parse

    Returns:
        List of dictionaries containing parsed feed entries
    """
    start_time = time.time()
    category = FEED_CATEGORIES.get(url, 'unknown')
    
    logger.info(f"Parsing RSS feed: {url} (category: {category})")
    
    try:
        feed = feedparser.parse(url)

        if feed.bozo:
            error_msg = f"Error parsing RSS feed {url}: {feed.bozo_exception}"
            logger.error(error_msg)
            metrics.record_error('feed_parse_error', category)
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
                "asset_class": category,
            }

            # Try to get published date in a standardized format
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published_time = time.mktime(entry.published_parsed)
                    std_entry["published_at"] = datetime.fromtimestamp(published_time)
                except (TypeError, ValueError) as e:
                    logger.warning(f"Could not parse publication date: {e}")

            standardized_entries.append(std_entry)

        duration = time.time() - start_time
        logger.info(f"Parsed {len(standardized_entries)} entries from {url} in {duration:.2f}s")
        
        # Record metrics
        metrics.record_entries_processed(len(standardized_entries), category)
        
        return standardized_entries
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Exception parsing RSS feed {url}: {e}")
        metrics.record_error('feed_parse_exception', category)
        return []


# Enhanced backoff strategy with better error handling
@backoff.on_exception(
    backoff.expo,
    (
        requests.exceptions.RequestException,
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
    ),
    max_tries=MAX_RETRIES,
    base=BASE_DELAY,
    max_value=MAX_DELAY,
    jitter=backoff.full_jitter,
    on_backoff=lambda details: logger.warning(
        f"Article download retry {details['tries']}/{MAX_RETRIES} for {details.get('args', ['unknown'])[0] if details.get('args') else 'unknown'}: {details['exception']}"
    ),
    on_giveup=lambda details: logger.error(
        f"Article download failed after {details['tries']} attempts for {details.get('args', ['unknown'])[0] if details.get('args') else 'unknown'}: {details['exception']}"
    )
)
def download_article(url: str) -> NewsArticle:
    """
    Download an article with enhanced retries and exception handling.

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
    return re.sub(r'\s+', ' ', text).strip()


def extract_article_content(url: str, rss_summary: str = "") -> Dict[str, Any]:
    """
    Extract full article content from a URL with enhanced error handling and metrics.

    Args:
        url: The URL of the article to extract
        rss_summary: Fallback summary from RSS feed

    Returns:
        Dictionary containing extracted article data and metadata
    """
    start_time = time.time()
    retry_count = 0
    
    # Initialize return data structure
    article_data = {
        "text": "",
        "authors": [],
        "publish_date": None,
        "top_image": None,
        "keywords": [],
        "summary": "",
        "error": None,
    }

    # Validate URL first
    if not is_valid_url(url):
        error_msg = f"Invalid URL format: {url}"
        logger.warning(error_msg)
        article_data["error"] = error_msg
        metrics.record_error('invalid_url', 'unknown')
        return article_data

    original_url = url
    logger.info(f"Extracting content from: {url}")

    try:
        # Download article with retries
        article = download_article(url)
        
        # Parse the article
        article.parse()

        # Extract text content
        if article.text:
            article_data["text"] = normalize_whitespace(article.text)

        # Extract metadata
        if article.authors:
            article_data["authors"] = article.authors

        if article.publish_date:
            article_data["publish_date"] = article.publish_date

        if article.top_image:
            article_data["top_image"] = article.top_image

        # Try to get keywords and summary (these might fail)
        try:
            if hasattr(article, 'nlp') and callable(article.nlp) and NLTK_RESOURCES_AVAILABLE:
                # Only run NLP if we have substantial content and NLTK resources are available
                if len(article_data["text"]) > 100:
                    article.nlp()
                    if article.keywords:
                        article_data["keywords"] = article.keywords
                    if article.summary:
                        article_data["summary"] = normalize_whitespace(article.summary)
            elif not NLTK_RESOURCES_AVAILABLE:
                # Skip NLP processing silently if resources are not available
                # This prevents spam warnings about missing punkt_tab
                pass
        except Exception as nlp_error:
            # Only log NLP errors if they're not related to missing NLTK resources
            error_str = str(nlp_error).lower()
            if "punkt_tab" not in error_str and "punkt" not in error_str:
                logger.warning(f"NLP processing failed for {url}: {nlp_error}")
            # Silently skip punkt-related errors to avoid spam

        # If no summary from NLP, create one from the text
        if not article_data["summary"] and article_data["text"]:
            if len(article_data["text"]) > 200:
                article_data["summary"] = (
                    article_data["text"][:200] + "..."
                    if len(article_data["text"]) > 200
                    else article_data["text"]
                )

        # Log successful extraction
        duration = time.time() - start_time
        content_length = len(article_data["text"])
        
        logger.info(
            f"Successfully extracted article from {original_url}: {content_length} chars in {duration:.2f}s"
        )
        
        # Record metrics
        metrics.record_article_extraction(duration, content_length, retry_count)

    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)
        logger.error(f"Error extracting content from {url}: {error_msg}")
        article_data["error"] = f"Extraction error: {error_msg}"
        
        # Record error metrics
        if "timeout" in error_msg.lower():
            metrics.record_error('article_timeout', 'unknown')
        elif "connection" in error_msg.lower():
            metrics.record_error('article_connection_error', 'unknown')
        else:
            metrics.record_error('article_extraction_error', 'unknown')

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
    start_time = time.time()
    category = FEED_CATEGORIES.get(feed_url, 'unknown')
    
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

                # Check if article already exists (with timing)
                db_start = time.time()
                existing_article = crud.get_article_by_url(db, entry["link"])
                db_duration = time.time() - db_start
                metrics.record_database_operation('check_duplicate', db_duration)
                
                if existing_article:
                    logger.debug(f"Article already exists: {entry['title']}")
                    continue

                # Extract content and metadata
                article_data = extract_article_content(
                    entry["link"], entry.get("summary", "")
                )

                # Skip if extraction failed
                if not article_data["text"]:
                    logger.warning(
                        f"Could not extract content for: {entry['title']} - {article_data.get('error', 'Unknown error')}"
                    )
                    errors += 1
                    metrics.record_error('content_extraction_failed', category)
                    continue

                # Use article publish date if available, otherwise use RSS feed date or current time
                published_at = article_data.get("publish_date") or entry.get(
                    "published_at", datetime.utcnow()
                )

                # Create article
                article_create_data = schemas.ArticleCreate(
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

                # Create article in database (with timing)
                db_start = time.time()
                new_article = crud.create_article(db, article_create_data)
                db_duration = time.time() - db_start
                metrics.record_database_operation('create_article', db_duration)
                
                articles_created += 1
                logger.info(f"Created new article: {new_article.title}")

            except Exception as e:
                logger.error(
                    f"Error processing entry {entry.get('title', 'unknown')}: {e}"
                )
                errors += 1
                metrics.record_error('entry_processing_error', category)

        # Record feed processing metrics
        duration = time.time() - start_time
        status = 'error' if errors > 0 else 'success'
        metrics.record_feed_processed(status, category)
        metrics.record_articles_created(articles_created, category)
        
        logger.info(
            f"Feed {feed_url} processed in {duration:.2f}s: "
            f"{entries_processed} entries, {articles_created} articles, {errors} errors"
        )

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Error processing RSS feed {feed_url}: {e}")
        errors += 1
        metrics.record_error('feed_processing_error', category)
        metrics.record_feed_processed('error', category)

    return (entries_processed, articles_created, errors)


def ingest_all_feeds(db: Session) -> Dict[str, Any]:
    """
    Ingest all RSS feeds and return comprehensive statistics.

    Args:
        db: SQLAlchemy database session

    Returns:
        Dictionary with detailed ingestion statistics
    """
    # Start metrics tracking
    metrics.start_ingestion_run()
    
    total_feeds = len(ALL_FEEDS)
    total_entries = 0
    total_articles = 0
    total_errors = 0
    feeds_with_errors = 0
    feed_results = []

    logger.info(f"Starting ingestion of {total_feeds} RSS feeds")

    for feed_url in ALL_FEEDS:
        feed_start_time = time.time()
        category = FEED_CATEGORIES.get(feed_url, 'unknown')
        
        try:
            # Validate feed before attempting to ingest
            is_valid, error_message = validate_feed(feed_url)
            if not is_valid:
                logger.error(f"Skipping invalid feed {feed_url}: {error_message}")
                feeds_with_errors += 1
                metrics.record_feed_processed('invalid', category)
                feed_results.append({
                    'url': feed_url,
                    'category': category,
                    'status': 'invalid',
                    'error': error_message,
                    'entries': 0,
                    'articles': 0,
                    'errors': 1,
                    'duration': time.time() - feed_start_time
                })
                continue

            entries, articles, errors = ingest_feed(db, feed_url)

            total_entries += entries
            total_articles += articles
            total_errors += errors

            if errors > 0:
                feeds_with_errors += 1

            feed_duration = time.time() - feed_start_time
            feed_results.append({
                'url': feed_url,
                'category': category,
                'status': 'success' if errors == 0 else 'partial_success',
                'entries': entries,
                'articles': articles,
                'errors': errors,
                'duration': feed_duration
            })

        except Exception as e:
            feed_duration = time.time() - feed_start_time
            logger.error(f"Unexpected error processing feed {feed_url}: {e}")
            feeds_with_errors += 1
            metrics.record_error('unexpected_feed_error', category)
            metrics.record_feed_processed('error', category)
            
            feed_results.append({
                'url': feed_url,
                'category': category,
                'status': 'error',
                'error': str(e),
                'entries': 0,
                'articles': 0,
                'errors': 1,
                'duration': feed_duration
            })

    # Finish metrics tracking
    final_stats = metrics.finish_ingestion_run(total_feeds)

    # Compile comprehensive statistics
    stats = {
        "total_feeds_processed": total_feeds,
        "feeds_with_errors": feeds_with_errors,
        "feeds_successful": total_feeds - feeds_with_errors,
        "total_entries_processed": total_entries,
        "articles_created": total_articles,
        "total_errors": total_errors,
        "processing_time_seconds": final_stats.get('duration', 0),
        "success_rate": (total_feeds - feeds_with_errors) / total_feeds if total_feeds > 0 else 0,
        "articles_per_feed": total_articles / total_feeds if total_feeds > 0 else 0,
        "feed_results": feed_results,
        "error_breakdown": final_stats.get('error_breakdown', {}),
        "timestamp": datetime.utcnow().isoformat()
    }

    logger.info(f"RSS ingestion complete. Comprehensive stats: {stats}")
    return stats


def ingest_with_alert_checking(db: Session) -> Dict[str, Any]:
    """
    Ingest all RSS feeds and check for alert triggers based on sentiment.
    
    This function performs the full ingestion process and then checks
    if any sentiment scores cross user-defined alert thresholds.
    
    Args:
        db: SQLAlchemy database session
        
    Returns:
        Dictionary with ingestion stats and alert information
    """
    logger.info("Starting RSS ingestion with alert checking")
    
    # Step 1: Perform normal RSS ingestion
    ingestion_stats = ingest_all_feeds(db)
    
    # Step 2: Check for alert triggers if articles were created
    alert_stats = {
        "alerts_checked": 0,
        "alerts_triggered": 0,
        "triggered_alert_ids": [],
        "asset_scores": {}
    }
    
    if ingestion_stats["articles_created"] > 0:
        try:
            logger.info("Checking for alert triggers after ingestion")
            
            # Get all assets that have recent sentiment data
            from .nlp.sentiment_analysis import analyze_sentiment
            
            # Get recently created articles (from this ingestion run)
            recent_articles = (
                db.query(models.Article)
                .filter(models.Article.published_at >= datetime.utcnow() - timedelta(hours=2))
                .order_by(models.Article.published_at.desc())
                .limit(100)  # Limit to recent articles
                .all()
            )
            
            # Analyze sentiment for articles that don't have sentiment data yet
            for article in recent_articles:
                try:
                    # Check if sentiment already exists
                    existing_sentiment = crud.get_sentiments_by_article(db, article.id)
                    if existing_sentiment:
                        continue
                    
                    # Analyze sentiment for new article
                    sentiment_result = analyze_sentiment(article.content)
                    
                    # Create sentiment record
                    sentiment_data = schemas.SentimentCreate(
                        article_id=article.id,
                        lexicon_score=sentiment_result.get("lexicon_score"),
                        finbert_score=sentiment_result.get("finbert_score")
                    )
                    
                    crud.create_sentiment(db, sentiment_data)
                    
                except Exception as e:
                    logger.error(f"Error analyzing sentiment for article {article.id}: {e}")
                    continue
            
            # Get latest sentiment scores for each asset
            asset_symbols = ["AAPL", "MSFT", "BTC", "ETH", "EUR/USD", "GOLD"]  # Common assets
            
            for symbol in asset_symbols:
                try:
                    # Get latest sentiment for this asset
                    latest_sentiment = crud.get_latest_sentiment_by_asset_symbol(db, symbol)
                    
                    if latest_sentiment and latest_sentiment.finbert_score is not None:
                        sentiment_score = latest_sentiment.finbert_score
                        alert_stats["asset_scores"][symbol] = sentiment_score
                        
                        # Check for alert triggers
                        triggered_ids = crud.check_and_trigger_alerts(db, symbol, sentiment_score)
                        
                        if triggered_ids:
                            alert_stats["alerts_triggered"] += len(triggered_ids)
                            alert_stats["triggered_alert_ids"].extend(triggered_ids)
                            logger.info(f"Triggered {len(triggered_ids)} alerts for {symbol} (score: {sentiment_score:.3f})")
                        
                        alert_stats["alerts_checked"] += 1
                        
                except Exception as e:
                    logger.error(f"Error checking alerts for {symbol}: {e}")
                    continue
            
            logger.info(f"Alert checking complete: {alert_stats['alerts_triggered']} alerts triggered")
            
        except Exception as e:
            logger.error(f"Error during alert checking: {e}")
            alert_stats["error"] = str(e)
    
    # Combine stats
    combined_stats = {
        **ingestion_stats,
        "alert_checking": alert_stats,
        "process_type": "ingestion_with_alerts"
    }
    
    return combined_stats


def process_asset_sentiment_alerts(db: Session, asset_symbol: str, sentiment_score: float) -> Dict[str, Any]:
    """
    Process alerts for a specific asset and sentiment score.
    
    This function can be called directly to test alert triggering
    or as part of the ingestion process.
    
    Args:
        db: Database session
        asset_symbol: Symbol of the asset (e.g., 'AAPL', 'BTC')
        sentiment_score: Current sentiment score (-1.0 to 1.0)
        
    Returns:
        Dictionary with alert processing results
    """
    from . import crud
    
    try:
        logger.info(f"Processing alerts for {asset_symbol} with sentiment score {sentiment_score:.3f}")
        
        # Check and trigger alerts
        triggered_alert_ids = crud.check_and_trigger_alerts(db, asset_symbol, sentiment_score)
        
        # Get details of triggered alerts
        triggered_alerts = []
        for alert_id in triggered_alert_ids:
            alert = crud.get_alert(db, alert_id)
            if alert:
                triggered_alerts.append({
                    "alert_id": str(alert_id),
                    "user_id": str(alert.user_id),
                    "threshold": alert.threshold,
                    "direction": alert.direction,
                    "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None
                })
        
        result = {
            "asset_symbol": asset_symbol,
            "sentiment_score": sentiment_score,
            "alerts_triggered": len(triggered_alert_ids),
            "triggered_alerts": triggered_alerts,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if triggered_alert_ids:
            logger.info(f"Successfully triggered {len(triggered_alert_ids)} alerts for {asset_symbol}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing alerts for {asset_symbol}: {e}")
        return {
            "asset_symbol": asset_symbol,
            "sentiment_score": sentiment_score,
            "alerts_triggered": 0,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# Additional imports needed for alert functionality
from . import models, schemas
from datetime import datetime, timedelta
 