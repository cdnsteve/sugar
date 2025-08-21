#!/usr/bin/env python3
"""
CCAL Main Entry Point - Start the Claude Code Autonomous Loop
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path
import click
from datetime import datetime

from .core.loop import CCLALoop

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ccal.log')
    ]
)

logger = logging.getLogger(__name__)

# Global variable to hold the loop instance
ccal_loop = None

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down...")
    if ccal_loop:
        asyncio.create_task(ccal_loop.stop())

@click.group()
@click.option('--config', default='.ccal/config.yaml', help='Configuration file path')
@click.pass_context
def cli(ctx, config):
    """CCAL - Claude Code Autonomous Loop
    
    A lightweight autonomous development system that works with Claude Code CLI
    """
    ctx.ensure_object(dict)
    ctx.obj['config'] = config

@cli.command()
@click.option('--project-dir', default='.', help='Project directory to initialize CCAL in')
def init(project_dir):
    """Initialize CCAL in a project directory"""
    import shutil
    import json
    
    project_path = Path(project_dir).resolve()
    ccal_dir = project_path / '.ccal'
    
    click.echo(f"🚀 Initializing CCAL in {project_path}")
    
    try:
        # Create .ccal directory
        ccal_dir.mkdir(exist_ok=True)
        
        # Find Claude CLI
        claude_cmd = _find_claude_cli()
        if not claude_cmd:
            click.echo("⚠️ Claude CLI not found in PATH or standard locations")
            claude_cmd = "claude"
        else:
            click.echo(f"✅ Found Claude CLI: {claude_cmd}")
        
        # Create default config
        config_content = _generate_default_config(claude_cmd, str(project_path))
        config_path = ccal_dir / 'config.yaml'
        
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # Create directories
        (ccal_dir / 'logs').mkdir(exist_ok=True)
        (ccal_dir / 'backups').mkdir(exist_ok=True)
        
        # Create sample error log for testing
        logs_dir = project_path / 'logs' / 'errors'
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        sample_error = {
            "timestamp": datetime.utcnow().isoformat(),
            "error": "CCAL initialization test",
            "description": "Sample error log to test CCAL discovery",
            "component": "ccal_init",
            "message": "CCAL has been successfully initialized in this project"
        }
        
        with open(logs_dir / 'init_test.json', 'w') as f:
            json.dump(sample_error, f, indent=2)
        
        click.echo(f"✅ CCAL initialized successfully!")
        click.echo(f"📁 Config: {config_path}")
        click.echo(f"📁 Database: {ccal_dir / 'ccal.db'}")
        click.echo(f"📁 Logs: {ccal_dir / 'logs'}")
        click.echo("\n🎯 Next steps:")
        click.echo("1. Review and customize the config: .ccal/config.yaml")
        click.echo("2. Add tasks: ccal add 'Your first task'")
        click.echo("3. Start autonomous mode: ccal run")
        
    except Exception as e:
        click.echo(f"❌ Failed to initialize CCAL: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('title')
@click.option('--type', 'task_type', default='feature', type=click.Choice(['bug_fix', 'feature', 'test', 'refactor', 'documentation']), help='Type of task')
@click.option('--priority', default=3, type=click.IntRange(1, 5), help='Priority (1=low, 5=urgent)')
@click.option('--description', help='Detailed description of the task')
@click.option('--urgent', is_flag=True, help='Mark as urgent (priority 5)')
@click.pass_context
def add(ctx, title, task_type, priority, description, urgent):
    """Add a new task to CCAL work queue"""
    
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
        work_queue = WorkQueue(config['ccal']['storage']['database'])
        
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
                'added_via': 'ccal_cli',
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
    """List tasks in CCAL work queue"""
    
    from .storage.work_queue import WorkQueue
    import yaml
    
    try:
        config_file = ctx.obj['config']
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        work_queue = WorkQueue(config['ccal']['storage']['database'])
        
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
            click.echo(f"   📅 {task['created_at']} | 🔄 {task['attempts']} attempts")
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
        
        work_queue = WorkQueue(config['ccal']['storage']['database'])
        
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
        
        work_queue = WorkQueue(config['ccal']['storage']['database'])
        
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
        
        work_queue = WorkQueue(config['ccal']['storage']['database'])
        
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
@click.pass_context  
def status(ctx):
    """Show CCAL system status and queue statistics"""
    
    from .storage.work_queue import WorkQueue
    import yaml
    
    try:
        config_file = ctx.obj['config']
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        work_queue = WorkQueue(config['ccal']['storage']['database'])
        
        # Get statistics
        stats = asyncio.run(_get_status_async(work_queue))
        
        click.echo("\n🤖 CCAL System Status")
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
@click.option('--dry-run', is_flag=True, help='Run in simulation mode (override config)')
@click.option('--once', is_flag=True, help='Run one cycle and exit')
@click.option('--validate', is_flag=True, help='Validate configuration and exit')
@click.pass_context
def run(ctx, dry_run, once, validate):
    """
    Start the Claude Code Autonomous Loop (CCAL)
    
    A lightweight autonomous development system that:
    - Discovers work from error logs and feedback
    - Executes tasks using Claude Code CLI
    - Learns and adapts from results
    """
    global ccal_loop
    
    try:
        # Initialize CCAL
        config = ctx.obj['config']
        ccal_loop = CCLALoop(config)
        
        # Override dry_run if specified
        if dry_run:
            ccal_loop.config['ccal']['dry_run'] = True
            logger.info("🧪 Dry run mode enabled via command line")
        
        # Validation mode
        if validate:
            asyncio.run(validate_config(ccal_loop))
            return
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run CCAL
        if once:
            asyncio.run(run_once(ccal_loop))
        else:
            asyncio.run(run_continuous(ccal_loop))
            
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested by user")
    except Exception as e:
        logger.error(f"💥 CCAL crashed: {e}", exc_info=True)
        sys.exit(1)

async def validate_config(ccal_loop):
    """Validate configuration and dependencies"""
    logger.info("🔍 Validating CCAL configuration...")
    
    # Check config structure
    config = ccal_loop.config
    required_sections = ['ccal']
    
    for section in required_sections:
        if section not in config:
            logger.error(f"❌ Missing required config section: {section}")
            sys.exit(1)
    
    # Validate Claude CLI
    from .executor.claude_wrapper import ClaudeWrapper
    claude_wrapper = ClaudeWrapper(config['ccal']['claude'])
    
    if await claude_wrapper.validate_claude_cli():
        logger.info("✅ Claude CLI validation passed")
    else:
        logger.warning("⚠️ Claude CLI validation failed - dry run mode recommended")
    
    # Check discovery paths
    from .discovery.error_monitor import ErrorLogMonitor
    if config['ccal']['discovery']['error_logs']['enabled']:
        error_monitor = ErrorLogMonitor(config['ccal']['discovery']['error_logs'])
        health = await error_monitor.health_check()
        logger.info(f"📁 Discovery paths: {health['paths_accessible']}/{health['paths_configured']} accessible")
    
    # Initialize storage
    await ccal_loop.work_queue.initialize()
    queue_health = await ccal_loop.work_queue.health_check()
    logger.info(f"💾 Storage initialized: {queue_health['database_path']}")
    
    logger.info("✅ Configuration validation completed")

async def run_once(ccal_loop):
    """Run CCAL for one cycle and exit"""
    logger.info("🔄 Running CCAL for one cycle...")
    
    # Initialize
    await ccal_loop.work_queue.initialize()
    
    # Run discovery
    await ccal_loop._discover_work()
    
    # Execute work
    await ccal_loop._execute_work()
    
    # Process feedback
    await ccal_loop._process_feedback()
    
    # Show final stats
    stats = await ccal_loop.work_queue.get_stats()
    logger.info(f"📊 Final stats: {stats}")
    
    logger.info("✅ Single cycle completed")

async def run_continuous(ccal_loop):
    """Run CCAL continuously"""
    logger.info("🚀 Starting CCAL in continuous mode...")
    
    try:
        await ccal_loop.start()
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown signal received")
    finally:
        await ccal_loop.stop()
        logger.info("🏁 CCAL stopped")

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

def _generate_default_config(claude_cmd: str, project_root: str) -> str:
    """Generate default CCAL configuration"""
    return f"""# CCAL Configuration for {Path(project_root).name}
ccal:
  # Core Loop Settings
  loop_interval: 300  # 5 minutes between cycles
  max_concurrent_work: 3  # Execute multiple tasks per cycle
  dry_run: true       # Start in safe mode - change to false when ready
  
  # Claude Code Integration
  claude:
    command: "{claude_cmd}"  # Auto-detected Claude CLI path
    timeout: 1800       # 30 minutes max per task
    context_file: ".ccal/context.json"
    
  # Work Discovery
  discovery:
    error_logs:
      enabled: true
      paths:
        - "logs/errors/"
        - "logs/feedback/"
        - ".ccal/logs/"
      patterns:
        - "*.json"
        - "*.log"
      max_age_hours: 24
    
    github:
      enabled: false  # Set to true and configure to enable
      repo: ""  # e.g., "user/repository"
      token: ""  # GitHub token for API access
      
    code_quality:
      enabled: true
      root_path: "."  # Analyze current project
      file_extensions: [".py", ".js", ".ts", ".jsx", ".tsx"]
      excluded_dirs: ["node_modules", ".git", "__pycache__", "venv", ".venv", ".ccal"]
      max_files_per_scan: 50
      
    test_coverage:
      enabled: true
      root_path: "."  # Analyze current project
      source_dirs: ["src", "lib", "app", "api", "server"]
      test_dirs: ["tests", "test", "__tests__", "spec"]
      
  # Storage
  storage:
    database: ".ccal/ccal.db"  # Project-specific database
    backup_interval: 3600  # 1 hour
    
  # Safety
  safety:
    max_retries: 3
    excluded_paths:
      - "/System"
      - "/usr/bin"
      - "/etc"
      - ".ccal"
    
  # Logging
  logging:
    level: "INFO"
    file: ".ccal/ccal.log"  # Project-specific logs
"""

if __name__ == "__main__":
    cli()