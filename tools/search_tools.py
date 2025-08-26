"""Search and information retrieval tools."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SearchTools:
    """Tools for search and information retrieval."""
    
    @staticmethod
    def search_keywords(text: str, keywords: List[str], case_sensitive: bool = False) -> Dict[str, Any]:
        """
        Search for keywords in text.
        
        Args:
            text: Text to search in
            keywords: List of keywords to search for
            case_sensitive: Whether search should be case sensitive
            
        Returns:
            Dictionary containing search results
        """
        if not case_sensitive:
            text = text.lower()
            keywords = [k.lower() for k in keywords]
        
        results = {
            'found_keywords': [],
            'keyword_counts': {},
            'total_matches': 0,
            'searched_at': datetime.now().isoformat()
        }
        
        try:
            for keyword in keywords:
                count = text.count(keyword)
                if count > 0:
                    results['found_keywords'].append(keyword)
                    results['keyword_counts'][keyword] = count
                    results['total_matches'] += count
            
        except Exception as e:
            logger.warning(f"Error searching keywords: {e}")
        
        return results
    
    @staticmethod
    def extract_entities(text: str) -> Dict[str, List[str]]:
        """
        Extract basic entities from text (simple implementation).
        
        Args:
            text: Text to extract entities from
            
        Returns:
            Dictionary containing extracted entities by type
        """
        import re
        
        entities = {
            'emails': [],
            'urls': [],
            'phone_numbers': [],
            'dates': [],
            'numbers': []
        }
        
        try:
            # Extract emails
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            entities['emails'] = re.findall(email_pattern, text)
            
            # Extract URLs
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            entities['urls'] = re.findall(url_pattern, text)
            
            # Extract phone numbers
            phone_patterns = [
                r'\b\d{3}-\d{3}-\d{4}\b',
                r'\b\(\d{3}\)\s*\d{3}-\d{4}\b',
                r'\b\d{3}\.\d{3}\.\d{4}\b'
            ]
            
            for pattern in phone_patterns:
                entities['phone_numbers'].extend(re.findall(pattern, text))
            
            # Extract dates (basic patterns)
            date_patterns = [
                r'\b\d{1,2}/\d{1,2}/\d{4}\b',
                r'\b\d{1,2}-\d{1,2}-\d{4}\b',
                r'\b\d{4}-\d{1,2}-\d{1,2}\b'
            ]
            
            for pattern in date_patterns:
                entities['dates'].extend(re.findall(pattern, text))
            
            # Extract numbers
            number_pattern = r'\b\d+(?:\.\d+)?\b'
            entities['numbers'] = re.findall(number_pattern, text)
            
            # Remove duplicates
            for entity_type in entities:
                entities[entity_type] = list(set(entities[entity_type]))
            
        except Exception as e:
            logger.warning(f"Error extracting entities: {e}")
        
        return entities
    
    @staticmethod
    def find_patterns(text: str, patterns: Dict[str, str]) -> Dict[str, List[str]]:
        """
        Find custom patterns in text.
        
        Args:
            text: Text to search in
            patterns: Dictionary of pattern names and regex patterns
            
        Returns:
            Dictionary containing matches for each pattern
        """
        import re
        
        results = {}
        
        try:
            for pattern_name, pattern in patterns.items():
                matches = re.findall(pattern, text, re.IGNORECASE)
                results[pattern_name] = matches
                
        except Exception as e:
            logger.warning(f"Error finding patterns: {e}")
            results[pattern_name] = []
        
        return results
    
    @staticmethod
    def calculate_text_similarity(text1: str, text2: str) -> float:
        """
        Calculate basic text similarity using word overlap.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            # Simple word-based similarity
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            
            if not words1 and not words2:
                return 1.0
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union)
            
        except Exception as e:
            logger.warning(f"Error calculating text similarity: {e}")
            return 0.0
    
    @staticmethod
    def extract_sentences(text: str, max_sentences: int = None) -> List[str]:
        """
        Extract sentences from text.
        
        Args:
            text: Text to extract sentences from
            max_sentences: Maximum number of sentences to return
            
        Returns:
            List of sentences
        """
        import re
        
        try:
            # Simple sentence splitting
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if max_sentences:
                sentences = sentences[:max_sentences]
            
            return sentences
            
        except Exception as e:
            logger.warning(f"Error extracting sentences: {e}")
            return []
    
    @staticmethod
    def get_text_statistics(text: str) -> Dict[str, Any]:
        """
        Get basic statistics about text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary containing text statistics
        """
        try:
            words = text.split()
            sentences = SearchTools.extract_sentences(text)
            
            stats = {
                'character_count': len(text),
                'word_count': len(words),
                'sentence_count': len(sentences),
                'average_word_length': sum(len(word) for word in words) / len(words) if words else 0,
                'average_sentence_length': len(words) / len(sentences) if sentences else 0,
                'analyzed_at': datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.warning(f"Error calculating text statistics: {e}")
            return {
                'character_count': 0,
                'word_count': 0,
                'sentence_count': 0,
                'average_word_length': 0,
                'average_sentence_length': 0,
                'analyzed_at': datetime.now().isoformat()
            }