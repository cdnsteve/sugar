"""
Code Quality Scanner - Discover improvement opportunities in the codebase
"""

import asyncio
import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Set
from pathlib import Path
import ast
import re

logger = logging.getLogger(__name__)


class CodeQualityScanner:
    """Scan codebase for quality improvement opportunities"""

    def __init__(self, config: dict):
        self.config = config
        # Ensure root_path stays within project directory
        root_path = config.get("root_path", ".")
        if root_path != "." and (".." in root_path or root_path.startswith("/")):
            logger.warning(
                f"Suspicious root_path '{root_path}', defaulting to current directory '.'"
            )
            root_path = "."
        self.root_path = os.path.abspath(root_path)
        self.file_extensions = config.get(
            "file_extensions", [".py", ".js", ".ts", ".jsx", ".tsx"]
        )
        self.excluded_dirs = set(
            config.get(
                "excluded_dirs",
                [
                    "node_modules",
                    ".git",
                    "__pycache__",
                    ".pytest_cache",
                    "venv",
                    "env",
                    ".venv",
                    ".env",
                    "ENV",
                    "env.bak",
                    "venv.bak",
                    "virtualenv",
                    "dist",
                    "build",
                    ".next",
                    ".tox",
                    ".nox",
                    "coverage",
                    "htmlcov",
                    ".sugar",
                    ".claude",
                ],
            )
        )
        self.max_files_per_scan = config.get("max_files_per_scan", 50)

    async def discover(self) -> List[Dict[str, Any]]:
        """Discover code quality improvement opportunities"""
        work_items = []

        try:
            # Find files to analyze
            files_to_scan = await self._get_files_to_scan()

            logger.debug(
                f"🔍 CodeQualityScanner scanning {len(files_to_scan)} files (max: {self.max_files_per_scan})"
            )

            # Analyze each file for quality issues
            for file_path in files_to_scan[: self.max_files_per_scan]:
                try:
                    # Extra safety check - don't analyze excluded paths
                    rel_path = os.path.relpath(file_path, self.root_path)
                    if self._path_contains_excluded_dir(rel_path):
                        logger.debug(f"🚫 Skipping excluded path: {rel_path}")
                        continue

                    issues = await self._analyze_file(file_path)
                    for issue in issues:
                        work_item = self._create_work_item_from_issue(issue, file_path)
                        if work_item:
                            work_items.append(work_item)
                except Exception as e:
                    logger.debug(f"Error analyzing {file_path}: {e}")

        except Exception as e:
            logger.error(f"Error in code quality scanning: {e}")

        # Remove duplicates and prioritize
        work_items = self._deduplicate_and_prioritize(work_items)

        logger.debug(f"🔍 CodeQualityScanner discovered {len(work_items)} work items")
        return work_items

    async def _get_files_to_scan(self) -> List[str]:
        """Get list of files to scan for quality issues"""
        files = []

        for root, dirs, filenames in os.walk(self.root_path):
            # Convert relative path for checking
            rel_root = os.path.relpath(root, self.root_path)

            # Skip if current path contains any excluded directories
            if self._path_contains_excluded_dir(rel_root):
                dirs.clear()  # Don't recurse into this directory
                continue

            # Filter out excluded directories from further traversal
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]

            for filename in filenames:
                if any(filename.endswith(ext) for ext in self.file_extensions):
                    file_path = os.path.join(root, filename)

                    # Double-check: Skip if file path contains excluded directories
                    rel_file_path = os.path.relpath(file_path, self.root_path)
                    if self._path_contains_excluded_dir(rel_file_path):
                        continue

                    # Skip very large files
                    try:
                        if os.path.getsize(file_path) > 100000:  # 100KB limit
                            continue
                    except OSError:
                        continue

                    files.append(file_path)

        return files

    def _path_contains_excluded_dir(self, path: str) -> bool:
        """Check if a path contains any excluded directory"""
        if path == "." or path == "":
            return False

        # Security check: Ensure path stays within project boundaries
        abs_path = os.path.abspath(path)
        if not abs_path.startswith(self.root_path):
            logger.warning(f"Path '{path}' is outside project directory, excluding")
            return True

        # Split path into components and check each
        path_parts = Path(path).parts
        for part in path_parts:
            if part in self.excluded_dirs:
                return True
        return False

    async def _analyze_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Analyze a single file for quality issues"""
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Different analyzers based on file type
            if file_path.endswith(".py"):
                issues.extend(await self._analyze_python_file(file_path, content))
            elif file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
                issues.extend(await self._analyze_javascript_file(file_path, content))

            # Generic analyzers for all files
            issues.extend(await self._analyze_generic_issues(file_path, content))

        except Exception as e:
            logger.debug(f"Could not analyze {file_path}: {e}")

        return issues

    async def _analyze_python_file(
        self, file_path: str, content: str
    ) -> List[Dict[str, Any]]:
        """Analyze Python file for quality issues"""
        issues = []
        lines = content.split("\n")

        try:
            # Parse AST for structural analysis
            tree = ast.parse(content)

            # Check for missing docstrings
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node):
                        issues.append(
                            {
                                "type": "missing_docstring",
                                "severity": "low",
                                "line": node.lineno,
                                "description": f"{node.__class__.__name__} '{node.name}' missing docstring",
                                "suggestion": f"Add docstring to {node.name}",
                            }
                        )

            # Check for long functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_lines = getattr(node, "end_lineno", node.lineno) - node.lineno
                    if func_lines > 50:
                        issues.append(
                            {
                                "type": "long_function",
                                "severity": "medium",
                                "line": node.lineno,
                                "description": f"Function '{node.name}' is {func_lines} lines long",
                                "suggestion": f"Consider breaking down {node.name} into smaller functions",
                            }
                        )

        except SyntaxError:
            issues.append(
                {
                    "type": "syntax_error",
                    "severity": "high",
                    "line": 1,
                    "description": "File has syntax errors",
                    "suggestion": "Fix syntax errors in the file",
                }
            )

        # Check for code smells
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # TODO comments
            if "TODO" in line_stripped or "FIXME" in line_stripped:
                issues.append(
                    {
                        "type": "todo_comment",
                        "severity": "low",
                        "line": i,
                        "description": "TODO/FIXME comment found",
                        "suggestion": "Address or remove TODO/FIXME comment",
                        "content": line_stripped[:100],
                    }
                )

            # Long lines
            if len(line) > 120:
                issues.append(
                    {
                        "type": "long_line",
                        "severity": "low",
                        "line": i,
                        "description": f"Line too long ({len(line)} characters)",
                        "suggestion": "Break line into multiple lines",
                    }
                )

        return issues

    async def _analyze_javascript_file(
        self, file_path: str, content: str
    ) -> List[Dict[str, Any]]:
        """Analyze JavaScript/TypeScript file for quality issues"""
        issues = []
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Console.log statements (shouldn't be in production)
            if re.search(r"console\.(log|warn|error)", line_stripped):
                issues.append(
                    {
                        "type": "console_statement",
                        "severity": "medium",
                        "line": i,
                        "description": "Console statement found",
                        "suggestion": "Remove or replace with proper logging",
                        "content": line_stripped[:100],
                    }
                )

            # TODO comments
            if "TODO" in line_stripped or "FIXME" in line_stripped:
                issues.append(
                    {
                        "type": "todo_comment",
                        "severity": "low",
                        "line": i,
                        "description": "TODO/FIXME comment found",
                        "suggestion": "Address or remove TODO/FIXME comment",
                        "content": line_stripped[:100],
                    }
                )

            # Debugger statements
            if "debugger" in line_stripped:
                issues.append(
                    {
                        "type": "debugger_statement",
                        "severity": "high",
                        "line": i,
                        "description": "Debugger statement found",
                        "suggestion": "Remove debugger statement",
                        "content": line_stripped[:100],
                    }
                )

        return issues

    async def _analyze_generic_issues(
        self, file_path: str, content: str
    ) -> List[Dict[str, Any]]:
        """Analyze generic code quality issues"""
        issues = []
        lines = content.split("\n")

        # Check for overly long files
        if len(lines) > 500:
            issues.append(
                {
                    "type": "large_file",
                    "severity": "medium",
                    "line": 1,
                    "description": f"File is very large ({len(lines)} lines)",
                    "suggestion": "Consider splitting into smaller modules",
                }
            )

        # Check for potential secrets (basic patterns)
        secret_patterns = [
            (r'api[_-]?key\s*[=:]\s*["\'][^"\']+["\']', "API key"),
            (r'password\s*[=:]\s*["\'][^"\']+["\']', "Password"),
            (r'token\s*[=:]\s*["\'][^"\']+["\']', "Token"),
            (r'secret\s*[=:]\s*["\'][^"\']+["\']', "Secret"),
        ]

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()

            for pattern, secret_type in secret_patterns:
                if (
                    re.search(pattern, line_lower)
                    and "your_" not in line_lower
                    and "example" not in line_lower
                ):
                    issues.append(
                        {
                            "type": "potential_secret",
                            "severity": "high",
                            "line": i,
                            "description": f"Potential {secret_type.lower()} found",
                            "suggestion": f"Move {secret_type.lower()} to environment variables",
                            "content": line[:50] + "..." if len(line) > 50 else line,
                        }
                    )

        return issues

    def _create_work_item_from_issue(
        self, issue: Dict[str, Any], file_path: str
    ) -> Dict[str, Any]:
        """Create work item from code quality issue"""

        severity_to_priority = {"high": 4, "medium": 3, "low": 2}

        priority = severity_to_priority.get(issue["severity"], 2)

        # Group similar issues into higher-level tasks
        work_type = "refactor"

        if issue["type"] in ["syntax_error", "debugger_statement", "potential_secret"]:
            work_type = "bug_fix"
            priority = 5  # Critical for security/syntax issues
        elif issue["type"] in ["missing_docstring", "todo_comment"]:
            work_type = "documentation"

        title = self._generate_title_from_issue(issue, file_path)
        description = self._generate_description_from_issue(issue, file_path)

        work_item = {
            "type": work_type,
            "title": title,
            "description": description,
            "priority": priority,
            "source": "code_quality",
            "source_file": file_path,
            "context": {
                "quality_issue": issue,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
                "source_type": "code_quality",
            },
        }

        return work_item

    def _generate_title_from_issue(self, issue: Dict[str, Any], file_path: str) -> str:
        """Generate work item title from quality issue"""
        filename = os.path.basename(file_path)

        title_templates = {
            "missing_docstring": f"Add documentation to {filename}",
            "long_function": f"Refactor large functions in {filename}",
            "syntax_error": f"Fix syntax errors in {filename}",
            "todo_comment": f"Address TODO comments in {filename}",
            "console_statement": f"Remove debug statements from {filename}",
            "debugger_statement": f"Remove debugger statements from {filename}",
            "potential_secret": f"Secure credentials in {filename}",
            "large_file": f"Split large file {filename}",
            "long_line": f"Fix line length issues in {filename}",
        }

        return title_templates.get(issue["type"], f"Improve code quality in {filename}")

    def _generate_description_from_issue(
        self, issue: Dict[str, Any], file_path: str
    ) -> str:
        """Generate detailed description from quality issue"""
        description_parts = [
            f"**Code Quality Issue in {file_path}**",
            f"Issue Type: {issue['type']}",
            f"Severity: {issue['severity']}",
            f"Line: {issue.get('line', 'N/A')}",
            "",
            f"**Description:** {issue['description']}",
            f"**Suggested Action:** {issue['suggestion']}",
        ]

        if "content" in issue:
            description_parts.extend(
                ["", "**Code Context:**", f"```", issue["content"], f"```"]
            )

        return "\n".join(description_parts)

    def _deduplicate_and_prioritize(
        self, work_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicates and limit to most important items"""

        # Group by file and issue type to avoid spam
        seen = set()
        filtered_items = []

        # Sort by priority (high to low)
        work_items.sort(key=lambda x: x["priority"], reverse=True)

        for item in work_items:
            # Create key for deduplication
            key = (item["source_file"], item["context"]["quality_issue"]["type"])

            if key not in seen:
                seen.add(key)
                filtered_items.append(item)

        # Limit total items to prevent overwhelming
        return filtered_items[:10]

    async def health_check(self) -> dict:
        """Return health status of code quality scanner"""
        return {
            "enabled": True,
            "root_path": self.root_path,
            "file_extensions": self.file_extensions,
            "excluded_dirs": list(self.excluded_dirs),
            "max_files_per_scan": self.max_files_per_scan,
        }
