"""
FinBERT transformer-based sentiment analysis module.

This module provides FinBERT (Financial BERT) sentiment analysis capabilities
using the ProsusAI/finbert model for financial text analysis with batch processing,
caching, and performance benchmarking.
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Union
from functools import lru_cache
import hashlib
import json

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from .preprocess import preprocess_article


# Configure logging
logger = logging.getLogger(__name__)

# Global FinBERT pipeline instance
_finbert_pipeline = None
_model_cache = {}


class FinBERTAnalyzer:
    """FinBERT sentiment analyzer with caching and benchmarking capabilities."""
    
    def __init__(self, model_name: str = "ProsusAI/finbert", device: Optional[str] = None, batch_size: int = 8):
        """
        Initialize FinBERT analyzer.
        
        Args:
            model_name (str): HuggingFace model name for FinBERT
            device (Optional[str]): Device to run model on ('cpu', 'cuda', or None for auto)
            batch_size (int): Batch size for processing multiple texts
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "transformers library is required for FinBERT analysis. "
                "Install with: pip install transformers torch"
            )
        
        self.model_name = model_name
        self.batch_size = batch_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.pipeline = None
        self.tokenizer = None
        self.model = None
        
        # Performance tracking
        self.inference_times = []
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Initialize model
        self._load_model()
    
    def _load_model(self):
        """Load FinBERT model and tokenizer."""
        try:
            logger.info(f"Loading FinBERT model: {self.model_name}")
            start_time = time.time()
            
            # Load tokenizer and model separately for more control
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            
            # Create pipeline
            self.pipeline = pipeline(
                "sentiment-analysis",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" and torch.cuda.is_available() else -1,
                batch_size=self.batch_size,
                return_all_scores=True  # Return probabilities for all classes
            )
            
            load_time = time.time() - start_time
            logger.info(f"FinBERT model loaded in {load_time:.2f} seconds on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to load FinBERT model: {e}")
            raise
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    @lru_cache(maxsize=1000)
    def _cached_analyze(self, text_hash: str, text: str) -> Dict:
        """Cached analysis for single text."""
        self.cache_misses += 1
        return self._analyze_single(text)
    
    def _analyze_single(self, text: str) -> Dict:
        """Analyze sentiment for a single text."""
        if not text or not text.strip():
            return {
                "positive": 0.0,
                "neutral": 1.0,
                "negative": 0.0,
                "composite_score": 0.0,
                "inference_time": 0.0
            }
        
        start_time = time.time()
        
        try:
            # Get predictions with all scores
            results = self.pipeline(text)
            inference_time = time.time() - start_time
            self.inference_times.append(inference_time)
            
            # Extract probabilities (FinBERT returns positive, negative, neutral)
            probabilities = {result['label'].lower(): result['score'] for result in results[0]}
            
            # Ensure all required labels are present
            positive = probabilities.get('positive', 0.0)
            negative = probabilities.get('negative', 0.0)
            neutral = probabilities.get('neutral', 0.0)
            
            # Calculate composite score (positive - negative)
            composite_score = positive - negative
            
            return {
                "positive": positive,
                "neutral": neutral,
                "negative": negative,
                "composite_score": composite_score,
                "inference_time": inference_time
            }
            
        except Exception as e:
            logger.error(f"Error analyzing text with FinBERT: {e}")
            return {
                "positive": 0.0,
                "neutral": 1.0,
                "negative": 0.0,
                "composite_score": 0.0,
                "inference_time": 0.0,
                "error": str(e)
            }
    
    def analyze_text(self, text: str, use_cache: bool = True) -> Dict:
        """
        Analyze sentiment for a single text.
        
        Args:
            text (str): Text to analyze
            use_cache (bool): Whether to use caching
            
        Returns:
            Dict: Sentiment analysis results
        """
        if use_cache:
            cache_key = self._get_cache_key(text)
            try:
                result = self._cached_analyze(cache_key, text)
                self.cache_hits += 1
                return result
            except:
                # Fallback to non-cached analysis
                pass
        
        return self._analyze_single(text)
    
    def analyze_batch(self, texts: List[str], use_cache: bool = True) -> List[Dict]:
        """
        Analyze sentiment for multiple texts in batches.
        
        Args:
            texts (List[str]): List of texts to analyze
            use_cache (bool): Whether to use caching
            
        Returns:
            List[Dict]: List of sentiment analysis results
        """
        if not texts:
            return []
        
        results = []
        
        # Process texts in batches
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            batch_results = []
            
            # Check cache first if enabled
            if use_cache:
                cached_results = []
                uncached_texts = []
                uncached_indices = []
                
                for j, text in enumerate(batch_texts):
                    cache_key = self._get_cache_key(text)
                    try:
                        cached_result = self._cached_analyze(cache_key, text)
                        cached_results.append((j, cached_result))
                        self.cache_hits += 1
                    except:
                        uncached_texts.append(text)
                        uncached_indices.append(j)
                
                # Process uncached texts
                if uncached_texts:
                    uncached_results = self._process_batch(uncached_texts)
                    
                    # Merge cached and uncached results
                    batch_results = [None] * len(batch_texts)
                    
                    # Fill in cached results
                    for idx, result in cached_results:
                        batch_results[idx] = result
                    
                    # Fill in uncached results
                    for i, idx in enumerate(uncached_indices):
                        batch_results[idx] = uncached_results[i]
                else:
                    batch_results = [result for _, result in cached_results]
            else:
                batch_results = self._process_batch(batch_texts)
            
            results.extend(batch_results)
        
        return results
    
    def _process_batch(self, texts: List[str]) -> List[Dict]:
        """Process a batch of texts through FinBERT."""
        if not texts:
            return []
        
        start_time = time.time()
        
        try:
            # Filter out empty texts
            valid_texts = [text if text and text.strip() else " " for text in texts]
            
            # Get batch predictions
            batch_results = self.pipeline(valid_texts)
            inference_time = time.time() - start_time
            
            # Track inference time per text
            avg_time_per_text = inference_time / len(texts)
            self.inference_times.extend([avg_time_per_text] * len(texts))
            
            results = []
            for i, text_results in enumerate(batch_results):
                # Extract probabilities
                probabilities = {result['label'].lower(): result['score'] for result in text_results}
                
                positive = probabilities.get('positive', 0.0)
                negative = probabilities.get('negative', 0.0)
                neutral = probabilities.get('neutral', 0.0)
                
                # Calculate composite score
                composite_score = positive - negative
                
                results.append({
                    "positive": positive,
                    "neutral": neutral,
                    "negative": negative,
                    "composite_score": composite_score,
                    "inference_time": avg_time_per_text
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing batch with FinBERT: {e}")
            # Return default results for all texts
            return [{
                "positive": 0.0,
                "neutral": 1.0,
                "negative": 0.0,
                "composite_score": 0.0,
                "inference_time": 0.0,
                "error": str(e)
            }] * len(texts)
    
    def analyze_article(self, article_text: str, preprocess: bool = True) -> Dict:
        """
        Analyze sentiment for a full article with preprocessing.
        
        Args:
            article_text (str): Raw article text (may contain HTML)
            preprocess (bool): Whether to preprocess the text
            
        Returns:
            Dict: Sentiment analysis results with additional metadata
        """
        if preprocess:
            # Use existing preprocessing pipeline
            tokens = preprocess_article(article_text)
            processed_text = " ".join(tokens)
        else:
            processed_text = article_text
        
        # Analyze with FinBERT
        result = self.analyze_text(processed_text)
        
        # Add metadata
        result.update({
            "original_length": len(article_text),
            "processed_length": len(processed_text),
            "preprocessed": preprocess
        })
        
        return result
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics."""
        if not self.inference_times:
            return {
                "total_inferences": 0,
                "avg_inference_time": 0.0,
                "min_inference_time": 0.0,
                "max_inference_time": 0.0,
                "cache_hit_rate": 0.0,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses
            }
        
        total_requests = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0.0
        
        return {
            "total_inferences": len(self.inference_times),
            "avg_inference_time": sum(self.inference_times) / len(self.inference_times),
            "min_inference_time": min(self.inference_times),
            "max_inference_time": max(self.inference_times),
            "cache_hit_rate": cache_hit_rate,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "device": self.device,
            "batch_size": self.batch_size
        }
    
    def clear_cache(self):
        """Clear the analysis cache."""
        self._cached_analyze.cache_clear()
        self.cache_hits = 0
        self.cache_misses = 0
    
    def benchmark(self, texts: List[str], iterations: int = 3) -> Dict:
        """
        Benchmark FinBERT performance.
        
        Args:
            texts (List[str]): Test texts for benchmarking
            iterations (int): Number of iterations to run
            
        Returns:
            Dict: Benchmark results
        """
        if not texts:
            raise ValueError("No texts provided for benchmarking")
        
        logger.info(f"Starting FinBERT benchmark with {len(texts)} texts, {iterations} iterations")
        
        # Clear cache for fair benchmarking
        self.clear_cache()
        
        # Warm up
        self.analyze_text(texts[0])
        
        # Benchmark single text analysis
        single_times = []
        for _ in range(iterations):
            start_time = time.time()
            self.analyze_text(texts[0], use_cache=False)
            single_times.append(time.time() - start_time)
        
        # Benchmark batch analysis
        batch_times = []
        for _ in range(iterations):
            start_time = time.time()
            self.analyze_batch(texts, use_cache=False)
            batch_times.append(time.time() - start_time)
        
        return {
            "single_text": {
                "avg_time": sum(single_times) / len(single_times),
                "min_time": min(single_times),
                "max_time": max(single_times)
            },
            "batch_processing": {
                "avg_time": sum(batch_times) / len(batch_times),
                "min_time": min(batch_times),
                "max_time": max(batch_times),
                "texts_per_second": len(texts) / (sum(batch_times) / len(batch_times))
            },
            "speedup_factor": (sum(single_times) / len(single_times) * len(texts)) / (sum(batch_times) / len(batch_times)),
            "device": self.device,
            "batch_size": self.batch_size,
            "num_texts": len(texts),
            "iterations": iterations
        }


# Global analyzer instance
_finbert_analyzer = None


def get_finbert_analyzer(model_name: str = "ProsusAI/finbert", **kwargs) -> FinBERTAnalyzer:
    """
    Get or create the global FinBERT analyzer instance.
    
    Args:
        model_name (str): HuggingFace model name
        **kwargs: Additional arguments for FinBERTAnalyzer
        
    Returns:
        FinBERTAnalyzer: The analyzer instance
    """
    global _finbert_analyzer
    
    if _finbert_analyzer is None:
        _finbert_analyzer = FinBERTAnalyzer(model_name=model_name, **kwargs)
    
    return _finbert_analyzer


def analyze_finbert_sentiment(text: str, use_cache: bool = True) -> Dict:
    """
    Analyze sentiment using FinBERT (convenience function).
    
    Args:
        text (str): Text to analyze
        use_cache (bool): Whether to use caching
        
    Returns:
        Dict: Sentiment analysis results
    """
    analyzer = get_finbert_analyzer()
    return analyzer.analyze_text(text, use_cache=use_cache)


def analyze_finbert_batch(texts: List[str], use_cache: bool = True) -> List[Dict]:
    """
    Analyze sentiment for multiple texts using FinBERT (convenience function).
    
    Args:
        texts (List[str]): List of texts to analyze
        use_cache (bool): Whether to use caching
        
    Returns:
        List[Dict]: List of sentiment analysis results
    """
    analyzer = get_finbert_analyzer()
    return analyzer.analyze_batch(texts, use_cache=use_cache)


def get_finbert_performance_stats() -> Dict:
    """Get FinBERT performance statistics (convenience function)."""
    analyzer = get_finbert_analyzer()
    return analyzer.get_performance_stats()


def benchmark_finbert(texts: List[str], iterations: int = 3) -> Dict:
    """Benchmark FinBERT performance (convenience function)."""
    analyzer = get_finbert_analyzer()
    return analyzer.benchmark(texts, iterations=iterations) 