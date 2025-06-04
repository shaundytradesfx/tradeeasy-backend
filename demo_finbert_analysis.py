#!/usr/bin/env python3
"""
FinBERT Sentiment Analysis Demonstration

This script demonstrates the FinBERT transformer-based sentiment analysis
functionality including single text analysis, batch processing, caching,
performance benchmarking, and combined analysis with lexicon scores.
"""

import sys
import os
import time

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def main():
    print("=" * 80)
    print("FinBERT Sentiment Analysis Demonstration")
    print("=" * 80)
    
    # Check if transformers is available
    try:
        from app.nlp.finbert import (
            FinBERTAnalyzer, 
            analyze_finbert_sentiment, 
            analyze_finbert_batch,
            get_finbert_performance_stats,
            benchmark_finbert,
            TRANSFORMERS_AVAILABLE
        )
        from app.nlp.sentiment import analyze_article_with_finbert
        
        if not TRANSFORMERS_AVAILABLE:
            print("❌ Transformers library not available. Please install with:")
            print("   pip install transformers torch")
            return
            
        print("✅ Transformers library available")
        print()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all dependencies are installed.")
        return
    
    # Sample financial news articles for testing
    sample_articles = [
        {
            "title": "Apple Reports Strong Quarterly Earnings",
            "content": """
            <div class="article">
                <h1>Apple Reports Strong Quarterly Earnings</h1>
                <p>Apple Inc. announced <strong>excellent</strong> quarterly results today, 
                showing significant <em>growth</em> in revenue and <strong>beneficial</strong> 
                market performance. The company's <em>achievement</em> demonstrates strong 
                fundamentals and positive outlook for investors.</p>
            </div>
            """,
            "expected": "positive"
        },
        {
            "title": "Tech Company Faces Bankruptcy Concerns",
            "content": """
            <div class="article">
                <h1>Tech Company Faces Bankruptcy Concerns</h1>
                <p>The struggling tech firm reported <strong>adverse</strong> financial 
                conditions with significant <em>losses</em> and <strong>declining</strong> 
                revenue. Investors are concerned about the company's ability to 
                <em>survive</em> the current market downturn.</p>
            </div>
            """,
            "expected": "negative"
        },
        {
            "title": "Market Analysis: Mixed Signals",
            "content": """
            <div class="article">
                <h1>Market Analysis: Mixed Signals</h1>
                <p>Financial analysts report mixed signals in today's market performance. 
                While some sectors show <em>growth</em>, others face <strong>challenges</strong>. 
                The overall outlook remains <em>uncertain</em> with both positive and 
                negative indicators present.</p>
            </div>
            """,
            "expected": "mixed"
        }
    ]
    
    try:
        print("🤖 Initializing FinBERT analyzer...")
        print("Note: This may take a moment to download the model on first run.")
        print()
        
        # Initialize analyzer with small batch size for demo
        analyzer = FinBERTAnalyzer(batch_size=2)
        
        print("✅ FinBERT analyzer initialized successfully!")
        print(f"   Model: {analyzer.model_name}")
        print(f"   Device: {analyzer.device}")
        print(f"   Batch size: {analyzer.batch_size}")
        print()
        
        # Demonstrate single text analysis
        print("📝 Single Text Analysis")
        print("-" * 40)
        
        for i, article in enumerate(sample_articles, 1):
            print(f"\n{i}. {article['title']} (Expected: {article['expected']})")
            
            # Analyze with FinBERT
            result = analyzer.analyze_article(article['content'], preprocess=True)
            
            print(f"   Positive: {result['positive']:.4f}")
            print(f"   Neutral:  {result['neutral']:.4f}")
            print(f"   Negative: {result['negative']:.4f}")
            print(f"   Composite Score: {result['composite_score']:.4f}")
            print(f"   Inference Time: {result['inference_time']:.4f}s")
            print(f"   Text Length: {result['original_length']} → {result['processed_length']} chars")
            
            # Interpret result
            if result['composite_score'] > 0.1:
                sentiment = "Positive 📈"
            elif result['composite_score'] < -0.1:
                sentiment = "Negative 📉"
            else:
                sentiment = "Neutral ➡️"
            
            print(f"   Interpretation: {sentiment}")
        
        # Demonstrate batch processing
        print("\n" + "=" * 80)
        print("📦 Batch Processing Demonstration")
        print("-" * 40)
        
        # Extract just the content for batch processing
        batch_texts = [article['content'] for article in sample_articles]
        
        print(f"Processing {len(batch_texts)} articles in batch...")
        start_time = time.time()
        
        batch_results = analyzer.analyze_batch(batch_texts, use_cache=False)
        
        batch_time = time.time() - start_time
        print(f"Batch processing completed in {batch_time:.4f}s")
        print(f"Average time per article: {batch_time/len(batch_texts):.4f}s")
        print()
        
        for i, (article, result) in enumerate(zip(sample_articles, batch_results), 1):
            print(f"{i}. {article['title']}")
            print(f"   Composite Score: {result['composite_score']:.4f}")
            print(f"   Inference Time: {result['inference_time']:.4f}s")
        
        # Demonstrate caching
        print("\n" + "=" * 80)
        print("🗄️ Caching Demonstration")
        print("-" * 40)
        
        # Clear cache and analyze same text twice
        analyzer.clear_cache()
        test_text = sample_articles[0]['content']
        
        print("First analysis (cache miss):")
        start_time = time.time()
        result1 = analyzer.analyze_text(test_text, use_cache=True)
        time1 = time.time() - start_time
        print(f"   Time: {time1:.4f}s")
        
        print("Second analysis (cache hit):")
        start_time = time.time()
        result2 = analyzer.analyze_text(test_text, use_cache=True)
        time2 = time.time() - start_time
        print(f"   Time: {time2:.4f}s")
        
        print(f"Speedup: {time1/time2:.2f}x faster with cache")
        
        # Show performance stats
        stats = analyzer.get_performance_stats()
        print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")
        print(f"Total inferences: {stats['total_inferences']}")
        
        # Demonstrate benchmarking
        print("\n" + "=" * 80)
        print("⚡ Performance Benchmarking")
        print("-" * 40)
        
        # Use shorter texts for faster benchmarking
        benchmark_texts = [
            "Company reports strong earnings growth.",
            "Stock prices decline amid market uncertainty.",
            "Quarterly results meet analyst expectations."
        ]
        
        print(f"Benchmarking with {len(benchmark_texts)} texts, 2 iterations...")
        
        benchmark_results = analyzer.benchmark(benchmark_texts, iterations=2)
        
        print(f"Single text analysis:")
        print(f"   Average time: {benchmark_results['single_text']['avg_time']:.4f}s")
        print(f"   Min time: {benchmark_results['single_text']['min_time']:.4f}s")
        print(f"   Max time: {benchmark_results['single_text']['max_time']:.4f}s")
        
        print(f"Batch processing:")
        print(f"   Average time: {benchmark_results['batch_processing']['avg_time']:.4f}s")
        print(f"   Texts per second: {benchmark_results['batch_processing']['texts_per_second']:.2f}")
        print(f"   Speedup factor: {benchmark_results['speedup_factor']:.2f}x")
        
        # Demonstrate combined analysis
        print("\n" + "=" * 80)
        print("🔄 Combined Lexicon + FinBERT Analysis")
        print("-" * 40)
        
        for i, article in enumerate(sample_articles, 1):
            print(f"\n{i}. {article['title']}")
            
            # Combined analysis
            combined_result = analyze_article_with_finbert(article['content'])
            
            lexicon_score = combined_result['lexicon_analysis']['lexicon_score']
            
            if combined_result['finbert_analysis']:
                finbert_score = combined_result['finbert_analysis']['composite_score']
                print(f"   Lexicon Score:  {lexicon_score:+.4f}")
                print(f"   FinBERT Score:  {finbert_score:+.4f}")
                print(f"   Average Score:  {(lexicon_score + finbert_score)/2:+.4f}")
                
                # Compare methods
                if abs(lexicon_score - finbert_score) < 0.2:
                    agreement = "✅ Agreement"
                else:
                    agreement = "⚠️ Disagreement"
                print(f"   Method Agreement: {agreement}")
            else:
                print(f"   Lexicon Score: {lexicon_score:+.4f}")
                print(f"   FinBERT Score: Not available")
        
        print("\n" + "=" * 80)
        print("✅ FinBERT Demonstration Complete!")
        print("=" * 80)
        
        # Final performance summary
        final_stats = analyzer.get_performance_stats()
        print(f"Session Summary:")
        print(f"   Total inferences: {final_stats['total_inferences']}")
        print(f"   Average inference time: {final_stats['avg_inference_time']:.4f}s")
        print(f"   Cache hit rate: {final_stats['cache_hit_rate']:.2%}")
        print(f"   Device used: {final_stats['device']}")
        
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        print("This is likely due to missing dependencies or model download issues.")
        print("Please ensure transformers and torch are properly installed.")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 