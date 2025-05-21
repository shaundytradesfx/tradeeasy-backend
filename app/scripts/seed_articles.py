#!/usr/bin/env python
"""
Database Seed Script for Articles.

This script populates the database with a week's worth of sample articles
for testing and development purposes.
"""

import sys
import logging
import random
from pathlib import Path
from datetime import datetime, timedelta
import uuid
import hashlib

# Add the project root to the path so we can import our app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.database import SessionLocal
from app import models, schemas, crud
# RSS_SOURCES contains the necessary feeds, no need to import ALL_FEEDS
# from app.rss_feeds import ALL_FEEDS

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Set random seed for deterministic output
random.seed(42)

# Sample content templates
ARTICLE_TEMPLATES = {
    "equities": [
        "{company} stock {movement} {percent}% after {event}",
        "Investors react to {company}'s {event}, stock {movement} {percent}%",
        "Analyst upgrades {company} from {old_rating} to {new_rating}",
        "{company} announces {announcement}, shares {movement}",
        "Market watch: {company} {movement} on {event} news",
    ],
    "forex": [
        "{currency_pair} {movement} as {country1} {event}",
        "{currency_pair} hits {timeframe} {high_low} amid {event}",
        "Forex focus: {currency_pair} {movement} {percent}% after {event}",
        "{country1} {economic_indicator} data pushes {currency_pair} {direction}",
        "{currency_pair} volatility increases after {event}",
    ],
    "crypto": [
        "{coin} {movement} {percent}% as {event}",
        "Crypto market: {coin} reaches ${price} amid {event}",
        "{coin} {movement} after {exchange} announces {announcement}",
        "Analysts predict ${price} target for {coin} by {timeframe}",
        "{coin} {movement} following {event}, experts say",
    ],
    "commodities": [
        "{commodity} prices {movement} {percent}% due to {event}",
        "Global {commodity} supply {increases_decreases} amid {event}",
        "{commodity} hits ${price} per {unit} as {event}",
        "{country} {commodity} production {increases_decreases}, prices {movement}",
        "Traders eye {commodity} as {event} concerns grow",
    ],
}

# Data for filling templates
TEMPLATE_DATA = {
    "equities": {
        "company": ["Apple", "Microsoft", "Google", "Amazon", "Tesla", "Facebook", "Netflix", "Walmart", "JPMorgan", "Visa"],
        "movement": ["rises", "falls", "jumps", "plunges", "surges", "declines", "rebounds", "drops"],
        "percent": [0.5, 1.2, 2.3, 3.1, 1.5, 2.7, 0.8, 4.2, 1.9, 3.5],
        "event": ["quarterly earnings", "product launch", "CEO departure", "acquisition", "regulatory approval", "analyst upgrade", "market trends", "sector rotation"],
        "old_rating": ["Hold", "Sell", "Neutral", "Underperform"],
        "new_rating": ["Buy", "Strong Buy", "Outperform", "Overweight"],
        "announcement": ["share buyback", "dividend increase", "cost-cutting measures", "expansion plans", "new partnership", "restructuring"],
    },
    "forex": {
        "currency_pair": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF", "NZD/USD", "EUR/GBP"],
        "movement": ["strengthens", "weakens", "rises", "falls", "appreciates", "depreciates"],
        "country1": ["US", "EU", "UK", "Japan", "Australia", "Canada", "Switzerland", "New Zealand"],
        "event": ["interest rate decision", "economic data release", "political uncertainty", "trade negotiations", "central bank statement", "inflation figures"],
        "timeframe": ["daily", "weekly", "monthly", "yearly", "two-year", "five-year"],
        "high_low": ["high", "low"],
        "economic_indicator": ["GDP", "inflation", "employment", "manufacturing", "retail sales", "consumer confidence"],
        "direction": ["higher", "lower"],
        "percent": [0.2, 0.5, 0.8, 1.1, 0.3, 0.6, 0.9, 1.2],
    },
    "crypto": {
        "coin": ["Bitcoin", "Ethereum", "Ripple", "Litecoin", "Cardano", "Solana", "Polkadot", "Dogecoin", "Avalanche", "Chainlink"],
        "movement": ["rallies", "crashes", "soars", "plummets", "stabilizes", "recovers", "declines", "jumps"],
        "percent": [2.5, 5.3, 8.1, 3.7, 10.2, 4.5, 7.8, 6.2, 9.5, 2.8],
        "event": ["regulatory news", "institutional adoption", "network upgrade", "security incident", "whale movement", "DeFi integration", "market sentiment", "mining difficulty adjustment"],
        "price": [19000, 28000, 35000, 42000, 50000, 1800, 2500, 3200, 0.45, 0.75],
        "exchange": ["Binance", "Coinbase", "Kraken", "FTX", "Gemini", "KuCoin", "Huobi", "OKX"],
        "announcement": ["new listing", "fee structure change", "trading competition", "staking rewards", "regulatory compliance", "liquidity enhancement"],
        "timeframe": ["year-end", "Q1", "Q2", "next bull run", "next halving"],
    },
    "commodities": {
        "commodity": ["gold", "silver", "oil", "natural gas", "wheat", "corn", "copper", "iron ore", "soybeans", "coffee"],
        "movement": ["rises", "falls", "jumps", "plunges", "surges", "declines", "rebounds", "drops"],
        "percent": [1.2, 2.4, 3.6, 0.8, 1.9, 2.7, 3.3, 1.5, 2.2, 2.8],
        "event": ["supply constraints", "demand recovery", "geopolitical tensions", "weather conditions", "inventory data", "production cuts", "economic outlook", "transportation issues"],
        "increases_decreases": ["increases", "decreases", "tightens", "expands", "contracts", "stabilizes"],
        "price": [1800, 22, 75, 3.5, 750, 650, 8500, 120, 1400, 180],
        "unit": ["ounce", "ounce", "barrel", "MMBtu", "bushel", "bushel", "tonne", "tonne", "bushel", "pound"],
        "country": ["US", "China", "Russia", "Brazil", "Australia", "Canada", "Saudi Arabia", "India"],
    },
}

# RSS sources
RSS_SOURCES = {
    "equities": [
        "https://www.investing.com/rss/news_25.rss",
        "https://seekingalpha.com/feed.xml",
        "https://www.marketwatch.com/rss/topstories",
    ],
    "forex": [
        "https://www.investing.com/rss/news_1.rss",
        "https://www.fxstreet.com/rss/news",
        "https://www.dailyfx.com/feeds/market-news",
    ],
    "crypto": [
        "https://cointelegraph.com/rss",
        "https://coindesk.com/arc/outboundfeeds/rss/",
        "https://bitcoinist.com/feed/",
    ],
    "commodities": [
        "https://www.investing.com/rss/news_13.rss",
        "https://www.kitco.com/rss/",
        "https://oilprice.com/rss/main",
    ],
}

def generate_article_content(template, data_dict, min_paragraphs=3, max_paragraphs=8):
    """
    Generate article content based on a template and data dictionary.
    
    Args:
        template: Article title template with placeholders
        data_dict: Dictionary of data to fill the placeholders
        min_paragraphs: Minimum number of paragraphs to generate
        max_paragraphs: Maximum number of paragraphs to generate
        
    Returns:
        Tuple of (title, content)
    """
    # Fill in the template for the title
    title = template
    for key, values in data_dict.items():
        if "{" + key + "}" in title:
            title = title.replace("{" + key + "}", str(random.choice(values)))
    
    # Generate paragraphs for content
    num_paragraphs = random.randint(min_paragraphs, max_paragraphs)
    paragraphs = []
    
    # First paragraph is a summary based on the title
    concluding_phrases = [
        'Analysts are monitoring the situation closely.',
        'Market participants reacted to the news quickly.',
        'This development could have significant implications for the market.',
        'Experts suggest this could be a turning point.',
        'The news came as a surprise to many investors.'
    ]
    paragraphs.append(f"{title}. {random.choice(concluding_phrases)}")
    
    # Generate additional paragraphs
    for _ in range(1, num_paragraphs):
        # Pick random elements from data dict to create sentences
        sentences = []
        for _ in range(random.randint(3, 6)):
            sentence_templates = [
                "The {event} has led to significant changes in {timeframe} projections.",
                "Experts from major institutions are {movement} their forecasts accordingly.",
                "The {announcement} was met with {reaction} from market participants.",
                "This continues the trend seen in recent {timeframe} performance.",
                "Analysts at {company} have noted that this could impact related sectors.",
                "Market sentiment remains {sentiment} despite recent developments.",
                "The {direction} move follows a series of {event} in recent weeks.",
                "Historical data suggests this pattern could {continue_reverse} in coming weeks.",
                "Several factors including {event} and {announcement} contributed to this outcome.",
                "Regulatory considerations remain important as {country1} authorities monitor developments."
            ]
            sentence_template = random.choice(sentence_templates)
            
            # Fill sentence template with random data
            sentence = sentence_template
            for key, values in data_dict.items():
                if "{" + key + "}" in sentence:
                    sentence = sentence.replace("{" + key + "}", str(random.choice(values)))
            
            # Replace any remaining placeholders with generic terms
            sentence = sentence.replace("{reaction}", random.choice(["optimism", "skepticism", "caution", "enthusiasm"]))
            sentence = sentence.replace("{sentiment}", random.choice(["positive", "mixed", "cautious", "optimistic", "bearish", "bullish"]))
            sentence = sentence.replace("{continue_reverse}", random.choice(["continue", "reverse", "stabilize", "accelerate"]))
            
            sentences.append(sentence)
        
        paragraphs.append(" ".join(sentences))
    
    return title, "\n\n".join(paragraphs)

def generate_sample_articles(asset_class, num_articles, start_date, end_date):
    """
    Generate sample articles for a specific asset class within a date range.
    
    Args:
        asset_class: Asset class to generate articles for
        num_articles: Number of articles to generate
        start_date: Start date for articles
        end_date: End date for articles
        
    Returns:
        List of ArticleCreate objects
    """
    articles = []
    
    # Get templates and data for this asset class
    templates = ARTICLE_TEMPLATES[asset_class]
    data_dict = TEMPLATE_DATA[asset_class]
    sources = RSS_SOURCES[asset_class]
    
    # Calculate time delta for even distribution over the date range
    time_delta = (end_date - start_date) / num_articles
    
    for i in range(num_articles):
        # Pick a random template
        template = random.choice(templates)
        
        # Generate article content
        title, content = generate_article_content(template, data_dict)
        
        # Generate a unique URL
        url_hash = hashlib.md5(f"{title}{content}".encode()).hexdigest()[:8]
        source = random.choice(sources)
        domain = source.split("/")[2]
        url = f"https://{domain}/articles/{asset_class}/{url_hash}"
        
        # Calculate published date
        published_at = start_date + (time_delta * i)
        # Add some randomness to the time
        published_at = published_at + timedelta(
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        
        # Generate sample authors
        first_names = ["John", "Sarah", "Michael", "Emma", "David", "Jennifer", "James", "Lisa", "Robert", "Michelle"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia", "Wilson", "Anderson"]
        
        num_authors = random.randint(1, 2)
        authors = ", ".join([f"{random.choice(first_names)} {random.choice(last_names)}" for _ in range(num_authors)])
        
        # Create summary (first 150 chars of content)
        summary = content.split("\n\n")[0][:150] + "..."
        
        # Create article object
        article = schemas.ArticleCreate(
            source=domain,
            title=title,
            content=content,
            url=url,
            published_at=published_at,
            authors=authors,
            summary=summary,
            image_url=f"https://{domain}/images/{asset_class}/{url_hash}.jpg" if random.random() > 0.3 else None
        )
        
        articles.append(article)
    
    return articles

def seed_database():
    """
    Seed the database with sample articles.
    """
    logger.info("Starting database seed for articles...")
    
    # Use fixed dates for deterministic generation
    end_date = datetime(2023, 5, 21)
    start_date = end_date - timedelta(days=7)
    
    logger.info(f"Generating articles from {start_date} to {end_date}")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Generate articles for each asset class
        asset_classes = ["equities", "forex", "crypto", "commodities"]
        
        # Number of articles per asset class
        articles_per_class = {
            "equities": 40,
            "forex": 30,
            "crypto": 35,
            "commodities": 25
        }
        
        total_created = 0
        total_updated = 0
        
        for asset_class in asset_classes:
            logger.info(f"Generating {articles_per_class[asset_class]} articles for {asset_class}")
            
            articles = generate_sample_articles(
                asset_class,
                articles_per_class[asset_class],
                start_date,
                end_date
            )
            
            # Insert articles into database using upsert
            for article in articles:
                db_article, created = crud.upsert_article(db, article)
                if created:
                    total_created += 1
                else:
                    total_updated += 1
            
            logger.info(f"Processed {len(articles)} {asset_class} articles")
        
        logger.info(f"Database seed complete. Created: {total_created}, Updated: {total_updated}")
        
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database() 