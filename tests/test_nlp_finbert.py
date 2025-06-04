"""
Unit tests for the FinBERT sentiment analysis module.

Tests cover FinBERT functionality, batch processing, caching,
performance benchmarking, and integration scenarios.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from typing import Dict, List

# Test if transformers is available
try:
    import torch
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from app.nlp.finbert import (
    FinBERTAnalyzer,
    get_finbert_analyzer,
    analyze_finbert_sentiment,
    analyze_finbert_batch,
    get_finbert_performance_stats,
    benchmark_finbert,
    TRANSFORMERS_AVAILABLE as MODULE_TRANSFORMERS_AVAILABLE
)


class TestFinBERTAvailability:
    """Test FinBERT availability and import handling."""
    
    def test_transformers_availability_detection(self):
        """Test that transformers availability is correctly detected."""
        # The module should detect transformers availability
        assert isinstance(MODULE_TRANSFORMERS_AVAILABLE, bool)
    
    @patch('app.nlp.finbert.TRANSFORMERS_AVAILABLE', False)
    def test_finbert_analyzer_without_transformers(self):
        """Test FinBERT analyzer initialization without transformers."""
        with pytest.raises(ImportError) as exc_info:
            FinBERTAnalyzer()
        
        assert "transformers library is required" in str(exc_info.value)


@pytest.mark.skipif(not TRANSFORMERS_AVAILABLE, reason="transformers not available")
class TestFinBERTAnalyzer:
    """Test FinBERT analyzer functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock the model loading to avoid downloading actual models
        self.mock_tokenizer = MagicMock()
        self.mock_model = MagicMock()
        self.mock_pipeline = MagicMock()
        
    @patch('app.nlp.finbert.AutoTokenizer.from_pretrained')
    @patch('app.nlp.finbert.AutoModelForSequenceClassification.from_pretrained')
    @patch('app.nlp.finbert.pipeline')
    def test_finbert_analyzer_initialization(self, mock_pipeline_func, mock_model_class, mock_tokenizer_class):
        """Test FinBERT analyzer initialization."""
        # Mock the components
        mock_tokenizer_class.return_value = self.mock_tokenizer
        mock_model_class.return_value = self.mock_model
        mock_pipeline_func.return_value = self.mock_pipeline
        
        # Initialize analyzer
        analyzer = FinBERTAnalyzer(model_name="test-model", batch_size=4)
        
        # Verify initialization
        assert analyzer.model_name == "test-model"
        assert analyzer.batch_size == 4
        assert analyzer.tokenizer == self.mock_tokenizer
        assert analyzer.model == self.mock_model
        assert analyzer.pipeline == self.mock_pipeline
        
        # Verify model loading calls
        mock_tokenizer_class.assert_called_once_with("test-model")
        mock_model_class.assert_called_once_with("test-model")
        mock_pipeline_func.assert_called_once()
    
    @patch('app.nlp.finbert.AutoTokenizer.from_pretrained')
    @patch('app.nlp.finbert.AutoModelForSequenceClassification.from_pretrained')
    @patch('app.nlp.finbert.pipeline')
    def test_analyze_single_text(self, mock_pipeline_func, mock_model_class, mock_tokenizer_class):
        """Test single text analysis."""
        # Mock pipeline response
        mock_pipeline_response = [[
            {'label': 'positive', 'score': 0.7},
            {'label': 'neutral', 'score': 0.2},
            {'label': 'negative', 'score': 0.1}
        ]]
        
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = mock_pipeline_response
        mock_pipeline_func.return_value = mock_pipeline
        
        # Mock other components
        mock_tokenizer_class.return_value = self.mock_tokenizer
        mock_model_class.return_value = self.mock_model
        
        # Initialize and test
        analyzer = FinBERTAnalyzer()
        result = analyzer.analyze_text("Test financial news about positive earnings.")
        
        # Verify results
        assert result["positive"] == 0.7
        assert result["neutral"] == 0.2
        assert result["negative"] == 0.1
        assert result["composite_score"] == 0.6  # 0.7 - 0.1
        assert "inference_time" in result
        assert result["inference_time"] >= 0
    
    @patch('app.nlp.finbert.AutoTokenizer.from_pretrained')
    @patch('app.nlp.finbert.AutoModelForSequenceClassification.from_pretrained')
    @patch('app.nlp.finbert.pipeline')
    def test_analyze_empty_text(self, mock_pipeline_func, mock_model_class, mock_tokenizer_class):
        """Test analysis of empty text."""
        # Mock components
        mock_tokenizer_class.return_value = self.mock_tokenizer
        mock_model_class.return_value = self.mock_model
        mock_pipeline_func.return_value = self.mock_pipeline
        
        analyzer = FinBERTAnalyzer()
        
        # Test empty string
        result = analyzer.analyze_text("")
        assert result["positive"] == 0.0
        assert result["neutral"] == 1.0
        assert result["negative"] == 0.0
        assert result["composite_score"] == 0.0
        
        # Test whitespace only
        result = analyzer.analyze_text("   ")
        assert result["positive"] == 0.0
        assert result["neutral"] == 1.0
        assert result["negative"] == 0.0
        assert result["composite_score"] == 0.0
    
    @patch('app.nlp.finbert.AutoTokenizer.from_pretrained')
    @patch('app.nlp.finbert.AutoModelForSequenceClassification.from_pretrained')
    @patch('app.nlp.finbert.pipeline')
    def test_batch_analysis(self, mock_pipeline_func, mock_model_class, mock_tokenizer_class):
        """Test batch text analysis."""
        # Mock pipeline response for batch
        mock_pipeline_response = [
            [
                {'label': 'positive', 'score': 0.8},
                {'label': 'neutral', 'score': 0.1},
                {'label': 'negative', 'score': 0.1}
            ],
            [
                {'label': 'positive', 'score': 0.2},
                {'label': 'neutral', 'score': 0.3},
                {'label': 'negative', 'score': 0.5}
            ]
        ]
        
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = mock_pipeline_response
        mock_pipeline_func.return_value = mock_pipeline
        
        # Mock other components
        mock_tokenizer_class.return_value = self.mock_tokenizer
        mock_model_class.return_value = self.mock_model
        
        # Initialize and test
        analyzer = FinBERTAnalyzer(batch_size=2)
        texts = ["Positive earnings report", "Company faces bankruptcy"]
        results = analyzer.analyze_batch(texts, use_cache=False)
        
        # Verify results
        assert len(results) == 2
        
        # First text (positive)
        assert results[0]["positive"] == 0.8
        assert results[0]["negative"] == 0.1
        assert results[0]["composite_score"] == 0.7
        
        # Second text (negative)
        assert results[1]["positive"] == 0.2
        assert results[1]["negative"] == 0.5
        assert results[1]["composite_score"] == -0.3
    
    @patch('app.nlp.finbert.AutoTokenizer.from_pretrained')
    @patch('app.nlp.finbert.AutoModelForSequenceClassification.from_pretrained')
    @patch('app.nlp.finbert.pipeline')
    def test_caching_functionality(self, mock_pipeline_func, mock_model_class, mock_tokenizer_class):
        """Test caching functionality."""
        # Mock pipeline response
        mock_pipeline_response = [[
            {'label': 'positive', 'score': 0.6},
            {'label': 'neutral', 'score': 0.3},
            {'label': 'negative', 'score': 0.1}
        ]]
        
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = mock_pipeline_response
        mock_pipeline_func.return_value = mock_pipeline
        
        # Mock other components
        mock_tokenizer_class.return_value = self.mock_tokenizer
        mock_model_class.return_value = self.mock_model
        
        # Initialize analyzer
        analyzer = FinBERTAnalyzer()
        
        # Clear cache and stats
        analyzer.clear_cache()
        
        # First analysis (cache miss)
        text = "Test text for caching"
        result1 = analyzer.analyze_text(text, use_cache=True)
        
        # Second analysis of same text (cache hit)
        result2 = analyzer.analyze_text(text, use_cache=True)
        
        # Verify results are identical
        assert result1["composite_score"] == result2["composite_score"]
        
        # Verify cache statistics
        stats = analyzer.get_performance_stats()
        assert stats["cache_hits"] >= 1
        assert stats["cache_misses"] >= 1
    
    @patch('app.nlp.finbert.AutoTokenizer.from_pretrained')
    @patch('app.nlp.finbert.AutoModelForSequenceClassification.from_pretrained')
    @patch('app.nlp.finbert.pipeline')
    def test_error_handling(self, mock_pipeline_func, mock_model_class, mock_tokenizer_class):
        """Test error handling in analysis."""
        # Mock pipeline to raise an exception
        mock_pipeline = MagicMock()
        mock_pipeline.side_effect = Exception("Model inference failed")
        mock_pipeline_func.return_value = mock_pipeline
        
        # Mock other components
        mock_tokenizer_class.return_value = self.mock_tokenizer
        mock_model_class.return_value = self.mock_model
        
        # Initialize analyzer
        analyzer = FinBERTAnalyzer()
        
        # Test error handling
        result = analyzer.analyze_text("Test text")
        
        # Verify error result
        assert result["positive"] == 0.0
        assert result["neutral"] == 1.0
        assert result["negative"] == 0.0
        assert result["composite_score"] == 0.0
        assert "error" in result
        assert "Model inference failed" in result["error"]
    
    @patch('app.nlp.finbert.AutoTokenizer.from_pretrained')
    @patch('app.nlp.finbert.AutoModelForSequenceClassification.from_pretrained')
    @patch('app.nlp.finbert.pipeline')
    def test_performance_stats(self, mock_pipeline_func, mock_model_class, mock_tokenizer_class):
        """Test performance statistics tracking."""
        # Mock pipeline response
        mock_pipeline_response = [[
            {'label': 'positive', 'score': 0.5},
            {'label': 'neutral', 'score': 0.3},
            {'label': 'negative', 'score': 0.2}
        ]]
        
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = mock_pipeline_response
        mock_pipeline_func.return_value = mock_pipeline
        
        # Mock other components
        mock_tokenizer_class.return_value = self.mock_tokenizer
        mock_model_class.return_value = self.mock_model
        
        # Initialize analyzer
        analyzer = FinBERTAnalyzer()
        analyzer.clear_cache()
        
        # Perform some analyses
        analyzer.analyze_text("Text 1", use_cache=False)
        analyzer.analyze_text("Text 2", use_cache=False)
        
        # Get performance stats
        stats = analyzer.get_performance_stats()
        
        # Verify stats structure
        assert "total_inferences" in stats
        assert "avg_inference_time" in stats
        assert "min_inference_time" in stats
        assert "max_inference_time" in stats
        assert "cache_hit_rate" in stats
        assert "device" in stats
        assert "batch_size" in stats
        
        # Verify stats values
        assert stats["total_inferences"] >= 2
        assert stats["avg_inference_time"] >= 0
    
    @patch('app.nlp.finbert.AutoTokenizer.from_pretrained')
    @patch('app.nlp.finbert.AutoModelForSequenceClassification.from_pretrained')
    @patch('app.nlp.finbert.pipeline')
    def test_article_analysis_with_preprocessing(self, mock_pipeline_func, mock_model_class, mock_tokenizer_class):
        """Test article analysis with preprocessing."""
        # Mock pipeline response
        mock_pipeline_response = [[
            {'label': 'positive', 'score': 0.7},
            {'label': 'neutral', 'score': 0.2},
            {'label': 'negative', 'score': 0.1}
        ]]
        
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = mock_pipeline_response
        mock_pipeline_func.return_value = mock_pipeline
        
        # Mock other components
        mock_tokenizer_class.return_value = self.mock_tokenizer
        mock_model_class.return_value = self.mock_model
        
        # Initialize analyzer
        analyzer = FinBERTAnalyzer()
        
        # Test with HTML content
        article_html = """
        <div class="article">
            <h1>Company Reports Strong Earnings</h1>
            <p>The company announced <strong>excellent</strong> quarterly results.</p>
        </div>
        """
        
        result = analyzer.analyze_article(article_html, preprocess=True)
        
        # Verify result structure
        assert "positive" in result
        assert "negative" in result
        assert "composite_score" in result
        assert "original_length" in result
        assert "processed_length" in result
        assert "preprocessed" in result
        assert result["preprocessed"] is True
        
        # Verify preprocessing occurred
        assert result["processed_length"] < result["original_length"]


class TestFinBERTConvenienceFunctions:
    """Test FinBERT convenience functions."""
    
    @patch('app.nlp.finbert.get_finbert_analyzer')
    def test_analyze_finbert_sentiment(self, mock_get_analyzer):
        """Test convenience function for single text analysis."""
        # Mock analyzer
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_text.return_value = {
            "positive": 0.6,
            "neutral": 0.3,
            "negative": 0.1,
            "composite_score": 0.5
        }
        mock_get_analyzer.return_value = mock_analyzer
        
        # Test function
        result = analyze_finbert_sentiment("Test text")
        
        # Verify calls
        mock_get_analyzer.assert_called_once()
        mock_analyzer.analyze_text.assert_called_once_with("Test text", use_cache=True)
        
        # Verify result
        assert result["composite_score"] == 0.5
    
    @patch('app.nlp.finbert.get_finbert_analyzer')
    def test_analyze_finbert_batch(self, mock_get_analyzer):
        """Test convenience function for batch analysis."""
        # Mock analyzer
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_batch.return_value = [
            {"positive": 0.7, "negative": 0.1, "composite_score": 0.6},
            {"positive": 0.2, "negative": 0.6, "composite_score": -0.4}
        ]
        mock_get_analyzer.return_value = mock_analyzer
        
        # Test function
        texts = ["Positive text", "Negative text"]
        results = analyze_finbert_batch(texts)
        
        # Verify calls
        mock_get_analyzer.assert_called_once()
        mock_analyzer.analyze_batch.assert_called_once_with(texts, use_cache=True)
        
        # Verify results
        assert len(results) == 2
        assert results[0]["composite_score"] == 0.6
        assert results[1]["composite_score"] == -0.4
    
    @patch('app.nlp.finbert.get_finbert_analyzer')
    def test_get_finbert_performance_stats(self, mock_get_analyzer):
        """Test convenience function for performance stats."""
        # Mock analyzer
        mock_analyzer = MagicMock()
        mock_analyzer.get_performance_stats.return_value = {
            "total_inferences": 10,
            "avg_inference_time": 0.1,
            "cache_hit_rate": 0.5
        }
        mock_get_analyzer.return_value = mock_analyzer
        
        # Test function
        stats = get_finbert_performance_stats()
        
        # Verify calls
        mock_get_analyzer.assert_called_once()
        mock_analyzer.get_performance_stats.assert_called_once()
        
        # Verify result
        assert stats["total_inferences"] == 10
        assert stats["avg_inference_time"] == 0.1
    
    @patch('app.nlp.finbert.get_finbert_analyzer')
    def test_benchmark_finbert(self, mock_get_analyzer):
        """Test convenience function for benchmarking."""
        # Mock analyzer
        mock_analyzer = MagicMock()
        mock_analyzer.benchmark.return_value = {
            "single_text": {"avg_time": 0.1},
            "batch_processing": {"avg_time": 0.3, "texts_per_second": 10},
            "speedup_factor": 3.3
        }
        mock_get_analyzer.return_value = mock_analyzer
        
        # Test function
        texts = ["Text 1", "Text 2", "Text 3"]
        benchmark_result = benchmark_finbert(texts, iterations=2)
        
        # Verify calls
        mock_get_analyzer.assert_called_once()
        mock_analyzer.benchmark.assert_called_once_with(texts, iterations=2)
        
        # Verify result
        assert benchmark_result["speedup_factor"] == 3.3
        assert benchmark_result["batch_processing"]["texts_per_second"] == 10


class TestFinBERTSingleton:
    """Test FinBERT singleton functionality."""
    
    @patch('app.nlp.finbert.FinBERTAnalyzer')
    def test_get_finbert_analyzer_singleton(self, mock_analyzer_class):
        """Test that get_finbert_analyzer returns the same instance."""
        # Mock analyzer instance
        mock_instance = MagicMock()
        mock_analyzer_class.return_value = mock_instance
        
        # Clear global instance
        import app.nlp.finbert
        app.nlp.finbert._finbert_analyzer = None
        
        # Get analyzer instances
        analyzer1 = get_finbert_analyzer()
        analyzer2 = get_finbert_analyzer()
        
        # Verify same instance
        assert analyzer1 is analyzer2
        
        # Verify analyzer was created only once
        mock_analyzer_class.assert_called_once()


class TestFinBERTIntegration:
    """Test FinBERT integration scenarios."""
    
    def test_finbert_without_transformers_graceful_degradation(self):
        """Test graceful degradation when transformers is not available."""
        # This test verifies that the module can be imported even without transformers
        # and that appropriate error messages are shown
        
        # The import should work regardless of transformers availability
        from app.nlp.finbert import TRANSFORMERS_AVAILABLE
        
        # The availability flag should be a boolean
        assert isinstance(TRANSFORMERS_AVAILABLE, bool)
    
    @pytest.mark.skipif(not TRANSFORMERS_AVAILABLE, reason="transformers not available")
    @patch('app.nlp.finbert.AutoTokenizer.from_pretrained')
    @patch('app.nlp.finbert.AutoModelForSequenceClassification.from_pretrained')
    @patch('app.nlp.finbert.pipeline')
    def test_finbert_with_financial_text(self, mock_pipeline_func, mock_model_class, mock_tokenizer_class):
        """Test FinBERT with realistic financial text scenarios."""
        # Mock pipeline responses for different financial scenarios
        def mock_pipeline_side_effect(texts):
            if isinstance(texts, str):
                texts = [texts]
            
            results = []
            for text in texts:
                if "profit" in text.lower() or "growth" in text.lower():
                    # Positive financial news
                    results.append([
                        {'label': 'positive', 'score': 0.8},
                        {'label': 'neutral', 'score': 0.15},
                        {'label': 'negative', 'score': 0.05}
                    ])
                elif "loss" in text.lower() or "decline" in text.lower():
                    # Negative financial news
                    results.append([
                        {'label': 'positive', 'score': 0.1},
                        {'label': 'neutral', 'score': 0.2},
                        {'label': 'negative', 'score': 0.7}
                    ])
                else:
                    # Neutral financial news
                    results.append([
                        {'label': 'positive', 'score': 0.3},
                        {'label': 'neutral', 'score': 0.5},
                        {'label': 'negative', 'score': 0.2}
                    ])
            
            return results if len(results) > 1 else results[0]
        
        mock_pipeline = MagicMock()
        mock_pipeline.side_effect = mock_pipeline_side_effect
        mock_pipeline_func.return_value = mock_pipeline
        
        # Mock other components
        mock_tokenizer_class.return_value = MagicMock()
        mock_model_class.return_value = MagicMock()
        
        # Initialize analyzer
        analyzer = FinBERTAnalyzer()
        
        # Test positive financial news
        positive_result = analyzer.analyze_text("Company reports record profit growth")
        assert positive_result["composite_score"] > 0.5
        
        # Test negative financial news
        negative_result = analyzer.analyze_text("Company faces significant loss and decline")
        assert negative_result["composite_score"] < -0.5
        
        # Test neutral financial news
        neutral_result = analyzer.analyze_text("Company releases quarterly report")
        assert -0.5 < neutral_result["composite_score"] < 0.5 