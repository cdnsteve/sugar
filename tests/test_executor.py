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
