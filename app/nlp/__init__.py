"""
NLP module for TradeEasy backend.

This module provides text preprocessing and sentiment analysis capabilities
for financial news articles using the Loughran-McDonald lexicon.
"""

from .preprocess import (
    preprocess_text,
    preprocess_article,
    preprocess_for_sentiment,
    remove_html,
    get_text_statistics,
    get_nlp_model
)

from .lexicon import (
    LoughranMcDonaldLexicon,
    get_lexicon
)

from .sentiment import (
    analyze_article_sentiment,
    calculate_lexicon_score,
    store_article_sentiment,
    analyze_and_store_sentiment,
    batch_analyze_articles,
    get_sentiment_statistics,
    analyze_article_with_finbert,
    store_combined_sentiment,
    analyze_and_store_combined_sentiment,
    batch_analyze_with_finbert
)

from .finbert import (
    FinBERTAnalyzer,
    get_finbert_analyzer,
    analyze_finbert_sentiment,
    analyze_finbert_batch,
    get_finbert_performance_stats,
    benchmark_finbert
)

__all__ = [
    # Preprocessing functions
    "preprocess_text",
    "preprocess_article", 
    "preprocess_for_sentiment",
    "remove_html",
    "get_text_statistics",
    "get_nlp_model",
    
    # Lexicon functions
    "LoughranMcDonaldLexicon",
    "get_lexicon",
    
    # Sentiment analysis functions
    "analyze_article_sentiment",
    "calculate_lexicon_score",
    "store_article_sentiment",
    "analyze_and_store_sentiment",
    "batch_analyze_articles",
    "get_sentiment_statistics",
    "analyze_article_with_finbert",
    "store_combined_sentiment",
    "analyze_and_store_combined_sentiment",
    "batch_analyze_with_finbert",
    
    # FinBERT functions
    "FinBERTAnalyzer",
    "get_finbert_analyzer",
    "analyze_finbert_sentiment",
    "analyze_finbert_batch",
    "get_finbert_performance_stats",
    "benchmark_finbert"
] 