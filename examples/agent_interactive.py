#!/usr/bin/env python3
"""
Interactive REPL for testing Sugar 3.0 Agent SDK.

Run with: ./venv/bin/python test_agent_repl.py
"""

import asyncio
import sys
from sugar.agent.base import SugarAgent, SugarAgentConfig


async def main():
    config = SugarAgentConfig(
        model="claude-sonnet-4-20250514",
        permission_mode="acceptEdits",
        quality_gates_enabled=True,
    )

    agent = SugarAgent(config)

    print("=" * 60)
    print("Sugar 3.0 Interactive Agent")
    print("=" * 60)
    print("Type your prompts and press Enter.")
    print("Commands: 'quit' to exit, 'history' to see execution history")
    print("=" * 60)

    async with agent:
        while True:
            try:
                prompt = input("\n🍰 > ").strip()

                if not prompt:
                    continue

                if prompt.lower() == 'quit':
                    print("Goodbye!")
                    break

                if prompt.lower() == 'history':
                    history = agent.get_execution_history()
                    print(f"\n{len(history)} executions:")
                    for i, h in enumerate(history):
                        print(f"  {i+1}. {h['prompt'][:50]}...")
                    continue

                print("\nExecuting...")
                response = await agent.execute(prompt)

                print(f"\n✓ Success: {response.success} | Time: {response.execution_time:.2f}s")

                if response.tool_uses:
                    print(f"  Tools used: {', '.join(t['tool'] for t in response.tool_uses)}")

                if response.files_modified:
                    print(f"  Files modified: {', '.join(response.files_modified)}")

                if response.content:
                    print(f"\n{response.content}")

                if response.error:
                    print(f"\n❌ Error: {response.error}")

            except KeyboardInterrupt:
                print("\nInterrupted. Type 'quit' to exit.")
            except EOFError:
                break


if __name__ == "__main__":
    asyncio.run(main())
