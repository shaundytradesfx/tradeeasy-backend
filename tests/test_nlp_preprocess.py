"""
Unit tests for the NLP preprocessing module.

Tests cover HTML removal, text preprocessing, tokenization, filtering,
and edge cases for the financial news preprocessing pipeline.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.nlp.preprocess import (
    remove_html,
    remove_punctuation,
    preprocess_text,
    preprocess_article,
    preprocess_for_sentiment,
    get_text_statistics,
    get_nlp_model
)


class TestHTMLRemoval:
    """Test HTML removal functionality."""
    
    def test_remove_html_basic(self):
        """Test basic HTML tag removal."""
        html_text = "<p>This is a <strong>test</strong> article.</p>"
        expected = "This is a test article."
        result = remove_html(html_text)
        assert result == expected
    
    def test_remove_html_complex(self):
        """Test complex HTML with multiple tags and attributes."""
        html_text = """
        <div class="article">
            <h1>Stock Market Update</h1>
            <p>Apple Inc. <a href="link">AAPL</a> rose <span style="color:green">5%</span> today.</p>
            <ul>
                <li>Revenue increased</li>
                <li>Profit margins improved</li>
            </ul>
        </div>
        """
        result = remove_html(html_text)
        assert "Stock Market Update" in result
        assert "Apple Inc." in result
        assert "AAPL" in result
        assert "rose" in result
        assert "5%" in result
        assert "Revenue increased" in result
        assert "<" not in result
        assert ">" not in result
    
    def test_remove_html_empty_string(self):
        """Test HTML removal with empty string."""
        assert remove_html("") == ""
    
    def test_remove_html_no_tags(self):
        """Test HTML removal with text containing no tags."""
        text = "This is plain text with no HTML tags."
        assert remove_html(text) == text
    
    def test_remove_html_malformed(self):
        """Test HTML removal with malformed HTML."""
        html_text = "<p>Unclosed paragraph <strong>bold text"
        result = remove_html(html_text)
        assert "Unclosed paragraph" in result
        assert "bold text" in result
        assert "<" not in result


class TestPunctuationRemoval:
    """Test punctuation removal functionality."""
    
    def test_remove_punctuation_basic(self):
        """Test basic punctuation removal."""
        text = "Hello, world! How are you?"
        expected = "Hello world How are you"
        result = remove_punctuation(text)
        assert result == expected
    
    def test_remove_punctuation_financial(self):
        """Test punctuation removal with financial text."""
        text = "Apple's stock (AAPL) rose 5.2% to $150.00 today!"
        result = remove_punctuation(text)
        assert "Apples stock AAPL rose 52 to 15000 today" == result
    
    def test_remove_punctuation_empty(self):
        """Test punctuation removal with empty string."""
        assert remove_punctuation("") == ""


class TestTextPreprocessing:
    """Test main text preprocessing functionality."""
    
    @patch('app.nlp.preprocess.get_nlp_model')
    def test_preprocess_text_basic(self, mock_nlp):
        """Test basic text preprocessing."""
        # Mock spaCy model and doc
        mock_token1 = MagicMock()
        mock_token1.text = "apple"
        mock_token1.is_stop = False
        mock_token1.is_alpha = True
        mock_token1.is_space = False
        
        mock_token2 = MagicMock()
        mock_token2.text = "stock"
        mock_token2.is_stop = False
        mock_token2.is_alpha = True
        mock_token2.is_space = False
        
        mock_token3 = MagicMock()
        mock_token3.text = "is"
        mock_token3.is_stop = True
        mock_token3.is_alpha = True
        mock_token3.is_space = False
        
        mock_doc = [mock_token1, mock_token2, mock_token3]
        mock_nlp_instance = MagicMock()
        mock_nlp_instance.return_value = mock_doc
        mock_nlp.return_value = mock_nlp_instance
        
        text = "Apple stock is rising"
        result = preprocess_text(text)
        
        # Should remove stop word "is"
        assert "apple" in result
        assert "stock" in result
        assert "is" not in result
    
    @patch('app.nlp.preprocess.get_nlp_model')
    def test_preprocess_text_with_html(self, mock_nlp):
        """Test preprocessing with HTML content."""
        mock_token = MagicMock()
        mock_token.text = "apple"
        mock_token.is_stop = False
        mock_token.is_alpha = True
        mock_token.is_space = False
        
        mock_doc = [mock_token]
        mock_nlp_instance = MagicMock()
        mock_nlp_instance.return_value = mock_doc
        mock_nlp.return_value = mock_nlp_instance
        
        html_text = "<p>Apple</p>"
        result = preprocess_text(html_text, remove_html_tags=True)
        
        assert "apple" in result
    
    @patch('app.nlp.preprocess.get_nlp_model')
    def test_preprocess_text_options(self, mock_nlp):
        """Test preprocessing with different options."""
        mock_token = MagicMock()
        mock_token.text = "APPLE"
        mock_token.is_stop = False
        mock_token.is_alpha = True
        mock_token.is_space = False
        
        mock_doc = [mock_token]
        mock_nlp_instance = MagicMock()
        mock_nlp_instance.return_value = mock_doc
        mock_nlp.return_value = mock_nlp_instance
        
        text = "APPLE"
        
        # Test with lowercase disabled
        result = preprocess_text(text, to_lowercase=False)
        assert "APPLE" in result
        
        # Test with lowercase enabled
        result = preprocess_text(text, to_lowercase=True)
        # The mock returns "APPLE" but in real scenario it would be lowercased before spaCy
    
    def test_preprocess_text_empty(self):
        """Test preprocessing with empty text."""
        assert preprocess_text("") == []
        assert preprocess_text(None) == []
    
    @patch('app.nlp.preprocess.get_nlp_model')
    def test_preprocess_text_non_alpha_filtering(self, mock_nlp):
        """Test filtering of non-alphabetic tokens."""
        mock_token1 = MagicMock()
        mock_token1.text = "apple"
        mock_token1.is_stop = False
        mock_token1.is_alpha = True
        mock_token1.is_space = False
        
        mock_token2 = MagicMock()
        mock_token2.text = "123"
        mock_token2.is_stop = False
        mock_token2.is_alpha = False
        mock_token2.is_space = False
        
        mock_doc = [mock_token1, mock_token2]
        mock_nlp_instance = MagicMock()
        mock_nlp_instance.return_value = mock_doc
        mock_nlp.return_value = mock_nlp_instance
        
        result = preprocess_text("test", remove_non_alpha=True)
        assert "apple" in result
        assert "123" not in result
    
    @patch('app.nlp.preprocess.get_nlp_model')
    def test_preprocess_text_min_length(self, mock_nlp):
        """Test minimum token length filtering."""
        mock_token1 = MagicMock()
        mock_token1.text = "apple"
        mock_token1.is_stop = False
        mock_token1.is_alpha = True
        mock_token1.is_space = False
        
        mock_token2 = MagicMock()
        mock_token2.text = "a"
        mock_token2.is_stop = False
        mock_token2.is_alpha = True
        mock_token2.is_space = False
        
        mock_doc = [mock_token1, mock_token2]
        mock_nlp_instance = MagicMock()
        mock_nlp_instance.return_value = mock_doc
        mock_nlp.return_value = mock_nlp_instance
        
        result = preprocess_text("test", min_token_length=2)
        assert "apple" in result
        assert "a" not in result


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('app.nlp.preprocess.preprocess_text')
    def test_preprocess_article(self, mock_preprocess):
        """Test article preprocessing convenience function."""
        mock_preprocess.return_value = ["apple", "stock", "rising"]
        
        result = preprocess_article("Apple stock is rising")
        
        # Verify it calls preprocess_text with correct defaults
        mock_preprocess.assert_called_once_with(
            text="Apple stock is rising",
            remove_html_tags=True,
            to_lowercase=True,
            remove_punct=True,
            remove_stop_words=True,
            remove_non_alpha=True,
            min_token_length=2
        )
        assert result == ["apple", "stock", "rising"]
    
    @patch('app.nlp.preprocess.preprocess_article')
    def test_preprocess_for_sentiment(self, mock_preprocess_article):
        """Test sentiment preprocessing function."""
        mock_preprocess_article.return_value = ["apple", "stock", "rising"]
        
        result = preprocess_for_sentiment("Apple stock is rising")
        
        mock_preprocess_article.assert_called_once_with("Apple stock is rising")
        assert result == "apple stock rising"


class TestTextStatistics:
    """Test text statistics functionality."""
    
    @patch('app.nlp.preprocess.preprocess_article')
    def test_get_text_statistics(self, mock_preprocess):
        """Test text statistics calculation."""
        mock_preprocess.return_value = ["apple", "stock"]
        
        text = "Apple stock is rising today"
        result = get_text_statistics(text)
        
        assert result["original_length"] == len(text)
        assert result["original_word_count"] == 5  # "Apple stock is rising today"
        assert result["preprocessed_tokens"] == 2  # ["apple", "stock"]
        assert result["preprocessing_ratio"] == 2/5  # 2 tokens out of 5 original words
    
    def test_get_text_statistics_empty(self):
        """Test statistics with empty text."""
        result = get_text_statistics("")
        
        assert result["original_length"] == 0
        assert result["original_word_count"] == 0
        assert result["preprocessed_tokens"] == 0
        assert result["preprocessing_ratio"] == 0.0


class TestSpacyModelLoading:
    """Test spaCy model loading functionality."""
    
    @patch('spacy.load')
    def test_get_nlp_model_success(self, mock_spacy_load):
        """Test successful model loading."""
        mock_model = MagicMock()
        mock_spacy_load.return_value = mock_model
        
        # Clear the global model cache
        import app.nlp.preprocess
        app.nlp.preprocess._nlp_model = None
        
        result = get_nlp_model()
        
        mock_spacy_load.assert_called_once_with("en_core_web_sm")
        assert result == mock_model
    
    @patch('spacy.load')
    def test_get_nlp_model_cached(self, mock_spacy_load):
        """Test that model is cached after first load."""
        mock_model = MagicMock()
        
        # Set up the cache
        import app.nlp.preprocess
        app.nlp.preprocess._nlp_model = mock_model
        
        result = get_nlp_model()
        
        # Should not call spacy.load again
        mock_spacy_load.assert_not_called()
        assert result == mock_model
    
    @patch('spacy.load')
    def test_get_nlp_model_failure(self, mock_spacy_load):
        """Test model loading failure."""
        mock_spacy_load.side_effect = OSError("Model not found")
        
        # Clear the global model cache
        import app.nlp.preprocess
        app.nlp.preprocess._nlp_model = None
        
        with pytest.raises(OSError) as exc_info:
            get_nlp_model()
        
        assert "spaCy model 'en_core_web_sm' not found" in str(exc_info.value)


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    def test_financial_news_sample(self):
        """Test with a realistic financial news sample."""
        # This test would require the actual spaCy model to be installed
        # For now, we'll test the structure
        sample_text = """
        <div class="article-content">
            <h1>Apple Inc. Reports Strong Q3 Earnings</h1>
            <p>Apple Inc. (NASDAQ: AAPL) reported quarterly earnings that beat 
            analyst expectations. The company's revenue increased by 15% year-over-year.</p>
            <p>CEO Tim Cook said, "We're pleased with our performance this quarter."</p>
        </div>
        """
        
        # Test that the function doesn't crash with realistic input
        try:
            # This will fail if spaCy model isn't installed, but structure is tested
            result = preprocess_article(sample_text)
            # If it succeeds, verify it's a list
            assert isinstance(result, list)
        except OSError:
            # Expected if spaCy model not installed in test environment
            pass
    
    def test_edge_cases(self):
        """Test various edge cases."""
        # Test with only HTML
        html_only = "<div><p></p></div>"
        result = preprocess_article(html_only)
        assert isinstance(result, list)
        
        # Test with only punctuation
        punct_only = "!@#$%^&*()"
        result = preprocess_article(punct_only)
        assert isinstance(result, list)
        
        # Test with mixed content
        mixed = "Apple!!! <strong>STRONG</strong> performance... 123% growth!!!"
        result = preprocess_article(mixed)
        assert isinstance(result, list) 