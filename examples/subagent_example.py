"""
Example: Using SubAgentManager to spawn sub-agents for parallel execution

This example demonstrates:
1. Creating a SubAgentManager from a parent agent config
2. Spawning a single sub-agent for an isolated task
3. Spawning multiple sub-agents in parallel with concurrency control
4. Handling results and tracking file modifications
"""

import asyncio
from sugar.agent import SugarAgent, SugarAgentConfig, SubAgentManager


async def example_single_subagent():
    """Example: Spawn a single sub-agent"""

    # Create parent agent configuration
    parent_config = SugarAgentConfig(
        model="claude-sonnet-4-20250514",
        permission_mode="acceptEdits",
        quality_gates_enabled=True,
        timeout=300,
    )

    # Create SubAgentManager
    manager = SubAgentManager(
        parent_config=parent_config,
        max_concurrent=3,  # Allow up to 3 concurrent sub-agents
        default_timeout=120,  # 2 minutes per task
    )

    # Spawn a sub-agent for a specific task
    result = await manager.spawn(
        task_id="refactor-auth",
        prompt="Refactor the authentication module to use JWT tokens",
        task_context="Part of security upgrade sprint",
        timeout=180,  # Custom timeout for this task
    )

    # Check results
    if result.success:
        print(f"Task {result.task_id} completed successfully!")
        print(f"Summary: {result.summary}")
        print(f"Files modified: {result.files_modified}")
        print(f"Execution time: {result.execution_time:.2f}s")
    else:
        print(f"Task {result.task_id} failed: {result.error}")

    return result


async def example_parallel_subagents():
    """Example: Spawn multiple sub-agents in parallel"""

    parent_config = SugarAgentConfig(
        model="claude-sonnet-4-20250514",
        permission_mode="acceptEdits",
    )

    manager = SubAgentManager(
        parent_config=parent_config,
        max_concurrent=3,  # Process 3 tasks at a time
        default_timeout=120,
    )

    # Define multiple tasks to execute in parallel
    tasks = [
        {
            "task_id": "implement-login",
            "prompt": "Implement the login endpoint with JWT authentication",
            "context": "Auth feature - login flow",
        },
        {
            "task_id": "implement-logout",
            "prompt": "Implement the logout endpoint that invalidates tokens",
            "context": "Auth feature - logout flow",
        },
        {
            "task_id": "implement-refresh",
            "prompt": "Implement token refresh endpoint",
            "context": "Auth feature - token refresh",
        },
        {
            "task_id": "add-tests",
            "prompt": "Add unit tests for all auth endpoints",
            "context": "Auth feature - testing",
            "timeout": 180,  # This task gets extra time
        },
    ]

    # Spawn all sub-agents in parallel
    # They will respect max_concurrent limit (3 at a time)
    results = await manager.spawn_parallel(tasks)

    # Process results
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print(f"\nCompleted {len(successful)}/{len(tasks)} tasks successfully")

    for result in successful:
        print(f"\n✓ {result.task_id}")
        print(f"  Summary: {result.summary}")
        print(f"  Files: {', '.join(result.files_modified)}")
        print(f"  Time: {result.execution_time:.2f}s")

    if failed:
        print(f"\n{len(failed)} tasks failed:")
        for result in failed:
            print(f"\n✗ {result.task_id}")
            print(f"  Error: {result.error}")

    # Get all modified files across all tasks
    all_files = set()
    for result in results:
        all_files.update(result.files_modified)

    print(f"\nTotal files modified: {len(all_files)}")
    print(f"Files: {', '.join(sorted(all_files))}")

    return results


async def example_with_parent_agent():
    """Example: Using SubAgentManager within a parent agent's workflow"""

    # Create and configure parent agent
    parent_config = SugarAgentConfig(
        model="claude-sonnet-4-20250514",
        permission_mode="acceptEdits",
        quality_gates_enabled=True,
    )

    parent_agent = SugarAgent(parent_config)

    # Parent agent could analyze what needs to be done
    # and then spawn sub-agents for independent sub-tasks

    # Create manager using parent's config
    manager = SubAgentManager(
        parent_config=parent_agent.config,
        max_concurrent=3,
        default_timeout=120,
    )

    # Spawn sub-agents for different components
    tasks = [
        {
            "task_id": "backend-api",
            "prompt": "Implement the backend API endpoints for user management",
        },
        {
            "task_id": "frontend-ui",
            "prompt": "Create the frontend UI components for user management",
        },
        {
            "task_id": "database-schema",
            "prompt": "Design and implement the database schema for users",
        },
    ]

    results = await manager.spawn_parallel(tasks)

    # Parent agent could then integrate the results
    print("\nSub-agents completed. Parent agent integrating results...")

    return results


async def main():
    """Run all examples"""
    print("=" * 60)
    print("Example 1: Single Sub-Agent")
    print("=" * 60)
    await example_single_subagent()

    print("\n" + "=" * 60)
    print("Example 2: Parallel Sub-Agents")
    print("=" * 60)
    await example_parallel_subagents()

    print("\n" + "=" * 60)
    print("Example 3: Sub-Agents with Parent Agent")
    print("=" * 60)
    await example_with_parent_agent()


if __name__ == "__main__":
    # Note: This is a conceptual example
    # In practice, you would use this within Sugar's workflow
    # where the Claude Agent SDK is properly configured
    print("SubAgentManager Usage Examples")
    print("Note: These are conceptual examples showing the API")
    print("In production, sub-agents would actually execute tasks\n")

    # Uncomment to run (requires proper SDK setup):
    # asyncio.run(main())
