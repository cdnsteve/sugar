#!/usr/bin/env python3
"""
Context Manager Demo

This script demonstrates how to use the ContextManager for managing
conversation context with automatic summarization.

Run with:
    python examples/context_manager_demo.py
"""

import asyncio
import sys
import importlib.util
from pathlib import Path

# Import ContextManager directly to avoid SDK dependencies
spec = importlib.util.spec_from_file_location(
    "context_manager",
    Path(__file__).parent.parent / "sugar" / "agent" / "context_manager.py"
)
cm_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm_module)

ContextManager = cm_module.ContextManager


async def main():
    """Demonstrate ContextManager usage."""

    print("=" * 70)
    print("Context Manager Demo")
    print("=" * 70)
    print()

    # Create a context manager with a low threshold for demo purposes
    manager = ContextManager(
        token_threshold=500,  # Low threshold to trigger summarization
        preserve_recent=3,     # Keep last 3 messages in full
        summarization_model="claude-3-haiku-20240307"
    )

    print(f"Initial configuration:")
    print(f"  - Token threshold: {manager.token_threshold}")
    print(f"  - Preserve recent: {manager.preserve_recent}")
    print(f"  - Summarization enabled: {manager._anthropic_client is not None}")
    print()

    # Simulate a conversation
    conversation = [
        ("user", "I need to build a user authentication system for my web app."),
        ("assistant", "I'll help you build authentication. First, let me understand your requirements. What framework are you using?"),
        ("user", "I'm using FastAPI for the backend and React for the frontend."),
        ("assistant", "Great! I decided to implement JWT-based authentication. I'll create the following files: auth.py for authentication logic, models.py for user models, and routes.py for API endpoints."),
        ("user", "Sounds good. Can you also add password hashing?"),
        ("assistant", "Yes, I'll use bcrypt for password hashing. I modified auth.py to include password hashing and verification functions."),
        ("user", "What about refresh tokens?"),
        ("assistant", "I'll implement refresh token rotation. The approach is to store refresh tokens in a database with expiration. I created token_manager.py for this."),
        ("user", "Perfect. Can you add rate limiting?"),
        ("assistant", "I decided to use Redis for rate limiting. I modified middleware.py to add rate limiting decorator and config.py for Redis settings."),
    ]

    print("Adding messages to context...")
    print()

    for i, (role, content) in enumerate(conversation, 1):
        manager.add_message(role, content)
        stats = manager.get_stats()

        print(f"Message {i} ({role}):")
        print(f"  Content: {content[:60]}...")
        print(f"  Total messages: {stats['total_messages']}")
        print(f"  Total tokens: {stats['total_tokens']}")
        print(f"  Threshold: {stats['threshold_percentage']:.1f}%")

        if stats['total_tokens'] > manager.token_threshold:
            print(f"  ⚠️  Threshold exceeded! Summarization would be triggered.")
        print()

    # Show statistics
    print("=" * 70)
    print("Final Statistics")
    print("=" * 70)
    stats = manager.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()

    # Demonstrate key decision extraction
    print("=" * 70)
    print("Extracted Key Decisions")
    print("=" * 70)
    decisions = manager._extract_key_decisions(manager.messages)
    for i, decision in enumerate(decisions, 1):
        print(f"  {i}. {decision}")
    print()

    # Demonstrate file extraction
    print("=" * 70)
    print("Extracted Files Modified")
    print("=" * 70)
    files = manager._extract_files_modified(manager.messages)
    for i, file in enumerate(files, 1):
        print(f"  {i}. {file}")
    print()

    # Show context format
    print("=" * 70)
    print("Context Format (for Claude API)")
    print("=" * 70)
    context = manager.get_context()
    print(f"Total context messages: {len(context)}")
    for i, msg in enumerate(context[:3], 1):  # Show first 3
        print(f"\n  Message {i}:")
        print(f"    Role: {msg['role']}")
        print(f"    Content: {msg['content'][:100]}...")
    print()

    # Demonstrate state export/import
    print("=" * 70)
    print("State Export/Import")
    print("=" * 70)
    state = manager.export_state()
    print(f"Exported state contains:")
    print(f"  - Messages: {len(state['messages'])}")
    print(f"  - Summaries: {len(state['summaries'])}")
    print(f"  - Total tokens: {state['total_tokens']}")
    print()

    # If Anthropic client is available, demonstrate summarization
    if manager._anthropic_client:
        print("=" * 70)
        print("Summarization Demo")
        print("=" * 70)
        print("Note: Summarization would call Claude Haiku API")
        print("This demo doesn't make actual API calls")
        print()
    else:
        print("=" * 70)
        print("Summarization Info")
        print("=" * 70)
        print("Summarization is disabled (Anthropic SDK not available)")
        print("To enable summarization:")
        print("  1. Install: pip install anthropic")
        print("  2. Set ANTHROPIC_API_KEY environment variable")
        print()

    # Clear context
    manager.clear()
    print("Context cleared!")
    print(f"Messages after clear: {len(manager.messages)}")
    print()

    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
