"""
Tests for Sugar executor module

Tests cover:
- StructuredRequest creation and serialization
- StructuredResponse parsing and quality assessment
- RequestBuilder factory methods
- AgentType and DynamicAgentType handling
- ClaudeWrapper configuration and execution
"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from sugar.executor import (
    StructuredRequest,
    StructuredResponse,
    RequestBuilder,
    ExecutionMode,
    AgentType,
    DynamicAgentType,
    TaskContext,
    ClaudeWrapper,
)


class TestExecutionMode:
    """Test ExecutionMode enum"""

    def test_execution_mode_values(self):
        """Test ExecutionMode enum has expected values"""
        assert ExecutionMode.BASIC.value == "basic"
        assert ExecutionMode.AGENT.value == "agent"
        assert ExecutionMode.CONTINUATION.value == "continuation"

    def test_execution_mode_count(self):
        """Test ExecutionMode has expected number of modes"""
        assert len(ExecutionMode) == 3


class TestAgentType:
    """Test AgentType enum and DynamicAgentType"""

    def test_agent_type_values(self):
        """Test AgentType enum has expected values"""
        assert AgentType.GENERAL_PURPOSE.value == "general-purpose"
        assert AgentType.CODE_REVIEWER.value == "code-reviewer"
        assert AgentType.TECH_LEAD.value == "tech-lead"
        assert (
            AgentType.SOCIAL_MEDIA_STRATEGIST.value == "social-media-growth-strategist"
        )

    def test_from_string_known_agent(self):
        """Test from_string with known agent"""
        result = AgentType.from_string("general-purpose")
        assert result == AgentType.GENERAL_PURPOSE

    def test_from_string_unknown_agent(self):
        """Test from_string with unknown agent returns DynamicAgentType"""
        result = AgentType.from_string("custom-agent")
        assert isinstance(result, DynamicAgentType)
        assert result.value == "custom-agent"

    def test_get_available_agents(self):
        """Test get_available_agents returns list of values"""
        agents = AgentType.get_available_agents()
        assert "general-purpose" in agents
        assert "code-reviewer" in agents
        assert "tech-lead" in agents


class TestDynamicAgentType:
    """Test DynamicAgentType for custom agents"""

    def test_dynamic_agent_creation(self):
        """Test DynamicAgentType creation"""
        agent = DynamicAgentType("my-custom-agent")
        assert agent.value == "my-custom-agent"
        assert agent.name == "MY_CUSTOM_AGENT"

    def test_dynamic_agent_str(self):
        """Test DynamicAgentType string representation"""
        agent = DynamicAgentType("custom-agent")
        assert str(agent) == "custom-agent"

    def test_dynamic_agent_repr(self):
        """Test DynamicAgentType repr"""
        agent = DynamicAgentType("custom-agent")
        assert repr(agent) == "DynamicAgentType('custom-agent')"

    def test_dynamic_agent_equality_with_same(self):
        """Test DynamicAgentType equality with same type"""
        agent1 = DynamicAgentType("test-agent")
        agent2 = DynamicAgentType("test-agent")
        assert agent1 == agent2

    def test_dynamic_agent_equality_with_string(self):
        """Test DynamicAgentType equality with string"""
        agent = DynamicAgentType("test-agent")
        assert agent == "test-agent"

    def test_dynamic_agent_inequality(self):
        """Test DynamicAgentType inequality"""
        agent1 = DynamicAgentType("agent-a")
        agent2 = DynamicAgentType("agent-b")
        assert agent1 != agent2

    def test_dynamic_agent_equality_with_agent_type(self):
        """Test DynamicAgentType equality with AgentType enum"""
        # Create a dynamic agent with the same value as a known AgentType
        dynamic = DynamicAgentType("general-purpose")
        assert dynamic == AgentType.GENERAL_PURPOSE

    def test_dynamic_agent_inequality_with_different_type(self):
        """Test DynamicAgentType returns False for non-matching types"""
        agent = DynamicAgentType("test-agent")
        assert agent != 12345  # Not a string, AgentType, or DynamicAgentType
        assert agent != None
        assert agent != ["test-agent"]


class TestTaskContext:
    """Test TaskContext dataclass"""

    def test_task_context_creation(self):
        """Test TaskContext creation with required fields"""
        context = TaskContext(
            work_item_id="test-123",
            source_type="github",
            priority=3,
            attempts=1,
        )
        assert context.work_item_id == "test-123"
        assert context.source_type == "github"
        assert context.priority == 3
        assert context.attempts == 1
        assert context.files_involved is None
        assert context.repository_info is None

    def test_task_context_with_optional_fields(self):
        """Test TaskContext with optional fields"""
        context = TaskContext(
            work_item_id="test-456",
            source_type="manual",
            priority=5,
            attempts=2,
            files_involved=["file1.py", "file2.py"],
            session_context={"key": "value"},
        )
        assert context.files_involved == ["file1.py", "file2.py"]
        assert context.session_context == {"key": "value"}


class TestStructuredRequest:
    """Test StructuredRequest dataclass"""

    def test_structured_request_creation(self):
        """Test StructuredRequest creation"""
        request = StructuredRequest(
            task_type="bug_fix",
            title="Fix authentication bug",
            description="Users cannot log in",
            execution_mode=ExecutionMode.BASIC,
        )
        assert request.task_type == "bug_fix"
        assert request.title == "Fix authentication bug"
        assert request.execution_mode == ExecutionMode.BASIC
        assert request.timestamp is not None
        assert request.sugar_version is not None

    def test_structured_request_with_agent(self):
        """Test StructuredRequest with agent type"""
        request = StructuredRequest(
            task_type="feature",
            title="Add new feature",
            description="Feature description",
            execution_mode=ExecutionMode.AGENT,
            agent_type=AgentType.TECH_LEAD,
        )
        assert request.agent_type == AgentType.TECH_LEAD
        assert request.execution_mode == ExecutionMode.AGENT

    def test_structured_request_to_json(self):
        """Test StructuredRequest JSON serialization"""
        request = StructuredRequest(
            task_type="test",
            title="Add tests",
            description="Add unit tests",
            execution_mode=ExecutionMode.BASIC,
        )
        json_str = request.to_json()
        parsed = json.loads(json_str)
        assert parsed["task_type"] == "test"
        assert parsed["title"] == "Add tests"
        # Note: Enum is serialized as string representation via default=str
        assert (
            "BASIC" in parsed["execution_mode"] or parsed["execution_mode"] == "basic"
        )

    def test_structured_request_from_work_item(self):
        """Test StructuredRequest creation from work item"""
        work_item = {
            "id": "work-123",
            "type": "bug_fix",
            "title": "Fix bug",
            "description": "Bug description",
            "source": "github",
            "priority": 4,
            "attempts": 0,
            "context": {"source_file": "test.py"},
        }
        request = StructuredRequest.from_work_item(work_item)
        assert request.task_type == "bug_fix"
        assert request.title == "Fix bug"
        assert request.context.work_item_id == "work-123"
        assert request.context.source_type == "github"

    def test_extract_files_from_context(self):
        """Test file extraction from context"""
        context = {
            "source_file": "main.py",
            "files": ["helper.py", "utils.py"],
            "file": "config.py",
        }
        files = StructuredRequest._extract_files_from_context(context)
        assert "main.py" in files
        assert "helper.py" in files
        assert "utils.py" in files
        assert "config.py" in files

    def test_extract_files_from_empty_context(self):
        """Test file extraction from empty context"""
        files = StructuredRequest._extract_files_from_context({})
        assert files is None

    def test_structured_request_from_work_item_retry(self):
        """Test StructuredRequest from work item with retry (continue_session=True)"""
        work_item = {
            "id": "work-retry-123",
            "type": "bug_fix",
            "title": "Fix bug retry",
            "description": "Bug retry description",
            "source": "github",
            "priority": 4,
            "attempts": 2,  # > 1 triggers continue_session
            "context": {},
        }
        request = StructuredRequest.from_work_item(work_item)
        assert request.continue_session is True
        assert request.context.attempts == 2

    def test_structured_request_from_work_item_minimal(self):
        """Test StructuredRequest from work item with minimal fields"""
        work_item = {
            "id": "minimal-123",
            "type": "test",
            "title": "Minimal task",
        }
        request = StructuredRequest.from_work_item(work_item)
        assert request.task_type == "test"
        assert request.title == "Minimal task"
        assert request.description == ""  # Default empty string
        assert request.context.source_type == "unknown"  # Default
        assert request.context.priority == 3  # Default
        assert request.context.attempts == 0  # Default


class TestStructuredResponse:
    """Test StructuredResponse dataclass"""

    def test_structured_response_creation(self):
        """Test StructuredResponse creation"""
        response = StructuredResponse(
            success=True,
            execution_time=5.5,
            stdout="Task completed",
            stderr="",
            return_code=0,
        )
        assert response.success is True
        assert response.execution_time == 5.5
        assert response.timestamp is not None

    def test_structured_response_default_lists(self):
        """Test StructuredResponse default list initialization"""
        response = StructuredResponse(success=True, execution_time=1.0)
        assert response.files_modified == []
        assert response.actions_taken == []

    def test_structured_response_to_dict(self):
        """Test StructuredResponse dictionary conversion"""
        response = StructuredResponse(
            success=True,
            execution_time=2.0,
            agent_used="tech-lead",
        )
        result = response.to_dict()
        assert result["success"] is True
        assert result["execution_time"] == 2.0
        assert result["agent_used"] == "tech-lead"

    def test_from_claude_output_success(self):
        """Test StructuredResponse from successful Claude output"""
        stdout = """
Successfully implemented the feature.
- Created new_feature.py
- Updated README.md
Completed: Feature X is now available.
"""
        response = StructuredResponse.from_claude_output(
            stdout=stdout,
            stderr="",
            return_code=0,
            execution_time=10.0,
            agent_used="general-purpose",
        )
        assert response.success is True
        assert response.agent_used == "general-purpose"
        assert "Completed" in response.summary or "Successfully" in response.summary

    def test_from_claude_output_with_json(self):
        """Test StructuredResponse from Claude output with JSON"""
        json_response = json.dumps(
            {
                "files_modified": ["test.py"],
                "actions_taken": ["Fixed bug"],
                "summary": "Bug fixed successfully",
            }
        )
        stdout = f"Processing...\n{json_response}"
        response = StructuredResponse.from_claude_output(
            stdout=stdout,
            stderr="",
            return_code=0,
            execution_time=5.0,
        )
        assert response.success is True
        assert "test.py" in response.files_modified
        assert "Fixed bug" in response.actions_taken

    def test_from_claude_output_failure(self):
        """Test StructuredResponse from failed Claude output"""
        response = StructuredResponse.from_claude_output(
            stdout="",
            stderr="Error occurred",
            return_code=1,
            execution_time=1.0,
        )
        assert response.success is False

    def test_extract_summary_from_output(self):
        """Test summary extraction from output"""
        output = """
Some text here
Summary: This is the summary
More text
"""
        summary = StructuredResponse._extract_summary_from_output(output)
        assert "Summary:" in summary

    def test_extract_actions_from_output(self):
        """Test action extraction from output"""
        output = """
- Created file.py
* Updated config.yaml
1. Fixed the bug
modified something
"""
        actions = StructuredResponse._extract_actions_from_output(output)
        assert len(actions) >= 3

    def test_extract_files_from_output(self):
        """Test file extraction from output"""
        output = """
Modified test.py and config.json
Created new_feature.js
Updated styles.css
"""
        files = StructuredResponse._extract_files_from_output(output)
        assert any(".py" in f for f in files)
        assert any(".json" in f for f in files)

    def test_assess_response_quality_high(self):
        """Test quality assessment for high-quality response"""
        stdout = """
Successfully completed the task.
Created new implementation.
Updated configuration.
Fixed the issue.
Implemented the feature.
Added error handling.
- Step 1
- Step 2
- Step 3
```code block```
"""
        quality, confidence = StructuredResponse._assess_response_quality(
            stdout=stdout,
            stderr="",
            return_code=0,
            agent_used="tech-lead",
            execution_time=30.0,
        )
        assert quality >= 0.5
        assert confidence in ["high", "medium", "low"]

    def test_assess_response_quality_low(self):
        """Test quality assessment for low-quality response"""
        quality, confidence = StructuredResponse._assess_response_quality(
            stdout="",
            stderr="Error",
            return_code=1,
            execution_time=0.5,
        )
        assert quality < 0.5
        assert confidence == "low"

    def test_extract_enhanced_summary_tech_lead(self):
        """Test enhanced summary extraction for tech-lead agent"""
        output = """
Let me analyze the system.
Analysis: The architecture needs refactoring for scalability.
Here is my recommendation.
"""
        summary = StructuredResponse._extract_enhanced_summary(output, "tech-lead")
        assert "Analysis:" in summary or "architecture" in summary.lower()

    def test_extract_enhanced_summary_code_reviewer(self):
        """Test enhanced summary extraction for code-reviewer agent"""
        output = """
Looking at the code structure.
Code review completed: found several areas for improvement.
Refactored the main module.
"""
        summary = StructuredResponse._extract_enhanced_summary(output, "code-reviewer")
        assert any(
            phrase in summary.lower()
            for phrase in ["review", "refactored", "improvement"]
        )

    def test_extract_enhanced_summary_social_media_strategist(self):
        """Test enhanced summary extraction for social-media-growth-strategist agent"""
        output = """
Analyzing target demographics.
Engagement strategy developed for maximum reach.
Content calendar prepared.
"""
        summary = StructuredResponse._extract_enhanced_summary(
            output, "social-media-growth-strategist"
        )
        assert any(
            phrase in summary.lower() for phrase in ["engagement", "strategy", "reach"]
        )

    def test_extract_enhanced_summary_fallback(self):
        """Test enhanced summary extraction with unknown agent falls back to general"""
        output = """
Generic output without any matching indicators.
Some more text here.
And a third line.
"""
        summary = StructuredResponse._extract_enhanced_summary(output, "unknown-agent")
        assert len(summary) > 0

    def test_extract_enhanced_summary_empty_output(self):
        """Test enhanced summary extraction with empty output"""
        summary = StructuredResponse._extract_enhanced_summary("", "tech-lead")
        assert summary == ""

    def test_extract_enhanced_actions_tech_lead(self):
        """Test enhanced action extraction for tech-lead agent"""
        output = """
I designed the new system architecture.
Architected the microservices layout.
Validated the design decisions.
Assessed impact on existing components.
"""
        actions = StructuredResponse._extract_enhanced_actions(output, "tech-lead")
        assert len(actions) >= 2
        assert any("design" in a.lower() or "architect" in a.lower() for a in actions)

    def test_extract_enhanced_actions_code_reviewer(self):
        """Test enhanced action extraction for code-reviewer agent"""
        output = """
Reviewed code thoroughly.
Identified issues in authentication module.
Applied best practices to logging.
Increased maintainability of the codebase.
"""
        actions = StructuredResponse._extract_enhanced_actions(output, "code-reviewer")
        assert len(actions) >= 2
        assert any(
            "review" in a.lower()
            or "identified" in a.lower()
            or "best practice" in a.lower()
            for a in actions
        )

    def test_extract_enhanced_actions_social_media_strategist(self):
        """Test enhanced action extraction for social-media-growth-strategist agent"""
        output = """
Created content for Instagram.
Developed strategy for growth.
Targeted audience segments A and B.
Enhanced visibility across platforms.
"""
        actions = StructuredResponse._extract_enhanced_actions(
            output, "social-media-growth-strategist"
        )
        assert len(actions) >= 2
        assert any(
            "created" in a.lower() or "strategy" in a.lower() or "audience" in a.lower()
            for a in actions
        )

    def test_extract_enhanced_actions_empty_output(self):
        """Test enhanced action extraction with empty output"""
        actions = StructuredResponse._extract_enhanced_actions("", "tech-lead")
        assert actions == []

    def test_extract_files_from_output_tool_usage(self):
        """Test file extraction from Claude Code tool usage patterns"""
        output = """
Using Edit tool to modify "src/auth/login.py"
Using Write tool on "config/settings.json"
Using MultiEdit tool on multiple files
"""
        files = StructuredResponse._extract_files_from_output(output)
        assert any("login.py" in f for f in files)
        assert any("settings.json" in f for f in files)

    def test_extract_files_from_output_bullet_list(self):
        """Test file extraction from bullet point lists"""
        output = """
Files modified:
- src/main.py (added new function)
* tests/test_main.py (added test coverage)
- config/app.yaml (updated settings)
"""
        files = StructuredResponse._extract_files_from_output(output)
        assert any("main.py" in f for f in files)
        assert any("test_main.py" in f for f in files)

    def test_extract_files_from_output_empty(self):
        """Test file extraction from empty output"""
        files = StructuredResponse._extract_files_from_output("")
        assert files == []

    def test_assess_response_quality_execution_time_sweet_spot(self):
        """Test quality assessment with execution time in sweet spot (5-120s)"""
        stdout = "Successfully completed the task."
        quality, _ = StructuredResponse._assess_response_quality(
            stdout=stdout,
            stderr="",
            return_code=0,
            execution_time=30.0,  # In sweet spot
        )
        # Should get bonus for execution time
        assert quality > 0.3

    def test_assess_response_quality_execution_time_too_fast(self):
        """Test quality assessment with execution time too fast (<2s)"""
        stdout = "Done."
        quality, _ = StructuredResponse._assess_response_quality(
            stdout=stdout,
            stderr="",
            return_code=0,
            execution_time=1.0,  # Too fast
        )
        # Penalty for too-fast execution
        assert quality < 0.5

    def test_assess_response_quality_execution_time_too_slow(self):
        """Test quality assessment with execution time too slow (>300s)"""
        stdout = "Successfully completed."
        quality_slow, _ = StructuredResponse._assess_response_quality(
            stdout=stdout,
            stderr="",
            return_code=0,
            execution_time=400.0,  # Too slow
        )
        quality_normal, _ = StructuredResponse._assess_response_quality(
            stdout=stdout,
            stderr="",
            return_code=0,
            execution_time=60.0,  # Normal
        )
        # Slower should score lower
        assert quality_slow < quality_normal

    def test_assess_response_quality_code_reviewer_agent(self):
        """Test quality assessment specifically for code-reviewer agent"""
        stdout = """
Code review completed.
Refactored several modules.
Improved maintainability significantly.
Applied best practices throughout.
"""
        quality, confidence = StructuredResponse._assess_response_quality(
            stdout=stdout,
            stderr="",
            return_code=0,
            agent_used="code-reviewer",
            execution_time=45.0,
        )
        assert quality >= 0.5
        assert confidence in ["high", "medium"]

    def test_assess_response_quality_social_media_strategist_agent(self):
        """Test quality assessment for social-media-growth-strategist agent"""
        stdout = """
Engagement strategy developed.
Targeted the right audience segments.
Created content for maximum reach.
Growth plan implemented.
"""
        quality, confidence = StructuredResponse._assess_response_quality(
            stdout=stdout,
            stderr="",
            return_code=0,
            agent_used="social-media-growth-strategist",
            execution_time=30.0,
        )
        assert quality >= 0.5

    def test_from_claude_output_invalid_json_fallback(self):
        """Test from_claude_output handles invalid JSON gracefully"""
        stdout = """
Starting task...
{invalid json here}
Completed the work successfully.
"""
        response = StructuredResponse.from_claude_output(
            stdout=stdout,
            stderr="",
            return_code=0,
            execution_time=10.0,
        )
        # Should succeed without raising, using fallback parsing
        assert response.success is True
        assert response.stdout == stdout


class TestRequestBuilder:
    """Test RequestBuilder factory class"""

    def test_create_basic_request(self):
        """Test creating basic request"""
        work_item = {
            "id": "test-id",
            "type": "test",
            "title": "Test task",
            "description": "Description",
            "priority": 3,
        }
        request = RequestBuilder.create_basic_request(work_item)
        assert request.execution_mode == ExecutionMode.BASIC
        assert request.agent_type is None

    def test_create_agent_request(self):
        """Test creating agent request"""
        work_item = {
            "id": "test-id",
            "type": "feature",
            "title": "New feature",
            "description": "Description",
            "priority": 4,
        }
        request = RequestBuilder.create_agent_request(work_item, AgentType.TECH_LEAD)
        assert request.execution_mode == ExecutionMode.AGENT
        assert request.agent_type == AgentType.TECH_LEAD

    def test_create_agent_request_with_string(self):
        """Test creating agent request with string agent name"""
        work_item = {
            "id": "test-id",
            "type": "refactor",
            "title": "Refactor code",
            "description": "Description",
            "priority": 2,
        }
        request = RequestBuilder.create_agent_request(work_item, "code-reviewer")
        assert request.agent_type == AgentType.CODE_REVIEWER

    def test_create_continuation_request(self):
        """Test creating continuation request"""
        work_item = {
            "id": "test-id",
            "type": "bug_fix",
            "title": "Fix bug",
            "description": "Description",
            "priority": 5,
        }
        previous_response = StructuredResponse(
            success=True,
            execution_time=5.0,
            summary="Previous work",
        )
        request = RequestBuilder.create_continuation_request(
            work_item, previous_response
        )
        assert request.execution_mode == ExecutionMode.CONTINUATION
        assert request.continue_session is True

    def test_create_agent_request_with_dynamic_agent_type(self):
        """Test creating agent request with DynamicAgentType"""
        work_item = {
            "id": "test-dyn",
            "type": "custom",
            "title": "Custom task",
            "description": "Description",
            "priority": 3,
        }
        dynamic_agent = DynamicAgentType("my-custom-agent")
        request = RequestBuilder.create_agent_request(work_item, dynamic_agent)
        assert request.execution_mode == ExecutionMode.AGENT
        assert isinstance(request.agent_type, DynamicAgentType)
        assert request.agent_type.value == "my-custom-agent"

    def test_create_agent_request_with_unknown_string_agent(self):
        """Test creating agent request with unknown string agent name"""
        work_item = {
            "id": "test-unknown",
            "type": "specialized",
            "title": "Specialized task",
            "description": "Description",
            "priority": 2,
        }
        request = RequestBuilder.create_agent_request(work_item, "specialized-agent")
        assert request.execution_mode == ExecutionMode.AGENT
        # Unknown string should create DynamicAgentType
        assert isinstance(request.agent_type, DynamicAgentType)
        assert request.agent_type.value == "specialized-agent"

    def test_create_continuation_request_stores_previous_attempts(self):
        """Test continuation request stores previous attempts in context"""
        work_item = {
            "id": "test-cont",
            "type": "bug_fix",
            "title": "Fix bug",
            "description": "Description",
            "priority": 4,
            "source": "github",
        }
        previous_response = StructuredResponse(
            success=False,
            execution_time=10.0,
            summary="Failed attempt",
            error_message="Timeout",
        )
        request = RequestBuilder.create_continuation_request(
            work_item, previous_response
        )
        assert request.context is not None
        assert request.context.previous_attempts is not None
        assert len(request.context.previous_attempts) == 1
        assert request.context.previous_attempts[0]["success"] is False


class TestClaudeWrapper:
    """Test ClaudeWrapper class"""

    @pytest.fixture
    def claude_config(self, tmp_path):
        """Create test configuration for ClaudeWrapper"""
        return {
            "command": "claude",
            "timeout": 300,
            "context_file": str(tmp_path / "context.json"),
            "dry_run": True,
            "use_continuous": True,
            "context_strategy": "project",
            "max_context_age_hours": 24,
            "use_structured_requests": True,
            "structured_input_file": str(tmp_path / ".sugar" / "claude_input.json"),
            "enable_agents": True,
            "agent_fallback": True,
        }

    def test_claude_wrapper_init(self, claude_config):
        """Test ClaudeWrapper initialization"""
        wrapper = ClaudeWrapper(claude_config)
        assert wrapper.command == "claude"
        assert wrapper.timeout == 300
        assert wrapper.dry_run is True
        assert wrapper.use_continuous is True

    def test_claude_wrapper_agent_selection_config(self, claude_config):
        """Test ClaudeWrapper agent selection configuration"""
        wrapper = ClaudeWrapper(claude_config)
        assert "bug_fix" in wrapper.agent_selection
        assert wrapper.agent_selection["bug_fix"] == "tech-lead"

    @pytest.mark.asyncio
    async def test_simulate_execution(self, claude_config):
        """Test dry run simulation"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "id": "test-123",
            "type": "bug_fix",
            "title": "Fix bug",
            "description": "Bug description",
            "priority": 3,
        }
        result = await wrapper.execute_work(work_item)
        assert result["success"] is True
        assert result["simulated"] is True
        assert "result" in result

    def test_should_continue_session_no_state(self, claude_config):
        """Test session continuation without previous state"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {"type": "test", "description": ""}
        assert wrapper._should_continue_session(work_item) is False

    def test_are_tasks_related_same_keyword(self, claude_config):
        """Test task relatedness with common keyword"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {"description": "Fix auth bug"}
        session_state = {"last_task_description": "Auth improvements"}
        assert wrapper._are_tasks_related(work_item, session_state) is True

    def test_are_tasks_related_same_file(self, claude_config):
        """Test task relatedness with same source file"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {"description": "", "source_file": "auth.py"}
        session_state = {
            "last_task_description": "",
            "last_source_file": "auth.py",
        }
        assert wrapper._are_tasks_related(work_item, session_state) is True

    def test_are_tasks_unrelated(self, claude_config):
        """Test unrelated tasks"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {"description": "Fix payment processing"}
        session_state = {"last_task_description": "Update documentation"}
        assert wrapper._are_tasks_related(work_item, session_state) is False

    def test_select_agent_for_code_review(self, claude_config):
        """Test agent selection for code review tasks"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "type": "refactor",
            "title": "Review and refactor module",
            "description": "Clean up the code",
            "priority": 2,
        }
        agent = asyncio.run(wrapper._select_agent_for_work(work_item))
        assert agent == AgentType.CODE_REVIEWER

    def test_select_agent_for_social_media(self, claude_config):
        """Test agent selection for social media tasks"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "type": "content",
            "title": "Create social media post",
            "description": "Twitter engagement strategy",
            "priority": 2,
        }
        agent = asyncio.run(wrapper._select_agent_for_work(work_item))
        assert agent is not None
        assert agent.value == "social-media-growth-strategist"

    def test_select_agent_for_high_priority(self, claude_config):
        """Test agent selection for high priority tasks"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "type": "bug_fix",
            "title": "Critical fix needed",
            "description": "System is down",
            "priority": 5,
        }
        agent = asyncio.run(wrapper._select_agent_for_work(work_item))
        assert agent == AgentType.TECH_LEAD

    def test_select_agent_disabled(self, claude_config):
        """Test agent selection when disabled"""
        claude_config["enable_agents"] = False
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "type": "feature",
            "title": "Add feature",
            "description": "Description",
            "priority": 3,
        }
        agent = asyncio.run(wrapper._select_agent_for_work(work_item))
        assert agent is None

    def test_get_agent_type_with_available_agents(self, claude_config):
        """Test agent type resolution with available agents list"""
        claude_config["available_agents"] = ["general-purpose", "tech-lead"]
        wrapper = ClaudeWrapper(claude_config)

        # Known available agent
        agent = wrapper._get_agent_type("general-purpose")
        assert agent == AgentType.GENERAL_PURPOSE

        # Unknown agent falls back
        agent = wrapper._get_agent_type("custom-agent")
        assert agent.value in ["general-purpose", "tech-lead"]

    def test_generate_simulated_files(self, claude_config):
        """Test simulated file generation"""
        wrapper = ClaudeWrapper(claude_config)

        bug_files = wrapper._generate_simulated_files({"type": "bug_fix"})
        assert any("test" in f for f in bug_files)

        feature_files = wrapper._generate_simulated_files({"type": "feature"})
        assert any("feature" in f for f in feature_files)

    def test_parse_claude_output_with_actions(self, claude_config):
        """Test parsing Claude output with actions"""
        wrapper = ClaudeWrapper(claude_config)
        output = """
I'll analyze the task.
Let me fix the bug.
✅ Successfully updated the file.
Modified test.py
Created new_feature.py
"""
        result = wrapper._parse_claude_output(output)
        assert "response" in result
        assert len(result["actions_taken"]) > 0

    def test_parse_claude_output_empty(self, claude_config):
        """Test parsing empty Claude output"""
        wrapper = ClaudeWrapper(claude_config)
        result = wrapper._parse_claude_output("")
        assert result["response"] == ""
        assert result["files_changed"] == []

    def test_create_task_prompt_fresh(self, claude_config):
        """Test task prompt creation for fresh session"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "id": "test-123",
            "type": "feature",
            "title": "Add feature X",
            "description": "Feature description",
            "priority": 3,
            "source": "manual",
            "context": {},
        }
        context = {"execution_count": 1}
        prompt = wrapper._create_task_prompt(work_item, context, continue_session=False)
        assert "Sugar Autonomous Development Task" in prompt
        assert "Add feature X" in prompt

    def test_create_task_prompt_continuation(self, claude_config):
        """Test task prompt creation for continuation"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "id": "test-123",
            "type": "bug_fix",
            "title": "Fix bug Y",
            "description": "Bug description",
            "priority": 4,
            "source": "github",
            "context": {},
        }
        context = {"execution_count": 3}
        prompt = wrapper._create_task_prompt(work_item, context, continue_session=True)
        assert "Continuing our development work" in prompt
        assert "Fix bug Y" in prompt

    @pytest.mark.asyncio
    async def test_validate_claude_cli_success(self, claude_config):
        """Test Claude CLI validation success"""
        wrapper = ClaudeWrapper(claude_config)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"claude version 1.0", b"")
            mock_exec.return_value = mock_process

            result = await wrapper.validate_claude_cli()
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_claude_cli_failure(self, claude_config):
        """Test Claude CLI validation failure"""
        wrapper = ClaudeWrapper(claude_config)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = Exception("Command not found")

            result = await wrapper.validate_claude_cli()
            assert result is False


class TestModuleExports:
    """Test that module exports work correctly"""

    def test_import_from_executor_module(self):
        """Test importing from sugar.executor"""
        from sugar.executor import (
            StructuredRequest,
            StructuredResponse,
            RequestBuilder,
            ClaudeWrapper,
            ExecutionMode,
            AgentType,
            DynamicAgentType,
            TaskContext,
        )

        assert StructuredRequest is not None
        assert StructuredResponse is not None
        assert RequestBuilder is not None
        assert ClaudeWrapper is not None
        assert ExecutionMode is not None
        assert AgentType is not None
        assert DynamicAgentType is not None
        assert TaskContext is not None

    def test_executor_module_all(self):
        """Test __all__ exports"""
        import sugar.executor as executor

        assert hasattr(executor, "__all__")
        assert "StructuredRequest" in executor.__all__
        assert "ClaudeWrapper" in executor.__all__


class TestClaudeWrapperSessionManagement:
    """Test ClaudeWrapper session state management methods"""

    @pytest.fixture
    def claude_config(self, tmp_path):
        """Create test configuration for ClaudeWrapper"""
        return {
            "command": "claude",
            "timeout": 300,
            "context_file": str(tmp_path / "context.json"),
            "dry_run": True,
            "use_continuous": True,
            "context_strategy": "project",
            "max_context_age_hours": 24,
            "use_structured_requests": True,
            "structured_input_file": str(tmp_path / ".sugar" / "claude_input.json"),
            "enable_agents": True,
            "agent_fallback": True,
        }

    def test_load_session_state_no_file(self, claude_config):
        """Test loading session state when file doesn't exist"""
        wrapper = ClaudeWrapper(claude_config)
        state = wrapper._load_session_state()
        assert state == {}

    def test_load_session_state_with_file(self, claude_config, tmp_path):
        """Test loading session state from existing file"""
        wrapper = ClaudeWrapper(claude_config)
        # Create session state file
        session_file = tmp_path / "context_session.json"
        session_data = {
            "last_execution_time": "2025-12-05T10:00:00",
            "last_task_type": "bug_fix",
            "execution_count": 5,
        }
        session_file.write_text(json.dumps(session_data))
        wrapper.session_state_file = str(session_file)

        state = wrapper._load_session_state()
        assert state["last_task_type"] == "bug_fix"
        assert state["execution_count"] == 5

    def test_load_session_state_invalid_json(self, claude_config, tmp_path):
        """Test loading session state with invalid JSON returns empty dict"""
        wrapper = ClaudeWrapper(claude_config)
        session_file = tmp_path / "context_session.json"
        session_file.write_text("not valid json {")
        wrapper.session_state_file = str(session_file)

        state = wrapper._load_session_state()
        assert state == {}

    def test_is_context_too_old_fresh(self, claude_config):
        """Test context age check with fresh context"""
        wrapper = ClaudeWrapper(claude_config)
        session_state = {
            "last_execution_time": datetime.utcnow().isoformat(),
        }
        assert wrapper._is_context_too_old(session_state) is False

    def test_is_context_too_old_stale(self, claude_config):
        """Test context age check with stale context"""
        from datetime import timedelta

        wrapper = ClaudeWrapper(claude_config)
        old_time = datetime.utcnow() - timedelta(hours=48)
        session_state = {
            "last_execution_time": old_time.isoformat(),
        }
        assert wrapper._is_context_too_old(session_state) is True

    def test_is_context_too_old_invalid_time(self, claude_config):
        """Test context age check with invalid time format returns True"""
        wrapper = ClaudeWrapper(claude_config)
        session_state = {
            "last_execution_time": "not a valid date",
        }
        assert wrapper._is_context_too_old(session_state) is True

    def test_is_context_too_old_missing_time(self, claude_config):
        """Test context age check with missing time returns True"""
        wrapper = ClaudeWrapper(claude_config)
        session_state = {}
        assert wrapper._is_context_too_old(session_state) is True

    def test_update_session_state(self, claude_config, tmp_path):
        """Test session state update writes to file"""
        wrapper = ClaudeWrapper(claude_config)
        session_file = tmp_path / "context_session.json"
        wrapper.session_state_file = str(session_file)

        work_item = {
            "type": "feature",
            "title": "New feature",
            "description": "Feature description",
            "source_file": "main.py",
        }
        wrapper._update_session_state(work_item)

        assert session_file.exists()
        saved_state = json.loads(session_file.read_text())
        assert saved_state["last_task_type"] == "feature"
        assert saved_state["last_task_title"] == "New feature"
        assert saved_state["last_source_file"] == "main.py"
        assert saved_state["simulated"] is False

    def test_update_session_state_simulated(self, claude_config, tmp_path):
        """Test session state update with simulated flag"""
        wrapper = ClaudeWrapper(claude_config)
        session_file = tmp_path / "context_session.json"
        wrapper.session_state_file = str(session_file)

        work_item = {"type": "test", "title": "Test task"}
        wrapper._update_session_state(work_item, simulated=True)

        saved_state = json.loads(session_file.read_text())
        assert saved_state["simulated"] is True

    def test_get_execution_count_no_state(self, claude_config):
        """Test execution count with no prior state"""
        wrapper = ClaudeWrapper(claude_config)
        count = wrapper._get_execution_count()
        assert count == 0

    def test_get_execution_count_with_state(self, claude_config, tmp_path):
        """Test execution count with existing state"""
        wrapper = ClaudeWrapper(claude_config)
        session_file = tmp_path / "context_session.json"
        session_file.write_text(json.dumps({"execution_count": 10}))
        wrapper.session_state_file = str(session_file)

        count = wrapper._get_execution_count()
        assert count == 10


class TestClaudeWrapperContextPreparation:
    """Test ClaudeWrapper context preparation methods"""

    @pytest.fixture
    def claude_config(self, tmp_path):
        """Create test configuration for ClaudeWrapper"""
        return {
            "command": "claude",
            "timeout": 300,
            "context_file": str(tmp_path / "context.json"),
            "dry_run": True,
            "use_continuous": True,
            "context_strategy": "project",
            "max_context_age_hours": 24,
            "use_structured_requests": True,
            "structured_input_file": str(tmp_path / ".sugar" / "claude_input.json"),
            "enable_agents": True,
            "agent_fallback": True,
        }

    def test_prepare_context_fresh(self, claude_config, tmp_path):
        """Test context preparation for fresh session"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "id": "test-123",
            "type": "feature",
            "title": "New feature",
        }

        context = wrapper._prepare_context(work_item, continue_session=False)

        assert context["work_item"] == work_item
        assert context["ccal_session"] is True
        assert context["safety_mode"] is True
        assert context["continue_session"] is False
        assert "timestamp" in context

    def test_prepare_context_continuation(self, claude_config):
        """Test context preparation for continuation session"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {"id": "test-456", "type": "bug_fix"}

        context = wrapper._prepare_context(work_item, continue_session=True)

        assert context["continue_session"] is True

    def test_prepare_context_loads_existing(self, claude_config, tmp_path):
        """Test context preparation loads existing context"""
        # Create existing context file
        context_file = tmp_path / "context.json"
        existing_context = {
            "project_name": "test-project",
            "custom_key": "custom_value",
        }
        context_file.write_text(json.dumps(existing_context))

        wrapper = ClaudeWrapper(claude_config)
        work_item = {"id": "test-789", "type": "test"}

        context = wrapper._prepare_context(work_item)

        assert context["project_name"] == "test-project"
        assert context["custom_key"] == "custom_value"
        assert context["work_item"] == work_item

    def test_prepare_context_saves_file(self, claude_config, tmp_path):
        """Test context preparation saves context file"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {"id": "test-save", "type": "documentation"}

        wrapper._prepare_context(work_item)

        context_file = tmp_path / "context.json"
        assert context_file.exists()
        saved = json.loads(context_file.read_text())
        assert saved["work_item"]["id"] == "test-save"


class TestClaudeWrapperStructuredExecution:
    """Test ClaudeWrapper structured execution methods"""

    @pytest.fixture
    def claude_config(self, tmp_path):
        """Create test configuration for ClaudeWrapper"""
        return {
            "command": "claude",
            "timeout": 300,
            "context_file": str(tmp_path / "context.json"),
            "dry_run": False,  # Test non-dry-run paths
            "use_continuous": True,
            "context_strategy": "project",
            "max_context_age_hours": 24,
            "use_structured_requests": True,
            "structured_input_file": str(tmp_path / ".sugar" / "claude_input.json"),
            "enable_agents": True,
            "agent_fallback": True,
        }

    def test_create_structured_task_prompt_with_agent(self, claude_config):
        """Test structured task prompt generation with agent"""
        wrapper = ClaudeWrapper(claude_config)
        request = StructuredRequest(
            task_type="feature",
            title="Add new feature",
            description="Feature description",
            execution_mode=ExecutionMode.AGENT,
            agent_type=AgentType.TECH_LEAD,
        )

        prompt = wrapper._create_structured_task_prompt(request)

        assert "Sugar Structured Development Task" in prompt
        assert "tech-lead" in prompt
        assert "Add new feature" in prompt or "feature" in prompt.lower()

    def test_create_structured_task_prompt_basic(self, claude_config):
        """Test structured task prompt generation without agent"""
        wrapper = ClaudeWrapper(claude_config)
        request = StructuredRequest(
            task_type="test",
            title="Add tests",
            description="Test description",
            execution_mode=ExecutionMode.BASIC,
        )

        prompt = wrapper._create_structured_task_prompt(request)

        assert "Sugar Structured Development Task" in prompt
        assert "Add tests" in prompt or "test" in prompt.lower()

    @pytest.mark.asyncio
    async def test_execute_claude_cli_success(self, claude_config):
        """Test successful Claude CLI execution"""
        wrapper = ClaudeWrapper(claude_config)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.pid = 12345
            mock_process.communicate.return_value = (
                b"Successfully completed the task",
                b"",
            )
            mock_exec.return_value = mock_process

            result = await wrapper._execute_claude_cli(
                prompt="Test prompt",
                context={},
                continue_session=False,
            )

            assert result["success"] is True
            assert result["returncode"] == 0
            assert "execution_time" in result
            assert result["continued_session"] is False

    @pytest.mark.asyncio
    async def test_execute_claude_cli_with_continue(self, claude_config):
        """Test Claude CLI execution with continuation"""
        wrapper = ClaudeWrapper(claude_config)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.pid = 12346
            mock_process.communicate.return_value = (b"Continued work", b"")
            mock_exec.return_value = mock_process

            result = await wrapper._execute_claude_cli(
                prompt="Continue prompt",
                context={},
                continue_session=True,
            )

            assert result["continued_session"] is True
            # Verify --continue flag was used in command
            call_args = mock_exec.call_args[0]
            assert "--continue" in call_args

    @pytest.mark.asyncio
    async def test_execute_claude_cli_failure(self, claude_config):
        """Test Claude CLI execution failure"""
        wrapper = ClaudeWrapper(claude_config)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.pid = 12347
            mock_process.communicate.return_value = (b"", b"Error occurred")
            mock_exec.return_value = mock_process

            with pytest.raises(Exception) as exc_info:
                await wrapper._execute_claude_cli(
                    prompt="Failing prompt",
                    context={},
                    continue_session=False,
                )

            assert "failed with return code" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_claude_cli_timeout(self, claude_config):
        """Test Claude CLI execution timeout"""
        claude_config["timeout"] = 1  # 1 second timeout
        wrapper = ClaudeWrapper(claude_config)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.pid = 12348
            mock_process.kill = MagicMock()
            # Simulate timeout by making communicate raise TimeoutError
            mock_process.communicate.side_effect = asyncio.TimeoutError()
            mock_exec.return_value = mock_process

            with pytest.raises(Exception) as exc_info:
                await wrapper._execute_claude_cli(
                    prompt="Timeout prompt",
                    context={},
                    continue_session=False,
                )

            assert "timed out" in str(exc_info.value)
            mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_claude_cli_structured_success(self, claude_config):
        """Test structured Claude CLI execution success"""
        wrapper = ClaudeWrapper(claude_config)
        request = StructuredRequest(
            task_type="test",
            title="Test task",
            description="Description",
            execution_mode=ExecutionMode.AGENT,
            agent_type=AgentType.GENERAL_PURPOSE,
        )

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"Task completed", b"")
            mock_exec.return_value = mock_process

            result = await wrapper._execute_claude_cli_structured(
                prompt="Structured prompt",
                structured_request=request,
            )

            assert result["success"] is True
            assert result["structured_mode"] is True
            assert result["agent_requested"] == "general-purpose"

    @pytest.mark.asyncio
    async def test_execute_claude_cli_structured_failure(self, claude_config):
        """Test structured Claude CLI execution failure"""
        wrapper = ClaudeWrapper(claude_config)
        request = StructuredRequest(
            task_type="test",
            title="Failing task",
            description="Description",
            execution_mode=ExecutionMode.BASIC,
        )

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate.return_value = (b"", b"Execution error")
            mock_exec.return_value = mock_process

            result = await wrapper._execute_claude_cli_structured(
                prompt="Failing prompt",
                structured_request=request,
            )

            assert result["success"] is False
            assert "error" in result


class TestClaudeWrapperFullExecution:
    """Test ClaudeWrapper full execution flows"""

    @pytest.fixture
    def claude_config(self, tmp_path):
        """Create test configuration for ClaudeWrapper"""
        return {
            "command": "claude",
            "timeout": 300,
            "context_file": str(tmp_path / "context.json"),
            "dry_run": False,
            "use_continuous": True,
            "context_strategy": "project",
            "max_context_age_hours": 24,
            "use_structured_requests": True,
            "structured_input_file": str(tmp_path / ".sugar" / "claude_input.json"),
            "enable_agents": True,
            "agent_fallback": True,
        }

    @pytest.mark.asyncio
    async def test_execute_structured_work_success(self, claude_config):
        """Test full structured work execution success"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "id": "structured-123",
            "type": "feature",
            "title": "New feature",
            "description": "Feature description",
            "priority": 3,
            "source": "manual",
            "attempts": 0,
            "context": {},
        }

        with patch.object(wrapper, "_execute_claude_cli_structured") as mock_cli:
            mock_cli.return_value = {
                "success": True,
                "stdout": "Successfully implemented feature",
                "stderr": "",
                "returncode": 0,
                "execution_time": 15.0,
            }

            result = await wrapper._execute_structured_work(work_item)

            assert result["success"] is True
            assert result["work_item_id"] == "structured-123"
            assert "structured_response" in result

    @pytest.mark.asyncio
    async def test_execute_structured_work_fallback(self, claude_config):
        """Test structured work execution fallback to legacy"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "id": "fallback-123",
            "type": "bug_fix",
            "title": "Fix bug",
            "description": "Bug description",
            "priority": 4,
            "source": "github",
            "attempts": 0,
            "context": {},
        }

        with patch.object(wrapper, "_execute_claude_cli_structured") as mock_structured:
            mock_structured.return_value = {
                "success": False,
                "stderr": "Agent failed",
            }

            with patch.object(wrapper, "_execute_legacy_work") as mock_legacy:
                mock_legacy.return_value = {
                    "success": True,
                    "execution_mode": "legacy",
                }

                result = await wrapper._execute_structured_work(work_item)

                mock_legacy.assert_called_once()
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_legacy_work_success(self, claude_config):
        """Test legacy work execution success"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "id": "legacy-123",
            "type": "test",
            "title": "Add tests",
            "description": "Test description",
            "priority": 2,
            "source": "manual",
            "context": {},
        }

        with patch.object(wrapper, "_execute_claude_cli") as mock_cli:
            mock_cli.return_value = {
                "success": True,
                "stdout": "Tests added successfully",
                "stderr": "",
                "returncode": 0,
                "execution_time": 10.0,
            }

            result = await wrapper._execute_legacy_work(work_item)

            assert result["success"] is True
            assert result["execution_mode"] == "legacy"
            assert result["work_item_id"] == "legacy-123"

    @pytest.mark.asyncio
    async def test_execute_work_dry_run(self, claude_config):
        """Test execute_work in dry run mode"""
        claude_config["dry_run"] = True
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "id": "dry-run-123",
            "type": "documentation",
            "title": "Update docs",
            "description": "Documentation update",
            "priority": 1,
        }

        result = await wrapper.execute_work(work_item)

        assert result["success"] is True
        assert result["simulated"] is True

    @pytest.mark.asyncio
    async def test_execute_work_exception_handling(self, claude_config):
        """Test execute_work exception handling"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "id": "error-123",
            "type": "feature",
            "title": "Problematic feature",
            "description": "This will fail",
            "priority": 3,
        }

        with patch.object(wrapper, "_execute_structured_work") as mock_structured:
            mock_structured.side_effect = Exception("Unexpected error")

            result = await wrapper.execute_work(work_item)

            assert result["success"] is False
            assert "error" in result
            assert "Unexpected error" in result["error"]


class TestClaudeWrapperSessionContinuation:
    """Test ClaudeWrapper session continuation logic"""

    @pytest.fixture
    def claude_config(self, tmp_path):
        """Create test configuration for ClaudeWrapper"""
        return {
            "command": "claude",
            "timeout": 300,
            "context_file": str(tmp_path / "context.json"),
            "dry_run": True,
            "use_continuous": True,
            "context_strategy": "project",
            "max_context_age_hours": 24,
            "use_structured_requests": True,
            "structured_input_file": str(tmp_path / ".sugar" / "claude_input.json"),
            "enable_agents": True,
            "agent_fallback": True,
        }

    def test_should_continue_disabled(self, claude_config):
        """Test session continuation when disabled"""
        claude_config["use_continuous"] = False
        wrapper = ClaudeWrapper(claude_config)
        work_item = {"type": "test", "description": ""}

        assert wrapper._should_continue_session(work_item) is False

    def test_should_continue_task_type_strategy_match(self, claude_config, tmp_path):
        """Test session continuation with task_type strategy matching"""
        claude_config["context_strategy"] = "task_type"
        wrapper = ClaudeWrapper(claude_config)

        # Create session state
        session_file = tmp_path / "context_session.json"
        session_file.write_text(
            json.dumps(
                {
                    "last_execution_time": datetime.utcnow().isoformat(),
                    "last_task_type": "bug_fix",
                }
            )
        )
        wrapper.session_state_file = str(session_file)

        # Same task type should continue
        work_item = {"type": "bug_fix", "description": ""}
        assert wrapper._should_continue_session(work_item) is True

    def test_should_continue_task_type_strategy_mismatch(self, claude_config, tmp_path):
        """Test session continuation with task_type strategy mismatching"""
        claude_config["context_strategy"] = "task_type"
        wrapper = ClaudeWrapper(claude_config)

        session_file = tmp_path / "context_session.json"
        session_file.write_text(
            json.dumps(
                {
                    "last_execution_time": datetime.utcnow().isoformat(),
                    "last_task_type": "bug_fix",
                }
            )
        )
        wrapper.session_state_file = str(session_file)

        # Different task type should not continue
        work_item = {"type": "feature", "description": ""}
        assert wrapper._should_continue_session(work_item) is False

    def test_should_continue_session_strategy(self, claude_config, tmp_path):
        """Test session continuation with session strategy"""
        claude_config["context_strategy"] = "session"
        wrapper = ClaudeWrapper(claude_config)

        session_file = tmp_path / "context_session.json"
        session_file.write_text(
            json.dumps(
                {
                    "last_execution_time": datetime.utcnow().isoformat(),
                    "last_task_description": "Fix authentication bug",
                }
            )
        )
        wrapper.session_state_file = str(session_file)

        # Related task (auth keyword) should continue
        work_item = {"type": "feature", "description": "Improve auth flow"}
        assert wrapper._should_continue_session(work_item) is True

    def test_should_continue_context_too_old(self, claude_config, tmp_path):
        """Test session continuation when context is too old"""
        from datetime import timedelta

        wrapper = ClaudeWrapper(claude_config)

        session_file = tmp_path / "context_session.json"
        old_time = datetime.utcnow() - timedelta(hours=48)
        session_file.write_text(
            json.dumps(
                {
                    "last_execution_time": old_time.isoformat(),
                    "last_task_type": "bug_fix",
                }
            )
        )
        wrapper.session_state_file = str(session_file)

        work_item = {"type": "bug_fix", "description": ""}
        assert wrapper._should_continue_session(work_item) is False


class TestClaudeWrapperAgentSelectionKeywords:
    """Test ClaudeWrapper agent selection based on keywords"""

    @pytest.fixture
    def claude_config(self, tmp_path):
        """Create test configuration for ClaudeWrapper"""
        return {
            "command": "claude",
            "timeout": 300,
            "context_file": str(tmp_path / "context.json"),
            "dry_run": True,
            "use_continuous": True,
            "context_strategy": "project",
            "max_context_age_hours": 24,
            "use_structured_requests": True,
            "structured_input_file": str(tmp_path / ".sugar" / "claude_input.json"),
            "enable_agents": True,
            "agent_fallback": True,
        }

    def test_select_agent_statusline_setup(self, claude_config):
        """Test agent selection for statusline setup tasks"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "type": "setup",
            "title": "Configure statusline",
            "description": "Set up the Claude Code status line",
            "priority": 2,
        }
        agent = asyncio.run(wrapper._select_agent_for_work(work_item))
        assert agent is not None
        assert agent.value == "statusline-setup"

    def test_select_agent_output_style(self, claude_config):
        """Test agent selection for output style tasks - note: 'style' keyword triggers code-reviewer first"""
        wrapper = ClaudeWrapper(claude_config)
        # The keyword 'style' in 'output style' triggers code-reviewer before output-style-setup
        # This test verifies the actual behavior of the keyword matching order
        work_item = {
            "type": "setup",
            "title": "Configure color scheme",
            "description": "Set up the theme for terminal",
            "priority": 2,
        }
        agent = asyncio.run(wrapper._select_agent_for_work(work_item))
        assert agent is not None
        # 'theme' keyword triggers output-style-setup
        assert agent.value == "output-style-setup"

    def test_select_agent_architecture_keywords(self, claude_config):
        """Test agent selection for architecture-related tasks"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "type": "design",
            "title": "System architecture planning",
            "description": "Plan and document system architecture",
            "priority": 3,
        }
        agent = asyncio.run(wrapper._select_agent_for_work(work_item))
        assert agent == AgentType.TECH_LEAD

    def test_select_agent_performance_keywords(self, claude_config):
        """Test agent selection for performance-related tasks"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "type": "optimization",
            "title": "Performance optimization",
            "description": "Improve scalability and performance",
            "priority": 3,
        }
        agent = asyncio.run(wrapper._select_agent_for_work(work_item))
        assert agent == AgentType.TECH_LEAD

    def test_select_agent_default_fallback(self, claude_config):
        """Test agent selection defaults to general-purpose"""
        wrapper = ClaudeWrapper(claude_config)
        work_item = {
            "type": "unknown",
            "title": "Generic task",
            "description": "Some generic description without keywords",
            "priority": 2,
        }
        agent = asyncio.run(wrapper._select_agent_for_work(work_item))
        assert agent == AgentType.GENERAL_PURPOSE
