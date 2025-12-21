#!/usr/bin/env python3
"""
Local test script for Sugar 3.0 Agent SDK integration.

Run with: ./venv/bin/python test_agent_local.py
"""

import asyncio
from sugar.agent.base import SugarAgent, SugarAgentConfig


async def main():
    # Configure the agent
    config = SugarAgentConfig(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        permission_mode="acceptEdits",  # Auto-accept file edits
        quality_gates_enabled=True,      # Enable security hooks
        working_directory="/Users/steve/Dev/sugar",
    )

    # Create agent with quality gates
    agent = SugarAgent(config, quality_gates_config={
        "enabled": True,
        "protected_paths": [".env", "credentials.json"],
    })

    print("=" * 60)
    print("Sugar 3.0 Agent SDK Test")
    print("=" * 60)
    print(f"Model: {config.model}")
    print(f"Quality Gates: {'Enabled' if config.quality_gates_enabled else 'Disabled'}")
    print("=" * 60)

    # Start a session
    async with agent:
        # Test prompt - change this to whatever you want to test
        prompt = """
        Read the pyproject.toml file and tell me:
        1. What is the current version?
        2. What are the main dependencies?
        3. What Python versions are supported?
        """

        print(f"\nPrompt: {prompt.strip()[:100]}...")
        print("\nExecuting...\n")

        response = await agent.execute(prompt)

        print("-" * 60)
        print("RESPONSE")
        print("-" * 60)
        print(f"Success: {response.success}")
        print(f"Execution Time: {response.execution_time:.2f}s")
        print(f"Tool Uses: {len(response.tool_uses)}")
        print(f"Files Modified: {response.files_modified}")
        print()

        if response.content:
            print("Content:")
            print(response.content[:2000])  # First 2000 chars

        if response.error:
            print(f"\nError: {response.error}")

        # Show quality gate results
        if response.quality_gate_results:
            print("\nQuality Gate Results:")
            for key, value in response.quality_gate_results.items():
                print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
