"""
Tests for Sugar profiles module (P2 priority)

Tests workflow profiles: DefaultProfile, IssueResponderProfile.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any

from sugar.profiles import DefaultProfile, IssueResponderProfile
from sugar.profiles.base import ProfileConfig, BaseProfile
from sugar.profiles.issue_responder import IssueAnalysis, IssueResponse


class TestProfileConfig:
    """Tests for ProfileConfig dataclass"""

    def test_config_creation_defaults(self):
        config = ProfileConfig(name="test")
        assert config.name == "test"
        assert config.description == ""
        assert config.model == "claude-sonnet-4-20250514"
        assert config.max_tokens == 8192
        assert config.temperature == 0.7
        assert config.allowed_tools == []
        assert config.quality_gates_enabled is True
        assert config.confidence_threshold == 0.7

    def test_config_creation_custom(self):
        config = ProfileConfig(
            name="custom",
            description="Custom profile",
            model="claude-opus-4-20250514",
            max_tokens=4096,
            temperature=0.5,
            allowed_tools=["Read", "Write"],
            quality_gates_enabled=False,
            confidence_threshold=0.9,
            settings={"custom_setting": True},
        )
        assert config.name == "custom"
        assert config.description == "Custom profile"
        assert config.model == "claude-opus-4-20250514"
        assert config.max_tokens == 4096
        assert config.temperature == 0.5
        assert config.allowed_tools == ["Read", "Write"]
        assert config.quality_gates_enabled is False
        assert config.confidence_threshold == 0.9
        assert config.settings["custom_setting"] is True


class TestDefaultProfile:
    """Tests for DefaultProfile"""

    def test_default_profile_init(self, default_profile):
        assert default_profile.name == "default"
        assert (
            default_profile.config.description
            == "General-purpose development assistance"
        )
        assert "Read" in default_profile.config.allowed_tools
        assert "Write" in default_profile.config.allowed_tools
        assert "Edit" in default_profile.config.allowed_tools
        assert "Bash" in default_profile.config.allowed_tools

    def test_default_profile_custom_config(self):
        custom_config = ProfileConfig(
            name="custom_default",
            description="Custom default",
            allowed_tools=["Read"],
        )
        profile = DefaultProfile(config=custom_config)
        assert profile.name == "custom_default"
        assert profile.config.allowed_tools == ["Read"]

    def test_get_system_prompt_basic(self, default_profile):
        prompt = default_profile.get_system_prompt()
        assert "Sugar" in prompt
        assert "autonomous development assistant" in prompt
        assert "Capabilities" in prompt
        assert "Guidelines" in prompt
        assert "Safety" in prompt

    def test_get_system_prompt_with_context(self, default_profile):
        context = {
            "project_name": "TestProject",
            "additional_context": "This is a Python project.",
        }
        prompt = default_profile.get_system_prompt(context)
        assert "TestProject" in prompt
        assert "This is a Python project" in prompt

    def test_get_tools(self, default_profile):
        tools = default_profile.get_tools()
        assert isinstance(tools, list)
        assert "Read" in tools
        assert "Glob" in tools

    def test_get_quality_gate_config(self, default_profile):
        config = default_profile.get_quality_gate_config()
        assert "enabled" in config
        assert "confidence_threshold" in config
        assert config["enabled"] is True
        assert config["confidence_threshold"] == 0.7

    @pytest.mark.asyncio
    async def test_process_input(self, default_profile):
        input_data = {
            "type": "bug_fix",
            "title": "Fix login bug",
            "description": "Users cannot login with special characters",
            "priority": 4,
        }
        processed = await default_profile.process_input(input_data)

        assert processed["task_type"] == "bug_fix"
        assert processed["title"] == "Fix login bug"
        assert processed["priority"] == 4
        assert "prompt" in processed
        assert "Fix login bug" in processed["prompt"]

    @pytest.mark.asyncio
    async def test_process_input_defaults(self, default_profile):
        input_data = {}
        processed = await default_profile.process_input(input_data)

        assert processed["task_type"] == "general"
        assert processed["title"] == "Development Task"
        assert processed["priority"] == 3

    @pytest.mark.asyncio
    async def test_process_output(self, default_profile):
        output_data = {
            "content": "Fixed the login bug by escaping special characters.",
            "success": True,
            "files_modified": ["src/auth.py"],
            "tool_uses": ["Read", "Edit"],
        }
        processed = await default_profile.process_output(output_data)

        assert processed["success"] is True
        assert "Fixed the login bug" in processed["content"]
        assert processed["files_modified"] == ["src/auth.py"]
        assert "summary" in processed

    def test_validate_output_high_confidence(self, default_profile):
        output = {"confidence": 0.9}
        assert default_profile.validate_output(output) is True

    def test_validate_output_low_confidence(self, default_profile):
        output = {"confidence": 0.5}
        assert default_profile.validate_output(output) is False


class TestIssueAnalysis:
    """Tests for IssueAnalysis dataclass"""

    def test_issue_analysis_creation(self):
        analysis = IssueAnalysis(
            issue_number=123,
            title="Test issue",
            body="Test body",
            issue_type="bug",
            sentiment="neutral",
            key_topics=["api", "auth"],
            mentioned_files=["src/auth.py"],
            mentioned_errors=["AttributeError"],
            similar_issues=[100, 101],
            confidence=0.85,
        )
        assert analysis.issue_number == 123
        assert analysis.issue_type == "bug"
        assert "api" in analysis.key_topics
        assert analysis.confidence == 0.85

    def test_issue_analysis_to_dict(self):
        analysis = IssueAnalysis(
            issue_number=456,
            title="Another issue",
            body="Body content",
            issue_type="feature",
            sentiment="positive",
            key_topics=["database"],
            mentioned_files=[],
            mentioned_errors=[],
            similar_issues=[],
            confidence=0.75,
        )
        d = analysis.to_dict()
        assert d["issue_number"] == 456
        assert d["issue_type"] == "feature"
        assert d["sentiment"] == "positive"
        assert d["confidence"] == 0.75


class TestIssueResponse:
    """Tests for IssueResponse dataclass"""

    def test_issue_response_creation(self):
        response = IssueResponse(
            content="Thank you for reporting this issue.",
            confidence=0.9,
            code_references=[{"file": "src/main.py", "line": 42}],
            suggested_labels=["bug", "high-priority"],
            should_auto_post=True,
        )
        assert response.confidence == 0.9
        assert response.should_auto_post is True
        assert len(response.suggested_labels) == 2

    def test_issue_response_to_dict(self):
        response = IssueResponse(
            content="Response content",
            confidence=0.7,
            code_references=[],
            suggested_labels=["question"],
            should_auto_post=False,
        )
        d = response.to_dict()
        assert d["content"] == "Response content"
        assert d["confidence"] == 0.7
        assert d["should_auto_post"] is False


class TestIssueResponderProfile:
    """Tests for IssueResponderProfile"""

    def test_issue_responder_init(self, issue_responder_profile):
        assert issue_responder_profile.name == "issue_responder"
        assert "Read" in issue_responder_profile.config.allowed_tools
        assert "Glob" in issue_responder_profile.config.allowed_tools
        assert "Grep" in issue_responder_profile.config.allowed_tools
        # Should not have dangerous tools
        assert "Write" not in issue_responder_profile.config.allowed_tools
        assert "Bash" not in issue_responder_profile.config.allowed_tools

    def test_issue_responder_settings(self, issue_responder_profile):
        settings = issue_responder_profile.config.settings
        assert settings["auto_post_threshold"] == 0.8
        assert settings["max_response_length"] == 2000
        assert settings["include_signature"] is True
        assert "Sugar" in settings["signature"]

    def test_get_system_prompt_basic(self, issue_responder_profile):
        prompt = issue_responder_profile.get_system_prompt()
        assert "Sugar" in prompt
        assert "GitHub issues" in prompt
        assert "Confidence Scoring" in prompt
        assert "Response Format" in prompt

    def test_get_system_prompt_with_repo(self, issue_responder_profile):
        context = {"repo": "owner/repo"}
        prompt = issue_responder_profile.get_system_prompt(context)
        assert "Repository: owner/repo" in prompt

    def test_pre_analyze_issue_bug(self, issue_responder_profile):
        analysis = issue_responder_profile._pre_analyze_issue(
            title="Application crashes on startup",
            body="I get an error when running the app: AttributeError in main.py",
            labels=[],
        )
        assert analysis["issue_type"] == "bug"
        assert "main.py" in analysis["mentioned_files"] or any(
            "py" in f for f in analysis["mentioned_files"]
        )

    def test_pre_analyze_issue_feature(self, issue_responder_profile):
        analysis = issue_responder_profile._pre_analyze_issue(
            title="Feature request: Add dark mode",
            body="It would be nice to have dark mode support in the UI.",
            labels=[],
        )
        assert analysis["issue_type"] == "feature"

    def test_pre_analyze_issue_documentation(self, issue_responder_profile):
        analysis = issue_responder_profile._pre_analyze_issue(
            title="Update documentation",
            body="The README needs an example for the API usage.",
            labels=[],
        )
        assert analysis["issue_type"] == "documentation"

    def test_pre_analyze_issue_question(self, issue_responder_profile):
        analysis = issue_responder_profile._pre_analyze_issue(
            title="How do I configure the settings?",
            body="I'm trying to understand how to set up the configuration.",
            labels=[],
        )
        assert analysis["issue_type"] == "question"

    def test_pre_analyze_issue_extracts_topics(self, issue_responder_profile):
        analysis = issue_responder_profile._pre_analyze_issue(
            title="API authentication failing",
            body="The auth endpoint returns 401 when using the CLI with docker.",
            labels=[],
        )
        assert "api" in analysis["key_topics"]
        assert "auth" in analysis["key_topics"]
        assert "cli" in analysis["key_topics"]
        assert "docker" in analysis["key_topics"]

    @pytest.mark.asyncio
    async def test_process_input(self, issue_responder_profile, sample_github_issue):
        input_data = {
            "issue": sample_github_issue,
            "repo": "test/repo",
        }
        processed = await issue_responder_profile.process_input(input_data)

        assert "prompt" in processed
        assert processed["issue_number"] == 123
        assert "Application crashes" in processed["issue_title"]
        assert processed["repo"] == "test/repo"
        assert "pre_analysis" in processed
        assert processed["pre_analysis"]["issue_type"] == "bug"

    def test_parse_response_structured(self, issue_responder_profile):
        content = """### Confidence Score
0.85

### Suggested Labels
bug, needs-triage

### Response
Thank you for reporting this issue. I found the problem in src/config.py:42.

### Code References
src/config.py:42
src/main.py:15
"""
        parsed = issue_responder_profile._parse_response(content)

        assert parsed["confidence"] == 0.85
        assert "bug" in parsed["suggested_labels"]
        assert "needs-triage" in parsed["suggested_labels"]
        assert "Thank you for reporting" in parsed["response"]
        assert len(parsed["code_references"]) == 2
        assert parsed["code_references"][0]["file"] == "src/config.py"
        assert parsed["code_references"][0]["line"] == 42

    def test_parse_response_unstructured(self, issue_responder_profile):
        content = "Just a plain response without structure."
        parsed = issue_responder_profile._parse_response(content)

        assert parsed["confidence"] == 0.5  # Default
        assert parsed["suggested_labels"] == []
        assert parsed["response"] == content

    @pytest.mark.asyncio
    async def test_process_output_with_signature(self, issue_responder_profile):
        output_data = {
            "content": """### Confidence Score
0.9

### Suggested Labels
bug

### Response
Thank you for reporting this issue!

### Code References
src/main.py:10
""",
            "success": True,
        }
        processed = await issue_responder_profile.process_output(output_data)

        assert processed["success"] is True
        response = processed["response"]
        assert response["confidence"] == 0.9
        assert response["should_auto_post"] is True
        assert "Sugar" in response["content"]  # Signature added

    @pytest.mark.asyncio
    async def test_process_output_truncates_long_response(
        self, issue_responder_profile
    ):
        long_content = "A" * 3000
        output_data = {
            "content": f"### Response\n{long_content}",
            "success": True,
        }
        processed = await issue_responder_profile.process_output(output_data)
        response = processed["response"]

        # Should be truncated to max_response_length (2000)
        assert len(response["content"]) <= 2000 + len(
            issue_responder_profile.config.settings["signature"]
        )

    @pytest.mark.asyncio
    async def test_process_output_low_confidence_no_auto_post(
        self, issue_responder_profile
    ):
        output_data = {
            "content": """### Confidence Score
0.6

### Response
I'm not sure about this issue.
""",
            "success": True,
        }
        processed = await issue_responder_profile.process_output(output_data)
        response = processed["response"]

        assert response["confidence"] == 0.6
        assert response["should_auto_post"] is False

    def test_validate_output_valid(self, issue_responder_profile):
        output = {
            "response": {
                "content": "This is a valid response with enough content to pass validation.",
                "confidence": 0.8,
            }
        }
        assert issue_responder_profile.validate_output(output) is True

    def test_validate_output_too_short(self, issue_responder_profile):
        output = {
            "response": {
                "content": "Too short",
                "confidence": 0.9,
            }
        }
        assert issue_responder_profile.validate_output(output) is False

    def test_validate_output_low_confidence(self, issue_responder_profile):
        output = {
            "response": {
                "content": "This response has enough content but low confidence score.",
                "confidence": 0.3,
            }
        }
        assert issue_responder_profile.validate_output(output) is False


class TestProfileInheritance:
    """Tests for profile inheritance and abstract methods"""

    def test_profiles_inherit_from_base(self, default_profile, issue_responder_profile):
        assert isinstance(default_profile, BaseProfile)
        assert isinstance(issue_responder_profile, BaseProfile)

    def test_profiles_implement_required_methods(
        self, default_profile, issue_responder_profile
    ):
        # All profiles must implement these methods
        for profile in [default_profile, issue_responder_profile]:
            assert hasattr(profile, "get_system_prompt")
            assert hasattr(profile, "process_input")
            assert hasattr(profile, "process_output")
            assert hasattr(profile, "get_tools")
            assert hasattr(profile, "get_quality_gate_config")
            assert hasattr(profile, "validate_output")
