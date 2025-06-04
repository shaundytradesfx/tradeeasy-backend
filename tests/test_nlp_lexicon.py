"""
Unit tests for the Loughran-McDonald lexicon module.

Tests cover lexicon functionality, sentiment scoring, word counting,
and edge cases for financial sentiment analysis.
"""

import pytest
from app.nlp.lexicon import LoughranMcDonaldLexicon, get_lexicon


class TestLoughranMcDonaldLexicon:
    """Test Loughran-McDonald lexicon functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.lexicon = LoughranMcDonaldLexicon()
    
    def test_lexicon_initialization(self):
        """Test lexicon initialization."""
        assert isinstance(self.lexicon.positive_words, set)
        assert isinstance(self.lexicon.negative_words, set)
        assert len(self.lexicon.positive_words) > 0
        assert len(self.lexicon.negative_words) > 0
    
    def test_get_positive_words(self):
        """Test getting positive words."""
        positive_words = self.lexicon.get_positive_words()
        assert isinstance(positive_words, set)
        assert "achievement" in positive_words
        assert "advance" in positive_words
        assert "beneficial" in positive_words
    
    def test_get_negative_words(self):
        """Test getting negative words."""
        negative_words = self.lexicon.get_negative_words()
        assert isinstance(negative_words, set)
        assert "abandon" in negative_words
        assert "adverse" in negative_words
        assert "bankrupt" in negative_words
    
    def test_is_positive(self):
        """Test positive word detection."""
        assert self.lexicon.is_positive("achievement")
        assert self.lexicon.is_positive("ACHIEVEMENT")  # Case insensitive
        assert self.lexicon.is_positive("beneficial")
        assert not self.lexicon.is_positive("abandon")
        assert not self.lexicon.is_positive("neutral_word")
    
    def test_is_negative(self):
        """Test negative word detection."""
        assert self.lexicon.is_negative("abandon")
        assert self.lexicon.is_negative("ABANDON")  # Case insensitive
        assert self.lexicon.is_negative("adverse")
        assert not self.lexicon.is_negative("achievement")
        assert not self.lexicon.is_negative("neutral_word")
    
    def test_count_sentiment_words_positive(self):
        """Test counting sentiment words with positive text."""
        tokens = ["achievement", "advance", "beneficial", "neutral", "word"]
        positive_count, negative_count = self.lexicon.count_sentiment_words(tokens)
        
        assert positive_count == 3
        assert negative_count == 0
    
    def test_count_sentiment_words_negative(self):
        """Test counting sentiment words with negative text."""
        tokens = ["abandon", "adverse", "bankrupt", "neutral", "word"]
        positive_count, negative_count = self.lexicon.count_sentiment_words(tokens)
        
        assert positive_count == 0
        assert negative_count == 3
    
    def test_count_sentiment_words_mixed(self):
        """Test counting sentiment words with mixed sentiment."""
        tokens = ["achievement", "abandon", "beneficial", "adverse", "neutral"]
        positive_count, negative_count = self.lexicon.count_sentiment_words(tokens)
        
        assert positive_count == 2
        assert negative_count == 2
    
    def test_count_sentiment_words_empty(self):
        """Test counting sentiment words with empty list."""
        tokens = []
        positive_count, negative_count = self.lexicon.count_sentiment_words(tokens)
        
        assert positive_count == 0
        assert negative_count == 0
    
    def test_count_sentiment_words_no_sentiment(self):
        """Test counting sentiment words with no sentiment words."""
        tokens = ["neutral", "words", "without", "sentiment"]
        positive_count, negative_count = self.lexicon.count_sentiment_words(tokens)
        
        assert positive_count == 0
        assert negative_count == 0
    
    def test_calculate_sentiment_score_positive(self):
        """Test sentiment score calculation for positive text."""
        tokens = ["achievement", "beneficial", "neutral", "word"]  # 2 positive out of 4
        score = self.lexicon.calculate_sentiment_score(tokens)
        
        expected_score = (2 - 0) / 4  # (positive - negative) / total
        assert score == expected_score
        assert score == 0.5
    
    def test_calculate_sentiment_score_negative(self):
        """Test sentiment score calculation for negative text."""
        tokens = ["abandon", "adverse", "neutral", "word"]  # 2 negative out of 4
        score = self.lexicon.calculate_sentiment_score(tokens)
        
        expected_score = (0 - 2) / 4  # (positive - negative) / total
        assert score == expected_score
        assert score == -0.5
    
    def test_calculate_sentiment_score_neutral(self):
        """Test sentiment score calculation for neutral text."""
        tokens = ["neutral", "words", "without", "sentiment"]
        score = self.lexicon.calculate_sentiment_score(tokens)
        
        assert score == 0.0
    
    def test_calculate_sentiment_score_mixed_equal(self):
        """Test sentiment score calculation for equal positive/negative."""
        tokens = ["achievement", "abandon", "beneficial", "adverse"]  # 2 pos, 2 neg
        score = self.lexicon.calculate_sentiment_score(tokens)
        
        expected_score = (2 - 2) / 4  # (positive - negative) / total
        assert score == expected_score
        assert score == 0.0
    
    def test_calculate_sentiment_score_empty(self):
        """Test sentiment score calculation for empty tokens."""
        tokens = []
        score = self.lexicon.calculate_sentiment_score(tokens)
        
        assert score == 0.0
    
    def test_calculate_sentiment_score_bounds(self):
        """Test sentiment score stays within [-1, 1] bounds."""
        # All positive words
        all_positive = ["achievement", "beneficial", "advance", "asset"]
        score = self.lexicon.calculate_sentiment_score(all_positive)
        assert -1.0 <= score <= 1.0
        
        # All negative words
        all_negative = ["abandon", "adverse", "bankrupt", "burden"]
        score = self.lexicon.calculate_sentiment_score(all_negative)
        assert -1.0 <= score <= 1.0
    
    def test_get_sentiment_details(self):
        """Test detailed sentiment analysis."""
        tokens = ["achievement", "abandon", "beneficial", "neutral", "word"]
        details = self.lexicon.get_sentiment_details(tokens)
        
        assert details["positive_count"] == 2
        assert details["negative_count"] == 1
        assert details["total_tokens"] == 5
        assert details["sentiment_score"] == (2 - 1) / 5  # 0.2
        assert details["positive_ratio"] == 2 / 5  # 0.4
        assert details["negative_ratio"] == 1 / 5  # 0.2
        assert details["sentiment_words_ratio"] == 3 / 5  # 0.6
    
    def test_get_sentiment_details_empty(self):
        """Test detailed sentiment analysis with empty tokens."""
        tokens = []
        details = self.lexicon.get_sentiment_details(tokens)
        
        assert details["positive_count"] == 0
        assert details["negative_count"] == 0
        assert details["total_tokens"] == 0
        assert details["sentiment_score"] == 0.0
        assert details["positive_ratio"] == 0.0
        assert details["negative_ratio"] == 0.0
        assert details["sentiment_words_ratio"] == 0.0
    
    def test_case_insensitive_matching(self):
        """Test that lexicon matching is case insensitive."""
        tokens = ["ACHIEVEMENT", "achievement", "Achievement", "ABANDON", "abandon"]
        positive_count, negative_count = self.lexicon.count_sentiment_words(tokens)
        
        assert positive_count == 3  # All variations of "achievement"
        assert negative_count == 2  # All variations of "abandon"


class TestLexiconSingleton:
    """Test lexicon singleton functionality."""
    
    def test_get_lexicon_singleton(self):
        """Test that get_lexicon returns the same instance."""
        lexicon1 = get_lexicon()
        lexicon2 = get_lexicon()
        
        assert lexicon1 is lexicon2
        assert isinstance(lexicon1, LoughranMcDonaldLexicon)
    
    def test_lexicon_consistency(self):
        """Test that lexicon data is consistent across calls."""
        lexicon1 = get_lexicon()
        lexicon2 = get_lexicon()
        
        assert lexicon1.positive_words == lexicon2.positive_words
        assert lexicon1.negative_words == lexicon2.negative_words


class TestFinancialScenarios:
    """Test lexicon with realistic financial scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.lexicon = LoughranMcDonaldLexicon()
    
    def test_positive_financial_news(self):
        """Test with positive financial news tokens."""
        tokens = [
            "company", "reported", "strong", "earnings", "achievement",
            "revenue", "increased", "beneficial", "growth", "advance"
        ]
        
        score = self.lexicon.calculate_sentiment_score(tokens)
        assert score > 0  # Should be positive
        
        details = self.lexicon.get_sentiment_details(tokens)
        assert details["positive_count"] > 0
        assert details["positive_count"] >= details["negative_count"]
    
    def test_negative_financial_news(self):
        """Test with negative financial news tokens."""
        tokens = [
            "company", "reported", "losses", "abandon", "revenue",
            "declined", "adverse", "conditions", "bankrupt", "burden"
        ]
        
        score = self.lexicon.calculate_sentiment_score(tokens)
        assert score < 0  # Should be negative
        
        details = self.lexicon.get_sentiment_details(tokens)
        assert details["negative_count"] > 0
        assert details["negative_count"] > details["positive_count"]
    
    def test_mixed_financial_news(self):
        """Test with mixed sentiment financial news."""
        tokens = [
            "company", "achievement", "quarter", "but", "adverse",
            "conditions", "beneficial", "outlook", "despite", "abandon"
        ]
        
        score = self.lexicon.calculate_sentiment_score(tokens)
        details = self.lexicon.get_sentiment_details(tokens)
        
        # Should have both positive and negative words
        assert details["positive_count"] > 0
        assert details["negative_count"] > 0
        
        # Score should reflect the balance
        expected_score = (details["positive_count"] - details["negative_count"]) / len(tokens)
        assert abs(score - expected_score) < 0.001
    
    def test_neutral_financial_news(self):
        """Test with neutral financial news (no sentiment words)."""
        tokens = [
            "company", "reported", "quarterly", "results", "revenue",
            "million", "dollars", "shares", "trading", "market"
        ]
        
        score = self.lexicon.calculate_sentiment_score(tokens)
        assert score == 0.0  # Should be neutral
        
        details = self.lexicon.get_sentiment_details(tokens)
        assert details["positive_count"] == 0
        assert details["negative_count"] == 0
        assert details["sentiment_words_ratio"] == 0.0 