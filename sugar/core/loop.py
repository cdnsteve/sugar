"""
Sugar Core Loop - The heart of autonomous development
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List
import yaml
from pathlib import Path

from ..discovery.error_monitor import ErrorLogMonitor
from ..discovery.github_watcher import GitHubWatcher
from ..discovery.code_quality import CodeQualityScanner
from ..discovery.test_coverage import TestCoverageAnalyzer
from ..executor.claude_wrapper import ClaudeWrapper
from ..storage.work_queue import WorkQueue
from ..learning.feedback_processor import FeedbackProcessor
from ..learning.adaptive_scheduler import AdaptiveScheduler

logger = logging.getLogger(__name__)

class SugarLoop:
    """Sugar - AI-powered autonomous development system - Main orchestrator"""
    
    def __init__(self, config_path: str = ".sugar/config.yaml"):
        self.config = self._load_config(config_path)
        self.running = False
        self.work_queue = WorkQueue(self.config['sugar']['storage']['database'])
        # Pass the full config so ClaudeWrapper can access dry_run setting
        claude_config = self.config['sugar']['claude'].copy()
        claude_config['dry_run'] = self.config['sugar']['dry_run']
        self.claude_executor = ClaudeWrapper(claude_config)
        
        # Initialize learning components
        self.feedback_processor = FeedbackProcessor(self.work_queue)
        self.adaptive_scheduler = AdaptiveScheduler(self.work_queue, self.feedback_processor)
        
        # Initialize work discovery modules
        self.discovery_modules = []
        
        # Error log monitoring
        if self.config['sugar']['discovery']['error_logs']['enabled']:
            error_monitor = ErrorLogMonitor(self.config['sugar']['discovery']['error_logs'])
            error_monitor.work_queue = self.work_queue  # Pass work_queue reference
            self.discovery_modules.append(error_monitor)
        
        # GitHub integration
        if self.config['sugar']['discovery'].get('github', {}).get('enabled', False):
            self.discovery_modules.append(
                GitHubWatcher(self.config['sugar']['discovery']['github'])
            )
        
        # Code quality scanning
        if self.config['sugar']['discovery'].get('code_quality', {}).get('enabled', True):
            quality_config = self.config['sugar']['discovery'].get('code_quality', {})
            quality_config.setdefault('root_path', '.')
            self.discovery_modules.append(
                CodeQualityScanner(quality_config)
            )
        
        # Test coverage analysis
        if self.config['sugar']['discovery'].get('test_coverage', {}).get('enabled', True):
            coverage_config = self.config['sugar']['discovery'].get('test_coverage', {})
            coverage_config.setdefault('root_path', '.')
            self.discovery_modules.append(
                TestCoverageAnalyzer(coverage_config)
            )
    
    def _load_config(self, config_path: str) -> dict:
        """Load Sugar configuration"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML config: {e}")
            raise
    
    async def start(self):
        """Start the autonomous loop"""
        logger.info("🤖 Starting Sugar - AI-powered autonomous development system")
        
        # Initialize storage
        await self.work_queue.initialize()
        
        self.running = True
        
        # Start main loop
        await self._main_loop()
    
    async def start_with_shutdown(self, shutdown_event):
        """Start the autonomous loop with shutdown event monitoring"""
        logger.info("🤖 Starting Sugar - AI-powered autonomous development system")
        
        # Initialize storage
        await self.work_queue.initialize()
        
        self.running = True
        
        # Start main loop with shutdown monitoring
        await self._main_loop_with_shutdown(shutdown_event)
    
    async def stop(self):
        """Stop the autonomous loop gracefully"""
        logger.info("🛑 Stopping Sugar...")
        self.running = False
    
    async def _main_loop(self):
        """Main autonomous development loop"""
        loop_interval = self.config['sugar']['loop_interval']
        
        while self.running:
            try:
                cycle_start = datetime.utcnow()
                logger.info(f"🔄 Starting Sugar cycle at {cycle_start}")
                
                # Phase 1: Discover new work
                await self._discover_work()
                
                # Phase 2: Execute highest priority work
                await self._execute_work()
                
                # Phase 3: Process results and learn
                await self._process_feedback()
                
                # Wait for next cycle
                cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
                sleep_time = max(0, loop_interval - cycle_duration)
                
                logger.info(f"✅ Cycle completed in {cycle_duration:.1f}s, sleeping {sleep_time:.1f}s")
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _main_loop_with_shutdown(self, shutdown_event):
        """Main autonomous development loop with shutdown event monitoring"""
        loop_interval = self.config['sugar']['loop_interval']
        
        while self.running and not shutdown_event.is_set():
            try:
                cycle_start = datetime.utcnow()
                logger.info(f"🔄 Starting Sugar cycle at {cycle_start}")
                
                # Phase 1: Discover new work
                await self._discover_work()
                
                # Check for shutdown before execution
                if shutdown_event.is_set():
                    logger.info("🛑 Shutdown requested, finishing current cycle...")
                    break
                
                # Phase 2: Execute highest priority work
                await self._execute_work()
                
                # Check for shutdown after execution
                if shutdown_event.is_set():
                    logger.info("🛑 Shutdown requested, finishing current cycle...")
                    break
                
                # Phase 3: Process results and learn
                await self._process_feedback()
                
                # Wait for next cycle or shutdown
                cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
                sleep_time = max(0, loop_interval - cycle_duration)
                
                logger.info(f"✅ Cycle completed in {cycle_duration:.1f}s, sleeping {sleep_time:.1f}s")
                
                # Sleep with periodic shutdown checks
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=sleep_time)
                    # If we get here, shutdown was requested
                    logger.info("🛑 Shutdown requested during sleep")
                    break
                except asyncio.TimeoutError:
                    # Normal timeout, continue to next cycle
                    pass
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                # Even during error recovery, check for shutdown
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=60)
                    logger.info("🛑 Shutdown requested during error recovery")
                    break
                except asyncio.TimeoutError:
                    pass
    
    async def _discover_work(self):
        """Discover new work from all enabled sources"""
        logger.debug("🔍 Discovering work...")
        
        discovered_work = []
        
        for module in self.discovery_modules:
            try:
                work_items = await module.discover()
                discovered_work.extend(work_items)
                logger.debug(f"📋 {module.__class__.__name__} found {len(work_items)} work items")
            except Exception as e:
                logger.error(f"Error in {module.__class__.__name__}: {e}")
        
        # Add discovered work to queue (with deduplication)
        added_count = 0
        skipped_count = 0
        
        for work_item in discovered_work:
            source_file = work_item.get('source_file', '')
            
            # Check if work item already exists (skip failed items for retry)
            if source_file and await self.work_queue.work_exists(source_file):
                skipped_count += 1
                logger.debug(f"⏭️ Skipping duplicate work item: {work_item['title']}")
                continue
            
            await self.work_queue.add_work(work_item)
            added_count += 1
        
        if added_count > 0:
            logger.info(f"➕ Added {added_count} new work items to queue")
        if skipped_count > 0:
            logger.info(f"⏭️ Skipped {skipped_count} duplicate work items")
        if added_count == 0 and skipped_count == 0:
            logger.info("📭 No new work discovered this cycle")
    
    async def _execute_work(self):
        """Execute the highest priority work item"""
        max_concurrent = self.config['sugar']['max_concurrent_work']
        
        for _ in range(max_concurrent):
            work_item = await self.work_queue.get_next_work()
            if not work_item:
                logger.info("📭 No work items ready for execution")
                break
            
            logger.info(f"⚡ Executing work [{work_item['id']}]: {work_item['title']}")
            
            try:
                # Execute with Claude Code
                result = await self.claude_executor.execute_work(work_item)
                
                # Update work item with result
                await self.work_queue.complete_work(work_item['id'], result)
                
                # Comment on GitHub issue if this work came from GitHub
                await self._comment_on_github_issue(work_item, result)
                
                logger.info(f"✅ Work completed [{work_item['id']}]: {work_item['title']}")
                
            except Exception as e:
                logger.error(f"❌ Work execution failed [{work_item['id']}]: {e}")
                await self.work_queue.fail_work(work_item['id'], str(e))
    
    async def _process_feedback(self):
        """Process execution results and learn from them"""
        try:
            # Process feedback and generate insights
            insights = await self.feedback_processor.process_feedback()
            
            # Apply adaptive changes based on learning
            adaptations = await self.adaptive_scheduler.adapt_system_behavior()
            
            # Log learning summary
            stats = await self.work_queue.get_stats()
            logger.info(f"📊 Queue stats: {stats['pending']} pending, "
                       f"{stats['completed']} completed, {stats['failed']} failed")
            
            if insights.get('recommendations'):
                rec_count = len(insights['recommendations'])
                logger.info(f"🧠 Generated {rec_count} recommendations for system improvement")
            
            if adaptations:
                adapt_count = len(adaptations)
                logger.info(f"🎯 Applied {adapt_count} adaptive improvements")
                
        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
    
    async def _comment_on_github_issue(self, work_item: dict, result: dict):
        """Comment on GitHub issue if work item originated from GitHub"""
        try:
            # Check if this work came from GitHub
            if (work_item.get('source') != 'github_watcher' or 
                not work_item.get('context', {}).get('github_issue')):
                return
            
            # Find GitHub watcher module
            github_watcher = None
            for module in self.discovery_modules:
                if isinstance(module, GitHubWatcher):
                    github_watcher = module
                    break
            
            if not github_watcher or not github_watcher.enabled:
                logger.debug("GitHub watcher not available for commenting")
                return
            
            # Extract issue details
            github_issue = work_item['context']['github_issue']
            issue_number = github_issue.get('number')
            
            if not issue_number:
                logger.warning("No issue number found in GitHub work item")
                return
            
            # Create comment body
            comment_body = self._format_completion_comment(work_item, result)
            
            # Post comment
            success = await github_watcher.comment_on_issue(issue_number, comment_body)
            
            if success:
                logger.info(f"💬 Posted completion comment to GitHub issue #{issue_number} for task [{work_item['id']}]")
            else:
                logger.warning(f"Failed to comment on GitHub issue #{issue_number}")
                
        except Exception as e:
            logger.error(f"Error commenting on GitHub issue: {e}")
    
    def _format_completion_comment(self, work_item: dict, result: dict) -> str:
        """Format concise completion comment for GitHub issue"""
        task_id = work_item.get('id', 'unknown')[:8]
        
        # Extract the most important information concisely
        lines = [
            f"## ✅ Issue Resolved (`{task_id}...`)",
            ""
        ]
        
        # Add concise summary from Claude's response or actions
        summary = self._extract_concise_summary(result)
        if summary:
            lines.extend([
                summary,
                ""
            ])
        
        # Add files changed if available (most important info)
        if result.get('files_changed'):
            lines.extend([
                f"**Files updated:** {', '.join(f'`{file}`' for file in result['files_changed'])}",
                ""
            ])
        
        # Add key actions in bullet format
        if result.get('actions_taken'):
            key_actions = [action.lstrip('✅✓ ').strip() for action in result['actions_taken'][:3]]
            if key_actions:
                lines.extend([
                    "**Changes made:**",
                    *[f"- {action}" for action in key_actions if action],
                    ""
                ])
        
        # Execution details in compact format
        exec_time = result.get('execution_time', 0)
        lines.append(f"*Completed in {exec_time:.1f}s by [Sugar AI](https://github.com/cdnsteve/sugar)*")
        
        return "\n".join(lines)
    
    def _extract_concise_summary(self, result: dict) -> str:
        """Extract a concise summary from Claude's output"""
        # Try to get Claude's actual response first
        claude_response = result.get('claude_response', '')
        
        # Look for summary patterns in Claude's response
        if claude_response:
            lines = claude_response.split('\n')
            for line in lines:
                line = line.strip()
                # Find lines that summarize what was done
                if any(word in line.lower() for word in ['successfully', 'completed', 'updated', 'added', 'fixed', 'created']):
                    if len(line) > 10 and len(line) < 200:  # Good summary length
                        return line.rstrip('.')
        
        # Fallback to summary field
        summary = result.get('summary', '')
        if summary and len(summary) < 200:
            return summary.rstrip('.')
        
        # Fallback to first meaningful action
        actions = result.get('actions_taken', [])
        if actions:
            first_action = actions[0].lstrip('✅✓ ').strip()
            if len(first_action) < 200:
                return first_action.rstrip('.')
        
        return "Task completed successfully"

    async def health_check(self) -> dict:
        """Return system health status"""
        return {
            "status": "running" if self.running else "stopped",
            "queue_stats": await self.work_queue.get_stats(),
            "last_cycle": datetime.utcnow().isoformat(),
            "discovery_modules": len(self.discovery_modules),
            "config_loaded": bool(self.config)
        }