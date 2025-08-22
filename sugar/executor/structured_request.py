"""
Structured Request Format for Claude Code CLI Integration

Provides unified request/response format for both basic Claude and agent mode interactions.
"""
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class ExecutionMode(Enum):
    """Claude execution modes"""
    BASIC = "basic"
    AGENT = "agent"
    CONTINUATION = "continuation"


class AgentType(Enum):
    """Available Claude agent types"""
    GENERAL_PURPOSE = "general-purpose"
    CODE_REVIEWER = "code-reviewer" 
    TECH_LEAD = "tech-lead"
    SOCIAL_MEDIA_STRATEGIST = "social-media-growth-strategist"
    STATUSLINE_SETUP = "statusline-setup"
    OUTPUT_STYLE_SETUP = "output-style-setup"


@dataclass
class TaskContext:
    """Context information for task execution"""
    work_item_id: str
    source_type: str
    priority: int
    attempts: int
    files_involved: Optional[List[str]] = None
    repository_info: Optional[Dict[str, Any]] = None
    previous_attempts: Optional[List[Dict[str, Any]]] = None
    session_context: Optional[Dict[str, Any]] = None


@dataclass
class StructuredRequest:
    """Structured request format for Claude interactions"""
    # Core task information
    task_type: str  # bug_fix, feature, test, refactor, etc.
    title: str
    description: str
    
    # Execution configuration
    execution_mode: ExecutionMode
    agent_type: Optional[AgentType] = None
    agent_fallback: bool = True
    
    # Context and metadata
    context: Optional[TaskContext] = None
    timestamp: Optional[str] = None
    sugar_version: Optional[str] = None
    
    # Claude-specific options
    continue_session: bool = False
    timeout_seconds: int = 1800
    working_directory: Optional[str] = None
    
    def __post_init__(self):
        """Set defaults after initialization"""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
        
        if self.sugar_version is None:
            try:
                from ..__version__ import __version__
                self.sugar_version = __version__
            except ImportError:
                self.sugar_version = "unknown"
    
    def to_json(self) -> str:
        """Convert to JSON string for Claude input"""
        return json.dumps(asdict(self), indent=2, default=str)
    
    @classmethod
    def from_work_item(cls, work_item: Dict[str, Any], execution_mode: ExecutionMode = ExecutionMode.BASIC) -> 'StructuredRequest':
        """Create structured request from Sugar work item"""
        # Extract context information
        context = TaskContext(
            work_item_id=work_item['id'],
            source_type=work_item.get('source', 'unknown'),
            priority=work_item.get('priority', 3),
            attempts=work_item.get('attempts', 0),
            files_involved=cls._extract_files_from_context(work_item.get('context', {})),
            session_context=work_item.get('context', {})
        )
        
        return cls(
            task_type=work_item['type'],
            title=work_item['title'],
            description=work_item.get('description', ''),
            execution_mode=execution_mode,
            context=context,
            continue_session=work_item.get('attempts', 0) > 1  # Continue if retry
        )
    
    @staticmethod
    def _extract_files_from_context(context: Dict[str, Any]) -> Optional[List[str]]:
        """Extract file paths from work item context"""
        files = []
        
        # Check various context fields for file information
        if 'source_file' in context:
            files.append(context['source_file'])
        
        if 'files' in context:
            files.extend(context['files'])
            
        if 'file' in context:
            files.append(context['file'])
            
        return files if files else None


@dataclass 
class StructuredResponse:
    """Structured response format from Claude"""
    # Execution results
    success: bool
    execution_time: float
    agent_used: Optional[str] = None
    fallback_occurred: bool = False
    
    # Task results
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    files_modified: List[str] = None
    actions_taken: List[str] = None
    
    # Context and continuation
    summary: str = ""
    continued_session: bool = False
    session_updated: bool = False
    
    # Error handling
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    # Metadata
    timestamp: Optional[str] = None
    claude_version: Optional[str] = None
    
    def __post_init__(self):
        """Set defaults after initialization"""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
            
        if self.files_modified is None:
            self.files_modified = []
            
        if self.actions_taken is None:
            self.actions_taken = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for work queue storage"""
        return asdict(self)
    
    @classmethod
    def from_claude_output(cls, stdout: str, stderr: str, return_code: int, 
                          execution_time: float, agent_used: Optional[str] = None) -> 'StructuredResponse':
        """Create structured response from raw Claude output"""
        success = return_code == 0 and not stderr.strip()
        
        # Try to parse structured JSON response from Claude
        try:
            # Look for JSON in stdout (Claude might output structured responses)
            lines = stdout.strip().split('\n')
            for line in reversed(lines):  # Check from end for JSON response
                if line.strip().startswith('{') and line.strip().endswith('}'):
                    claude_data = json.loads(line.strip())
                    
                    return cls(
                        success=success,
                        execution_time=execution_time,
                        agent_used=agent_used,
                        stdout=stdout,
                        stderr=stderr,
                        return_code=return_code,
                        files_modified=claude_data.get('files_modified', []),
                        actions_taken=claude_data.get('actions_taken', []),
                        summary=claude_data.get('summary', ''),
                        continued_session=claude_data.get('continued_session', False)
                    )
        except (json.JSONDecodeError, KeyError):
            pass
            
        # Fallback to basic response parsing
        return cls(
            success=success,
            execution_time=execution_time,
            agent_used=agent_used,
            stdout=stdout,
            stderr=stderr,
            return_code=return_code,
            summary=cls._extract_summary_from_output(stdout),
            actions_taken=cls._extract_actions_from_output(stdout)
        )
    
    @staticmethod
    def _extract_summary_from_output(stdout: str) -> str:
        """Extract summary from Claude's text output"""
        lines = stdout.strip().split('\n')
        
        # Look for summary indicators
        for i, line in enumerate(lines):
            if any(indicator in line.lower() for indicator in ['summary:', 'completed:', 'result:']):
                # Take this line and a few following lines
                summary_lines = lines[i:i+3]
                return ' '.join(summary_lines).strip()
        
        # Fallback: first few lines or last few lines
        if len(lines) >= 3:
            return ' '.join(lines[:3]).strip()
        
        return stdout[:200] + "..." if len(stdout) > 200 else stdout
    
    @staticmethod
    def _extract_actions_from_output(stdout: str) -> List[str]:
        """Extract action items from Claude's text output"""
        actions = []
        lines = stdout.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for action indicators
            if any(line.startswith(prefix) for prefix in ['- ', '* ', '1. ', '2. ', '3.']):
                actions.append(line)
            elif any(indicator in line.lower() for indicator in ['created', 'modified', 'updated', 'fixed', 'added']):
                actions.append(line)
        
        return actions[:10]  # Limit to first 10 actions


class RequestBuilder:
    """Helper class for building structured requests"""
    
    @staticmethod
    def create_basic_request(work_item: Dict[str, Any]) -> StructuredRequest:
        """Create a basic (non-agent) structured request"""
        return StructuredRequest.from_work_item(work_item, ExecutionMode.BASIC)
    
    @staticmethod  
    def create_agent_request(work_item: Dict[str, Any], agent_type: AgentType) -> StructuredRequest:
        """Create an agent mode structured request"""
        request = StructuredRequest.from_work_item(work_item, ExecutionMode.AGENT)
        request.agent_type = agent_type
        return request
    
    @staticmethod
    def create_continuation_request(work_item: Dict[str, Any], previous_response: StructuredResponse) -> StructuredRequest:
        """Create a continuation request based on previous response"""
        request = StructuredRequest.from_work_item(work_item, ExecutionMode.CONTINUATION)
        request.continue_session = True
        
        # Add previous context
        if request.context:
            request.context.previous_attempts = [previous_response.to_dict()]
            
        return request