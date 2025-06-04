"""
Sentiment analysis module for financial news articles.

This module provides functions to analyze sentiment using the Loughran-McDonald
lexicon and store results in the database.
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from .preprocess import preprocess_article
from .lexicon import get_lexicon
from ..models import Article, Sentiment
from ..database import get_db

# Import FinBERT functions (with fallback if not available)
try:
    from .finbert import analyze_finbert_sentiment
    FINBERT_AVAILABLE = True
except ImportError:
    FINBERT_AVAILABLE = False


def analyze_article_sentiment(article_text: str) -> Dict:
    """
    Analyze sentiment of an article using Loughran-McDonald lexicon.
    
    Args:
        article_text (str): Raw article text (may contain HTML)
        
    Returns:
        Dict: Sentiment analysis results including score and details
    """
    # Preprocess the article text
    tokens = preprocess_article(article_text)
    
    # Get lexicon and analyze sentiment
    lexicon = get_lexicon()
    sentiment_details = lexicon.get_sentiment_details(tokens)
    
    return {
        "lexicon_score": sentiment_details["sentiment_score"],
        "positive_count": sentiment_details["positive_count"],
        "negative_count": sentiment_details["negative_count"],
        "total_tokens": sentiment_details["total_tokens"],
        "positive_ratio": sentiment_details["positive_ratio"],
        "negative_ratio": sentiment_details["negative_ratio"],
        "sentiment_words_ratio": sentiment_details["sentiment_words_ratio"],
        "preprocessed_tokens": tokens
    }


def calculate_lexicon_score(article_text: str) -> float:
    """
    Calculate just the lexicon sentiment score for an article.
    
    Args:
        article_text (str): Raw article text
        
    Returns:
        float: Sentiment score in range [-1, 1]
    """
    tokens = preprocess_article(article_text)
    lexicon = get_lexicon()
    return lexicon.calculate_sentiment_score(tokens)


def store_article_sentiment(
    db: Session, 
    article_id: str, 
    lexicon_score: float, 
    finbert_score: Optional[float] = None
) -> Sentiment:
    """
    Store sentiment analysis results in the database.
    
    Args:
        db (Session): Database session
        article_id (str): Article ID
        lexicon_score (float): Loughran-McDonald lexicon score
        finbert_score (Optional[float]): FinBERT score (if available)
        
    Returns:
        Sentiment: Created sentiment record
    """
    # Check if sentiment already exists for this article
    existing_sentiment = db.query(Sentiment).filter(
        Sentiment.article_id == article_id
    ).first()
    
    if existing_sentiment:
        # Update existing sentiment
        existing_sentiment.lexicon_score = lexicon_score
        if finbert_score is not None:
            existing_sentiment.finbert_score = finbert_score
        db.commit()
        db.refresh(existing_sentiment)
        return existing_sentiment
    else:
        # Create new sentiment record
        sentiment = Sentiment(
            article_id=article_id,
            lexicon_score=lexicon_score,
            finbert_score=finbert_score
        )
        db.add(sentiment)
        db.commit()
        db.refresh(sentiment)
        return sentiment


def analyze_and_store_sentiment(db: Session, article_id: str) -> Dict:
    """
    Analyze sentiment for an article and store results in database.
    
    Args:
        db (Session): Database session
        article_id (str): Article ID
        
    Returns:
        Dict: Analysis results and stored sentiment record info
        
    Raises:
        ValueError: If article not found
    """
    # Get the article
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise ValueError(f"Article with ID {article_id} not found")
    
    # Analyze sentiment
    sentiment_analysis = analyze_article_sentiment(article.content)
    lexicon_score = sentiment_analysis["lexicon_score"]
    
    # Store in database
    sentiment_record = store_article_sentiment(
        db=db,
        article_id=article_id,
        lexicon_score=lexicon_score
    )
    
    return {
        "article_id": article_id,
        "article_title": article.title,
        "sentiment_id": sentiment_record.id,
        "lexicon_score": lexicon_score,
        "analysis_details": sentiment_analysis
    }


def batch_analyze_articles(db: Session, limit: Optional[int] = None) -> List[Dict]:
    """
    Analyze sentiment for multiple articles that don't have sentiment scores yet.
    
    Args:
        db (Session): Database session
        limit (Optional[int]): Maximum number of articles to process
        
    Returns:
        List[Dict]: List of analysis results
    """
    # Get articles without sentiment analysis
    query = db.query(Article).outerjoin(Sentiment).filter(
        Sentiment.id.is_(None)
    )
    
    if limit:
        query = query.limit(limit)
    
    articles = query.all()
    results = []
    
    for article in articles:
        try:
            result = analyze_and_store_sentiment(db, article.id)
            results.append(result)
        except Exception as e:
            # Log error but continue processing other articles
            error_result = {
                "article_id": article.id,
                "article_title": article.title,
                "error": str(e),
                "status": "failed"
            }
            results.append(error_result)
    
    return results


def get_sentiment_statistics(db: Session) -> Dict:
    """
    Get statistics about sentiment analysis coverage.
    
    Args:
        db (Session): Database session
        
    Returns:
        Dict: Statistics about sentiment analysis
    """
    total_articles = db.query(Article).count()
    analyzed_articles = db.query(Sentiment).count()
    
    if analyzed_articles > 0:
        avg_lexicon_score = db.query(Sentiment.lexicon_score).filter(
            Sentiment.lexicon_score.isnot(None)
        ).all()
        avg_score = sum(score[0] for score in avg_lexicon_score) / len(avg_lexicon_score)
        
        positive_articles = len([s for s in avg_lexicon_score if s[0] > 0])
        negative_articles = len([s for s in avg_lexicon_score if s[0] < 0])
        neutral_articles = len([s for s in avg_lexicon_score if s[0] == 0])
    else:
        avg_score = 0.0
        positive_articles = 0
        negative_articles = 0
        neutral_articles = 0
    
    return {
        "total_articles": total_articles,
        "analyzed_articles": analyzed_articles,
        "unanalyzed_articles": total_articles - analyzed_articles,
        "coverage_percentage": (analyzed_articles / total_articles * 100) if total_articles > 0 else 0.0,
        "average_lexicon_score": avg_score,
        "positive_articles": positive_articles,
        "negative_articles": negative_articles,
        "neutral_articles": neutral_articles
    }


def analyze_article_with_finbert(article_text: str) -> Dict:
    """
    Analyze sentiment using both Loughran-McDonald lexicon and FinBERT.
    
    Args:
        article_text (str): Raw article text (may contain HTML)
        
    Returns:
        Dict: Combined sentiment analysis results
    """
    # Get lexicon analysis
    lexicon_analysis = analyze_article_sentiment(article_text)
    
    result = {
        "lexicon_analysis": lexicon_analysis,
        "finbert_analysis": None,
        "finbert_available": FINBERT_AVAILABLE
    }
    
    # Add FinBERT analysis if available
    if FINBERT_AVAILABLE:
        try:
            # Preprocess text for FinBERT
            tokens = preprocess_article(article_text)
            processed_text = " ".join(tokens)
            
            # Analyze with FinBERT
            finbert_result = analyze_finbert_sentiment(processed_text)
            result["finbert_analysis"] = finbert_result
            
        except Exception as e:
            result["finbert_error"] = str(e)
    
    return result


def store_combined_sentiment(
    db: Session, 
    article_id: str, 
    lexicon_score: float, 
    finbert_score: Optional[float] = None
) -> Sentiment:
    """
    Store both lexicon and FinBERT sentiment scores in the database.
    
    Args:
        db (Session): Database session
        article_id (str): Article ID
        lexicon_score (float): Loughran-McDonald lexicon score
        finbert_score (Optional[float]): FinBERT composite score
        
    Returns:
        Sentiment: Created or updated sentiment record
    """
    return store_article_sentiment(
        db=db,
        article_id=article_id,
        lexicon_score=lexicon_score,
        finbert_score=finbert_score
    )


def analyze_and_store_combined_sentiment(db: Session, article_id: str) -> Dict:
    """
    Analyze sentiment using both methods and store results in database.
    
    Args:
        db (Session): Database session
        article_id (str): Article ID
        
    Returns:
        Dict: Combined analysis results and stored sentiment record info
        
    Raises:
        ValueError: If article not found
    """
    # Get the article
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise ValueError(f"Article with ID {article_id} not found")
    
    # Analyze with both methods
    combined_analysis = analyze_article_with_finbert(article.content)
    
    # Extract scores
    lexicon_score = combined_analysis["lexicon_analysis"]["lexicon_score"]
    finbert_score = None
    
    if combined_analysis["finbert_analysis"]:
        finbert_score = combined_analysis["finbert_analysis"]["composite_score"]
    
    # Store in database
    sentiment_record = store_combined_sentiment(
        db=db,
        article_id=article_id,
        lexicon_score=lexicon_score,
        finbert_score=finbert_score
    )
    
    return {
        "article_id": article_id,
        "article_title": article.title,
        "sentiment_id": sentiment_record.id,
        "lexicon_score": lexicon_score,
        "finbert_score": finbert_score,
        "combined_analysis": combined_analysis
    }


def batch_analyze_with_finbert(db: Session, limit: Optional[int] = None) -> List[Dict]:
    """
    Analyze sentiment for multiple articles using both methods.
    
    Args:
        db (Session): Database session
        limit (Optional[int]): Maximum number of articles to process
        
    Returns:
        List[Dict]: List of combined analysis results
    """
    # Get articles without sentiment analysis
    query = db.query(Article).outerjoin(Sentiment).filter(
        Sentiment.id.is_(None)
    )
    
    if limit:
        query = query.limit(limit)
    
    articles = query.all()
    results = []
    
    for article in articles:
        try:
            result = analyze_and_store_combined_sentiment(db, article.id)
            results.append(result)
        except Exception as e:
            # Log error but continue processing other articles
            error_result = {
                "article_id": article.id,
                "article_title": article.title,
                "error": str(e),
                "status": "failed"
            }
            results.append(error_result)
    
    return results 