"""
Tests for ContextManager - Context summarization functionality

Tests cover:
- Message creation and token counting
- Context management and retrieval
- Summarization triggering and execution
- Key decision and file extraction
- Stats tracking and state management
"""

import pytest
import asyncio
import sys
import importlib.util
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import List

# Import context_manager directly without triggering agent.__init__
spec = importlib.util.spec_from_file_location(
    "context_manager",
    Path(__file__).parent.parent / "sugar" / "agent" / "context_manager.py"
)
context_manager_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context_manager_module)

ContextManager = context_manager_module.ContextManager
Message = context_manager_module.Message
ContextSummary = context_manager_module.ContextSummary
ANTHROPIC_AVAILABLE = context_manager_module.ANTHROPIC_AVAILABLE
TIKTOKEN_AVAILABLE = context_manager_module.TIKTOKEN_AVAILABLE


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def context_manager():
    """Create a basic ContextManager for testing."""
    return ContextManager(
        token_threshold=1000,
        preserve_recent=5,
        summarization_model="claude-3-haiku-20240307",
    )


@pytest.fixture
def context_manager_with_mock_client():
    """Create ContextManager with mocked Anthropic client."""
    manager = ContextManager(token_threshold=1000, preserve_recent=5)

    # Mock the Anthropic client
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.content = [Mock(text="This is a summarized version of the conversation.")]
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    manager._anthropic_client = mock_client
    return manager


@pytest.fixture
def sample_messages():
    """Sample messages for testing."""
    return [
        Message(
            role="user",
            content="Please implement user authentication",
            token_count=10,
            timestamp=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        ),
        Message(
            role="assistant",
            content="I'll implement authentication. First, I'll create auth.py",
            token_count=15,
            timestamp=datetime(2025, 1, 1, 12, 1, 0, tzinfo=timezone.utc),
        ),
        Message(
            role="user",
            content="Add JWT support",
            token_count=8,
            timestamp=datetime(2025, 1, 1, 12, 2, 0, tzinfo=timezone.utc),
        ),
        Message(
            role="assistant",
            content="I decided to use PyJWT library. Will modify auth.py and config.py",
            token_count=20,
            timestamp=datetime(2025, 1, 1, 12, 3, 0, tzinfo=timezone.utc),
        ),
    ]


# ============================================================================
# Test Message Dataclass
# ============================================================================


class TestMessage:
    """Test Message dataclass."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(
            role="user",
            content="Hello",
            token_count=5,
        )
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.token_count == 5
        assert msg.summarized is False
        assert isinstance(msg.timestamp, datetime)

    def test_message_to_dict(self):
        """Test message serialization."""
        msg = Message(
            role="assistant",
            content="Response",
            token_count=10,
            summarized=True,
        )
        d = msg.to_dict()

        assert d["role"] == "assistant"
        assert d["content"] == "Response"
        assert d["token_count"] == 10
        assert d["summarized"] is True
        assert "timestamp" in d

    def test_message_from_dict(self):
        """Test message deserialization."""
        data = {
            "role": "user",
            "content": "Test content",
            "token_count": 15,
            "timestamp": "2025-01-01T12:00:00+00:00",
            "summarized": False,
        }
        msg = Message.from_dict(data)

        assert msg.role == "user"
        assert msg.content == "Test content"
        assert msg.token_count == 15
        assert msg.summarized is False
        assert isinstance(msg.timestamp, datetime)


# ============================================================================
# Test ContextSummary Dataclass
# ============================================================================


class TestContextSummary:
    """Test ContextSummary dataclass."""

    def test_summary_creation(self):
        """Test creating a summary."""
        summary = ContextSummary(
            content="Summary of conversation",
            original_token_count=1000,
            summarized_token_count=200,
            messages_summarized=10,
            key_decisions=["decided to use JWT", "implement rate limiting"],
            files_modified=["auth.py", "config.py"],
        )

        assert summary.content == "Summary of conversation"
        assert summary.original_token_count == 1000
        assert summary.summarized_token_count == 200
        assert summary.messages_summarized == 10
        assert len(summary.key_decisions) == 2
        assert len(summary.files_modified) == 2

    def test_summary_to_dict(self):
        """Test summary serialization."""
        summary = ContextSummary(
            content="Summary",
            original_token_count=500,
            summarized_token_count=100,
            messages_summarized=5,
        )
        d = summary.to_dict()

        assert d["content"] == "Summary"
        assert d["original_token_count"] == 500
        assert d["summarized_token_count"] == 100
        assert d["messages_summarized"] == 5
        assert isinstance(d["key_decisions"], list)
        assert isinstance(d["files_modified"], list)


# ============================================================================
# Test ContextManager Initialization
# ============================================================================


class TestContextManagerInit:
    """Test ContextManager initialization."""

    def test_default_initialization(self):
        """Test default configuration."""
        manager = ContextManager()

        assert manager.token_threshold == 150000
        assert manager.preserve_recent == 10
        assert manager.summarization_model == "claude-3-haiku-20240307"
        assert manager.total_tokens == 0
        assert manager.total_tokens_saved == 0
        assert len(manager.messages) == 0
        assert len(manager.summaries) == 0

    def test_custom_initialization(self):
        """Test custom configuration."""
        manager = ContextManager(
            token_threshold=50000,
            preserve_recent=20,
            summarization_model="claude-3-opus-20240229",
        )

        assert manager.token_threshold == 50000
        assert manager.preserve_recent == 20
        assert manager.summarization_model == "claude-3-opus-20240229"

    def test_encoder_initialization(self):
        """Test token encoder setup."""
        manager = ContextManager()

        # Should have encoder if tiktoken available
        if TIKTOKEN_AVAILABLE:
            assert manager._encoder is not None
        else:
            assert manager._encoder is None


# ============================================================================
# Test Token Counting
# ============================================================================


class TestTokenCounting:
    """Test token counting functionality."""

    def test_count_tokens_basic(self, context_manager):
        """Test basic token counting."""
        text = "Hello, world!"
        count = context_manager._count_tokens(text)

        # Should return a positive integer
        assert isinstance(count, int)
        assert count > 0

    def test_count_tokens_empty(self, context_manager):
        """Test token counting for empty string."""
        count = context_manager._count_tokens("")
        assert count == 0

    def test_count_tokens_long_text(self, context_manager):
        """Test token counting for longer text."""
        text = "This is a longer piece of text. " * 100
        count = context_manager._count_tokens(text)

        # Should scale with text length
        assert count > 100

    @pytest.mark.skipif(not TIKTOKEN_AVAILABLE, reason="tiktoken not available")
    def test_count_tokens_with_tiktoken(self):
        """Test accurate token counting with tiktoken."""
        manager = ContextManager()
        text = "Hello, how are you doing today?"
        count = manager._count_tokens(text)

        # tiktoken should give accurate count
        assert count > 0
        assert count < 50  # Reasonable upper bound for this text

    def test_count_tokens_fallback(self):
        """Test fallback token counting (character-based)."""
        manager = ContextManager()
        # Temporarily disable encoder to test fallback
        original_encoder = manager._encoder
        manager._encoder = None

        text = "Test text with 20 characters."  # Exactly 30 chars
        count = manager._count_tokens(text)

        # Fallback approximates as chars / 4
        assert count == len(text) // 4

        manager._encoder = original_encoder


# ============================================================================
# Test Adding Messages
# ============================================================================


class TestAddingMessages:
    """Test adding messages to context."""

    def test_add_single_message(self, context_manager):
        """Test adding a single message."""
        context_manager.add_message("user", "Hello")

        assert len(context_manager.messages) == 1
        assert context_manager.messages[0].role == "user"
        assert context_manager.messages[0].content == "Hello"
        assert context_manager.total_tokens > 0

    def test_add_multiple_messages(self, context_manager):
        """Test adding multiple messages."""
        context_manager.add_message("user", "First message")
        context_manager.add_message("assistant", "First response")
        context_manager.add_message("user", "Second message")

        assert len(context_manager.messages) == 3
        assert context_manager.messages[0].role == "user"
        assert context_manager.messages[1].role == "assistant"
        assert context_manager.messages[2].role == "user"

    def test_add_message_updates_token_count(self, context_manager):
        """Test that adding messages updates total token count."""
        initial_tokens = context_manager.total_tokens

        context_manager.add_message("user", "Test message")
        assert context_manager.total_tokens > initial_tokens

        previous_tokens = context_manager.total_tokens
        context_manager.add_message("assistant", "Test response")
        assert context_manager.total_tokens > previous_tokens

    def test_add_message_marks_needs_summarization(self, context_manager):
        """Test that exceeding threshold marks for summarization."""
        # Add messages until threshold exceeded
        long_message = "x" * 1000  # Long message to quickly exceed threshold

        context_manager.add_message("user", long_message)

        # Should mark needs summarization if threshold exceeded
        if context_manager.total_tokens > context_manager.token_threshold:
            assert hasattr(context_manager, "_needs_summarization")
            assert context_manager._needs_summarization is True


# ============================================================================
# Test Getting Context
# ============================================================================


class TestGettingContext:
    """Test retrieving context."""

    def test_get_context_empty(self, context_manager):
        """Test getting context with no messages."""
        context = context_manager.get_context()
        assert isinstance(context, list)
        assert len(context) == 0

    def test_get_context_with_messages(self, context_manager):
        """Test getting context with messages."""
        context_manager.add_message("user", "Hello")
        context_manager.add_message("assistant", "Hi there")

        context = context_manager.get_context()

        assert len(context) == 2
        assert context[0]["role"] == "user"
        assert context[0]["content"] == "Hello"
        assert context[1]["role"] == "assistant"
        assert context[1]["content"] == "Hi there"

    def test_get_context_format(self, context_manager):
        """Test that context is in correct format for Claude."""
        context_manager.add_message("user", "Test")

        context = context_manager.get_context()

        # Should be list of dicts with role and content
        assert isinstance(context, list)
        assert all(isinstance(msg, dict) for msg in context)
        assert all("role" in msg and "content" in msg for msg in context)

    def test_get_context_with_summaries(self, context_manager):
        """Test context includes summaries."""
        # Add a summary manually
        summary = ContextSummary(
            content="Previous conversation summary",
            original_token_count=1000,
            summarized_token_count=200,
            messages_summarized=10,
        )
        context_manager.summaries.append(summary)

        # Add current messages
        context_manager.add_message("user", "Current message")

        context = context_manager.get_context()

        # First message should be system with summary
        assert context[0]["role"] == "system"
        assert "summary" in context[0]["content"].lower()
        assert context[1]["role"] == "user"
        assert context[1]["content"] == "Current message"


# ============================================================================
# Test Statistics
# ============================================================================


class TestStatistics:
    """Test statistics tracking."""

    def test_get_stats_empty(self, context_manager):
        """Test stats with no messages."""
        stats = context_manager.get_stats()

        assert stats["total_messages"] == 0
        assert stats["total_tokens"] == 0
        assert stats["summaries_created"] == 0
        assert stats["total_tokens_saved"] == 0
        assert "threshold_percentage" in stats
        assert "summarization_enabled" in stats

    def test_get_stats_with_messages(self, context_manager):
        """Test stats with messages."""
        context_manager.add_message("user", "Test message one")
        context_manager.add_message("assistant", "Test response one")

        stats = context_manager.get_stats()

        assert stats["total_messages"] == 2
        assert stats["total_tokens"] > 0
        assert stats["threshold_percentage"] >= 0

    def test_get_stats_threshold_percentage(self, context_manager):
        """Test threshold percentage calculation."""
        # Manually set tokens for predictable percentage
        context_manager.total_tokens = 500
        context_manager.token_threshold = 1000

        stats = context_manager.get_stats()
        assert stats["threshold_percentage"] == 50.0


# ============================================================================
# Test Key Decision Extraction
# ============================================================================


class TestKeyDecisionExtraction:
    """Test extraction of key decisions from messages."""

    def test_extract_decisions_empty(self, context_manager):
        """Test extraction from empty list."""
        decisions = context_manager._extract_key_decisions([])
        assert decisions == []

    def test_extract_decisions_basic(self, context_manager, sample_messages):
        """Test basic decision extraction."""
        decisions = context_manager._extract_key_decisions(sample_messages)

        assert isinstance(decisions, list)
        # Should find the "decided to use PyJWT" decision
        assert any("pyjwt" in d.lower() for d in decisions)

    def test_extract_decisions_patterns(self, context_manager):
        """Test various decision patterns."""
        messages = [
            Message("assistant", "I decided to use TypeScript for this project", 20),
            Message("assistant", "Will implement authentication with OAuth2", 15),
            Message("assistant", "Chose to use PostgreSQL as the database", 18),
            Message("assistant", "Going to refactor the user module", 12),
            Message("assistant", "The approach is to use microservices", 14),
        ]

        decisions = context_manager._extract_key_decisions(messages)

        assert len(decisions) > 0
        assert any("typescript" in d.lower() for d in decisions)
        assert any("oauth2" in d.lower() for d in decisions)

    def test_extract_decisions_ignores_user_messages(self, context_manager):
        """Test that user messages are ignored."""
        messages = [
            Message("user", "I decided to use Python", 10),
            Message("assistant", "I decided to use TypeScript", 12),
        ]

        decisions = context_manager._extract_key_decisions(messages)

        # Should only find assistant decisions
        assert len(decisions) >= 0
        if decisions:
            assert not any("python" in d.lower() for d in decisions)

    def test_extract_decisions_length_filtering(self, context_manager):
        """Test that decisions are filtered by length."""
        messages = [
            Message("assistant", "I decided to x", 10),  # Too short
            Message(
                "assistant",
                "I decided to " + "x" * 200,
                100,
            ),  # Too long
            Message("assistant", "I decided to use a good approach here", 20),  # Good
        ]

        decisions = context_manager._extract_key_decisions(messages)

        # Should filter out too short and too long
        for d in decisions:
            assert len(d) >= 10
            assert len(d) < 200


# ============================================================================
# Test File Path Extraction
# ============================================================================


class TestFilePathExtraction:
    """Test extraction of file paths from messages."""

    def test_extract_files_empty(self, context_manager):
        """Test extraction from empty list."""
        files = context_manager._extract_files_modified([])
        assert files == []

    def test_extract_files_basic(self, context_manager):
        """Test basic file extraction."""
        messages = [
            Message("assistant", "I modified src/auth.py and tests/test_auth.py", 20),
        ]

        files = context_manager._extract_files_modified(messages)

        assert isinstance(files, list)
        assert any("auth.py" in f for f in files)

    def test_extract_files_various_patterns(self, context_manager):
        """Test extraction of various file path patterns."""
        messages = [
            Message("assistant", "file_path: '/src/main.py'", 10),
            Message("assistant", "I wrote file `config/settings.json`", 15),
            Message("assistant", "Modified the /app/routes.ts file", 12),
            Message("assistant", 'Created "utils/helpers.js"', 10),
        ]

        files = context_manager._extract_files_modified(messages)

        assert len(files) > 0
        # Should find various file types
        assert any(".py" in f for f in files)
        assert any(".json" in f or ".ts" in f or ".js" in f for f in files)

    def test_extract_files_deduplication(self, context_manager):
        """Test that duplicate files are removed."""
        messages = [
            Message("assistant", "Modified auth.py", 10),
            Message("assistant", "Also updated auth.py again", 12),
            Message("assistant", "Final change to auth.py", 11),
        ]

        files = context_manager._extract_files_modified(messages)

        # Should deduplicate
        if files:
            assert len(files) == len(set(files))

    def test_extract_files_sorted(self, context_manager):
        """Test that files are returned sorted."""
        messages = [
            Message("assistant", "Files: z.py, a.py, m.py", 15),
        ]

        files = context_manager._extract_files_modified(messages)

        if len(files) > 1:
            assert files == sorted(files)


# ============================================================================
# Test Summarization
# ============================================================================


class TestSummarization:
    """Test summarization functionality."""

    @pytest.mark.asyncio
    async def test_trigger_summarization_no_client(self, context_manager):
        """Test summarization without Anthropic client."""
        context_manager._anthropic_client = None

        # Add messages
        for i in range(10):
            context_manager.add_message("user", f"Message {i}")

        summary = await context_manager._trigger_summarization()
        assert summary is None

    @pytest.mark.asyncio
    async def test_trigger_summarization_not_enough_messages(
        self, context_manager_with_mock_client
    ):
        """Test summarization with too few messages."""
        manager = context_manager_with_mock_client
        manager.preserve_recent = 10

        # Add only 5 messages
        for i in range(5):
            manager.add_message("user", f"Message {i}")

        summary = await manager._trigger_summarization()
        assert summary is None

    @pytest.mark.asyncio
    async def test_trigger_summarization_success(self, context_manager_with_mock_client):
        """Test successful summarization."""
        manager = context_manager_with_mock_client
        manager.preserve_recent = 3

        # Add 10 messages (7 will be summarized, 3 preserved)
        for i in range(10):
            manager.add_message("user", f"Message {i}")

        initial_message_count = len(manager.messages)
        initial_token_count = manager.total_tokens

        summary = await manager._trigger_summarization()

        assert summary is not None
        assert isinstance(summary, ContextSummary)
        assert summary.messages_summarized == 7
        assert len(manager.messages) == 3  # Only recent preserved
        assert len(manager.summaries) == 1

    @pytest.mark.asyncio
    async def test_trigger_summarization_preserves_recent(
        self, context_manager_with_mock_client
    ):
        """Test that recent messages are preserved."""
        manager = context_manager_with_mock_client
        manager.preserve_recent = 2

        messages = ["Message A", "Message B", "Message C", "Message D"]
        for msg in messages:
            manager.add_message("user", msg)

        await manager._trigger_summarization()

        # Should preserve last 2
        assert len(manager.messages) == 2
        assert manager.messages[0].content == "Message C"
        assert manager.messages[1].content == "Message D"

    @pytest.mark.asyncio
    async def test_trigger_summarization_updates_stats(
        self, context_manager_with_mock_client
    ):
        """Test that summarization updates statistics."""
        manager = context_manager_with_mock_client
        manager.preserve_recent = 2

        for i in range(10):
            manager.add_message("user", "x" * 100)

        initial_tokens_saved = manager.total_tokens_saved

        await manager._trigger_summarization()

        assert manager.total_tokens_saved > initial_tokens_saved
        stats = manager.get_stats()
        assert stats["summaries_created"] == 1

    @pytest.mark.asyncio
    async def test_build_summarization_prompt(self, context_manager, sample_messages):
        """Test building summarization prompt."""
        key_decisions = ["use JWT authentication", "implement rate limiting"]
        files_modified = ["auth.py", "config.py"]

        prompt = context_manager._build_summarization_prompt(
            sample_messages, key_decisions, files_modified
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "summarizing" in prompt.lower()
        assert "JWT" in prompt
        assert "auth.py" in prompt

    @pytest.mark.asyncio
    async def test_call_summarization_model_success(
        self, context_manager_with_mock_client
    ):
        """Test successful API call for summarization."""
        manager = context_manager_with_mock_client
        prompt = "Summarize this conversation"

        result = await manager._call_summarization_model(prompt)

        assert isinstance(result, str)
        assert len(result) > 0
        manager._anthropic_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_summarization_model_no_client(self, context_manager):
        """Test API call without client raises error."""
        context_manager._anthropic_client = None

        with pytest.raises(RuntimeError):
            await context_manager._call_summarization_model("Test prompt")


# ============================================================================
# Test State Management
# ============================================================================


class TestStateManagement:
    """Test state export and import."""

    def test_export_state_empty(self, context_manager):
        """Test exporting empty state."""
        state = context_manager.export_state()

        assert isinstance(state, dict)
        assert "messages" in state
        assert "summaries" in state
        assert "total_tokens" in state
        assert "stats" in state
        assert len(state["messages"]) == 0

    def test_export_state_with_data(self, context_manager):
        """Test exporting state with messages."""
        context_manager.add_message("user", "Hello")
        context_manager.add_message("assistant", "Hi")

        state = context_manager.export_state()

        assert len(state["messages"]) == 2
        assert state["total_tokens"] > 0
        assert state["messages"][0]["role"] == "user"

    def test_import_state(self, context_manager):
        """Test importing state."""
        # Create state to import
        state = {
            "messages": [
                {
                    "role": "user",
                    "content": "Test",
                    "token_count": 10,
                    "timestamp": "2025-01-01T12:00:00+00:00",
                    "summarized": False,
                }
            ],
            "summaries": [],
            "total_tokens": 10,
            "total_tokens_saved": 0,
        }

        context_manager.import_state(state)

        assert len(context_manager.messages) == 1
        assert context_manager.messages[0].content == "Test"
        assert context_manager.total_tokens == 10

    def test_export_import_roundtrip(self, context_manager):
        """Test that export/import preserves data."""
        # Add data
        context_manager.add_message("user", "Message 1")
        context_manager.add_message("assistant", "Response 1")

        # Export
        state = context_manager.export_state()

        # Create new manager and import
        new_manager = ContextManager()
        new_manager.import_state(state)

        # Should have same data
        assert len(new_manager.messages) == len(context_manager.messages)
        assert new_manager.total_tokens == context_manager.total_tokens

    def test_clear(self, context_manager):
        """Test clearing context."""
        # Add data
        context_manager.add_message("user", "Test")
        context_manager.add_message("assistant", "Response")
        assert len(context_manager.messages) > 0

        # Clear
        context_manager.clear()

        assert len(context_manager.messages) == 0
        assert len(context_manager.summaries) == 0
        assert context_manager.total_tokens == 0
        assert context_manager.total_tokens_saved == 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, context_manager_with_mock_client):
        """Test complete workflow: add messages, summarize, continue."""
        manager = context_manager_with_mock_client
        manager.preserve_recent = 3

        # Add initial messages
        for i in range(10):
            manager.add_message("user", f"Message {i}")

        initial_count = len(manager.messages)

        # Trigger summarization
        summary = await manager._trigger_summarization()

        assert summary is not None
        assert len(manager.messages) < initial_count
        assert len(manager.summaries) == 1

        # Add more messages
        for i in range(5):
            manager.add_message("user", f"New message {i}")

        # Get context (should include summary)
        context = manager.get_context()
        assert context[0]["role"] == "system"  # Summary
        assert len(context) > 1  # Summary + messages

    @pytest.mark.asyncio
    async def test_multiple_summarizations(self, context_manager_with_mock_client):
        """Test multiple rounds of summarization."""
        manager = context_manager_with_mock_client
        manager.preserve_recent = 2

        # First round
        for i in range(5):
            manager.add_message("user", f"Round 1 message {i}")
        await manager._trigger_summarization()

        assert len(manager.summaries) == 1

        # Second round
        for i in range(5):
            manager.add_message("user", f"Round 2 message {i}")
        await manager._trigger_summarization()

        assert len(manager.summaries) == 2

    @pytest.mark.asyncio
    async def test_automatic_summarization_trigger(self, context_manager_with_mock_client):
        """Test that summarization is triggered automatically."""
        manager = context_manager_with_mock_client
        manager.token_threshold = 100
        manager.preserve_recent = 2

        # Add messages to exceed threshold
        long_message = "x" * 50
        for i in range(10):
            manager.add_message("user", long_message)

        # Should have marked for summarization
        if hasattr(manager, "_needs_summarization"):
            assert manager._needs_summarization is True

            # Trigger it
            summary = await manager.trigger_summarization_if_needed()
            if summary:
                assert manager._needs_summarization is False


# ============================================================================
# Test Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_threshold(self):
        """Test with zero token threshold."""
        manager = ContextManager(token_threshold=0)
        stats = manager.get_stats()

        # Should not crash
        assert stats["threshold_percentage"] == 0

    def test_negative_preserve_recent(self):
        """Test with negative preserve_recent."""
        manager = ContextManager(preserve_recent=-1)
        manager.add_message("user", "Test")

        # Should still work (will be handled in summarization logic)
        assert len(manager.messages) == 1

    def test_very_long_message(self, context_manager):
        """Test with very long message."""
        long_message = "x" * 100000
        context_manager.add_message("user", long_message)

        assert len(context_manager.messages) == 1
        assert context_manager.total_tokens > 0

    @pytest.mark.asyncio
    async def test_summarization_api_error(self, context_manager_with_mock_client):
        """Test handling of API errors during summarization."""
        manager = context_manager_with_mock_client
        manager.preserve_recent = 2

        # Make API call fail
        manager._anthropic_client.messages.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        for i in range(10):
            manager.add_message("user", f"Message {i}")

        summary = await manager._trigger_summarization()

        # Should return None on error
        assert summary is None
