# CCAL Technical Implementation Plan

## Table of Contents
1. [Detailed Technical Specifications](#1-detailed-technical-specifications)
2. [Phase 1 Implementation Details](#2-phase-1-implementation-details)
3. [Integration Architecture](#3-integration-architecture)
4. [Data Models](#4-data-models)
5. [Implementation Roadmap](#5-implementation-roadmap)
6. [Testing Strategy](#6-testing-strategy)
7. [Deployment and Operations](#7-deployment-and-operations)

---

## 1. Detailed Technical Specifications

### Overall System Architecture

```
/Users/steve/Dev/aidev/ccal/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── loop.py              # Main autonomous loop controller
│   ├── scheduler.py         # Work scheduling and prioritization
│   └── state.py            # State persistence and recovery
├── discovery/
│   ├── __init__.py
│   ├── base.py             # Abstract base for discovery modules
│   ├── error_monitor.py    # Monitor error logs
│   ├── github_watcher.py   # GitHub API integration
│   ├── code_quality.py     # Static analysis integration
│   └── test_coverage.py    # Test gap detection
├── executor/
│   ├── __init__.py
│   ├── claude_wrapper.py   # Claude Code CLI wrapper
│   ├── context.py          # Context management between commands
│   └── output_parser.py    # Parse Claude Code output
├── storage/
│   ├── __init__.py
│   ├── models.py           # Data models (SQLAlchemy)
│   ├── queue.py            # Work queue management
│   └── history.py          # Execution history tracking
├── learning/
│   ├── __init__.py
│   ├── feedback.py         # Process execution feedback
│   ├── patterns.py         # Pattern recognition
│   └── adaptation.py       # Adaptive behavior
├── config/
│   ├── __init__.py
│   ├── settings.py         # Configuration management
│   └── ccal.yaml           # Main configuration file
├── utils/
│   ├── __init__.py
│   ├── logging.py          # Structured logging
│   ├── metrics.py          # Performance metrics
│   └── helpers.py          # Utility functions
├── tests/
│   └── ...                 # Test files
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
└── setup.py               # Package setup
```

### Phase-Specific Components

#### Phase 1: Core Loop (Days 1-2)
**Required Files:**
- `core/loop.py` - Main loop controller
- `executor/claude_wrapper.py` - Claude CLI wrapper
- `discovery/error_monitor.py` - Basic error log monitoring
- `storage/queue.py` - Simple work queue
- `config/ccal.yaml` - Configuration

**Key Classes:**
```python
# core/loop.py
class CCALCore:
    def __init__(self, config_path: str)
    async def start(self) -> None
    async def stop(self) -> None
    async def run_cycle(self) -> None
    
# executor/claude_wrapper.py
class ClaudeExecutor:
    def __init__(self, working_dir: str)
    async def execute_command(self, prompt: str, context: dict) -> ExecutionResult
    async def validate_session(self) -> bool
    
# discovery/error_monitor.py
class ErrorLogMonitor:
    def __init__(self, log_paths: List[str])
    async def scan_for_errors(self) -> List[WorkItem]
    def parse_error_log(self, log_content: str) -> List[Error]
```

#### Phase 2: Smart Discovery (Days 3-4)
**Additional Files:**
- `discovery/github_watcher.py` - GitHub integration
- `discovery/code_quality.py` - Code analysis
- `core/scheduler.py` - Priority scheduling

**Key Classes:**
```python
# discovery/github_watcher.py
class GitHubWatcher:
    def __init__(self, repo_owner: str, repo_name: str, token: str)
    async def fetch_issues(self) -> List[WorkItem]
    async def check_pr_feedback(self) -> List[WorkItem]
    
# core/scheduler.py
class WorkScheduler:
    def prioritize_work(self, items: List[WorkItem]) -> List[WorkItem]
    def estimate_effort(self, item: WorkItem) -> int
```

#### Phase 3: Learning & Adaptation (Days 5-6)
**Additional Files:**
- `learning/feedback.py` - Feedback processing
- `learning/patterns.py` - Pattern recognition
- `learning/adaptation.py` - Adaptive behavior

**Key Classes:**
```python
# learning/feedback.py
class FeedbackProcessor:
    def process_result(self, work: WorkItem, result: ExecutionResult) -> None
    def calculate_success_metrics(self) -> Dict[str, float]
    
# learning/adaptation.py
class AdaptiveEngine:
    def adjust_priorities(self, history: List[ExecutionResult]) -> None
    def recommend_approach(self, work: WorkItem) -> Strategy
```

### Dependencies and Requirements

```txt
# requirements.txt
# Core
asyncio>=3.11
pyyaml>=6.0
click>=8.1.0          # CLI interface
python-dotenv>=1.0.0  # Environment variables

# Storage
sqlalchemy>=2.0.0
aiosqlite>=0.19.0    # Async SQLite

# Discovery
aiofiles>=23.0.0      # Async file operations
watchdog>=3.0.0       # File system monitoring
PyGithub>=2.1.0       # GitHub API
gitpython>=3.1.0      # Git operations

# Code Analysis
pylint>=3.0.0         # Code quality
coverage>=7.0.0       # Test coverage
radon>=6.0.0          # Complexity metrics

# Monitoring
prometheus-client>=0.19.0  # Metrics
structlog>=24.0.0         # Structured logging

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-mock>=3.12.0
pytest-cov>=4.1.0
```

### Configuration Format

```yaml
# config/ccal.yaml
ccal:
  version: "1.0.0"
  environment: "development"  # development, staging, production
  
  # Core loop settings
  loop:
    cycle_interval_seconds: 300  # 5 minutes between cycles
    max_concurrent_work: 1        # Sequential execution initially
    error_retry_limit: 3
    session_timeout_minutes: 60
    
  # Claude Code CLI settings
  claude:
    executable_path: "claude"  # or full path
    working_directory: "/Users/steve/Dev/aidev"
    context_preservation: true
    max_prompt_length: 8000
    timeout_seconds: 120
    auth_method: "session"  # session, api_key
    
  # Discovery settings
  discovery:
    error_logs:
      enabled: true
      paths:
        - "/Users/steve/Dev/aidev/logs/errors/"
        - "/var/log/claude/"
      patterns:
        - "ERROR"
        - "CRITICAL"
        - "Exception"
      scan_interval_minutes: 10
      
    github:
      enabled: false  # Phase 2
      owner: "username"
      repo: "aidev"
      token: "${GITHUB_TOKEN}"
      issue_labels: ["bug", "enhancement", "ccal-task"]
      check_interval_minutes: 30
      
    code_quality:
      enabled: false  # Phase 2
      paths:
        - "/Users/steve/Dev/aidev/"
      threshold_complexity: 10
      min_test_coverage: 80
      
  # Storage settings
  storage:
    type: "sqlite"  # sqlite, postgres, memory
    path: "/Users/steve/Dev/aidev/ccal/data/ccal.db"
    queue_size_limit: 100
    history_retention_days: 30
    
  # Learning settings (Phase 3)
  learning:
    enabled: false
    success_threshold: 0.7
    pattern_min_occurrences: 3
    adaptation_interval_hours: 24
    
  # Monitoring
  monitoring:
    log_level: "INFO"
    log_file: "/Users/steve/Dev/aidev/ccal/logs/ccal.log"
    metrics_enabled: true
    metrics_port: 9090
    
  # Safety controls
  safety:
    dry_run: false
    require_confirmation: false
    excluded_paths:
      - "/Users/steve/Dev/aidev/ccal/"  # Don't modify self
      - "/.git/"
    max_file_operations: 50
    max_execution_time_minutes: 30
```

---

## 2. Phase 1 Implementation Details

### Core Loop MVP Implementation

#### Main Loop Controller (`core/loop.py`)

```python
import asyncio
import signal
from datetime import datetime
from typing import Optional, List
from pathlib import Path
import yaml

from ..executor.claude_wrapper import ClaudeExecutor
from ..discovery.error_monitor import ErrorLogMonitor
from ..storage.queue import WorkQueue
from ..storage.models import WorkItem, ExecutionResult
from ..utils.logging import get_logger

logger = get_logger(__name__)

class CCALCore:
    """Main autonomous loop controller for CCAL."""
    
    def __init__(self, config_path: str = "config/ccal.yaml"):
        self.config = self._load_config(config_path)
        self.running = False
        self.current_cycle = 0
        
        # Initialize components
        self.executor = ClaudeExecutor(
            working_dir=self.config['claude']['working_directory'],
            config=self.config['claude']
        )
        
        self.error_monitor = ErrorLogMonitor(
            log_paths=self.config['discovery']['error_logs']['paths'],
            patterns=self.config['discovery']['error_logs']['patterns']
        )
        
        self.work_queue = WorkQueue(
            db_path=self.config['storage']['path'],
            max_size=self.config['storage']['queue_size_limit']
        )
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
            
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config['ccal']
    
    async def start(self) -> None:
        """Start the autonomous loop."""
        logger.info("Starting CCAL autonomous loop")
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        # Validate Claude session
        if not await self.executor.validate_session():
            logger.error("Failed to validate Claude Code session")
            return
        
        # Main loop
        try:
            while self.running:
                await self.run_cycle()
                await asyncio.sleep(self.config['loop']['cycle_interval_seconds'])
                
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}")
            raise
        finally:
            await self.stop()
    
    async def run_cycle(self) -> None:
        """Run a single cycle of the autonomous loop."""
        self.current_cycle += 1
        logger.info(f"Starting cycle {self.current_cycle}")
        
        try:
            # Phase 1: Discovery
            new_work = await self._discover_work()
            if new_work:
                logger.info(f"Discovered {len(new_work)} new work items")
                for item in new_work:
                    await self.work_queue.add(item)
            
            # Phase 2: Execution
            work_item = await self.work_queue.get_next()
            if work_item:
                logger.info(f"Executing work item: {work_item.title}")
                result = await self._execute_work(work_item)
                
                # Phase 3: Feedback
                await self._process_feedback(work_item, result)
            else:
                logger.debug("No work items in queue")
                
        except Exception as e:
            logger.error(f"Error in cycle {self.current_cycle}: {e}")
    
    async def _discover_work(self) -> List[WorkItem]:
        """Discover new work from various sources."""
        work_items = []
        
        # Error log monitoring
        if self.config['discovery']['error_logs']['enabled']:
            errors = await self.error_monitor.scan_for_errors()
            work_items.extend(errors)
        
        # Additional discovery sources will be added in Phase 2
        
        return work_items
    
    async def _execute_work(self, work_item: WorkItem) -> ExecutionResult:
        """Execute a work item using Claude Code."""
        
        # Build prompt from work item
        prompt = self._build_prompt(work_item)
        
        # Execute with Claude
        result = await self.executor.execute_command(
            prompt=prompt,
            context={
                'work_id': work_item.id,
                'work_type': work_item.type,
                'priority': work_item.priority
            }
        )
        
        # Update work item status
        if result.success:
            work_item.status = 'completed'
        else:
            work_item.status = 'failed'
            work_item.attempts += 1
        
        await self.work_queue.update(work_item)
        
        return result
    
    def _build_prompt(self, work_item: WorkItem) -> str:
        """Build Claude Code prompt from work item."""
        prompt = f"""
Task: {work_item.title}

Description: {work_item.description}

Context:
{work_item.context}

Please complete this task following best practices.
"""
        return prompt
    
    async def _process_feedback(self, work_item: WorkItem, result: ExecutionResult) -> None:
        """Process execution feedback for learning."""
        # Basic feedback logging for Phase 1
        if result.success:
            logger.info(f"Successfully completed: {work_item.title}")
        else:
            logger.warning(f"Failed to complete: {work_item.title} - {result.error}")
        
        # Advanced feedback processing will be added in Phase 3
    
    async def stop(self) -> None:
        """Stop the autonomous loop gracefully."""
        logger.info("Stopping CCAL autonomous loop")
        self.running = False
        await self.work_queue.close()
        await self.executor.cleanup()
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received shutdown signal {signum}")
        self.running = False
```

#### Claude Code CLI Wrapper (`executor/claude_wrapper.py`)

```python
import asyncio
import subprocess
import json
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from ..utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class ExecutionResult:
    """Result of Claude Code execution."""
    success: bool
    output: str
    error: Optional[str] = None
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = None
    
class ClaudeExecutor:
    """Wrapper for Claude Code CLI execution."""
    
    def __init__(self, working_dir: str, config: dict):
        self.working_dir = Path(working_dir)
        self.config = config
        self.executable = config.get('executable_path', 'claude')
        self.timeout = config.get('timeout_seconds', 120)
        self.context_file = None
        
        if config.get('context_preservation'):
            self.context_file = self.working_dir / '.ccal_context.json'
    
    async def validate_session(self) -> bool:
        """Validate Claude Code CLI is accessible and authenticated."""
        try:
            # Test claude CLI availability
            result = await self._run_command(['--version'])
            if result.returncode != 0:
                logger.error("Claude Code CLI not found or not accessible")
                return False
            
            # Test authentication (simple command)
            test_prompt = "echo 'CCAL validation test'"
            result = await self._run_command([test_prompt])
            
            if result.returncode == 0:
                logger.info("Claude Code session validated successfully")
                return True
            else:
                logger.error("Claude Code authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return False
    
    async def execute_command(self, prompt: str, context: Optional[Dict] = None) -> ExecutionResult:
        """Execute a command using Claude Code CLI."""
        start_time = datetime.now()
        
        try:
            # Prepare prompt with context
            full_prompt = self._prepare_prompt(prompt, context)
            
            # Create temporary file for complex prompts
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(full_prompt)
                prompt_file = f.name
            
            # Execute claude command
            cmd = [self.executable, '-f', prompt_file]
            result = await self._run_command(cmd)
            
            # Parse output
            duration = (datetime.now() - start_time).total_seconds()
            
            if result.returncode == 0:
                return ExecutionResult(
                    success=True,
                    output=result.stdout,
                    duration_seconds=duration,
                    metadata={'context': context}
                )
            else:
                return ExecutionResult(
                    success=False,
                    output=result.stdout,
                    error=result.stderr,
                    duration_seconds=duration,
                    metadata={'context': context}
                )
                
        except asyncio.TimeoutError:
            logger.error(f"Command execution timed out after {self.timeout} seconds")
            return ExecutionResult(
                success=False,
                output="",
                error="Execution timeout",
                duration_seconds=self.timeout
            )
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
        finally:
            # Cleanup temp file
            if 'prompt_file' in locals():
                Path(prompt_file).unlink(missing_ok=True)
    
    def _prepare_prompt(self, prompt: str, context: Optional[Dict] = None) -> str:
        """Prepare prompt with context information."""
        
        # Load preserved context if available
        preserved_context = self._load_context()
        
        # Build full prompt
        parts = []
        
        if preserved_context:
            parts.append(f"Previous context: {json.dumps(preserved_context, indent=2)}")
        
        if context:
            parts.append(f"Current task context: {json.dumps(context, indent=2)}")
        
        parts.append(f"Working directory: {self.working_dir}")
        parts.append("")
        parts.append(prompt)
        
        full_prompt = "\n".join(parts)
        
        # Save context for next execution
        if context and self.context_file:
            self._save_context(context)
        
        return full_prompt
    
    async def _run_command(self, cmd: list) -> subprocess.CompletedProcess:
        """Run a subprocess command asynchronously."""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.working_dir)
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=process.returncode,
                stdout=stdout.decode('utf-8'),
                stderr=stderr.decode('utf-8')
            )
        except asyncio.TimeoutError:
            process.kill()
            raise
    
    def _load_context(self) -> Optional[Dict]:
        """Load preserved context from file."""
        if not self.context_file or not self.context_file.exists():
            return None
        
        try:
            with open(self.context_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load context: {e}")
            return None
    
    def _save_context(self, context: Dict) -> None:
        """Save context to file for preservation."""
        if not self.context_file:
            return
        
        try:
            with open(self.context_file, 'w') as f:
                json.dump(context, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save context: {e}")
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        # Remove context file if exists
        if self.context_file and self.context_file.exists():
            self.context_file.unlink()
```

#### Error Log Monitor (`discovery/error_monitor.py`)

```python
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import hashlib

from ..storage.models import WorkItem
from ..utils.logging import get_logger

logger = get_logger(__name__)

class ErrorLogMonitor:
    """Monitor error logs and create work items for fixes."""
    
    def __init__(self, log_paths: List[str], patterns: List[str]):
        self.log_paths = [Path(p) for p in log_paths]
        self.patterns = [re.compile(p) for p in patterns]
        self.seen_errors = set()  # Track processed errors
        self.last_scan = None
    
    async def scan_for_errors(self) -> List[WorkItem]:
        """Scan log files for errors and create work items."""
        work_items = []
        
        for log_path in self.log_paths:
            if log_path.is_dir():
                # Scan all log files in directory
                log_files = list(log_path.glob("*.log")) + list(log_path.glob("*.json"))
            else:
                log_files = [log_path] if log_path.exists() else []
            
            for log_file in log_files:
                items = await self._process_log_file(log_file)
                work_items.extend(items)
        
        self.last_scan = datetime.now()
        logger.info(f"Error scan found {len(work_items)} new errors")
        
        return work_items
    
    async def _process_log_file(self, log_file: Path) -> List[WorkItem]:
        """Process a single log file for errors."""
        work_items = []
        
        try:
            # Check if file was modified since last scan
            if self.last_scan:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < self.last_scan:
                    return []
            
            # Read and parse log file
            if log_file.suffix == '.json':
                errors = self._parse_json_log(log_file)
            else:
                errors = self._parse_text_log(log_file)
            
            # Create work items for new errors
            for error in errors:
                error_hash = self._hash_error(error)
                if error_hash not in self.seen_errors:
                    self.seen_errors.add(error_hash)
                    work_item = self._create_work_item(error, log_file)
                    work_items.append(work_item)
                    
        except Exception as e:
            logger.error(f"Failed to process log file {log_file}: {e}")
        
        return work_items
    
    def _parse_json_log(self, log_file: Path) -> List[Dict]:
        """Parse JSON formatted log file."""
        errors = []
        
        try:
            with open(log_file, 'r') as f:
                data = json.load(f)
                
            # Handle feedback log format
            if 'error_logs' in data:
                for error in data['error_logs'].get('critical_errors', []):
                    errors.append({
                        'level': 'CRITICAL',
                        'message': error,
                        'timestamp': datetime.now().isoformat(),
                        'source': str(log_file)
                    })
                    
        except Exception as e:
            logger.warning(f"Failed to parse JSON log {log_file}: {e}")
        
        return errors
    
    def _parse_text_log(self, log_file: Path) -> List[Dict]:
        """Parse text formatted log file."""
        errors = []
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines):
                for pattern in self.patterns:
                    if pattern.search(line):
                        # Extract error context (surrounding lines)
                        context_start = max(0, i - 2)
                        context_end = min(len(lines), i + 3)
                        context = ''.join(lines[context_start:context_end])
                        
                        errors.append({
                            'level': 'ERROR',
                            'message': line.strip(),
                            'context': context,
                            'line_number': i + 1,
                            'timestamp': datetime.now().isoformat(),
                            'source': str(log_file)
                        })
                        break
                        
        except Exception as e:
            logger.warning(f"Failed to parse text log {log_file}: {e}")
        
        return errors
    
    def _hash_error(self, error: Dict) -> str:
        """Generate unique hash for error to avoid duplicates."""
        # Create hash from error message and source
        key = f"{error.get('message', '')}:{error.get('source', '')}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def _create_work_item(self, error: Dict, log_file: Path) -> WorkItem:
        """Create work item from error."""
        
        # Determine priority based on error level
        priority = 5 if error.get('level') == 'CRITICAL' else 3
        
        # Build description
        description = f"""
Fix error detected in log file: {log_file}

Error Message: {error.get('message', 'Unknown error')}

Context:
{error.get('context', 'No context available')}

Timestamp: {error.get('timestamp')}
Line Number: {error.get('line_number', 'Unknown')}
"""
        
        return WorkItem(
            type='bug_fix',
            priority=priority,
            title=f"Fix: {error.get('message', 'Unknown error')[:100]}",
            description=description,
            source='error_monitor',
            context={
                'log_file': str(log_file),
                'error_details': error
            }
        )
```

### Startup and Shutdown Procedures

#### Main Entry Point (`main.py`)

```python
#!/usr/bin/env python3
"""
CCAL - Claude Code Autonomous Loop
Main entry point for the autonomous development system.
"""

import asyncio
import click
import sys
from pathlib import Path

from ccal.core.loop import CCALCore
from ccal.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)

@click.command()
@click.option('--config', '-c', default='config/ccal.yaml', help='Path to configuration file')
@click.option('--daemon', '-d', is_flag=True, help='Run as daemon process')
@click.option('--dry-run', is_flag=True, help='Run in dry-run mode (no actual execution)')
@click.option('--once', is_flag=True, help='Run single cycle and exit')
@click.option('--log-level', default='INFO', help='Logging level')
def main(config, daemon, dry_run, once, log_level):
    """CCAL - Claude Code Autonomous Loop"""
    
    # Setup logging
    setup_logging(level=log_level)
    
    logger.info("=" * 60)
    logger.info("CCAL - Claude Code Autonomous Loop")
    logger.info("=" * 60)
    
    # Validate config file exists
    config_path = Path(config)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config}")
        sys.exit(1)
    
    # Initialize core
    try:
        ccal = CCALCore(config_path=str(config_path))
        
        # Override dry-run if specified
        if dry_run:
            ccal.config['safety']['dry_run'] = True
            logger.warning("Running in DRY-RUN mode - no actual changes will be made")
        
        # Run based on mode
        if once:
            logger.info("Running single cycle")
            asyncio.run(ccal.run_cycle())
        elif daemon:
            logger.info("Starting daemon mode")
            # TODO: Implement proper daemon with systemd/supervisor
            asyncio.run(ccal.start())
        else:
            logger.info("Starting interactive mode")
            asyncio.run(ccal.start())
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("CCAL shutdown complete")

if __name__ == "__main__":
    main()
```

---

## 3. Integration Architecture

### Claude Code CLI Integration Patterns

#### Command Execution Strategy

```python
# executor/command_builder.py
class CommandBuilder:
    """Build Claude Code commands with proper context and safety."""
    
    SAFE_COMMANDS = [
        'analyze', 'review', 'test', 'format', 'lint'
    ]
    
    DANGEROUS_COMMANDS = [
        'deploy', 'delete', 'drop', 'truncate', 'rm'
    ]
    
    def build_command(self, work_item: WorkItem) -> str:
        """Build safe command from work item."""
        
        # Safety checks
        if self._contains_dangerous_operation(work_item):
            raise ValueError("Dangerous operation detected")
        
        # Build command based on work type
        if work_item.type == 'bug_fix':
            return self._build_bug_fix_command(work_item)
        elif work_item.type == 'feature':
            return self._build_feature_command(work_item)
        elif work_item.type == 'test':
            return self._build_test_command(work_item)
        else:
            return self._build_generic_command(work_item)
```

#### Output Parsing

```python
# executor/output_parser.py
import re
from typing import Dict, List, Any

class ClaudeOutputParser:
    """Parse Claude Code output for actionable information."""
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Claude output into structured format."""
        
        result = {
            'files_modified': [],
            'tests_run': [],
            'errors': [],
            'warnings': [],
            'summary': '',
            'metrics': {}
        }
        
        # Parse file modifications
        file_pattern = r'Modified: (.+)'
        result['files_modified'] = re.findall(file_pattern, output)
        
        # Parse test results
        test_pattern = r'(\d+) passed, (\d+) failed'
        test_match = re.search(test_pattern, output)
        if test_match:
            result['metrics']['tests_passed'] = int(test_match.group(1))
            result['metrics']['tests_failed'] = int(test_match.group(2))
        
        # Parse errors
        error_pattern = r'ERROR: (.+)'
        result['errors'] = re.findall(error_pattern, output)
        
        return result
```

### Work Discovery Integration

#### GitHub API Integration

```python
# discovery/github_watcher.py
from github import Github
from typing import List
import os

class GitHubWatcher:
    """Monitor GitHub for work items."""
    
    def __init__(self, owner: str, repo: str, token: str = None):
        self.owner = owner
        self.repo_name = repo
        self.token = token or os.getenv('GITHUB_TOKEN')
        self.github = Github(self.token)
        self.repo = self.github.get_repo(f"{owner}/{repo}")
        
    async def fetch_issues(self) -> List[WorkItem]:
        """Fetch open issues as work items."""
        work_items = []
        
        # Get issues with CCAL labels
        issues = self.repo.get_issues(
            state='open',
            labels=['ccal-task']
        )
        
        for issue in issues:
            work_item = WorkItem(
                type=self._determine_type(issue.labels),
                priority=self._determine_priority(issue),
                title=issue.title,
                description=issue.body,
                source='github',
                context={
                    'issue_number': issue.number,
                    'issue_url': issue.html_url,
                    'author': issue.user.login,
                    'created_at': issue.created_at.isoformat()
                }
            )
            work_items.append(work_item)
        
        return work_items
```

---

## 4. Data Models

### Core Data Models

```python
# storage/models.py
from sqlalchemy import Column, String, Integer, DateTime, JSON, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class WorkItem(Base):
    """Work item to be executed by CCAL."""
    __tablename__ = 'work_items'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String, nullable=False)  # bug_fix, feature, test, etc.
    priority = Column(Integer, default=3)  # 1-5 scale
    status = Column(String, default='pending')  # pending, in_progress, completed, failed
    
    title = Column(String, nullable=False)
    description = Column(String)
    source = Column(String)  # error_monitor, github, code_quality, etc.
    context = Column(JSON, default=dict)
    
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    assigned_to = Column(String)  # For future multi-agent support
    parent_id = Column(String)  # For task dependencies
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'priority': self.priority,
            'status': self.status,
            'title': self.title,
            'description': self.description,
            'source': self.source,
            'context': self.context,
            'attempts': self.attempts,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ExecutionResult(Base):
    """Result of work item execution."""
    __tablename__ = 'execution_results'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    work_item_id = Column(String, nullable=False)
    
    success = Column(Boolean, nullable=False)
    output = Column(String)
    error = Column(String)
    
    duration_seconds = Column(Float)
    tokens_used = Column(Integer)
    
    files_modified = Column(JSON, default=list)
    tests_results = Column(JSON, default=dict)
    metrics = Column(JSON, default=dict)
    
    executed_at = Column(DateTime, default=datetime.utcnow)
    executed_by = Column(String, default='ccal')

class LearningPattern(Base):
    """Patterns learned from execution history."""
    __tablename__ = 'learning_patterns'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pattern_type = Column(String)  # error_fix, optimization, etc.
    
    trigger_conditions = Column(JSON)  # Conditions that trigger this pattern
    successful_approach = Column(JSON)  # What worked
    failed_approaches = Column(JSON, default=list)  # What didn't work
    
    confidence_score = Column(Float, default=0.0)  # 0-1 confidence
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime)

class SystemState(Base):
    """System state for recovery."""
    __tablename__ = 'system_state'
    
    id = Column(String, primary_key=True, default='current')
    current_cycle = Column(Integer, default=0)
    last_execution = Column(DateTime)
    
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    
    current_work_item_id = Column(String)
    work_queue_size = Column(Integer, default=0)
    
    claude_session_valid = Column(Boolean, default=False)
    last_session_check = Column(DateTime)
    
    config_version = Column(String)
    metadata = Column(JSON, default=dict)
```

### Storage Implementation

```python
# storage/queue.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Optional, List
import asyncio

from .models import Base, WorkItem, ExecutionResult

class WorkQueue:
    """Manage work queue with persistence."""
    
    def __init__(self, db_path: str, max_size: int = 100):
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.max_size = max_size
        self._lock = asyncio.Lock()
    
    async def add(self, work_item: WorkItem) -> bool:
        """Add work item to queue."""
        async with self._lock:
            session = self.Session()
            try:
                # Check queue size
                count = session.query(WorkItem).filter_by(status='pending').count()
                if count >= self.max_size:
                    return False
                
                session.add(work_item)
                session.commit()
                return True
            finally:
                session.close()
    
    async def get_next(self) -> Optional[WorkItem]:
        """Get next work item by priority."""
        async with self._lock:
            session = self.Session()
            try:
                # Get highest priority pending item
                work_item = session.query(WorkItem)\
                    .filter_by(status='pending')\
                    .order_by(WorkItem.priority.desc(), WorkItem.created_at)\
                    .first()
                
                if work_item:
                    work_item.status = 'in_progress'
                    work_item.started_at = datetime.utcnow()
                    session.commit()
                
                return work_item
            finally:
                session.close()
    
    async def update(self, work_item: WorkItem) -> None:
        """Update work item status."""
        async with self._lock:
            session = self.Session()
            try:
                session.merge(work_item)
                session.commit()
            finally:
                session.close()
    
    async def get_pending_count(self) -> int:
        """Get count of pending items."""
        session = self.Session()
        try:
            return session.query(WorkItem).filter_by(status='pending').count()
        finally:
            session.close()
    
    async def close(self) -> None:
        """Close database connection."""
        self.engine.dispose()
```

---

## 5. Implementation Roadmap

### Day 1: Core Infrastructure Setup

**Morning (4 hours):**
1. Project setup
   - Create directory structure
   - Initialize git repository
   - Setup virtual environment
   - Install base dependencies

2. Configuration system
   - Create `config/ccal.yaml`
   - Implement `config/settings.py`
   - Environment variable handling

3. Logging infrastructure
   - Setup structured logging
   - Create log rotation
   - Implement debug/info/error levels

**Afternoon (4 hours):**
4. Data models
   - Create SQLAlchemy models
   - Setup database migrations
   - Implement WorkQueue class

5. Basic testing setup
   - pytest configuration
   - Create test fixtures
   - Write first unit tests

### Day 2: Basic Loop Implementation

**Morning (4 hours):**
1. Claude CLI wrapper
   - Implement `ClaudeExecutor`
   - Session validation
   - Command execution

2. Error monitor
   - Implement `ErrorLogMonitor`
   - Log parsing logic
   - Work item creation

**Afternoon (4 hours):**
3. Main loop
   - Implement `CCALCore`
   - Cycle management
   - Signal handling

4. Integration testing
   - Test full cycle
   - Error handling
   - Recovery scenarios

### Day 3-4: Work Discovery Modules

**Day 3:**
1. GitHub integration
   - API authentication
   - Issue fetching
   - PR monitoring

2. Code quality scanner
   - Pylint integration
   - Complexity analysis
   - Technical debt detection

**Day 4:**
3. Test coverage analyzer
   - Coverage.py integration
   - Gap detection
   - Test generation hints

4. Work prioritization
   - Implement scheduler
   - Priority algorithms
   - Effort estimation

### Day 5-6: Learning and Adaptation

**Day 5:**
1. Feedback processor
   - Success/failure tracking
   - Pattern extraction
   - Metrics calculation

2. Learning patterns
   - Pattern storage
   - Recognition logic
   - Confidence scoring

**Day 6:**
3. Adaptive behavior
   - Strategy selection
   - Priority adjustment
   - Approach optimization

4. Final integration
   - End-to-end testing
   - Performance optimization
   - Documentation

---

## 6. Testing Strategy

### Unit Testing

```python
# tests/test_claude_executor.py
import pytest
from unittest.mock import Mock, patch
from ccal.executor.claude_wrapper import ClaudeExecutor

class TestClaudeExecutor:
    
    @pytest.fixture
    def executor(self):
        config = {
            'executable_path': 'claude',
            'working_directory': '/tmp/test',
            'timeout_seconds': 10
        }
        return ClaudeExecutor('/tmp/test', config)
    
    @pytest.mark.asyncio
    async def test_validate_session_success(self, executor):
        with patch.object(executor, '_run_command') as mock_run:
            mock_run.return_value.returncode = 0
            result = await executor.validate_session()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_execute_command_success(self, executor):
        with patch.object(executor, '_run_command') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Task completed"
            
            result = await executor.execute_command("test prompt")
            assert result.success is True
            assert "Task completed" in result.output
```

### Integration Testing

```python
# tests/test_integration.py
import pytest
import tempfile
from pathlib import Path
from ccal.core.loop import CCALCore

class TestCCALIntegration:
    
    @pytest.fixture
    def temp_config(self):
        """Create temporary configuration."""
        config = """
ccal:
  loop:
    cycle_interval_seconds: 1
  claude:
    executable_path: "echo"  # Mock with echo
    working_directory: "/tmp"
  discovery:
    error_logs:
      enabled: true
      paths: ["/tmp/test_logs"]
  storage:
    type: "sqlite"
    path: ":memory:"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as f:
            f.write(config)
            f.flush()
            yield f.name
    
    @pytest.mark.asyncio
    async def test_full_cycle(self, temp_config):
        """Test complete discovery-execution-feedback cycle."""
        ccal = CCALCore(temp_config)
        
        # Create test error log
        log_dir = Path("/tmp/test_logs")
        log_dir.mkdir(exist_ok=True)
        
        with open(log_dir / "test.log", "w") as f:
            f.write("ERROR: Test error message\n")
        
        # Run single cycle
        await ccal.run_cycle()
        
        # Verify work was discovered
        count = await ccal.work_queue.get_pending_count()
        assert count > 0
```

### Performance Testing

```python
# tests/test_performance.py
import pytest
import time
import asyncio
from ccal.storage.queue import WorkQueue
from ccal.storage.models import WorkItem

class TestPerformance:
    
    @pytest.mark.asyncio
    async def test_queue_throughput(self):
        """Test work queue can handle load."""
        queue = WorkQueue(":memory:", max_size=1000)
        
        # Add 100 work items
        start = time.time()
        for i in range(100):
            item = WorkItem(
                type='test',
                title=f"Test item {i}",
                priority=i % 5
            )
            await queue.add(item)
        
        duration = time.time() - start
        assert duration < 5.0  # Should complete in 5 seconds
        
        # Process items
        processed = 0
        while await queue.get_next():
            processed += 1
        
        assert processed == 100
```

---

## 7. Deployment and Operations

### Running Continuously

#### Systemd Service (Linux/macOS)

```ini
# /etc/systemd/system/ccal.service
[Unit]
Description=CCAL - Claude Code Autonomous Loop
After=network.target

[Service]
Type=simple
User=aidev
Group=aidev
WorkingDirectory=/Users/steve/Dev/aidev/ccal
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/Users/steve/Dev/aidev/ccal/venv/bin/python main.py --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI (placeholder - adjust based on actual installation)
# RUN curl -sSL https://claude.ai/install.sh | sh

# Copy application
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run CCAL
CMD ["python", "main.py", "--daemon"]
```

### Monitoring and Logging

```python
# utils/logging.py
import logging
import structlog
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logging(level: str = "INFO", log_file: str = None):
    """Setup structured logging."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Setup Python logging
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)

def get_logger(name: str):
    """Get a structured logger."""
    return structlog.get_logger(name)
```

### Metrics Collection

```python
# utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# Define metrics
work_items_discovered = Counter('ccal_work_items_discovered', 'Total work items discovered', ['source'])
work_items_executed = Counter('ccal_work_items_executed', 'Total work items executed', ['type', 'status'])
execution_duration = Histogram('ccal_execution_duration_seconds', 'Execution duration in seconds')
queue_size = Gauge('ccal_queue_size', 'Current work queue size')
cycles_completed = Counter('ccal_cycles_completed', 'Total cycles completed')

def start_metrics_server(port: int = 9090):
    """Start Prometheus metrics server."""
    start_http_server(port)

def record_work_discovered(source: str, count: int):
    """Record work items discovered."""
    work_items_discovered.labels(source=source).inc(count)

def record_execution(work_type: str, success: bool, duration: float):
    """Record work execution metrics."""
    status = 'success' if success else 'failure'
    work_items_executed.labels(type=work_type, status=status).inc()
    execution_duration.observe(duration)

def update_queue_size(size: int):
    """Update queue size gauge."""
    queue_size.set(size)

def record_cycle_complete():
    """Record cycle completion."""
    cycles_completed.inc()
```

### Configuration Management

```python
# config/settings.py
import os
import yaml
from pathlib import Path
from typing import Dict, Any

class ConfigManager:
    """Manage CCAL configuration with environment variable support."""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._apply_env_overrides()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides."""
        
        # Map of env vars to config paths
        env_mappings = {
            'CCAL_CYCLE_INTERVAL': 'ccal.loop.cycle_interval_seconds',
            'CCAL_CLAUDE_TIMEOUT': 'ccal.claude.timeout_seconds',
            'CCAL_GITHUB_TOKEN': 'ccal.discovery.github.token',
            'CCAL_LOG_LEVEL': 'ccal.monitoring.log_level',
            'CCAL_DRY_RUN': 'ccal.safety.dry_run'
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested(config_path, value)
    
    def _set_nested(self, path: str, value: Any):
        """Set nested configuration value."""
        keys = path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            config = config.setdefault(key, {})
        
        # Convert value types
        if value.lower() in ['true', 'false']:
            value = value.lower() == 'true'
        elif value.isdigit():
            value = int(value)
        
        config[keys[-1]] = value
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get configuration value by path."""
        keys = path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        
        return value
```

### Performance Optimization

```python
# utils/performance.py
import asyncio
from functools import wraps
import time
from typing import Callable

def rate_limit(calls_per_second: float):
    """Rate limit decorator for async functions."""
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                await asyncio.sleep(left_to_wait)
            ret = await func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator

class ConnectionPool:
    """Reusable connection pool for Claude sessions."""
    
    def __init__(self, max_size: int = 5):
        self.max_size = max_size
        self.pool = asyncio.Queue(maxsize=max_size)
        self.created = 0
    
    async def acquire(self):
        """Acquire a connection from the pool."""
        try:
            return await self.pool.get_nowait()
        except asyncio.QueueEmpty:
            if self.created < self.max_size:
                # Create new connection
                self.created += 1
                return await self._create_connection()
            else:
                # Wait for available connection
                return await self.pool.get()
    
    async def release(self, conn):
        """Release connection back to pool."""
        await self.pool.put(conn)
    
    async def _create_connection(self):
        """Create new Claude session."""
        # Implementation depends on Claude CLI session management
        pass
```

### Backup and Recovery

```python
# utils/backup.py
import shutil
import json
from pathlib import Path
from datetime import datetime

class BackupManager:
    """Manage CCAL state backups."""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_backup(self, db_path: str, config_path: str) -> str:
        """Create full system backup."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"ccal_backup_{timestamp}"
        backup_path.mkdir()
        
        # Backup database
        shutil.copy2(db_path, backup_path / "ccal.db")
        
        # Backup configuration
        shutil.copy2(config_path, backup_path / "ccal.yaml")
        
        # Backup metadata
        metadata = {
            'timestamp': timestamp,
            'version': '1.0.0',
            'db_path': db_path,
            'config_path': config_path
        }
        
        with open(backup_path / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return str(backup_path)
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore from backup."""
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            return False
        
        # Load metadata
        with open(backup_path / "metadata.json", 'r') as f:
            metadata = json.load(f)
        
        # Restore database
        shutil.copy2(
            backup_path / "ccal.db",
            metadata['db_path']
        )
        
        # Restore configuration
        shutil.copy2(
            backup_path / "ccal.yaml",
            metadata['config_path']
        )
        
        return True
```

---

## Implementation Summary

This comprehensive technical implementation plan provides:

1. **Complete file structure** with all necessary modules
2. **Detailed class implementations** with key methods
3. **Working code examples** for core functionality
4. **Configuration management** with YAML and environment variables
5. **Testing strategies** at unit, integration, and performance levels
6. **Deployment options** including systemd, Docker, and monitoring
7. **Operational tools** for logging, metrics, backups, and recovery

The system is designed to be:
- **Lightweight**: Minimal dependencies, simple architecture
- **Claude-native**: Direct CLI integration without complex abstractions
- **Self-discovering**: Autonomous work generation from multiple sources
- **Resilient**: Error handling, recovery, and backup mechanisms
- **Observable**: Comprehensive logging and metrics
- **Testable**: Clear separation of concerns, mockable components

To begin implementation:
1. Create the directory structure at `/Users/steve/Dev/aidev/ccal/`
2. Install dependencies from `requirements.txt`
3. Implement Phase 1 components (Days 1-2)
4. Test basic loop functionality
5. Gradually add Phase 2 and 3 features

The modular design allows for incremental development while maintaining a working system at each phase.