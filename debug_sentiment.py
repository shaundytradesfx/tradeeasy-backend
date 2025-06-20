#!/usr/bin/env python3
"""
Debug script to test sentiment analysis functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test basic imports first
try:
    from app.nlp.preprocess import preprocess_article
    print("✅ Preprocessing import successful")
except Exception as e:
    print(f"❌ Preprocessing import failed: {e}")

try:
    from app.nlp.lexicon import get_lexicon
    print("✅ Lexicon import successful")
except Exception as e:
    print(f"❌ Lexicon import failed: {e}")

def test_sentiment_analysis():
    """Test sentiment analysis without database imports."""
    
    # Test preprocessing
    test_text = "This company has excellent earnings growth and outstanding performance."
    print(f"\nTesting text: {test_text}")
    
    try:
        tokens = preprocess_article(test_text)
        print(f"✅ Preprocessing successful: {tokens}")
    except Exception as e:
        print(f"❌ Preprocessing failed: {e}")
        return
    
    # Test lexicon scoring
    try:
        lexicon = get_lexicon()
        positive_count, negative_count = lexicon.count_sentiment_words(tokens)
        score = lexicon.calculate_sentiment_score(tokens)
        details = lexicon.get_sentiment_details(tokens)
        
        print(f"✅ Lexicon scoring successful:")
        print(f"   Positive words: {positive_count}")
        print(f"   Negative words: {negative_count}")
        print(f"   Score: {score}")
        print(f"   Details: {details}")
        
        # Check which words are in the lexicon
        positive_words = []
        negative_words = []
        for token in tokens:
            if lexicon.is_positive(token):
                positive_words.append(token)
            elif lexicon.is_negative(token):
                negative_words.append(token)
        
        print(f"   Matched positive words: {positive_words}")
        print(f"   Matched negative words: {negative_words}")
        
    except Exception as e:
        print(f"❌ Lexicon scoring failed: {e}")

def test_negative_sentiment():
    """Test with negative sentiment text."""
    test_text = "The company faces severe financial difficulties and terrible losses."
    print(f"\nTesting negative text: {test_text}")
    
    try:
        tokens = preprocess_article(test_text)
        lexicon = get_lexicon()
        score = lexicon.calculate_sentiment_score(tokens)
        details = lexicon.get_sentiment_details(tokens)
        
        print(f"✅ Negative sentiment test:")
        print(f"   Tokens: {tokens}")
        print(f"   Score: {score}")
        print(f"   Details: {details}")
        
    except Exception as e:
        print(f"❌ Negative sentiment test failed: {e}")

if __name__ == "__main__":
    print("🔍 Testing Sentiment Analysis Components")
    print("=" * 50)
    
    test_sentiment_analysis()
    test_negative_sentiment()
    
    print("\n" + "=" * 50)
    print("Debug sentiment analysis complete") 