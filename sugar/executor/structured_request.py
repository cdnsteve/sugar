"""
Structured Request Format for Claude Code CLI Integration

Provides unified request/response format for both basic Claude and agent mode interactions.
"""

import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class ExecutionMode(Enum):
    """Claude execution modes"""

    BASIC = "basic"
    AGENT = "agent"
    CONTINUATION = "continuation"


class AgentType(Enum):
    """Available Claude agent types - extensible for user's local agents"""

    GENERAL_PURPOSE = "general-purpose"
    CODE_REVIEWER = "code-reviewer"
    TECH_LEAD = "tech-lead"
    SOCIAL_MEDIA_STRATEGIST = "social-media-growth-strategist"
    STATUSLINE_SETUP = "statusline-setup"
    OUTPUT_STYLE_SETUP = "output-style-setup"

    @classmethod
    def from_string(cls, agent_name: str) -> Optional["AgentType"]:
        """Get AgentType from string, supporting both known and custom agents"""
        # Try to find exact match in known agents
        for agent_type in cls:
            if agent_type.value == agent_name:
                return agent_type

        # For unknown agents, create a dynamic entry
        return DynamicAgentType(agent_name)

    @classmethod
    def get_available_agents(cls) -> List[str]:
        """Get list of all available agent names"""
        return [agent.value for agent in cls]


class DynamicAgentType:
    """Dynamic agent type for user-configured agents not in the enum"""

    def __init__(self, agent_name: str):
        self.value = agent_name
        self.name = agent_name.upper().replace("-", "_")

    def __str__(self):
        return self.value

    def __repr__(self):
        return f"DynamicAgentType('{self.value}')"

    def __eq__(self, other):
        if isinstance(other, DynamicAgentType):
            return self.value == other.value
        elif isinstance(other, AgentType):
            return self.value == other.value
        elif isinstance(other, str):
            return self.value == other
        return False


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
    agent_type: Optional[Union[AgentType, DynamicAgentType]] = None
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
    def from_work_item(
        cls,
        work_item: Dict[str, Any],
        execution_mode: ExecutionMode = ExecutionMode.BASIC,
    ) -> "StructuredRequest":
        """Create structured request from Sugar work item"""
        # Extract context information
        context = TaskContext(
            work_item_id=work_item["id"],
            source_type=work_item.get("source", "unknown"),
            priority=work_item.get("priority", 3),
            attempts=work_item.get("attempts", 0),
            files_involved=cls._extract_files_from_context(
                work_item.get("context", {})
            ),
            session_context=work_item.get("context", {}),
        )

        return cls(
            task_type=work_item["type"],
            title=work_item["title"],
            description=work_item.get("description", ""),
            execution_mode=execution_mode,
            context=context,
            continue_session=work_item.get("attempts", 0) > 1,  # Continue if retry
        )

    @staticmethod
    def _extract_files_from_context(context: Dict[str, Any]) -> Optional[List[str]]:
        """Extract file paths from work item context"""
        files = []

        # Check various context fields for file information
        if "source_file" in context:
            files.append(context["source_file"])

        if "files" in context:
            files.extend(context["files"])

        if "file" in context:
            files.append(context["file"])

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

    # Quality metrics
    response_quality_score: Optional[float] = None  # 0.0 to 1.0 quality rating
    confidence_level: Optional[str] = None  # high, medium, low

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
    def from_claude_output(
        cls,
        stdout: str,
        stderr: str,
        return_code: int,
        execution_time: float,
        agent_used: Optional[str] = None,
    ) -> "StructuredResponse":
        """Create structured response from raw Claude output with enhanced parsing"""
        success = return_code == 0 and not stderr.strip()

        # Try to parse structured JSON response from Claude
        try:
            # Look for JSON in stdout (Claude might output structured responses)
            lines = stdout.strip().split("\n")
            for line in reversed(lines):  # Check from end for JSON response
                if line.strip().startswith("{") and line.strip().endswith("}"):
                    claude_data = json.loads(line.strip())

                    return cls(
                        success=success,
                        execution_time=execution_time,
                        agent_used=agent_used,
                        stdout=stdout,
                        stderr=stderr,
                        return_code=return_code,
                        files_modified=claude_data.get("files_modified", []),
                        actions_taken=claude_data.get("actions_taken", []),
                        summary=claude_data.get("summary", ""),
                        continued_session=claude_data.get("continued_session", False),
                    )
        except (json.JSONDecodeError, KeyError):
            pass

        # Enhanced response parsing with agent-specific extraction
        quality_score, confidence_level = cls._assess_response_quality(
            stdout, stderr, return_code, agent_used, execution_time
        )

        return cls(
            success=success,
            execution_time=execution_time,
            agent_used=agent_used,
            stdout=stdout,
            stderr=stderr,
            return_code=return_code,
            summary=cls._extract_enhanced_summary(stdout, agent_used),
            actions_taken=cls._extract_enhanced_actions(stdout, agent_used),
            files_modified=cls._extract_files_from_output(stdout),
            response_quality_score=quality_score,
            confidence_level=confidence_level,
        )

    @staticmethod
    def _extract_summary_from_output(stdout: str) -> str:
        """Extract summary from Claude's text output"""
        lines = stdout.strip().split("\n")

        # Look for summary indicators
        for i, line in enumerate(lines):
            if any(
                indicator in line.lower()
                for indicator in ["summary:", "completed:", "result:"]
            ):
                # Take this line and a few following lines
                summary_lines = lines[i : i + 3]
                return " ".join(summary_lines).strip()

        # Fallback: first few lines or last few lines
        if len(lines) >= 3:
            return " ".join(lines[:3]).strip()

        return stdout[:200] + "..." if len(stdout) > 200 else stdout

    @staticmethod
    def _extract_actions_from_output(stdout: str) -> List[str]:
        """Extract action items from Claude's text output"""
        actions = []
        lines = stdout.strip().split("\n")

        for line in lines:
            line = line.strip()
            # Look for action indicators
            if any(
                line.startswith(prefix) for prefix in ["- ", "* ", "1. ", "2. ", "3."]
            ):
                actions.append(line)
            elif any(
                indicator in line.lower()
                for indicator in ["created", "modified", "updated", "fixed", "added"]
            ):
                actions.append(line)

        return actions[:10]  # Limit to first 10 actions

    @staticmethod
    def _extract_enhanced_summary(stdout: str, agent_used: Optional[str] = None) -> str:
        """Extract enhanced summary with agent-specific parsing"""
        if not stdout:
            return ""

        lines = stdout.strip().split("\n")

        # Agent-specific summary extraction patterns
        if agent_used == "tech-lead":
            # Look for strategic analysis and architectural insights
            for line in lines:
                if any(
                    phrase in line.lower()
                    for phrase in [
                        "analysis:",
                        "architectural",
                        "strategic approach",
                        "implementation strategy",
                        "design decision",
                        "technical solution",
                        "approach taken",
                        "solution architecture",
                    ]
                ):
                    return line.strip()

        elif agent_used == "code-reviewer":
            # Look for code quality insights and improvement recommendations
            for line in lines:
                if any(
                    phrase in line.lower()
                    for phrase in [
                        "code review",
                        "refactored",
                        "improved",
                        "optimized",
                        "cleaned up",
                        "better practices",
                        "code quality",
                        "maintainability",
                        "performance improvement",
                    ]
                ):
                    return line.strip()

        elif agent_used == "social-media-growth-strategist":
            # Look for engagement and growth insights
            for line in lines:
                if any(
                    phrase in line.lower()
                    for phrase in [
                        "engagement strategy",
                        "growth tactics",
                        "content strategy",
                        "audience",
                        "social media",
                        "followers",
                        "reach",
                        "viral potential",
                        "community building",
                    ]
                ):
                    return line.strip()

        # Fallback to general summary extraction
        return StructuredResponse._extract_summary_from_output(stdout)

    @staticmethod
    def _extract_enhanced_actions(
        stdout: str, agent_used: Optional[str] = None
    ) -> List[str]:
        """Extract enhanced actions with agent-specific patterns"""
        if not stdout:
            return []

        # Start with general action extraction
        actions = StructuredResponse._extract_actions_from_output(stdout)

        # Add agent-specific action patterns
        lines = stdout.strip().split("\n")

        if agent_used == "tech-lead":
            # Look for strategic and architectural actions
            for line in lines:
                if any(
                    phrase in line.lower()
                    for phrase in [
                        "designed",
                        "architected",
                        "planned",
                        "strategized",
                        "analyzed system",
                        "evaluated approach",
                        "considered alternatives",
                        "recommended solution",
                        "assessed impact",
                        "reviewed design",
                        "validated architecture",
                    ]
                ):
                    actions.append(line.strip())

        elif agent_used == "code-reviewer":
            # Look for code quality and review actions
            for line in lines:
                if any(
                    phrase in line.lower()
                    for phrase in [
                        "reviewed code",
                        "identified issues",
                        "suggested improvements",
                        "refactored",
                        "optimized performance",
                        "enhanced readability",
                        "improved structure",
                        "applied best practices",
                        "eliminated code smell",
                        "increased maintainability",
                    ]
                ):
                    actions.append(line.strip())

        elif agent_used == "social-media-growth-strategist":
            # Look for social media and growth actions
            for line in lines:
                if any(
                    phrase in line.lower()
                    for phrase in [
                        "created content",
                        "developed strategy",
                        "optimized for engagement",
                        "targeted audience",
                        "increased reach",
                        "built community",
                        "grew followers",
                        "analyzed metrics",
                        "improved conversion",
                        "enhanced visibility",
                    ]
                ):
                    actions.append(line.strip())

        # Remove duplicates and limit
        return list(dict.fromkeys(actions))[:12]  # Keep top 12 unique actions

    @staticmethod
    def _extract_files_from_output(stdout: str) -> List[str]:
        """Extract modified files from Claude output with enhanced detection"""
        if not stdout:
            return []

        files = []
        lines = stdout.strip().split("\n")

        for line in lines:
            line_lower = line.lower()

            # Look for explicit file operation mentions
            if (
                any(
                    phrase in line_lower
                    for phrase in [
                        "modified",
                        "updated",
                        "created",
                        "wrote to",
                        "saved to",
                        "edited",
                        "changed",
                        "added to",
                        "deleted from",
                    ]
                )
                or ":" in line
                and any(ext in line for ext in [".py", ".js", ".md", ".json", ".yaml"])
            ):
                # Extract file paths from the line
                import re

                # Match common file extensions and paths
                file_patterns = [
                    r"(\S+\.py\b)",  # Python files
                    r"(\S+\.js\b)",  # JavaScript files
                    r"(\S+\.ts\b)",  # TypeScript files
                    r"(\S+\.tsx\b)",  # TypeScript React files
                    r"(\S+\.jsx\b)",  # JavaScript React files
                    r"(\S+\.md\b)",  # Markdown files
                    r"(\S+\.txt\b)",  # Text files
                    r"(\S+\.json\b)",  # JSON files
                    r"(\S+\.yaml\b)",  # YAML files
                    r"(\S+\.yml\b)",  # YAML files
                    r"(\S+\.html\b)",  # HTML files
                    r"(\S+\.css\b)",  # CSS files
                    r"(\S+\.scss\b)",  # SCSS files
                    r"(\S+\.go\b)",  # Go files
                    r"(\S+\.rs\b)",  # Rust files
                    r"(\S+\.java\b)",  # Java files
                    r"(\S+\.cpp\b)",  # C++ files
                    r"(\S+\.c\b)",  # C files
                    r"(\S+\.h\b)",  # Header files
                ]

                for pattern in file_patterns:
                    matches = re.findall(pattern, line, re.IGNORECASE)
                    for match in matches:
                        clean_file = match.strip(".,;:()[]{}")
                        if clean_file and clean_file not in files:
                            files.append(clean_file)

        # Also look for tool usage patterns (Claude Code tools) and file lists
        for line in lines:
            if any(
                phrase in line
                for phrase in [
                    "Edit tool",
                    "Write tool",
                    "MultiEdit tool",
                    "NotebookEdit tool",
                ]
            ):
                # Look for file paths in the next few lines or in the same line
                import re

                path_match = re.search(r'["\']([^"\']+\.[a-zA-Z0-9]+)["\']', line)
                if path_match:
                    file_path = path_match.group(1)
                    if file_path not in files:
                        files.append(file_path)

            # Look for file listings (e.g., "- filename.py (description)")
            import re

            if line.strip().startswith("-") or line.strip().startswith("*"):
                # Extract files from bullet points
                for pattern in [
                    r"([a-zA-Z0-9_/]+\.py)\b",
                    r"([a-zA-Z0-9_/]+\.js)\b",
                    r"([a-zA-Z0-9_/]+\.md)\b",
                    r"([a-zA-Z0-9_/]+\.json)\b",
                    r"([a-zA-Z0-9_/]+\.yaml)\b",
                ]:
                    matches = re.findall(pattern, line)
                    for match in matches:
                        if match not in files:
                            files.append(match)

        return files[:15]  # Limit to first 15 files to prevent overflow

    @staticmethod
    def _assess_response_quality(
        stdout: str,
        stderr: str,
        return_code: int,
        agent_used: Optional[str] = None,
        execution_time: float = 0,
    ) -> tuple[float, str]:
        """Assess the quality of Claude's response and assign confidence level"""
        if not stdout:
            return 0.1, "low"

        quality_score = 0.0
        confidence_factors = []

        # Base score for successful execution
        if return_code == 0:
            quality_score += 0.3
            confidence_factors.append("successful_execution")

        # Check for meaningful content length
        meaningful_lines = [
            line.strip()
            for line in stdout.split("\n")
            if line.strip() and not line.startswith("#")
        ]
        if len(meaningful_lines) > 10:
            quality_score += 0.2
            confidence_factors.append("substantial_content")
        elif len(meaningful_lines) > 5:
            quality_score += 0.1

        # Check for code completion indicators
        completion_indicators = [
            "successfully",
            "completed",
            "implemented",
            "created",
            "updated",
            "fixed",
            "resolved",
            "added",
            "enhanced",
            "improved",
        ]
        stdout_lower = stdout.lower()
        completion_matches = sum(
            1 for indicator in completion_indicators if indicator in stdout_lower
        )
        quality_score += min(completion_matches * 0.05, 0.2)
        if completion_matches > 3:
            confidence_factors.append("strong_completion_signals")

        # Check for structured output (lists, explanations, code blocks)
        if any(pattern in stdout for pattern in ["```", "- ", "* ", "1. ", "2. "]):
            quality_score += 0.1
            confidence_factors.append("structured_output")

        # Agent-specific quality checks
        if agent_used:
            if agent_used == "tech-lead":
                # Look for strategic thinking indicators
                if any(
                    phrase in stdout_lower
                    for phrase in [
                        "analysis",
                        "approach",
                        "strategy",
                        "architecture",
                        "design",
                        "consider",
                    ]
                ):
                    quality_score += 0.1
                    confidence_factors.append("strategic_thinking")

            elif agent_used == "code-reviewer":
                # Look for review quality indicators
                if any(
                    phrase in stdout_lower
                    for phrase in [
                        "review",
                        "refactor",
                        "improve",
                        "optimize",
                        "best practice",
                        "maintainability",
                    ]
                ):
                    quality_score += 0.1
                    confidence_factors.append("thorough_review")

            elif agent_used == "social-media-growth-strategist":
                # Look for engagement and growth indicators
                if any(
                    phrase in stdout_lower
                    for phrase in [
                        "engagement",
                        "audience",
                        "growth",
                        "strategy",
                        "content",
                        "reach",
                    ]
                ):
                    quality_score += 0.1
                    confidence_factors.append("growth_focused")

        # Penalty for errors or warnings
        if stderr:
            quality_score -= 0.2

        # Check for execution time reasonableness
        if execution_time > 0:
            if 5 <= execution_time <= 120:  # Sweet spot: 5 seconds to 2 minutes
                quality_score += 0.05
            elif execution_time < 2:  # Too fast might indicate insufficient work
                quality_score -= 0.05
            elif execution_time > 300:  # Too slow might indicate problems
                quality_score -= 0.1

        # Normalize score to 0.0-1.0 range
        quality_score = max(0.0, min(1.0, quality_score))

        # Determine confidence level
        if quality_score >= 0.8:
            confidence = "high"
        elif quality_score >= 0.5:
            confidence = "medium"
        else:
            confidence = "low"

        return quality_score, confidence


class RequestBuilder:
    """Helper class for building structured requests"""

    @staticmethod
    def create_basic_request(work_item: Dict[str, Any]) -> StructuredRequest:
        """Create a basic (non-agent) structured request"""
        return StructuredRequest.from_work_item(work_item, ExecutionMode.BASIC)

    @staticmethod
    def create_agent_request(
        work_item: Dict[str, Any], agent_type: Union[AgentType, DynamicAgentType, str]
    ) -> StructuredRequest:
        """Create an agent mode structured request"""
        request = StructuredRequest.from_work_item(work_item, ExecutionMode.AGENT)

        # Handle string agent names by converting to appropriate type
        if isinstance(agent_type, str):
            request.agent_type = AgentType.from_string(agent_type)
        else:
            request.agent_type = agent_type

        return request

    @staticmethod
    def create_continuation_request(
        work_item: Dict[str, Any], previous_response: StructuredResponse
    ) -> StructuredRequest:
        """Create a continuation request based on previous response"""
        request = StructuredRequest.from_work_item(
            work_item, ExecutionMode.CONTINUATION
        )
        request.continue_session = True

        # Add previous context
        if request.context:
            request.context.previous_attempts = [previous_response.to_dict()]

        return request
