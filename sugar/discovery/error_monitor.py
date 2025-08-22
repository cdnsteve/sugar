"""
Error Log Monitor - Discover work by analyzing error logs and feedback
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import glob
import os

logger = logging.getLogger(__name__)

class ErrorLogMonitor:
    """Monitor error logs and feedback to discover bug fix tasks"""
    
    def __init__(self, config: dict):
        self.config = config
        self.paths = config['paths']
        self.patterns = config['patterns']
        self.max_age_hours = config['max_age_hours']
        self.processed_files = set()  # Track processed files to avoid duplicates
        self.work_queue = None  # Will be set by the main loop
    
    async def discover(self) -> List[Dict[str, Any]]:
        """Discover work items from error logs"""
        work_items = []
        
        # Get files that already have active tasks to avoid duplicates
        active_files = await self._get_active_task_files() if self.work_queue else set()
        
        for path in self.paths:
            if not os.path.exists(path):
                logger.debug(f"Path does not exist: {path}")
                continue
                
            for pattern in self.patterns:
                file_pattern = os.path.join(path, pattern)
                files = glob.glob(file_pattern)
                
                for file_path in files:
                    try:
                        # Skip if file already has active tasks or was recently processed
                        if (file_path in active_files or 
                            file_path in self.processed_files or
                            not self._is_file_recent(file_path)):
                            continue
                            
                        items = await self._process_log_file(file_path)
                        work_items.extend(items)
                        self.processed_files.add(file_path)
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {e}")
        
        # If no work found, generate simple maintenance tasks
        if not work_items:
            work_items = await self._generate_maintenance_tasks()
        
        logger.debug(f"🔍 ErrorLogMonitor discovered {len(work_items)} work items")
        return work_items
    
    def _is_file_recent(self, file_path: str) -> bool:
        """Check if file is recent enough to process"""
        try:
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            cutoff_time = datetime.now() - timedelta(hours=self.max_age_hours)
            return file_mtime > cutoff_time
        except Exception as e:
            logger.error(f"Error checking file age for {file_path}: {e}")
            return False
    
    async def _process_log_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Process a single log file and extract work items"""
        work_items = []
        
        try:
            if file_path.endswith('.json'):
                work_items = await self._process_json_log(file_path)
            else:
                work_items = await self._process_text_log(file_path)
        except Exception as e:
            logger.error(f"Error processing log file {file_path}: {e}")
        
        return work_items
    
    async def _process_json_log(self, file_path: str) -> List[Dict[str, Any]]:
        """Process JSON log files (like feedback logs)"""
        work_items = []
        
        try:
            with open(file_path, 'r') as f:
                log_data = json.load(f)
            
            # Handle different JSON log formats
            if isinstance(log_data, dict):
                work_item = self._create_work_item_from_json(log_data, file_path)
                if work_item:
                    work_items.append(work_item)
            elif isinstance(log_data, list):
                for entry in log_data:
                    work_item = self._create_work_item_from_json(entry, file_path)
                    if work_item:
                        work_items.append(work_item)
                        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error reading JSON file {file_path}: {e}")
        
        return work_items
    
    def _create_work_item_from_json(self, log_entry: dict, source_file: str) -> Dict[str, Any]:
        """Create a work item from a JSON log entry"""
        
        # Look for error indicators
        error_indicators = ['error', 'exception', 'failed', 'bug', 'issue']
        feedback_indicators = ['feedback', 'improvement', 'suggestion', 'request']
        
        entry_text = json.dumps(log_entry).lower()
        
        # Determine work item type and priority
        work_type = 'bug_fix'
        priority = 3
        
        if any(indicator in entry_text for indicator in error_indicators):
            work_type = 'bug_fix'
            priority = 4  # High priority for errors
        elif any(indicator in entry_text for indicator in feedback_indicators):
            work_type = 'feature'
            priority = 2  # Lower priority for feature requests
        
        # Extract meaningful information
        title = self._extract_title_from_json(log_entry)
        description = self._extract_description_from_json(log_entry)
        
        if not title and not description:
            return None  # Skip if we can't extract meaningful information
        
        work_item = {
            'type': work_type,
            'title': title or f"Address issue from {Path(source_file).name}",
            'description': description,
            'priority': priority,
            'source': 'error_monitor',
            'source_file': source_file,
            'context': {
                'log_entry': log_entry,
                'discovered_at': datetime.utcnow().isoformat(),
                'source_type': 'json_log'
            }
        }
        
        return work_item
    
    def _extract_title_from_json(self, log_entry: dict) -> str:
        """Extract a meaningful title from JSON log entry"""
        # Common title fields
        title_fields = ['title', 'summary', 'message', 'error', 'issue', 'subject']
        
        for field in title_fields:
            if field in log_entry and isinstance(log_entry[field], str):
                title = log_entry[field].strip()
                if title:
                    return title[:100]  # Limit title length
        
        # If no direct title, try to construct one
        if 'error' in log_entry:
            return f"Fix error: {str(log_entry['error'])[:50]}..."
        
        return ""
    
    def _extract_description_from_json(self, log_entry: dict) -> str:
        """Extract a detailed description from JSON log entry"""
        description_parts = []
        
        # Add timestamp if available
        if 'timestamp' in log_entry:
            description_parts.append(f"Timestamp: {log_entry['timestamp']}")
        
        # Add error details
        if 'error' in log_entry:
            description_parts.append(f"Error: {log_entry['error']}")
        
        if 'traceback' in log_entry:
            description_parts.append(f"Traceback: {log_entry['traceback']}")
        
        if 'details' in log_entry:
            description_parts.append(f"Details: {json.dumps(log_entry['details'], indent=2)}")
        
        # Add feedback content
        if 'feedback' in log_entry:
            description_parts.append(f"Feedback: {log_entry['feedback']}")
        
        if 'message' in log_entry and 'error' not in log_entry:
            description_parts.append(f"Message: {log_entry['message']}")
        
        # Add context information
        context_fields = ['file', 'function', 'line', 'component', 'module']
        for field in context_fields:
            if field in log_entry:
                description_parts.append(f"{field.title()}: {log_entry[field]}")
        
        return "\n\n".join(description_parts) if description_parts else ""
    
    async def _process_text_log(self, file_path: str) -> List[Dict[str, Any]]:
        """Process plain text log files"""
        work_items = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Look for error patterns in text logs
            error_patterns = [
                'ERROR:', 'CRITICAL:', 'FATAL:', 'Exception:', 'Traceback',
                'failed', 'error', 'crash', 'bug'
            ]
            
            lines = content.split('\n')
            current_error = []
            in_error_block = False
            
            for line in lines:
                line_lower = line.lower()
                
                # Start of error block
                if any(pattern.lower() in line_lower for pattern in error_patterns):
                    if current_error:  # Save previous error
                        work_item = self._create_work_item_from_text(current_error, file_path)
                        if work_item:
                            work_items.append(work_item)
                    current_error = [line]
                    in_error_block = True
                elif in_error_block:
                    # Continue collecting error lines
                    if line.strip():  # Non-empty line
                        current_error.append(line)
                    else:  # Empty line might end error block
                        if len(current_error) > 1:  # Multi-line error
                            work_item = self._create_work_item_from_text(current_error, file_path)
                            if work_item:
                                work_items.append(work_item)
                        current_error = []
                        in_error_block = False
            
            # Handle final error block
            if current_error:
                work_item = self._create_work_item_from_text(current_error, file_path)
                if work_item:
                    work_items.append(work_item)
                    
        except Exception as e:
            logger.error(f"Error processing text log {file_path}: {e}")
        
        return work_items
    
    def _create_work_item_from_text(self, error_lines: List[str], source_file: str) -> Dict[str, Any]:
        """Create work item from text log error lines"""
        if not error_lines:
            return None
        
        first_line = error_lines[0].strip()
        full_error = "\n".join(error_lines)
        
        # Extract title from first line
        title = f"Fix error: {first_line[:50]}..." if len(first_line) > 50 else f"Fix error: {first_line}"
        
        work_item = {
            'type': 'bug_fix',
            'title': title,
            'description': f"Error found in log file:\n\n{full_error}",
            'priority': 4,  # High priority for errors
            'source': 'error_monitor',
            'source_file': source_file,
            'context': {
                'error_lines': error_lines,
                'discovered_at': datetime.utcnow().isoformat(),
                'source_type': 'text_log'
            }
        }
        
        return work_item
    
    async def _get_active_task_files(self) -> set:
        """Get files that already have pending or active tasks"""
        active_files = set()
        
        try:
            # Get recent pending and active tasks
            pending_tasks = await self.work_queue.get_recent_work(limit=100, status='pending')
            active_tasks = await self.work_queue.get_recent_work(limit=20, status='active')
            
            for task in pending_tasks + active_tasks:
                if task.get('source_file'):
                    active_files.add(task['source_file'])
            
        except Exception as e:
            logger.debug(f"Could not get active task files: {e}")
        
        return active_files
    
    async def _generate_maintenance_tasks(self) -> List[Dict[str, Any]]:
        """Generate simple maintenance tasks when no work is found"""
        maintenance_tasks = []
        
        try:
            # Find Python files in the project that might need attention
            project_files = []
            for root, dirs, files in os.walk('..'):
                # Skip certain directories
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'venv', '.venv', 'node_modules']]
                
                for file in files:
                    if file.endswith('.py') and not file.startswith('.'):
                        file_path = os.path.join(root, file)
                        project_files.append(file_path)
            
            # Select a few files for maintenance tasks
            import random
            selected_files = random.sample(project_files, min(3, len(project_files)))
            
            maintenance_types = [
                {
                    'type': 'documentation',
                    'title_template': 'Review and improve documentation in {}',
                    'description_template': 'Review the documentation and comments in {} and improve clarity, completeness, and accuracy.',
                    'priority': 2
                },
                {
                    'type': 'refactor', 
                    'title_template': 'Code review and optimization for {}',
                    'description_template': 'Review {} for potential improvements: code clarity, performance, error handling, and best practices.',
                    'priority': 2
                },
                {
                    'type': 'test',
                    'title_template': 'Review test coverage for {}', 
                    'description_template': 'Analyze {} and ensure adequate test coverage. Add missing tests for critical functionality.',
                    'priority': 3
                }
            ]
            
            for file_path in selected_files:
                filename = os.path.basename(file_path)
                task_type = random.choice(maintenance_types)
                
                maintenance_tasks.append({
                    'type': task_type['type'],
                    'title': task_type['title_template'].format(filename),
                    'description': task_type['description_template'].format(file_path),
                    'priority': task_type['priority'],
                    'source': 'maintenance_generator',
                    'source_file': file_path,
                    'context': {
                        'maintenance_task': True,
                        'task_type': task_type['type'],
                        'discovered_at': datetime.utcnow().isoformat(),
                        'source_type': 'maintenance'
                    }
                })
            
            if maintenance_tasks:
                logger.info(f"Generated {len(maintenance_tasks)} maintenance tasks")
                
        except Exception as e:
            logger.error(f"Error generating maintenance tasks: {e}")
        
        return maintenance_tasks
    
    async def health_check(self) -> dict:
        """Return health status of the error monitor"""
        accessible_paths = []
        for path in self.paths:
            if os.path.exists(path):
                accessible_paths.append(path)
        
        return {
            "paths_configured": len(self.paths),
            "paths_accessible": len(accessible_paths),
            "patterns": self.patterns,
            "max_age_hours": self.max_age_hours,
            "processed_files": len(self.processed_files)
        }