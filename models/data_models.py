"""Core data models for the AI Agent Framework."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
import json


@dataclass
class TriggerData:
    """Data structure for incoming triggers from various sources."""
    source: str  # 'webhook', 'email', 'api', etc.
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_field_value(self, field_path: str) -> Any:
        """
        Get a value from the data using dot notation.
        
        Args:
            field_path: Dot-separated path to the field (e.g., 'email.subject')
            
        Returns:
            The value at the specified path, or None if not found
        """
        parts = field_path.split('.')
        current = self.data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trigger data to dictionary format."""
        return {
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'metadata': self.metadata
        }
    
    def to_json(self, indent: Optional[int] = None) -> str:
        """Convert trigger data to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TriggerData':
        """Create TriggerData from dictionary."""
        return cls(
            source=data['source'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            data=data['data'],
            metadata=data.get('metadata', {})
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TriggerData':
        """Create TriggerData from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class EmailMessage:
    """Data structure for email messages."""
    subject: str
    sender: str
    recipient: str
    body: str
    headers: Dict[str, str] = field(default_factory=dict)
    attachments: List['Attachment'] = field(default_factory=list)
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert email message to dictionary format."""
        return {
            'subject': self.subject,
            'sender': self.sender,
            'recipient': self.recipient,
            'body': self.body,
            'headers': self.headers,
            'attachments': [att.to_dict() for att in self.attachments],
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    def to_json(self, indent: Optional[int] = None) -> str:
        """Convert email message to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailMessage':
        """Create EmailMessage from dictionary."""
        attachments = []
        if 'attachments' in data:
            attachments = [Attachment.from_dict(att) for att in data['attachments']]
        
        timestamp = None
        if data.get('timestamp'):
            timestamp = datetime.fromisoformat(data['timestamp'])
        
        return cls(
            subject=data['subject'],
            sender=data['sender'],
            recipient=data['recipient'],
            body=data['body'],
            headers=data.get('headers', {}),
            attachments=attachments,
            timestamp=timestamp
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'EmailMessage':
        """Create EmailMessage from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class Attachment:
    """Data structure for email attachments."""
    filename: str
    content_type: str
    size: int
    content: Optional[bytes] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert attachment to dictionary format."""
        return {
            'filename': self.filename,
            'content_type': self.content_type,
            'size': self.size,
            'has_content': self.content is not None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Attachment':
        """Create Attachment from dictionary."""
        return cls(
            filename=data['filename'],
            content_type=data['content_type'],
            size=data['size'],
            content=None  # Content not serialized for security/size reasons
        )


@dataclass
class AgentMatch:
    """Data structure for agent matching results."""
    agent_name: str
    criteria_name: str
    priority: int
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Data structure for agent execution results."""
    success: bool
    output: Dict[str, Any]
    notes: List[str] = field(default_factory=list)
    requires_human_review: bool = False
    execution_time: float = 0.0
    agent_name: str = ""
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_note(self, note: str) -> None:
        """Add a note to the result."""
        self.notes.append(note)
    
    def set_error(self, error_message: str) -> None:
        """Set error state and message."""
        self.success = False
        self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent result to dictionary format."""
        return {
            'success': self.success,
            'output': self.output,
            'notes': self.notes,
            'requires_human_review': self.requires_human_review,
            'execution_time': self.execution_time,
            'agent_name': self.agent_name,
            'error_message': self.error_message,
            'metadata': self.metadata
        }
    
    def to_json(self, indent: Optional[int] = None) -> str:
        """Convert agent result to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentResult':
        """Create AgentResult from dictionary."""
        return cls(
            success=data['success'],
            output=data['output'],
            notes=data.get('notes', []),
            requires_human_review=data.get('requires_human_review', False),
            execution_time=data.get('execution_time', 0.0),
            agent_name=data.get('agent_name', ''),
            error_message=data.get('error_message'),
            metadata=data.get('metadata', {})
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AgentResult':
        """Create AgentResult from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class SalesNotes:
    """Data structure for sales agent generated notes."""
    customer_problem: str
    proposed_solution: str
    urgency_level: str  # 'low', 'medium', 'high', 'critical'
    follow_up_required: bool
    key_points: List[str] = field(default_factory=list)
    customer_info: Dict[str, Any] = field(default_factory=dict)
    estimated_value: Optional[float] = None
    next_steps: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert sales notes to dictionary format."""
        return {
            'customer_problem': self.customer_problem,
            'proposed_solution': self.proposed_solution,
            'urgency_level': self.urgency_level,
            'follow_up_required': self.follow_up_required,
            'key_points': self.key_points,
            'customer_info': self.customer_info,
            'estimated_value': self.estimated_value,
            'next_steps': self.next_steps
        }
    
    def to_json(self, indent: Optional[int] = None) -> str:
        """Convert sales notes to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SalesNotes':
        """Create SalesNotes from dictionary."""
        return cls(
            customer_problem=data['customer_problem'],
            proposed_solution=data['proposed_solution'],
            urgency_level=data['urgency_level'],
            follow_up_required=data['follow_up_required'],
            key_points=data.get('key_points', []),
            customer_info=data.get('customer_info', {}),
            estimated_value=data.get('estimated_value'),
            next_steps=data.get('next_steps', [])
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'SalesNotes':
        """Create SalesNotes from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class WorkflowContext:
    """Context information for workflow execution."""
    workflow_id: str
    agent_name: str
    trigger_data: TriggerData
    start_time: datetime
    current_step: str = ""
    step_history: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    
    def add_step(self, step_name: str) -> None:
        """Add a step to the execution history."""
        if self.current_step:
            self.step_history.append(self.current_step)
        self.current_step = step_name
    
    def set_variable(self, key: str, value: Any) -> None:
        """Set a workflow variable."""
        self.variables[key] = value
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a workflow variable."""
        return self.variables.get(key, default)


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    success: bool
    result: AgentResult
    context: WorkflowContext
    execution_time: float
    steps_completed: List[str]
    error_step: Optional[str] = None
    error_message: Optional[str] = None