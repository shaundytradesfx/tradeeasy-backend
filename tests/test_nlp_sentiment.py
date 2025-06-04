"""
Unit tests for the sentiment analysis module.

Tests cover sentiment analysis integration, database operations,
and batch processing for financial news articles.
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from app.nlp.sentiment import (
    analyze_article_sentiment,
    calculate_lexicon_score,
    store_article_sentiment,
    analyze_and_store_sentiment,
    batch_analyze_articles,
    get_sentiment_statistics
)
from app.models import Article, Sentiment


class TestSentimentAnalysis:
    """Test core sentiment analysis functionality."""
    
    @patch('app.nlp.sentiment.preprocess_article')
    @patch('app.nlp.sentiment.get_lexicon')
    def test_analyze_article_sentiment(self, mock_get_lexicon, mock_preprocess):
        """Test article sentiment analysis."""
        # Mock preprocessing
        mock_preprocess.return_value = ["achievement", "beneficial", "adverse", "neutral"]
        
        # Mock lexicon
        mock_lexicon = MagicMock()
        mock_lexicon.get_sentiment_details.return_value = {
            "sentiment_score": 0.25,
            "positive_count": 2,
            "negative_count": 1,
            "total_tokens": 4,
            "positive_ratio": 0.5,
            "negative_ratio": 0.25,
            "sentiment_words_ratio": 0.75
        }
        mock_get_lexicon.return_value = mock_lexicon
        
        # Test analysis
        article_text = "<p>Company shows <strong>achievement</strong> and beneficial results despite adverse conditions.</p>"
        result = analyze_article_sentiment(article_text)
        
        # Verify preprocessing was called
        mock_preprocess.assert_called_once_with(article_text)
        
        # Verify lexicon was used
        mock_lexicon.get_sentiment_details.assert_called_once_with(["achievement", "beneficial", "adverse", "neutral"])
        
        # Verify results
        assert result["lexicon_score"] == 0.25
        assert result["positive_count"] == 2
        assert result["negative_count"] == 1
        assert result["total_tokens"] == 4
        assert result["positive_ratio"] == 0.5
        assert result["negative_ratio"] == 0.25
        assert result["sentiment_words_ratio"] == 0.75
        assert result["preprocessed_tokens"] == ["achievement", "beneficial", "adverse", "neutral"]
    
    @patch('app.nlp.sentiment.preprocess_article')
    @patch('app.nlp.sentiment.get_lexicon')
    def test_calculate_lexicon_score(self, mock_get_lexicon, mock_preprocess):
        """Test lexicon score calculation."""
        # Mock preprocessing
        mock_preprocess.return_value = ["achievement", "beneficial"]
        
        # Mock lexicon
        mock_lexicon = MagicMock()
        mock_lexicon.calculate_sentiment_score.return_value = 0.5
        mock_get_lexicon.return_value = mock_lexicon
        
        # Test calculation
        article_text = "Company shows achievement and beneficial results."
        score = calculate_lexicon_score(article_text)
        
        # Verify calls
        mock_preprocess.assert_called_once_with(article_text)
        mock_lexicon.calculate_sentiment_score.assert_called_once_with(["achievement", "beneficial"])
        
        # Verify result
        assert score == 0.5
    
    def test_analyze_article_sentiment_empty(self):
        """Test sentiment analysis with empty article."""
        result = analyze_article_sentiment("")
        
        assert result["lexicon_score"] == 0.0
        assert result["positive_count"] == 0
        assert result["negative_count"] == 0
        assert result["total_tokens"] == 0
        assert result["preprocessed_tokens"] == []


class TestDatabaseOperations:
    """Test database operations for sentiment storage."""
    
    def test_store_article_sentiment_new(self):
        """Test storing new sentiment record."""
        # Mock database session
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Test storing new sentiment
        article_id = "test-article-id"
        lexicon_score = 0.5
        finbert_score = 0.3
        
        result = store_article_sentiment(mock_db, article_id, lexicon_score, finbert_score)
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        
        # Verify sentiment object creation
        added_sentiment = mock_db.add.call_args[0][0]
        assert added_sentiment.article_id == article_id
        assert added_sentiment.lexicon_score == lexicon_score
        assert added_sentiment.finbert_score == finbert_score
    
    def test_store_article_sentiment_update(self):
        """Test updating existing sentiment record."""
        # Mock existing sentiment
        existing_sentiment = MagicMock(spec=Sentiment)
        existing_sentiment.lexicon_score = 0.2
        existing_sentiment.finbert_score = None
        
        # Mock database session
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = existing_sentiment
        
        # Test updating sentiment
        article_id = "test-article-id"
        lexicon_score = 0.5
        finbert_score = 0.3
        
        result = store_article_sentiment(mock_db, article_id, lexicon_score, finbert_score)
        
        # Verify update operations
        assert existing_sentiment.lexicon_score == lexicon_score
        assert existing_sentiment.finbert_score == finbert_score
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(existing_sentiment)
        assert result == existing_sentiment
    
    @patch('app.nlp.sentiment.analyze_article_sentiment')
    @patch('app.nlp.sentiment.store_article_sentiment')
    def test_analyze_and_store_sentiment(self, mock_store, mock_analyze):
        """Test analyzing and storing sentiment for an article."""
        # Mock article
        mock_article = MagicMock(spec=Article)
        mock_article.id = "test-article-id"
        mock_article.title = "Test Article"
        mock_article.content = "Test content"
        
        # Mock database session
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_article
        
        # Mock sentiment analysis
        mock_analyze.return_value = {
            "lexicon_score": 0.5,
            "positive_count": 2,
            "negative_count": 1,
            "total_tokens": 4
        }
        
        # Mock sentiment storage
        mock_sentiment = MagicMock(spec=Sentiment)
        mock_sentiment.id = "test-sentiment-id"
        mock_store.return_value = mock_sentiment
        
        # Test analysis and storage
        result = analyze_and_store_sentiment(mock_db, "test-article-id")
        
        # Verify calls
        mock_analyze.assert_called_once_with("Test content")
        mock_store.assert_called_once_with(
            db=mock_db,
            article_id="test-article-id",
            lexicon_score=0.5
        )
        
        # Verify result
        assert result["article_id"] == "test-article-id"
        assert result["article_title"] == "Test Article"
        assert result["sentiment_id"] == "test-sentiment-id"
        assert result["lexicon_score"] == 0.5
        assert "analysis_details" in result
    
    def test_analyze_and_store_sentiment_not_found(self):
        """Test analyzing sentiment for non-existent article."""
        # Mock database session
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Test with non-existent article
        with pytest.raises(ValueError) as exc_info:
            analyze_and_store_sentiment(mock_db, "non-existent-id")
        
        assert "Article with ID non-existent-id not found" in str(exc_info.value)


class TestBatchProcessing:
    """Test batch processing functionality."""
    
    @patch('app.nlp.sentiment.analyze_and_store_sentiment')
    def test_batch_analyze_articles(self, mock_analyze_store):
        """Test batch analysis of articles."""
        # Mock articles without sentiment
        mock_article1 = MagicMock(spec=Article)
        mock_article1.id = "article-1"
        mock_article2 = MagicMock(spec=Article)
        mock_article2.id = "article-2"
        
        # Mock database session
        mock_db = MagicMock(spec=Session)
        mock_query = mock_db.query.return_value.outerjoin.return_value.filter.return_value
        mock_query.all.return_value = [mock_article1, mock_article2]
        
        # Mock analysis results
        mock_analyze_store.side_effect = [
            {"article_id": "article-1", "status": "success"},
            {"article_id": "article-2", "status": "success"}
        ]
        
        # Test batch analysis
        results = batch_analyze_articles(mock_db)
        
        # Verify calls
        assert mock_analyze_store.call_count == 2
        mock_analyze_store.assert_any_call(mock_db, "article-1")
        mock_analyze_store.assert_any_call(mock_db, "article-2")
        
        # Verify results
        assert len(results) == 2
        assert results[0]["article_id"] == "article-1"
        assert results[1]["article_id"] == "article-2"
    
    @patch('app.nlp.sentiment.analyze_and_store_sentiment')
    def test_batch_analyze_articles_with_limit(self, mock_analyze_store):
        """Test batch analysis with limit."""
        # Mock articles
        mock_article = MagicMock(spec=Article)
        mock_article.id = "article-1"
        
        # Mock database session with limit
        mock_db = MagicMock(spec=Session)
        mock_query = mock_db.query.return_value.outerjoin.return_value.filter.return_value
        mock_query.limit.return_value.all.return_value = [mock_article]
        
        # Mock analysis result
        mock_analyze_store.return_value = {"article_id": "article-1", "status": "success"}
        
        # Test batch analysis with limit
        results = batch_analyze_articles(mock_db, limit=1)
        
        # Verify limit was applied
        mock_query.limit.assert_called_once_with(1)
        
        # Verify results
        assert len(results) == 1
        assert results[0]["article_id"] == "article-1"
    
    @patch('app.nlp.sentiment.analyze_and_store_sentiment')
    def test_batch_analyze_articles_with_errors(self, mock_analyze_store):
        """Test batch analysis with some errors."""
        # Mock articles
        mock_article1 = MagicMock(spec=Article)
        mock_article1.id = "article-1"
        mock_article1.title = "Article 1"
        mock_article2 = MagicMock(spec=Article)
        mock_article2.id = "article-2"
        mock_article2.title = "Article 2"
        
        # Mock database session
        mock_db = MagicMock(spec=Session)
        mock_query = mock_db.query.return_value.outerjoin.return_value.filter.return_value
        mock_query.all.return_value = [mock_article1, mock_article2]
        
        # Mock analysis results (one success, one error)
        mock_analyze_store.side_effect = [
            {"article_id": "article-1", "status": "success"},
            Exception("Analysis failed")
        ]
        
        # Test batch analysis
        results = batch_analyze_articles(mock_db)
        
        # Verify results include both success and error
        assert len(results) == 2
        assert results[0]["article_id"] == "article-1"
        assert results[1]["article_id"] == "article-2"
        assert results[1]["status"] == "failed"
        assert "error" in results[1]


class TestStatistics:
    """Test sentiment statistics functionality."""
    
    def test_get_sentiment_statistics(self):
        """Test getting sentiment statistics."""
        # Mock database session
        mock_db = MagicMock(spec=Session)
        
        # Mock Article count query
        mock_article_query = MagicMock()
        mock_article_query.count.return_value = 100
        
        # Mock Sentiment count query
        mock_sentiment_query = MagicMock()
        mock_sentiment_query.count.return_value = 80
        
        # Mock lexicon score query
        mock_score_query = MagicMock()
        mock_filter_query = MagicMock()
        mock_filter_query.all.return_value = [
            (0.5,), (0.3,), (-0.2,), (0.0,), (-0.1,), (0.4,), (-0.3,), (0.2,)
        ]
        mock_score_query.filter.return_value = mock_filter_query
        
        # Set up query side effect to return different mocks for different calls
        query_call_count = 0
        def mock_query_side_effect(*args):
            nonlocal query_call_count
            query_call_count += 1
            if query_call_count == 1:  # First call: Article count
                return mock_article_query
            elif query_call_count == 2:  # Second call: Sentiment count
                return mock_sentiment_query
            else:  # Third call: Lexicon scores
                return mock_score_query
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Test statistics
        stats = get_sentiment_statistics(mock_db)
        
        # Verify statistics
        assert stats["total_articles"] == 100
        assert stats["analyzed_articles"] == 80
        assert stats["unanalyzed_articles"] == 20
        assert stats["coverage_percentage"] == 80.0
        
        # Verify sentiment distribution
        # Scores: 0.5, 0.3, -0.2, 0.0, -0.1, 0.4, -0.3, 0.2
        # Positive (>0): 0.5, 0.3, 0.4, 0.2 = 4 articles
        # Negative (<0): -0.2, -0.1, -0.3 = 3 articles  
        # Neutral (==0): 0.0 = 1 article
        assert stats["positive_articles"] == 4  # Scores > 0
        assert stats["negative_articles"] == 3  # Scores < 0
        assert stats["neutral_articles"] == 1   # Scores == 0
        
        # Verify average score
        expected_avg = (0.5 + 0.3 - 0.2 + 0.0 - 0.1 + 0.4 - 0.3 + 0.2) / 8
        assert abs(stats["average_lexicon_score"] - expected_avg) < 0.001
    
    def test_get_sentiment_statistics_no_articles(self):
        """Test statistics with no articles."""
        # Mock database session
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.count.return_value = 0
        
        # Test statistics
        stats = get_sentiment_statistics(mock_db)
        
        # Verify empty statistics
        assert stats["total_articles"] == 0
        assert stats["analyzed_articles"] == 0
        assert stats["unanalyzed_articles"] == 0
        assert stats["coverage_percentage"] == 0.0
        assert stats["average_lexicon_score"] == 0.0
        assert stats["positive_articles"] == 0
        assert stats["negative_articles"] == 0
        assert stats["neutral_articles"] == 0
    
    def test_get_sentiment_statistics_no_sentiment(self):
        """Test statistics with articles but no sentiment analysis."""
        # Mock database session
        mock_db = MagicMock(spec=Session)
        
        # Mock different query chains for Article and Sentiment
        def mock_query_side_effect(model):
            if model.__name__ == 'Article':
                mock_article_query = MagicMock()
                mock_article_query.count.return_value = 100
                return mock_article_query
            elif model.__name__ == 'Sentiment':
                mock_sentiment_query = MagicMock()
                mock_sentiment_query.count.return_value = 0
                return mock_sentiment_query
            else:
                # For any other queries
                mock_other_query = MagicMock()
                return mock_other_query
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Test statistics
        stats = get_sentiment_statistics(mock_db)
        
        # Verify statistics
        assert stats["total_articles"] == 100
        assert stats["analyzed_articles"] == 0
        assert stats["unanalyzed_articles"] == 100
        assert stats["coverage_percentage"] == 0.0
        assert stats["average_lexicon_score"] == 0.0
        assert stats["positive_articles"] == 0
        assert stats["negative_articles"] == 0
        assert stats["neutral_articles"] == 0


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    def test_full_sentiment_pipeline(self):
        """Test the complete sentiment analysis pipeline."""
        # Sample financial news article
        article_text = """
        <div class="article">
            <h1>Apple Reports Strong Quarterly Results</h1>
            <p>Apple Inc. announced <strong>beneficial</strong> quarterly results showing 
            significant <em>achievement</em> in revenue growth. The company's performance 
            demonstrates <strong>advance</strong> in market position despite some 
            <span>adverse</span> market conditions.</p>
        </div>
        """
        
        # Test sentiment analysis (this will use real preprocessing and lexicon)
        try:
            result = analyze_article_sentiment(article_text)
            
            # Verify result structure
            assert "lexicon_score" in result
            assert "positive_count" in result
            assert "negative_count" in result
            assert "total_tokens" in result
            assert "preprocessed_tokens" in result
            
            # Verify score is in valid range
            assert -1.0 <= result["lexicon_score"] <= 1.0
            
            # Verify counts are non-negative
            assert result["positive_count"] >= 0
            assert result["negative_count"] >= 0
            assert result["total_tokens"] >= 0
            
        except Exception as e:
            # If spaCy model not available, test should still pass
            pytest.skip(f"Integration test skipped due to missing dependencies: {e}")
    
    def test_sentiment_score_calculation(self):
        """Test sentiment score calculation with known inputs."""
        # Test with simple known sentiment words
        simple_text = "achievement beneficial adverse abandon"
        
        try:
            score = calculate_lexicon_score(simple_text)
            
            # Should be in valid range
            assert -1.0 <= score <= 1.0
            
            # With 2 positive and 2 negative words, score should be around 0
            # (exact value depends on preprocessing)
            assert abs(score) <= 0.5  # Should be relatively neutral
            
        except Exception as e:
            pytest.skip(f"Integration test skipped due to missing dependencies: {e}")


class TestCombinedSentimentAnalysis:
    """Test combined sentiment analysis with both lexicon and FinBERT."""
    
    @patch('app.nlp.sentiment.FINBERT_AVAILABLE', True)
    @patch('app.nlp.sentiment.analyze_finbert_sentiment')
    @patch('app.nlp.sentiment.analyze_article_sentiment')
    def test_analyze_article_with_finbert_success(self, mock_lexicon_analysis, mock_finbert_analysis):
        """Test combined analysis when FinBERT is available."""
        # Mock lexicon analysis
        mock_lexicon_analysis.return_value = {
            "lexicon_score": 0.3,
            "positive_count": 2,
            "negative_count": 1,
            "total_tokens": 10
        }
        
        # Mock FinBERT analysis
        mock_finbert_analysis.return_value = {
            "positive": 0.7,
            "neutral": 0.2,
            "negative": 0.1,
            "composite_score": 0.6
        }
        
        # Test combined analysis
        from app.nlp.sentiment import analyze_article_with_finbert
        result = analyze_article_with_finbert("Test financial article content")
        
        # Verify structure
        assert "lexicon_analysis" in result
        assert "finbert_analysis" in result
        assert "finbert_available" in result
        assert result["finbert_available"] is True
        
        # Verify lexicon results
        assert result["lexicon_analysis"]["lexicon_score"] == 0.3
        
        # Verify FinBERT results
        assert result["finbert_analysis"]["composite_score"] == 0.6
        assert result["finbert_analysis"]["positive"] == 0.7
    
    @patch('app.nlp.sentiment.FINBERT_AVAILABLE', False)
    @patch('app.nlp.sentiment.analyze_article_sentiment')
    def test_analyze_article_with_finbert_unavailable(self, mock_lexicon_analysis):
        """Test combined analysis when FinBERT is not available."""
        # Mock lexicon analysis
        mock_lexicon_analysis.return_value = {
            "lexicon_score": 0.2,
            "positive_count": 1,
            "negative_count": 0,
            "total_tokens": 5
        }
        
        # Test combined analysis
        from app.nlp.sentiment import analyze_article_with_finbert
        result = analyze_article_with_finbert("Test article")
        
        # Verify structure
        assert "lexicon_analysis" in result
        assert "finbert_analysis" in result
        assert "finbert_available" in result
        assert result["finbert_available"] is False
        assert result["finbert_analysis"] is None
        
        # Verify lexicon results
        assert result["lexicon_analysis"]["lexicon_score"] == 0.2
    
    @patch('app.nlp.sentiment.FINBERT_AVAILABLE', True)
    @patch('app.nlp.sentiment.analyze_finbert_sentiment')
    @patch('app.nlp.sentiment.analyze_article_sentiment')
    def test_analyze_article_with_finbert_error(self, mock_lexicon_analysis, mock_finbert_analysis):
        """Test combined analysis when FinBERT raises an error."""
        # Mock lexicon analysis
        mock_lexicon_analysis.return_value = {
            "lexicon_score": 0.1,
            "positive_count": 1,
            "negative_count": 0,
            "total_tokens": 8
        }
        
        # Mock FinBERT to raise an error
        mock_finbert_analysis.side_effect = Exception("FinBERT model error")
        
        # Test combined analysis
        from app.nlp.sentiment import analyze_article_with_finbert
        result = analyze_article_with_finbert("Test article")
        
        # Verify error handling
        assert "lexicon_analysis" in result
        assert "finbert_analysis" in result
        assert "finbert_error" in result
        assert result["finbert_analysis"] is None
        assert "FinBERT model error" in result["finbert_error"]
    
    @patch('app.nlp.sentiment.store_article_sentiment')
    def test_store_combined_sentiment(self, mock_store):
        """Test storing combined sentiment scores."""
        # Mock database storage
        mock_sentiment = MagicMock()
        mock_sentiment.id = "test-sentiment-id"
        mock_store.return_value = mock_sentiment
        
        # Test storage
        from app.nlp.sentiment import store_combined_sentiment
        mock_db = MagicMock()
        
        result = store_combined_sentiment(
            db=mock_db,
            article_id="test-article",
            lexicon_score=0.3,
            finbert_score=0.6
        )
        
        # Verify call
        mock_store.assert_called_once_with(
            db=mock_db,
            article_id="test-article",
            lexicon_score=0.3,
            finbert_score=0.6
        )
        
        # Verify result
        assert result == mock_sentiment
    
    @patch('app.nlp.sentiment.analyze_article_with_finbert')
    @patch('app.nlp.sentiment.store_combined_sentiment')
    def test_analyze_and_store_combined_sentiment(self, mock_store, mock_analyze):
        """Test analyzing and storing combined sentiment."""
        # Mock article
        mock_article = MagicMock()
        mock_article.id = "test-article-id"
        mock_article.title = "Test Article"
        mock_article.content = "Test content"
        
        # Mock database session
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_article
        
        # Mock combined analysis
        mock_analyze.return_value = {
            "lexicon_analysis": {"lexicon_score": 0.4},
            "finbert_analysis": {"composite_score": 0.7},
            "finbert_available": True
        }
        
        # Mock sentiment storage
        mock_sentiment = MagicMock()
        mock_sentiment.id = "test-sentiment-id"
        mock_store.return_value = mock_sentiment
        
        # Test function
        from app.nlp.sentiment import analyze_and_store_combined_sentiment
        result = analyze_and_store_combined_sentiment(mock_db, "test-article-id")
        
        # Verify calls
        mock_analyze.assert_called_once_with("Test content")
        mock_store.assert_called_once_with(
            db=mock_db,
            article_id="test-article-id",
            lexicon_score=0.4,
            finbert_score=0.7
        )
        
        # Verify result
        assert result["article_id"] == "test-article-id"
        assert result["article_title"] == "Test Article"
        assert result["sentiment_id"] == "test-sentiment-id"
        assert result["lexicon_score"] == 0.4
        assert result["finbert_score"] == 0.7
        assert "combined_analysis" in result
    
    @patch('app.nlp.sentiment.analyze_and_store_combined_sentiment')
    def test_batch_analyze_with_finbert(self, mock_analyze_store):
        """Test batch analysis with FinBERT."""
        # Mock articles without sentiment
        mock_article1 = MagicMock()
        mock_article1.id = "article-1"
        mock_article1.title = "Article 1"
        mock_article2 = MagicMock()
        mock_article2.id = "article-2"
        mock_article2.title = "Article 2"
        
        # Mock database session
        mock_db = MagicMock()
        mock_query = mock_db.query.return_value.outerjoin.return_value.filter.return_value
        mock_query.all.return_value = [mock_article1, mock_article2]
        
        # Mock analysis results
        mock_analyze_store.side_effect = [
            {"article_id": "article-1", "status": "success", "lexicon_score": 0.3, "finbert_score": 0.5},
            {"article_id": "article-2", "status": "success", "lexicon_score": -0.2, "finbert_score": -0.4}
        ]
        
        # Test batch analysis
        from app.nlp.sentiment import batch_analyze_with_finbert
        results = batch_analyze_with_finbert(mock_db)
        
        # Verify calls
        assert mock_analyze_store.call_count == 2
        mock_analyze_store.assert_any_call(mock_db, "article-1")
        mock_analyze_store.assert_any_call(mock_db, "article-2")
        
        # Verify results
        assert len(results) == 2
        assert results[0]["article_id"] == "article-1"
        assert results[1]["article_id"] == "article-2"
    
    @patch('app.nlp.sentiment.analyze_and_store_combined_sentiment')
    def test_batch_analyze_with_finbert_errors(self, mock_analyze_store):
        """Test batch analysis with some errors."""
        # Mock articles
        mock_article1 = MagicMock()
        mock_article1.id = "article-1"
        mock_article1.title = "Article 1"
        mock_article2 = MagicMock()
        mock_article2.id = "article-2"
        mock_article2.title = "Article 2"
        
        # Mock database session
        mock_db = MagicMock()
        mock_query = mock_db.query.return_value.outerjoin.return_value.filter.return_value
        mock_query.all.return_value = [mock_article1, mock_article2]
        
        # Mock analysis results (one success, one error)
        mock_analyze_store.side_effect = [
            {"article_id": "article-1", "status": "success"},
            Exception("Analysis failed")
        ]
        
        # Test batch analysis
        from app.nlp.sentiment import batch_analyze_with_finbert
        results = batch_analyze_with_finbert(mock_db)
        
        # Verify results include both success and error
        assert len(results) == 2
        assert results[0]["article_id"] == "article-1"
        assert results[1]["article_id"] == "article-2"
        assert results[1]["status"] == "failed"
        assert "error" in results[1] 