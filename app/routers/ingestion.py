import os
import logging
import feedparser
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from newspaper import Article as NewsArticle

from ..database import get_db
from .. import crud, models, schemas

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/ingestion",
    tags=["ingestion"],
    responses={404: {"description": "Not found"}},
)

# Get RSS sources from environment variable or use default for development
RSS_SOURCES = os.getenv("RSS_SOURCES", "https://finance.yahoo.com/news/rssindex").split(",")


def parse_rss_feed(url: str) -> List[Dict[str, Any]]:
    """
    Parse an RSS feed and return a list of items.
    """
    logger.info(f"Parsing RSS feed: {url}")
    feed = feedparser.parse(url)
    
    if feed.bozo:
        logger.error(f"Error parsing RSS feed {url}: {feed.bozo_exception}")
        return []
    
    return feed.entries


def extract_article_content(url: str) -> str:
    """
    Extract the full content of an article from its URL using newspaper3k.
    """
    try:
        article = NewsArticle(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {e}")
        return ""


def ingest_rss_feeds():
    """
    Background task to ingest all RSS feeds.
    """
    db = next(get_db())
    
    for source_url in RSS_SOURCES:
        if not source_url:
            continue
            
        try:
            # Parse RSS feed
            entries = parse_rss_feed(source_url)
            
            # Process each entry
            for entry in entries:
                # Skip if no link
                if not hasattr(entry, 'link'):
                    continue
                    
                # Check if article already exists
                existing_article = crud.get_article_by_url(db, entry.link)
                if existing_article:
                    logger.info(f"Article already exists: {entry.title}")
                    continue
                
                # Extract content
                content = extract_article_content(entry.link)
                if not content:
                    logger.warning(f"Could not extract content for: {entry.title}")
                    continue
                
                # Create article
                published_at = datetime.fromtimestamp(entry.published_parsed.timestamp()) if hasattr(entry, 'published_parsed') else datetime.utcnow()
                
                article_data = schemas.ArticleCreate(
                    source=entry.get('source', source_url),
                    title=entry.get('title', 'No title'),
                    content=content,
                    url=entry.link,
                    published_at=published_at
                )
                
                new_article = crud.create_article(db, article_data)
                logger.info(f"Created new article: {new_article.title}")
                
        except Exception as e:
            logger.error(f"Error processing RSS feed {source_url}: {e}")


@router.post("/rss", response_model=Dict[str, str])
async def trigger_rss_ingestion(background_tasks: BackgroundTasks):
    """
    Manually trigger the RSS ingestion process.
    """
    background_tasks.add_task(ingest_rss_feeds)
    return {"status": "RSS ingestion started"}


@router.get("/sources", response_model=List[str])
async def get_rss_sources():
    """
    Get the list of RSS sources being monitored.
    """
    return [source for source in RSS_SOURCES if source]


# For debugging purposes
if __name__ == "__main__":
    for source in RSS_SOURCES:
        print(f"Source: {source}")
        entries = parse_rss_feed(source)
        for entry in entries:
            print(f"  - {entry.get('title', 'No title')}")
