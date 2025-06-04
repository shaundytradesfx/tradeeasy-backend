"""
Loughran-McDonald Financial Sentiment Lexicon implementation.

This module provides the Loughran-McDonald lexicon for financial sentiment analysis
and functions to calculate sentiment scores based on word counts.
"""

from typing import Dict, List, Set, Tuple
import os
import json
from pathlib import Path


# Loughran-McDonald Positive Words (subset for demonstration)
POSITIVE_WORDS = {
    "able", "abundance", "abundant", "acclaimed", "accomplish", "accomplished", 
    "achievement", "achievements", "achieves", "achieving", "acknowledge", 
    "acknowledged", "acknowledges", "acknowledging", "acknowledgment", 
    "acknowledgments", "accolade", "accolades", "accommodate", "accommodated", 
    "accommodates", "accommodating", "accommodation", "accommodations", 
    "accomplish", "accomplished", "accomplishes", "accomplishing", 
    "accomplishment", "accomplishments", "achieve", "achieved", "achievement", 
    "achievements", "achieves", "achieving", "adequate", "adequately", 
    "advance", "advanced", "advancement", "advancements", "advances", "advancing", 
    "advantage", "advantaged", "advantageous", "advantageously", "advantages", 
    "alliance", "alliances", "amazing", "ambitious", "amicable", "amicably", 
    "ample", "amplify", "amplifying", "applaud", "applauded", "applauding", 
    "applauds", "appreciate", "appreciated", "appreciates", "appreciating", 
    "appreciation", "appreciative", "appropriate", "appropriately", "approval", 
    "approve", "approved", "approves", "approving", "asset", "assets", 
    "assurance", "assure", "assured", "assures", "assuring", "attain", 
    "attained", "attaining", "attainment", "attains", "attractive", 
    "attractively", "attractiveness", "award", "awarded", "awarding", "awards",
    "beneficial", "beneficially", "benefit", "benefited", "benefiting", 
    "benefits", "best", "better", "bolster", "bolstered", "bolstering", 
    "bolsters", "boom", "booming", "boost", "boosted", "boosting", "boosts", 
    "breakthrough", "breakthroughs", "bright", "brilliant", "bullish"
}

# Loughran-McDonald Negative Words (subset for demonstration)
NEGATIVE_WORDS = {
    "abandon", "abandoned", "abandoning", "abandonment", "abandons", "abdicated", 
    "abdication", "aberrant", "aberration", "aberrations", "abetting", "abnormal", 
    "abnormalities", "abnormality", "abnormally", "abort", "aborted", "aborting", 
    "aborts", "abruptly", "absence", "absent", "absenteeism", "abuse", "abused", 
    "abuses", "abusing", "abusive", "accident", "accidental", "accidentally", 
    "accidents", "accusation", "accusations", "accuse", "accused", "accuses", 
    "accusing", "acquiesce", "acquiesced", "acquiescence", "acquiescent", 
    "acquiesces", "acquiescing", "adverse", "adversely", "adversities", 
    "adversity", "alarm", "alarmed", "alarming", "alarmingly", "alarms", 
    "allegations", "allege", "alleged", "allegedly", "alleges", "alleging", 
    "annoy", "annoyed", "annoying", "annoys", "annoyance", "annoyances", 
    "antitrust", "anxiety", "anxieties", "anxious", "anxiously", "arbitrary", 
    "arbitrarily", "argue", "argued", "argues", "arguing", "argument", 
    "arguments", "argumentative", "arrest", "arrested", "arresting", "arrests", 
    "assault", "assaulted", "assaulting", "assaults", "attack", "attacked", 
    "attacking", "attacks", "bad", "badly", "bail", "bailed", "bailing", 
    "bailout", "bails", "ban", "banned", "banning", "bans", "bankrupt", 
    "bankruptcy", "bankruptcies", "bear", "bearish", "bears", "blame", 
    "blamed", "blames", "blaming", "breach", "breached", "breaches", 
    "breaching", "break", "breakdown", "breakdowns", "breaking", "breaks", 
    "broken", "burden", "burdened", "burdening", "burdens", "burdensome"
}


class LoughranMcDonaldLexicon:
    """Loughran-McDonald Financial Sentiment Lexicon."""
    
    def __init__(self):
        """Initialize the lexicon with positive and negative word sets."""
        self.positive_words = POSITIVE_WORDS
        self.negative_words = NEGATIVE_WORDS
        
    def get_positive_words(self) -> Set[str]:
        """Get the set of positive words."""
        return self.positive_words
    
    def get_negative_words(self) -> Set[str]:
        """Get the set of negative words."""
        return self.negative_words
    
    def is_positive(self, word: str) -> bool:
        """Check if a word is in the positive lexicon."""
        return word.lower() in self.positive_words
    
    def is_negative(self, word: str) -> bool:
        """Check if a word is in the negative lexicon."""
        return word.lower() in self.negative_words
    
    def count_sentiment_words(self, tokens: List[str]) -> Tuple[int, int]:
        """
        Count positive and negative words in a list of tokens.
        
        Args:
            tokens (List[str]): List of preprocessed tokens
            
        Returns:
            Tuple[int, int]: (positive_count, negative_count)
        """
        positive_count = 0
        negative_count = 0
        
        for token in tokens:
            token_lower = token.lower()
            if token_lower in self.positive_words:
                positive_count += 1
            elif token_lower in self.negative_words:
                negative_count += 1
                
        return positive_count, negative_count
    
    def calculate_sentiment_score(self, tokens: List[str]) -> float:
        """
        Calculate sentiment score normalized to [-1, 1] range.
        
        The score is calculated as:
        score = (positive_count - negative_count) / total_tokens
        
        Where:
        - score = 1.0 means all words are positive
        - score = -1.0 means all words are negative  
        - score = 0.0 means equal positive/negative or no sentiment words
        
        Args:
            tokens (List[str]): List of preprocessed tokens
            
        Returns:
            float: Sentiment score in range [-1, 1]
        """
        if not tokens:
            return 0.0
            
        positive_count, negative_count = self.count_sentiment_words(tokens)
        total_tokens = len(tokens)
        
        if total_tokens == 0:
            return 0.0
            
        # Calculate normalized score
        score = (positive_count - negative_count) / total_tokens
        
        # Ensure score is in [-1, 1] range
        return max(-1.0, min(1.0, score))
    
    def get_sentiment_details(self, tokens: List[str]) -> Dict:
        """
        Get detailed sentiment analysis results.
        
        Args:
            tokens (List[str]): List of preprocessed tokens
            
        Returns:
            Dict: Detailed sentiment analysis results
        """
        positive_count, negative_count = self.count_sentiment_words(tokens)
        total_tokens = len(tokens)
        score = self.calculate_sentiment_score(tokens)
        
        return {
            "positive_count": positive_count,
            "negative_count": negative_count,
            "total_tokens": total_tokens,
            "sentiment_score": score,
            "positive_ratio": positive_count / total_tokens if total_tokens > 0 else 0.0,
            "negative_ratio": negative_count / total_tokens if total_tokens > 0 else 0.0,
            "sentiment_words_ratio": (positive_count + negative_count) / total_tokens if total_tokens > 0 else 0.0
        }


# Global lexicon instance
_lexicon_instance = None


def get_lexicon() -> LoughranMcDonaldLexicon:
    """Get or create the global lexicon instance."""
    global _lexicon_instance
    if _lexicon_instance is None:
        _lexicon_instance = LoughranMcDonaldLexicon()
    return _lexicon_instance 