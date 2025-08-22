#!/usr/bin/env python3
"""
Sugar Main Entry Point - Start the AI-powered autonomous development system
"""
import asyncio
import json
import logging
import signal
import sys
from pathlib import Path
import click
from datetime import datetime

from .core.loop import SugarLoop
from .__version__ import get_version_info, __version__

def setup_logging(log_file_path='.sugar/sugar.log', debug=False):
    """Setup logging with proper file path from configuration"""
    # Ensure log directory exists
    Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)
    
    level = logging.DEBUG if debug else logging.INFO
    
    # Clear any existing handlers
    logging.getLogger().handlers.clear()
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file_path)
        ]
    )

logger = logging.getLogger(__name__)

def _format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.0f}s"
    else:
        hours = int(seconds / 3600)
        remaining_minutes = int((seconds % 3600) / 60)
        return f"{hours}h {remaining_minutes}m"

# Global variable to hold the loop instance
sugar_loop = None
shutdown_event = None

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"🛑 Shutdown signal received, stopping Sugar...")
    if shutdown_event:
        shutdown_event.set()
        logger.info("🔔 Shutdown event triggered")
    else:
        logger.warning("⚠️ Shutdown event not available")

@click.group(invoke_without_command=True)
@click.option('--config', default='.sugar/config.yaml', help='Configuration file path')
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--version', is_flag=True, help='Show version information')
@click.pass_context
def cli(ctx, config, debug, version):
    """Sugar - AI-powered autonomous development system
    
    A lightweight autonomous development system that works with Claude Code CLI
    """
    # Handle version request
    if version:
        click.echo(get_version_info())
        ctx.exit()
    
    # If no command was given, show help
    if ctx.invoked_subcommand is None and not version:
        click.echo(ctx.get_help())
        return
    
    # Setup logging with proper configuration
    log_file_path = '.sugar/sugar.log'  # Default
    if Path(config).exists():
        try:
            import yaml
            with open(config, 'r') as f:
                config_data = yaml.safe_load(f)
            log_file_path = config_data.get('sugar', {}).get('logging', {}).get('file', '.sugar/sugar.log')
        except Exception:
            pass  # Use default if config can't be read
    
    setup_logging(log_file_path, debug)
    
    if debug:
        logger.debug("🐛 Debug logging enabled")
    
    ctx.ensure_object(dict)
    ctx.obj['config'] = config

@cli.command()
@click.option('--project-dir', default='.', help='Project directory to initialize Sugar in')
def init(project_dir):
    """Initialize Sugar in a project directory"""
    import shutil
    import json
    
    project_path = Path(project_dir).resolve()
    sugar_dir = project_path / '.sugar'
    
    click.echo(f"🚀 Initializing {get_version_info()} in {project_path}")
    
    try:
        # Create .sugar directory
        sugar_dir.mkdir(exist_ok=True)
        
        # Find Claude CLI
        claude_cmd = _find_claude_cli()
        if not claude_cmd:
            click.echo("⚠️ Claude CLI not found in PATH or standard locations")
            claude_cmd = "claude"
        else:
            click.echo(f"✅ Found Claude CLI: {claude_cmd}")
        
        # Detect GitHub CLI and repository
        github_config = _detect_github_config(project_path)
        if github_config['cli_available']:
            click.echo(f"✅ Found GitHub CLI: {github_config['gh_command']}")
            if github_config['repo']:
                click.echo(f"✅ Detected GitHub repository: {github_config['repo']}")
            if not github_config['authenticated']:
                click.echo("⚠️ GitHub CLI found but not authenticated. Run 'gh auth login' to enable GitHub integration.")
        else:
            click.echo("ℹ️ GitHub CLI not found. You can install it later for GitHub integration.")
        
        # Create default config
        config_content = _generate_default_config(claude_cmd, str(project_path), github_config)
        config_path = sugar_dir / 'config.yaml'
        
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # Create directories
        (sugar_dir / 'logs').mkdir(exist_ok=True)
        (sugar_dir / 'backups').mkdir(exist_ok=True)
        
        # Create logs/errors directory structure (for user's actual error logs)
        logs_dir = project_path / 'logs' / 'errors'  
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create .gitkeep to preserve directory structure but don't create sample files
        # that would be discovered as work items
        with open(logs_dir / '.gitkeep', 'w') as f:
            f.write('# This directory is monitored by Sugar for error logs\n')
        
        click.echo(f"✅ {get_version_info()} initialized successfully!")
        click.echo(f"📁 Config: {config_path}")
        click.echo(f"📁 Database: {sugar_dir / 'sugar.db'}")
        click.echo(f"📁 Logs: {sugar_dir / 'logs'}")
        click.echo("\n🎯 Next steps:")
        click.echo("1. Review and customize the config: .sugar/config.yaml")
        click.echo("2. Add tasks: sugar add 'Your first task'")
        click.echo("3. Start autonomous mode: sugar run")
        
    except Exception as e:
        click.echo(f"❌ Failed to initialize Sugar: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('title')
@click.option('--type', 'task_type', default='feature', type=click.Choice(['bug_fix', 'feature', 'test', 'refactor', 'documentation']), help='Type of task')
@click.option('--priority', default=3, type=click.IntRange(1, 5), help='Priority (1=low, 5=urgent)')
@click.option('--description', help='Detailed description of the task')
@click.option('--urgent', is_flag=True, help='Mark as urgent (priority 5)')
@click.pass_context
def add(ctx, title, task_type, priority, description, urgent):
    """Add a new task to Sugar work queue"""
    
    if urgent:
        priority = 5
    
    if not description:
        description = f"Task: {title}"
    
    # Import here to avoid circular imports
    from .storage.work_queue import WorkQueue
    import uuid
    
    try:
        config_file = ctx.obj['config']
        # Load config to get database path
        import yaml
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Initialize work queue
        work_queue = WorkQueue(config['sugar']['storage']['database'])
        
        # Create task data
        task_data = {
            'id': str(uuid.uuid4()),
            'type': task_type,
            'title': title,
            'description': description,
            'priority': priority,
            'status': 'pending',
            'source': 'cli',
            'context': {
                'added_via': 'sugar_cli',
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        
        # Add to queue
        asyncio.run(_add_task_async(work_queue, task_data))
        
        urgency = "🚨 URGENT" if urgent else f"Priority {priority}"
        click.echo(f"✅ Added {task_type} task: '{title}' ({urgency})")
        
    except Exception as e:
        click.echo(f"❌ Error adding task: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--status', type=click.Choice(['pending', 'active', 'completed', 'failed', 'all']), default='all', help='Filter by status')
@click.option('--limit', default=10, help='Number of tasks to show')
@click.option('--type', 'task_type', type=click.Choice(['bug_fix', 'feature', 'test', 'refactor', 'documentation', 'all']), default='all', help='Filter by type')
@click.pass_context
def list(ctx, status, limit, task_type):
    """List tasks in Sugar work queue"""
    
    from .storage.work_queue import WorkQueue
    import yaml
    
    try:
        config_file = ctx.obj['config']
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        work_queue = WorkQueue(config['sugar']['storage']['database'])
        
        # Get tasks
        tasks = asyncio.run(_list_tasks_async(work_queue, status, limit, task_type))
        
        if not tasks:
            click.echo(f"📭 No {status if status != 'all' else ''} tasks found")
            return
        
        click.echo(f"\n📋 {len(tasks)} Tasks ({status if status != 'all' else 'all statuses'}):")
        click.echo("=" * 60)
        
        for task in tasks:
            status_emoji = {
                'pending': '⏳',
                'active': '⚡',
                'completed': '✅',
                'failed': '❌'
            }.get(task['status'], '📄')
            
            priority_str = "🚨" if task['priority'] == 5 else f"P{task['priority']}"
            
            click.echo(f"{status_emoji} {priority_str} [{task['type']}] {task['title']}")
            if task.get('description') and len(task['description']) < 100:
                click.echo(f"   📝 {task['description']}")
            
            # Build info line with timing for completed/failed tasks
            info_parts = [
                f"🆔 {task['id']}",
                f"📅 {task['created_at']}",
                f"🔄 {task['attempts']} attempts"
            ]
            
            # Add timing information for completed/failed tasks
            if task['status'] in ['completed', 'failed']:
                if task.get('total_execution_time', 0) > 0:
                    info_parts.append(f"⏱️ {task['total_execution_time']:.1f}s")
                if task.get('total_elapsed_time', 0) > 0:
                    info_parts.append(f"🕐 {_format_duration(task['total_elapsed_time'])}")
            
            click.echo(f"   {' | '.join(info_parts)}")
            click.echo()
        
    except Exception as e:
        click.echo(f"❌ Error listing tasks: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('task_id')
@click.pass_context
def view(ctx, task_id):
    """View detailed information about a specific task"""
    
    from .storage.work_queue import WorkQueue
    import yaml
    
    try:
        config_file = ctx.obj['config']
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        work_queue = WorkQueue(config['sugar']['storage']['database'])
        
        # Get specific task
        task = asyncio.run(_get_task_by_id_async(work_queue, task_id))
        
        if not task:
            click.echo(f"❌ Task not found: {task_id}")
            return
        
        # Display detailed task information
        status_emoji = {
            'pending': '⏳',
            'active': '⚡',
            'completed': '✅',
            'failed': '❌'
        }.get(task['status'], '📄')
        
        priority_str = "🚨" if task['priority'] == 5 else f"P{task['priority']}"
        
        click.echo(f"\n📋 Task Details")
        click.echo("=" * 50)
        click.echo(f"{status_emoji} {priority_str} [{task['type']}] {task['title']}")
        click.echo(f"📝 Description: {task.get('description', 'No description')}")
        click.echo(f"🆔 ID: {task['id']}")
        click.echo(f"📅 Created: {task['created_at']}")
        click.echo(f"🔄 Attempts: {task['attempts']}")
        click.echo(f"📊 Status: {task['status']}")
        click.echo(f"🎯 Priority: {task['priority']}/5")
        click.echo(f"🏷️  Source: {task.get('source', 'unknown')}")
        
        # Display timing information
        if task.get('total_execution_time', 0) > 0:
            click.echo(f"⏱️  Execution Time: {task['total_execution_time']:.1f}s")
        if task.get('total_elapsed_time', 0) > 0:
            click.echo(f"🕐 Total Elapsed: {_format_duration(task['total_elapsed_time'])}")
        if task.get('started_at'):
            click.echo(f"🚀 Started: {task['started_at']}")
        
        if task.get('context'):
            click.echo(f"🔍 Context: {json.dumps(task['context'], indent=2)}")
        
        if task.get('result'):
            click.echo(f"📋 Result: {task['result']}")
            
        click.echo()
        
    except Exception as e:
        click.echo(f"❌ Error viewing task: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('task_id')
@click.pass_context
def remove(ctx, task_id):
    """Remove a task from the work queue"""
    
    from .storage.work_queue import WorkQueue
    import yaml
    
    try:
        config_file = ctx.obj['config']
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        work_queue = WorkQueue(config['sugar']['storage']['database'])
        
        # Remove the task
        success = asyncio.run(_remove_task_async(work_queue, task_id))
        
        if success:
            click.echo(f"✅ Removed task: {task_id}")
        else:
            click.echo(f"❌ Task not found: {task_id}")
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"❌ Error removing task: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('task_id')
@click.option('--title', help='Update task title')
@click.option('--description', help='Update task description')  
@click.option('--priority', type=click.IntRange(1, 5), help='Update priority (1-5)')
@click.option('--type', 'task_type', type=click.Choice(['bug_fix', 'feature', 'test', 'refactor', 'documentation']), help='Update task type')
@click.option('--status', type=click.Choice(['pending', 'active', 'completed', 'failed']), help='Update task status')
@click.pass_context
def update(ctx, task_id, title, description, priority, task_type, status):
    """Update an existing task"""
    
    from .storage.work_queue import WorkQueue
    import yaml
    
    if not any([title, description, priority, task_type, status]):
        click.echo("❌ No updates specified. Use --help to see available options.")
        sys.exit(1)
    
    try:
        config_file = ctx.obj['config']
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        work_queue = WorkQueue(config['sugar']['storage']['database'])
        
        # Build updates dictionary
        updates = {}
        if title:
            updates['title'] = title
        if description:
            updates['description'] = description
        if priority:
            updates['priority'] = priority
        if task_type:
            updates['type'] = task_type
        if status:
            updates['status'] = status
            
        updates['updated_at'] = datetime.utcnow().isoformat()
        
        # Update the task
        success = asyncio.run(_update_task_async(work_queue, task_id, updates))
        
        if success:
            click.echo(f"✅ Updated task: {task_id}")
            # Show updated task
            task = asyncio.run(_get_task_by_id_async(work_queue, task_id))
            if task:
                status_emoji = {
                    'pending': '⏳', 'active': '⚡', 'completed': '✅', 'failed': '❌'
                }.get(task['status'], '📄')
                priority_str = "🚨" if task['priority'] == 5 else f"P{task['priority']}"
                click.echo(f"{status_emoji} {priority_str} [{task['type']}] {task['title']}")
        else:
            click.echo(f"❌ Task not found: {task_id}")
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"❌ Error updating task: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--lines', '-n', default=50, help='Number of log lines to show')
@click.option('--follow', '-f', is_flag=True, help='Follow log output (like tail -f)')
@click.option('--level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']), help='Filter by log level')
@click.pass_context
def logs(ctx, lines, follow, level):
    """Show Sugar logs with debugging information"""
    import yaml
    
    try:
        config_file = ctx.obj['config']
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        log_file = config.get('sugar', {}).get('logging', {}).get('file', '.sugar/sugar.log')
        log_path = Path(log_file)
        
        if not log_path.exists():
            click.echo(f"❌ Log file not found: {log_path}")
            return
        
        if follow:
            click.echo(f"📋 Following Sugar logs (Ctrl+C to stop): {log_path}")
            click.echo("=" * 60)
            
            # Use tail -f equivalent
            import subprocess
            import sys
            
            cmd = ['tail', '-f']
            if lines != 50:
                cmd.extend(['-n', str(lines)])
            cmd.append(str(log_path))
            
            try:
                process = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)
                process.wait()
            except KeyboardInterrupt:
                process.terminate()
                click.echo("\n👋 Stopped following logs")
        else:
            click.echo(f"📋 Last {lines} lines from Sugar logs: {log_path}")
            click.echo("=" * 60)
            
            # Read last N lines
            with open(log_path, 'r') as f:
                log_lines = f.readlines()
            
            # Filter by level if specified
            if level:
                log_lines = [line for line in log_lines if f" - {level} - " in line]
            
            # Show last N lines
            for line in log_lines[-lines:]:
                click.echo(line.rstrip())
    
    except Exception as e:
        click.echo(f"❌ Error reading logs: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.pass_context
def debug(ctx):
    """Show debugging information about last Claude execution"""
    import yaml
    import os
    
    try:
        config_file = ctx.obj['config']
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check if session state exists
        context_file = config.get('sugar', {}).get('claude', {}).get('context_file', '.sugar/context.json')
        session_file = context_file.replace('.json', '_session.json')
        
        click.echo("🔍 Sugar Debug Information")
        click.echo("=" * 50)
        
        # Show session state
        if Path(session_file).exists():
            with open(session_file, 'r') as f:
                session_state = json.load(f)
            
            click.echo("📋 Last Session State:")
            click.echo(f"   Last execution: {session_state.get('last_execution_time', 'unknown')}")
            click.echo(f"   Task type: {session_state.get('last_task_type', 'unknown')}")
            click.echo(f"   Context strategy: {session_state.get('context_strategy', 'unknown')}")
            click.echo(f"   Execution count: {session_state.get('execution_count', 0)}")
            click.echo(f"   Simulated: {session_state.get('simulated', False)}")
            click.echo()
        else:
            click.echo("📋 No session state found (fresh start)")
            click.echo()
        
        # Show current context file
        if Path(context_file).exists():
            with open(context_file, 'r') as f:
                context = json.load(f)
            
            click.echo("📄 Current Context:")
            click.echo(f"   Continue session: {context.get('continue_session', False)}")
            click.echo(f"   Execution count: {context.get('execution_count', 0)}")
            click.echo(f"   Safety mode: {context.get('safety_mode', True)}")
            click.echo()
        else:
            click.echo("📄 No context file found")
            click.echo()
        
        # Show Claude CLI configuration
        claude_config = config.get('sugar', {}).get('claude', {})
        click.echo("🤖 Claude Configuration:")
        click.echo(f"   Command: {claude_config.get('command', 'unknown')}")
        click.echo(f"   Timeout: {claude_config.get('timeout', 'unknown')}s")
        click.echo(f"   Use continuous: {claude_config.get('use_continuous', True)}")
        click.echo(f"   Context strategy: {claude_config.get('context_strategy', 'project')}")
        click.echo()
        
        # Show working directory and key files
        click.echo("📁 Environment:")
        click.echo(f"   Working directory: {os.getcwd()}")
        click.echo(f"   Config file: {config_file}")
        click.echo(f"   Context file: {context_file}")
        click.echo(f"   Session file: {session_file}")
        click.echo()
        
        # Test Claude CLI availability
        claude_cmd = claude_config.get('command', 'claude')
        click.echo("🧪 Claude CLI Test:")
        try:
            import subprocess
            result = subprocess.run([claude_cmd, '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                click.echo(f"   ✅ Claude CLI working: {result.stdout.strip()}")
            else:
                click.echo(f"   ❌ Claude CLI error: {result.stderr.strip()}")
        except Exception as e:
            click.echo(f"   ❌ Claude CLI not found: {e}")
        click.echo()
        
        # Suggest next steps
        click.echo("💡 Debugging Tips:")
        click.echo("   • Use 'sugar logs -f' to follow live logs")
        click.echo("   • Use 'sugar logs --level DEBUG' to see detailed execution")
        click.echo("   • Check if Claude CLI works: claude --version")
        click.echo("   • Try dry run mode first: set dry_run: true in config")
        click.echo("   • Use 'sugar run --once --dry-run' to test execution")
        
    except Exception as e:
        click.echo(f"❌ Error getting debug info: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.pass_context  
def status(ctx):
    """Show Sugar system status and queue statistics"""
    
    from .storage.work_queue import WorkQueue
    import yaml
    
    try:
        config_file = ctx.obj['config']
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        work_queue = WorkQueue(config['sugar']['storage']['database'])
        
        # Get statistics
        stats = asyncio.run(_get_status_async(work_queue))
        
        click.echo("\n🤖 Sugar System Status")
        click.echo("=" * 40)
        click.echo(f"📊 Total Tasks: {stats['total']}")
        click.echo(f"⏳ Pending: {stats['pending']}")
        click.echo(f"⚡ Active: {stats['active']}")
        click.echo(f"✅ Completed: {stats['completed']}")
        click.echo(f"❌ Failed: {stats['failed']}")
        click.echo(f"📈 Recent (24h): {stats['recent_24h']}")
        
        # Show next few pending tasks
        next_tasks = asyncio.run(_get_next_tasks_async(work_queue, 3))
        if next_tasks:
            click.echo("\n🔜 Next Tasks:")
            click.echo("-" * 20)
            for task in next_tasks:
                priority_str = "🚨" if task['priority'] == 5 else f"P{task['priority']}"
                click.echo(f"{priority_str} [{task['type']}] {task['title']}")
        
        click.echo()
        
    except Exception as e:
        click.echo(f"❌ Error getting status: {e}", err=True)
        sys.exit(1)

@cli.command()  
def help():
    """Show comprehensive Sugar help and getting started guide"""
    
    click.echo("""
🤖 Sugar - AI-Powered Autonomous Development System
================================================

Sugar is an autonomous development system that works with Claude Code CLI to 
provide 24/7 development assistance through task discovery and execution.

📋 QUICK START
--------------
1. Initialize Sugar in your project:
   sugar init

2. Add your first task:
   sugar add "Implement user authentication" --type feature --priority 4

3. Test Sugar in safe mode:
   sugar run --dry-run --once

4. Start autonomous development:
   sugar run

🎯 WHAT SUGAR DOES
------------------
Sugar operates in TWO modes:

🤖 AUTONOMOUS DISCOVERY:
   • Discovers work from error logs, GitHub issues, code quality analysis
   • Analyzes test coverage gaps and suggests improvements  
   • Continuously monitors and adapts to your project needs

👤 MANUAL TASK MANAGEMENT:
   • Add specific tasks via CLI: sugar add "task description"
   • Set priorities and task types (bug_fix, feature, test, refactor, documentation)
   • Full control over work queue with sugar list, sugar view, sugar update

📚 CORE COMMANDS
----------------
sugar init              Initialize Sugar in current project
sugar add TITLE         Add new task to work queue
sugar list              List tasks (--status, --type, --limit options)
sugar view TASK_ID      Show detailed task information
sugar update TASK_ID    Update existing task (--title, --priority, etc.)
sugar remove TASK_ID    Remove task from queue
sugar status            Show system status and queue statistics
sugar run               Start autonomous development system
                        (--dry-run, --once, --validate options)

🔧 CONFIGURATION
----------------
Sugar uses .sugar/config.yaml for project-specific settings:
• Discovery sources (error logs, GitHub, code analysis)
• Claude CLI integration settings
• Safety controls and execution limits
• Task prioritization and scheduling

📁 PROJECT STRUCTURE
--------------------
your-project/
├── .sugar/                    Sugar configuration and data
│   ├── config.yaml           Project settings
│   ├── sugar.db             Task database  
│   └── sugar.log            Activity logs
└── logs/errors/             Error logs monitored by Sugar

🛡️ SAFETY FEATURES
-------------------
• Dry-run mode by default (no changes until you set dry_run: false)
• Path exclusions prevent system file modifications
• Timeout protection prevents runaway processes
• Project isolation - each project gets its own Sugar instance

⚠️  EXECUTION CONTEXT
---------------------
• Run Sugar OUTSIDE of Claude Code sessions (in regular terminal)
• Sugar calls Claude Code CLI as needed for task execution
• Architecture: Terminal → Sugar → Claude Code CLI
• Avoid: Claude Code → Sugar (recursive execution)

📖 DOCUMENTATION
----------------
Complete documentation: docs/README.md
• User Guide: docs/user/quick-start.md
• CLI Reference: docs/user/cli-reference.md
• Examples: docs/user/examples.md
• Troubleshooting: docs/user/troubleshooting.md
• Contributing: docs/dev/contributing.md

🆘 NEED HELP?
--------------
• Check troubleshooting guide: docs/user/troubleshooting.md
• GitHub Issues: https://github.com/cdnsteve/sugar/issues
• Email: contact@roboticforce.io

💡 TIPS
-------
• Start with 'sugar run --dry-run --once' to see what Sugar would do
• Monitor logs with 'tail -f .sugar/sugar.log'
• Use 'sugar status' to check queue health
• Each project needs its own 'sugar init'

Ready to supercharge your development workflow? 🚀
""")

@cli.command()
@click.option('--dry-run', is_flag=True, help='Run in simulation mode (override config)')
@click.option('--once', is_flag=True, help='Run one cycle and exit')
@click.option('--validate', is_flag=True, help='Validate configuration and exit')
@click.pass_context
def run(ctx, dry_run, once, validate):
    """
    Start Sugar - AI-powered autonomous development system
    
    A lightweight autonomous development system that:
    - Discovers work from error logs and feedback
    - Executes tasks using Claude Code CLI
    - Learns and adapts from results
    """
    global sugar_loop
    
    try:
        # Initialize Sugar
        config = ctx.obj['config']
        sugar_loop = SugarLoop(config)
        
        # Override dry_run if specified
        if dry_run:
            sugar_loop.config['sugar']['dry_run'] = True
            logger.info("🧪 Dry run mode enabled via command line")
        
        # Validation mode
        if validate:
            asyncio.run(validate_config(sugar_loop))
            return
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run Sugar
        if once:
            asyncio.run(run_once(sugar_loop))
        else:
            asyncio.run(run_continuous(sugar_loop))
            
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested by user")
    except Exception as e:
        logger.error(f"💥 Sugar crashed: {e}", exc_info=True)
        sys.exit(1)

async def validate_config(sugar_loop):
    """Validate configuration and dependencies"""
    logger.info("🔍 Validating Sugar configuration...")
    
    # Check config structure
    config = sugar_loop.config
    required_sections = ['sugar']
    
    for section in required_sections:
        if section not in config:
            logger.error(f"❌ Missing required config section: {section}")
            sys.exit(1)
    
    # Validate Claude CLI
    from .executor.claude_wrapper import ClaudeWrapper
    claude_wrapper = ClaudeWrapper(config['sugar']['claude'])
    
    if await claude_wrapper.validate_claude_cli():
        logger.info("✅ Claude CLI validation passed")
    else:
        logger.warning("⚠️ Claude CLI validation failed - dry run mode recommended")
    
    # Check discovery paths
    from .discovery.error_monitor import ErrorLogMonitor
    if config['sugar']['discovery']['error_logs']['enabled']:
        error_monitor = ErrorLogMonitor(config['sugar']['discovery']['error_logs'])
        health = await error_monitor.health_check()
        logger.info(f"📁 Discovery paths: {health['paths_accessible']}/{health['paths_configured']} accessible")
    
    # Initialize storage
    await sugar_loop.work_queue.initialize()
    queue_health = await sugar_loop.work_queue.health_check()
    logger.info(f"💾 Storage initialized: {queue_health['database_path']}")
    
    logger.info("✅ Configuration validation completed")

async def run_once(sugar_loop):
    """Run Sugar for one cycle and exit"""
    logger.info(f"🔄 Running {get_version_info()} for one cycle...")
    
    # Initialize
    await sugar_loop.work_queue.initialize()
    
    # Run discovery
    await sugar_loop._discover_work()
    
    # Execute work
    await sugar_loop._execute_work()
    
    # Process feedback
    await sugar_loop._process_feedback()
    
    # Show final stats
    stats = await sugar_loop.work_queue.get_stats()
    logger.info(f"📊 Final stats: {stats}")
    
    logger.info("✅ Single cycle completed")

async def run_continuous(sugar_loop):
    """Run Sugar continuously"""
    global shutdown_event
    shutdown_event = asyncio.Event()
    
    # Create PID file for stop command
    import pathlib
    import os
    config_dir = pathlib.Path(sugar_loop.config.get('sugar', {}).get('storage', {}).get('database', '.sugar/sugar.db')).parent
    config_dir.mkdir(exist_ok=True)
    pidfile = config_dir / "sugar.pid"
    
    try:
        with open(pidfile, 'w') as f:
            f.write(str(os.getpid()))
        
        logger.info(f"🚀 Starting {get_version_info()} in continuous mode...")
        logger.info("💡 Press Ctrl+C to stop Sugar gracefully")
        logger.info(f"💡 Or run 'sugar stop' from another terminal")
        
        await sugar_loop.start_with_shutdown(shutdown_event)
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown signal received")
    finally:
        logger.info("⏳ Stopping Sugar gracefully...")
        await sugar_loop.stop()
        
        # Clean up PID file
        if pidfile.exists():
            pidfile.unlink()
            
        logger.info("🏁 Sugar stopped")

# Async helper functions for CLI commands
async def _add_task_async(work_queue, task_data):
    """Helper to add task asynchronously"""
    await work_queue.initialize()
    task_id = await work_queue.add_work(task_data)
    return task_id

async def _list_tasks_async(work_queue, status_filter, limit, task_type_filter):
    """Helper to list tasks asynchronously"""
    await work_queue.initialize()
    
    if status_filter == 'all':
        status_filter = None
    
    tasks = await work_queue.get_recent_work(limit=limit, status=status_filter)
    
    # Filter by task type if specified
    if task_type_filter != 'all':
        tasks = [task for task in tasks if task['type'] == task_type_filter]
    
    return tasks

async def _get_status_async(work_queue):
    """Helper to get status asynchronously"""
    await work_queue.initialize()
    return await work_queue.get_stats()

async def _get_next_tasks_async(work_queue, limit):
    """Helper to get next pending tasks"""
    await work_queue.initialize()
    return await work_queue.get_recent_work(limit=limit, status='pending')

async def _get_task_by_id_async(work_queue, task_id):
    """Helper to get specific task by ID"""
    await work_queue.initialize()
    return await work_queue.get_work_by_id(task_id)

async def _remove_task_async(work_queue, task_id):
    """Helper to remove task by ID"""
    await work_queue.initialize()
    return await work_queue.remove_work(task_id)

async def _update_task_async(work_queue, task_id, updates):
    """Helper to update task by ID"""
    await work_queue.initialize()
    return await work_queue.update_work(task_id, updates)

def _detect_github_config(project_path: Path) -> dict:
    """Detect GitHub CLI availability and current repository configuration"""
    import subprocess
    import os
    
    github_config = {
        'detected': True,  # Mark that detection was attempted
        'cli_available': False,
        'gh_available': False,  # Keep for backward compatibility
        'gh_command': 'gh',
        'authenticated': False,
        'repo': '',
        'auth_method': 'auto'
    }
    
    try:
        # Check if GitHub CLI is available
        result = subprocess.run(['gh', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            github_config['cli_available'] = True
            github_config['gh_available'] = True  # Keep for backward compatibility
            
            # Check if authenticated
            auth_result = subprocess.run(['gh', 'auth', 'status'], capture_output=True, text=True, timeout=10)
            github_config['authenticated'] = auth_result.returncode == 0
            
            # Try to detect current repository
            try:
                # Change to project directory for repo detection
                original_cwd = os.getcwd()
                os.chdir(project_path)
                
                repo_result = subprocess.run(['gh', 'repo', 'view', '--json', 'nameWithOwner'], 
                                           capture_output=True, text=True, timeout=10)
                if repo_result.returncode == 0:
                    import json
                    repo_data = json.loads(repo_result.stdout)
                    github_config['repo'] = repo_data.get('nameWithOwner', '')
                
                # Restore original directory
                os.chdir(original_cwd)
                
            except Exception:
                # If repo detection fails, try git remote
                try:
                    os.chdir(project_path)
                    git_result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                              capture_output=True, text=True, timeout=5)
                    if git_result.returncode == 0:
                        remote_url = git_result.stdout.strip()
                        # Parse GitHub repository from remote URL
                        repo = _parse_github_repo_from_url(remote_url)
                        if repo:
                            github_config['repo'] = repo
                    os.chdir(original_cwd)
                except Exception:
                    os.chdir(original_cwd)
                    pass
                    
            # Set auth method based on availability
            if github_config['authenticated']:
                github_config['auth_method'] = 'gh_cli'
            else:
                github_config['auth_method'] = 'auto'
                
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    
    return github_config

def _parse_github_repo_from_url(url: str) -> str:
    """Parse GitHub repository name from remote URL"""
    import re
    
    # Handle both HTTPS and SSH URLs
    # HTTPS: https://github.com/owner/repo.git
    # SSH: git@github.com:owner/repo.git
    
    patterns = [
        r'github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$',
        r'github\.com/([^/]+/[^/]+?)(?:\.git)?/?$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return ''

def _find_claude_cli():
    """Find Claude CLI in standard locations"""
    # Try common paths
    possible_paths = [
        "claude",  # In PATH
        "/usr/local/bin/claude",
        "/opt/homebrew/bin/claude",
        Path.home() / ".claude" / "local" / "claude",
        Path.home() / ".local" / "bin" / "claude"
    ]
    
    for path in possible_paths:
        try:
            import subprocess
            result = subprocess.run([str(path), "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return str(path)
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
            continue
    
    return None

def _get_workflow_config_section() -> str:
    """Generate GitHub workflow configuration section"""
    return """
      # Label filtering options:
      # issue_labels: ["bug", "enhancement"]  # Specific labels to watch
      # issue_labels: []                      # No filtering - work on ALL open issues  
      # issue_labels: ["*"]                   # Work on issues with any labels (exclude unlabeled)
      # issue_labels: ["unlabeled"]           # Work only on issues without labels
      
      # Workflow settings for completed work
      workflow:
        # Auto-close issues after successful completion
        auto_close_issues: true
        
        # Git workflow: "direct_commit" or "pull_request"
        git_workflow: "direct_commit"  # direct_commit|pull_request
        
        # Branch settings (used when git_workflow: "pull_request")
        branch:
          # Auto-create feature branches for each issue
          create_branches: true
          # Branch naming pattern (variables: {issue_number}, {issue_title_slug})
          name_pattern: "sugar/issue-{issue_number}"
          # Base branch for new branches and PRs
          base_branch: "main"
          
        # Pull request settings (used when git_workflow: "pull_request")
        pull_request:
          # Auto-create PRs after completing work
          auto_create: true
          # Auto-merge PRs (only if all checks pass)
          auto_merge: false
          # PR title pattern (variables: same as branch naming)
          title_pattern: "Fix #{issue_number}: {issue_title}"
          # Include work summary in PR description
          include_work_summary: true
          
        # Commit settings
        commit:
          # Include issue reference in commit messages
          include_issue_ref: true
          # Commit message pattern (variables: {issue_number}, {work_summary})
          message_pattern: "Fix #{issue_number}: {work_summary}"
          # Auto-commit changes after completing work
          auto_commit: true"""

def _get_github_config_section(github_config: dict = None) -> str:
    """Generate GitHub configuration section based on detection results"""
    if not github_config or not github_config.get('detected'):
        # Default GitHub section when no detection attempted
        return f"""
      enabled: false  # Set to true and configure to enable
      repo: ""  # e.g., "user/repository"
      
      # Authentication method: "token", "gh_cli", or "auto"
      auth_method: "auto"  # Try gh CLI first, fallback to token
      
      # GitHub Personal Access Token (if using "token" method)
      token: ""  # Or set GITHUB_TOKEN environment variable
      
      # GitHub CLI integration (if using "gh_cli" method)  
      gh_cli:
        command: "gh"  # Path to gh command
        use_default_auth: true  # Use gh CLI's existing authentication
        
      # Discovery settings  
      issue_labels: []  # No filtering - work on ALL open issues
      check_interval_minutes: 30{_get_workflow_config_section()}"""
    
    if github_config.get('authenticated') and github_config.get('repo'):
        # GitHub CLI detected, authenticated, and repo found
        return f"""
      enabled: true  # GitHub CLI detected and authenticated
      repo: "{github_config['repo']}"  # Auto-detected from git remote
      
      # Authentication method: using GitHub CLI
      auth_method: "gh_cli"  # GitHub CLI is authenticated
      
      # GitHub CLI integration  
      gh_cli:
        command: "gh"  # GitHub CLI detected
        use_default_auth: true  # Using existing gh authentication
        
      # Discovery settings  
      issue_labels: []  # No filtering - work on ALL open issues
      check_interval_minutes: 30{_get_workflow_config_section()}"""
    
    elif github_config.get('cli_available'):
        repo_comment = f'# Auto-detected: "{github_config["repo"]}"' if github_config.get('repo') else '# Set to "owner/repository" format'
        auth_status = "# GitHub CLI detected but not authenticated - run 'gh auth login'"
        
        return f"""
      enabled: false  {auth_status}
      repo: "{github_config.get('repo', '')}"  {repo_comment}
      
      # Authentication method: GitHub CLI available but not authenticated
      auth_method: "gh_cli"  # GitHub CLI detected
      
      # GitHub CLI integration (run 'gh auth login' to authenticate)
      gh_cli:
        command: "gh"  # GitHub CLI detected
        use_default_auth: true  # Authenticate with 'gh auth login'
        
      # Discovery settings  
      issue_labels: []  # No filtering - work on ALL open issues
      check_interval_minutes: 30{_get_workflow_config_section()}"""
    
    else:
        # GitHub CLI not detected
        return f"""
      enabled: false  # GitHub CLI not detected - install or use token auth
      repo: ""  # e.g., "user/repository"
      
      # Authentication method: GitHub CLI not found
      auth_method: "auto"  # Install gh CLI or use token
      
      # GitHub Personal Access Token (alternative if gh CLI not available)
      token: ""  # Get from: https://github.com/settings/tokens
      
      # GitHub CLI integration (install GitHub CLI for best experience)
      gh_cli:
        command: "gh"  # Install with: brew install gh (macOS) or see github.com/cli/cli
        use_default_auth: true
        
      # Discovery settings  
      issue_labels: []  # No filtering - work on ALL open issues
      check_interval_minutes: 30{_get_workflow_config_section()}"""

def _generate_default_config(claude_cmd: str, project_root: str, github_config: dict = None) -> str:
    """Generate default Sugar configuration"""
    return f"""# Sugar Configuration for {Path(project_root).name}
sugar:
  # Core Loop Settings
  loop_interval: 300  # 5 minutes between cycles
  max_concurrent_work: 3  # Execute multiple tasks per cycle
  dry_run: true       # Start in safe mode - change to false when ready
  
  # Claude Code Integration
  claude:
    command: "{claude_cmd}"  # Auto-detected Claude CLI path
    timeout: 1800       # 30 minutes max per task
    context_file: ".sugar/context.json"
    
    # Structured Request System (Phase 1 of Agent Integration)
    use_structured_requests: true  # Enable structured JSON communication
    structured_input_file: ".sugar/claude_input.json"  # Temp file for complex inputs
    
    # Agent Selection System (Phase 2 of Agent Integration)
    enable_agents: true        # Enable Claude agent mode selection
    agent_fallback: true       # Fall back to basic Claude if agent fails
    agent_selection:           # Map work types to specific agents
      bug_fix: "tech-lead"           # Strategic analysis for bug fixes
      feature: "general-purpose"     # General development for features
      refactor: "code-reviewer"      # Code review expertise for refactoring
      test: "general-purpose"        # General development for tests
      documentation: "general-purpose"  # General development for docs
    
    # Dynamic Agent Discovery (supports any agents you have configured locally)
    # available_agents: []       # Optional: specify which agents are available
                                # If empty, Sugar will accept any agent name
                                # Example: ["my-custom-agent", "security-specialist", "database-expert"]
    # auto_discover_agents: false  # Future: auto-discover agents from Claude CLI
    
  # Work Discovery
  discovery:
    # Global exclusions for all discovery modules
    global_excluded_dirs: [
      "node_modules", ".git", "__pycache__", 
      "venv", ".venv", "env", ".env", "ENV", 
      "env.bak", "venv.bak", "virtualenv",
      "build", "dist", ".tox", ".nox",
      "coverage", "htmlcov", ".pytest_cache",
      ".sugar", ".claude"
    ]
    
    error_logs:
      enabled: true
      paths:
        - "logs/errors/"
        - "logs/feedback/"
        - ".sugar/logs/"
      patterns:
        - "*.json"
        - "*.log"
      max_age_hours: 24
    
    github:{_get_github_config_section(github_config)}
      
    code_quality:
      enabled: true
      root_path: "."  # Analyze current project
      file_extensions: [".py", ".js", ".ts", ".jsx", ".tsx"]
      excluded_dirs: [
        "node_modules", ".git", "__pycache__", 
        "venv", ".venv", "env", ".env", "ENV", 
        "env.bak", "venv.bak", "virtualenv",
        "build", "dist", ".tox", ".nox",
        "coverage", "htmlcov", ".pytest_cache",
        ".sugar", ".claude"
      ]
      max_files_per_scan: 50
      
    test_coverage:
      enabled: true
      root_path: "."  # Analyze current project
      source_dirs: ["src", "lib", "app", "api", "server"]
      test_dirs: ["tests", "test", "__tests__", "spec"]
      excluded_dirs: [
        "node_modules", ".git", "__pycache__", 
        "venv", ".venv", "env", ".env", "ENV", 
        "env.bak", "venv.bak", "virtualenv",
        "build", "dist", ".tox", ".nox",
        "coverage", "htmlcov", ".pytest_cache",
        ".sugar", ".claude"
      ]
      
  # Storage
  storage:
    database: ".sugar/sugar.db"  # Project-specific database
    backup_interval: 3600  # 1 hour
    
  # Safety
  safety:
    max_retries: 3
    excluded_paths:
      - "/System"
      - "/usr/bin"
      - "/etc"
      - ".sugar"
    
  # Logging
  logging:
    level: "INFO"
    file: ".sugar/sugar.log"  # Project-specific logs
    
  # Unified Workflow System
  workflow:
    # Workflow profiles: solo (fast), balanced (process), enterprise (governance)
    profile: "solo"  # Recommended for individual developers
    
    # Profile overrides (uncomment to customize beyond profiles)
    # custom:
    #   git:
    #     workflow_type: "direct_commit"  # direct_commit | pull_request
    #     commit_style: "conventional"    # conventional | simple
    #     auto_commit: true
    #   github:
    #     auto_create_issues: false       # Create GitHub issues for discovered work
    #     update_existing_issues: true    # Update issues from GitHub discovery
    #   discovery:
    #     handle_internally: true         # Keep test/quality improvements internal
"""

@cli.command()
@click.pass_context  
def stop(ctx):
    """Stop running Sugar instance gracefully"""
    import os
    import pathlib
    
    config_file = ctx.obj['config']
    config_dir = pathlib.Path(config_file).parent
    pidfile = config_dir / "sugar.pid"
    
    if not pidfile.exists():
        click.echo("❌ No running Sugar instance found")
        return
    
    try:
        with open(pidfile, 'r') as f:
            pid = int(f.read().strip())
        
        # Send SIGTERM for graceful shutdown
        os.kill(pid, signal.SIGTERM)
        click.echo(f"✅ Sent shutdown signal to Sugar process (PID: {pid})")
        
        # Wait a moment and check if process stopped
        import time
        time.sleep(2)
        
        try:
            # Check if process is still running
            os.kill(pid, 0)  # This will raise exception if process doesn't exist
            click.echo("⏳ Sugar is shutting down...")
        except ProcessLookupError:
            pidfile.unlink()  # Clean up pid file
            click.echo("🏁 Sugar stopped successfully")
            
    except (ValueError, ProcessLookupError):
        pidfile.unlink()  # Clean up stale pid file
        click.echo("❌ Stale PID file found and removed")
    except PermissionError:
        click.echo("❌ Permission denied - cannot stop Sugar process")
    except Exception as e:
        click.echo(f"❌ Error stopping Sugar: {e}")


@cli.command()
@click.option('--dry-run', is_flag=True, help='Show what would be removed without actually removing')
@click.pass_context
def dedupe(ctx, dry_run):
    """Remove duplicate work items based on source_file"""
    import aiosqlite
    from .storage.work_queue import WorkQueue
    import yaml
    
    async def _dedupe_work():
        config_file = ctx.obj['config']
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            
        work_queue = WorkQueue(config['sugar']['storage']['database'])
        await work_queue.initialize()
        
        async with aiosqlite.connect(work_queue.db_path) as db:
            # Find duplicates - keep the earliest created one for each source_file
            cursor = await db.execute("""
                WITH ranked_items AS (
                    SELECT id, source_file, title, created_at,
                           ROW_NUMBER() OVER (PARTITION BY source_file ORDER BY created_at ASC) as rn
                    FROM work_items 
                    WHERE source_file != '' AND source_file IS NOT NULL
                )
                SELECT id, source_file, title, created_at
                FROM ranked_items 
                WHERE rn > 1
                ORDER BY source_file, created_at
            """)
            
            duplicates = await cursor.fetchall()
            
            if not duplicates:
                click.echo("✅ No duplicate work items found")
                return
            
            click.echo(f"Found {len(duplicates)} duplicate work items:")
            click.echo("=" * 60)
            
            for work_id, source_file, title, created_at in duplicates:
                click.echo(f"🗑️  {work_id[:8]}... - {title}")
                click.echo(f"    Source: {source_file}")
                click.echo(f"    Created: {created_at}")
                click.echo()
            
            if dry_run:
                click.echo("🔍 Dry run mode - no items were removed")
                return
            
            # Remove duplicates
            if click.confirm(f"Remove {len(duplicates)} duplicate work items?"):
                duplicate_ids = [row[0] for row in duplicates]
                
                for work_id in duplicate_ids:
                    await db.execute("DELETE FROM work_items WHERE id = ?", (work_id,))
                
                await db.commit()
                click.echo(f"✅ Removed {len(duplicates)} duplicate work items")
            else:
                click.echo("❌ Operation cancelled")
    
    try:
        asyncio.run(_dedupe_work())
    except Exception as e:
        click.echo(f"❌ Error deduplicating work items: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--dry-run', is_flag=True, help='Show what would be removed without actually removing')
@click.pass_context
def cleanup(ctx, dry_run):
    """Remove bogus work items (Sugar initialization tests, venv files, etc.)"""
    import aiosqlite
    from .storage.work_queue import WorkQueue
    import yaml
    
    async def _cleanup_bogus_work():
        # Load configuration
        config_file = ctx.obj['config']
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Connect to database
        db_path = config['sugar']['storage']['database']
        async with aiosqlite.connect(db_path) as db:
            # Find bogus work items
            bogus_patterns = [
                "Sugar initialization test",
                "Sugar has been successfully initialized",
                "sugar_init_success.json",
                "init_test.json",
                "/venv/lib/",
                "/venv/site-packages/",
                "/.venv/lib/",
                "/node_modules/",
                "/__pycache__/"
            ]
            
            bogus_items = []
            for pattern in bogus_patterns:
                # Check title, description, and source_file
                query = """
                    SELECT id, title, source_file, created_at, status 
                    FROM work_items 
                    WHERE title LIKE ? 
                       OR description LIKE ?
                       OR source_file LIKE ?
                    ORDER BY created_at DESC
                """
                like_pattern = f"%{pattern}%"
                async with db.execute(query, (like_pattern, like_pattern, like_pattern)) as cursor:
                    rows = await cursor.fetchall()
                    bogus_items.extend(rows)
            
            # Remove duplicates (same ID)
            unique_bogus = {}
            for item in bogus_items:
                unique_bogus[item[0]] = item
            bogus_items = list(unique_bogus.values())
            
            if not bogus_items:
                click.echo("✅ No bogus work items found")
                return
            
            click.echo(f"Found {len(bogus_items)} potentially bogus work items:")
            click.echo("=" * 80)
            
            for work_id, title, source_file, created_at, status in bogus_items:
                status_icon = "⚡" if status == "active" else "✅" if status == "completed" else "⏳"
                click.echo(f"{status_icon} {work_id[:8]}... - {title}")
                if source_file:
                    click.echo(f"    Source: {source_file}")
                click.echo(f"    Created: {created_at} | Status: {status}")
                click.echo()
            
            if dry_run:
                click.echo("🔍 Dry run mode - no items were removed")
                return
            
            # Remove bogus items
            if click.confirm(f"Remove {len(bogus_items)} potentially bogus work items?"):
                bogus_ids = [row[0] for row in bogus_items]
                
                for work_id in bogus_ids:
                    await db.execute("DELETE FROM work_items WHERE id = ?", (work_id,))
                
                await db.commit()
                click.echo(f"✅ Removed {len(bogus_items)} bogus work items")
                
                # Also clean up the old init_test.json if it exists
                import pathlib
                project_path = pathlib.Path.cwd()
                old_test_file = project_path / 'logs' / 'errors' / 'init_test.json'
                if old_test_file.exists():
                    old_test_file.unlink()
                    click.echo("🗑️  Removed old init_test.json file")
                    
            else:
                click.echo("❌ Operation cancelled")
    
    try:
        asyncio.run(_cleanup_bogus_work())
    except Exception as e:
        click.echo(f"❌ Error cleaning up bogus work items: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()