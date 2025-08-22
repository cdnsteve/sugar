"""
Claude Code CLI Wrapper - Execute development tasks with Claude and context persistence
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile
import os

logger = logging.getLogger(__name__)

class ClaudeWrapper:
    """Wrapper for Claude Code CLI execution with context persistence using --continue"""
    
    def __init__(self, config: dict):
        self.config = config
        self.command = config['command']
        self.timeout = config['timeout']
        self.context_file = config['context_file']
        
        # New context persistence settings
        self.use_continuous = config.get('use_continuous', True)
        self.context_strategy = config.get('context_strategy', 'project')  # project, task_type, session
        self.max_context_age_hours = config.get('max_context_age_hours', 24)
        self.context_sharing = config.get('context_sharing', 'same_type')  # same_type, all, none
        
        # Track session state
        self.session_state_file = self.context_file.replace('.json', '_session.json')
        self.dry_run = config.get('dry_run', True)
        
        logger.debug(f"🤖 Claude wrapper initialized: {self.command}")
        logger.debug(f"🧪 Dry run mode: {self.dry_run}")
        logger.debug(f"🔄 Context persistence: {self.use_continuous}")
        logger.debug(f"📋 Context strategy: {self.context_strategy}")
    
    async def execute_work(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a work item using Claude Code CLI with context persistence"""
        
        if self.dry_run:
            return await self._simulate_execution(work_item)
        
        try:
            # Determine if we should continue previous session
            should_continue = self._should_continue_session(work_item)
            
            # Prepare the execution context
            context = self._prepare_context(work_item, continue_session=should_continue)
            
            # Create task prompt
            task_prompt = self._create_task_prompt(work_item, context, continue_session=should_continue)
            
            # Execute Claude Code CLI with or without --continue
            result = await self._execute_claude_cli(task_prompt, context, continue_session=should_continue)
            
            # Update session state for next execution
            self._update_session_state(work_item)

            # Parse Claude's output for better GitHub comments
            parsed_output = self._parse_claude_output(result.get('stdout', ''))
            
            return {
                "success": True,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
                "work_item_id": work_item['id'],
                "execution_time": result.get('execution_time', 0),
                "used_continue": should_continue,
                "context_strategy": self.context_strategy,
                "output": result.get('stdout', ''),
                "claude_response": parsed_output.get('response', ''),
                "files_changed": parsed_output.get('files_changed', []),
                "summary": parsed_output.get('summary', ''),
                "actions_taken": parsed_output.get('actions_taken', [])
            }
            
        except Exception as e:
            logger.error(f"Claude execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "work_item_id": work_item['id']
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
        if self.context_strategy == 'project':
            # Always continue within same project (default behavior)
            should_continue = True
        elif self.context_strategy == 'task_type':
            # Continue only for same task type
            should_continue = (work_item['type'] == session_state.get('last_task_type'))
        elif self.context_strategy == 'session':
            # Continue only within same logical session (related tasks)
            should_continue = self._are_tasks_related(work_item, session_state)
        else:
            should_continue = True
        
        if should_continue:
            logger.debug(f"🔄 Continuing previous session (strategy: {self.context_strategy})")
        else:
            logger.debug(f"🆕 Starting fresh session (strategy: {self.context_strategy})")
            
        return should_continue
    
    def _load_session_state(self) -> Dict[str, Any]:
        """Load session state from file"""
        try:
            if os.path.exists(self.session_state_file):
                with open(self.session_state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load session state: {e}")
        return {}
    
    def _is_context_too_old(self, session_state: Dict[str, Any]) -> bool:
        """Check if the last session is too old"""
        try:
            last_time = datetime.fromisoformat(session_state.get('last_execution_time', ''))
            age_hours = (datetime.utcnow() - last_time).total_seconds() / 3600
            return age_hours > self.max_context_age_hours
        except:
            return True
    
    def _are_tasks_related(self, work_item: Dict[str, Any], session_state: Dict[str, Any]) -> bool:
        """Determine if current task is related to previous tasks"""
        # Check if tasks are in same component or area
        current_desc = work_item.get('description', '').lower()
        last_desc = session_state.get('last_task_description', '').lower()
        
        # Simple relatedness check based on keywords
        common_keywords = ['auth', 'user', 'api', 'database', 'test', 'dashboard', 'payment']
        
        for keyword in common_keywords:
            if keyword in current_desc and keyword in last_desc:
                return True
        
        # Check if same source file mentioned
        current_file = work_item.get('source_file', '')
        last_file = session_state.get('last_source_file', '')
        if current_file and last_file and current_file == last_file:
            return True
            
        return False
    
    def _update_session_state(self, work_item: Dict[str, Any], simulated: bool = False):
        """Update session state after execution"""
        session_state = {
            'last_execution_time': datetime.utcnow().isoformat(),
            'last_task_type': work_item['type'],
            'last_task_title': work_item['title'],
            'last_task_description': work_item.get('description', ''),
            'last_source_file': work_item.get('source_file', ''),
            'session_started': True,
            'simulated': simulated,
            'context_strategy': self.context_strategy,
            'execution_count': self._get_execution_count() + 1
        }
        
        try:
            with open(self.session_state_file, 'w') as f:
                json.dump(session_state, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save session state: {e}")
    
    def _get_execution_count(self) -> int:
        """Get number of executions in current session"""
        session_state = self._load_session_state()
        return session_state.get('execution_count', 0)

    def _prepare_context(self, work_item: Dict[str, Any], continue_session: bool = False) -> Dict[str, Any]:
        """Prepare execution context for Claude with continuation awareness"""
        context = {
            "work_item": work_item,
            "timestamp": datetime.utcnow().isoformat(),
            "ccal_session": True,
            "safety_mode": True,
            "continue_session": continue_session,
            "execution_count": self._get_execution_count() + 1
        }
        
        # Load existing context if available
        if os.path.exists(self.context_file):
            try:
                with open(self.context_file, 'r') as f:
                    existing_context = json.load(f)
                    context.update(existing_context)
            except Exception as e:
                logger.warning(f"Could not load existing context: {e}")
        
        # Save updated context
        try:
            with open(self.context_file, 'w') as f:
                json.dump(context, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save context: {e}")
        
        return context
    
    def _create_task_prompt(self, work_item: Dict[str, Any], context: Dict[str, Any], continue_session: bool = False) -> str:
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
    
    async def _execute_claude_cli(self, prompt: str, context: Dict[str, Any], continue_session: bool = False) -> Dict[str, Any]:
        """Execute the Claude CLI command with the given prompt and optional continuation"""
        start_time = datetime.utcnow()
        
        if continue_session:
            # Use --continue flag to maintain conversation context with --print for non-interactive mode
            logger.debug(f"🔄 Executing Claude CLI with --continue")
            cmd = [self.command, '--continue', '--print', '--permission-mode', 'bypassPermissions']
        else:
            # Fresh session with --print for non-interactive mode
            logger.debug(f"🆕 Executing Claude CLI with fresh session")
            cmd = [self.command, '--print', '--permission-mode', 'bypassPermissions']
        
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
                cwd=os.getcwd()
            )
            
            logger.debug(f"🚀 Claude process started (PID: {process.pid})")
            
            # Send prompt via stdin and wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=prompt.encode('utf-8')),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"⏰ Claude CLI execution timed out after {self.timeout}s")
                process.kill()
                raise Exception(f"Claude CLI execution timed out after {self.timeout}s")
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Detailed logging of results
            logger.debug(f"✅ Claude process completed in {execution_time:.2f}s")
            logger.debug(f"📤 Return code: {process.returncode}")
            
            stdout_text = stdout.decode('utf-8')
            stderr_text = stderr.decode('utf-8')
            
            logger.debug(f"📤 Stdout length: {len(stdout_text)} characters")
            logger.debug(f"📤 Stderr length: {len(stderr_text)} characters")
            
            # Log first few lines of output for debugging
            if stdout_text:
                stdout_preview = '\n'.join(stdout_text.split('\n')[:5])
                logger.debug(f"📤 Stdout preview:\n{stdout_preview}")
                if len(stdout_text.split('\n')) > 5:
                    logger.debug(f"📤 ... (truncated, {len(stdout_text.split('\n'))} total lines)")
            
            if stderr_text:
                stderr_preview = '\n'.join(stderr_text.split('\n')[:3])
                logger.debug(f"⚠️ Stderr preview:\n{stderr_preview}")
                if len(stderr_text.split('\n')) > 3:
                    logger.debug(f"⚠️ ... (truncated, {len(stderr_text.split('\n'))} total lines)")
            
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
                    "command": ' '.join(cmd),
                    "prompt_length": len(prompt),
                    "working_directory": os.getcwd()
                }
            else:
                logger.error(f"❌ Claude CLI failed with return code {process.returncode}")
                logger.error(f"❌ Error output: {stderr_text}")
                raise Exception(f"Claude CLI failed with return code {process.returncode}: {stderr_text}")
                
        except Exception as e:
            logger.error(f"❌ Claude CLI execution error: {e}")
            raise
    
    async def _simulate_execution(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate Claude execution for testing (dry run mode) with continuation support"""
        should_continue = self._should_continue_session(work_item)
        
        if should_continue:
            logger.debug(f"🧪 SIMULATION: Continuing session for {work_item['type']} - {work_item['title']}")
        else:
            logger.debug(f"🧪 SIMULATION: Fresh session for {work_item['type']} - {work_item['title']}")
        
        # Update session state even in dry run for testing continuity logic
        self._update_session_state(work_item, simulated=True)
        
        # Simulate some execution time
        execution_time = 2.0 + (hash(work_item['id']) % 10)  # 2-12 seconds
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
                    "Updated documentation"
                ],
                "files_modified": self._generate_simulated_files(work_item),
                "summary": f"Successfully completed {work_item['title']} - this was a simulation",
                "execution_time": execution_time,
                "continued_session": should_continue
            },
            "timestamp": datetime.utcnow().isoformat(),
            "work_item_id": work_item['id'],
            "used_continue": should_continue,
            "context_strategy": self.context_strategy
        }
        
        logger.info(f"✅ SIMULATION: Task completed in {execution_time:.1f}s (continue: {should_continue})")
        return simulation_result
    
    def _generate_simulated_files(self, work_item: Dict[str, Any]) -> list:
        """Generate realistic file names for simulation"""
        task_type = work_item['type'].lower()
        
        file_patterns = {
            'bug_fix': ['src/components/buggy_component.py', 'tests/test_fix.py'],
            'feature': ['src/features/new_feature.py', 'src/api/feature_endpoint.py'],
            'test': ['tests/test_new_functionality.py', 'tests/integration/test_api.py'],
            'refactor': ['src/legacy_code.py', 'src/improved_code.py'],
            'documentation': ['README.md', 'docs/api_documentation.md']
        }
        
        return file_patterns.get(task_type, ['src/generic_file.py'])
    
    def _parse_claude_output(self, output: str) -> dict:
        """Parse Claude's output to extract meaningful information for GitHub comments"""
        if not output:
            return {"response": "", "files_changed": [], "summary": "", "actions_taken": []}
        
        lines = output.split('\n')
        
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
                
            # Skip prompt echoes and system messages
            if (line.startswith('I\'ll') or line.startswith('Let me') or 
                line.startswith('I\'m') or line.startswith('I need to') or
                line.startswith('Looking at') or line.startswith('I can see')):
                in_claude_response = True
                claude_response_lines.append(line)
                continue
            
            # Capture file operations
            if ('wrote to' in line.lower() or 'created' in line.lower() or 
                'updated' in line.lower() or 'modified' in line.lower()):
                if '.py' in line or '.js' in line or '.md' in line or '.txt' in line:
                    # Extract filename
                    words = line.split()
                    for word in words:
                        if '.' in word and any(ext in word for ext in ['.py', '.js', '.md', '.txt', '.json', '.yaml']):
                            files_changed.append(word.strip('.,'))
                            break
                actions_taken.append(line)
                
            # Capture success indicators and actions
            if (line.startswith('✅') or line.startswith('✓') or 
                'successfully' in line.lower() or 'completed' in line.lower() or
                'added' in line.lower() or 'fixed' in line.lower()):
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
            summary = summary.lstrip('✅✓ ').strip()
        
        return {
            "response": '\n'.join(claude_response_lines[-20:]),  # Last 20 lines of Claude's response
            "files_changed": list(set(files_changed)),  # Remove duplicates
            "summary": summary,
            "actions_taken": actions_taken[:5]  # Top 5 actions
        }

    async def validate_claude_cli(self) -> bool:
        """Validate that Claude CLI is available and working"""
        try:
            process = await asyncio.create_subprocess_exec(
                self.command, '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"✅ Claude CLI validated: {stdout.decode('utf-8').strip()}")
                return True
            else:
                logger.error(f"❌ Claude CLI validation failed: {stderr.decode('utf-8')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Claude CLI not found: {e}")
            return False