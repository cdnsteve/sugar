"""
Test Coverage Analyzer - Discover testing gaps and opportunities.

This module provides functionality for analyzing codebases to identify:
- Source files lacking corresponding test files
- Existing test files with quality issues (missing assertions, low coverage)
- Complex functions that would benefit from additional test coverage

The analyzer uses static analysis (AST parsing) to examine code structure
and heuristics to match source files with their corresponding test files
based on common naming conventions (e.g., auth.py -> test_auth.py).

Example Usage:
    config = {
        "root_path": ".",
        "source_dirs": ["src", "lib"],
        "test_dirs": ["tests"],
    }
    analyzer = TestCoverageAnalyzer(config)
    work_items = await analyzer.discover()

Typical Workflow:
    1. Analyzer scans source directories for code files
    2. Analyzer scans test directories for test files
    3. Cross-references to find untested source files
    4. Analyzes test quality in existing test files
    5. Identifies complex functions needing test coverage
    6. Returns prioritized work items for test creation/improvement
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
import ast
import re

logger = logging.getLogger(__name__)


class TestCoverageAnalyzer:
    """
    Analyze codebase for testing gaps and opportunities.

    This analyzer discovers work items related to test coverage by:
    - Finding source files without corresponding test files
    - Analyzing test file quality (assertions, coverage ratios)
    - Identifying complex functions that need comprehensive testing

    Attributes:
        config: Configuration dictionary for the analyzer.
        root_path: Absolute path to the project root directory.
        source_dirs: List of directory names containing source code.
        test_dirs: List of directory names containing test files.
        excluded_dirs: List of directory names to exclude from analysis.
        test_file_patterns: Regex patterns for identifying test files.

    Security:
        The analyzer validates paths to prevent directory traversal attacks
        and ensures all file operations stay within the project boundaries.
    """

    def __init__(self, config: dict) -> None:
        """
        Initialize the test coverage analyzer.

        Args:
            config: Configuration dictionary with the following keys:
                - root_path (str): Project root directory. Defaults to ".".
                    Security: Paths with ".." or absolute paths are rejected.
                - source_dirs (list[str]): Directories containing source code.
                    Defaults to ["src", "lib", "app"].
                - test_dirs (list[str]): Directories containing test files.
                    Defaults to ["tests", "test", "__tests__", "spec"].
                - excluded_dirs (list[str]): Directories to skip during analysis.
                    Defaults include common virtual env and cache directories.
                - test_file_patterns (list[str]): Regex patterns for test files.
                    Defaults support Python (test_*.py, *_test.py) and
                    JavaScript/TypeScript (*.test.js, *.spec.ts) conventions.

        Raises:
            No explicit exceptions, but logs warnings for suspicious paths.
        """
        self.config = config
        # Ensure root_path stays within project directory
        root_path = config.get("root_path", ".")
        if root_path != "." and (".." in root_path or root_path.startswith("/")):
            logger.warning(
                f"Suspicious root_path '{root_path}', defaulting to current directory '.'"
            )
            root_path = "."
        self.root_path = os.path.abspath(root_path)
        self.source_dirs = config.get("source_dirs", ["src", "lib", "app"])
        self.test_dirs = config.get("test_dirs", ["tests", "test", "__tests__", "spec"])
        self.excluded_dirs = config.get(
            "excluded_dirs",
            [
                "node_modules",
                ".git",
                "__pycache__",
                "venv",
                ".venv",
                "env",
                ".env",
                "ENV",
                "env.bak",
                "venv.bak",
                "virtualenv",
                "build",
                "dist",
                ".tox",
                ".nox",
                "coverage",
                "htmlcov",
                ".pytest_cache",
                ".sugar",
                ".claude",
            ],
        )
        self.test_file_patterns = config.get(
            "test_file_patterns",
            [
                r"test_.*\.py$",
                r".*_test\.py$",
                r".*\.test\.(js|ts)$",
                r".*\.spec\.(js|ts)$",
            ],
        )

    def _should_exclude_path(self, path: str) -> bool:
        """
        Check if a path should be excluded from analysis.

        A path is excluded if:
        1. It resolves to a location outside the project root (security check)
        2. Any path component matches an entry in excluded_dirs
        3. The path string contains any excluded directory name

        Args:
            path: Relative or absolute path to check.

        Returns:
            True if the path should be excluded, False otherwise.
        """
        path_obj = Path(path)

        # Security check: Ensure path stays within project boundaries
        abs_path = os.path.abspath(path)
        if not abs_path.startswith(self.root_path):
            logger.warning(f"Path '{path}' is outside project directory, excluding")
            return True

        # Check if any part of the path matches excluded directories
        for part in path_obj.parts:
            if part in self.excluded_dirs:
                return True

        # Check if the path contains any excluded patterns
        path_str = str(path_obj)
        for excluded in self.excluded_dirs:
            if excluded in path_str:
                return True

        return False

    async def discover(self) -> List[Dict[str, Any]]:
        """
        Discover testing gaps and opportunities in the codebase.

        Performs three types of analysis:
        1. Finds source files without corresponding test files
        2. Analyzes existing test files for quality issues
        3. Identifies complex functions that need comprehensive testing

        Returns:
            List of work item dictionaries, each containing:
                - type: Always "test"
                - title: Human-readable description of the work
                - description: Detailed markdown description
                - priority: Integer priority (higher = more important)
                - source: Always "test_coverage"
                - source_file: Path to the file needing work
                - context: Additional metadata about the issue

        Note:
            Results are prioritized by priority field and limited to 8 items
            to avoid overwhelming the work queue.
        """
        work_items = []

        try:
            # Find source files without tests
            untested_files = await self._find_untested_files()
            for file_path in untested_files:
                work_item = self._create_test_work_item(file_path, "missing_tests")
                if work_item:
                    work_items.append(work_item)

            # Find test files with issues
            test_issues = await self._analyze_test_quality()
            for issue in test_issues:
                work_item = self._create_test_work_item(
                    issue["file_path"], "improve_tests", issue
                )
                if work_item:
                    work_items.append(work_item)

            # Find complex functions needing tests
            complex_functions = await self._find_complex_functions()
            for func_info in complex_functions:
                work_item = self._create_test_work_item(
                    func_info["file_path"], "test_complex_function", func_info
                )
                if work_item:
                    work_items.append(work_item)

        except Exception as e:
            logger.error(f"Error in test coverage analysis: {e}")

        # Prioritize and limit results
        work_items = self._prioritize_test_work(work_items)

        logger.debug(f"🔍 TestCoverageAnalyzer discovered {len(work_items)} work items")
        return work_items

    async def _find_untested_files(self) -> List[str]:
        """
        Find source files that lack corresponding test files.

        Uses naming conventions to match source files to test files:
        - auth.py is considered tested if test_auth.py or auth_test.py exists
        - user.js is considered tested if user.test.js or user.spec.js exists

        Returns:
            List of file paths for source files without matching test files.
            Limited to first 20 source files to avoid overwhelming results.
        """
        source_files = []
        test_files = set()

        # Collect all source files
        for root, dirs, files in os.walk(self.root_path):
            # Skip excluded directories
            if self._should_exclude_path(root):
                dirs[:] = []  # Don't recurse into this directory
                continue

            # Filter out excluded subdirectories before walking into them
            dirs[:] = [
                d for d in dirs if not self._should_exclude_path(os.path.join(root, d))
            ]

            # Skip non-source directories early
            path_parts = Path(root).parts
            if not any(src_dir in path_parts for src_dir in self.source_dirs):
                continue

            for file in files:
                file_path = os.path.join(root, file)

                # Skip excluded files
                if self._should_exclude_path(file_path):
                    continue

                if file.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
                    source_files.append(file_path)

        # Collect all test files and extract what they might be testing
        for root, dirs, files in os.walk(self.root_path):
            # Skip excluded directories
            if self._should_exclude_path(root):
                dirs[:] = []  # Don't recurse into this directory
                continue

            # Filter out excluded subdirectories before walking into them
            dirs[:] = [
                d for d in dirs if not self._should_exclude_path(os.path.join(root, d))
            ]

            for file in files:
                file_path = os.path.join(root, file)

                # Skip excluded files
                if self._should_exclude_path(file_path):
                    continue

                if self._is_test_file(file):
                    test_files.add(self._extract_tested_module_name(file))

        # Find source files without corresponding tests
        untested_files = []
        for source_file in source_files[:20]:  # Limit to avoid overwhelming
            module_name = self._extract_module_name(source_file)
            if module_name not in test_files:
                untested_files.append(source_file)

        return untested_files

    def _is_test_file(self, filename: str) -> bool:
        """
        Check if a file is a test file based on configured patterns.

        Args:
            filename: The filename (not full path) to check.

        Returns:
            True if the filename matches any test file pattern.
        """
        for pattern in self.test_file_patterns:
            if re.search(pattern, filename):
                return True
        return False

    def _extract_module_name(self, file_path: str) -> str:
        """
        Extract the module name from a source file path.

        Args:
            file_path: Full path to the source file.

        Returns:
            Lowercase module name without extension.
            Example: "/path/to/AuthService.py" -> "authservice"
        """
        filename = os.path.basename(file_path)
        name, _ = os.path.splitext(filename)
        return name.lower()

    def _extract_tested_module_name(self, test_filename: str) -> str:
        """
        Extract the module name that a test file is testing.

        Strips common test prefixes, suffixes, and file extensions to derive
        the name of the module under test.

        Args:
            test_filename: The test filename (not full path).

        Returns:
            Lowercase name of the module being tested.

        Examples:
            - "test_auth.py" -> "auth"
            - "auth_test.py" -> "auth"
            - "auth.test.js" -> "auth"
            - "user.spec.ts" -> "user"
        """
        name = test_filename.lower()

        # Remove test prefixes/suffixes
        patterns_to_remove = [r"^test_", r"_test$", r"\.test$", r"\.spec$"]

        for pattern in patterns_to_remove:
            name = re.sub(pattern, "", name)

        # Remove file extensions
        name = re.sub(r"\.(py|js|ts|jsx|tsx)$", "", name)

        return name

    async def _analyze_test_quality(self) -> List[Dict[str, Any]]:
        """
        Analyze existing test files for quality issues.

        Scans all test files in the project and checks for common issues:
        - Missing assertions in test methods
        - Low assertion-to-test ratios
        - Syntax errors in test files
        - Insufficient number of test cases

        Returns:
            List of issue dictionaries, each containing:
                - type: Issue category (e.g., "missing_assertions")
                - file_path: Path to the problematic test file
                - description: Human-readable issue description
                - suggestion: Recommended fix
        """
        test_issues = []

        for root, dirs, files in os.walk(self.root_path):
            # Skip excluded directories
            if self._should_exclude_path(root):
                logger.debug(
                    f"Skipping excluded directory in test quality analysis: {root}"
                )
                dirs[:] = []  # Don't recurse into this directory
                continue

            # Filter out excluded subdirectories before walking into them
            original_dirs = dirs[:]
            dirs[:] = [
                d for d in dirs if not self._should_exclude_path(os.path.join(root, d))
            ]
            if len(dirs) != len(original_dirs):
                excluded_dirs = [d for d in original_dirs if d not in dirs]
                logger.debug(
                    f"Filtered out excluded subdirectories from {root}: {excluded_dirs}"
                )

            for file in files:
                if self._is_test_file(file):
                    file_path = os.path.join(root, file)

                    # Skip excluded files (double-check at file level)
                    if self._should_exclude_path(file_path):
                        logger.debug(f"Skipping excluded test file: {file_path}")
                        continue

                    try:
                        issues = await self._analyze_test_file(file_path)
                        test_issues.extend(issues)
                    except Exception as e:
                        logger.debug(f"Error analyzing test file {file_path}: {e}")

        return test_issues

    async def _analyze_test_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Analyze a single test file for quality issues.

        Performs language-specific analysis for Python and JavaScript/TypeScript
        files, plus generic checks applicable to all test files.

        Args:
            file_path: Full path to the test file to analyze.

        Returns:
            List of issue dictionaries found in the file. May be empty if
            no issues are detected or if the file cannot be read.
        """
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            lines = content.split("\n")

            if file_path.endswith(".py"):
                issues.extend(await self._analyze_python_test_file(file_path, content))
            elif file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
                issues.extend(await self._analyze_js_test_file(file_path, content))

            # Generic test issues
            test_function_count = len(
                [line for line in lines if re.search(r"def test_|it\(|test\(", line)]
            )

            if test_function_count < 3:
                issues.append(
                    {
                        "type": "insufficient_tests",
                        "file_path": file_path,
                        "description": f"Only {test_function_count} test functions found",
                        "suggestion": "Add more comprehensive test cases",
                    }
                )

        except Exception as e:
            logger.debug(f"Could not analyze test file {file_path}: {e}")

        return issues

    async def _analyze_python_test_file(
        self, file_path: str, content: str
    ) -> List[Dict[str, Any]]:
        """
        Analyze a Python test file for quality issues.

        Uses AST parsing to find test methods (functions starting with "test_")
        and verifies they contain assertions. Detects both assert statements
        and pytest/unittest assertion methods (e.g., self.assertEqual).

        Args:
            file_path: Path to the Python test file.
            content: File content as a string.

        Returns:
            List of issues found. Common issues include:
            - missing_assertions: Test method lacks assert statements
            - test_syntax_error: File cannot be parsed due to syntax errors
        """
        issues = []

        try:
            tree = ast.parse(content)

            test_methods = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    test_methods.append(node)

            # Check for missing assertions
            for method in test_methods:
                has_assert = any(
                    isinstance(n, ast.Assert)
                    or (
                        isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Attribute)
                        and n.func.attr.startswith("assert")
                    )
                    for n in ast.walk(method)
                )

                if not has_assert:
                    issues.append(
                        {
                            "type": "missing_assertions",
                            "file_path": file_path,
                            "description": f"Test method '{method.name}' lacks assertions",
                            "suggestion": f"Add assertions to verify {method.name} behavior",
                        }
                    )

        except SyntaxError:
            issues.append(
                {
                    "type": "test_syntax_error",
                    "file_path": file_path,
                    "description": "Test file has syntax errors",
                    "suggestion": "Fix syntax errors in test file",
                }
            )

        return issues

    async def _analyze_js_test_file(
        self, file_path: str, content: str
    ) -> List[Dict[str, Any]]:
        """
        Analyze a JavaScript/TypeScript test file for quality issues.

        Uses regex-based pattern matching to identify test functions
        (it(), test(), describe()) and expect() assertions. Calculates
        the assertion-to-test ratio to detect undertested code.

        Args:
            file_path: Path to the JS/TS test file.
            content: File content as a string.

        Returns:
            List of issues found. Common issues include:
            - insufficient_assertions: Low expect-to-test ratio
        """
        issues = []
        lines = content.split("\n")

        # Count test functions
        test_patterns = [r"\bit\(", r"\btest\(", r"\bdescribe\("]
        test_count = sum(
            len(re.findall(pattern, line))
            for line in lines
            for pattern in test_patterns
        )

        # Count expect statements
        expect_count = sum(len(re.findall(r"\bexpect\(", line)) for line in lines)

        # Check assertion to test ratio
        if test_count > 0 and expect_count / test_count < 1:
            issues.append(
                {
                    "type": "insufficient_assertions",
                    "file_path": file_path,
                    "description": f"Low assertion to test ratio ({expect_count}/{test_count})",
                    "suggestion": "Add more assertions to test cases",
                }
            )

        return issues

    async def _find_complex_functions(self) -> List[Dict[str, Any]]:
        """
        Find complex functions that would benefit from additional testing.

        Scans Python source files for functions with high cyclomatic complexity
        or excessive line counts. Complex functions are more likely to contain
        bugs and benefit from comprehensive test coverage.

        Thresholds:
            - Cyclomatic complexity > 5 (multiple decision points)
            - Line count > 20 (long functions)

        Returns:
            List of dictionaries describing complex functions, limited to
            the top 5 most complex. Each contains:
                - file_path: Path to the source file
                - function_name: Name of the complex function
                - complexity: Calculated cyclomatic complexity score
                - line_count: Number of lines in the function
                - line_number: Starting line of the function
        """
        complex_functions = []

        # Ensure we stay within project directory boundaries
        project_root = os.path.abspath(self.root_path)

        for root, dirs, files in os.walk(self.root_path):
            # Skip excluded directories
            if self._should_exclude_path(root):
                logger.debug(f"Skipping excluded directory: {root}")
                dirs[:] = []  # Don't recurse into this directory
                continue

            # Filter out excluded subdirectories before walking into them
            original_dirs = dirs[:]
            dirs[:] = [
                d for d in dirs if not self._should_exclude_path(os.path.join(root, d))
            ]
            if len(dirs) != len(original_dirs):
                excluded_dirs = [d for d in original_dirs if d not in dirs]
                logger.debug(
                    f"Filtered out excluded subdirectories from {root}: {excluded_dirs}"
                )

            # Focus on source directories (but only if not already excluded)
            path_parts = Path(root).parts
            if not any(src_dir in path_parts for src_dir in self.source_dirs):
                continue

            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)

                    # Skip excluded files (double-check at file level)
                    if self._should_exclude_path(file_path):
                        logger.debug(f"Skipping excluded file: {file_path}")
                        continue

                    try:
                        functions = await self._analyze_python_complexity(file_path)
                        complex_functions.extend(functions)
                    except Exception as e:
                        logger.debug(f"Error analyzing complexity in {file_path}: {e}")

        return complex_functions[:5]  # Limit to top 5 most complex

    async def _analyze_python_complexity(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Analyze a Python file to identify complex functions.

        Parses the file using AST and calculates cyclomatic complexity for
        each function. Functions exceeding complexity or size thresholds
        are flagged as needing additional test coverage.

        Args:
            file_path: Path to the Python source file to analyze.

        Returns:
            List of complex function metadata dictionaries.
        """
        complex_functions = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    complexity = self._calculate_cyclomatic_complexity(node)
                    line_count = getattr(node, "end_lineno", node.lineno) - node.lineno

                    if complexity > 5 or line_count > 20:  # Thresholds for complexity
                        complex_functions.append(
                            {
                                "file_path": file_path,
                                "function_name": node.name,
                                "complexity": complexity,
                                "line_count": line_count,
                                "line_number": node.lineno,
                            }
                        )

        except Exception as e:
            logger.debug(f"Could not analyze complexity in {file_path}: {e}")

        return complex_functions

    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """
        Calculate the cyclomatic complexity of a function.

        Cyclomatic complexity measures the number of linearly independent
        paths through a function. Higher values indicate more complex code
        that is harder to test and maintain.

        Calculation:
            - Start with base complexity of 1
            - Add 1 for each: if, while, for, except handler
            - Add (n-1) for each boolean operator with n operands

        Args:
            node: AST node representing the function definition.

        Returns:
            Integer complexity score. Common interpretations:
            - 1-4: Low complexity, easy to test
            - 5-7: Moderate complexity
            - 8-10: High complexity, consider refactoring
            - 11+: Very high complexity, refactoring recommended
        """
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _create_test_work_item(
        self, file_path: str, work_type: str, details: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create a work item for a testing-related task.

        Generates a structured work item that can be processed by Sugar's
        work queue system. Work items include detailed descriptions and
        context to help developers or AI agents understand and address
        the testing gap.

        Args:
            file_path: Path to the file requiring test work.
            work_type: Category of work needed. One of:
                - "missing_tests": Source file lacks test coverage
                - "improve_tests": Existing tests have quality issues
                - "test_complex_function": Complex function needs tests
            details: Additional context specific to the work type.
                For "improve_tests": includes description and suggestion.
                For "test_complex_function": includes function_name,
                    complexity, line_count.

        Returns:
            Work item dictionary with type, title, description, priority,
            source, source_file, and context fields.
        """
        filename = os.path.basename(file_path)
        details = details or {}

        work_types = {
            "missing_tests": {
                "type": "test",
                "title": f"Add tests for {filename}",
                "priority": 3,
                "description": f"**Missing Test Coverage**\n\nFile: {file_path}\n\nThis source file appears to lack corresponding test coverage. Adding tests will help ensure code reliability and catch regressions.",
            },
            "improve_tests": {
                "type": "test",
                "title": f"Improve test quality in {filename}",
                "priority": 2,
                "description": f"**Test Quality Issues**\n\nFile: {file_path}\n\nIssue: {details.get('description', 'Quality issues detected')}\n\nSuggestion: {details.get('suggestion', 'Improve test coverage and quality')}",
            },
            "test_complex_function": {
                "type": "test",
                "title": f"Add tests for complex function in {filename}",
                "priority": 4,
                "description": f"**Complex Function Needs Testing**\n\nFile: {file_path}\nFunction: {details.get('function_name', 'Unknown')}\nComplexity: {details.get('complexity', 'High')}\nLines: {details.get('line_count', 'Many')}\n\nThis complex function should have comprehensive test coverage to ensure reliability.",
            },
        }

        template = work_types.get(work_type, work_types["missing_tests"])

        work_item = {
            "type": template["type"],
            "title": template["title"],
            "description": template["description"],
            "priority": template["priority"],
            "source": "test_coverage",
            "source_file": file_path,
            "context": {
                "test_analysis": {
                    "work_type": work_type,
                    "details": details,
                    "discovered_at": datetime.utcnow().isoformat(),
                    "source_type": "test_coverage",
                }
            },
        }

        return work_item

    def _prioritize_test_work(
        self, work_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Prioritize and deduplicate test work items.

        Sorts items by priority (higher values first) and removes duplicates
        based on source file path. Limits the result to prevent overwhelming
        the work queue with too many testing tasks at once.

        Args:
            work_items: List of work item dictionaries to process.

        Returns:
            Filtered and sorted list of up to 8 unique work items,
            ordered by priority (highest first).
        """
        # Sort by priority (high to low)
        work_items.sort(key=lambda x: x["priority"], reverse=True)

        # Limit total items and remove duplicates
        seen_files = set()
        filtered_items = []

        for item in work_items:
            file_path = item["source_file"]
            if file_path not in seen_files:
                seen_files.add(file_path)
                filtered_items.append(item)

        return filtered_items[:8]  # Limit to 8 test-related tasks

    async def health_check(self) -> dict:
        """
        Return the health status of the test coverage analyzer.

        Provides configuration information useful for diagnostics and
        verifying the analyzer is properly configured.

        Returns:
            Dictionary containing:
                - enabled: Always True (analyzer is operational)
                - root_path: Configured project root path
                - source_dirs: Directories searched for source files
                - test_dirs: Directories searched for test files
                - test_patterns: Regex patterns for identifying test files
        """
        return {
            "enabled": True,
            "root_path": self.root_path,
            "source_dirs": self.source_dirs,
            "test_dirs": self.test_dirs,
            "test_patterns": self.test_file_patterns,
        }
