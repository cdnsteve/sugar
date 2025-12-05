"""
Claude Code CLI Wrapper - Execute development tasks with Claude and context persistence
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union
import tempfile
import os

from .structured_request import (
    StructuredRequest,
    StructuredResponse,
    RequestBuilder,
    ExecutionMode,
    AgentType,
    DynamicAgentType,
)
from ..storage.task_type_manager import TaskTypeManager

logger = logging.getLogger(__name__)


class ClaudeWrapper:
    """Wrapper for Claude Code CLI execution with context persistence using --continue"""

    def __init__(self, config: dict):
        self.config = config
        self.command = config["command"]
        self.timeout = config["timeout"]
        self.context_file = config["context_file"]

        # New context persistence settings
        self.use_continuous = config.get("use_continuous", True)
        self.context_strategy = config.get(
            "context_strategy", "project"
        )  # project, task_type, session
        self.max_context_age_hours = config.get("max_context_age_hours", 24)
        self.context_sharing = config.get(
            "context_sharing", "same_type"
        )  # same_type, all, none

        # Structured request settings
        self.use_structured_requests = config.get("use_structured_requests", True)
        self.structured_input_file = config.get(
            "structured_input_file", ".sugar/claude_input.json"
        )

        # Agent configuration
        self.enable_agents = config.get("enable_agents", True)
        self.agent_fallback = config.get("agent_fallback", True)
        # Keep fallback mapping for backwards compatibility
        self.agent_selection_fallback = {
            "bug_fix": "tech-lead",
            "feature": "general-purpose",
            "refactor": "code-reviewer",
            "test": "general-purpose",
            "documentation": "general-purpose",
        }
        self.agent_selection = config.get(
            "agent_selection", self.agent_selection_fallback
        )

        # Initialize TaskTypeManager if database path is available
        self.db_path = config.get("database_path")
        self.task_type_manager = TaskTypeManager(self.db_path) if self.db_path else None

        # Dynamic agent discovery
        self.available_agents = config.get(
            "available_agents", []
        )  # User can specify available agents
        self.auto_discover_agents = config.get(
            "auto_discover_agents", False
        )  # Future: auto-discover from Claude CLI

        # Track session state
        self.session_state_file = self.context_file.replace(".json", "_session.json")
        self.dry_run = config.get("dry_run", True)

        logger.debug(f"🤖 Claude wrapper initialized: {self.command}")
        logger.debug(f"🧪 Dry run mode: {self.dry_run}")
        logger.debug(f"🔄 Context persistence: {self.use_continuous}")
        logger.debug(f"📋 Context strategy: {self.context_strategy}")
        logger.debug(f"🏗️ Structured requests: {self.use_structured_requests}")

    async def execute_work(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a work item using Claude Code CLI with context persistence"""

        if self.dry_run:
            return await self._simulate_execution(work_item)

        try:
            # Choose execution path based on configuration
            if self.use_structured_requests:
                return await self._execute_structured_work(work_item)
            else:
                return await self._execute_legacy_work(work_item)

        except Exception as e:
            logger.error(f"Claude execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "work_item_id": work_item["id"],
            }

    def _should_continue_session(self, work_item: Dict[str, Any]) -> bool:
        """Determine if we should continue the previous Claude session"""

        if not self.use_continuous:
            return False

        # Load session state
        session_state = self._load_session_state()
        if not session_state:
            logger.debug("🆕 Starting fresh session - no previous state")
            return False

        # Check if context is too old
        if self._is_context_too_old(session_state):
            logger.debug("⏰ Starting fresh session - context too old")
            return False

        # Check strategy-specific continuation logic
        if self.context_strategy == "project":
            # Always continue within same project (default behavior)
            should_continue = True
        elif self.context_strategy == "task_type":
            # Continue only for same task type
            should_continue = work_item["type"] == session_state.get("last_task_type")
        elif self.context_strategy == "session":
            # Continue only within same logical session (related tasks)
            should_continue = self._are_tasks_related(work_item, session_state)
        else:
            should_continue = True

        if should_continue:
            logger.debug(
                f"🔄 Continuing previous session (strategy: {self.context_strategy})"
            )
        else:
            logger.debug(
                f"🆕 Starting fresh session (strategy: {self.context_strategy})"
            )

        return should_continue

    def _load_session_state(self) -> Dict[str, Any]:
        """Load session state from file"""
        try:
            if os.path.exists(self.session_state_file):
                with open(self.session_state_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load session state: {e}")
        return {}

    def _is_context_too_old(self, session_state: Dict[str, Any]) -> bool:
        """Check if the last session is too old"""
        try:
            last_time = datetime.fromisoformat(
                session_state.get("last_execution_time", "")
            )
            age_hours = (datetime.utcnow() - last_time).total_seconds() / 3600
            return age_hours > self.max_context_age_hours
        except:
            return True

    def _are_tasks_related(
        self, work_item: Dict[str, Any], session_state: Dict[str, Any]
    ) -> bool:
        """Determine if current task is related to previous tasks"""
        # Check if tasks are in same component or area
        current_desc = work_item.get("description", "").lower()
        last_desc = session_state.get("last_task_description", "").lower()

        # Simple relatedness check based on keywords
        common_keywords = [
            "auth",
            "user",
            "api",
            "database",
            "test",
            "dashboard",
            "payment",
        ]

        for keyword in common_keywords:
            if keyword in current_desc and keyword in last_desc:
                return True

        # Check if same source file mentioned
        current_file = work_item.get("source_file", "")
        last_file = session_state.get("last_source_file", "")
        if current_file and last_file and current_file == last_file:
            return True

        return False

    def _update_session_state(self, work_item: Dict[str, Any], simulated: bool = False):
        """Update session state after execution"""
        session_state = {
            "last_execution_time": datetime.utcnow().isoformat(),
            "last_task_type": work_item["type"],
            "last_task_title": work_item["title"],
            "last_task_description": work_item.get("description", ""),
            "last_source_file": work_item.get("source_file", ""),
            "session_started": True,
            "simulated": simulated,
            "context_strategy": self.context_strategy,
            "execution_count": self._get_execution_count() + 1,
        }

        try:
            with open(self.session_state_file, "w") as f:
                json.dump(session_state, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save session state: {e}")

    def _get_execution_count(self) -> int:
        """Get number of executions in current session"""
        session_state = self._load_session_state()
        return session_state.get("execution_count", 0)

    def _prepare_context(
        self, work_item: Dict[str, Any], continue_session: bool = False
    ) -> Dict[str, Any]:
        """Prepare execution context for Claude with continuation awareness"""
        context = {
            "work_item": work_item,
            "timestamp": datetime.utcnow().isoformat(),
            "ccal_session": True,
            "safety_mode": True,
            "continue_session": continue_session,
            "execution_count": self._get_execution_count() + 1,
        }

        # Load existing context if available
        if os.path.exists(self.context_file):
            try:
                with open(self.context_file, "r") as f:
                    existing_context = json.load(f)
                    context.update(existing_context)
            except Exception as e:
                logger.warning(f"Could not load existing context: {e}")

        # Save updated context
        try:
            with open(self.context_file, "w") as f:
                json.dump(context, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save context: {e}")

        return context

    def _create_task_prompt(
        self,
        work_item: Dict[str, Any],
        context: Dict[str, Any],
        continue_session: bool = False,
    ) -> str:
        """Create a structured prompt for Claude with embedded task details"""

        if continue_session:
            # Continuation prompt with embedded task details
            prompt = f"""Continuing our development work on this project.

## Next Task: {work_item['title']}
- **Type**: {work_item['type']} 
- **Priority**: {work_item['priority']}/5
- **Source**: {work_item.get('source', 'manual')}

## Task Description
{work_item['description']}

## Task Context
{json.dumps(work_item.get('context', {}), indent=2)}

This is task #{context['execution_count']} in our current development session. Building on our previous work in this project, please:

1. **Analyze the task** in the context of what we've already accomplished  
2. **Implement the solution** following the patterns and practices we've established
3. **Test and verify** the implementation
4. **Document changes** with clear commit messages

---
*Continuing autonomous development session with Sugar*
"""
        else:
            # Fresh session prompt with embedded task details
            prompt = f"""# Sugar Autonomous Development Task

Hello! I'm working with Sugar, an autonomous development system. I have a specific task to implement.

## Task Information
- **Type**: {work_item['type']}
- **Priority**: {work_item['priority']}/5
- **Title**: {work_item['title']}
- **ID**: {work_item['id']}
- **Source**: {work_item.get('source', 'manual')}

## Task Description
{work_item['description']}

## Task Context
{json.dumps(work_item.get('context', {}), indent=2)}

## Instructions
Please implement this task by:

1. **Analyze the task** and understand the requirements
2. **Implement the solution** following best practices
3. **Test the implementation** if applicable  
4. **Document any important changes** in comments or commit messages
5. **Report back** with a summary of what was accomplished

## Important Notes
- This is an autonomous development session powered by Sugar
- Focus on the specific task requirements provided above
- Follow existing code patterns and conventions in this project
- Make actual file changes to complete the task

---
*This task is being executed by Sugar - an autonomous development system.*
"""

        return prompt.strip()

    async def _execute_claude_cli(
        self, prompt: str, context: Dict[str, Any], continue_session: bool = False
    ) -> Dict[str, Any]:
        """Execute the Claude CLI command with the given prompt and optional continuation"""
        start_time = datetime.utcnow()

        if continue_session:
            # Use --continue flag to maintain conversation context with --print for non-interactive mode
            logger.debug(f"🔄 Executing Claude CLI with --continue")
            cmd = [
                self.command,
                "--continue",
                "--print",
                "--permission-mode",
                "bypassPermissions",
            ]
        else:
            # Fresh session with --print for non-interactive mode
            logger.debug(f"🆕 Executing Claude CLI with fresh session")
            cmd = [self.command, "--print", "--permission-mode", "bypassPermissions"]

        # Log more details about execution
        logger.debug(f"🤖 Executing Claude CLI: {' '.join(cmd)}")
        logger.debug(f"📁 Working directory: {os.getcwd()}")
        logger.debug(f"📄 Prompt length: {len(prompt)} characters")
        logger.debug(f"⏱️ Timeout set to: {self.timeout}s")
        if continue_session:
            logger.debug(f"🔄 Using continuation mode - prompt will be sent via stdin")
        else:
            logger.debug(f"🆕 Fresh session - prompt will be sent via stdin")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd(),
            )

            logger.debug(f"🚀 Claude process started (PID: {process.pid})")

            # Send prompt via stdin and wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=prompt.encode("utf-8")),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                logger.error(f"⏰ Claude CLI execution timed out after {self.timeout}s")
                process.kill()
                raise Exception(f"Claude CLI execution timed out after {self.timeout}s")

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Detailed logging of results
            logger.debug(f"✅ Claude process completed in {execution_time:.2f}s")
            logger.debug(f"📤 Return code: {process.returncode}")

            stdout_text = stdout.decode("utf-8")
            stderr_text = stderr.decode("utf-8")

            logger.debug(f"📤 Stdout length: {len(stdout_text)} characters")
            logger.debug(f"📤 Stderr length: {len(stderr_text)} characters")

            # Log first few lines of output for debugging
            if stdout_text:
                stdout_lines = stdout_text.split("\n")
                stdout_preview = "\n".join(stdout_lines[:5])
                logger.debug(f"📤 Stdout preview:\n{stdout_preview}")
                if len(stdout_lines) > 5:
                    total_lines = len(stdout_lines)
                    logger.debug(f"📤 ... (truncated, {total_lines} total lines)")

            if stderr_text:
                stderr_lines = stderr_text.split("\n")
                stderr_preview = "\n".join(stderr_lines[:3])
                logger.debug(f"⚠️ Stderr preview:\n{stderr_preview}")
                if len(stderr_lines) > 3:
                    total_lines = len(stderr_lines)
                    logger.debug(f"⚠️ ... (truncated, {total_lines} total lines)")

            # Process results
            if process.returncode == 0:
                logger.debug(f"✅ Claude execution successful")
                return {
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "returncode": process.returncode,
                    "execution_time": execution_time,
                    "success": True,
                    "continued_session": continue_session,
                    "command": " ".join(cmd),
                    "prompt_length": len(prompt),
                    "working_directory": os.getcwd(),
                }
            else:
                logger.error(
                    f"❌ Claude CLI failed with return code {process.returncode}"
                )
                logger.error(f"❌ Error output: {stderr_text}")
                raise Exception(
                    f"Claude CLI failed with return code {process.returncode}: {stderr_text}"
                )

        except Exception as e:
            logger.error(f"❌ Claude CLI execution error: {e}")
            raise

    async def _simulate_execution(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate Claude execution for testing (dry run mode) with continuation support"""
        should_continue = self._should_continue_session(work_item)

        if should_continue:
            logger.debug(
                f"🧪 SIMULATION: Continuing session for {work_item['type']} - {work_item['title']}"
            )
        else:
            logger.debug(
                f"🧪 SIMULATION: Fresh session for {work_item['type']} - {work_item['title']}"
            )

        # Update session state even in dry run for testing continuity logic
        self._update_session_state(work_item, simulated=True)

        # Simulate some execution time
        execution_time = 2.0 + (hash(work_item["id"]) % 10)  # 2-12 seconds
        await asyncio.sleep(2.0)  # Actually wait 2 seconds for realism

        # Generate realistic simulation results
        simulation_result = {
            "success": True,
            "simulated": True,
            "result": {
                "stdout": f"SIMULATION: Successfully completed {work_item['type']} task",
                "actions_taken": [
                    "Analyzed task requirements",
                    "Implemented solution following best practices",
                    "Added appropriate error handling",
                    "Updated documentation",
                ],
                "files_modified": self._generate_simulated_files(work_item),
                "summary": f"Successfully completed {work_item['title']} - this was a simulation",
                "execution_time": execution_time,
                "continued_session": should_continue,
            },
            "timestamp": datetime.utcnow().isoformat(),
            "work_item_id": work_item["id"],
            "used_continue": should_continue,
            "context_strategy": self.context_strategy,
        }

        logger.info(
            f"✅ SIMULATION: Task completed in {execution_time:.1f}s (continue: {should_continue})"
        )
        return simulation_result

    def _generate_simulated_files(self, work_item: Dict[str, Any]) -> list:
        """Generate realistic file names for simulation"""
        task_type = work_item["type"].lower()

        file_patterns = {
            "bug_fix": ["src/components/buggy_component.py", "tests/test_fix.py"],
            "feature": ["src/features/new_feature.py", "src/api/feature_endpoint.py"],
            "test": [
                "tests/test_new_functionality.py",
                "tests/integration/test_api.py",
            ],
            "refactor": ["src/legacy_code.py", "src/improved_code.py"],
            "documentation": ["README.md", "docs/api_documentation.md"],
        }

        return file_patterns.get(task_type, ["src/generic_file.py"])

    def _parse_claude_output(self, output: str) -> dict:
        """Parse Claude's output to extract meaningful information for GitHub comments"""
        if not output:
            return {
                "response": "",
                "files_changed": [],
                "summary": "",
                "actions_taken": [],
            }

        lines = output.split("\n")

        # Extract Claude's actual response (usually after prompts)
        claude_response_lines = []
        files_changed = []
        actions_taken = []
        in_claude_response = False

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Detect start of Claude's actual response
            if (
                line.startswith("I'll")
                or line.startswith("Let me")
                or line.startswith("I'm")
                or line.startswith("I need to")
                or line.startswith("Looking at")
                or line.startswith("I can see")
                or line.startswith("I have successfully")
                or line.startswith("I successfully")
                or line.startswith("I've successfully")
                or line.startswith("I implemented")
            ):
                in_claude_response = True
                claude_response_lines.append(line)
                # Also capture detailed implementation statements as actions
                if any(
                    phrase in line.lower()
                    for phrase in [
                        "i have successfully",
                        "i successfully",
                        "i've successfully",
                        "i implemented",
                        "i created",
                        "i added",
                        "i updated",
                    ]
                ):
                    actions_taken.append(line)
                continue

            # Capture file operations
            if (
                "wrote to" in line.lower()
                or "created" in line.lower()
                or "updated" in line.lower()
                or "modified" in line.lower()
            ):
                if ".py" in line or ".js" in line or ".md" in line or ".txt" in line:
                    # Extract filename
                    words = line.split()
                    for word in words:
                        if "." in word and any(
                            ext in word
                            for ext in [".py", ".js", ".md", ".txt", ".json", ".yaml"]
                        ):
                            files_changed.append(word.strip(".,"))
                            break
                actions_taken.append(line)

            # Capture success indicators and actions
            if (
                line.startswith("✅")
                or line.startswith("✓")
                or "successfully" in line.lower()
                or "completed" in line.lower()
                or "added" in line.lower()
                or "fixed" in line.lower()
            ):
                actions_taken.append(line)

            # Capture analysis and findings
            if any(
                phrase in line.lower()
                for phrase in [
                    "already exists",
                    "already includes",
                    "found that",
                    "verified that",
                    "analysis shows",
                    "readme contains",
                    "file contains",
                    "properly listed",
                    "no changes needed",
                    "requirement satisfied",
                    "confirmed that",
                    "includes a comprehensive",
                    "with:",
                    "lines",
                    "section",
                    "steven leggett",
                ]
            ):
                actions_taken.append(line)

            # Capture detailed explanations and multi-line descriptions
            if any(
                phrase in line.lower()
                for phrase in [
                    "here's what",
                    "accomplished:",
                    "the readme.md file",
                    "author section",
                    "comprehensive",
                    "resolved",
                    "requesting to",
                    "ensure you add",
                    "changes made:",
                    "i have successfully",
                    "the changes include",
                    "i successfully",
                    "i've successfully",
                    "implementation includes",
                    "the solution",
                    "this implementation",
                    "the feature",
                    "i added",
                    "i created",
                    "i implemented",
                    "i updated",
                    "i modified",
                ]
            ):
                actions_taken.append(line)

            # Include in Claude response if we're in that section
            if in_claude_response:
                claude_response_lines.append(line)

        # Generate summary from actions
        summary = ""
        if actions_taken:
            # Take the most descriptive action
            summary = actions_taken[0] if actions_taken else ""
            # Clean up summary
            summary = summary.lstrip("✅✓ ").strip()

        # Sort actions by length to prioritize detailed explanations
        actions_taken.sort(key=len, reverse=True)

        return {
            "response": "\n".join(
                claude_response_lines[-20:]
            ),  # Last 20 lines of Claude's response
            "files_changed": list(set(files_changed)),  # Remove duplicates
            "summary": summary,
            "actions_taken": actions_taken[:8],  # Top 8 actions, sorted by detail level
        }

    async def validate_claude_cli(self) -> bool:
        """Validate that Claude CLI is available and working"""
        try:
            process = await asyncio.create_subprocess_exec(
                self.command,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(
                    f"✅ Claude CLI validated: {stdout.decode('utf-8').strip()}"
                )
                return True
            else:
                logger.error(
                    f"❌ Claude CLI validation failed: {stderr.decode('utf-8')}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Claude CLI not found: {e}")
            return False

    async def _execute_structured_work(
        self, work_item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute work using structured request format with agent selection"""
        try:
            # Select agent based on work item characteristics
            agent_type = await self._select_agent_for_work(work_item)
            execution_mode = ExecutionMode.AGENT if agent_type else ExecutionMode.BASIC

            # Create structured request
            if agent_type:
                structured_request = RequestBuilder.create_agent_request(
                    work_item, agent_type
                )
                logger.info(
                    f"🤖 Selected agent: {agent_type.value} for {work_item['type']} task"
                )
            else:
                structured_request = RequestBuilder.create_basic_request(work_item)
                logger.info(f"📝 Using basic Claude for {work_item['type']} task")

            # Save structured request to file for Claude input
            request_json = structured_request.to_json()
            os.makedirs(os.path.dirname(self.structured_input_file), exist_ok=True)
            with open(self.structured_input_file, "w") as f:
                f.write(request_json)

            # Create task prompt for structured execution
            task_prompt = self._create_structured_task_prompt(structured_request)

            # Execute Claude CLI
            result = await self._execute_claude_cli_structured(
                task_prompt, structured_request
            )

            # Parse response
            if result.get("success", False):
                structured_response = StructuredResponse.from_claude_output(
                    stdout=result.get("stdout", ""),
                    stderr=result.get("stderr", ""),
                    return_code=result.get("returncode", 0),
                    execution_time=result.get("execution_time", 0),
                    agent_used=agent_type.value if agent_type else None,
                )

                return {
                    "success": True,
                    "result": result,
                    "structured_response": structured_response.to_dict(),
                    "timestamp": datetime.utcnow().isoformat(),
                    "work_item_id": work_item["id"],
                    "execution_time": result.get("execution_time", 0),
                    "agent_used": agent_type.value if agent_type else None,
                    "execution_mode": execution_mode.value,
                    "output": result.get("stdout", ""),
                    "claude_response": structured_response.summary,
                    "files_changed": structured_response.files_modified,
                    "summary": structured_response.summary,
                    "actions_taken": structured_response.actions_taken,
                }
            else:
                # Agent execution failed - try fallback if enabled
                if agent_type and self.agent_fallback:
                    logger.warning(
                        f"🔄 Agent {agent_type.value} failed, falling back to basic Claude"
                    )
                    return await self._execute_legacy_work(work_item)
                else:
                    raise Exception(
                        f"Structured execution failed: {result.get('stderr', 'Unknown error')}"
                    )

        except Exception as e:
            logger.error(f"Structured execution error: {e}")

            # Try fallback if enabled
            if self.agent_fallback:
                logger.info("🔄 Falling back to legacy execution")
                return await self._execute_legacy_work(work_item)
            else:
                raise

    async def _execute_legacy_work(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute work using legacy prompt format"""
        # Determine if we should continue previous session
        should_continue = self._should_continue_session(work_item)

        # Prepare the execution context
        context = self._prepare_context(work_item, continue_session=should_continue)

        # Create task prompt
        task_prompt = self._create_task_prompt(
            work_item, context, continue_session=should_continue
        )

        # Execute Claude Code CLI with or without --continue
        result = await self._execute_claude_cli(
            task_prompt, context, continue_session=should_continue
        )

        # Update session state for next execution
        self._update_session_state(work_item)

        # Parse Claude's output for better GitHub comments
        parsed_output = self._parse_claude_output(result.get("stdout", ""))

        return {
            "success": True,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
            "work_item_id": work_item["id"],
            "execution_time": result.get("execution_time", 0),
            "used_continue": should_continue,
            "context_strategy": self.context_strategy,
            "execution_mode": "legacy",
            "output": result.get("stdout", ""),
            "claude_response": parsed_output.get("response", ""),
            "files_changed": parsed_output.get("files_changed", []),
            "summary": parsed_output.get("summary", ""),
            "actions_taken": parsed_output.get("actions_taken", []),
        }

    async def _select_agent_for_work(
        self, work_item: Dict[str, Any]
    ) -> Optional[Union[AgentType, DynamicAgentType]]:
        """Select the best agent for a work item based on task characteristics"""
        if not self.enable_agents:
            return None

        task_type = work_item.get("type", "").lower()
        title = work_item.get("title", "").lower()
        description = work_item.get("description", "").lower()

        # First check TaskTypeManager for agent configuration
        selected_agent_name = None
        if self.task_type_manager:
            try:
                selected_agent_name = await self.task_type_manager.get_agent_for_type(
                    task_type
                )
            except Exception as e:
                logger.debug(f"Could not get agent from TaskTypeManager: {e}")

        # Fallback to static configuration
        if not selected_agent_name:
            selected_agent_name = self.agent_selection.get(task_type)

        # If no configured mapping, use intelligent keyword-based selection
        if not selected_agent_name:
            # Social media content - use social-media-growth-strategist (check first for specificity)
            if any(
                keyword in title or keyword in description
                for keyword in [
                    "social media",
                    "post",
                    "content strategy",
                    "engagement",
                    "followers",
                    "twitter",
                    "linkedin",
                    "instagram",
                    "marketing",
                    "growth",
                    "social",
                ]
            ):
                selected_agent_name = "social-media-growth-strategist"

            # Code review indicators - use code-reviewer
            elif any(
                keyword in title or keyword in description
                for keyword in [
                    "review",
                    "refactor",
                    "cleanup",
                    "optimize",
                    "improve code quality",
                    "code smell",
                    "technical debt",
                    "style",
                    "formatting",
                ]
            ):
                selected_agent_name = "code-reviewer"

            # Technical architecture/strategy - use tech-lead
            elif (
                any(
                    keyword in title or keyword in description
                    for keyword in [
                        "architecture",
                        "design",
                        "strategy",
                        "approach",
                        "plan",
                        "complex",
                        "system design",
                        "integration",
                        "performance",
                        "scalability",
                        "security",
                        "critical bug",
                    ]
                )
                or work_item.get("priority", 3) >= 4
            ):
                selected_agent_name = "tech-lead"

            # Configuration/setup tasks - use specific setup agents
            elif any(
                keyword in title or keyword in description
                for keyword in ["statusline", "status line", "claude code status"]
            ):
                selected_agent_name = "statusline-setup"

            elif any(
                keyword in title or keyword in description
                for keyword in ["output style", "styling", "color scheme", "theme"]
            ):
                selected_agent_name = "output-style-setup"

            # Final fallback
            else:
                selected_agent_name = "general-purpose"

        # Validate agent availability and return appropriate type
        return self._get_agent_type(selected_agent_name)

    def _get_agent_type(
        self, agent_name: str
    ) -> Optional[Union[AgentType, DynamicAgentType]]:
        """Get agent type, supporting both built-in and custom agents"""
        if not agent_name:
            return AgentType.GENERAL_PURPOSE

        # Check if user has specified available agents
        if self.available_agents:
            if agent_name in self.available_agents:
                return AgentType.from_string(agent_name)
            else:
                logger.debug(
                    f"Agent '{agent_name}' not in available_agents list, falling back to general-purpose"
                )
                # Try to find a fallback agent in the available list
                fallback_options = ["general-purpose", "tech-lead", "code-reviewer"]
                for fallback in fallback_options:
                    if fallback in self.available_agents:
                        return AgentType.from_string(fallback)

                # If no fallback found, use first available agent
                if self.available_agents:
                    return AgentType.from_string(self.available_agents[0])

                return AgentType.GENERAL_PURPOSE

        # If no available agents specified, allow any agent (dynamic discovery)
        return AgentType.from_string(agent_name)

    def _create_structured_task_prompt(
        self, structured_request: StructuredRequest
    ) -> str:
        """Create a task prompt for structured request execution"""
        agent_info = ""
        if structured_request.agent_type:
            agent_info = f"\n**Agent Mode**: {structured_request.agent_type.value}\n"

        prompt = f"""# Sugar Structured Development Task
{agent_info}
I'm working with Sugar's structured request system. Here's the task information in JSON format:

```json
{structured_request.to_json()}
```

## Instructions
Please process this structured request by:

1. **Understanding the task** from the JSON context above
2. **Implementing the solution** according to the task type and requirements
3. **Following the execution mode** specified ({structured_request.execution_mode.value})
4. **Using appropriate tools and patterns** for this type of work
5. **Providing structured feedback** if possible

## Important Notes
- This is part of Sugar's autonomous development system
- The task details are in the JSON structure above
- Focus on the specific requirements and context provided
- Make actual changes to complete the task effectively

---
*Structured task execution via Sugar autonomous development system*
"""
        return prompt.strip()

    async def _execute_claude_cli_structured(
        self, prompt: str, structured_request: StructuredRequest
    ) -> Dict[str, Any]:
        """Execute Claude CLI with structured request support"""
        start_time = datetime.utcnow()

        # Determine if we should use agent mode
        if (
            structured_request.agent_type
            and structured_request.execution_mode == ExecutionMode.AGENT
        ):
            logger.debug(
                f"🤖 Executing with agent: {structured_request.agent_type.value}"
            )
            # Note: Agent mode would be implemented when Claude CLI supports it
            # For now, we execute normally but track that an agent was intended
            cmd = [self.command, "--print", "--permission-mode", "bypassPermissions"]
        else:
            logger.debug(f"📝 Executing structured request in basic mode")
            cmd = [self.command, "--print", "--permission-mode", "bypassPermissions"]

        # Log execution details
        logger.debug(f"🚀 Executing structured Claude CLI: {' '.join(cmd)}")
        logger.debug(f"📋 Request mode: {structured_request.execution_mode.value}")
        if structured_request.agent_type:
            logger.debug(f"🎯 Target agent: {structured_request.agent_type.value}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd(),
            )

            # Send prompt and wait for completion
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=prompt.encode("utf-8")),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"⏰ Structured Claude execution timed out after {self.timeout}s"
                )
                process.kill()
                raise Exception(f"Claude CLI execution timed out after {self.timeout}s")

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            stdout_text = stdout.decode("utf-8")
            stderr_text = stderr.decode("utf-8")

            logger.debug(f"✅ Structured execution completed in {execution_time:.2f}s")

            if process.returncode == 0:
                return {
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "returncode": process.returncode,
                    "execution_time": execution_time,
                    "success": True,
                    "structured_mode": True,
                    "agent_requested": (
                        structured_request.agent_type.value
                        if structured_request.agent_type
                        else None
                    ),
                    "command": " ".join(cmd),
                }
            else:
                logger.error(f"❌ Structured Claude execution failed: {stderr_text}")
                return {
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "returncode": process.returncode,
                    "execution_time": execution_time,
                    "success": False,
                    "error": stderr_text,
                }

        except Exception as e:
            logger.error(f"❌ Structured Claude CLI error: {e}")
            raise
