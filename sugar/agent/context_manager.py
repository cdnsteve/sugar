"""
Context Manager - Manages conversation context with automatic summarization

This module provides intelligent context management for long-running conversations,
automatically summarizing older messages to stay within token limits while preserving
key information.

Features:
- Automatic token counting and threshold management
- Claude Haiku-powered summarization for cost efficiency
- Preservation of recent messages in full
- Extraction of key decisions and file modifications
- Graceful fallback when Anthropic SDK is unavailable
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import anthropic for summarization
try:
    from anthropic import AsyncAnthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.debug("Anthropic SDK not available - summarization will be disabled")

# Try to import tiktoken for accurate token counting
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.debug("tiktoken not available - using character-based approximation")


@dataclass
class Message:
    """Represents a single message in the conversation context"""

    role: str  # "user", "assistant", "system"
    content: str
    token_count: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    summarized: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "role": self.role,
            "content": self.content,
            "token_count": self.token_count,
            "timestamp": self.timestamp.isoformat(),
            "summarized": self.summarized,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary"""
        return cls(
            role=data["role"],
            content=data["content"],
            token_count=data["token_count"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            summarized=data.get("summarized", False),
        )


@dataclass
class ContextSummary:
    """Represents a summarized portion of the conversation"""

    content: str
    original_token_count: int
    summarized_token_count: int
    messages_summarized: int
    key_decisions: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary"""
        return {
            "content": self.content,
            "original_token_count": self.original_token_count,
            "summarized_token_count": self.summarized_token_count,
            "messages_summarized": self.messages_summarized,
            "key_decisions": self.key_decisions,
            "files_modified": self.files_modified,
            "timestamp": self.timestamp.isoformat(),
        }


class ContextManager:
    """
    Manages conversation context with automatic summarization.

    Tracks messages and their token counts, automatically triggering
    summarization when thresholds are exceeded to keep context manageable.
    """

    def __init__(
        self,
        token_threshold: int = 150000,
        preserve_recent: int = 10,
        summarization_model: str = "claude-3-haiku-20240307",
        anthropic_api_key: Optional[str] = None,
    ):
        """
        Initialize the context manager.

        Args:
            token_threshold: Token limit before triggering summarization
            preserve_recent: Number of recent messages to preserve in full
            summarization_model: Claude model to use for summarization
            anthropic_api_key: Optional API key (falls back to env var)
        """
        self.token_threshold = token_threshold
        self.preserve_recent = preserve_recent
        self.summarization_model = summarization_model

        self.messages: List[Message] = []
        self.summaries: List[ContextSummary] = []
        self.total_tokens = 0
        self.total_tokens_saved = 0

        # Token encoder for accurate counting
        self._encoder = None
        if TIKTOKEN_AVAILABLE:
            try:
                self._encoder = tiktoken.encoding_for_model("gpt-4")
                logger.debug("Using tiktoken for accurate token counting")
            except Exception as e:
                logger.warning(f"Failed to initialize tiktoken: {e}")

        # Anthropic client for summarization
        self._anthropic_client = None
        if ANTHROPIC_AVAILABLE:
            try:
                self._anthropic_client = AsyncAnthropic(api_key=anthropic_api_key)
                logger.debug("Anthropic client initialized for summarization")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")

        logger.info(
            f"ContextManager initialized: threshold={token_threshold}, "
            f"preserve_recent={preserve_recent}, "
            f"summarization_enabled={self._anthropic_client is not None}"
        )

    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the context.

        Automatically triggers summarization if token threshold is exceeded.

        Args:
            role: Message role ("user", "assistant", "system")
            content: Message content
        """
        token_count = self._count_tokens(content)
        message = Message(
            role=role,
            content=content,
            token_count=token_count,
        )

        self.messages.append(message)
        self.total_tokens += token_count

        logger.debug(
            f"Added message: role={role}, tokens={token_count}, "
            f"total_tokens={self.total_tokens}"
        )

        # Check if we need to summarize
        if self.total_tokens > self.token_threshold:
            logger.info(
                f"Token threshold exceeded ({self.total_tokens} > {self.token_threshold}), "
                "triggering summarization"
            )
            # Schedule summarization asynchronously
            # Note: This is sync method, actual summarization happens on next get_context
            self._needs_summarization = True

    def get_context(self) -> List[Dict[str, str]]:
        """
        Get the current context for the agent.

        Returns messages in the format expected by Claude:
        [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]

        If summaries exist, they are prepended as a system message.

        Returns:
            List of message dictionaries
        """
        context = []

        # Add summaries as system context if they exist
        if self.summaries:
            summary_content = self._build_summary_context()
            context.append({"role": "system", "content": summary_content})

        # Add all current messages
        for msg in self.messages:
            context.append({"role": msg.role, "content": msg.content})

        return context

    async def trigger_summarization_if_needed(self) -> Optional[ContextSummary]:
        """
        Trigger summarization if needed and possible.

        Returns:
            ContextSummary if summarization occurred, None otherwise
        """
        if not hasattr(self, "_needs_summarization") or not self._needs_summarization:
            return None

        self._needs_summarization = False
        return await self._trigger_summarization()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the context.

        Returns:
            Dictionary with token counts, message counts, and savings
        """
        return {
            "total_messages": len(self.messages),
            "total_tokens": self.total_tokens,
            "token_threshold": self.token_threshold,
            "threshold_percentage": (
                (self.total_tokens / self.token_threshold * 100)
                if self.token_threshold > 0
                else 0
            ),
            "summaries_created": len(self.summaries),
            "total_tokens_saved": self.total_tokens_saved,
            "messages_in_summaries": sum(s.messages_summarized for s in self.summaries),
            "summarization_enabled": self._anthropic_client is not None,
            "recent_messages_preserved": self.preserve_recent,
        }

    async def _trigger_summarization(self) -> Optional[ContextSummary]:
        """
        Perform summarization of older messages.

        Summarizes all but the most recent N messages, replacing them
        with a compact summary that preserves key information.

        Returns:
            ContextSummary if successful, None otherwise
        """
        if not self._anthropic_client:
            logger.warning(
                "Summarization requested but Anthropic client not available"
            )
            return None

        # Determine which messages to summarize
        if len(self.messages) <= self.preserve_recent:
            logger.debug("Not enough messages to summarize")
            return None

        messages_to_summarize = self.messages[: -self.preserve_recent]
        messages_to_keep = self.messages[-self.preserve_recent :]

        if not messages_to_summarize:
            logger.debug("No messages to summarize")
            return None

        logger.info(
            f"Summarizing {len(messages_to_summarize)} messages, "
            f"preserving {len(messages_to_keep)} recent messages"
        )

        # Extract key information
        key_decisions = self._extract_key_decisions(messages_to_summarize)
        files_modified = self._extract_files_modified(messages_to_summarize)

        # Build summarization prompt
        prompt = self._build_summarization_prompt(
            messages_to_summarize, key_decisions, files_modified
        )

        # Call summarization model
        try:
            summary_content = await self._call_summarization_model(prompt)

            # Calculate token counts
            original_tokens = sum(m.token_count for m in messages_to_summarize)
            summary_tokens = self._count_tokens(summary_content)
            tokens_saved = original_tokens - summary_tokens

            # Create summary object
            summary = ContextSummary(
                content=summary_content,
                original_token_count=original_tokens,
                summarized_token_count=summary_tokens,
                messages_summarized=len(messages_to_summarize),
                key_decisions=key_decisions,
                files_modified=files_modified,
            )

            # Update state
            self.summaries.append(summary)
            self.messages = messages_to_keep
            self.total_tokens = sum(m.token_count for m in self.messages) + sum(
                s.summarized_token_count for s in self.summaries
            )
            self.total_tokens_saved += tokens_saved

            logger.info(
                f"Summarization complete: {original_tokens} -> {summary_tokens} tokens "
                f"({tokens_saved} saved, {(tokens_saved/original_tokens*100):.1f}% reduction)"
            )

            return summary

        except Exception as e:
            logger.error(f"Summarization failed: {e}", exc_info=True)
            return None

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Uses tiktoken if available, otherwise approximates with character count.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        if self._encoder:
            try:
                return len(self._encoder.encode(text))
            except Exception as e:
                logger.warning(f"Token encoding failed: {e}")

        # Fallback: approximate as chars / 4 (rough estimate for English)
        return len(text) // 4

    def _extract_key_decisions(self, messages: List[Message]) -> List[str]:
        """
        Extract key decisions from messages.

        Looks for patterns indicating decisions or important outcomes.

        Args:
            messages: Messages to analyze

        Returns:
            List of key decision strings
        """
        decisions = []
        decision_patterns = [
            r"decided to (.+?)(?:\.|$)",
            r"will implement (.+?)(?:\.|$)",
            r"chose (.+?)(?:\.|$)",
            r"going to (.+?)(?:\.|$)",
            r"plan to (.+?)(?:\.|$)",
            r"approach is to (.+?)(?:\.|$)",
        ]

        for msg in messages:
            if msg.role != "assistant":
                continue

            content_lower = msg.content.lower()
            for pattern in decision_patterns:
                matches = re.findall(pattern, content_lower, re.IGNORECASE)
                for match in matches:
                    decision = match.strip()
                    if len(decision) > 10 and len(decision) < 200:
                        decisions.append(decision)

        # Deduplicate and limit
        decisions = list(dict.fromkeys(decisions))[:10]
        return decisions

    def _extract_files_modified(self, messages: List[Message]) -> List[str]:
        """
        Extract file paths mentioned in messages.

        Looks for file paths in tool uses and content.

        Args:
            messages: Messages to analyze

        Returns:
            List of file paths
        """
        files = set()

        # Common file path patterns
        path_patterns = [
            r"(?:file_path|path)[\"\']?\s*:\s*[\"\']([^\"\'\s]+)[\"\']",
            r"(?:wrote|edited|modified|created|read)\s+(?:file\s+)?[`\"]?([/\w\.\-]+\.\w+)[`\"]?",
            r"`([/\w\.\-]+\.\w+)`",
        ]

        for msg in messages:
            for pattern in path_patterns:
                matches = re.findall(pattern, msg.content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    # Filter out obviously wrong matches
                    if (
                        len(match) > 2
                        and "/" in match or "\\" in match or "." in match
                    ):
                        files.add(match)

        return sorted(list(files))

    def _build_summarization_prompt(
        self,
        messages: List[Message],
        key_decisions: List[str],
        files_modified: List[str],
    ) -> str:
        """
        Build the prompt for summarization.

        Args:
            messages: Messages to summarize
            key_decisions: Extracted key decisions
            files_modified: Extracted file paths

        Returns:
            Summarization prompt
        """
        # Build conversation text
        conversation_text = "\n\n".join(
            [f"[{msg.role.upper()}]: {msg.content}" for msg in messages]
        )

        prompt = f"""You are summarizing a conversation between a user and an AI development assistant.

Your task is to create a concise summary that preserves the essential information while reducing token count.

FOCUS ON:
1. Technical decisions made
2. Implementation approaches chosen
3. Files modified or created
4. Key outcomes and results
5. Important context for future work

DO NOT INCLUDE:
- Verbose explanations
- Step-by-step reasoning
- Tool usage details
- Intermediate debugging steps

DETECTED KEY DECISIONS:
{chr(10).join(f"- {d}" for d in key_decisions) if key_decisions else "None detected"}

DETECTED FILE MODIFICATIONS:
{chr(10).join(f"- {f}" for f in files_modified) if files_modified else "None detected"}

CONVERSATION TO SUMMARIZE:
{conversation_text}

Provide a concise summary in 2-4 paragraphs that captures the essential information."""

        return prompt

    async def _call_summarization_model(self, prompt: str) -> str:
        """
        Call Claude Haiku to generate a summary.

        Args:
            prompt: Summarization prompt

        Returns:
            Summary text

        Raises:
            Exception if API call fails
        """
        if not self._anthropic_client:
            raise RuntimeError("Anthropic client not initialized")

        try:
            response = await self._anthropic_client.messages.create(
                model=self.summarization_model,
                max_tokens=2000,
                temperature=0.3,  # Lower temperature for more focused summaries
                messages=[{"role": "user", "content": prompt}],
            )

            summary = response.content[0].text
            logger.debug(f"Summarization API call successful, summary length: {len(summary)}")
            return summary

        except Exception as e:
            logger.error(f"Summarization API call failed: {e}")
            raise

    def _build_summary_context(self) -> str:
        """
        Build a context message from all summaries.

        Returns:
            Combined summary context
        """
        if not self.summaries:
            return ""

        parts = ["=== Previous Conversation Summary ===\n"]

        for i, summary in enumerate(self.summaries, 1):
            parts.append(f"\n--- Summary {i} ---")
            parts.append(summary.content)

            if summary.files_modified:
                parts.append(
                    f"\nFiles modified: {', '.join(summary.files_modified[:10])}"
                )

        parts.append("\n=== End of Summary ===\n")
        return "\n".join(parts)

    def clear(self) -> None:
        """Clear all messages and summaries."""
        self.messages.clear()
        self.summaries.clear()
        self.total_tokens = 0
        self.total_tokens_saved = 0
        if hasattr(self, "_needs_summarization"):
            self._needs_summarization = False
        logger.info("Context cleared")

    def export_state(self) -> Dict[str, Any]:
        """
        Export the current state for persistence.

        Returns:
            Dictionary containing all state
        """
        return {
            "messages": [m.to_dict() for m in self.messages],
            "summaries": [s.to_dict() for s in self.summaries],
            "total_tokens": self.total_tokens,
            "total_tokens_saved": self.total_tokens_saved,
            "stats": self.get_stats(),
        }

    def import_state(self, state: Dict[str, Any]) -> None:
        """
        Import state from exported data.

        Args:
            state: State dictionary from export_state()
        """
        self.messages = [Message.from_dict(m) for m in state.get("messages", [])]
        self.summaries = [
            ContextSummary(**s) for s in state.get("summaries", [])
        ]  # Note: ContextSummary needs from_dict too if timestamps matter
        self.total_tokens = state.get("total_tokens", 0)
        self.total_tokens_saved = state.get("total_tokens_saved", 0)
        logger.info("Context state imported")
