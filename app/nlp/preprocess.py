"""
Text preprocessing module for financial news articles.

This module provides functions to clean and preprocess text data for sentiment analysis,
including HTML removal, tokenization, and filtering using spaCy.
"""

import re
import string
from typing import List, Optional
import spacy
from bs4 import BeautifulSoup


# Global spaCy model instance (loaded once for efficiency)
_nlp_model: Optional[spacy.Language] = None


def get_nlp_model() -> spacy.Language:
    """
    Get or load the spaCy model instance.
    
    Returns:
        spacy.Language: The loaded spaCy model
        
    Raises:
        OSError: If the spaCy model cannot be loaded
    """
    global _nlp_model
    if _nlp_model is None:
        try:
            _nlp_model = spacy.load("en_core_web_sm")
        except OSError:
            raise OSError(
                "spaCy model 'en_core_web_sm' not found. "
                "Please install it with: python -m spacy download en_core_web_sm"
            )
    return _nlp_model


def remove_html(text: str) -> str:
    """
    Remove HTML tags from text using BeautifulSoup.
    
    Args:
        text (str): Input text that may contain HTML tags
        
    Returns:
        str: Text with HTML tags removed
    """
    if not text:
        return ""
    
    # Parse HTML and extract text
    soup = BeautifulSoup(text, 'html.parser')
    return soup.get_text()


def remove_punctuation(text: str) -> str:
    """
    Remove punctuation from text.
    
    Args:
        text (str): Input text
        
    Returns:
        str: Text with punctuation removed
    """
    if not text:
        return ""
    
    # Create translation table to remove punctuation
    translator = str.maketrans('', '', string.punctuation)
    return text.translate(translator)


def preprocess_text(
    text: str,
    remove_html_tags: bool = True,
    to_lowercase: bool = True,
    remove_punct: bool = True,
    remove_stop_words: bool = True,
    remove_non_alpha: bool = True,
    min_token_length: int = 2
) -> List[str]:
    """
    Preprocess text for sentiment analysis.
    
    This function performs the following preprocessing steps:
    1. Remove HTML tags (optional)
    2. Convert to lowercase (optional)
    3. Remove punctuation (optional)
    4. Tokenize using spaCy
    5. Remove stop words (optional)
    6. Remove non-alphabetic tokens (optional)
    7. Filter tokens by minimum length
    
    Args:
        text (str): Input text to preprocess
        remove_html_tags (bool): Whether to remove HTML tags
        to_lowercase (bool): Whether to convert to lowercase
        remove_punct (bool): Whether to remove punctuation
        remove_stop_words (bool): Whether to remove stop words
        remove_non_alpha (bool): Whether to remove non-alphabetic tokens
        min_token_length (int): Minimum token length to keep
        
    Returns:
        List[str]: List of preprocessed tokens
    """
    if not text or not isinstance(text, str):
        return []
    
    # Step 1: Remove HTML tags
    if remove_html_tags:
        text = remove_html(text)
    
    # Step 2: Convert to lowercase
    if to_lowercase:
        text = text.lower()
    
    # Step 3: Remove punctuation
    if remove_punct:
        text = remove_punctuation(text)
    
    # Step 4: Tokenize using spaCy
    nlp = get_nlp_model()
    doc = nlp(text)
    
    # Step 5-7: Filter tokens
    tokens = []
    for token in doc:
        # Skip stop words if requested
        if remove_stop_words and token.is_stop:
            continue
            
        # Skip non-alphabetic tokens if requested
        if remove_non_alpha and not token.is_alpha:
            continue
            
        # Skip tokens that are too short
        if len(token.text) < min_token_length:
            continue
            
        # Skip whitespace tokens
        if token.is_space:
            continue
            
        tokens.append(token.text)
    
    return tokens


def preprocess_article(article_text: str) -> List[str]:
    """
    Preprocess article text with default settings optimized for financial news.
    
    This is a convenience function that applies standard preprocessing
    for financial news articles.
    
    Args:
        article_text (str): Raw article text
        
    Returns:
        List[str]: List of preprocessed tokens
    """
    return preprocess_text(
        text=article_text,
        remove_html_tags=True,
        to_lowercase=True,
        remove_punct=True,
        remove_stop_words=True,
        remove_non_alpha=True,
        min_token_length=2
    )


def preprocess_for_sentiment(article_text: str) -> str:
    """
    Preprocess article text and return as a single string for sentiment analysis.
    
    Args:
        article_text (str): Raw article text
        
    Returns:
        str: Preprocessed text as a single string
    """
    tokens = preprocess_article(article_text)
    return " ".join(tokens)


def get_text_statistics(text: str) -> dict:
    """
    Get basic statistics about the text before and after preprocessing.
    
    Args:
        text (str): Input text
        
    Returns:
        dict: Dictionary containing text statistics
    """
    if not text:
        return {
            "original_length": 0,
            "original_word_count": 0,
            "preprocessed_tokens": 0,
            "preprocessing_ratio": 0.0
        }
    
    # Original statistics
    original_length = len(text)
    original_words = len(text.split())
    
    # Preprocessed statistics
    preprocessed_tokens = preprocess_article(text)
    token_count = len(preprocessed_tokens)
    
    # Calculate ratio
    ratio = token_count / original_words if original_words > 0 else 0.0
    
    return {
        "original_length": original_length,
        "original_word_count": original_words,
        "preprocessed_tokens": token_count,
        "preprocessing_ratio": ratio
    } 