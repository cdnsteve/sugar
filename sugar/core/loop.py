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
    
    async def _discover_work(self):
        """Discover new work from all enabled sources"""
        logger.info("🔍 Discovering work...")
        
        discovered_work = []
        
        for module in self.discovery_modules:
            try:
                work_items = await module.discover()
                discovered_work.extend(work_items)
                logger.info(f"📋 {module.__class__.__name__} found {len(work_items)} work items")
            except Exception as e:
                logger.error(f"Error in {module.__class__.__name__}: {e}")
        
        # Add discovered work to queue
        for work_item in discovered_work:
            await self.work_queue.add_work(work_item)
        
        if discovered_work:
            logger.info(f"➕ Added {len(discovered_work)} new work items to queue")
        else:
            logger.info("📭 No new work discovered this cycle")
    
    async def _execute_work(self):
        """Execute the highest priority work item"""
        max_concurrent = self.config['sugar']['max_concurrent_work']
        
        for _ in range(max_concurrent):
            work_item = await self.work_queue.get_next_work()
            if not work_item:
                logger.info("📭 No work items ready for execution")
                break
            
            logger.info(f"⚡ Executing work: {work_item['title']}")
            
            try:
                # Execute with Claude Code
                result = await self.claude_executor.execute_work(work_item)
                
                # Update work item with result
                await self.work_queue.complete_work(work_item['id'], result)
                
                logger.info(f"✅ Work completed: {work_item['title']}")
                
            except Exception as e:
                logger.error(f"❌ Work execution failed: {e}")
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
    
    async def health_check(self) -> dict:
        """Return system health status"""
        return {
            "status": "running" if self.running else "stopped",
            "queue_stats": await self.work_queue.get_stats(),
            "last_cycle": datetime.utcnow().isoformat(),
            "discovery_modules": len(self.discovery_modules),
            "config_loaded": bool(self.config)
        }