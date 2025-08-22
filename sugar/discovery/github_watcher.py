"""
GitHub Issue Watcher - Discover work from GitHub issues and PRs
Supports both GitHub CLI (gh) and PyGithub authentication
"""
import asyncio
import logging
import subprocess
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Optional PyGithub import
try:
    from github import Github, GithubException
    PYGITHUB_AVAILABLE = True
except ImportError:
    PYGITHUB_AVAILABLE = False

logger = logging.getLogger(__name__)

class GitHubWatcher:
    """Monitor GitHub repository for issues and pull requests"""
    
    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.repo_name = config.get('repo', '')
        self.auth_method = config.get('auth_method', 'auto')
        
        if not self.enabled:
            return
            
        if not self.repo_name:
            logger.warning("GitHub repo not configured - GitHub watching disabled")
            self.enabled = False
            return
        
        # Check authentication methods
        self.gh_cli_available = False
        self.pygithub_available = False
        
        # Try GitHub CLI first if specified
        if self.auth_method in ['gh_cli', 'auto']:
            self.gh_cli_available = self._check_gh_cli()
            
        # Try PyGithub if CLI not available or method is token/auto
        if self.auth_method in ['token', 'auto'] and not self.gh_cli_available:
            self.pygithub_available = self._init_pygithub()
            
        # Determine if we can proceed
        if self.auth_method == 'gh_cli' and not self.gh_cli_available:
            logger.warning("GitHub CLI specified but not available - GitHub watching disabled")
            self.enabled = False
        elif self.auth_method == 'token' and not self.pygithub_available:
            logger.warning("Token auth specified but PyGithub not available - GitHub watching disabled")
            self.enabled = False
        elif self.auth_method == 'auto' and not (self.gh_cli_available or self.pygithub_available):
            logger.warning("Neither GitHub CLI nor PyGithub available - GitHub watching disabled")
            self.enabled = False
            
        if self.enabled:
            method = "GitHub CLI" if self.gh_cli_available else "PyGithub"
            logger.info(f"✅ GitHub watcher initialized for {self.repo_name} using {method}")
    
    def _check_gh_cli(self) -> bool:
        """Check if GitHub CLI is available and authenticated"""
        try:
            gh_command = self.config.get('gh_cli', {}).get('command', 'gh')
            
            # Check if gh CLI is available
            result = subprocess.run([gh_command, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.debug("GitHub CLI not found")
                return False
            
            # Check if authenticated
            result = subprocess.run([gh_command, 'auth', 'status'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.debug("GitHub CLI not authenticated")
                return False
                
            logger.info("🔑 GitHub CLI available and authenticated")
            return True
            
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"GitHub CLI check failed: {e}")
            return False
    
    def _init_pygithub(self) -> bool:
        """Initialize PyGithub if available"""
        if not PYGITHUB_AVAILABLE:
            logger.debug("PyGithub not available")
            return False
            
        token = self.config.get('token', '') or os.getenv('GITHUB_TOKEN', '')
        if not token:
            logger.debug("No GitHub token configured")
            return False
        
        try:
            self.github = Github(token)
            # Test the connection
            repo = self.github.get_repo(self.repo_name)
            logger.info("🔑 PyGithub initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize PyGithub: {e}")
            return False
    
    async def discover(self) -> List[Dict[str, Any]]:
        """Discover work items from GitHub issues and PRs"""
        if not self.enabled:
            return []
        
        work_items = []
        
        try:
            if self.gh_cli_available:
                # Use GitHub CLI
                issues_work = await self._discover_issues_gh_cli()
                work_items.extend(issues_work)
            elif self.pygithub_available:
                # Use PyGithub
                issues_work = await self._discover_issues_pygithub()
                work_items.extend(issues_work)
            
        except Exception as e:
            logger.error(f"Error discovering GitHub work: {e}")
        
        logger.debug(f"🔍 GitHubWatcher discovered {len(work_items)} work items")
        return work_items
    
    async def _discover_issues_gh_cli(self) -> List[Dict[str, Any]]:
        """Discover work from GitHub issues using GitHub CLI"""
        work_items = []
        
        try:
            gh_command = self.config.get('gh_cli', {}).get('command', 'gh')
            issue_labels = self.config.get('issue_labels', ['bug', 'enhancement'])
            
            # Get all open issues first (we'll filter by labels after)
            cmd = [
                gh_command, 'issue', 'list',
                '--repo', self.repo_name,
                '--state', 'open',
                '--limit', '50',  # Get more issues to filter from
                '--json', 'number,title,body,labels,assignees,comments,createdAt,updatedAt,url'
            ]
            
            # Note: We don't use --label flag here because it uses AND logic
            # Instead we'll filter by labels after getting the results
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.error(f"GitHub CLI issue command failed: {result.stderr}")
                return []
            
            issues = json.loads(result.stdout)
            
            # Filter issues by labels (OR logic - issue needs at least one matching label)
            filtered_issues = []
            for issue in issues:
                issue_label_names = [label['name'].lower() for label in issue.get('labels', [])]
                config_labels = [label.lower() for label in issue_labels]
                
                # Check if issue has any of the configured labels
                if any(label in issue_label_names for label in config_labels):
                    filtered_issues.append(issue)
                elif not issue_labels:  # If no label filter configured, include all issues
                    filtered_issues.append(issue)
            
            # Limit to 10 issues after filtering
            filtered_issues = filtered_issues[:10]
            
            logger.debug(f"Found {len(issues)} total issues, {len(filtered_issues)} match label filter: {issue_labels}")
            
            for issue in filtered_issues:
                work_item = self._create_work_item_from_issue_data(issue)
                if work_item:
                    work_items.append(work_item)
                    
        except Exception as e:
            logger.error(f"Error getting issues via GitHub CLI: {e}")
        
        return work_items
    
    async def _discover_issues_pygithub(self) -> List[Dict[str, Any]]:
        """Discover work from GitHub issues using PyGithub"""
        work_items = []
        
        try:
            # Get recent issues
            since = datetime.utcnow() - timedelta(days=7)
            repo = self.github.get_repo(self.repo_name)
            issues = repo.get_issues(state='open', since=since, sort='created')
            
            for issue in issues[:10]:  # Limit to 10 most recent
                # Skip pull requests (they show up in issues)
                if issue.pull_request:
                    continue
                
                # Convert PyGithub issue to dict format
                issue_data = {
                    'number': issue.number,
                    'title': issue.title,
                    'body': issue.body,
                    'labels': [{'name': label.name} for label in issue.labels],
                    'assignees': [{'login': issue.assignee.login}] if issue.assignee else [],
                    'comments': issue.comments,
                    'createdAt': issue.created_at.isoformat(),
                    'updatedAt': issue.updated_at.isoformat(),
                    'url': issue.html_url
                }
                
                work_item = self._create_work_item_from_issue_data(issue_data)
                if work_item:
                    work_items.append(work_item)
                    
        except Exception as e:
            logger.error(f"GitHub API error getting issues: {e}")
        
        return work_items
    
    def _create_work_item_from_issue_data(self, issue: dict) -> Optional[Dict[str, Any]]:
        """Create work item from GitHub issue data (works with both CLI and PyGithub)"""
        
        # Determine work type from labels
        work_type = 'feature'  # default
        priority = 3  # default
        
        labels = [label['name'].lower() for label in issue.get('labels', [])]
        
        if any(label in labels for label in ['bug', 'error', 'critical']):
            work_type = 'bug_fix'
            priority = 4
        elif any(label in labels for label in ['enhancement', 'feature']):
            work_type = 'feature'
            priority = 3
        elif any(label in labels for label in ['documentation', 'docs']):
            work_type = 'documentation'
            priority = 2
        elif any(label in labels for label in ['test', 'testing']):
            work_type = 'test'
            priority = 3
        
        # Increase priority for urgent labels
        if any(label in labels for label in ['urgent', 'high priority', 'critical']):
            priority = min(5, priority + 1)
        
        # Skip if assigned to someone else (optional)
        assignees = issue.get('assignees', [])
        if self.config.get('only_unassigned', False) and assignees:
            return None
        
        work_item = {
            'type': work_type,
            'title': f"Address GitHub issue: {issue['title']}",
            'description': self._format_issue_description(issue),
            'priority': priority,
            'source': 'github_watcher',
            'source_file': f"github://issues/{issue['number']}",
            'context': {
                'github_issue': {
                    'number': issue['number'],
                    'url': issue['url'],
                    'labels': labels,
                    'assignees': [a.get('login') for a in issue.get('assignees', [])],
                    'comments': issue.get('comments', 0),
                    'created_at': issue['createdAt'],
                    'updated_at': issue['updatedAt']
                },
                'discovered_at': datetime.utcnow().isoformat(),
                'source_type': 'github_issue'
            }
        }
        
        return work_item
    
    def _format_issue_description(self, issue: dict) -> str:
        """Format GitHub issue into work description"""
        description_parts = [
            f"**GitHub Issue #{issue['number']}**",
            f"URL: {issue['url']}",
            f"Created: {issue['createdAt']}",
            f"Comments: {issue.get('comments', 0)}",
            ""
        ]
        
        if issue.get('labels'):
            label_names = [label['name'] for label in issue['labels']]
            description_parts.append(f"Labels: {', '.join(label_names)}")
            description_parts.append("")
        
        assignees = issue.get('assignees', [])
        if assignees:
            assignee_names = [a.get('login', 'unknown') for a in assignees]
            description_parts.append(f"Assigned to: {', '.join(assignee_names)}")
            description_parts.append("")
        
        description_parts.append("**Issue Description:**")
        description_parts.append(issue.get('body') or "No description provided.")
        
        return "\n".join(description_parts)
    
    async def health_check(self) -> dict:
        """Return health status of GitHub watcher"""
        if not self.enabled:
            return {
                "enabled": False,
                "reason": "GitHub integration disabled or not configured"
            }
        
        method = "GitHub CLI" if self.gh_cli_available else "PyGithub"
        
        try:
            if self.gh_cli_available:
                # Test GitHub CLI
                gh_command = self.config.get('gh_cli', {}).get('command', 'gh')
                result = subprocess.run([gh_command, 'auth', 'status'], 
                                      capture_output=True, text=True, timeout=10)
                auth_ok = result.returncode == 0
                
                return {
                    "enabled": True,
                    "method": method,
                    "repository": self.repo_name,
                    "authenticated": auth_ok,
                    "last_check": datetime.utcnow().isoformat()
                }
            elif self.pygithub_available:
                # Test PyGithub API access
                rate_limit = self.github.get_rate_limit()
                
                return {
                    "enabled": True,
                    "method": method,
                    "repository": self.repo_name,
                    "api_rate_limit": {
                        "remaining": rate_limit.core.remaining,
                        "limit": rate_limit.core.limit,
                        "reset": rate_limit.core.reset.isoformat()
                    },
                    "last_check": datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            return {
                "enabled": True,
                "method": method,
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def comment_on_issue(self, issue_number: int, comment_body: str) -> bool:
        """Add a comment to a GitHub issue"""
        if not self.enabled:
            return False
            
        try:
            if self.gh_cli_available:
                return await self._comment_via_gh_cli(issue_number, comment_body)
            elif self.pygithub_available:
                return await self._comment_via_pygithub(issue_number, comment_body)
            else:
                logger.warning("No GitHub authentication method available for commenting")
                return False
                
        except Exception as e:
            logger.error(f"Error commenting on GitHub issue #{issue_number}: {e}")
            return False
    
    async def assign_issue(self, issue_number: int) -> bool:
        """Assign a GitHub issue to the authenticated user"""
        if not self.enabled:
            return False
            
        try:
            if self.gh_cli_available:
                return await self._assign_via_gh_cli(issue_number)
            elif self.pygithub_available:
                return await self._assign_via_pygithub(issue_number)
            else:
                logger.warning("No GitHub authentication method available for assignment")
                return False
                
        except Exception as e:
            logger.error(f"Error assigning GitHub issue #{issue_number}: {e}")
            return False
    
    async def _comment_via_gh_cli(self, issue_number: int, comment_body: str) -> bool:
        """Add comment using GitHub CLI"""
        try:
            gh_command = self.config.get('gh_cli', {}).get('command', 'gh')
            
            cmd = [
                gh_command, 'issue', 'comment', str(issue_number),
                '--repo', self.repo_name,
                '--body', comment_body
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info(f"✅ Added comment to GitHub issue #{issue_number}")
                return True
            else:
                logger.error(f"GitHub CLI comment failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error using GitHub CLI to comment: {e}")
            return False
    
    async def _comment_via_pygithub(self, issue_number: int, comment_body: str) -> bool:
        """Add comment using PyGithub"""
        try:
            repo = self.github.get_repo(self.repo_name)
            issue = repo.get_issue(issue_number)
            issue.create_comment(comment_body)
            logger.info(f"✅ Added comment to GitHub issue #{issue_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error using PyGithub to comment: {e}")
            return False
    
    async def _assign_via_gh_cli(self, issue_number: int) -> bool:
        """Assign issue using GitHub CLI"""
        try:
            gh_command = self.config.get('gh_cli', {}).get('command', 'gh')
            
            cmd = [
                gh_command, 'issue', 'edit', str(issue_number),
                '--repo', self.repo_name,
                '--add-assignee', '@me'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info(f"✅ Assigned GitHub issue #{issue_number} to authenticated user")
                return True
            else:
                logger.error(f"GitHub CLI assignment failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error using GitHub CLI to assign: {e}")
            return False
    
    async def _assign_via_pygithub(self, issue_number: int) -> bool:
        """Assign issue using PyGithub"""
        try:
            repo = self.github.get_repo(self.repo_name)
            issue = repo.get_issue(issue_number)
            
            # Get current user
            user = self.github.get_user()
            
            # Add current user to assignees (preserving existing ones)
            current_assignees = [assignee.login for assignee in issue.assignees]
            if user.login not in current_assignees:
                current_assignees.append(user.login)
                issue.edit(assignees=current_assignees)
                logger.info(f"✅ Assigned GitHub issue #{issue_number} to {user.login}")
            else:
                logger.debug(f"GitHub issue #{issue_number} already assigned to {user.login}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error using PyGithub to assign: {e}")
            return False