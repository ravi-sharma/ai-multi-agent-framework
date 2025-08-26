"""Email processing and analysis tools."""

import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from email.utils import parseaddr

logger = logging.getLogger(__name__)


class EmailTools:
    """Tools for email processing and analysis."""
    
    @staticmethod
    def extract_email_metadata(email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from email data.
        
        Args:
            email_data: Raw email data
            
        Returns:
            Dictionary containing extracted metadata
        """
        metadata = {
            'sender_domain': '',
            'recipient_domain': '',
            'subject_length': 0,
            'body_length': 0,
            'has_attachments': False,
            'is_reply': False,
            'is_forward': False,
            'urgency_indicators': [],
            'extracted_at': datetime.now().isoformat()
        }
        
        try:
            # Extract sender domain
            sender = email_data.get('sender', '')
            if '@' in sender:
                metadata['sender_domain'] = sender.split('@')[1]
            
            # Extract recipient domain
            recipient = email_data.get('recipient', '')
            if '@' in recipient:
                metadata['recipient_domain'] = recipient.split('@')[1]
            
            # Subject analysis
            subject = email_data.get('subject', '')
            metadata['subject_length'] = len(subject)
            metadata['is_reply'] = subject.lower().startswith(('re:', 'reply:'))
            metadata['is_forward'] = subject.lower().startswith(('fwd:', 'fw:', 'forward:'))
            
            # Body analysis
            body = email_data.get('body', '')
            metadata['body_length'] = len(body)
            
            # Check for attachments
            attachments = email_data.get('attachments', [])
            metadata['has_attachments'] = len(attachments) > 0
            
            # Detect urgency indicators
            urgency_keywords = [
                'urgent', 'asap', 'immediately', 'quickly', 'rush', 
                'deadline', 'critical', 'emergency', 'priority'
            ]
            
            text_to_check = f"{subject} {body}".lower()
            metadata['urgency_indicators'] = [
                keyword for keyword in urgency_keywords 
                if keyword in text_to_check
            ]
            
        except Exception as e:
            logger.warning(f"Error extracting email metadata: {e}")
        
        return metadata
    
    @staticmethod
    def extract_contact_info(email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract contact information from email content.
        
        Args:
            email_data: Email data to analyze
            
        Returns:
            Dictionary containing extracted contact information
        """
        contact_info = {
            'emails': [],
            'phone_numbers': [],
            'names': [],
            'companies': [],
            'extracted_at': datetime.now().isoformat()
        }
        
        try:
            body = email_data.get('body', '')
            
            # Extract email addresses
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, body)
            contact_info['emails'] = list(set(emails))
            
            # Extract phone numbers (basic patterns)
            phone_patterns = [
                r'\b\d{3}-\d{3}-\d{4}\b',  # 123-456-7890
                r'\b\(\d{3}\)\s*\d{3}-\d{4}\b',  # (123) 456-7890
                r'\b\d{3}\.\d{3}\.\d{4}\b',  # 123.456.7890
                r'\b\d{10}\b'  # 1234567890
            ]
            
            phone_numbers = []
            for pattern in phone_patterns:
                phones = re.findall(pattern, body)
                phone_numbers.extend(phones)
            
            contact_info['phone_numbers'] = list(set(phone_numbers))
            
            # Extract potential company names (basic heuristics)
            company_indicators = [
                r'([A-Z][a-z]+ (?:Inc|LLC|Corp|Corporation|Company|Co)\.?)',
                r'([A-Z][a-z]+ (?:Technologies|Tech|Solutions|Systems|Services))',
                r'([A-Z][a-z]+ & [A-Z][a-z]+)'
            ]
            
            companies = []
            for pattern in company_indicators:
                matches = re.findall(pattern, body)
                companies.extend(matches)
            
            contact_info['companies'] = list(set(companies))
            
        except Exception as e:
            logger.warning(f"Error extracting contact info: {e}")
        
        return contact_info
    
    @staticmethod
    def classify_email_type(email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify the type of email based on content analysis.
        
        Args:
            email_data: Email data to classify
            
        Returns:
            Dictionary containing classification results
        """
        classification = {
            'primary_type': 'general',
            'confidence': 0.0,
            'indicators': [],
            'classified_at': datetime.now().isoformat()
        }
        
        try:
            subject = email_data.get('subject', '').lower()
            body = email_data.get('body', '').lower()
            text = f"{subject} {body}"
            
            # Define classification patterns
            patterns = {
                'sales': {
                    'keywords': ['buy', 'purchase', 'price', 'quote', 'demo', 'trial', 'sales'],
                    'weight': 1.0
                },
                'support': {
                    'keywords': ['help', 'issue', 'problem', 'error', 'bug', 'support', 'trouble'],
                    'weight': 1.0
                },
                'billing': {
                    'keywords': ['invoice', 'payment', 'billing', 'charge', 'refund', 'subscription'],
                    'weight': 1.0
                },
                'partnership': {
                    'keywords': ['partner', 'collaboration', 'integrate', 'api', 'partnership'],
                    'weight': 0.8
                },
                'feedback': {
                    'keywords': ['feedback', 'review', 'suggestion', 'improvement', 'feature'],
                    'weight': 0.7
                }
            }
            
            # Calculate scores for each type
            scores = {}
            for email_type, config in patterns.items():
                score = 0
                matched_keywords = []
                
                for keyword in config['keywords']:
                    if keyword in text:
                        score += config['weight']
                        matched_keywords.append(keyword)
                
                if score > 0:
                    scores[email_type] = {
                        'score': score,
                        'keywords': matched_keywords
                    }
            
            # Determine primary type
            if scores:
                primary_type = max(scores.keys(), key=lambda k: scores[k]['score'])
                max_score = scores[primary_type]['score']
                
                # Normalize confidence (simple approach)
                total_keywords = sum(len(config['keywords']) for config in patterns.values())
                confidence = min(max_score / total_keywords, 1.0)
                
                classification.update({
                    'primary_type': primary_type,
                    'confidence': confidence,
                    'indicators': scores[primary_type]['keywords'],
                    'all_scores': scores
                })
            
        except Exception as e:
            logger.warning(f"Error classifying email: {e}")
        
        return classification
    
    @staticmethod
    def extract_key_phrases(email_data: Dict[str, Any], max_phrases: int = 10) -> List[str]:
        """
        Extract key phrases from email content.
        
        Args:
            email_data: Email data to analyze
            max_phrases: Maximum number of phrases to return
            
        Returns:
            List of key phrases
        """
        try:
            subject = email_data.get('subject', '')
            body = email_data.get('body', '')
            text = f"{subject} {body}"
            
            # Simple key phrase extraction (can be enhanced with NLP)
            # Remove common words and extract meaningful phrases
            common_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
                'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
                'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you',
                'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
            }
            
            # Extract words and phrases
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
            filtered_words = [word for word in words if word not in common_words]
            
            # Count frequency
            word_freq = {}
            for word in filtered_words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # Sort by frequency and return top phrases
            key_phrases = sorted(word_freq.keys(), key=lambda k: word_freq[k], reverse=True)
            return key_phrases[:max_phrases]
            
        except Exception as e:
            logger.warning(f"Error extracting key phrases: {e}")
            return []
    
    @staticmethod
    def validate_email_format(email_address: str) -> bool:
        """
        Validate email address format.
        
        Args:
            email_address: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic email validation
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(pattern, email_address))
        except Exception:
            return False
    
    @staticmethod
    def parse_email_address(email_string: str) -> Dict[str, str]:
        """
        Parse email address string to extract name and email.
        
        Args:
            email_string: Email string (e.g., "John Doe <john@example.com>")
            
        Returns:
            Dictionary with 'name' and 'email' keys
        """
        try:
            name, email = parseaddr(email_string)
            return {
                'name': name.strip() if name else '',
                'email': email.strip() if email else email_string.strip()
            }
        except Exception as e:
            logger.warning(f"Error parsing email address: {e}")
            return {
                'name': '',
                'email': email_string.strip()
            }