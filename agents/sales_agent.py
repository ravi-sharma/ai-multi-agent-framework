"""Simplified sales agent implementation."""

import logging
from typing import Dict, Any, List
from datetime import datetime

from agents.base_agent import BaseAgent
from models.data_models import AgentResult, EmailMessage, SalesNotes

logger = logging.getLogger(__name__)


class SalesAgent(BaseAgent):
    """
    Specialized agent for processing sales-related communications.
    
    This agent analyzes email content and generates structured sales notes.
    """
    
    def __init__(self, name: str = "sales_agent", config: Dict[str, Any] = None):
        """
        Initialize the sales agent.
        
        Args:
            name: Agent name
            config: Agent configuration
        """
        super().__init__(name, config)
        logger.info(f"Initialized sales agent '{self.name}'")
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Process input data for sales analysis.
        
        Args:
            input_data: Dictionary containing email data and other context
            
        Returns:
            AgentResult with sales processing outcome
        """
        start_time = datetime.now()
        
        try:
            # Validate input
            if not self.validate_input(input_data):
                return AgentResult(
                    success=False,
                    output={},
                    agent_name=self.name,
                    error_message="Invalid input data for sales agent",
                    execution_time=0.0
                )
            
            # Process email data
            email_data = input_data.get('data', {}).get('email', {})
            
            # Create EmailMessage object
            email_message = EmailMessage(
                subject=email_data.get('subject', ''),
                sender=email_data.get('sender', ''),
                recipient=email_data.get('recipient', ''),
                body=email_data.get('body', ''),
                headers=email_data.get('headers', {}),
                timestamp=datetime.now()
            )
            
            # Extract customer information
            customer_info = self._extract_customer_info(email_message)
            
            # Analyze intent
            intent_analysis = self._analyze_intent(email_message)
            
            # Generate sales notes
            sales_notes = self._generate_sales_notes(email_message, customer_info, intent_analysis)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Create final output
            final_output = {
                'agent_type': 'sales',
                'customer_email': customer_info['email'],
                'customer_domain': customer_info['domain'],
                'primary_intent': intent_analysis.get('primary_intent', 'unknown'),
                'urgency_level': sales_notes.urgency_level,
                'requires_human_review': sales_notes.follow_up_required or sales_notes.urgency_level in ['high', 'critical'],
                'sales_notes': sales_notes.to_dict(),
                'processing_notes': [
                    f"Processed email from {customer_info['email']}",
                    f"Identified intent: {intent_analysis.get('primary_intent', 'unknown')}",
                    f"Urgency level: {sales_notes.urgency_level}",
                    f"Follow-up required: {sales_notes.follow_up_required}"
                ]
            }
            
            return AgentResult(
                success=True,
                output=final_output,
                agent_name=self.name,
                execution_time=execution_time,
                notes=final_output['processing_notes'],
                requires_human_review=final_output['requires_human_review']
            )
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Sales agent processing failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                output={},
                agent_name=self.name,
                error_message=str(e),
                execution_time=execution_time
            )
    
    def _extract_customer_info(self, email_message: EmailMessage) -> Dict[str, Any]:
        """
        Extract customer information from the email.
        
        Args:
            email_message: Email message to analyze
            
        Returns:
            Dictionary containing customer information
        """
        customer_info = {
            'email': email_message.sender,
            'domain': email_message.sender.split('@')[1] if '@' in email_message.sender else '',
            'communication_timestamp': email_message.timestamp.isoformat() if email_message.timestamp else datetime.now().isoformat()
        }
        
        # Basic extraction from email content
        body_lower = email_message.body.lower()
        
        # Try to extract company name (simple heuristics)
        if 'from' in body_lower and 'company' in body_lower:
            # Look for patterns like "I'm from XYZ Company"
            import re
            company_pattern = r'from\s+([A-Z][a-zA-Z\s]+(?:Inc|LLC|Corp|Company|Co))'
            match = re.search(company_pattern, email_message.body)
            if match:
                customer_info['company_name'] = match.group(1).strip()
        
        return customer_info
    
    def _analyze_intent(self, email_message: EmailMessage) -> Dict[str, Any]:
        """
        Analyze customer intent from email content.
        
        Args:
            email_message: Email message to analyze
            
        Returns:
            Dictionary containing intent analysis
        """
        text = f"{email_message.subject} {email_message.body}".lower()
        
        # Define intent keywords
        intent_keywords = {
            'purchase': ['buy', 'purchase', 'order', 'acquire', 'get', 'need'],
            'pricing': ['price', 'cost', 'quote', 'pricing', 'budget', 'fee'],
            'demo': ['demo', 'demonstration', 'trial', 'test', 'preview'],
            'information': ['info', 'information', 'details', 'learn', 'about'],
            'support': ['help', 'support', 'issue', 'problem', 'trouble'],
            'partnership': ['partner', 'partnership', 'collaborate', 'integration']
        }
        
        urgency_keywords = ['urgent', 'asap', 'immediately', 'quickly', 'rush', 'deadline']
        
        # Count keyword matches
        intent_scores = {}
        for intent, keywords in intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                intent_scores[intent] = score
        
        # Determine primary intent
        primary_intent = max(intent_scores.keys(), key=lambda k: intent_scores[k]) if intent_scores else 'general_inquiry'
        
        # Check urgency
        urgency_score = sum(1 for keyword in urgency_keywords if keyword in text)
        urgency_level = 'high' if urgency_score > 0 else 'medium' if primary_intent in ['purchase', 'pricing'] else 'low'
        
        return {
            'primary_intent': primary_intent,
            'intent_scores': intent_scores,
            'urgency_level': urgency_level,
            'urgency_score': urgency_score
        }
    
    def _generate_sales_notes(self, email_message: EmailMessage, customer_info: Dict[str, Any], 
                            intent_analysis: Dict[str, Any]) -> SalesNotes:
        """
        Generate structured sales notes.
        
        Args:
            email_message: Email message
            customer_info: Customer information
            intent_analysis: Intent analysis results
            
        Returns:
            SalesNotes object
        """
        # Extract problem summary
        customer_problem = f"Customer inquiry from {customer_info['email']} regarding {intent_analysis.get('primary_intent', 'general inquiry')}"
        
        # Generate basic solution
        intent = intent_analysis.get('primary_intent', 'general_inquiry')
        solution_map = {
            'purchase': 'Provide product information and pricing, schedule sales call',
            'pricing': 'Send detailed pricing information and schedule consultation',
            'demo': 'Schedule product demonstration and trial setup',
            'information': 'Provide comprehensive product information and resources',
            'support': 'Route to technical support team for assistance',
            'partnership': 'Connect with business development team'
        }
        proposed_solution = solution_map.get(intent, 'Review inquiry and provide appropriate response')
        
        # Determine urgency and follow-up
        urgency_level = intent_analysis.get('urgency_level', 'medium')
        follow_up_required = urgency_level in ['high', 'critical'] or intent in ['purchase', 'pricing']
        
        # Create key points
        key_points = [
            f"Intent: {intent}",
            f"Customer: {customer_info['email']}",
            f"Subject: {email_message.subject}"
        ]
        
        if customer_info.get('company_name'):
            key_points.append(f"Company: {customer_info['company_name']}")
        
        # Create next steps
        next_steps = []
        if follow_up_required:
            next_steps.append("Schedule follow-up call within 24 hours")
        if intent == 'pricing':
            next_steps.append("Prepare detailed pricing proposal")
        if intent == 'demo':
            next_steps.append("Set up demo environment")
        
        return SalesNotes(
            customer_problem=customer_problem,
            proposed_solution=proposed_solution,
            urgency_level=urgency_level,
            follow_up_required=follow_up_required,
            key_points=key_points,
            customer_info=customer_info,
            next_steps=next_steps
        )
    
    def get_workflow_config(self):
        """Get the workflow configuration for this agent."""
        return {
            "agent_name": self.name,
            "workflow_type": "simple",
            "max_retries": 3,
            "timeout": 180,
            "retry_delay": 2.0
        }
    
    def get_required_llm_capabilities(self) -> List[str]:
        """Get the list of LLM capabilities required by this agent."""
        return ['text_generation', 'analysis']
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data before processing.
        
        Args:
            input_data: Dictionary containing the data to validate
            
        Returns:
            True if input is valid, False otherwise
        """
        if not isinstance(input_data, dict):
            return False
        
        # Check for required structure
        if 'data' not in input_data:
            return False
        
        data = input_data['data']
        if not isinstance(data, dict):
            return False
        
        # For sales agent, we expect email data
        if 'email' not in data:
            return False
        
        email_data = data['email']
        if not isinstance(email_data, dict):
            return False
        
        # Must have either subject or body
        if not email_data.get('subject') and not email_data.get('body'):
            return False
        
        return True