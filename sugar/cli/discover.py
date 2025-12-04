"""
Sugar Discover CLI Command - Run external tool discovery workflow

This command executes configured external code quality tools, passes their output
to Claude Code for interpretation, and creates Sugar tasks from the results.
"""

import asyncio
import click
import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def _parse_sugar_add_commands(claude_output: str) -> List[Dict[str, Any]]:
    """
    Parse sugar add commands from Claude's output.

    Args:
        claude_output: Raw output from Claude Code containing sugar add commands

    Returns:
        List of parsed command dictionaries with task details
    """
    commands = []

    # Match sugar add commands with various option formats
    # Pattern handles: sugar add "title" --type x --priority N --description "..."
    pattern = r'sugar\s+add\s+"([^"]+)"([^\n]*)'

    matches = re.findall(pattern, claude_output, re.MULTILINE)

    for title, options_str in matches:
        command = {"title": title}

        # Parse --type
        type_match = re.search(r"--type\s+(\S+)", options_str)
        if type_match:
            command["type"] = type_match.group(1)
        else:
            command["type"] = "refactor"  # Default type for tool discoveries

        # Parse --priority
        priority_match = re.search(r"--priority\s+(\d+)", options_str)
        if priority_match:
            command["priority"] = int(priority_match.group(1))
        else:
            command["priority"] = 3  # Default priority

        # Parse --urgent flag
        if "--urgent" in options_str:
            command["priority"] = 5

        # Parse --description
        desc_match = re.search(r'--description\s+"([^"]*)"', options_str)
        if desc_match:
            command["description"] = desc_match.group(1)
        else:
            command["description"] = f"Discovered by external tool analysis: {title}"

        # Parse --status
        status_match = re.search(r"--status\s+(\S+)", options_str)
        if status_match:
            command["status"] = status_match.group(1)
        else:
            command["status"] = "pending"

        commands.append(command)

    return commands


async def _execute_tool_discovery(
    tool_config,
    working_dir: Path,
    timeout: int,
    dry_run: bool,
    work_queue,
    claude_wrapper,
    prompt_template_manager,
) -> Dict[str, Any]:
    """
    Execute a single tool and process its output.

    Returns a summary dict with success status and task count.
    """
    from sugar.discovery.orchestrator import ToolOrchestrator
    from sugar.discovery.prompt_templates import create_tool_interpretation_prompt

    # Create orchestrator for single tool
    orchestrator = ToolOrchestrator(
        external_tools=[tool_config],
        working_dir=working_dir,
        default_timeout=timeout,
    )

    # Execute the tool
    results = orchestrator.execute_all(timeout_per_tool=timeout)

    if not results:
        return {
            "name": tool_config.name,
            "success": False,
            "error": "No results returned",
            "tasks_created": 0,
        }

    result = results[0]

    # Build result summary
    summary = {
        "name": result.name,
        "command": result.command,
        "exit_code": result.exit_code,
        "duration": result.duration_seconds,
        "stdout_lines": len(result.stdout.split("\n")) if result.stdout else 0,
        "success": result.success,
        "tasks_created": 0,
        "error": result.error_message,
    }

    if not result.success:
        if result.tool_not_found:
            summary["error"] = f"Tool not found: {result.command.split()[0]}"
        elif result.timed_out:
            summary["error"] = f"Tool timed out after {timeout}s"
        return summary

    # Check if tool produced output
    if not result.has_output:
        summary["error"] = "No output from tool"
        return summary

    # Check if output file exists
    if not result.output_path or not result.output_path.exists():
        summary["error"] = "No output file from tool"
        return summary

    # Create interpretation prompt with file path (not inline content)
    # Claude Code will read the file directly
    prompt = create_tool_interpretation_prompt(
        tool_name=result.name,
        command=result.command,
        output_file_path=result.output_path,
    )

    # Pass to Claude Code for interpretation
    if dry_run:
        output_size = result.output_path.stat().st_size if result.output_path else 0
        click.echo(
            f"   📝 [DRY-RUN] Would pass file to Claude Code: {result.output_path}"
        )
        click.echo(f"   📝 [DRY-RUN] Output file size: {output_size} bytes")
        click.echo(f"   📝 [DRY-RUN] Prompt preview (first 500 chars):")
        click.echo(f"      {prompt[:500]}...")
        summary["dry_run"] = True
        return summary

    # Execute Claude to interpret the output
    work_item = {
        "id": f"discover_{result.name}",
        "type": "discovery",
        "title": f"Interpret {result.name} output",
        "description": prompt,
        "priority": 3,
        "context": {
            "tool_name": result.name,
            "tool_command": result.command,
            "discovery_mode": True,
        },
    }

    try:
        # Execute Claude wrapper
        claude_result = await claude_wrapper.execute_work(work_item)

        if claude_result.get("success"):
            # Parse sugar add commands from output
            claude_output = claude_result.get("output", "") or claude_result.get(
                "result", {}
            ).get("stdout", "")
            parsed_commands = _parse_sugar_add_commands(claude_output)

            # Create tasks from parsed commands
            import uuid
            from datetime import datetime

            for cmd in parsed_commands:
                task_data = {
                    "id": str(uuid.uuid4()),
                    "type": cmd.get("type", "refactor"),
                    "title": cmd["title"],
                    "description": cmd.get("description", ""),
                    "priority": cmd.get("priority", 3),
                    "status": cmd.get("status", "pending"),
                    "source": f"discover:{result.name}",
                    "context": {
                        "discovered_by": result.name,
                        "discovery_command": result.command,
                        "added_via": "sugar_discover",
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
                await work_queue.add_work(task_data)
                summary["tasks_created"] += 1

        else:
            summary["error"] = (
                f"Claude interpretation failed: {claude_result.get('error', 'Unknown error')}"
            )

    except Exception as e:
        summary["error"] = f"Claude execution error: {str(e)}"
        logger.exception(f"Error during Claude interpretation for {result.name}")

    return summary


@click.command()
@click.option(
    "--tool",
    "tool_name",
    default=None,
    help="Run specific tool only (default: all configured)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show tool outputs without creating tasks",
)
@click.option(
    "--timeout",
    default=300,
    type=int,
    help="Per-tool timeout in seconds (default: 300)",
)
@click.pass_context
def discover(ctx, tool_name: Optional[str], dry_run: bool, timeout: int):
    """Run external tool discovery workflow

    Executes configured external code quality tools, passes their output
    to Claude Code for interpretation, and creates Sugar tasks from the results.

    Examples:

        # Run all configured tools
        sugar discover

        # Run specific tool
        sugar discover --tool eslint

        # Preview without creating tasks
        sugar discover --dry-run

        # Custom timeout
        sugar discover --timeout 600
    """
    import yaml
    from sugar.storage.work_queue import WorkQueue
    from sugar.executor.claude_wrapper import ClaudeWrapper
    from sugar.discovery.external_tool_config import (
        parse_external_tools_from_code_quality_config,
        ExternalToolConfigError,
    )
    from sugar.discovery.orchestrator import ToolOrchestrator
    from sugar.discovery.prompt_templates import PromptTemplateManager

    config_file = ctx.obj.get("config", ".sugar/config.yaml")

    # Load configuration
    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        click.echo(f"❌ Configuration file not found: {config_file}")
        click.echo("   Run 'sugar init' to initialize Sugar in this directory.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error loading configuration: {e}")
        sys.exit(1)

    sugar_config = config.get("sugar", {})
    discovery_config = sugar_config.get("discovery", {})
    code_quality_config = discovery_config.get("code_quality", {})

    # Check if external tools are configured
    if not code_quality_config.get("external_tools"):
        click.echo("❌ No external tools configured.")
        click.echo("")
        click.echo("   Add external tools to your .sugar/config.yaml:")
        click.echo("")
        click.echo("   discovery:")
        click.echo("     code_quality:")
        click.echo("       external_tools:")
        click.echo("         - name: eslint")
        click.echo('           command: "npx eslint . --format json"')
        click.echo("         - name: ruff")
        click.echo('           command: "ruff check . --output-format json"')
        click.echo("")
        sys.exit(1)

    # Parse and validate external tool configurations
    try:
        external_tools = parse_external_tools_from_code_quality_config(
            code_quality_config
        )
    except ExternalToolConfigError as e:
        click.echo(f"❌ Invalid external tool configuration: {e}")
        sys.exit(1)

    if not external_tools:
        click.echo("❌ No external tools configured in code_quality.external_tools")
        sys.exit(1)

    # Filter to specific tool if requested
    if tool_name:
        matching_tools = [
            t for t in external_tools if t.name.lower() == tool_name.lower()
        ]
        if not matching_tools:
            available = ", ".join(t.name for t in external_tools)
            click.echo(f"❌ Tool '{tool_name}' not found.")
            click.echo(f"   Available tools: {available}")
            sys.exit(1)
        external_tools = matching_tools

    # Determine working directory
    root_path = code_quality_config.get("root_path", ".")
    working_dir = Path(root_path).resolve()

    # Initialize components
    work_queue = WorkQueue(
        sugar_config.get("storage", {}).get("database", ".sugar/sugar.db")
    )

    claude_config = sugar_config.get("claude", {})
    # Add database path for TaskTypeManager
    claude_config["database_path"] = sugar_config.get("storage", {}).get(
        "database", ".sugar/sugar.db"
    )

    # Force dry_run in Claude wrapper if --dry-run flag is set
    if dry_run:
        claude_config["dry_run"] = True

    claude_wrapper = ClaudeWrapper(claude_config)
    prompt_manager = PromptTemplateManager(discovery_config.get("external_tools", {}))

    # Display header
    mode_str = " (DRY-RUN)" if dry_run else ""
    click.echo(f"\n🔍 Running external tool discovery{mode_str}...\n")

    # Track results
    total_tasks = 0
    tool_summaries = []

    async def run_discovery():
        nonlocal total_tasks

        await work_queue.initialize()

        for tool_config in external_tools:
            click.echo(f"📦 {tool_config.name} ({tool_config.command})")

            # Execute tool discovery
            summary = await _execute_tool_discovery(
                tool_config=tool_config,
                working_dir=working_dir,
                timeout=timeout,
                dry_run=dry_run,
                work_queue=work_queue,
                claude_wrapper=claude_wrapper,
                prompt_template_manager=prompt_manager,
            )

            tool_summaries.append(summary)

            # Display result
            if summary.get("success"):
                exit_info = f"exit code {summary.get('exit_code', 'N/A')}"
                lines_info = f"{summary.get('stdout_lines', 0)} lines output"
                duration_info = f"{summary.get('duration', 0):.1f}s"
                click.echo(
                    f"   ✅ Completed ({exit_info}, {lines_info}, {duration_info})"
                )

                if not dry_run:
                    tasks = summary.get("tasks_created", 0)
                    if tasks > 0:
                        click.echo(f"   → Passing to Claude Code for interpretation...")
                        click.echo(f"   → Generated {tasks} tasks")
                        total_tasks += tasks
                    else:
                        click.echo(f"   → No actionable issues found")
            else:
                error = summary.get("error", "Unknown error")
                click.echo(f"   ❌ Failed: {error}")

            click.echo()

    # Run the async discovery
    try:
        asyncio.run(run_discovery())
    except KeyboardInterrupt:
        click.echo("\n\n⚠️ Discovery interrupted by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n❌ Discovery failed: {e}")
        logger.exception("Discovery failed")
        sys.exit(1)

    # Display summary
    successful_tools = sum(1 for s in tool_summaries if s.get("success"))
    failed_tools = len(tool_summaries) - successful_tools

    if dry_run:
        click.echo(f"✅ Discovery dry-run complete")
        click.echo(
            f"   {successful_tools} tools executed successfully, {failed_tools} failed"
        )
        click.echo(f"   Run without --dry-run to create tasks")
    else:
        click.echo(f"✅ Discovery complete: {total_tasks} new tasks created")
        if total_tasks > 0:
            click.echo(f"   Run 'sugar list' to view")
