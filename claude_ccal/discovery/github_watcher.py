"""
GitHub Issue Watcher - Discover work from GitHub issues and PRs
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os
import json

try:
    import git
    from github import Github, GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

logger = logging.getLogger(__name__)

class GitHubWatcher:
    """Monitor GitHub repository for issues and pull requests"""
    
    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get('enabled', False) and GITHUB_AVAILABLE
        
        if not GITHUB_AVAILABLE:
            logger.warning("PyGithub not available - GitHub watching disabled")
            self.enabled = False
            return
        
        self.repo_name = config.get('repo', '')
        self.token = config.get('token', '') or os.getenv('GITHUB_TOKEN', '')
        
        if not self.repo_name or not self.token:
            logger.warning("GitHub repo or token not configured - GitHub watching disabled")
            self.enabled = False
            return
        
        try:
            self.github = Github(self.token)
            self.repo = self.github.get_repo(self.repo_name)
            logger.info(f"✅ GitHub watcher initialized for {self.repo_name}")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {e}")
            self.enabled = False
    
    async def discover(self) -> List[Dict[str, Any]]:
        """Discover work items from GitHub issues and PRs"""
        if not self.enabled:
            return []
        
        work_items = []
        
        try:
            # Get recent issues
            issues_work = await self._discover_from_issues()
            work_items.extend(issues_work)
            
            # Get pull requests that need review/work
            pr_work = await self._discover_from_prs()
            work_items.extend(pr_work)
            
        except Exception as e:
            logger.error(f"Error discovering GitHub work: {e}")
        
        logger.info(f"🔍 GitHubWatcher discovered {len(work_items)} work items")
        return work_items
    
    async def _discover_from_issues(self) -> List[Dict[str, Any]]:
        """Discover work from GitHub issues"""
        work_items = []
        
        try:
            # Get open issues from last 7 days
            since = datetime.utcnow() - timedelta(days=7)
            issues = self.repo.get_issues(state='open', since=since, sort='created')
            
            for issue in issues[:10]:  # Limit to 10 most recent
                # Skip pull requests (they show up in issues)
                if issue.pull_request:
                    continue
                
                work_item = await self._create_work_item_from_issue(issue)
                if work_item:
                    work_items.append(work_item)
                    
        except GithubException as e:
            logger.error(f"GitHub API error getting issues: {e}")
        except Exception as e:
            logger.error(f"Error processing issues: {e}")
        
        return work_items
    
    async def _discover_from_prs(self) -> List[Dict[str, Any]]:
        """Discover work from pull requests"""
        work_items = []
        
        try:
            # Get open PRs that might need work
            prs = self.repo.get_pulls(state='open', sort='created')
            
            for pr in prs[:5]:  # Limit to 5 most recent
                # Check if PR has failing checks or needs review
                work_item = await self._create_work_item_from_pr(pr)
                if work_item:
                    work_items.append(work_item)
                    
        except GithubException as e:
            logger.error(f"GitHub API error getting PRs: {e}")
        except Exception as e:
            logger.error(f"Error processing PRs: {e}")
        
        return work_items
    
    async def _create_work_item_from_issue(self, issue) -> Optional[Dict[str, Any]]:
        """Create work item from GitHub issue"""
        
        # Determine work type from labels
        work_type = 'feature'  # default
        priority = 3  # default
        
        labels = [label.name.lower() for label in issue.labels]
        
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
        
        # Increase priority for high-priority labels
        if any(label in labels for label in ['urgent', 'high priority', 'critical']):
            priority = min(5, priority + 1)
        
        # Skip if too old or low engagement
        age_days = (datetime.utcnow() - issue.created_at.replace(tzinfo=None)).days
        if age_days > 30 and issue.comments < 2:
            return None
        
        work_item = {
            'type': work_type,
            'title': f"Address GitHub issue: {issue.title}",
            'description': self._format_issue_description(issue),
            'priority': priority,
            'source': 'github_watcher',
            'source_file': f"github://issues/{issue.number}",
            'context': {
                'github_issue': {
                    'number': issue.number,
                    'url': issue.html_url,
                    'state': issue.state,
                    'labels': labels,
                    'assignee': issue.assignee.login if issue.assignee else None,
                    'comments': issue.comments,
                    'created_at': issue.created_at.isoformat(),
                    'updated_at': issue.updated_at.isoformat()
                },
                'discovered_at': datetime.utcnow().isoformat(),
                'source_type': 'github_issue'
            }
        }
        
        return work_item
    
    async def _create_work_item_from_pr(self, pr) -> Optional[Dict[str, Any]]:
        """Create work item from pull request if it needs work"""
        
        # Check if PR has failing status checks
        try:
            commits = list(pr.get_commits())
            if not commits:
                return None
            
            latest_commit = commits[-1]
            statuses = list(latest_commit.get_statuses())
            
            failing_checks = [s for s in statuses if s.state in ['failure', 'error']]
            
            if not failing_checks:
                return None  # PR is healthy, no work needed
            
        except Exception as e:
            logger.debug(f"Could not check PR status: {e}")
            return None
        
        work_item = {
            'type': 'bug_fix',
            'title': f"Fix failing checks in PR: {pr.title}",
            'description': self._format_pr_description(pr, failing_checks),
            'priority': 4,  # High priority for broken PRs
            'source': 'github_watcher',
            'source_file': f"github://pulls/{pr.number}",
            'context': {
                'github_pr': {
                    'number': pr.number,
                    'url': pr.html_url,
                    'state': pr.state,
                    'failing_checks': [
                        {
                            'context': check.context,
                            'state': check.state,
                            'description': check.description,
                            'target_url': check.target_url
                        } for check in failing_checks
                    ],
                    'created_at': pr.created_at.isoformat(),
                    'updated_at': pr.updated_at.isoformat()
                },
                'discovered_at': datetime.utcnow().isoformat(),
                'source_type': 'github_pr'
            }
        }
        
        return work_item
    
    def _format_issue_description(self, issue) -> str:
        """Format GitHub issue into work description"""
        description_parts = [
            f"**GitHub Issue #{issue.number}**",
            f"URL: {issue.html_url}",
            f"State: {issue.state}",
            f"Created: {issue.created_at}",
            f"Comments: {issue.comments}",
            ""
        ]
        
        if issue.labels:
            labels = [label.name for label in issue.labels]
            description_parts.append(f"Labels: {', '.join(labels)}")
            description_parts.append("")
        
        if issue.assignee:
            description_parts.append(f"Assigned to: {issue.assignee.login}")
            description_parts.append("")
        
        description_parts.append("**Issue Description:**")
        description_parts.append(issue.body or "No description provided.")
        
        return "\n".join(description_parts)
    
    def _format_pr_description(self, pr, failing_checks) -> str:
        """Format PR with failing checks into work description"""
        description_parts = [
            f"**Pull Request #{pr.number} - Failing Checks**",
            f"URL: {pr.html_url}",
            f"State: {pr.state}",
            f"Created: {pr.created_at}",
            "",
            "**Failing Status Checks:**"
        ]
        
        for check in failing_checks:
            description_parts.append(f"- ❌ **{check.context}**: {check.description}")
            if check.target_url:
                description_parts.append(f"  Details: {check.target_url}")
        
        description_parts.extend([
            "",
            "**PR Description:**",
            pr.body or "No description provided."
        ])
        
        return "\n".join(description_parts)
    
    async def health_check(self) -> dict:
        """Return health status of GitHub watcher"""
        if not self.enabled:
            return {
                "enabled": False,
                "reason": "GitHub integration disabled or not configured"
            }
        
        try:
            # Test API access
            rate_limit = self.github.get_rate_limit()
            
            return {
                "enabled": True,
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
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }